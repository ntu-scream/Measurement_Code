import tkinter
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
import os
import time
import threading 
import mss
from datetime import datetime
from LockinAmp import lockinAmp
from keithley2400 import Keithley2400
from keithley import Keithley
from PIL import Image

root = Tk()
root.title('SOT MOKE Current Switching Measurement')

global current_output, measured_values, dataplot, fix_lbl, pulse_lbl, x1, y1, x2, y2

fig = plt.Figure(figsize=(6,5), dpi=100)
ax = fig.add_subplot(111)
current_output = []
measured_values = []
fix_lbl = [0]
pulse_lbl = [0]

x1=1086
y1=350
x2=1206
y2=428

def click(root2):
    print("X1: %d, Y1: %d" %(root2.winfo_x(), root2.winfo_y()))
    print("X2: %d, Y2: %d\n" %(root2.winfo_x()+root2.winfo_width(), root2.winfo_y()+root2.winfo_height()))
    global y1
    global x2
    global y2
    global x1
    x1 = root2.winfo_x()
    y1 = root2.winfo_y()
    x2 = root2.winfo_x()+root2.winfo_width()
    y2 = root2.winfo_y()+root2.winfo_height()

def perfSettings():

    perfFrame = Tk()

    perfFrame.title("Determine Capture Area Coordinates")
    perfFrame.configure(bg='#F2F2F2')
    perfFrame.geometry("200x150")

    btn = ttk.Button(master=perfFrame, text='box', command = lambda : click(perfFrame), width=10)
    btn.pack()
    perfFrame.protocol('WM_DELETE_WINDOW', quit) 
    perfFrame.mainloop()


screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

def main():

    # plot labels
    plot_title = "Realtime MOKE Signal vs I Plot"
    x_lbl = "Applied Current (mA)"
    y_lbl = "Realtime MOKE Signal (R+B+G)"

    # dictionaries of GUI contents
    # default initial values
    mag_dict = {'Hz Field (Oe)': 0,
                'Hz Step (Oe)': 0,
                'Hx Field (Oe)': 0,
                'Hx Step (Oe)': 0,
                'Output Time (s)': 1
                }

    keith_dict = {'Current (mA)': 1.9,
                'Current Step (mA)': 0,
                'Write Pulse Width (s)': 0.05, 
                'Write Pulse Step (s)': 0,
                'Read Pulse Width (s)': 0.05, # delay between write and read
                'Delay (s)': 0.5 # delay between loops
                }

    # default values required for initializing lockin via Pyvisa
    lockin_dict = {'Mode': '1st', # Set a default mode (1st or 2nd)
                'Sensitivity': '10mV', # Set a default sensitivity range (mV or uV)
                'Signal Voltage': 1, # Set a default OSC signal voltage (V)
                'Frequency': 1171 # Set a default OSC frequency (Hz)
                }

    # values set by various functions, define measurement settings
    control_dict = {'Field Step': 'Step', # set with make_extras()
                    'I_app Step': 'Step', # set with make_extras()
                    'H Scan Direction': 'Hx', # set with make_extras()
                    'H Output Direction': 'Hz', # set with make_buttons()
                    'Hz DAC Channel': 2, # displayed in make_extras()
                    'Hx DAC Channel': 3, # displayed in make_extras()
                    'Hz/DAC (Oe/V)': 1022, # displayed in make_extras()
                    'Hx/DAC (Oe/V)': 396.59, # displayed in make_extras()
                    'Hz DAC Limit': 1, # Voltage limit of Z direction mag
                    'Hx DAC Limit': 12, # Voltage limit of X direction mag
                    'Display': '', # set with make_info()
                    'File Name': 'Sample Name', # set with make_extras(), used in save function
                    'Directory': ''# set with set_directory(), updated with change_directory()
                    }


    # frames for various widgets
    content = Frame(root)
    plt_frame = Frame(content, borderwidth=10, relief="sunken")
    settings_frame = Frame(content, borderwidth=5)
    information_frame = Frame(content, borderwidth=5)
    buttons_frame = Frame(content, borderwidth=5)
    rows =20

    # grid of above frames
    content.grid(column=0, row=0, sticky='nsew')
    plt_frame.grid(column=0, row=0, columnspan=3, rowspan=rows, sticky='nsew')
    settings_frame.grid(column=3, row=0, columnspan=2, rowspan=rows, sticky='nsew')
    information_frame.grid(column=0, row=rows, columnspan=3, sticky='nsew')
    buttons_frame.grid(column=3, row=rows, columnspan=2, sticky='nsew')

    control_dict['Display'] = make_info(information_frame)
    mag_dict = make_form(settings_frame, mag_dict, 'Magnetic Settings')
    keith_dict = make_form(settings_frame, keith_dict, 'Current Settings')
    make_extras(settings_frame, mag_dict, keith_dict, control_dict)
    make_plot(plt_frame, plot_title, x_lbl, y_lbl)
    make_buttons(buttons_frame, mag_dict, keith_dict, control_dict, plot_title, x_lbl, y_lbl, lockin_dict)

    #weights columns for all multiple weight=1 columns
    weight(buttons_frame)
    weight(information_frame)
    weight(settings_frame)

    # weights for all rows and columns with weight!=1
    content.columnconfigure(0, weight=3)
    content.columnconfigure(1, weight=3)
    content.columnconfigure(2, weight=3)
    content.columnconfigure(3, weight=1)
    content.columnconfigure(4, weight=1)
    content.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    plt_frame.columnconfigure(0, weight=1)
    plt_frame.rowconfigure(0, weight=1)   
    information_frame.columnconfigure(3, weight=0) # necessary to keep the scroll bar tiny
    information_frame.rowconfigure(0, weight=1)    
    buttons_frame.rowconfigure(0, weight=1)
    #--------end of GUI settings-----------#

    # sets current directory to default (~/Documents/Measurements)
    control_dict['Directory'] = set_directory(control_dict['Display'])

    ani = animation.FuncAnimation(fig, animate, interval=200, fargs=[plot_title, x_lbl, y_lbl])
    th2 = threading.Thread(target=perfSettings)
    th2.daemon = True
    th2.start()

    root.protocol('WM_DELETE_WINDOW', quit) 
    root.mainloop()
