# Information for backing up on NERSC
Note: the following info is only intended for people managing MGKDB on NERSC. Regular users won't need to impement this.


## Step 1 : Creating backup  of the database 
- ssh to perlmutter
- module load mongodb/4.0.28
- mongodump --host "mongodb03.nersc.gov" -u <db_username> -p <db_password> --archive="<backup_location_folder>" --db=mgk_fusion

## Step 2: Writing to HPSS tape at NERSC
Further information (here)[https://docs.nersc.gov/filesystems/archive/#hsi]
- hsi
This logs you in to the HPSS command shell
- hsi put -R <backup_location_folder>

## Retriving data from HPSS 
- cd <location_on_file_system>
- hsi get -R <hpss_backup_folder> 

