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
from bson.objectid import ObjectId

from mgkdb.support.mgk_file_handling import get_suffixes, upload_to_mongo, isLinear, Global_vars, f_get_linked_oid, f_set_metadata, f_check_id_exists, f_load_config
from mgkdb.support.mgk_login import mgk_login,f_login_dbase

import yaml 

def f_parse_args():
    #==========================================================
    # argument parser
    #==========================================================
    parser = argparse.ArgumentParser(description='Process input for uploading files')

    parser.add_argument('-T', '--target', help='Target run output folder')
    parser.add_argument('-SIM', '--sim_type', choices=['GENE','CGYRO','TGLF','GS2','GX'], type=str, help='Type of simulation', required=True)
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
    parser.add_argument('-C', '--config_file', default = None, help='Configuration file (.yaml) to avoid terminal prompts.')
    parser.add_argument('-D', '--default', default = False, action='store_true', help='Using default inputs for all.')
    parser.add_argument('-V', '--verbose', dest='verbose', default = False, action='store_true', help='output verbose')
    
    # parser.add_argument('-lf', '--linked_id_file', default = None, help='File with Object ID to link')
    # parser.add_argument('-ls', '--linked_id_string', default = None, help='String of Object ID to link')
    # parser.add_argument('-K', '--keywords', default = '-', help='relevant keywords for future references, separated by comma')
    parser.add_argument('-Ex', '--extra', dest='extra', default = False, action='store_true', help='whether or not to include extra files')
    parser.add_argument('-L', '--large_files', dest='large_files', default = False, action='store_true', help='whether or not to include large files')
    parser.add_argument('-X', '--exclude', default = None, help='folders to exclude')
    
    return parser.parse_args()

