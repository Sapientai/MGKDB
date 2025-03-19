# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit
from bson.objectid import ObjectId

import gridfs
import json 

from mgkdb import mgk_download
from mgkdb.support.mgk_login import mgk_login,f_login_dbase
from mgkdb.support.mgk_file_handling import get_oid_from_query, Str2Query, download_dir_by_name, download_file_by_path, download_file_by_id, download_runs_by_id


# Run this as : 
# python 2d_template_download_linear_fields.py -A <.pkl> -C linear -D <download_location>


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
    # query_dict = {"gyrokineticsIMAS.species.1.density_norm": {"$gte": 1, "$lte": 2.1}}
    # query_dict = {'gyrokineticsIMAS.flux_surface.q':{"$gte": 2.0, "$lte": 2.1}}
    query_dict = {}
    
    all_ids = [r['_id'] for r in collection_name.find(query_dict,{'id':1}).limit(300)]
    print("Number of collections", len(all_ids))

    # # Loop over oids and download with download module
    for count,oid in enumerate(all_ids[:200]):
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
            suffix = record['Metadata']['DBtag']['run_suffix']

            # Save the field file in diagnostics
            if 'field' in record['Diagnostics'].keys(): 
                op_fname = 'field'+ suffix
                file_id = record['Diagnostics']['field']
                download_file_by_id(database, file_id, destination, op_fname, session = None)

            ## Save all other input files 
            for key,val in record['Files'].items():
                # if val !='None':
                if isinstance(val,ObjectId):
                    print(key)
                    op_fname = key+suffix
                    file_id = val
                    download_file_by_id(database, file_id, destination, op_fname, session = None)

            print("Successfully downloaded run %s to the directory %s " % (oid,destination))
        except Exception as e: 
            print(e)
            print("unsuccessful for %s"%(oid))
