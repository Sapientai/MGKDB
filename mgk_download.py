# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 14:39:26 2020

@author: dykua

For downloading files from mgk_fusion in shell
"""

import sys
sys.path.append('support')

from mgk_file_handling import get_oid_from_query, Str2Query, download_dir_by_name, download_file_by_path, download_file_by_id, download_runs_by_id
import gridfs
from mgk_login import mgk_login,f_login_dbase
import argparse
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

def f_parse_args():
    #==========================================================
    # argument parser
    #==========================================================
    parser = argparse.ArgumentParser(description='Process input for downloading files')

    parser.add_argument('-Q', '--query', default= None,help='mongodb query')
    parser.add_argument('-T', '--target', default= None,help='run collection_name, i.e. gene output folder path')
    parser.add_argument('-F', '--file', default = None, help='filename to be downloaded if any')
    parser.add_argument('-C', '--collection', default = None, help='collection name in the database')
    parser.add_argument('-OID', '--objectID', default = None, help = 'Object ID in the database')
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
    parser.add_argument('-D', '--destination', default = '', help = 'directory where files are downloaded to.')
    parser.add_argument('-S', '--saveas', default = None, help = 'Name to save the file as')

    return parser.parse_args()

### Main 

if __name__=="__main__":

    ### Parse arguments 
    args = f_parse_args()
    # print(args)

    ### Initial setup 
    tar_dir = args.target
    filepath = args.file
    info = args.authenticate
    OID = args.objectID
    destination = args.destination
    collection = args.collection
    fname = args.saveas
    query = args.query

    ### Connect to database 
    login = f_login_dbase(args.authenticate)
    database = login.connect()

    if query:
        print("working on query: {} ......".format(query))
        if collection in ['linear', 'Linear', 'LinearRuns']:
            found = get_oid_from_query(database, database.LinearRuns, Str2Query(query))
            for oid in found:
                download_runs_by_id(database, database.LinearRuns, oid, destination)
        elif collection in ['nonlinear','Nonlinear', 'NonlinRuns']:
            found = get_oid_from_query(database, database.NonlinRuns, Str2Query(query))
            for oid in found:
                download_runs_by_id(database, database.NonlinRuns, oid, destination)
            
    elif filepath:
        download_file_by_path(database, filepath, destination, revision=-1, session=None)   
        
    elif OID:
        if collection in ['linear', 'Linear', 'LinearRuns']:
            download_runs_by_id(database, database.LinearRuns, ObjectId(OID), destination)
        elif collection in ['nonlinear','Nonlinear', 'NonlinRuns']:
            download_runs_by_id(database, database.NonlinRuns, ObjectId(OID), destination)
        elif fname:
            download_file_by_id(database, ObjectId(OID), destination, fname, session = None)

    elif tar_dir:
        if collection in ['linear', 'Linear', 'LinearRuns']:
            download_dir_by_name(database, database.LinearRuns, tar_dir, destination)
        elif collection in ['nonlinear','Nonlinear', 'NonlinRuns']:
            download_dir_by_name(database, database.NonlinRuns, tar_dir, destination)