#----------------------------------------END OF MAIN-------------------------------------------#


# animation to plot data
def animate(i, title, x, y):
    global current_output, measured_values, fix_lbl, pulse_lbl

    ax.clear()
    ax.grid(True)
    ax.set_title(title+"\n Measuring with Hx: %.2f (Oe) and %.2f (s) pulse width" % (fix_lbl[0], pulse_lbl[0]))
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.plot(current_output[0:len(measured_values)], measured_values,'b-o', ms=10, mew=0.5)


# takes a given frame and gives all columns a weight of 1
def weight(frame):

    for x in range(frame.grid_size()[0]):
        frame.columnconfigure(x, weight=1)


# takes a dictionary and makes labels and entry widgets for key/value pairs
# returns updated dictionary with entry values
def make_form(root, dictionary, frametxt):

    lf = LabelFrame(root, text=frametxt)
    lf.grid(ipadx=2, ipady=2, sticky='nsew')
    for counter, x in enumerate(dictionary.items()):
        lab = Label(lf, width=20, text=x[0], anchor='w')
        ent = Entry(lf, width=20); ent.insert(0, str(x[1]))
        lab.grid(row=counter, column=0, sticky='nsew')
        ent.grid(row=counter, column=1, sticky='nsew')
        dictionary[x[0]] = ent # set dictionary value to entry widget

    return dictionary


# initializes and grids matplotlib plot 
def make_plot(root, title, x_label, y_label):

    global dataplot

    # canvas for matplotlib gui
    dataplot = FigureCanvasTkAgg(fig, root)
    dataplot.draw()
    dataplot.get_tk_widget().grid(row=0, column=0, pady=0, padx=0, sticky='nsew')


# creates and grids the listbox and scroll bar
def make_info(root):

    listbox = Listbox(root, height=5)
    y_scroll = Scrollbar(root, orient=VERTICAL, command=listbox.yview)
    listbox['yscrollcommand'] = y_scroll.set
    listbox.grid(column=0, row=0, columnspan=3, sticky='nsew')
    y_scroll.grid(column=3, row=0, sticky='ns')

    return listbox