def f_user_input_metadata(database):
    '''
    Create a dictonary of user inputs for metadata
    Used as keyword arguments to construct metadata dictionary
    '''

    user_ip = {} 
    print("Filling metadata.")
    skip_metadata = input("To skip entering Metadata, please enter 0\n")
    if skip_metadata=='0': 
        return user_ip

    print("Please provide input for metadata. Press Enter to skip that entry.\n")
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

    restart = input('Is this run a restart starting from a different run? For yes -> Y .\n')

    user_ip['restart'] = (restart=='Y')

    if restart=='Y':
        user_ip['restart_timestep'] = int(input('What was the timestep of the previous run used to start this run?\n'))
        initial_run_info = input('Has the initial run been uploaded to this database. For yes -> Y .\n')
        run_oid = ObjectId(input('Please enter the ObjectID for that run\n')) if initial_run_info == 'Y' else None
        if f_check_id_exists(database, run_oid):
            user_ip['initial_run_oid'] =  run_oid 
        else:
            print(f"Entered object id {run_oid} doesn't exist\n")
            

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
def main_upload(target, exclude, default, sim_type, extra, authenticate, verbose, large_files, config_file):
    '''
    Upload a set of suffixes with common Metadata
    '''
    ### Initial setup 
    output_folder = os.path.abspath(target)
    global_vars = Global_vars(sim_type)    

    # manual_time_flag = not default
    manual_time_flag = False
    exclude_folders = []

    if config_file is not None: 
        config_dict = f_load_config(config_file)

        ## to do : Add check for format of config file

        user_ip = config_dict['user_input']    
        metadata_info = config_dict['metadata']
        shared_files = user_ip['shared_files']

        if user_ip['extra_files']:
            ex_files = user_ip['extra_files'].split(',')
            global_vars.Docs_ex +=ex_files

        if user_ip['exclude_folders'] is not None:
            ex_files = user_ip['exclude'].split(',')
            exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]

    else : 
        if exclude is not None:
            exclude_folders = exclude.split(',')
            exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]
            print('Scanning will skip specified folders:\n {}\n'.format(exclude_folders) )
        
        if extra: # this will change the global variable
            ex_files = input('Please type FULL file names to update, separated by comma.\n').split(',')
            global_vars.Docs_ex +=ex_files

    ### Connect to database 
    login = f_login_dbase(authenticate)
    client, database = login.connect()
    with client:
        user = login.login['user']

        ### Run uploader 
        #######################################################################
        print("Processing files for uploading ........")
        # #scan through a directory for more than one run
        # for count, (dirpath, dirnames, files) in enumerate(os.walk(output_folder)):
        #     condition = ( sim_type in ['CGYRO','TGLF','GS2','GX'] and count==0)  \
        #         or (sim_type=='GENE' and str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1 and str(dirpath) not in exclude_folders)
        #     if ( condition ):    
        dirpath = output_folder

        print('Scanning in {} *******************\n'.format( str(dirpath)) )
        linear = isLinear(dirpath, sim_type)                      
        all_suffixes = get_suffixes(dirpath, sim_type)
        if not all_suffixes:
            print("Did not find any suffixes in the folder",dirpath)
            return

        if not default:
            if config_file is not None: 
                ## Add suffixes
                ip_suffixes = user_ip['suffixes']
                if ip_suffixes: 
                    suffixes=ip_suffixes.split(',')
                    ## Check if input suffixes exist in the folder
                    incorrect_suffixes = [s1 for s1 in suffixes if s1 not in all_suffixes]
                    if incorrect_suffixes: 
                        print("The following suffixes provided don't exist in this folder")
                        print(f"Found in {dirpath} these suffixes:\n {all_suffixes}")
                        print('Skipping this folder')
                        # continue
                else:    suffixes = None

                ## Adding shared files info
                run_shared = shared_files.split(',') if shared_files else None
                
                ## Add metadata info
                metadata = metadata_info
                metadata['CodeTag']['sim_type']=sim_type
                linked_id_strg = metadata['DBTag']['linkedObjectID']
                if linked_id_strg is not None:
                    metadata['DBTag']['linkedObjectID'] = f_get_linked_oid(database, linked_id_strg)

            else: ## Get data through user input 
                
                print("Found in {} these suffixes:\n {}".format(dirpath, all_suffixes))
                
                suffixes = input('Which run do you want to upload? Separate them by comma. \n Press q to skip. Press ENTER to upload ALL.\n')
                if suffixes == 'q':
                    print("Skipping the folder {}.".format(dirpath))
                    # continue
                elif len(suffixes):
                    suffixes = suffixes.split(',')
                else:
                    suffixes = None                              
                
                run_shared = input('Do you want to upload any shared files for all suffixes? Please specify path relative to parent folder.\n Separate them by comma. Press Enter to skip.\n')
                if len(run_shared):
                    run_shared = run_shared.split(',')
                else:
                    run_shared = None

                linked_id_strg = input('Do you want to link this run to another existing run in MGKDB. Press Enter to skip\n')
                linked_id = f_get_linked_oid(database, linked_id_strg) if linked_id_strg else None

                keywords  = input('Any keywords to categorize this run. Press Enter to skip\n')

                ### Metadata inputs
                user_ip_dict = f_user_input_metadata(database)
                metadata = f_set_metadata(**user_ip_dict,user=user, keywords = keywords, sim_type=sim_type, linked_ID=linked_id)
        else:
            suffixes = None
            run_shared = None
            metadata = f_set_metadata(user=user, sim_type=sim_type)
        
        upload_to_mongo(database, linear, metadata, dirpath, suffixes, run_shared,
                        large_files, extra, verbose, manual_time_flag,global_vars)

    # if len(global_vars.troubled_runs):
    #     print("The following runs are skipped due to exceptions.")
    #     for r in global_vars.troubled_runs:
    #         print(r)


def main():
    
    ### Parse arguments 
    args = f_parse_args()
    print(args)

    main_upload(**vars(args))


## Runner 
if __name__=="__main__":
    main()

