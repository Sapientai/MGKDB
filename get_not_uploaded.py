# -*- coding: utf-8 -*-
"""
Created on Sat Aug 29 15:42:12 2020

@author: dykua

a script for getting folder paths that are not uploaded
"""

from mgk_file_handling import not_uploaded_list
import os
from mgk_login import mgk_login
import argparse


parser = argparse.ArgumentParser(description='Process input.')

parser.add_argument('-T', '--target', help='Target GENE output folder to check.')
parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file.')
parser.add_argument('-L', '--linear', default = True, help='linear collections or nonlinear collections.')
parser.add_argument('-F', '--file', default = None, help='file to write to.')

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

database = login.connect()

user = login.login['user']

out_dir = os.path.abspath(args.target)

linear = args.linear

file = args.file

if args.linear in ['T', 'True', '1', 't', 'true']:
    linear = True
else:
    linear = False
    
if linear:
#    for folder in not_uploaded_list(out_dir, database.LinearRuns):
#        print(folder)
    not_uploaded_list(out_dir, database.LinearRuns, file)
else:
#    for folder in not_uploaded_list(out_dir, database.NonlinRuns):
#        print(folder)

    not_uploaded_list(out_dir, database.NonlinRuns, file)