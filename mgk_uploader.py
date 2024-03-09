# -*- coding: utf-8 -*-
"""
Main script to handle uploading GENE runs to the MGK database
Required fields:    user
                    output_folder
                    multiple_runs (True or False)
                    
Optional fields:    confidence
                    input_heat
                    keywords
                    
@author: Austin Blackmon, Dongyang Kuang
"""

import sys
sys.path.append('support')

#from mgk_file_handling import *
from mgk_file_handling import get_suffixes, upload_to_mongo, isLinear, Docs_ex, Keys_ex, _troubled_runs
#from ParIO import *
import os
from mgk_login import mgk_login
import argparse
from sys import exit

########################################################################
#user_info = get_user_info()
#
#user =user_info["username"]
#pwd = user_info["password"]
#multiple_runs = user_info["multiruns"]
#user = 'dykuang'
#
##output_folder = 'D:/test_data/data_nonlin_1'
#output_folder = 'data_linear_multi'     ### Set as '.' for current directory ###
#multiple_runs = False  ### Automate scanning through a directory of numerous runs ###
#
#
#large_files = True # whether or not to include large_files: field, mom, vsp, ...
#extra = False # whether or not to include user's specific files: fluxspectra, ...
#verbose = False
#
#
#if not multiple_runs:
#    confidence = '5'     ### 1-10, 1: little confidence, 10: well checked ###
#else:
#    confidence = 'None'  ### Set if  same for all runs, else set as 'None' ###
#    
#input_heat = 'None'      ### Set if input heat is known, else set as 'None' ###
#    
#### enter any relevant keywords, i.e., ETG, ITG, pedestal, core ###
#keywords = 'ETG, pedestal, GENE, '


#==========================================================
# argument parser
#==========================================================
parser = argparse.ArgumentParser(description='Process input for uploading files')

parser.add_argument('-T', '--target', help='Target GENE output folder')
parser.add_argument('-H', '--input_heat', default = 'None', help='input heat')
parser.add_argument('-L', '--large_files', default = False, help='where or not to inclulde large files: field, mom, vsp')
parser.add_argument('-Ex','--extra', default = False, help='whether or not to include extra files')
parser.add_argument('-V', '--verbose', default = False, help='output verbose')
#parser.add_argument('-M', '--multiple_runs', default = 'F', help='output verbose')
#parser.add_argument('-C', '--confidence', default = '5', help='confidence of simulation')
parser.add_argument('-K', '--keywords', default = 'GENE', help='relevant keywords for future references, separated by comma')
parser.add_argument('-SIM', '--sim_type', choices=['GENE','CGYRO'], type=str, help='Type of simulation', required=True)
parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
parser.add_argument('-X', '--exclude', default = None, help='folders to exclude')
parser.add_argument('-Img', '--image_dir', default = './mgk_diagplots', help='folders to save temporal image files.')
#parser.add_argument('-S', '--suffixes', default = None, help='Only select specific suffixes to upload.')

parser.add_argument('-D', '--default', default = False, help='Using default inputs for all.')

args = parser.parse_args()

output_folder = os.path.abspath(args.target)
#if args.multiple_runs in ['T', 'True', '1', 't', 'true']:
#    multiple_runs = True
#else:
#    multiple_runs = False
    
#if args.suffixes is not None:
#    suffixes = args.suffixes.split(',')
#else:
#    suffixes = args.suffixes

keywords = args.keywords
input_heat = args.input_heat

img_dir = os.path.abspath(args.image_dir)

if args.large_files in ['T', 'True', '1', 't', 'true']:
    large_files = True
else:
    large_files = False

if args.extra in ['T', 'True', '1', 't', 'true']:
    extra = True
else:
    extra = False

if args.verbose in ['T', 'True', '1', 't', 'true']:
    verbose = True
else:
    verbose = False
    
if args.exclude is not None:
    exclude_folders = args.exclude.split(',')
    exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]
    print('Scanning will skip specified folders:\n {}\n'.format(exclude_folders) )
else:
    exclude_folders = []
    
if args.default in ['T', 'True', '1', 't', 'true']:
    default = True
    manual_time_flag = False

else:
    default = False
    manual_time_flag = True
    
sim_type = args.sim_type
print(sim_type)

#confidence = args.confidence
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
        
if extra: # this will change the global variable
    exfiles = input('Please type FULL file names to update, separated by comma.\n').split(',')
    exkeys  = input('Please type key names for each file you typed, separated by comma.\n').split(',')
    
    Docs_ex += exfiles
    Keys_ex += exkeys


database = login.connect()

user = login.login['user']

#######################################################################
print("Processing files for uploading ........")
#scan through a directory for more than one run

