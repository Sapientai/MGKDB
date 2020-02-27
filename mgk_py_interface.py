"""
Created on Wed Feb 26 15:08:36 2020

@author: dykuang

Make plots of some diagnostics
"""
from mgk_file_handling import load
import os
from mgk_login import mgk_login
import argparse
from sys import exit
from diag_plot import diag_plot
from bson.objectid  import ObjectId

#==========================================================
# argument parser
#==========================================================
parser = argparse.ArgumentParser(description='Plotting diagnositcs')

parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')

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
        


mgk_fusion = login.connect()

user = login.login['user']


def diag_plot_from_query(db, collection, query, projection={'Meta':1, 'Diagnostics':1}):

    data = load(db, collection, query, projection)
    if data is not None:
        n_records = len(data)
        print('{} records returned from your query.'.format(n_records) )
        
        p = [diag_plot(data[i]) for i in range(n_records)]
        
        for i in range(n_records):
            p[i].plot_all()
            print('Plotting found record {}'.format(i+1) )
            input('Press ENTER to continue ...')
    else:
        print('The database returns None for your query.')




