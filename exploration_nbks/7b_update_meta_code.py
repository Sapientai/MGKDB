# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit

import gridfs
import json 
from bson.objectid import ObjectId

from mgkdb.support.mgk_login import mgk_login,f_login_dbase
from mgkdb.support.mgk_file_handling import f_set_metadata

# Run this as : 
# python exploration_nbks/7b_update_meta_code.py -A <fname.pkl> -C linear -m 3

def f_parse_args():
    parser = argparse.ArgumentParser(description='Update Metadata entries. 3 modes.  1: Append to publication list.\n2: Append to comments.\n 3: Update any specific entry. \n Modes 1 and 2 add entered values to existing entry.\nUse mode=3 with caution as you are rewriting previous entry.')

    parser.add_argument('-C', '--collection', choices=['linear','nonlinear'], default='linear', type=str, help='collection name in the database')
    parser.add_argument('-OID', '--objectID', default = '67891a84c3da391a06cf0af9', help = 'Object ID in the database')
    parser.add_argument('-m', '--mode', type=int, choices=[1,2,3], default = 3, help = 'Choose mode of operation for updating Metadata. 1: Append to publication list.\n2: Append to comments.\n 3: Update any specific entry.')
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')

    return parser.parse_args()


def f_metadata_template():
    ''' Create metadata dictionary template'''
    code_tag_keys = ['sim_type','git_hash','platform','execution_date','workflow_type']
    scenario_keys = ['NameOfActualOrHypotheticalExpt','shotOrTimeOrRunid']
    publication_keys = ['firstAuthor','journal','title','year','doi']
    top_keys = ['scenario_tag','Code_tag','archive_location','publications', \
                'user','run_suffix','run_collection_name','linked_objectID','confidence','comments','time_uploaded','last_updated']
    
    ## Warning : The code below assume two level dictionary only. For more levels, need to modify code ! 
    dict_template = {} 
    
    for key in top_keys:
        dict_template[key]={}
        default = ''
        if key =='Code_tag':
            for k2 in code_tag_keys:
                dict_template[key][k2] = default
        elif key =='scenario_tag':
            for k2 in scenario_keys:
                dict_template[key][k2] = default
        elif key =='publications':
            for k2 in publication_keys:
                dict_template[key][k2] = default
                
        else: 
            dict_template[key] = None

    return dict_template

def f_update_metadata(data, key_name, template_d):
    '''
    Update the existing metadata key entry 
    key_name : key to update 
    template_d : dictionary containing template
    '''
    if isinstance(data, dict):
        new_dict ={}
        for key,value in data.items():
            new_val = f_update_metadata(value, key, template_d)
            new_dict[key] = new_val

        return new_dict 
    
    elif isinstance(data, list):
        ## Create dictionary using last value 
        new_val = f_update_metadata(data[-1],key_name, template_d)
        
        return new_val

    else:
        print("The existing entry for this key is:\t%s"%(data))
        ## if entry is string, just replace
        new_value = input('Please enter the new entry you want for %s. If you don\'t want to proceed, enter : none \n'%(key_name))

        return new_value

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
    all_ids = [r['_id'] for r in collection.find({},{'id':1})]
    
    oid = ObjectId(args.objectID)
    ### Test code with oids read from full collection
    # oid = all_ids[0]

    assert oid in all_ids,"Given oid entry %s doesn't exist in database"%(oid)
    
    ### Extract document for this oid
    document = collection.find_one({"_id":oid},{'Metadata':1,'_id':0})

    ### Check user credential
    uname = login.login['user']
    input_usr = document['Metadata']['DBtag']['user']

    if uname!=input_usr:
        cont = input(f"Data was input by another use {input_usr}. Do you wish to continue ? y or n \n")
        if not cont=='y': 
            raise SystemExit
        
    keys = document.get('Metadata').keys()

    ### Options : Append to publications list, Append to comments, Update any specific entry
    if args.mode==1: 
        user_ip = input('Enter the value of the following entries, separated by commas: firstAuthor, journal, title, year, doi\n')
        ip = ['' for _ in range(3)]
        for idx,i in enumerate(user_ip.split(',')): ip[idx] = i
        publication_to_add = {'firstAuthor':ip[0], 'journal':ip[1], 'title':ip[2], 'year':ip[3], "doi": ip[4] }
        
        ## If entry is not a list, convert it to one with current entry as element 0 
        entry_val = document['Metadata']['Publications']
        if not isinstance(entry_val,list): 
            collection.update_one({"_id": oid},{"$set": {"Metadata.Publications": [entry_val]}})
        
        fltr = {"_id": oid}
        # Using $push to add to the list
        update = {"$push": {"Metadata.Publications": publication_to_add}}
        result = collection.update_one(fltr, update)
        print("Appended publication record")

    elif args.mode==2: # Option to append to comment string
        old_comment = document['Metadata']['DBtag']['comments']
        # assert isinstance(old_comment,str),f"Existing entry {old_comment} is not a string" 
        user_ip = input(f'Enter the string to append to current entry. Current entry is {old_comment} \n')
        
        fltr = {"_id": oid}
        # Using $set to add appended string to comments
        update = {"$set": {"Metadata.DBtag.comments": old_comment+'.\n'+user_ip}}
        result = collection.update_one(fltr, update)
        print("Appended comment")
        
    elif args.mode==3: 
        top_key = input(f'Please enter the key in Metadata that you want to update. Allowed options are: \n {keys}\n')
        assert top_key in keys,f"Invalid input key {top_key}"

        if top_key=='Publications':
            ans = document.get('Metadata').get(top_key)
            print("The existing entry for this key is:\t%s"%(ans))
            print("You will be resetting the entire value for this key. Please use caution")  

            dict_template = f_set_metadata()
            data = dict_template[top_key]
            new_value = f_update_metadata(data,top_key, dict_template)

        else: 
            sub_keys = document.get('Metadata').get(top_key).keys()
            key_name = input(f'The key {top_key} has the following subkeys {sub_keys}. \nPlease select which subkey you want to modify\n')
            assert key_name in sub_keys,f"Invalid input key {key_name}"

            ans = document.get('Metadata').get(top_key).get(key_name)
            print("The existing entry for this key is:\t%s"%(ans))
            print("You will be resetting the entire value for this key. Please use caution")  

            dict_template = f_set_metadata()
            data = dict_template[top_key][key_name]
            new_value = f_update_metadata(data,key_name, dict_template)
        
        confirm = input(f'Confirm changing entry to {new_value}? Enter Y or N\n').strip().upper()

        ## Some entries need to be in a list 
        if top_key in ['Publications']:
            new_value = [new_value]

        if (confirm!='Y' or (new_value == 'none')):
            print('Didn not receive confirmation. Aborting update')
            raise SystemExit
            
        fltr = {"_id": oid}
        update = {"$set": {f"Metadata.{top_key}.{key_name}": new_value}}
        result = collection.update_one(fltr, update)

        document = collection.find_one({"_id":oid},{'Metadata':1,'_id':0})
        print('Updated entry: %s '%(document.get('Metadata').get(top_key).get(key_name)))    