# extra radio buttons and selectors
def make_extras(root, mag_dict, keith_dict, control_dict):

    lf = LabelFrame(root, text='Measurement Options')
    lf.grid(ipadx=2, ipady=2, sticky='nsew')

    # radiobutton to determine scanning field vs. set field
    control_dict['H Scan Direction'] = StringVar(); control_dict['H Scan Direction'].set('Hx')
    Hz = Radiobutton(lf, text="Scan Hz", variable=control_dict['H Scan Direction'], value='Hz', width=12, anchor='w', \
        command = lambda: Hscan_select(control_dict['H Scan Direction'].get(), control_dict['Display']))
    Hx = Radiobutton(lf, text="Scan Hx", variable=control_dict['H Scan Direction'], value='Hx', width=12, anchor='w', \
        command = lambda: Hscan_select(control_dict['H Scan Direction'].get(), control_dict['Display']))

    # radiobutton to determine loop via step or user defined values
    control_dict['Field Step'] = StringVar(); control_dict['Field Step'].set('Step')
    control_dict['I_app Step'] = StringVar(); control_dict['I_app Step'].set('Step')
    fstep = Radiobutton(lf, text="Field Step Loop", variable=control_dict['Field Step'], value='Step', width=12, anchor='w', \
        command = lambda: field_input(control_dict['Field Step'].get(), mag_dict, control_dict['Display']))
    fuser = Radiobutton(lf, text="Field User Input", variable=control_dict['Field Step'], value='User', width=12, anchor='w', \
        command = lambda: field_input(control_dict['Field Step'].get(), mag_dict, control_dict['Display']))
    cstep = Radiobutton(lf, text="Iapp Step Loop", variable=control_dict['I_app Step'], value='Step', width=12, anchor='w', \
        command = lambda: I_app_input(control_dict['I_app Step'].get(), keith_dict, control_dict['Display']))
    cuser = Radiobutton(lf, text="Iapp User Input", variable=control_dict['I_app Step'], value='User', width=12, anchor='w', \
        command = lambda: I_app_input(control_dict['I_app Step'].get(), keith_dict, control_dict['Display']))       

    Hz_lbl = Label(lf, width=20, text=('Hz DAC: %s' % control_dict['Hz DAC Channel']), anchor='w')
    Hx_lbl = Label(lf, width=20, text=('Hx DAC: %s' % control_dict['Hx DAC Channel']), anchor='w')
    Hz_conv_lbl = Label(lf, width=20, text=('Hz DAC: %s' % control_dict['Hz/DAC (Oe/V)']), anchor='w')
    Hx_conv_lbl = Label(lf, width=20, text=('Hx DAC: %s' % control_dict['Hx/DAC (Oe/V)']), anchor='w')
    
    # grid created buttons 
    Hz.grid(row=0, column=0, sticky='nsew')
    Hx.grid(row=0, column=1, sticky='nsew')
    fstep.grid(row=1, column=0, sticky='nsew')
    fuser.grid(row=1, column=1, sticky='nsew')
    cstep.grid(row=2, column=0, sticky='nsew')
    cuser.grid(row=2, column=1, sticky='nsew')
    # labels for DAC channels and conversion values, now only editable back end.
    Hz_lbl.grid(row=3, column=0, sticky='nsew')    
    Hz_conv_lbl.grid(row=3, column=1, sticky='nsew')
    Hx_lbl.grid(row=4, column=0, sticky='nsew')
    Hx_conv_lbl.grid(row=4, column=1, sticky='nsew')
    # file name label and entry
    file_lab = Label(lf, width=20, text='File Name', anchor='w')
    file_ent = Entry(lf, width=20); file_ent.insert(0, control_dict['File Name'])
    file_lab.grid(row=5, column=0, sticky='nsew')
    file_ent.grid(row=5, column=1, sticky='nsew')
    control_dict['File Name'] = file_ent


