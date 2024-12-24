# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit

import gridfs
import json 
from bson.objectid import ObjectId

from mgkdb.support.mgk_login import mgk_login,f_login_dbase

# Run this as : 
# python 2b_template_download_all_nonlinear_specific_files.py -A <.pkl> -C nonlinear -D <download_location>

def f_parse_args():
    parser = argparse.ArgumentParser(description='Update Metadata entries')

    parser.add_argument('-C', '--collection', choices=['linear','nonlinear'], default='linear', type=str, help='collection name in the database')
    parser.add_argument('-OID', '--objectID', default = None, help = 'Object ID in the database')
    parser.add_argument('-m', '--mode', type=int, choices=[1,2,3], default = 1, help = 'Choose mode of operation for updating Metadata. 1: Append to publication list.\n2: Append to comments.\n 3: Update any specific entry.')
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')

    return parser.parse_args()


if __name__=="__main__":
    
    ### Parse arguments 
    args = f_parse_args()
    Args = vars(args)
    
    authenticate = Args['authenticate']
    collection_ip = Args['collection']
    
    ### Connect to database 
    login = f_login_dbase(authenticate)
    database = login.connect()

    #### Dict to convert from argument to collection name in database
    collection_dict={'linear':'LinearRuns','nonlinear':'NonlinRuns','files':'fs.files'}
    collection =  getattr(database,collection_dict[collection_ip])
    
    # Get Object IDs 
    # oid = ObjectId(args.objectID)
    all_ids = [r['_id'] for r in collection.find({},{'id':1})]
    oid = all_ids[0]
    assert oid in all_ids,"Given oid entry %s doesn't exist in database"%(oid)
    
    ### Extract document for this oid
    document = collection.find_one({"_id":oid},{'Metadata':1,'_id':0})
    keys = document.get('Metadata').keys()

    ### Options : Append to publications list, Append to comments, Update any specific entry
    if args.mode==1: 
        user_ip = input('Enter the value of the following entries, separated by commas: title, year, doi\n')
        ip = ['' for _ in range(3)]
        for idx,i in enumerate(user_ip.split(',')): ip[idx] = i
        publication_to_add = {"article": {'title':ip[0],'year':ip[1]}, "doi": ip[2]}
        
        ## If entry is not a list, convert it to one with current entry as element 0 
        entry_val = document['Metadata']['publications']
        if not isinstance(entry_val,list): 
            collection.update_one({"_id": oid},{"$set": {"Metadata.publications": [entry_val]}})
        
        fltr = {"_id": oid}
        # Using $push to add to the list
        update = {"$push": {"Metadata.publications": publication_to_add}}
        result = collection.update_one(fltr, update)
        print("Updated publication record")

    elif args.mode==2:
        pass
        
    elif args.mode==3: 
        key_name = input(f'Please enter the key in Metadata that you want to update. Allowed options are: \n {keys}\n')
        assert key_name in keys,f"Invalid input key {key_name}"

        ans = document.get('Metadata').get(key_name)
        print("The existing entry for this key is:\t%s"%(ans))
        print("You will be resetting the entire value for this key. Please use caution")  
        new_value = input('Please enter the new entry you want to append to %s. If you don\'t want to proceed, enter : none \n'%(key_name))
        confirm = input(f'Confirm changing entry to {new_value}? Enter Y or N\n')
        
        if ((not confirm) or (new_value == 'none')):
            print('Received "none" string. Aborting update')
            raise SystemExit
            
        fltr = {"_id": oid}
        update = {"$set": {f"Metadata.{key_name}": new_value}}
        result = collection.update_one(fltr, update)

        document = collection.find_one({"_id":oid},{'Metadata':1,'_id':0})
        print('Updated entry: %s '%(document.get('Metadata').get(key_name)))    
        print('test')


