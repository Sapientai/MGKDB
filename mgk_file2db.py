# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:01:35 2020

@author: dykua

upload a .pkl file to database
"""
import os
import pickle
from bson.objectid import ObjectId
import gridfs
from time import strftime
from mgk_file_handling import gridfs_put_npArray, isUploaded, remove_from_mongo

def upload_dict(db, collection, data_dict):
    shared_file = {} 
    fs = gridfs.GridFS(db)

    for count, suffix in enumerate(data_dict['suffixes']): 
        '''
        Meta
        '''
        time_upload = strftime("%y%m%d-%H%M%S")
        meta_dict = {**data_dict[suffix]['Meta'],
                     "time_uploaded": time_upload,
                     "last_updated": time_upload
                    } 
        '''
        Files
        '''
        file_dict = {}
        if count==0 and isinstance(data_dict['shared'], dict):
            for filename, file_cont in data_dict['shared'].items():
                filepath = os.path.join(data_dict['Location'], filename)
                _id = fs.put(file_cont, encoding='UTF-8', 
                             filepath = filepath,
                             filename = filename,
                             metadata = None)
                if '.' in filename:
                    filename = '_'.join(filename.split(','))
                shared_file[filename] = _id
        
        for filename, file_cont in data_dict[suffix]['Files'].items():
            if file_cont is None:
                file_dict[filename] = 'None'
            else:
                filepath = os.path.join(data_dict['Location'], filename+suffix)
                _id = fs.put(file_cont, encoding='UTF-8', 
                             filepath = filepath,
                             filename = filename+suffix,
                             metadata = None)
                file_dict[filename] = _id
        
        '''
        gyrokinetics
        '''
        
        
        '''
        Diagnostics
        '''
        Diag_dict = data_dict[suffix]['Diagnostics']
        for key, val in Diag_dict.items():
            if key != 'omega':
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], data_dict['Location'], key)
        
        
        
        '''
        assemble
        '''
        run_data =  {'Meta': meta_dict, 'Files': {**shared_file, **file_dict}, 
                     'gyrokinetics': data_dict[suffix]['gyrokinetics'], 
                     'Diagnostics': Diag_dict, 'Plots': data_dict[suffix]['Plots']}
        collection.insert_one(run_data).inserted_id  
        print('Files with suffix: {} in folder {} uploaded successfully'.format(suffix, data_dict['Location']))
        print('='*40)


def file2db(db, pkfile):
    '''
    Get the pickle file
    '''
    with open(pkfile, 'rb') as f:
        data_dict = pickle.load(f)
    
    if data_dict['linear'] is True:
        collection = db.LinearRuns
    
    elif data_dict['linear'] is False:
        collection = db.NonlinRuns
    
    else:
        linear_flag = input('Is the file containing LINEAR runs? Y/N')
        if linear_flag in ['Y', 'y']:
            collection = db.LinearRuns
        elif linear_flag in ['N', 'n']:
            collection = db.NonlinRuns
        else:
            exit('Invalid input')
    
        
    if isUploaded(data_dict['Location'], collection):
        option = input("Folder exists in the database.\n 0: Use this newer version.\n Press other keys to skip.\n")
        if option == '0':
            remove_from_mongo(data_dict['Location'], db, collection) 
            upload_dict(db, collection, data_dict)
        else:
            print("Skipping folder {}...".format(data_dict['Location']))
    else:
        print('Folder tag:\n{}\n not detected, creating new.\n'.format(data_dict['Location']))
        upload_dict(db, collection, data_dict)

    


if __name__ == '__main__':
    from mgk_login import mgk_login
#    login = mgk_login(server='localhost',
#                      port='27017',
#                      dbname='mgk_fusion',
#                      user='dykuang',   # relace with actual username
#                      pwd = '1234')  # replace with actual pass
#
#    mgk_fusion = login.connect()
#    
#    filepath =  r'D:\200904-162623_mgk.pkl' 
#    
#    
#    
#    file2db(mgk_fusion, filepath)
    import argparse
    parser = argparse.ArgumentParser(description='Process input for uploading files')

    parser.add_argument('-T', '--target', default = None, help='Target folder containing saved .pkl files')
    parser.add_argument('-F', '--File', default = None, help='A File containing path to .pkl files to be uplaoded')
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
    args = parser.parse_args()
    info = args.authenticate
    

    if info is None:
        O1 = input("You did not enter credentials for accessing the database.\n You can \n 0: Enter it manually. \n 1: Enter the full path of the saved .pkl file\n")
        if O1 == '0':
            O2 = input("Please enter the server location, port, database name, username, password in order and separated by comma.\n").split(',')
            login = mgk_login(server= O2[0], port= O2[1], dbname=O2[2], user=O2[3], pwd = O2[4])
            O2_1 = input("You can save it by entering a target path, press ENTER if you choose not to save it\n")
            if len(O2_1)>1:
                login.save(os.path.abspath(O2_1) )
            else:
                print('Info not saved!')
                pass
        elif O1 == '1':
            O2= input("Please enter the target path\n")
            login = mgk_login()
            login.from_saved(os.path.abspath(O2))
        
        else:
            exit("Invalid input. Abort")
        
                   
    else:
        login = mgk_login()
        try:
            login.from_saved(os.path.abspath(info))
        except OSError:
            exit("The specified credential file is not found!")
            
    
    mgk_fusion = login.connect()
    
    skipped = []
    
    if args.target is not None:
        output_folder = os.path.abspath(args.target)
        files = next(os.walk(output_folder))[2]
        for filepath in files:
            try:
                if filepath[-4:]=='.pkl':
                    print('Uploading {}.'.format(os.path.join(output_folder, filepath)) )
                    file2db(mgk_fusion, os.path.join(output_folder, filepath))
            except Exception as ee:
                print(ee)
                skipped.append(filepath)
                
        if len(skipped):
            print("These files are skipped: \n {}".format(skipped) )

                
    
    elif args.File is not None:
        filepath = os.path.abspath(args.File)
        with open(filepath, 'r') as f:
            try:
                target_file = f.readline()
                print('Uploading {}.'.format(target_file))
                file2db(mgk_fusion, target_file)
            except Exception as ee:
                print(ee)
                skipped.append(filepath) 
                
        if len(skipped):
            print("These files are skipped: \n {}".format(skipped) )
    
    else:
        exit('Missing necessary argument.')
        
    

    
    


    