# creates and grids buttons
def make_buttons(root, mag_dict, keith_dict, control_dict, plot_title, x_lbl, y_lbl, lockin_dict):

    control_dict['H Output Direction'] = StringVar(); control_dict['H Output Direction'].set('Hz')

    # button list
    measure_button = Button(root, text='Measure', \
        command=lambda:measure_method(mag_dict, keith_dict, control_dict, lockin_dict))
    dir_button = Button(root, text='Change Directory', \
        command=lambda:change_directory(control_dict, control_dict['Display']))
    quit_button = Button(root, text='Quit', \
        command=lambda:quit_method(control_dict['Display'], lockin_dict))
    clear_button = Button(root, text='Clear', \
        command=lambda:clear_method(plot_title, x_lbl, y_lbl, control_dict['Display']))
    output_button = Button(root, text='Output', \
        command=lambda:output_method(control_dict, mag_dict, lockin_dict))
    z_select = Radiobutton(root, text='Hz', variable=control_dict['H Output Direction'], value='Hz', \
        command= lambda: output_direction(control_dict['H Output Direction'].get(), control_dict['Display']))
    x_select = Radiobutton(root, text='Hx', variable=control_dict['H Output Direction'], value='Hx', \
        command= lambda: output_direction(control_dict['H Output Direction'].get(), control_dict['Display']))

    # grid buttons
    output_button.grid(row=0, column=0, columnspan=1, sticky='nsew')
    x_select.grid(row=0, column=1, sticky='e')
    z_select.grid(row=0, column=1, sticky='w')
    measure_button.grid(row=1, column =0, columnspan=2, sticky='nsew')
    clear_button.grid(row = 3, column = 0, columnspan=1, sticky='nsew')
    dir_button.grid(row=2, column=0, columnspan=2, sticky='nsew')
    quit_button.grid(row=3, column=1, columnspan=1, sticky='nsew')


# does the matplotlib gui stuff to clear plot area
def plot_set(title, x_label, y_label):

    ax.clear()
    ax.grid(True)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.axis([-1, 1, -1, 1]) 


# command to change H scan direction
def Hscan_select(var, display):

    display.insert('end', 'Scan in the %s direction.' % var)
    display.see(END)


# command to change applied field loop/user input
def field_input(var, mag_dict, display):

    if var == 'User':
        mag_dict['Hx Field (Oe)'].delete(0, len(mag_dict['Hx Field (Oe)'].get())) # clear entry
        mag_dict['Hx Field (Oe)'].insert(0, '-1, 0, -1'); mag_dict['Hx Field (Oe)'].update() # list entry
        mag_dict['Hz Field (Oe)'].delete(0, len(mag_dict['Hz Field (Oe)'].get())) # clear entry
        mag_dict['Hz Field (Oe)'].insert(0, '-1, 0, -1'); mag_dict['Hz Field (Oe)'].update() # list entry
        mag_dict['Hx Step (Oe)'].config(state=DISABLED); mag_dict['Hx Step (Oe)'].update() # disable step function
        mag_dict['Hz Step (Oe)'].config(state=DISABLED); mag_dict['Hz Step (Oe)'].update() # disable step function
    else:
        mag_dict['Hx Field (Oe)'].delete(0, len(mag_dict['Hx Field (Oe)'].get())) # clear entry
        mag_dict['Hx Field (Oe)'].insert(0, '0'); mag_dict['Hx Field (Oe)'].update() # step entry
        mag_dict['Hz Field (Oe)'].delete(0, len(mag_dict['Hz Field (Oe)'].get())) # clear entry
        mag_dict['Hz Field (Oe)'].insert(0, '0'); mag_dict['Hz Field (Oe)'].update() # step entry
        mag_dict['Hx Step (Oe)'].config(state=NORMAL); mag_dict['Hx Step (Oe)'].update() # enable step function
        mag_dict['Hz Step (Oe)'].config(state=NORMAL); mag_dict['Hz Step (Oe)'].update() # enable step function    

    display.insert('end', '%s loop type selected for applied fields.' % var)
    display.see(END)


