# -*- coding: utf-8 -*-
"""
Main script to handle uploading GENE runs to the MGK database
Required fields:    user
                    output_folder
                    multiple_runs (True or False)
                    
Optional fields:    confidence
                    input_heat
                    keywords
                    
@author: Austin Blackmon, Dongyang Kuang, Venkitesh Ayyar
"""

import sys
import os
import argparse
from sys import exit
sys.path.append('support')

from mgk_file_handling import get_suffixes, upload_to_mongo, isLinear, Global_vars, f_get_linked_oid
#from ParIO import *
from mgk_login import mgk_login,f_login_dbase

def f_parse_args():
    #==========================================================
    # argument parser
    #==========================================================
    parser = argparse.ArgumentParser(description='Process input for uploading files')

    parser.add_argument('-T', '--target', help='Target run output folder')

    parser.add_argument('-V', '--verbose', dest='verbose', default = False, action='store_true', help='output verbose')
    parser.add_argument('-Ex', '--extra', dest='extra', default = False, action='store_true', help='whether or not to include extra files')
    parser.add_argument('-L', '--large_files', dest='large_files', default = False, action='store_true', help='whether or not to include large files')
                        
    parser.add_argument('-K', '--keywords', default = '-', help='relevant keywords for future references, separated by comma')
    parser.add_argument('-SIM', '--sim_type', choices=['GENE','CGYRO','TGLF','GS2'], type=str, help='Type of simulation', required=True)
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
    parser.add_argument('-X', '--exclude', default = None, help='folders to exclude')
    
    parser.add_argument('-lf', '--linked_id_file', default = None, help='File with Object ID to link')
    parser.add_argument('-ls', '--linked_id_string', default = None, help='String of Object ID to link')

    parser.add_argument('-D', '--default', default = False, action='store_true', help='Using default inputs for all.')

    return parser.parse_args()

### Main 
def main_upload(target, keywords, exclude, default, sim_type, extra, authenticate, verbose, large_files, linked_id_file, linked_id_string):
    ### Initial setup 
    output_folder = os.path.abspath(target)
    keywords = keywords

    if exclude is not None:
        exclude_folders = exclude.split(',')
        exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]
        print('Scanning will skip specified folders:\n {}\n'.format(exclude_folders) )
    else:
        exclude_folders = []
        
    if default in ['T', 'True', '1', 't', 'true']:
        default = True
        manual_time_flag = False

    else:
        default = False
        manual_time_flag = True
    
    ### Update global variables 
    global_vars = Global_vars(sim_type)    
    
    if extra: # this will change the global variable
        exfiles = input('Please type FULL file names to update, separated by comma.\n').split(',')
        exkeys  = input('Please type key names for each file you typed, separated by comma.\n').split(',')
        
        global_vars.Docs_ex +=exfiles
        global_vars.Keys_ex +=exkeys

    ### Connect to database 
    login = f_login_dbase(authenticate)
    database = login.connect()
    user = login.login['user']

    linked_id = f_get_linked_oid(database, linked_id_file, linked_id_string)

    ### Run uploader 
    #######################################################################
    print("Processing files for uploading ........")
    #scan through a directory for more than one run
    for count, (dirpath, dirnames, files) in enumerate(os.walk(output_folder)):
        if ( ( sim_type in ['CGYRO','TGLF','GS2'] and count==0)  or (sim_type=='GENE' and str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1 and str(dirpath) not in exclude_folders) ):    
            print('Scanning in {} *******************\n'.format( str(dirpath)) )
            linear = isLinear(dirpath, sim_type)
            if linear == None:
                linear_input = input('Cannot decide if this folder is a linear run or not. Please make the selection manually by typing:\n 1: Linear\n 2: Nonlinear \n 3: Skip this folder \n')
                if linear_input.strip() == '1':
                    linear = True
                elif linear_input.strip() == '2':
                    linear = False
                elif linear_input.strip() == '3':
                    print('Folder skipped.')
                    continue
                else:
                    exit('Invalid input encountered!')            
            if linear:
                lin = ['linear']
            else:
                lin = ['nonlin']

            #add linear/nonlin to keywords
            keywords_lin = keywords.split('#') + lin                                 
            
            if not default:
                suffixes = get_suffixes(dirpath, sim_type)
                print("Found in {} these suffixes:\n {}".format(dirpath, suffixes))
                
                suffixes = input('Which run do you want to upload? Separate them by comma. \n Press q to skip. Press ENTER to upload ALL.\n')
                if suffixes == 'q':
                    print("Skipping the folder {}.".format(dirpath))
                    continue
                elif len(suffixes):
                    suffixes = suffixes.split(',')
                else:
                    suffixes = None                              
                                            
                confidence = input('What is your confidence (1-10) for the run? Press ENTER to use default value -1.0\n')
                if len(confidence):
                    confidence = float(confidence)
                else:
                    confidence = -1.0
                    print("Using default confidence -1.\n")

                
                comments = input('Any comments for data in this folder?Press Enter to skip.\n')
                run_shared = input('Any other files to upload than the default? Separate them by comma. Press Enter to skip.\n')
                if len(run_shared):
                    run_shared = run_shared.split(',')
                else:
                    run_shared = None
            
            else:
                suffixes = None
                confidence = -1
                comments = 'Uploaded with default settings.'
                run_shared = None
            
            # Send run to upload_to_mongo to be uploaded
            upload_to_mongo(database, dirpath, user, linear, confidence, 
                            keywords_lin, comments, sim_type, linked_id, suffixes, run_shared,
                            large_files, extra, verbose, manual_time_flag,global_vars)

    if len(global_vars.troubled_runs):
        print("The following runs are skipped due to exceptions.")
        for r in global_vars.troubled_runs:
            print(r)

## Runner 
if __name__=="__main__":
    
    ### Parse arguments 
    args = f_parse_args()
    print(args)

    main_upload(**vars(args))
