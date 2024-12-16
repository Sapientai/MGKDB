# Code to download all non-linear runs in database 

import sys
import os
import argparse
from sys import exit

from mgkdb import mgk_download
from mgkdb.support.mgk_login import mgk_login,f_login_dbase


# Run this as : 
# python template_download_all.py -A <.pkl> -C nonlinear -D <download_location>


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
    for count,oid in enumerate(all_ids[5:20]):
        
        ### Create parent directory for each run. 
        fldr = '%s_%s'%(count,str(oid))   # Add counter as prefix to folder name 
        destination = os.path.join(args.destination,fldr)
        os.makedirs(destination)
        print(oid, destination)
        
        #### Download
        mgk_download.main_download(None, None, oid, destination, None, None, args.authenticate, args.collection)
        

