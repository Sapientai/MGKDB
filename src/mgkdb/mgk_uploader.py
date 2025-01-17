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

from mgkdb.support.mgk_file_handling import get_suffixes, upload_to_mongo, isLinear, Global_vars, f_get_linked_oid, f_set_metadata
from mgkdb.support.mgk_login import mgk_login,f_login_dbase

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

def f_user_input_metadata():
    '''
    Create a dictonary of user inputs for metadata
    Used as keyword arguments to construct metadata dictionary
    '''

    user_ip = {} 
    print("Please provide input for metadata. Press Enter to skip.\n")

    confidence = input('What is your confidence (1-10) for the run? Press ENTER to use default value -1.0\n')
    if len(confidence):
        confidence = float(confidence)
    else:
        confidence = -1.0
        print("Using default confidence -1.\n")

    user_ip['confidence']= confidence 

    comments = input('Any comments for data in this folder?Press Enter to skip.\n')
    user_ip['comments'] = comments

    archive = input('Is there a location where the data is archived? Press Enter to skip.\n')
    user_ip['archive_loc'] = archive

    expt = input('Name of actual or hypothetical experiment? Eg: diiid, iter, sparc, etc. Press Enter to skip.\n')
    user_ip['expt'] = expt

    scenario_id = input('Scenario ID : shot ID or time or runID? Eg: 129913.1500ms . Press Enter to skip.\n')
    user_ip['scenario_runid'] = scenario_id

    git_hash = input('Do you have git-hash to store?Press Enter to skip.\n')
    user_ip['git_hash'] = git_hash

    platform = input('Platform on which this was run? Eg: perlmutter, summit, engaging, pc . Press Enter to skip.\n')
    user_ip['platform'] = platform

    exec_date = input('Execution date?Press Enter to skip.\n')
    user_ip['ex_date'] = exec_date

    workflow = input('Workflow type? Eg: portals, smarts, standalone, etc. Press Enter to skip.\n')
    user_ip['workflow_type'] = workflow

    print("Publication information should be uploaded with a separate script")

    return user_ip

### Main 
def main_upload(target, keywords, exclude, default, sim_type, extra, authenticate, verbose, large_files, linked_id_file, linked_id_string):
    ### Initial setup 
    output_folder = os.path.abspath(target)

    if exclude is not None:
        exclude_folders = exclude.split(',')
        exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]
        print('Scanning will skip specified folders:\n {}\n'.format(exclude_folders) )
    else:
        exclude_folders = []
    
    manual_time_flag = not default
    
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
                
                run_shared = input('Any other files to upload than the default? Separate them by comma. Press Enter to skip.\n')
                if len(run_shared):
                    run_shared = run_shared.split(',')
                else:
                    run_shared = None
                
                ### Metadata inputs 
                user_ip_dict = f_user_input_metadata()
                metadata = f_set_metadata(**user_ip_dict,user=user, keywords = keywords, sim_type=sim_type, linked_ID=linked_id)

            else:
                suffixes = None
                run_shared = None
            
                metadata = f_set_metadata(user=user, keywords=keywords, sim_type=sim_type,linked_ID=linked_id)

            # Send run to upload_to_mongo to be uploaded
            upload_to_mongo(database, linear, metadata, dirpath, suffixes, run_shared,
                            large_files, extra, verbose, manual_time_flag,global_vars)

    if len(global_vars.troubled_runs):
        print("The following runs are skipped due to exceptions.")
        for r in global_vars.troubled_runs:
            print(r)


def main():
    
    ### Parse arguments 
    args = f_parse_args()
    print(args)

    main_upload(**vars(args))


## Runner 
if __name__=="__main__":
    main()

