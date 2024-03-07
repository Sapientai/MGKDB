# -*- coding: utf-8 -*-
"""
Created on Tue Aug 25 22:22:06 2020

@author: dykua

Containing some classes/functions for mgk_gui
"""

from tkinter import *
from tkinter import filedialog
from mgk_file_handling import get_suffixes
import os
#import threading

class InputForm():
    '''
    A pop up window to get par_file, confidence, comments, suffixes
    '''
    def __init__ (self, out_dir):
#        self.master = master
        self.out_dir = out_dir
        self.master = Toplevel()
        self.data = {}
        
#        threading.Thread.__init__(self)
#        self.start()
        
        '''
        TopText
        '''
#        topTextFrame = Frame(self.master)
#        topTextFrame.pack(fill=X)
        
        topText = Text(self.master, height=3)
#        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Need your input for \n {} \n to prepare uploading.".format(self.out_dir) )
        
#        '''
#        A sample parameter file, assuming the rest shares some same settings as "magn_geometry" and 'mom'
#        '''
##        parFrame = Frame(self.master)
##        parFrame.pack(fill=X) 
#        
#        parLabel = Label(self.master, text="Sample parameter file: ")
##        parLabel.pack(side=LEFT, padx = 5, pady=5)
#        
#        self.par_file = StringVar()
#        parEntry = Entry(self.master, textvariable=self.par_file, width=100)
##        parEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
##        parEntry.focus_set()
#        
#                
#        def browse_file():
#            fname = filedialog.askopenfilename()
#            parEntry.insert(0, fname)
#        
#        parButton = Button(self.master, text="BROWSE", command = browse_file)
#        parButton.pack(side=RIGHT, padx=5, pady=5)
        '''
        shared_files
        '''
        sharedLabel= Label(self.master, text="Any other files shared by runs to upload?")
        self.shared = StringVar()
        sharedEntry = Entry(self.master, textvariable=self.shared, width=60)
        
        '''
        confidence
        '''
#        confiFrame = Frame(self.master)
#        confiFrame.pack(fill=X)

        confiLabel = Label(self.master, text="Confidence: (1-10)")
#        confiLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.confidence = IntVar()
        confiEntry = Entry(self.master, textvariable=self.confidence, width=5)
#        confiEntry.pack(fill=X, padx=5, expand=True)
#        confiEntry.focus_set()
        confiEntry.insert(0, '-1')
        
        '''
        Comments
        ''' 
#        commentFrame = Frame(self.master)
#        commentFrame.pack(fill = X)
        
        commentLabel = Label(self.master, text="Comments: ")
#        commentLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.comments = StringVar()
        commentEntry = Entry(self.master, textvariable=self.comments, width=60)
#        comment_entry.pack(fill=X, padx=5, expand=True)

#        comment_entry.focus_set()
        commentEntry.insert(0, '')
        
        '''
        grid arrangement
        '''
        topText.grid(row=0, column=1, columnspan=4)
        
#        parLabel.grid(row=1)
#        parEntry.grid(row=1, column=1, columnspan=8, sticky = W)
#        parButton.grid(row =1, column = 5)
        sharedLabel.grid(row=1)
        sharedEntry.grid(row=1, column=1,sticky=W)
        
        confiLabel.grid(row=2)
        confiEntry.grid(row=2, column=1,sticky=W)
        
        commentLabel.grid(row=2 ,column=2)
        commentEntry.grid(row=2, column=3, columnspan=8, sticky=W)
        
        '''
        suffixes
        '''
        suffixes = get_suffixes(self.out_dir)
#        suffixes = suffixes.sort()
        
#        suffixFrame = Frame(self.master)
#        suffixFrame.pack(fill=X)
#
        suffixLabel = Label(self.master, text="Suffixes: ").grid(row=3)