# command to change applied field loop/user input
def I_app_input(var, keith_dict, display):

    if var == 'User':
        keith_dict['Current (mA)'].delete(0, len(keith_dict['Current (mA)'].get())) # clear entry
        keith_dict['Current (mA)'].insert(0, '-1, 0, -1'); keith_dict['Current (mA)'].update() # list entry
        keith_dict['Current Step (mA)'].config(state=DISABLED); keith_dict['Current Step (mA)'].update() # disable step function
        keith_dict['Write Pulse Width (s)'].delete(0, len(keith_dict['Write Pulse Width (s)'].get())) # clear entry
        keith_dict['Write Pulse Width (s)'].insert(0, '-1, 0, -1'); keith_dict['Write Pulse Width (s)'].update() # list entry
        keith_dict['Write Pulse Step (s)'].config(state=DISABLED); keith_dict['Write Pulse Step (s)'].update() # disable step function
    else:
        keith_dict['Current (mA)'].delete(0, len(keith_dict['Current (mA)'].get())) # clear entry
        keith_dict['Current (mA)'].insert(0, '0'); keith_dict['Current (mA)'].update() # step entry
        keith_dict['Current Step (mA)'].config(state=NORMAL); keith_dict['Current Step (mA)'].update() # enable step function  
        keith_dict['Write Pulse Width (s)'].delete(0, len(keith_dict['Write Pulse Width (s)'].get())) # clear entry
        keith_dict['Write Pulse Width (s)'].insert(0, '0'); keith_dict['Write Pulse Width (s)'].update() # step entry
        keith_dict['Write Pulse Step (s)'].config(state=NORMAL); keith_dict['Write Pulse Step (s)'].update() # enable step function  

    display.insert('end', '%s loop type selected for applied currents.' % var)
    display.see(END)


# sets default save directory, returns directory path
def set_directory(display):

    test = os.path.expanduser('~/Documents')

    if os.path.isdir(test + '/Measurements'):
        os.chdir(test + '/Measurements')
    else:
        os.mkdir(test + '/Measurements')
        os.chdir(test + '/Measurements')

    cur_dir = os.getcwd()

    display.insert('end', 'The current directory is set to: %s' % cur_dir)
    display.see(END)

    return cur_dir


# changes the save directory
def change_directory(control_dict, display):

    control_dict['Directory'] = filedialog.askdirectory()
    display.insert('end', control_dict['Directory'])
    display.see(END)
    

# displays the current output direction selected
def output_direction(var, display):

    display.insert('end', 'Output direction set to the %s direction.' % var)
    display.see(END)


# applies a field H in the given direction at a given strength
# applies a field H in the given direction at a given strength
def output_method(control_dict, mag_dict, lockin_dict):
    display = control_dict['Display']
    amp = lockinAmp(lockin_dict['Mode'], lockin_dict['Sensitivity'], lockin_dict['Signal Voltage'], lockin_dict['Frequency'])
    d = control_dict['H Output Direction'].get() # direction output variable
    t = mag_dict['Output Time (s)'].get() # output time
    output = mag_dict['%s Field (Oe)' % d].get() # output value
    interval = control_dict['%s/DAC (Oe/V)' % d] # conversion integral

    # confirms output is number
    if output.lstrip('-').replace('.','',1).isdigit():
        # if output below threshold value, then have lockin amp output for t seconds
        if float(output) / float(interval) < float(control_dict['%s DAC Limit' % d]):
            amp.dacOutput((float(output) / float(interval)), control_dict['%s DAC Channel' % d])
            time.sleep(float(t))
            amp.dacOutput(0, control_dict['%s DAC Channel' % d])
            display.insert('end', '%s output for %s second(s)' % (d, t))
            display.see(END)
        else:
            messagebox.showwarning('Output Too Large', 'Output value beyond amp voltage threshold')
            display.insert('end', 'Output value too large!')
            display.see(END)
    else:
        messagebox.showwarning('Invalid Entry', 'Output or conversion factor not recognized as a number.')


# clears and redraws the matplotlib gui
def clear_method(title, x_label, y_label, display):

    plot_set(title, x_label, y_label)
    dataplot.show()
    display.delete(0, END)
    print("clear all")


# turns off all outputs and then quits the program
def quit_method(display, lockin_dict):

    global root

    q = messagebox.askquestion('Quit', 'Are you sure you want to quit?')

    if q == 'yes':
        amp = lockinAmp(lockin_dict['Mode'], lockin_dict['Sensitivity'], lockin_dict['Signal Voltage'], lockin_dict['Frequency'])
        amp.dacOutput(0, 1)
        amp.dacOutput(0, 2)
        amp.dacOutput(0, 3)
        amp.dacOutput(0, 4)
        keith_2400=Keithley2400('f') # Initiate K2400
        keith_2400.minimize()
        time.sleep(0.1)
        keith_2400.fourWireOff() 
        keith_2400.outputOff()
        display.insert('end', "All fields set to zero.")
        display.see(END)
        time.sleep(.1)

        root.quit()
    else:
        pass


