"""
Created on Wed Feb 26 15:08:36 2020

@author: dykuang

Make plots of some diagnostics
"""
from mgk_file_handling import load, _binary2npArray, _loadNPArrays
import os
from mgk_login import mgk_login
import argparse
from sys import exit
from diag_plot import diag_plot
from bson.objectid  import ObjectId
#==========================================================
# argument parser
#==========================================================
parser = argparse.ArgumentParser(description='Plotting diagnositcs')

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

user = login.login['user']


def diag_plot_from_query(db, collection, query, projection={'Meta':1, 'Diagnostics':1}):

    data = load(db, collection, query, projection)
    if data is not None:
        n_records = len(data)
        print('{} records returned from your query.'.format(n_records) )
        
        p = [diag_plot(data[i]) for i in range(n_records)]
        
        for i in range(n_records):
            p[i].plot_all()
            print('Plotting found record {}'.format(i+1) )
            input('Press ENTER to continue ...')
    else:
        print('The database returns None for your query.')


        
import gridfs
from pathlib import Path
import json

def download_from_query(db, collection, query, destination='./'):
    fs = gridfs.GridFSBucket(db)
    records_found = collection.find(query)
    
    for record in records_found:
        
        dir_name = record['Meta']['run_collection_name']
        path = os.path.join(destination, dir_name.split('/')[-1])
        if not os.path.exists(path):
            try:
                path = os.path.join(destination, dir_name.split('/')[-1])
                #os.mkdir(path)
                Path(path).mkdir(parents=True)
            except OSError:
                print ("Creation of the directory %s failed" % path)
        #else:
        
        '''
        Download saved files
        '''
        for key, val in record['Files'].items():
            if val != 'None':
                filename = db.fs.files.find_one(val)['filename']
                #print(db.fs.files.find_one(val)).keys()
                with open(os.path.join(path, filename),'wb+') as f:
    #                    fs.download_to_stream_by_name(filename, f, revision=-1, session=None)
                    fs.download_to_stream(val, f, session=None)
                record['Files'][key] = str(val)
        #print(record)
        
        '''
        Download diagnostics
        '''
        for key, val in record['Diagnostics'].items():
            if isinstance(val, ObjectId):
                data = _loadNPArrays(db, val)
                record['Diagnostics'][key] = data
        
        record['_id'] = str(record['_id'])
        
        f_path = os.path.join(path, 'mgkdb_summary_for'+record['Meta']['run_suffix']+'.json')
        if os.path.isfile(f_path):
            with open(f_path, 'w') as f:
                json.dump(record, f)
            print("Successfully downloaded files in the collection to directory %s " % path)
        else:
            exit('File exists already!')