#        suffixLabel.pack(side=LEFT, padx = 5, pady=5)
               
        self.suffixvals = {}
        self.suffixbox = {}
        for i, name in enumerate(suffixes):
            self.suffixvals[name] = BooleanVar()
            self.suffixbox[name] = Checkbutton(self.master, 
                                               text=name, 
                                               variable=self.suffixvals[name],
                                               onvalue=True, offvalue=False).grid(row=4+i//5, column=i%5) 
#            self.suffixbox[name].pack(side='bottom',padx = 5, pady=5)
                   
        
            
        self.checkALL = BooleanVar()
#        def check_all():
#            if self.checkALL.get() is True:
#                for name in suffixes:
#                    self.suffixbox[name].config(state=DISABLED)
#            else:
#                for name in suffixes:
#                    self.suffixbox[name].config(state=NORMAL)
        
        self.checkAllBox = Checkbutton(self.master, 
                                       text='Select All', 
                                       variable=self.checkALL, 
#                                       command = check_all,
                                       onvalue=True, offvalue=False).grid(row=4+i//5, column=i%5+1)
        
        
        def confirm():
#            self.data['par_file'] = self.par_file.get()
            self.data['confidence'] = self.confidence.get()
            self.data['comments'] = commentEntry.get()
            
            if self.shared.get():
                self.data['shared'] = self.shared.get().split(',')
            else:
                self.data['shared'] = None
                
            if self.checkALL.get():
                self.data['suffixes'] = suffixes
            else:
                self.data['suffixes'] = []
                for name in suffixes:
                    if self.suffixvals[name].get():
                        self.data['suffixes'].append(name)
            
#            pop_win = Tk()            
#            tspan = get_tspan_gui(pop_win).data
#            self.data['tspan'] = tspan
            
            self.master.destroy()
        
        self.data['skip_flag']=False
        def skip():
            print("Skipping {}".format(out_dir))
            self.data['skip_flag'] = True
            self.master.destroy()
        

        butt = Button(self.master, text = "CONFIRM", command = confirm).grid(row=5 + len(suffixes)//5, column=7)
        sButt = Button(self.master, text = 'Skip', command = skip).grid(row=5 + len(suffixes)//5, column=8)
#        self.master.mainloop()
        self.master.wait_window()


class make_par_choice():
    def __init__(self, out_dir, suffix, par_list):
        '''
        TopText
        '''
        self.master = Toplevel()
        
        topText = Text(self.master, height=3)
        topText.insert(END, "There seems to be multiple files detected starting with parameters{}:\n in {} \n".format(suffix, out_dir) ) 
        topText.grid(row=0, column=1, columnspan = 7)
        '''
        Confused parameter files
        '''
        suffixLabel = Label(self.master, text="Choose the parameter file: ").grid(row=1, column=1)
        
        candidates = []
        choices = []
        selection = IntVar()
        for i, par in enumerate(par_list):
            candidates.append(par.split('/')[-1])
            choices.append(Radiobutton(self.master, text=candidates[-1], variable=selection,
                                   indicatoron=False, value= i, width=30).grid(row=2+i//5, column=i%5+1) )
#        print(candidates)
            
        def confirm():
#            self.par_file = os.path.join(out_dir, par_list[selection.get()])
            self.par_file = par_list[selection.get()]

            self.master.destroy()
            

        
        butt = Button(self.master, text = "CONFIRM", command = confirm).grid(row=5, column=4) 
        
        
        self.master.wait_window()
        
        



# getting tspan from gui
class get_tspan_gui():
    
    def __init__(self):
        
#        self.master = Toplevel(master)
#        self.master = master
        self.master = Toplevel()
        
        '''
        TopText
        '''
        
        topText = Text(self.master, height=1, width=60, padx = 2)
        topText.insert(END, "Enter time span for calculating diagnostics.")
        
        
        self.data = {}
        
        startLabel = Label(self.master, text="Start time: ")
        endLabel = Label(self.master, text='End time:')
        
        t_start = StringVar()
        startEntry = Entry(self.master, textvariable=t_start, width=5)
        
        t_end = StringVar()
        endEntry = Entry(self.master, textvariable=t_end, width=5)
        
        opvals = BooleanVar()
        opbox = Checkbutton(self.master, text= 'Use NRG time span for the rest', 
                            variable=opvals, onvalue=True, offvalue=False)
        
        tspan_option= IntVar()
        def update_check():
        
            if tspan_option.get() == int(1):
               startEntry.config(state=DISABLED)
               endEntry.config(state=DISABLED)
               opbox.config(state=NORMAL)
                
            elif tspan_option.get() == int(0):
               startEntry.config(state=NORMAL)
               endEntry.config(state=NORMAL)
               opbox.config(state=DISABLED)
            
            else:
                exit("Invalide value encountered!")
                
        
        upt_Button_0 = Radiobutton(self.master, text="Manually", variable=tspan_option,
                                   indicatoron=False, value= int(0), width=8, command = update_check)
        upt_Button_1 = Radiobutton(self.master, text="From NRG File", variable=tspan_option,
                                   indicatoron=False, value= int(1), width=12, command = update_check)
        
        
        #optionLabel = Label(self.master, text="").grid(row=3)

        
        
        '''
        Arrangements
        '''
        topText.grid(row=0, column=1, columnspan=3)
        upt_Button_0.grid(row=1, column=1)
        upt_Button_1.grid(row=1, column=2)
        
        startLabel.grid(row=2, column=0)
        startEntry.grid(row=2, column=1)
        endLabel.grid(row=2, column=2)
        endEntry.grid(row=2, column=3)
        opbox.grid(row = 3)
        
        def confirm():
            self.data['all_nrg_flag'] = opvals.get()
            if tspan_option.get() == 0 and self.data['all_nrg_flag'] is False:
                self.data['tspan'] = [float(startEntry.get() ), float(endEntry.get() )]
                
            else:
                self.data['tspan'] = None
            

            self.master.destroy()

        butt = Button(self.master, text = "CONFIRM", command = confirm).grid(row=5, column=4)       
        
#        self.master.mainloop()
        self.master.wait_window()
        


#if __name__ == '__main__':
#    abc = InputForm(r"D:\test_data\data_linear_multi").data
#    print("returned value is:", abc)
#    
#    tspan = get_tspan_gui().data
#    print(tspan)