# takes maximum value and step size and creates a list of all values (floats) to run from low to high
def make_list(max_val, step_val):
    # checks to make sure inputs are valid (numbers)
    if max_val.lstrip('-').replace('.','',1).isdigit() and step_val.lstrip('-').replace('.','',1).isdigit():
        maximum = float(max_val)
        step = float(step_val)
        new_list = []
        # if step is zero, field is only measured at that value
        if step == 0.0:
            return [maximum]
        # if maximum is a positive value, build list from neg to positive
        elif maximum > 0.0:
            maximum = -maximum
            while maximum <= float(max_val):
                new_list.append(maximum)
                maximum += step
            return new_list
        # if maximum is a negative value, build the list
        else:
            while maximum <= -float(max_val):
                new_list.append(maximum)
                maximum += step
            return new_list
    else:
        messagebox.showwarning('Invalid Entry', 'Field or step input is not a digit')
        

# converts string to list, returns list (of floats), raises error if list is not all numeric
def convert_to_list(input_list):
    
    str_list = input_list.replace(",", ' ') # input list can have , and/or spaces to seperate values
    str_list = str_list.split()
    new_list = []
    for x in str_list:
        verify = x.lstrip('-')
        if verify.replace('.','',1).isdigit() == False:
            messagebox.showerror('Error', 'Formatting error with value %s.' % str(x))
        else:
            new_list.append(float(x))
    return(new_list)


# takes file parameters and results and saves the file, should have 5 lines before data is saved
def save_method(H_dir, fix_val, pulse, x_values, y_values, display, directory, name, resistance):

    stamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    file = open(str(directory)+"/"+name+"_SOT_Switching"+str(round(fix_val, 3))+"Oe_"+str(stamp), "w")
    file.write(H_dir+" field: "+str(round(fix_val, 3))+"(Oe)\n")
    file.write(str(round(pulse,3))+" (s) pulse width \n")
    file.write("Initial Resistance: "+str(resistance)+"Ohm\n")
    file.write("\n")
    file.write("Number"+" "+"Applied Current (mA)"+" "+"MOKE Signal (A.U.)"+"\n")

    for counter, value in enumerate(y_values):
        file.write(str(counter)+" "+str(round(x_values[counter],3))+" "+str(value)+"\n")
        
    file.closed

    display.insert('end', stamp)
    display.insert('end', "The Measurement data is saved.")
    display.see(END)


# counts the pixels and returns the luminosity for captured area
def imageMethodFAST(X1,Y1,X2,Y2):

    with mss.mss() as sct:
        monitor = {'top': Y1, 'left': X1, 'width': X2-X1, 'height': Y2-Y1}
        sct_img = sct.grab(monitor)
        image = Image.frombytes('RGB', sct_img.size, sct_img.rgb)

    width=image.size[0]
    height=image.size[1]

    R=0
    G=0
    B=0

    for x in range(width):
        for y in range(height):
            R+=image.getpixel((x, y))[0]
            G+=image.getpixel((x, y))[1]
            B+=image.getpixel((x, y))[2]

    R=R/(width*height)
    G=G/(width*height)
    B=B/(width*height)

    L=R+G+B
    return L

# takes the difference between to scan values and tells how long to rest
def charging(val):
    if val >= 2500:
        return 7.0
    elif 1500 <= val < 2500:
        return 5.0
    elif 1000 <= val < 1500:
        return 3.0
    elif 500 <= val < 1000:
        return 1.0
    elif 100 <= val < 500:
        return 0.5
    elif 50 <= val < 100:
        return 0.1
    else:
        return 0.02

