# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:03:11 2020

@author: dykua

A shell script to clear 'ex.Lin' and 'ex.Nonlin'
"""

from mgk_file_handling import clear_ex_lin, clear_ex, clear_ex_Nonlin
import os
from mgk_login import mgk_login
import argparse
from sys import exit

#==========================================================
# argument parser
#==========================================================
parser = argparse.ArgumentParser(description='Process input for uploading files')

parser.add_argument('-C', '--collection', default = 'both', help='collection to clear: ex.Lin, ex.Nonlin or both')
parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')

args = parser.parse_args()


confidence = args.collection
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

if args.verbose in ['l', 'L', 'linear', 'Linear', 'lin', 'Lin']:
    clear_ex_lin(database)
elif args.verbose in ['n', 'N', 'nonlinear', 'Nonlinear', 'non', 'Non']:
    clear_ex_Nonlin(database)
elif args.verbose in ['b', 'B', 'Both', 'both']:
    clear_ex()
else:
    print("Invalid input, please double check your argument.")

