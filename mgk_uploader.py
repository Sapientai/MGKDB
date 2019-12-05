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

########################################################################
#user_info = get_user_info()
#
#user =user_info["username"]
#pwd = user_info["password"]
#multiple_runs = user_info["multiruns"]
user = 'dykuang'

#output_folder = 'D:/test_data/data_nonlin_1'
output_folder = 'data_linear_multi'     ### Set as '.' for current directory ###
multiple_runs = False  ### Automate scanning through a directory of numerous runs ###


large_files = True # whether or not to include large_files: field, mom, vsp, ...
extra = False # whether or not to include user's specific files: fluxspectra, ...
verbose = False


if not multiple_runs:
    confidence = '5'     ### 1-10, 1: little confidence, 10: well checked ###
else:
    confidence = 'None'  ### Set if  same for all runs, else set as 'None' ###
    
input_heat = 'None'      ### Set if input heat is known, else set as 'None' ###
    
### enter any relevant keywords, i.e., ETG, ITG, pedestal, core ###
keywords = 'ETG, pedestal, GENE, '

#######################################################################
print("Processing files for uploading ........")
#scan through a directory for more than one run
if multiple_runs:
    #scan through directory for run directories
    dirnames = next(os.walk(output_folder))[1]
#    print(dirnames)
    for count, name in enumerate(dirnames, start=0):
        folder = os.path.join(output_folder, name)
#        if not os.path.isdir('in_par'):
        #check if run is linear or nonlinear
        print(folder)
        linear = isLinear(name)
        if linear:
            lin = 'linear'
        else:
            lin = 'nonlin'
        #add linear/nonlin to keywords
        keywords_lin = keywords + lin
        
        #send run list to upload_to_mongo to be uploaded
        upload_to_mongo(folder, user, linear, confidence, input_heat, keywords_lin, 
                        large_files, extra, verbose)
#        print("Data in {} Uploaded Successfully.".format(folder))

#submit a single run
else: 
    for dirpath, dirnames, files in os.walk(output_folder):
        if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1:
#            print(files)
            #check if run is linear or nonlinear
            linear = isLinear(output_folder)
            if linear:
                lin = 'linear'
            else:
                lin = 'nonlin'
            #add linear/nonlin to keywords
            keywords_lin = keywords + lin
#            print(keywords_lin)
            #send run to upload_to_mongo to be uploaded
            upload_to_mongo(output_folder, user, linear, confidence, input_heat, 
                            keywords_lin, large_files, extra, verbose)
#            print("The file {} Uploaded Successfully.".format(files))