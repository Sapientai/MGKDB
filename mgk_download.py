# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 14:39:26 2020

@author: dykua

For downloading files from mgk_fusion in shell
"""

from mgk_file_handling import download_dir_by_name, download_file_by_path, download_file_by_id, download_runs_by_id
import gridfs
from mgk_login import mgk_login
import argparse
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

#==========================================================
# argument parser
#==========================================================
parser = argparse.ArgumentParser(description='Process input for downloading files')

parser.add_argument('-T', '--target', default= None,help='run collection_name, i.e. gene output folder path')
parser.add_argument('-F', '--file', default = None, help='filename to be downloaded if any')
parser.add_argument('-C', '--collection', default = None, help='collection name in the database')
parser.add_argument('-OID', '--objectID', default = None, help = 'Object ID in the database')
parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
parser.add_argument('-D', '--destination', default = '', help = 'directory where files are downloaded to.')
parser.add_argument('-S', '--saveas', default = None, help = 'Name to save the file as')

args = parser.parse_args()

tar_dir = args.target
filepath = args.file
info = args.authenticate
OID = args.objectID
destination = args.destination
collection = args.collection
fname = args.saveas

'''
The login module
'''
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
        exit("The specified file for authentication is not found")
        

database = login.connect()

if filepath:
    download_file_by_path(database, filepath, destination, revision=-1, session=None)   
    
elif OID:
    if collection in ['linear', 'Linear', 'LinearRuns']:
        download_runs_by_id(database, database.LinearRuns, ObjectId(OID), destination)
    elif collection in ['nonlinear','Nonlinear', 'NonlinRuns']:
        download_runs_by_id(database, database.NonelinRuns, ObjectId(OID), destination)
    elif fname:
        download_file_by_id(database, ObjectId(OID), destination, fname, session = None)

elif tar_dir:
    if collection == 'linear':
        download_dir_by_name(database, database.LinearRuns, tar_dir, destination)
    elif collection == 'nonlinear':
        download_dir_by_name(database, database.LinearRuns, tar_dir, destination)
