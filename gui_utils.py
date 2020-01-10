
'''
A gui for mgk_uploader

Author: Gerardo Salazar, Dongyang Kuang
'''

from tkinter import *
from tkinter import filedialog
from pymongo import MongoClient
from mgk_file_handling_gui import *
import os
import sys
from tkinter.scrolledtext import ScrolledText

class StdRedirector(object):
    '''
    redirecting standard output to gui
    '''
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.config(state=NORMAL)
        self.text_space.insert("end", string)
        self.text_space.see("end")
        self.text_space.config(state=DISABLED)
        
        
class Window(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
#        self.master = Tk()
#        self.master.geometry('960x720')
#        self.master = master
        self.state = {}
        self.init_window()    
    
    def init_window(self):
        self.master.title("MGKDB--main")
        self.pack(fill=BOTH, expand=1)

        topTextFrame = Frame(self)
        topTextFrame.pack(fill=X)
        
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Welcome to MGK-GUI. Please fill in the info below to proceed.")
        
        
        '''
        Use saved files to login
        '''
        
        '''
        host
        '''
        hostFrame = Frame(self)
        hostFrame.pack(fill=X)

        hostLabel = Label(hostFrame, text="host: ", width=10)
        hostLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.host = StringVar()
        hostEntry = Entry(hostFrame, textvariable=self.host)
        hostEntry.pack(fill=X, padx=5, expand=True)
        hostEntry.focus_set()
        
        hostEntry.insert(0, 'mongodb03.nersc.gov') # set default value
        
        '''
        port
        '''
        portFrame = Frame(self)
        portFrame.pack(fill=X)

        portLabel = Label(portFrame, text="port: ", width=10)
        portLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.port = StringVar()
        portEntry = Entry(portFrame, textvariable=self.port)
        portEntry.pack(fill=X, padx=5, expand=True)
        portEntry.focus_set()
        
        portEntry.insert(0, '27017')
        
        
        '''
        database name
        '''
        dbnameFrame = Frame(self)
        dbnameFrame.pack(fill=X)

        dbnameLabel = Label(dbnameFrame, text="database: ", width=10)
        dbnameLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.dbname = StringVar()
        dbnameEntry = Entry(dbnameFrame, textvariable=self.dbname)
        dbnameEntry.pack(fill=X, padx=5, expand=True)
        dbnameEntry.focus_set()
        
        dbnameEntry.insert(0, 'mgk_fusion')

        '''
        username
        '''
        usernameFrame = Frame(self)
        usernameFrame.pack(fill=X)

        usernameLabel = Label(usernameFrame, text="Username: ", width=10)
        usernameLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.username = StringVar()
        usernameEntry = Entry(usernameFrame, textvariable=self.username)
        usernameEntry.pack(fill=X, padx=5, expand=True)
        usernameEntry.focus_set()
        
        
        '''
        password
        '''
        passwordFrame = Frame(self)
        passwordFrame.pack(fill=X)

        passwordLabel = Label(passwordFrame, text="Password: ", width=10)
        passwordLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.password = StringVar()
        passwordEntry = Entry(passwordFrame, show="*", textvariable=self.password)
        passwordEntry.pack(fill=X, padx=5, expand=True)
        passwordEntry.focus_set()
        
        '''
        GENE output folder
        '''
        dirFrame = Frame(self)
        dirFrame.pack(fill=X)

        dirLabel = Label(dirFrame, text="Target Directory: ", width=15)
        dirLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.out_dir = StringVar()
        dirEntry = Entry(dirFrame, textvariable=self.out_dir)
        dirEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        dirEntry.focus_set()
        
        def browse():
            dirname = filedialog.askdirectory()
            dirEntry.insert(0, dirname)
        
        BrButton = Button(dirFrame, text="BROWSE", command = browse)
        BrButton.pack(side=RIGHT, padx=5, pady=5)
#        self.master.bind("<Return>", self.upload) 
        
        
        '''
        keywords
        '''
        keywordsFrame = Frame(self)
        keywordsFrame.pack(fill=X)

        keywordsLabel = Label(keywordsFrame, text="keywords: ", width=10)
        keywordsLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.keywords = StringVar()
        keywordsEntry = Entry(keywordsFrame, textvariable=self.keywords)
        keywordsEntry.pack(fill=X, padx=5, expand=True)
        keywordsEntry.focus_set()

        keywordsEntry.insert(0, 'GENE')
        
        '''
        A sample parameter file, assuming the rest shares some same settings as "magn_geometry" and 'mom'
        '''
        parFrame = Frame(self)
        parFrame.pack(fill=X) 
        
        parLabel = Label(parFrame, text="Sample parameter file: ", width=20)
        parLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.par_file = StringVar()
        parEntry = Entry(parFrame, textvariable=self.par_file)
        parEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        parEntry.focus_set()
        
        parButton = Button(parFrame, text="BROWSE", command = browse)
        parButton.pack(side=RIGHT, padx=5, pady=5)        
        
        
        '''
        confidence
        '''
        confiFrame = Frame(self)
        confiFrame.pack(fill=X)

        confiLabel = Label(confiFrame, text="Confidence: (1-10)", width=15)
        confiLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.confidence = StringVar()
        confiEntry = Entry(confiFrame, textvariable=self.confidence)
        confiEntry.pack(fill=X, padx=5, expand=True)
        confiEntry.focus_set()
        
        '''
        input heat
        '''
        heatFrame = Frame(self)
        heatFrame.pack(fill=X)

        heatLabel = Label(heatFrame, text="Input Heat: ", width=10)
        heatLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.input_heat = StringVar()
        heatEntry = Entry(heatFrame, textvariable=self.input_heat)
        heatEntry.pack(fill=X, padx=5, expand=True)
        heatEntry.focus_set()
        heatEntry.insert(0, 'None')
        
        
        '''
        multirun option
        '''
        multirunsFrame = Frame(self)
        multirunsFrame.pack(fill=X)
        self.multiruns = BooleanVar()
        multirunsCheckbox = Checkbutton(multirunsFrame, text="Multiple Runs", 
                                        variable=self.multiruns, onvalue=True, offvalue=False)
        multirunsCheckbox.pack()
        
        '''
        large file option
        '''
        largeFileFrame = Frame(self)
        largeFileFrame.pack(fill=X)
        self.largeFile = BooleanVar()
        largeFileCheckbox = Checkbutton(largeFileFrame, text="Large Files", 
                                        variable=self.largeFile, onvalue=True, offvalue=False)
        largeFileCheckbox.pack()
               
        
        '''
        extra file option
        '''
        extraFrame = Frame(self)
        extraFrame.pack(fill=X)
        self.extra = BooleanVar()
        
        # Files
        extraFileFrame = Frame(self)
        extraFileFrame.pack(fill=X)

        extraFileLabel = Label(extraFileFrame, text="Extra File Name: ", width=20)
        extraFileLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.exFiles = StringVar()
        extraFileEntry = Entry(extraFileFrame, textvariable=self.exFiles)
        extraFileEntry.pack(fill=X, padx=5, expand=True)
        extraFileEntry.focus_set()
        extraFileEntry.config(state=DISABLED)
        
        # Keys
        extraKeyFrame = Frame(self)
        extraKeyFrame.pack(fill=X)

        extraKeyLabel = Label(extraKeyFrame, text="Extra Key: ", width=10)
        extraKeyLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.exKeys = StringVar()
        extraKeyEntry = Entry(extraKeyFrame, textvariable=self.exKeys)
        extraKeyEntry.pack(fill=X, padx=5, expand=True)
        extraKeyEntry.focus_set()
        extraKeyEntry.config(state=DISABLED)
        
        def extra_check():
        
            if self.extra.get():
                extraKeyEntry.config(state=NORMAL)
                extraFileEntry.config(state=NORMAL)
            else:
                extraKeyEntry.config(state=DISABLED)
                extraFileEntry.config(state=DISABLED)
                
                
        extraCheckbox = Checkbutton(extraFrame, text="Extra Files", 
                                    variable=self.extra, onvalue=True, offvalue=False,
                                    command = extra_check)
        extraCheckbox.pack()
                
        
        
        '''
        verbose option
        '''
        verboseFrame = Frame(self)
        verboseFrame.pack(fill=X)
        self.verbose= BooleanVar()
        verboseCheckbox = Checkbutton(verboseFrame, text="verbose", 
                                        variable=self.verbose, onvalue=True, offvalue=False)
        verboseCheckbox.pack()
        
        '''
        islinear option
        '''
        isLinearFrame = Frame(self)
        isLinearFrame.pack(fill=X)
        
        self.isLinear= BooleanVar()
#        isLinearCheckbox = Checkbutton(isLinearFrame, text="Linear", 
#                                        variable=self.isLinear, onvalue=True, offvalue=False)
#        isLinearCheckbox.pack()
        
#        self.isLinear = StringVar(value="Linear")
        Linear_Button = Radiobutton(isLinearFrame, text="Linear", variable=self.isLinear,
                             indicatoron=False, value= True, width=8)
        NonLinear_Button = Radiobutton(isLinearFrame, text="Nonlinear", variable=self.isLinear,
                             indicatoron=False, value= False, width=8)
        Linear_Button.pack(side='left')
        NonLinear_Button.pack(side='left')
        

        
        '''
        utils
        '''
        utilsFrame = Frame(self)
        utilsFrame.pack(fill=X)
        
        closeButton = Button(utilsFrame, text="Close", command = self.quit)
        closeButton.pack(side=RIGHT, padx=5, pady=5) 
        
        uploadButton = Button(utilsFrame, text="Upload", command=self.upload)
#        self.master.bind("<Return>", self.upload)
        uploadButton.pack(side=RIGHT, padx=5, pady=5)
        
        updateButton = Button(utilsFrame, text="Update", command=self.create_update_window)
        updateButton.pack(side=RIGHT, padx=5, pady=5)
        
        
        '''
        Window for console output
        '''
        outFrame = Frame(self)
        outFrame.pack(fill=X)
        
        outLabel = Label(outFrame, text="Console", width=10)
        outLabel.pack(side=TOP, padx = 5, pady=5)
        
        text_box = ScrolledText(outFrame, state='disabled')
        text_box.configure(font='TkFixedFont')
        text_box.pack(side=BOTTOM, fill=X, padx = 10, expand=True)
        
        sys.stdout = StdRedirector(text_box)
        

    def quit(self):
        self.master.destroy()  

    
    def create_update_window(self):
        t = Toplevel(self)
        t.wm_title("MGKDB -- update")
#        t.pack(fill=BOTH, expand=1)

        topTextFrame = Frame(t)
        topTextFrame.pack(fill=X)
        
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Folder exists in database. Please use the below options to proceed with updates.")
        

        '''
        update option
        '''
        updateFrame = Frame(t)
        updateFrame.pack(fill=X)
        
        self.update_option= IntVar()

        
        
        '''
        Will it change QoI?
        '''
        QoIFrame = Frame(t)
        QoIFrame.pack(fill=X)
        self.QoI_change = BooleanVar(value=True)
        QoICheckbox = Checkbutton(QoIFrame, text="Will files to update change default QoI to collect?", 
                                        variable=self.QoI_change, onvalue=True, offvalue=False)
        QoICheckbox.pack()
        
        
        '''
        update: Files relating to all runs.
        '''
        # Files
        A_FileFrame = Frame(t)
        A_FileFrame.pack(fill=X)

        A_FileLabel = Label(A_FileFrame, text="Please type FULL file names to update, separated by comma.", width=60)
        A_FileLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.A_Files = StringVar()
        A_FileEntry = Entry(A_FileFrame, textvariable=self.A_Files)
        A_FileEntry.pack(fill=X, padx=5, expand=True)
        A_FileEntry.focus_set()
        A_FileEntry.config(state=DISABLED)
        
        # Keys
        A_KeyFrame = Frame(t)
        A_KeyFrame.pack(fill=X)

        A_KeyLabel = Label(A_KeyFrame, text="Please type key names for each file you typed, separated by comma.", width=60)
        A_KeyLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.A_Keys = StringVar()
        A_KeyEntry = Entry(A_KeyFrame, textvariable=self.A_Keys)
        A_KeyEntry.pack(fill=X, padx=5, expand=True)
        A_KeyEntry.focus_set()
        A_KeyEntry.config(state=DISABLED)
        
        
        '''
        update: Just some runs
        '''
        # Files
        S_FileFrame = Frame(t)
        S_FileFrame.pack(fill=X)

        S_FileLabel = Label(S_FileFrame, text="Please type filenames (without suffixes) for files to update, separated by comma.", width=80)
        S_FileLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.S_Files = StringVar()
        S_FileEntry = Entry(S_FileFrame, textvariable=self.S_Files)
        S_FileEntry.pack(fill=X, padx=5, expand=True)
        S_FileEntry.focus_set()
        S_FileEntry.config(state=DISABLED)
        
        # Keys
        S_KeyFrame = Frame(t)
        S_KeyFrame.pack(fill=X)

        S_KeyLabel = Label(S_KeyFrame, text="Please type runs subject to which suffixes to update, separated by comma. If you need to update all runs, just type ALL.", width=100)
        S_KeyLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.S_Keys = StringVar()
        S_KeyEntry = Entry(S_KeyFrame, textvariable=self.S_Keys)
        S_KeyEntry.pack(fill=X, padx=  5, expand=True)
        S_KeyEntry.focus_set()
        S_KeyEntry.config(state=DISABLED)
        
        
        def update_check():
        
            if self.update_option.get() == int(0):
                A_KeyEntry.config(state=DISABLED)
                A_FileEntry.config(state=DISABLED)
                S_KeyEntry.config(state=DISABLED)
                S_FileEntry.config(state=DISABLED)
                
            elif self.update_option.get() == int(1):
                A_KeyEntry.config(state=NORMAL)
                A_FileEntry.config(state=NORMAL)
                S_KeyEntry.config(state=DISABLED)
                S_FileEntry.config(state=DISABLED)
                
            elif self.update_option.get() == int(2):
                A_KeyEntry.config(state=DISABLED)
                A_FileEntry.config(state=DISABLED)
                S_KeyEntry.config(state=NORMAL)
                S_FileEntry.config(state=NORMAL)                
            
            else:
                exit("Invalide value encountered!")
                
        
        upt_Button_0 = Radiobutton(updateFrame, text="Remove and upload all", variable=self.update_option,
                             indicatoron=False, value= int(0), width=20, command = update_check)
        upt_Button_1 = Radiobutton(updateFrame, text="Some files, shared by runs", variable=self.update_option,
                             indicatoron=False, value= int(1), width=20, command = update_check)
        upt_Button_2 = Radiobutton(updateFrame, text="Some files, certain runs", variable=self.update_option,
                             indicatoron=False, value= int(2), width=20, command = update_check)
        
        upt_Button_0.pack(side='left')
        upt_Button_1.pack(side='left') 
        upt_Button_2.pack(side='left')        
        
        
        '''
        utils
        '''
        utilsFrame = Frame(t)
        utilsFrame.pack(fill=X)       
        goButton = Button(utilsFrame, text="Update", command=self.update)
#        self.master.bind("<Return>", self.go)
        goButton.pack(side=RIGHT, padx=5, pady=5)

        cancelButton = Button(utilsFrame, text="Cancel", command=t.destroy)
        cancelButton.pack(side=RIGHT, padx=5, pady=5)  

    
    def connect(self):
        
        self.credential = {"host": self.host.get(), 
                      "port": self.port.get(),
                      "dbname": self.dbname.get(),
                      "username": self.username.get(),
                      "password": self.password.get(), 
                }
                
        database = MongoClient(self.credential['host'].strip())[self.credential['dbname'].strip()]
        database.authenticate(self.credential['username'].strip(), self.credential['password'].strip())
        
        return database
    

    def upload(self, event=None):      
        
        multiple_runs = self.multiruns.get()
        output_folder = os.path.abspath(self.out_dir.get())
        linear = self.isLinear.get()
        keywords = self.keywords.get().split(',')
        large_files = self.largeFile.get()
        verbose = self.verbose.get()
        confidence = self.confidence.get()
        input_heat = self.input_heat.get()
        extra = self.extra.get()
        user = self.username.get()
        par_file = self.par_file.get()
                
        # Global vars
        global Docs_ex, Keys_ex
        Docs_ex = self.exFiles.get().split(',')
        Keys_ex = self.exKeys.get().split(',')
        
        database = self.connect()

        
        self.state = {"host": self.host.get(), 
                      "port": self.port.get(),
                      "dbname": self.dbname.get(),
                      "username": user,
                      "password": self.password.get(), 
                      "multi_runs": multiple_runs, 
                      "out_dir": output_folder,
                      "verbose": verbose,
                      "keywords": keywords,
                      "extra": extra,
                      "large files": output_folder,
                      "confidence": confidence,
                      "input heat": input_heat,
                      "isLinear": linear,
                      "exFiles": Docs_ex,
                      "exKeys": Keys_ex,
                      "database": database,
                      "parfile": par_file
                      }
            
        
        
        if multiple_runs:
            #scan through directory for run directories
            dirnames = next(os.walk(output_folder))[1]
        #    print(dirnames)
            for count, name in enumerate(dirnames, start=0):
                folder = os.path.join(output_folder, name)
        #        if not os.path.isdir('in_par'):
                #check if run is linear or nonlinear
                linear = isLinear(name)
                if linear:
                    lin = ['linear']
                    keywords_lin = keywords + lin
                    runs_coll = database.LinearRuns
                    if isUploaded(out_dir, runs_coll):
                        self.create_update_window()
                    else:
                        upload_linear(database, folder, par_file, user, linear, confidence, 
                                      input_heat, keywords_lin, 
                                      large_files, extra, verbose)
                        messagebox.showinfo("MGKDB", "Upload complete!")
                                        
                else:
                    lin = ['nonlin']                    
                    keywords_lin = keywords + lin
                    runs_coll = database.NonlinRuns
                    if isUploaded(output_folder, runs_coll):
                        self.create_update_window()
                    else:
                        upload_nonlin(database, folder, par_file, user, linear, confidence, 
                                      input_heat, keywords_lin, 
                                      large_files, extra, verbose)
                        messagebox.showinfo("MGKDB", "Upload complete!")
        
        #submit a single run
        else: 
            for dirpath, dirnames, files in os.walk(output_folder):
                if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1:
        #            print(files)
                    #check if run is linear or nonlinear
                    #add linear/nonlin to keywords
                    linear = isLinear(output_folder)
                    if linear:
                        lin = ['linear']
                        keywords_lin = keywords + lin
                        runs_coll = database.LinearRuns
                        if isUploaded(dirpath, runs_coll):
                            self.create_update_window()
                        else:
                            upload_linear(database, dirpath, par_file, user, linear, confidence, 
                                          input_heat, keywords_lin, 
                                          large_files, extra, verbose)
                            messagebox.showinfo("MGKDB", "Upload complete!")
                                            
                    else:
                        lin = ['nonlin']                    
                        keywords_lin = keywords + lin
                        runs_coll = database.NonlinRuns
                        if isUploaded(dirpath, runs_coll):
                            self.create_update_window()
                        else:
                            upload_nonlin(database, dirpath, par_file, user, linear, confidence, 
                                          input_heat, keywords_lin, 
                                          large_files, extra, verbose)
                            messagebox.showinfo("MGKDB", "Upload complete!")

#        reset_docs_keys()
#        self.master.quit()
        
    def update(self, event=None):
        out_dir = os.path.abspath(self.out_dir.get())
        database = self.state['database']
        multiple_runs = self.multiruns.get()
        linear = self.isLinear.get()
        keywords = self.keywords.get().split(',')
        large_files = self.largeFile.get()
        verbose = self.verbose.get()
        confidence = self.confidence.get()
        input_heat = self.input_heat.get()
        extra = self.extra.get()
        user = self.username.get()
        par_file = self.par_file.get()
        suffixes = get_suffixes(out_dir)
        fs = gridfs.GridFS(database)
        
        if self.update_option.get() == int(0):
            if linear:
                lin = ['linear']
                keywords_lin = keywords + lin
                runs_coll = database.LinearRuns
                remove_from_mongo(out_dir, database, runs_coll)   
                upload_linear(database, out_dir, par_file, user, linear, confidence, input_heat, keywords,
                                  large_files, extra, verbose)
            else:
                lin = ['nonlin']                    
                keywords_lin = keywords + lin
                runs_coll = database.NonlinRuns
                remove_from_mongo(out_dir, database, runs_coll) 
                upload_nonlin(database, out_dir, par_file, user, linear, confidence, 
                                          input_heat, keywords_lin, 
                                          large_files, extra, verbose)
                
        elif self.update_option.get() == int(1):
            files_to_update = self.A_Files.get().split(',')
            keys_to_update = self.A_Keys.get().split(',')
            affect_QoI = self.QoI_change.get()
            updated=[]
            for doc, field in zip(files_to_update, keys_to_update):
                files = get_file_list(out_dir, doc) # get file with path
                if len(files)<1:
                    messagebox.showerror("MGKDB", "Files specified not found!")
                assert len(files), "Files specified not found!"
                
                # delete ALL history
                for file in files:
                    grid_out = fs.find({'filepath': file})
                    for grid in grid_out:
                        print('File with path tag:\n{}\n'.format(grid['filepath']) )
                        fs.delete(grid._id)
                        print('deleted!')
                        
                with open(file, 'rb') as f:
                    _id = fs.put(f, encoding='UTF-8', filepath=file)
    #            _id = str(_id)
                updated.append([field, _id])
        
            # update the summary dictionary  
            for entry in updated:
                for suffix in suffixes:
                    if affect_QoI:
                        QoI_dir = get_QoI_from_run(out_dir, suffix)
                        runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                     { "$set": {'QoI': QoI_dir}} 
                                     )
                        
                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                                     {"$set":{'Files.'+entry[0]: entry[1]}}
                                     )
