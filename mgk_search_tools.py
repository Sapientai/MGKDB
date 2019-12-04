# -*- coding: utf-8 -*-
"""
Created on Sat Oct  6 12:55:22 2018

@author: Austin Blackmon
"""

from pymongo import *

def find_in_mongo():
    print('What MGK key would you like to search?\n \
    1. user \n \
    2. run collection name \n \
    3. run suffix \n \
    4. keywords \n \
    5. other')
    key_num = int(input())
    if key_num == 1:
        key = "user"
    elif key_num == 2:
        key = "run_collection_name"
    elif key_num == 3:
        key = "run_suffix"
    elif key_num == 4:
        key = "keywords"
    elif key_num == 5:
        key = str(input())
    else:
        print('Please select an integer from 1-5!')
    search = str(input('Enter the value of "' + key + '" you would like to search: '))
    
    db = MongoClient().ETG
    runs = db.LinearRuns
    
    results = []
    result = runs.find({key : search})
    for doc in result:
        results.append(doc["run_collection_name"]+doc["run_suffix"])
    
    print(results)
    return(results)