# =============================================================================
# if multiple_runs:
#     print('Scanning in {} *******************\n'.format(output_folder) )
# #    try:
#     linear = isLinear(output_folder)
#     if linear == None:
#         linear_input = input('Cannot decide if this folder is a linear run or not. Please make the selection manually by typing:\n 1: Linear\n 2: Nonlinear \n 3: Skip this folder \n')
#         if linear_input.strip() == '1':
#             linear = True
#         elif linear_input.strip() == '2':
#             linear = False
#         elif linear_input.strip() == '3':
#             print('Folder skipped.')
#         else:
#             exit('Invalid input encountered!')
#             
#     if linear:
#         lin = ['linear']
#     else:
#         lin = ['nonlin']
#     keywords_lin = keywords.split('#') + lin
#                                   
#     suffixes = get_suffixes(output_folder)
#     print("Found in {} these suffixes:\n {}".format(output_folder, suffixes))
#     
#     suffixes = input('Which run do you want to upload? Separate them by comma. \n Press q to skip. Press ENTER to upload ALL.\n')
#     if suffixes == 'q':
#         print("Skipping the folder {}.".format(output_folder))
#     
#     else:
#         if len(suffixes):
#             suffixes = suffixes.split(',')
#         else:
#             suffixes = None                              
#     
#         confidence = input('What is your confidence (1-10) for the run? Press ENTER to use default value -1.0\n')
#         if len(confidence):
#             confidence = float(confidence)
#         else:
#             confidence = -1.0
#             print("Using default confidence -1.0.\n")
#         
#         comments = input('Any comments for data in this folder?Press Enter to skip. \n')
#         
#         upload_to_mongo(database, output_folder, user, linear, confidence, input_heat, 
#                         keywords_lin, comments, img_dir, suffixes,
#                         large_files, extra, verbose)
# #    except Exception as ex:
# #        print('Exception encountered.\n')
# #        print(ex)
# #        print('{} skipped!'.format(output_folder))
#         
#     #scan through directory for run directories
#     dirnames = next(os.walk(output_folder))[1]
# #    print(dirnames)
# #    if len(exclude_folders):
# #        dirnames[:] = [d for d in dirnames if d not in exclude_folders]
# #        print(dirnames)
#     for count, name in enumerate(dirnames, start=0):
#         folder = os.path.join(output_folder, name)
#         if folder in exclude_folders:
#             print('Skipping folder {}...'.format(folder))
#         else:
#             print('Scanning in {} *******************\n'.format(folder) )
# #            try:
#             linear = isLinear(folder)
#             if linear == None:
#                 linear_input = input('Cannot decide if this folder is a linear run or not. Please make the selection manually by typing:\n 1: Linear\n 2: Nonlinear \n 3: Skip this folder \n')
#                 if linear_input.strip() == '1':
#                     linear = True
#                 elif linear_input.strip() == '2':
#                     linear = False
#                 elif linear_input.strip() == '3':
#                     print('Folder skipped.')
#                     continue
#                 else:
#                     exit('Invalid input encountered!')
#                     
#             if linear:
#                 lin = ['linear']
#             else:
#                 lin = ['nonlin']
#             #add linear/nonlin to keywords
# #                keywords_lin = keywords.split(',') + lin
#             keywords_lin = keywords.split('#') + lin
#                                           
#             suffixes = get_suffixes(folder)
#             print("Found in {} these suffixes:\n {}".format(folder, suffixes))
#             
#             suffixes = input('Which run do you want to upload? Separate them by comma. \n Press q to skip. Press ENTER to upload ALL.\n')
#             if suffixes == 'q':
#                 print("Skipping the folder {}.".format(folder))
#                 continue
#             elif len(suffixes):
#                 suffixes = suffixes.split(',')
#             else:
#                 suffixes = None                              
# 
#             confidence = input('What is your confidence (1-10) for the run? Press ENTER to use default value -1.0\n')
#             if len(confidence):
#                 confidence = float(confidence)
#             else:
#                 confidence = -1.0
#                 print("Using default confidence -1.0.\n")
#             
#             #send run list to upload_to_mongo to be uploaded
#             comments = input('Any comments for data in this folder?Press Enter to skip. \n' )
# 
#             upload_to_mongo(database, folder, user, linear, confidence, input_heat, keywords_lin, comments,
#                             img_dir, suffixes,
#                             large_files, extra, verbose)
# #            except Exception as ex:
# #                print('Exception encountered.\n')
# #                print(ex)
# #                print('{} skipped!'.format(folder))
# #                continue
# #        print("Data in {} Uploaded Successfully.".format(folder))
# 
# else: 
# =============================================================================
for dirpath, dirnames, files in os.walk(output_folder):
    if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1 and str(dirpath) not in exclude_folders:    
        print('Scanning in {} *******************\n'.format( str(dirpath)) )
        #check if run is linear or nonlinear
        #print(str(dirpath))
#            try:
        linear = isLinear(dirpath)
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
        #print(linear)
        if linear:
            lin = ['linear']
        else:
            lin = ['nonlin']
        #add linear/nonlin to keywords
                    
#                keywords_lin = keywords.split(',') + lin
        #print(keywords_lin)
        #print(linear)
        keywords_lin = keywords.split('#') + lin
                                      
        if not default:
            suffixes = get_suffixes(dirpath)
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
        #send run to upload_to_mongo to be uploaded
        upload_to_mongo(database, dirpath, user, linear, confidence, input_heat, 
                        keywords_lin, comments, sim_type, img_dir, suffixes, run_shared,
                        large_files, extra, verbose, manual_time_flag)
#            except Exception as ex:
#                print('Exception encountered.\n')
#                print(ex)
#                print('{} skipped!'.format(dirpath))
#                continue
            
#            print("The file {} Uploaded Successfully.".format(files))
if len(_troubled_runs):
    print("The following runs are skipped due to exceptions.")
    for r in _troubled_runs:
        print(r)