#            print("Update complete")
                
        elif self.update_option.get() == int(2):
            files_to_update = self.S_Files.get().split(',')
            runs_to_update = self.S_Keys.get().split(',')
            affect_QoI = self.QoI_change.get()
            
            if runs_to_update == 'ALL':
                run_suffixes = runs_to_update
            else:
                run_suffixes = suffixes
                
            if linear:
                runs_coll = database.LinearRuns
            else:
                runs_coll = database.NonlinRuns
            
            for doc in files_to_update:
                for suffix in run_suffixes:
                    if affect_QoI:
                        QoI_dir = get_QoI_from_run(out_dir, suffix)
                        runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                     { "$set": {'QoI': QoI_dir}} 
                                     )
                    file = out_dir + '/' + doc  + suffix
                    grid_out = fs.find({'filepath': file})
                    for grid in grid_out:
                        print('File with path tag:\n{}\n'.format(grid['filepath']) )
                        fs.delete(grid._id)
                        print('deleted!')
                    
                    with open(file, 'rb') as f:
                        _id = fs.put(f, encoding='UTF-8', filepath=file)
    #                _id = str(_id)
                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                     { "$set": {'Files.'+ doc: _id} }
                                     )
#            print("Update complete")
            
        else:
            messagebox.showerror("MGKDB", "Invalide value encountered in update option!")
            exit("Invalide value encountered in update option!")
        
#        self.master.quit()
        messagebox.showinfo("MGKDB", "Update complete!")

##        

        
def get_specs():
    main_window = Tk()
    main_window.geometry("1080x960")
    app = Window(main_window)
    main_window.mainloop()
    return app.state

#def get_update():
#    upt_window = Tk()
#    upt_window.geometry("960x720")
#    app = Update_Window(upt_window)
#    upt_window.mainloop()
#    return app.state    

if __name__ == '__main__':
    specs = get_specs()
#    upt = get_update() 
    