# measurement loop, iterates over values of a list built from parameters in dictionaries
def measure_method(mag_dict, keith_dict, control_dict, lockin_dict):
    
    display = control_dict['Display']

    # target of threading, allows for smooth running
    def measure_loop():
        global current_output, measured_values, fix_lbl, pulse_lbl

        measured_values = []
        fix_lbl[0] = 0
        pulse_lbl[0] = 0


        # set the scan and fixed applied field directions
        fix = control_dict['H Scan Direction'].get()

        # create the lists of field values, scan loop is modified to include full loop
        if control_dict['Field Step'].get() == 'Step':
            fix_field_output = make_list(mag_dict['%s Field (Oe)' % fix].get(), mag_dict['%s Step (Oe)' % fix].get())
        else:
            fix_field_output = convert_to_list(mag_dict['%s Field (Oe)' % fix].get())

        # create the list of current values
        if control_dict['I_app Step'].get() == 'Step': 
            current_output = make_list(keith_dict['Current (mA)'].get(), keith_dict['Current Step (mA)'].get())
            inverse = reversed(current_output[0:-1])
            current_output += inverse
            pulse_width = make_list(keith_dict['Write Pulse Width (s)'].get(), keith_dict['Write Pulse Step (s)'].get())
        else:
            current_output = convert_to_list(keith_dict['Current (mA)'].get())
            inverse = reversed(current_output[0:-1])
            current_output += inverse
            pulse_width = convert_to_list(keith_dict['Write Pulse Width (s)']) 

        # ensures output voltages will not exceed amp thresholds
        if max(fix_field_output) / float(control_dict['%s/DAC (Oe/V)' % fix]) < float(control_dict['%s DAC Limit' % fix]):
            
            
            # initialize machines
            amp = lockinAmp(lockin_dict['Mode'], lockin_dict['Sensitivity'], lockin_dict['Signal Voltage'], lockin_dict['Frequency'])
            keith_2400=Keithley2400('f') #Initiate K2400

            # measurement loops - for fixed field value, scan current values and measure and save
            for counter, fix_val in enumerate(fix_field_output):
                fix_lbl[0] = round(fix_val, 3)

                if counter == 0:
                    diff = abs(fix_val)
                else:
                    diff = abs(fix_val - fix_field_output[counter-1])
                amp.dacOutput((fix_val / float(control_dict['%s/DAC (Oe/V)' % fix])), control_dict['%s DAC Channel' % fix])
                time.sleep(charging(diff))

                for pulse in pulse_width:
                    pulse_lbl[0] = round(pulse, 3)

                    # setup K2400 here
                    keith_2400.fourWireOff()
                    keith_2400.setCurrent(float(keith_dict['Sensing Current (mA)'].get()))
                    keith_2400.outputOn()
                    # take initial resistance measurement?
                    index=1
                    data=[]

                    while index<=5: #Average of five measurements
                        data=data+keith_2400.measureOnce()
                        index+=1
                    resistance = round(data[1]/data[2], 3)                
                    display.insert('end',"Measured current: %f mA" %(1000*data[2]))
                    display.insert('end',"Measured voltage: %f V" %data[1])
                    display.insert('end',"Measured resistance: %f Ohm" %(resistance))
                    display.see(END)

                    # intializes the measurement data list
                    measured_values = []

                    display.insert('end', 'Measurement with %s (s) write pulse width' % str(pulse))
                    display.see(END)

                    for current_val in current_output:

                        keith_2400.setCurrent(round(current_val,4))
                        time.sleep(pulse)
                        keith_2400.setCurrent(0)
                        time.sleep(float(keith_dict['Read Pulse Width (s)'].get()))
                        tmp = imageMethodFAST(x1, y1, x2, y2) # get image luminosity
                        measured_values.append(tmp)
                        display.insert('end', 'Applied Pulse Strength: %s (mA)      MOKE Signal: %s (A.U.)' %(round(current_val,4), tmp))
                        display.see(END)

                    # save data
                    save_method(control_dict['H Scan Direction'].get(), fix_val, pulse, \
                        current_output, measured_values, display, control_dict['Directory'], control_dict['File Name'].get(), resistance)
                    time.sleep(float(keith_dict['Delay (s)'].get()))

            # turn everything off at end of loop
            amp.dacOutput(0, control_dict['%s DAC Channel'% fix])
            keith_2400.minimize()
            time.sleep(0.1)

            display.insert('end',"Measurement finished")
            display.see(END)

        else:
            messagebox.showwarning('Output Too Large', 'Output value beyond amp voltage threshold')
            display.insert('end', 'Output value too large!')
            display.see(END)

        #----------------------------END measure_loop----------------------------------#

    # Only one measurement thread allowed. This is a cheap and easy workaround so we don't have to stop threads
    if threading.active_count() == 2:
        # thread is set to Daemon so if mainthread is quit, it dies
        t = threading.Thread(target=measure_loop, name='measure_thread', daemon=True)
        t.start()
    else:
        messagebox.showerror('Error', 'Multiple threads detected!')


if __name__ == '__main__':
    main()