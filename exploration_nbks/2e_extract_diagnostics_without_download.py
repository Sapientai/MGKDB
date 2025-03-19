# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit
from bson.objectid import ObjectId

import gridfs
import json 
import numpy as np

from mgkdb import mgk_download
from mgkdb.support.mgk_login import mgk_login,f_login_dbase
from mgkdb.support.mgk_file_handling import get_oid_from_query, Str2Query, download_dir_by_name, download_file_by_path, download_file_by_id, download_runs_by_id


# Run this as : 
# python 2e_extract_diagnostics_without_download.py -A <.pkl> -C linear -D <download_location>

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
    
    all_ids = [r['_id'] for r in collection_name.find(query_dict,{'id':1}).limit(30)]
    print("Number of collections", len(all_ids))

    # # Loop over oids and download with download module
    for count,oid in enumerate(all_ids[:2]):
        try : 

            ## Extract dictionary 
            # fs = gridfs.GridFSBucket(database)
            record = collection_name.find_one({ "_id": oid })
            print(record.keys())

            fs = gridfs.GridFS(database)
            file_oid = record['Files']['fingerprints_csv'] ## filenames with . are converted to _ during MGKDB upload

            out = fs.get(file_oid).read().decode('utf-8')

            ## Test conversion to numpy array 
            arr = np.array([j.split(',') for j in [i for i in out.split('\n') if i]])
            print(arr)

        except Exception as e: 
            print(e)
            print("unsuccessful for %s"%(oid))
