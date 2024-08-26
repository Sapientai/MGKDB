# Information for merging local database to the NERSC database 

Note: The following information is only relevant for people who want to build a local version of MGKDB and merge it with the NERSC database. 
We recommend that you manually upload data from NERSC to the `mgk_fusion` database directly using the MGKDB python tools.
Since this procedure changes the NERSC database directly, please be very cautious before performing any such database merge.

Steps to merge local database to the main NERSC database: 
1. Create local database and upload data to it ( For details, refer to `Local MGKDB` page on this git wiki)
2. From the terminal, create a dump of the local database: ```mongodump --db mgk_local --out <target_destination>```
3. Move the data to NERSC 
4. Login to NERSC
5. From the terminal, restore to target database (NERSC database) ``` mongorestore --db mgk_fusion --dir <path_to_mongodump_output>```


