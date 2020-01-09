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

from mgk_file_handling import *
from ParIO import *
import os
from gui_utils import *
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
parser.add_argument('-M', '--multiple_runs', default = False, help='output verbose')
parser.add_argument('-C', '--confidence', default = '5', help='confidence of simulation')
parser.add_argument('-K', '--keywords', default = 'GENE', help='relevant keywords for future references, separated by comma')
parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')

args = parser.parse_args()

output_folder = os.path.abspath(args.target)
if args.multiple_runs in ['T', 'True', '1', 't', 'true']:
    multiple_runs = True
else:
    multiple_runs = False

keywords = args.keywords
input_heat = args.input_heat

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


confidence = args.confidence
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
        exit("The specified file is not found")
        
if extra:
    exfiles = input('Please type FULL file names to update, separated by comma.\n').split(',')
    exkeys  = input('Please type key names for each file you typed, separated by comma.\n').split(',')
    
    Docs_ex += exfiles
    Keys_ex += exkeys


database = login.connect()

user = login.login['user']

#######################################################################
print("Processing files for uploading ........")
#scan through a directory for more than one run
if multiple_runs:
    #scan through directory for run directories
    dirnames = next(os.walk(output_folder))[1]
#    print(dirnames)
    for count, name in enumerate(dirnames, start=0):
        folder = os.path.join(output_folder, name)
        print('Scanning in {} *******************\n'.format(folder) )
#        if not os.path.isdir('in_par'):
        #check if run is linear or nonlinear
        #print(folder)
        linear = isLinear(name)
        if linear:
            lin = ['linear']
        else:
            lin = ['nonlin']
        #add linear/nonlin to keywords
        keywords_lin = keywords.split(',') + lin
        
        #send run list to upload_to_mongo to be uploaded
        upload_to_mongo(database, folder, user, linear, confidence, input_heat, keywords_lin, 
                        large_files, extra, verbose)
#        print("Data in {} Uploaded Successfully.".format(folder))

#submit a single run
else: 
    for dirpath, dirnames, files in os.walk(output_folder):
        if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1:    
            print('Scanning in {} *******************\n'.format(str(dirpath)) )
            #check if run is linear or nonlinear
            linear = isLinear(output_folder)
            if linear:
                lin = ['linear']
            else:
                lin = ['nonlin']
            #add linear/nonlin to keywords
            keywords_lin = keywords.split(',') + lin
#            print(keywords_lin)
            #send run to upload_to_mongo to be uploaded
            upload_to_mongo(database, dirpath, user, linear, confidence, input_heat, 
                            keywords_lin, large_files, extra, verbose)
#            print("The file {} Uploaded Successfully.".format(files))
