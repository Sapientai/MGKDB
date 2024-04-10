# Information for backing up on NERSC
Note: the following info is only intended for people managing MGKDB on NERSC. Regular users won't need to impement this.

## Creating backup 
- ssh to perlmutter
- module load mongodb/4.0.28
- mongodump --host "mongodb03.nersc.gov" -u <db_username> -p <db_password> --archive="<backup_location_folder>" --db=mgk_fusion

## Writing to HPSS 
Further information at 


## Retriving data from HPSS 
 

