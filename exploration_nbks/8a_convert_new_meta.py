import sys
import os
import argparse
from sys import exit
import pprint
import pymongo

# from mgkdb import mgk_download
from mgkdb.support.mgk_login import mgk_login
from mgkdb.support.mgk_file_handling import f_set_metadata

def f_login_db(method,db_credentials=None,login_dict=None):
    
    assert method in ['login_file','direct']
    
    #### Method 1: MGKDB code login.py file  with repository and saved credentials from file db_credentials
    if method=='login_file': 
        
        login = mgk_login()
        try:
            login.from_saved(os.path.abspath(db_credentials))
        except OSError:
            exit("The specified credential file is not found!")

        client = login.connect()
        
        
    #### Method 2 : Directly access database with login credentials from login_dict
    elif method=='direct': 
        
        client = pymongo.MongoClient(login_dict['server'])[login_dict['dbname']]
        client.authenticate(login_dict['user'],login_dict['pwd'])
    
    return client

if __name__=="__main__":

    db_credentials='../../mgkdb_data/db_credentials/ayyarv.pkl'
    client = f_login_db('login_file',db_credentials,None)
    ## Test extract 
    print("Collections",client.list_collection_names())

    table='LinearRuns'
    # table='NonlinRuns'
    
    if table =='LinearRuns':        
        linear='linear'
        quasi_linear = False    
        collection = client['LinearRuns']
    elif table=='NonlinRuns':
        linear='nonlinear'
        quasi_linear = False    
        collection = client['NonlinRuns']
        
    all_ids = [r['_id'] for r in collection.find({},{'id':1})]
    print(all_ids)
    
    for oid in all_ids[:]:
    
        fltr = {"_id":oid}
        document = collection.find_one(fltr,{'Metadata':1,'_id':0})
        old_meta = document.get('Metadata')
        print(old_meta)

        ## Fix for cases when time_uploaded doesn't have underscore (mostly for nonlinear runs)
        if old_meta.get('time uploaded')!=None:
            time_upload = old_meta.get('time uploaded')
        elif old_meta.get('time_uploaded')!=None:
            time_upload = old_meta.get('time_uploaded')
        else: time_upload = None

        print(time_upload)

        # Create new metadata 
        new_meta = f_set_metadata(user=old_meta.get('user'), 
                    out_dir = old_meta.get('run_collection_name'),
                    suffix = old_meta.get('run_suffix'),
                    # keywords = old_meta.get('keywords'),
                    confidence = old_meta.get('confidence'),
                    comments = old_meta.get('comments'),
                    time_upload = time_upload,
                    last_update = old_meta.get('last_updated'),
                    linked_ID = old_meta.get('linked_ID'),
                    expt = old_meta.get('expt'),
                    shot_info = old_meta.get('shot_info'),
                    linear = linear,
                    quasiLinear = quasi_linear,
                    sim_type = old_meta.get('simulation_type'),
                    git_hash = old_meta.get('git_hash'),
                    platform = old_meta.get('platform'),
                    ex_date = old_meta.get('ex_date'),
                    workflow_type = old_meta.get('workflow_type'),
                    archive_loc = old_meta.get('archive_loc'),
                    )
        
        # Update entry 
        update = {"$set": {"Metadata": new_meta}}
        
        # # Perform the update
        # result = collection.update_one(fltr, update)
        
        # # Check if the update was successful
        # if result.matched_count > 0:
        #     print(f"Successfully added publication to {result.modified_count} document(s)")
        # else:
        #     print("No documents matched the filter criteria")

    print("all conversions completed")
    
    
