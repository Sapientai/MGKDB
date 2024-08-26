# Information for merging local database to the NERSC database 

Note: The following procedure changes the NERSC database directly, so please be very cautious before implementing it.

The recommended workflow for uploading data to MGKDB is using the python tools from a terminal at NERSC. This requires the data to be present on the file system at NERSC.


However, in case users have a large amount of data on some other machine and can't move it to NERSC, they can use the MGKDB tools to upload their data to a local DB and then merge it with the NERSC database. 
The following information is only relevant for users who want to build a local version of MGKDB and merge it with the NERSC database. This procedure is described below: 

Steps to merge local database to the main NERSC database: 
1. Create local database and upload data to it ( For details, refer to [Local MGKDB](https://github.com/Sapientai/MGKDB/wiki/Local-MGKDB) page on the wiki page of this repository)
2. From the terminal, create a dump of the local database: ```mongodump --db mgk_local --out <target_destination>```
3. Move this data (which will be much smaller than the original data) to NERSC 
4. Login to NERSC
5. From the terminal, restore to target database (NERSC database) ``` mongorestore --db mgk_fusion --dir <path_to_mongodump_output>```


