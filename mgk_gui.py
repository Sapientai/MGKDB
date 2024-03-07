# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 13:31:10 2020

@author: dykua

A gui -- version 2

for the MGK-DB

Aiming for 3 main utilities:
    Uploading
    Downloading
    Viewing
"""

from tkinter import *
from tkinter import filedialog
from pymongo import MongoClient
from mgk_file_handling import *
from mgk_file_handling import _troubled_runs

from mgk_post_processing import *
import os
import sys
from tkinter.scrolledtext import ScrolledText
#import json
from diag_plot import diag_plot
#from threading import Thread
from time import strftime
from gui_support import *

def get_diag_with_gui(out_dir, suffix, manual_time_flag, img_dir='./mgk_diagplots'):
    
#    win = Tk()
#    Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, data['tspan'], img_dir)
#    manual_time_flag = not data['all_nrg_flag']
    if manual_time_flag:
        data = get_tspan_gui().data
        tspan = data['tspan']
        if tspan == None:
            manual_time_flag = False
            Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, None, img_dir)
        else:
            Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, tspan, img_dir) 
    else:
        Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, None, img_dir)
        
    return Diag_dict, manual_time_flag, imag_dict

def upload_file_chunks_gui(db, out_dir, large_files=False, extra_files=False, suffix = None, run_shared = None):
    '''
    This function does the actual uploading of grifs chunks and
    returns object_ids for the chunk.
    '''
    
    if suffix is not None:
        par_list = get_file_list(out_dir, 'parameters' + suffix) # assuming parameter files start with 'parameters' 
    else:
        print("Suffix is not provided!")
        
#    print(par_list)
    if len(par_list) == 0:
        exit('Cannot locate parameter files in folder {}.'.format(out_dir))
    elif len(par_list) == 1:
        par_file = par_list[0]
    elif os.path.join(out_dir, 'parameters') in par_list:
        par_file = os.path.join(out_dir, 'parameters')
    else: 
#        par_file = make_par_choice(out_dir, suffix, par_list).par_file
        par_list.sort()
        par_file = par_list[0]
        print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_list[0]))

        
    par = Parameters()
    par.Read_Pars(par_file)
    pars = par.pardict
    n_spec = pars['n_spec']
    
    
    if 'magn_geometry' in pars:
        Docs.append(pars['magn_geometry'][1:-1])
        Keys.append('magn_geometry')
    if large_files:
        if 'name1' in pars and 'mom' in Docs_L:
            Docs_L.pop(Docs_L.index('mom'))
            Keys_L.pop(Keys_L.index('mom'))
            for i in range(n_spec): # adding all particle species
                Docs_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
                Keys_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
    
    output_files = [get_file_list(out_dir, Qname+suffix) for Qname in Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
    
        
    if large_files:
        output_files += [get_file_list(out_dir, Qname+suffix) for Qname in Docs_L if Qname]
    if extra_files:
        output_files += [get_file_list(out_dir, Qname+suffix) for Qname in Docs_ex if Qname]
        
    '''
    Adding files not subject to suffixes 
    '''
    if run_shared is not None:
        output_files += [get_file_list(out_dir, ns) for ns in run_shared]
    
    output_files = set([item for sublist in output_files for item in sublist]) # flat the list and remove possible duplicates
         
    object_ids = {}
    for file in output_files:
        if os.path.isfile(file):
            _id = gridfs_put(db, file)
            object_ids[_id] = file
#    reset_docs_keys()
    return object_ids
        
def upload_linear_gui(db, out_dir, user, confidence, input_heat, keywords, 
                      comments, img_dir = './mgk_diagplots', suffixes = None, run_shared=None,
                      large_files=False, extra=False, verbose=True, default_flag=False):
    #connect to linear collection
#    runs_coll = mgkdb_client.mgk_fusion.LinearRuns
    runs_coll = db.LinearRuns
    
    #generate scan_info.dat
#    suffixes = scan_info(out_dir)
    
    #update files dictionary
    if suffixes is None:         
        suffixes = get_suffixes(out_dir)
        
    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}
   
    
#    manual_time_flag = True
    manual_time_flag = not(default_flag)
    for count, suffix in enumerate(suffixes):
        try:
            print('='*40)
            print('Working on files with suffix: {} in folder .......'.format(suffix, out_dir))
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffix, run_shared)
            else:
                object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffix, None)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            '''
            managing attributes
            '''
            _docs = Docs.copy()
            _keys = Keys.copy()
            
            if large_files:
                _docs = _docs + Docs_L
                _keys = _keys + Keys_L
            if extra:
                _docs = _docs + Docs_ex
                _keys = _keys + Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None')            
            _docs = set(_docs)
            _keys = set(_keys)
            
            print('='*60)
            print('Following files are uploaded.')
            for _id, line in list(object_ids.items()):
                for Q_name, Key in zip(_docs, _keys):
    #                if line.find(os.path.join(out_dir,Q_name + suffix) ) != -1:
    #                if (Q_name + suffix) == line.split('/')[-1]:
                    if os.path.join(out_dir,Q_name + suffix) == line:
    #                    files_dict[Key] = line.split()[0]
                        print(Q_name+suffix)
                        if '.' in Key:
                            Key = '_'.join(Key.split('.'))
    
                        files_dict[Key] = _id
                        try:
                            object_ids.pop(_id)
                        except KeyError:
                            continue
                        
                        break
    
                    if True in shared_not_uploaded and count==0:
                        for S_ind, S_name in enumerate(run_shared):
                            if os.path.join(out_dir,S_name) == line and shared_not_uploaded[S_ind]:
                                print(S_name)
                                if '.' in S_name:
                                    S_name = '_'.join(S_name.split('.'))
                                shared_file_dict[S_name] = _id
                                shared_not_uploaded[S_ind] = False
                            try:
                                object_ids.pop(_id)
                            except KeyError:
                                continue
                    elif count>0 and run_shared is not None:
                        for S_ind, S_name in enumerate(run_shared):
                            print(S_name)
                            
            files_dict = {**files_dict, **shared_file_dict}
            print('='*60)
            
            #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            meta_dict = {"user": user,
                         "run_collection_name": out_dir,
                         "run_suffix": '' + suffix,
                         "keywords": keywords,
                         "confidence": confidence,
                         "comments": comments,
                         "time_uploaded": time_upload,
                         "last_updated": time_upload
                        }  
                   
    #        QoI_dict, Diag_dict = get_QoI_from_run(out_dir, suffix)
            
    #        tspan = get_time_for_diag(suffix)
    #        Diag_dict = get_diag_from_run(out_dir, suffix, tspan) 
    
            print('Working on diagnostics with user specified time span......')
            Diag_dict, manual_time_flag, imag_dict = get_diag_with_gui(out_dir, suffix, manual_time_flag, img_dir)
            
            print('Working on OMAS gyrokinetics dictionary with time span in NRG file......')
            GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear=True)        
            for key, val in Diag_dict.items():
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)
                    
            '''
            Adding omega info to Diag_dict for linear runs
            '''
            omega_val = get_omega(out_dir, suffix)
            Diag_dict['omega'] = {}
            Diag_dict['omega']['ky'] = omega_val[0]
            Diag_dict['omega']['gamma'] = omega_val[1]
            Diag_dict['omega']['omega'] = omega_val[2]
    
    #        param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
            #combine dictionaries and upload
            run_data =  {'Meta': meta_dict, 'Files': files_dict, 'gyrokinetics': GK_dict, 'Diagnostics': Diag_dict, 'Plots': imag_dict}
            runs_coll.insert_one(run_data).inserted_id  
            print('Files with suffix: {} in folder {} uploaded successfully'.format(suffix, out_dir))
            print('='*40)
            if verbose:
                print('A summary is generated as below:\n')
                print(run_data)
        
            '''
            Get a dictionary of what's left in object_ids
            '''
            ex_dict = dict()
            for _id, line in object_ids.items():
                if '.' in line:
                    line = '_'.join(line.split('.'))
                ex_dict[line] = _id
            if ex_dict: 
                db.ex.Lin.insert_one(ex_dict)        
#            reset_docs_keys()
        
        except Exception as exception:
            print(exception)
            print("Skip suffix {} in \n {}. \n".format(suffix, out_dir))
            _troubled_runs.append(out_dir + '##' + suffix)
            print('cleaning ......')
            fs = gridfs.GridFS(db)
            try:
                for _id, _ in id_copy.items():
                    fs.delete(_id)
            except Exception as eee:
                print(eee)
                pass
            
            continue        
#    print('Run collection \'' + out_dir + '\' uploaded succesfully.')
    reset_docs_keys()   
        
def upload_nonlin_gui(db, out_dir, user, confidence, input_heat, keywords,
                      comments, img_dir = './mgk_diagplots', suffixes = None, run_shared=None,
                      large_files=False, extra=False, verbose=True, default_flag = False):
    #connect to nonlinear collection
    runs_coll = db.NonlinRuns
    
    if suffixes is None:         
        suffixes = get_suffixes(out_dir)
    
    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}
    manual_time_flag = not(default_flag)   
    for count, suffix in enumerate(suffixes):
#        print(suffix)
#        print(object_ids)
        try:
            print('='*40)
            print('Working on files with suffix: {} in folder .......'.format(suffix, out_dir))
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffix, run_shared)
            else:
                object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffix, None)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            proc_list = list(object_ids.items())
            '''
            managing attributes
            '''
            _docs = Docs.copy()
            _keys = Keys.copy()
            
            if large_files:
                _docs = _docs + Docs_L
                _keys = _keys + Keys_L
            if extra:
                _docs = _docs + Docs_ex
                _keys = _keys + Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None')            
            _docs = set(_docs)
            _keys = set(_keys)
            
            print('='*60)
            print('Following files are uploaded.')
            for _id, line in proc_list:  
                for Q_name, Key in zip(_docs, _keys):
    #                if line.find(os.path.join(out_dir, Q_name + suffix)) != -1:
                    if os.path.join(out_dir,Q_name + suffix) == line:
                        print(Q_name+suffix)
                        if '.' in Key:
                            Key = '_'.join(Key.split('.'))
    
                        files_dict[Key] = _id
                        try:
                            object_ids.pop(_id)
                            #print('{} removed fro dic.'.format(object_ids[_id]))
                        except KeyError:
                           # print(_id)
                           # print(object_ids)
                            continue
                        break
                        
                    if True in shared_not_uploaded and count==0:
                        for S_ind, S_name in enumerate(run_shared):
                            if os.path.join(out_dir,S_name) == line and shared_not_uploaded[S_ind]:
                                print(S_name)
                                if '.' in S_name:
                                    S_name = '_'.join(S_name.split('.'))
                                shared_file_dict[S_name] = _id
                                shared_not_uploaded[S_ind] = False
                            try:
                                object_ids.pop(_id)
                            except KeyError:
                                continue
                    elif count>0 and run_shared is not None:
                        for S_ind, S_name in enumerate(run_shared):
                            print(S_name)
            
            files_dict = {**files_dict, **shared_file_dict}
            print('='*60)
            #find relevant quantities from in/output
    #        print(suffix)
            
    #        param_dict = get_parsed_params( os.path.join(out_dir, 'parameters' + suffix) )
    
            #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            meta_dict = {"user": user,
                         "run_collection_name": out_dir,
                         "run_suffix": '' + suffix,
                         "keywords": keywords,
                         "confidence": confidence,
                         "comments": comments,
                         "time_uploaded": time_upload,
                         "last_updated": time_upload
                        }
            #data dictionary format for nonlinear runs
    #        QoI_dict, Diag_dict = get_QoI_from_run(out_dir, suffix)
            
    #        tspan = get_time_for_diag(suffix)
    #        Diag_dict = get_diag_from_run(out_dir, suffix, tspan) 
            print('Working on diagnostics with user specified time span......')
            Diag_dict, manual_time_flag, imag_dict = get_diag_with_gui(out_dir, suffix, manual_time_flag, img_dir)
            
            print('Working on OMAS gyrokinetics dictionary with time span in NRG file......')
            GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear=False)
            
            for key, val in Diag_dict.items():
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)
    #        Qes = get_Qes(out_dir, suffix)
    #        QoI_dict = {"Qes" : Qes, **QoI                        
    #                    }
                 
            #combine dictionaries and upload
    #        
    #        run_data =  {''meta_dict, **files_dict, **run_data_dict} 
            run_data =  {'Meta': meta_dict, 'Files': files_dict, 'gyrokinetics': GK_dict, 'Diagnostics': Diag_dict, 'Plots': imag_dict}
            runs_coll.insert_one(run_data).inserted_id  
    
    #        print('Run collection \'' + suffix + 'in ' + out_dir +'\' uploaded succesfully.')        
            print('Files with suffix: {} in folder {} uploaded successfully.'.format(suffix, out_dir))
            print('='*40)
            if verbose:
                print('A summary is generated as below:')
                print(run_data)
        
    
            '''
            Get a dictionary of what's left in object_ids
            '''
            ex_dict = dict()
            for _id, line in object_ids.items():        
                if '.' in line:
                    line = '_'.join(line.split('.'))
                ex_dict[line] = _id
            if ex_dict:
        #        print(ex_dict.values())
                db.ex.Nonlin.insert_one(ex_dict)    
#            reset_docs_keys()
            
        except Exception as exception:
            print(exception)
            print("Skip suffix {} in \n {}. \n".format(suffix, out_dir))
            _troubled_runs.append(out_dir + '##' + suffix)
            print('cleaning ......')
            fs = gridfs.GridFS(db)
            try:
                for _id, _ in id_copy.items():
                    fs.delete(_id)
            except Exception as eee:
                print(eee)
                pass
            
            continue
    reset_docs_keys()

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
    def flush(self):
        pass
        
#class db_info():
#    def __init__(self, host, port, dbname, user, password):
#        self.host = host
#        self.port = port
#        self.dbname = dbname,
#        self.user = user,
#        self.password = password


class Login_window(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        
        self.master.title("MGKDB--MAIN")
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

        hostLabel = Label(hostFrame, text="Host: ", width=10)
        hostLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.host = StringVar()
        hostEntry = Entry(hostFrame, textvariable=self.host)
        hostEntry.pack(fill=X, padx=5, expand=True)
        hostEntry.focus_set()
        
        hostEntry.insert(0, 'mongodb03.nersc.gov') # set default value
#        hostEntry.insert(0, 'localhost')
        '''
        port
        '''
        portFrame = Frame(self)
        portFrame.pack(fill=X)

        portLabel = Label(portFrame, text="Port: ", width=10)
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

        dbnameLabel = Label(dbnameFrame, text="Database: ", width=10)
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
        
#        usernameEntry.insert(0, 'dykuang')
        
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
        
#        passwordEntry.insert(0,'1234')
        
        '''
        If using credential file
        '''
#        credFrame = Frame(self)
#        credFrame.pack(fill=X)
#
#        credLabel = Label(credFrame, text="Authentication: ", width=25)
#        credLabel.pack(side=LEFT, padx = 5, pady=5)
#        
#        self.cred = StringVar()
#        credEntry = Entry(credFrame, textvariable=self.cred)
#        credEntry.pack(fill=X, padx=5, expand=True)
#        credEntry.focus_set()
#        
#        def browse_file():
#            fname = filedialog.askopenfilename()
#            credEntry.insert(0, fname)
#        
#        parButton = Button(credFrame, text="BROWSE", command = browse_file)
#        parButton.pack(side=RIGHT, padx=5, pady=5) 
        
        
        '''
        utils
        '''
        utilsFrame = Frame(self)
        utilsFrame.pack(fill=X)
        
        closeButton = Button(utilsFrame, text="Close", command = self.quit)
        closeButton.pack(side=RIGHT, padx=5, pady=5) 
        
        uploadButton = Button(utilsFrame, text="Connect", command=self.connect)
#        self.master.bind("<Return>", self.upload)
        uploadButton.pack(side=RIGHT, padx=5, pady=5)

    def quit(self):
        self.master.destroy() 
        
    def connect(self):
        
        self.credential = {"host": self.host.get(), 
                      "port": self.port.get(),
                      "dbname": self.dbname.get(),
                      "username": self.username.get(),
                      "password": self.password.get(), 
                }

        database = MongoClient(self.credential['host'].strip())[self.credential['dbname'].strip()]
        database.authenticate(self.credential['username'].strip(), self.credential['password'].strip())
        
        self.credential['database'] = database
        
        self.newWindow = Toplevel(self.master)
        self.app = Utility_window(self.newWindow, db=self.credential)
        
    
class Utility_window(Frame):
    
    def __init__(self, master, db):
        self.master = master
        
        self.database = db
#        print(self.database)
        
        self.frame = Frame(self.master)
        self.master.title("MGKDB -- UTILS")
#        
        topTextFrame = Frame(self.master)
        topTextFrame.pack(fill=X)       
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Utilities Available.")
        
        utilsFrame = Frame(self.master)

        closeButton = Button(utilsFrame, text="Close", command = self.close_windows)
        closeButton.pack(side=RIGHT, padx=50, pady=50)
        
        uploadButton = Button(utilsFrame, text="Upload", command=self.upload)
        uploadButton.pack(side=RIGHT, padx=50, pady=50)
        
        downloadButton = Button(utilsFrame, text="Download", command=self.download)
        downloadButton.pack(side=RIGHT, padx=50, pady=50)

        viewButton = Button(utilsFrame, text="View", command=self.view)
        viewButton.pack(side=RIGHT, padx=50, pady=50)
        
        utilsFrame.pack()

    def close_windows(self):
        self.master.destroy()
            
    def upload(self):
        self.upWindow = Toplevel(self.master)
        self.app = Upload_window(self.upWindow, db=self.database)
    
    def download(self):
        self.downWindow = Toplevel(self.master)
        self.app = Download_window(self.downWindow, db=self.database) 
        
    def view(self):
        self.viewWindow = Toplevel(self.master)
        self.app = View_window(self.viewWindow, db=self.database)
        
    
class Upload_window(Frame):
    def __init__(self, master, db):
        self.master = master
        self.master.title("MGKDB--Upload Panel")
        
        self.database = db

#        topTextFrame = Frame(self.master)
#        topTextFrame.pack(fill=X)
#        
#        topText = Text(topTextFrame, height=2, width=90)
#        topText.pack(side=TOP, padx=5, pady=5)
#        topText.insert(END, "Utilities Available.")
        
        '''
        GENE output folder
        '''
        dirFrame = Frame(self.master)
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
        keywordsFrame = Frame(self.master)
        keywordsFrame.pack(fill=X)

        keywordsLabel = Label(keywordsFrame, text="keywords: ", width=10)
        keywordsLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.keywords = StringVar()
        keywordsEntry = Entry(keywordsFrame, textvariable=self.keywords)
        keywordsEntry.pack(fill=X, padx=5, expand=True)
        keywordsEntry.focus_set()

        keywordsEntry.insert(0, 'GENE')
        
        '''
        temp image dir
        '''
        parFrame = Frame(self.master)
        parFrame.pack(fill=X) 
         
        parLabel = Label(parFrame, text="Temp image dir: ", width=20)
        parLabel.pack(side=LEFT, padx = 5, pady=5)
         
        self.img_dir = StringVar()
        parEntry = Entry(parFrame, textvariable=self.img_dir)
        parEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        parEntry.focus_set()
         
                 
        def browse_file():
            fname = filedialog.askdirectory()
            parEntry.insert(0, fname)
         
        parButton = Button(parFrame, text="BROWSE", command = browse_file)
        parButton.pack(side=RIGHT, padx=5, pady=5) 
# =============================================================================
#         '''
#         A sample parameter file, assuming the rest shares some same settings as "magn_geometry" and 'mom'
#         '''
#         parFrame = Frame(self.master)
#         parFrame.pack(fill=X) 
#         
#         parLabel = Label(parFrame, text="Sample parameter file: ", width=20)
#         parLabel.pack(side=LEFT, padx = 5, pady=5)
#         
#         self.par_file = StringVar()
#         parEntry = Entry(parFrame, textvariable=self.par_file)
#         parEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
#         parEntry.focus_set()
#         
#                 
#         def browse_file():
#             fname = filedialog.askopenfilename()
#             parEntry.insert(0, fname)
#         
#         parButton = Button(parFrame, text="BROWSE", command = browse_file)
#         parButton.pack(side=RIGHT, padx=5, pady=5) 
#         
#         '''
#         confidence
#         '''
#         confiFrame = Frame(self.master)
#         confiFrame.pack(fill=X)
# 
#         confiLabel = Label(confiFrame, text="Confidence: (1-10)", width=15)
#         confiLabel.pack(side=LEFT, padx = 5, pady=5)
#         
#         self.confidence = StringVar()
#         confiEntry = Entry(confiFrame, textvariable=self.confidence)
#         confiEntry.pack(fill=X, padx=5, expand=True)
#         confiEntry.focus_set()
#         confiEntry.insert(0, '5')
# =============================================================================
        
        '''
        input heat
        '''
        heatFrame = Frame(self.master)
        heatFrame.pack(fill=X)

        heatLabel = Label(heatFrame, text="Input Heat: ", width=10)
        heatLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.input_heat = StringVar()
        heatEntry = Entry(heatFrame, textvariable=self.input_heat)
        heatEntry.pack(fill=X, padx=5, expand=True)
        heatEntry.focus_set()
        heatEntry.insert(0, 'None')
        
        
#        '''
#        multirun option
#        '''
#        multirunsFrame = Frame(self.master)
#        multirunsFrame.pack(fill=X)
#        self.multiruns = BooleanVar(value=False)
#        multirunsCheckbox = Checkbutton(multirunsFrame, text="Multiple Runs", 
#                                        variable=self.multiruns, onvalue=True, offvalue=False)
#        multirunsCheckbox.pack()
#        
        '''
        large file option
        '''
        largeFileFrame = Frame(self.master)
        largeFileFrame.pack(fill=X)
        self.largeFile = BooleanVar()
        largeFileCheckbox = Checkbutton(largeFileFrame, text="Large Files", 
                                        variable=self.largeFile, onvalue=True, offvalue=False)
        largeFileCheckbox.pack()
               
        
        '''
        extra file option
        '''
        extraFrame = Frame(self.master)
        extraFrame.pack(fill=X)
        self.extra = BooleanVar()
        
        # Files
        extraFileFrame = Frame(self.master)
        extraFileFrame.pack(fill=X)

        extraFileLabel = Label(extraFileFrame, text="Extra File Name: ", width=20)
        extraFileLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.exFiles = StringVar()
        extraFileEntry = Entry(extraFileFrame, textvariable=self.exFiles)
        extraFileEntry.pack(fill=X, padx=5, expand=True)
        extraFileEntry.focus_set()
        extraFileEntry.config(state=DISABLED)
        
        # Keys
        extraKeyFrame = Frame(self.master)
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
        verboseFrame = Frame(self.master)
        verboseFrame.pack(fill=X)
        self.verbose= BooleanVar()
        verboseCheckbox = Checkbutton(verboseFrame, text="verbose", 
                                      variable=self.verbose, onvalue=True, offvalue=False)
        verboseCheckbox.pack()
        
        '''
        islinear option
        '''
        isLinearFrame = Frame(self.master)
        isLinearFrame.pack(fill=X)
        
        self.isLinear= BooleanVar()
#        isLinearCheckbox = Checkbutton(isLinearFrame, text="Linear", 
#                                        variable=self.isLinear, onvalue=True, offvalue=False)
#        isLinearCheckbox.pack()
        
#        self.isLinear = StringVar(value="Linear")
        isLinLabel = Label(isLinearFrame, text="Type of simulation?", width=35)
        isLinLabel.pack(side=LEFT, padx = 5, pady=5)
        Linear_Button = Radiobutton(isLinearFrame, text="Linear", variable=self.isLinear,
                             indicatoron=False, value= True, width=12, height=2)
        NonLinear_Button = Radiobutton(isLinearFrame, text="Nonlinear", variable=self.isLinear,
                             indicatoron=False, value= False, width=12, height=2)
        Linear_Button.pack(side='left')
        NonLinear_Button.pack(side='left')
        
        '''
        Default option
        '''
        defaultFrame = Frame(self.master)
        defaultFrame.pack(fill=X)
        self.default = BooleanVar()
        defaultLabel = Label(defaultFrame, text="Use default parameters?", width=35)
        defaultLabel.pack(side=LEFT, padx = 5, pady=5)
        defaultButton = Checkbutton(defaultFrame , text="Yes", 
                                    variable=self.default, onvalue=True, offvalue=False)
        defaultButton.pack(side='left')
        

        
        '''
        utils
        '''
        utilsFrame = Frame(self.master)
        utilsFrame.pack(fill=X)
        
        closeButton = Button(utilsFrame, text="Close", command = self.quit)
        closeButton.pack(side=RIGHT, padx=5, pady=5) 
        
        uploadButton = Button(utilsFrame, text="Upload", command=self.upload)
#        self.master.bind("<Return>", self.upload)
        uploadButton.pack(side=RIGHT, padx=5, pady=5)
        
#        updateButton = Button(utilsFrame, text="Update", command=self.create_update_window)
#        updateButton.pack(side=RIGHT, padx=5, pady=5)
        
        
        '''
        Window for console output
        '''
        outFrame = Frame(self.master)
        outFrame.pack(fill=X)
        
        outLabel = Label(outFrame, text="Console", width=10)
        outLabel.pack(side=TOP, padx = 5, pady=5)
        
        text_box = ScrolledText(outFrame, state='disabled')
        text_box.configure(font='TkFixedFont')
        text_box.pack(side=BOTTOM, fill=X, padx = 10, expand=True)
        
        sys.stdout = StdRedirector(text_box)
        

    def quit(self):
        self.master.destroy() 

    def upload(self, event=None):  
        
#        print(self.database['host'])
        
#        multiple_runs = self.multiruns.get()
        output_folder = os.path.abspath(self.out_dir.get())
        linear = self.isLinear.get()
        keywords = self.keywords.get().split(',')
        large_files = self.largeFile.get()
        verbose = self.verbose.get()
        img_dir = self.img_dir.get()
#        confidence = self.confidence.get()
        input_heat = self.input_heat.get()
        extra = self.extra.get()
#        par_file = self.par_file.get()
#        print(par_file)
        default_flag = self.default.get()
        user = self.database['username']
        
        # Global vars
        global Docs_ex, Keys_ex
        Docs_ex = self.exFiles.get().split(',')
        Keys_ex = self.exKeys.get().split(',')
        Docs_ex = [d.strip() for d in Docs_ex]
        Keys_ex = [k.strip() for k in Keys_ex]
        
#        self.state = {**self.database,
#              "multi_runs": multiple_runs, 
#              "out_dir": output_folder,
#              "verbose": verbose,
#              "keywords": keywords,
#              "extra": extra,
#              "large files": large_files,
#              "confidence": confidence,
#              "input heat": input_heat,
#              "isLinear": linear,
#              "exFiles": Docs_ex,
#              "exKeys": Keys_ex,
#              "parfile": par_file
#              }
#        
#        print(self.state)
        
# =============================================================================
#         if multiple_runs:
#             try:
#                 linear = isLinear(output_folder)
#                 if linear == None:
#                     linear = self.isLinear.get()
#                 elif linear != self.isLinear.get():
#                     raise ValueError("Linear/Nonlinear specification found in the parameter file does not agree with your button selection!") 
#                 if linear:
#                     lin = ['linear']
#                     keywords_lin = keywords + lin
#                     runs_coll = self.database['database'].LinearRuns
#                     if isUploaded(output_folder, runs_coll):
#                         self.create_update_window(output_folder)
#                     else:
#                         abc = InputForm(output_folder).data
#                         if abc['skip_flag']:
#                             print("Skipping the folder {}.".format(output_folder))
#                         else:
#                             upload_linear_gui(self.database['database'], output_folder, user, 
#                                               abc['confidence'], input_heat, keywords_lin, abc['comments'],
#                                               img_dir, abc['suffixes'],
#                                               large_files, extra, verbose)
#                 else:
#                     lin = ['nonlin']                    
#                     keywords_lin = keywords + lin
#                     runs_coll = self.database['database'].NonlinRuns
#                     if isUploaded(output_folder, runs_coll):
#                         self.create_update_window(output_folder)
#                     else:
#                         abc = InputForm(output_folder).data
#                         if abc['skip_flag']:
#                             print("Skipping the folder {}.".format(output_folder))
#                         else:
#                             upload_nonlin_gui(self.database['database'], output_folder, user, 
#                                               abc['confidence'], input_heat, keywords_lin, abc['comments'],
#                                               img_dir, abc['suffixes'],
#                                               large_files, extra, verbose)
#                         
#             except Exception as ex:
#                 print('Exception encountered.\n')
#                 print(ex)
#                 print('{} skipped!'.format(output_folder))
#                     
#             #scan through directory for run directories
#             dirnames = next(os.walk(output_folder))[1]
#         #    print(dirnames)
#             for count, name in enumerate(dirnames, start=0):
#                 folder = os.path.join(output_folder, name)
#         #        if not os.path.isdir('in_par'):
#                 #check if run is linear or nonlinear
#                 try:
#                     linear = isLinear(folder)
#                     if linear == None:
#                         linear = self.isLinear.get()
#                     elif linear != self.isLinear.get():
#                         raise ValueError("Linear/Nonlinear specification found in the parameter file does not agree with your button selection!") 
#                     if linear:
#                         lin = ['linear']
#                         keywords_lin = keywords + lin
#                         runs_coll = self.database['database'].LinearRuns
#                         if isUploaded(folder, runs_coll):
#                             self.create_update_window(folder)
#                         else:
#                             abc = InputForm(folder).data
#                             if abc['skip_flag']:
#                                 print("Skipping the folder {}.".format(folder))
#                             else:
#                                 upload_linear_gui(self.database['database'], folder, user, 
#                                                   abc['confidence'], input_heat, keywords_lin, abc['comments'],
#                                                   img_dir, abc['suffixes'],
#                                                   large_files, extra, verbose)
#                     else:
#                         lin = ['nonlin']                    
#                         keywords_lin = keywords + lin
#                         runs_coll = self.database['database'].NonlinRuns
#                         if isUploaded(folder, runs_coll):
#                             self.create_update_window(folder)
#                         else:
#                             abc = InputForm(folder).data
#                             if abc['skip_flag']:
#                                 print("Skipping the folder {}.".format(folder))
#                             else:
#                                 upload_nonlin_gui(self.database['database'], folder, user, 
#                                                   abc['confidence'], input_heat, keywords_lin, abc['comments'],
#                                                   img_dir, abc['suffixes'],
#                                                   large_files, extra, verbose)
#                             
#                 except Exception as ex:
#                     print('Exception encountered.\n')
#                     print(ex)
#                     print('{} skipped!'.format(folder))
#                     continue
#                 
#             messagebox.showinfo("MGKDB", "Upload complete!")
#         
#         else: 
# =============================================================================
        for dirpath, dirnames, files in os.walk(output_folder):
            if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1:
    #            print(files)
                #check if run is linear or nonlinear
                #add linear/nonlin to keywords
#                    try:
                    linear = isLinear(dirpath)
                    if linear == None:
                        linear = self.isLinear.get()
                    elif linear != self.isLinear.get():
                        raise ValueError("Linear/Nonlinear specification found in the parameter file does not agree with your button selection!") 
                    if linear:
                        lin = ['linear']
                        keywords_lin = keywords + lin
                        runs_coll = self.database['database'].LinearRuns
                        if isUploaded(dirpath, runs_coll):
                            self.create_update_window(dirpath)
                        else:
                            '''
                            A pop up window to get par_file, confidence, comments, suffixes
                            '''
                            if default_flag:
                                upload_linear_gui(self.database['database'], dirpath, user, 
                                                  -1, input_heat, keywords_lin, 'Uploaded with default setting',
                                                  img_dir, None, None,
                                                  large_files, extra, verbose, default_flag)
                            else:
                                abc = InputForm(dirpath).data
    #                                print(abc)
                                if abc['skip_flag']:
                                    print("Skipping the folder {}.".format(dirpath))
                                else:
                                    upload_linear_gui(self.database['database'], dirpath, user, 
                                                      abc['confidence'], input_heat, keywords_lin, abc['comments'],
                                                      img_dir, abc['suffixes'], abc['shared'],
                                                      large_files, extra, verbose, default_flag)
#                                pop_win.mainloop()
                    else:
                        lin = ['nonlin']                    
                        keywords_lin = keywords + lin
                        runs_coll = self.database['database'].NonlinRuns
                        if isUploaded(dirpath, runs_coll):
                            self.create_update_window(dirpath)
                        else:
                            if default_flag:
                                upload_nonlin_gui(self.database['database'], dirpath, user, 
                                                  -1, input_heat, keywords_lin, 'Uploaded with default setting',
                                                  img_dir, None, None,
                                                  large_files, extra, verbose, default_flag)
                            else:
                                abc = InputForm(dirpath).data
                                if abc['skip_flag']:
                                    print("Skipping the folder {}.".format(dirpath))
                                else:
                                    upload_nonlin_gui(self.database['database'], dirpath, user, 
                                                      abc['confidence'], input_heat, keywords_lin, abc['comments'],
                                                      img_dir, abc['suffixes'],abc['shared'],
                                                      large_files, extra, verbose, default_flag)

                                
#                    except Exception as ex:
#                        print('Exception encountered.\n')
#                        print(ex)
#                        print('{} skipped!'.format(dirpath))
#                        continue
        if len(_troubled_runs):
            print("The following runs are skipped due to exceptions.")
            for r in _troubled_runs:
                print(r)        
        messagebox.showinfo("MGKDB", "Upload complete!")
                            
    def create_update_window(self, target_folder):
        
#        multiple_runs = self.multiruns.get()
#        output_folder = os.path.abspath(self.out_dir.get())
        linear = self.isLinear.get()
        keywords = self.keywords.get().split(',')
        large_files = self.largeFile.get()
        verbose = self.verbose.get()
#        confidence = self.confidence.get()
        input_heat = self.input_heat.get()
        extra = self.extra.get()
        img_dir = self.img_dir.get()
#        par_file = self.par_file.get()
        
        self.state = {**self.database,
#              "multi_runs": multiple_runs, 
#              "out_dir": output_folder,
              "out_dir": target_folder,
              "verbose": verbose,
              "keywords": keywords,
              "extra": extra,
              "large files": large_files,
              "img_dir": img_dir,
#              "confidence": confidence,
              "input heat": input_heat,
              "isLinear": linear,
              "exFiles": Docs_ex,
              "exKeys": Keys_ex
#              "parfile": par_file
              }
        
        self.updateWindow = Toplevel(self.master)
        self.app = Update_window(self.updateWindow, dbstate=self.state)

class Update_window(Frame):
    
    def __init__(self, master, dbstate):
        self.master = master
        self.master.title("MGKDB--UPDATE")
        self.dbstate = dbstate

        topTextFrame = Frame(self.master)
        topTextFrame.pack(fill=X)
#        
#        topText = Text(topTextFrame, height=2, width=90)
#        topText.pack(side=TOP, padx=5, pady=5)
#        topText.insert(END, "Utilities Available.")
#        topTextFrame = Frame(t)
#        topTextFrame.pack(fill=X)
        
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Folder \n {} \n exists in database. Please use the below options to proceed with updates.".format(dbstate['out_dir']))
        

        '''
        update option
        '''
        updateFrame = Frame(self.master)
        updateFrame.pack(fill=X)
        
        self.update_option= IntVar()
       
#        '''
#        Will it change QoI?
#        '''
#        QoIFrame = Frame(self.master)
#        QoIFrame.pack(fill=X)
#        self.QoI_change = BooleanVar(value=True)
#        QoICheckbox = Checkbutton(QoIFrame, text="Will files-to-update change QoI/Diagnostic?", 
#                                  variable=self.QoI_change, onvalue=True, offvalue=False)
#        QoICheckbox.pack()
        
        
        '''
        update: Files relating to all runs.
        '''
        # Files
        A_FileFrame = Frame(self.master)
        A_FileFrame.pack(fill=X)

        A_FileLabel = Label(A_FileFrame, text="Please type FULL file names to update, separated by comma.", width=60)
        A_FileLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.A_Files = StringVar()
        A_FileEntry = Entry(A_FileFrame, textvariable=self.A_Files)
        A_FileEntry.pack(fill=X, padx=5, expand=True)
        A_FileEntry.focus_set()
        A_FileEntry.config(state=DISABLED)
        
        # Keys
        A_KeyFrame = Frame(self.master)
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
        S_FileFrame = Frame(self.master)
        S_FileFrame.pack(fill=X)

        S_FileLabel = Label(S_FileFrame, text="Please type filenames (without suffixes) for files to update, separated by comma.", width=80)
        S_FileLabel.pack(side=TOP, padx = 5, pady=5)
        
        self.S_Files = StringVar()
        S_FileEntry = Entry(S_FileFrame, textvariable=self.S_Files)
        S_FileEntry.pack(fill=X, padx=5, expand=True)
        S_FileEntry.focus_set()
        S_FileEntry.config(state=DISABLED)
        
        # Keys
        S_KeyFrame = Frame(self.master)
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
                             indicatoron=False, value= int(0), width=80, command = update_check)
        upt_Button_1 = Radiobutton(updateFrame, text="Some files, shared by all runs", variable=self.update_option,
                             indicatoron=False, value= int(1), width=80, command = update_check)
        upt_Button_2 = Radiobutton(updateFrame, text="Some files, each subject to a certain run", variable=self.update_option,
                             indicatoron=False, value= int(2), width=80, command = update_check)
        
        upt_Button_0.pack(side='top')
        upt_Button_1.pack(side='top') 
        upt_Button_2.pack(side='top') 
        
                   
        '''
        utils
        '''
        utilsFrame = Frame(self.master)
        utilsFrame.pack(fill=X) 
        
        cancelButton = Button(utilsFrame, text="Cancel", command=self.quit)
        cancelButton.pack(side=RIGHT, padx=5, pady=5)

        goButton = Button(utilsFrame, text="Update", command=self.update)
#        self.master.bind("<Return>", self.go)
        goButton.pack(side=RIGHT, padx=5, pady=5)

  
        
    def quit(self):
        self.master.destroy()
        
    def update(self, event=None):
        
        out_dir = self.dbstate['out_dir']
#        multiple_runs = self.dbstate['multi_runs']
        linear = self.dbstate['isLinear']
        keywords = self.dbstate['keywords']
        large_files = self.dbstate['large files']
        verbose = self.dbstate['verbose']
#        confidence = self.dbstate['confidence']
        input_heat = self.dbstate['input heat']
        extra = self.dbstate['extra']
        user = self.dbstate['username']
#        par_file = self.dbstate['parfile']
        database = self.dbstate['database']
        img_dir = self.dbstate['img_dir']
        
        suffixes = get_suffixes(out_dir)
        fs = gridfs.GridFS(self.dbstate['database'])
        
        if self.update_option.get() == int(0):
            if linear:
                lin = ['linear']
                keywords_lin = keywords + lin
                runs_coll = database.LinearRuns
                remove_from_mongo(out_dir, database, runs_coll) 
#                try:
                abc = InputForm(out_dir).data
                if abc['skip_flag']:
                    print("Skipping the folder {}.".format(out_dir))
                    
                else:
                    upload_linear_gui(database, out_dir, user, 
                                      abc['confidence'], input_heat, keywords_lin, 
                                      abc['comments'], img_dir, abc['suffixes'], abc['shared'],
                                      large_files, extra, verbose, False)
#                except Exception as ex:
#                    print('Exception encountered.\n')
#                    print(ex)
#                    print('{} skipped!'.format(out_dir))
                    
            else:
                lin = ['nonlin']                    
                keywords_lin = keywords + lin
                runs_coll = database.NonlinRuns
                remove_from_mongo(out_dir, database, runs_coll) 
#                try:
                abc = InputForm(out_dir).data
                if abc['skip_flag']:
                    print("Skipping the folder {}.".format(out_dir))
                else:
                    upload_nonlin_gui(database, out_dir, user, 
                                      abc['confidence'], input_heat, keywords_lin, 
                                      abc['comments'], img_dir, abc['suffixes'],abc['shared'],
                                      large_files, extra, verbose, False)
#                except Exception as ex:
#                    print('Exception encountered.\n')
#                    print(ex)
#                    print('{} skipped!'.format(out_dir))
                    
                
        elif self.update_option.get() == int(1):
            files_to_update = self.A_Files.get().split(',')
            files_to_update = [f.strip() for f in files_to_update]
            keys_to_update = self.A_Keys.get().split(',')
            keys_to_update = [k.strip() for k in keys_to_update]
#            affect_QoI = self.QoI_change.get()
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
                        print('File with path tag:\n{}\n'.format(grid.filepath) )
                        fs.delete(grid._id)
                        print('deleted!')
                        
                with open(file, 'rb') as f:
                    _id = fs.put(f, encoding='UTF-8', filepath=file, filename = file.split('/')[-1])
    #            _id = str(_id)
                updated.append([field, _id])
        
            # update the summary dictionary  
            for entry in updated:
                manual_time_flag = True
                for suffix in suffixes:
#                    if affect_QoI:

                    GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear)        
                    Diag_dict, manual_time_flag, imag_dict = get_diag_with_gui(out_dir, suffix, manual_time_flag, img_dir)
 
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(database, Diag_dict[key], key, out_dir)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                         { "$set": {'gyrokinetics': GK_dict, 'Diagnostics':Diag_dict, 'Plots': imag_dict}}  )

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                                     {"$set":{'Files.'+entry[0]: entry[1], 
                                              "Meta.last_updated": strftime("%y%m%d-%H%M%S")}
                                     }
                                     )
#            print("Update complete")
                
        elif self.update_option.get() == int(2):
            files_to_update = self.S_Files.get().split(',')
            files_to_update = [file.strip() for file in files_to_update]
            runs_to_update = self.S_Keys.get().split(',')
#            affect_QoI = self.QoI_change.get()
            
            if len(runs_to_update) ==1 and runs_to_update[0].strip() in ['ALL','all', 'All']:
                run_suffixes = suffixes
            else:
                run_suffixes = [i.strip() for i in runs_to_update]
                
            if linear:
                runs_coll = database.LinearRuns
            else:
                runs_coll = database.NonlinRuns
            
            for doc in files_to_update:
                for suffix in run_suffixes:
#                    if affect_QoI:
                    GK_dict = get_gyrokinetics_from_run(out_dir, suffix, user, linear)        
                    Diag_dict, manual_time_flag, imag_dict = get_diag_with_gui(out_dir, suffix, manual_time_flag, img_dir)
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(database, Diag_dict[key], key, out_dir)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix },
                        { "$set": {'gyrokinetics': GK_dict, 'Diagnostics':Diag_dict, 'Plots': imag_dict}}
                             )                        
                    
                    file = os.path.join(out_dir, doc  + suffix)
                    grid_out = fs.find({'filepath': file})
                    for grid in grid_out:
                        print('File with path tag:\n{}\n'.format(grid.filepath) )
                        fs.delete(grid._id)
                        print('deleted!')
                    
                    with open(file, 'rb') as f:
                        _id = fs.put(f, encoding='UTF-8', filepath=file, filename = file.split('/')[-1])
    #                _id = str(_id)
                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                     { "$set": {'Files.'+ doc: _id, "Meta.last_updated": strftime("%y%m%d-%H%M%S")}}
                                     )
#            print("Update complete")
            
        else:
            messagebox.showerror("MGKDB", "Invalide value encountered in update option!")
            exit("Invalide value encountered in update option!")
        
#        self.master.quit()
        print("******* Update complete! *******")
        messagebox.showinfo("MGKDB", "Update complete!")
        
        

class Download_window(Frame):
    
    def __init__(self, master, db):
        self.master = master
        self.database = db
        self.master.title("MGKDB--Download Panel")
        
        topTextFrame = Frame(self.master)
        topTextFrame.pack(fill=X)
        
        topText = Text(topTextFrame, height=2, width=90)
        topText.pack(side=TOP, padx=5, pady=5)
        topText.insert(END, "Please select the download option to proceed.")
        
        '''
        Download options
        '''
        self.dl_option= IntVar()
        
        def option_check():
        
            if self.dl_option.get() == int(0):
                dirEntry.config(state=DISABLED)
                IdEntry.config(state=NORMAL)
                qEntry.config(state=DISABLED)
            elif self.dl_option.get() == int(1):
                dirEntry.config(state=NORMAL)
                IdEntry.config(state=DISABLED)
                qEntry.config(state=DISABLED)
            elif self.dl_option.get() == int(2):
                dirEntry.config(state=DISABLED)
                IdEntry.config(state=DISABLED)
                qEntry.config(state=NORMAL)
            
            else:
                exit("Invalide value encountered!")
                
        dlFrame = Frame(self.master)
        dlFrame.pack(fill=X)
        
        dl_Button_0 = Radiobutton(dlFrame, text="Download a run with ID", variable=self.dl_option,
                             indicatoron=False, value= int(0), width=80, command = option_check)
        dl_Button_1 = Radiobutton(dlFrame, text="Download all runs with the same run_collection_name", variable=self.dl_option,
                             indicatoron=False, value= int(1), width=80, command = option_check)
        dl_Button_2 = Radiobutton(dlFrame, text="Download with query", variable=self.dl_option,
                             indicatoron=False, value= int(2), width=80, command = option_check)

        dl_Button_0.pack(side='top',padx = 5, pady=5)
        dl_Button_1.pack(side='top',padx = 5, pady=5) 
        dl_Button_2.pack(side='top',padx = 5, pady=5)
        
        '''
        run_collection_name
        '''
        dirFrame = Frame(self.master)
        dirFrame.pack(fill=X)

        dirLabel = Label(dirFrame, text="Run_collection_name: ", width=25)
        dirLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.rcn = StringVar()
        dirEntry = Entry(dirFrame, textvariable=self.rcn)
        dirEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        dirEntry.config(state=DISABLED)
        dirEntry.focus_set()
        
        '''
        Id
        '''
        IdFrame = Frame(self.master)
        IdFrame.pack(fill=X)

        IdLabel = Label(IdFrame, text="ObjectId: ", width=25)
        IdLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.oid = StringVar()
        IdEntry = Entry(IdFrame, textvariable=self.oid)
        IdEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        IdEntry.focus_set()
        
        '''
        Query
        '''
        qFrame = Frame(self.master)
        qFrame.pack(fill=X)

        qLabel = Label(qFrame, text="Filter: ", width=25)
        qLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.query = StringVar()
        qEntry = Entry(qFrame, textvariable=self.query)
        qEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        qEntry.config(state=DISABLED)
        qEntry.focus_set()
       
        qButton = Button(qFrame, text="Find", command = self.find)
        qButton.pack(side=RIGHT, padx=5, pady=5)
        
        '''
        islinear option
        '''
        isLinearFrame = Frame(self.master)
        isLinearFrame.pack(fill=X)
        
        isLinLabel = Label(isLinearFrame, text="Which collection?", width=25)
        isLinLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.isLinear= BooleanVar()
        Linear_Button = Radiobutton(isLinearFrame, text="Linear", variable=self.isLinear,
                             indicatoron=False, value= True, height = 2, width=8)
        NonLinear_Button = Radiobutton(isLinearFrame, text="Nonlinear", variable=self.isLinear,
                             indicatoron=False, value= False, height = 2, width=8)
        Linear_Button.pack(side='left')
        NonLinear_Button.pack(side='left')
        
        
        '''
        Download to 
        '''
        dlFrame = Frame(self.master)
        dlFrame.pack(fill=X)

        dlLabel = Label(dlFrame, text="Download to:", width=25)
        dlLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.dl_dir = StringVar()
        dlEntry = Entry(dlFrame, textvariable=self.dl_dir)
        dlEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        dlEntry.focus_set()
        
        def browse():
            dirname = filedialog.askdirectory()
            dlEntry.insert(0, dirname)
        
        BrButton = Button(dlFrame, text="BROWSE", command = browse)
        BrButton.pack(side=RIGHT, padx=5, pady=5)
        
        '''
        utils
        '''
        utilsFrame = Frame(self.master)
        utilsFrame.pack(fill=X) 
        
        closeButton = Button(utilsFrame, text="Close", command = self.quit)
        closeButton.pack(side=RIGHT, padx=5, pady=5) 
        
        dlButton = Button(utilsFrame, text="Download", command= self.down)
        dlButton.pack(side=RIGHT, padx=5, pady=5)

        utilsFrame.pack()
        
        '''
        Window for console output
        '''
        outFrame = Frame(self.master)
        outFrame.pack(fill=X)
        
        outLabel = Label(outFrame, text="Console", width=10)
        outLabel.pack(side=TOP, padx = 5, pady=5)
        
        text_box = ScrolledText(outFrame, state='disabled')
        text_box.configure(font='TkFixedFont')
        text_box.pack(side=BOTTOM, fill=X, padx = 10, expand=True)
            
        sys.stdout = StdRedirector(text_box)
        
    def find(self):
        if self.isLinear.get():
            self.runs_coll = self.database['database'].LinearRuns
        else:
            self.runs_coll = self.database['database'].NonlinRuns
        q_dict = Str2Query(self.query.get())
        records = self.runs_coll.find(q_dict)
        self.ids_list = []
        print('{} records found.'.format(records.count()))
        for _record in records:
            print(_record['_id'])
            print(_record['Meta'])
            self.ids_list.append(_record['_id'])          
    
    def down(self):
        
        if self.isLinear.get():
            self.runs_coll = self.database['database'].LinearRuns
        else:
            self.runs_coll = self.database['database'].NonlinRuns
        
#        print(self.runs_coll)
        if self.dl_option.get() == int(0):
            ids_list_raw = self.oid.get().split(',')
            self.ids_list = [_id.strip() for _id in ids_list_raw]
            for oid in self.ids_list:
                print(self.dl_dir.get())
                download_runs_by_id(self.database['database'], self.runs_coll, ObjectId(oid), self.dl_dir.get())
        elif self.dl_option.get() == int(1): 
            tar_list_raw = self.rcn.get().split(',')
            self.tar_list = [_dir.strip() for _dir in tar_list_raw]
            for doc in self.tar_list:
#                print(doc)
                download_dir_by_name(self.database['database'], self.runs_coll, doc, self.dl_dir.get())
        
        elif self.dl_option.get() == int(2):
            for oid in self.ids_list:
                download_runs_by_id(self.database['database'], self.runs_coll, oid, self.dl_dir.get())

        else:
            exit('Invalid download option encountered!')
        
    
    def quit(self):
        self.master.destroy()     
                           
        

class View_window(Frame):  
    def __init__(self, master, db):
        self.master = master
        self.database = db
        self.master.title("MGKDB--View Panel")
    
#        topTextFrame = Frame(self.master)
#        topTextFrame.pack(fill=X)
#        
#        topText = Text(topTextFrame, height=2, width=90)
#        topText.pack(side=TOP, padx=5, pady=5)
#        topText.insert(END, "Please select the download option to proceed.") 
        '''
        islinear option
        '''
        isLinearFrame = Frame(self.master)
        isLinearFrame.pack(fill=X)
        
        isLinLabel = Label(isLinearFrame, text="Which collection?", width=25)
        isLinLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.isLinear= BooleanVar()
        Linear_Button = Radiobutton(isLinearFrame, text="Linear", variable=self.isLinear,
                             indicatoron=False, value= True, height=2, width=8)
        NonLinear_Button = Radiobutton(isLinearFrame, text="Nonlinear", variable=self.isLinear,
                             indicatoron=False, value= False, height=2, width=8)
        Linear_Button.pack(side='left')
        NonLinear_Button.pack(side='left')
        
        '''
        Query option
        '''
        self.q_option= IntVar()
        
        def option_check():
        
            if self.q_option.get() == int(0):
                qEntry.config(state=DISABLED)
                IdEntry.config(state=NORMAL)
            elif self.q_option.get() == int(1):
                qEntry.config(state=NORMAL)
                IdEntry.config(state=DISABLED)
            
            else:
                exit("Invalide value encountered!")
                
        qopFrame = Frame(self.master)
        qopFrame.pack(fill=X)
        
        qop_Button_0 = Radiobutton(qopFrame, text="Query with ID", variable=self.q_option,
                             indicatoron=False, value= int(0), width=80, command = option_check)
        qop_Button_1 = Radiobutton(qopFrame, text="General Queries", variable=self.q_option,
                             indicatoron=False, value= int(1), width=80, command = option_check)
        
        qop_Button_0.pack(side='top',padx = 5, pady=5)
        qop_Button_1.pack(side='top',padx = 5, pady=5) 

        '''
        Id
        '''
        IdFrame = Frame(self.master)
        IdFrame.pack(fill=X)

        IdLabel = Label(IdFrame, text="ObjectId: ", width=25)
        IdLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.oid = StringVar()
        IdEntry = Entry(IdFrame, textvariable=self.oid)
        IdEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        IdEntry.config(state=DISABLED)
        IdEntry.focus_set() 
        
        '''
        Query
        '''
        qFrame = Frame(self.master)
        qFrame.pack(fill=X)

        qLabel = Label(qFrame, text="Filter: ", width=25)
        qLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.query = StringVar()
        qEntry = Entry(qFrame, textvariable=self.query)
        qEntry.pack(side=LEFT, fill=X, padx=5, expand=True)
        qEntry.config(state=DISABLED)
        qEntry.focus_set()
       
        qButton = Button(qFrame, text="Find", command = self.find)
        qButton.pack(side=RIGHT, padx=5, pady=5)
        
         
        '''
        Plot Option
        '''
        plotFrame = Frame(self.master)
        plotFrame.pack(fill=X)

        plotLabel = Label(plotFrame, text="Diagnostics: ", width=25)
        plotLabel.pack(side=LEFT, padx = 5, pady=5)
        
        self.pltnames = ['Amplitude Spectra', "Flux Spectra", "Shearing Rate"]
        
        self.pltvals = {}
        self.pltbox = {}
        for name in self.pltnames:
            self.pltvals[name] = BooleanVar()
            self.pltbox[name] = Checkbutton(plotFrame, text=name, 
                                            variable=self.pltvals[name], onvalue=True, offvalue=False)
            self.pltbox[name].pack(side='right',padx = 5, pady=5)
        
#        self.AS = BooleanVar()
#        ASCheckbox = Checkbutton(plotFrame, text="Amplitude Spectra", 
#                                        variable=self.AS, onvalue=True, offvalue=False)
#        ASCheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.FS = BooleanVar()
#        FSCheckbox = Checkbutton(plotFrame, text="Flux Spectra", 
#                                        variable=self.FS, onvalue=True, offvalue=False)
#        FSCheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.SR = BooleanVar()
#        SRCheckbox = Checkbutton(plotFrame, text="Shearing Rate", 
#                                        variable=self.SR, onvalue=True, offvalue=False)
#        SRCheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.FGR = BooleanVar()
#        FGRCheckbox = Checkbutton(plotFrame, text="Freq Growth Rate", 
#                                        variable=self.FGR, onvalue=True, offvalue=False)
#        FGRCheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.CT = BooleanVar()
#        CTCheckbox = Checkbutton(plotFrame, text="Contours", 
#                                        variable=self.CT, onvalue=True, offvalue=False)
#        CTCheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.BA = BooleanVar()
#        BACheckbox = Checkbutton(plotFrame, text="Ballamp", 
#                                        variable=self.BA, onvalue=True, offvalue=False)
#        BACheckbox.pack(side='right',padx = 5, pady=5)
#        
#        self.CP = BooleanVar()
#        CPCheckbox = Checkbutton(plotFrame, text="Cross Phase", 
#                                        variable=self.CP, onvalue=True, offvalue=False)
#        CPCheckbox.pack(side='right',padx = 5, pady=5)
        
        
        '''
        utils
        '''
        utilsFrame = Frame(self.master)
        utilsFrame.pack(fill=X) 

        closeButton = Button(utilsFrame, text="Close", command = self.quit)
        closeButton.pack(side=RIGHT, padx=5, pady=5) 
        
        dlButton = Button(utilsFrame, text="Plot", command= self.plot)
        dlButton.pack(side=RIGHT, padx=5, pady=5)
        
        utilsFrame.pack()
        
        '''
        Window for console output
        '''
        outFrame = Frame(self.master)
        outFrame.pack(fill=X)
        
        outLabel = Label(outFrame, text="Console", width=10)
        outLabel.pack(side=TOP, padx = 5, pady=5)
        
        text_box = ScrolledText(outFrame, state='disabled')
        text_box.configure(font='TkFixedFont')
        text_box.pack(side=BOTTOM, fill=X, padx = 10, expand=True)
        
        sys.stdout = StdRedirector(text_box)
        
#    def start_plot(self):
#        thread = Thread(target=self.plot)
#        thread.start()
        
    def find(self):
        if self.isLinear.get():
            self.runs_coll = self.database['database'].LinearRuns
        else:
            self.runs_coll = self.database['database'].NonlinRuns
#        print(self.query.get())
        q_dict = Str2Query(self.query.get())
        records = self.runs_coll.find(q_dict)
        self.ids_list = []
        print('{} records found.'.format(records.count()))
        for _record in records:
            print(_record['_id'])
            print(_record['Meta'])
            self.ids_list.append(_record['_id'])

        
    def plot(self):
#        fs = gridfs.GridFS(self.database['database'])
        if self.isLinear.get():
            self.runs_coll = self.database['database'].LinearRuns
        else:           
            self.runs_coll = self.database['database'].NonlinRuns
            
        if self.q_option.get() == int(0):    
            ids_list_raw = self.oid.get().split(',')
            self.ids_list = [_id.strip() for _id in ids_list_raw]
            
        for _id in self.ids_list:
            data_dict = load(self.database['database'], self.runs_coll, 
                             {'_id':ObjectId(_id)}, projection={'Meta':1,'Diagnostics':1})[0] # load method returns a list
            if data_dict == None:
                print('Cannot find this id: {} in this collection.'.format(_id))
                break
            else:
                fig = diag_plot(data_dict, save_fig = False)
                
                for name in self.pltnames:
                    if self.pltvals[name].get():
                        fig.avail_plts[name]()
                        
#                if self.AS.get():
#                    fig.diag_amplitude_spectra()            
#                
#                if self.FS.get():
#                    fig.diag_flux_spectra()
#    
#                if self.SR.get():
#                    fig.diag_shearing_rate()
#                    
#                if self.BA.get():
#                    fig.diag_ballamp()
#
#                if self.CP.get():
#                    fig.diag_crossphase()
#                    
#                if self.FGR.get():
#                    fig.diag_freqgrowrate()()
#                    
#                if self.CT.get():
#                    fig.diag_contours()                    
                
        
    def quit(self):
        self.master.destroy()  
      

def make_gui():
    main_window = Tk()
    main_window.geometry("1080x480")
    mgk=Login_window(main_window)
    
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            main_window.destroy()

    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()
    
if __name__ == '__main__':
    make_gui()