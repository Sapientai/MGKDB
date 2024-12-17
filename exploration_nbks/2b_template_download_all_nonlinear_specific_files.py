# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit

import gridfs
import json 

from mgkdb import mgk_download
from mgkdb.support.mgk_login import mgk_login,f_login_dbase
from mgkdb.support.mgk_file_handling import get_oid_from_query, Str2Query, download_dir_by_name, download_file_by_path, download_file_by_id, download_runs_by_id


# Run this as : 
# python 2b_template_download_all_nonlinear_specific_files.py -A <.pkl> -C nonlinear -D <download_location>


if __name__=="__main__":
    
    ### Parse arguments 
    args = mgk_download.f_parse_args()
    Args = vars(args)
    
    authenticate = Args['authenticate']
    collection = Args['collection']
    
    ### Connect to database 
    login = f_login_dbase(authenticate)
    database = login.connect()

    #### Dict to convert from argument to collection name in database
    collection_dict={'linear':'LinearRuns','nonlinear':'NonlinRuns','files':'fs.files'}
    collection_name =  getattr(database,collection_dict[collection])
    
    # Get Object IDs 
    all_ids = [r['_id'] for r in collection_name.find({},{'id':1})]
    print("Number of collections", len(all_ids))

    # Loop over oids and download with download module
    for count,oid in enumerate(all_ids[:]):
        try : 
            ### Create parent directory for each run. 
            fldr = '%s_%s'%(count,str(oid))   # Add counter as prefix to folder name 
            destination = os.path.join(args.destination,fldr)
            os.makedirs(destination, exist_ok=True)
            print(oid, destination)
            
            ## Extract dictionary 
            fs = gridfs.GridFSBucket(database)
            record = collection_name.find_one({ "_id": oid })
            print(record.keys())
            suffix = record['Metadata']['run_suffix']

            ## Fix to save GENE specific input file 
            if 'nrg' in record['Files'].keys(): 
                op_fname = 'nrg'+ suffix
                file_id = record['Files']['nrg']
                download_file_by_id(database, file_id, destination, op_fname, session = None)

            ## Download IMAS dict
            record['_id'] = str(record['_id'])
            if 'gyrokineticsIMAS' in record.keys(): 
                modified_dict = {k:record[k] for k in ['_id','Metadata','gyrokineticsIMAS']}
                with open(os.path.join(destination, 'mgkdb_summary_for_run'+ suffix +'.json'), 'w') as f:
                    json.dump(modified_dict, f)
            else: 
                print('No gyrokineticsIMAS field found for run %s'%(oid))

            print("Successfully downloaded run %s to the directory %s " % (oid,destination))
        except Exception as e: 
            print(e)
            print("unsuccessful for %s"%(oid))
