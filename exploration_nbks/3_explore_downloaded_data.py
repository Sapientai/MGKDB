
## Sample code to explore data downloaded from the database 

import numpy as np
import datetime
import os
import glob 
import json 

import pymongo
import pprint
from bson.objectid import ObjectId



if __name__=="__main__":
    
    ## Read .json file 
    top_dir = '<dir_name>'
    fname = glob.glob(top_dir+'*.json')[0]
    print(fname)
    
    # Opening JSON file
    with open(fname, 'r') as f:
        data_dict = json.load(f)
    
    ## List all entry keys
    print(data_dict.keys())
    
    ## Explore gyrokinetics 
    print(data_dict['gyrokinetics'].keys())
    
    ## Print 
    print(data_dict['gyrokinetics']['species'])