# Information for merging local database to the NERSC database 

Note: The following procedure changes the NERSC database directly, so please be very cautious before implementing it.

The recommended workflow for uploading data to MGKDB is using the python tools from a terminal at NERSC. This requires the data to be present on the file system at NERSC.

However, in case users have a large amount of data on some other machine and can't move it to NERSC, they can use the MGKDB tools to upload their data to a local DB and then merge it with the NERSC database. 
The following information is only relevant for users who want to build a local version of MGKDB and merge it with the NERSC database. This procedure is described below: 

## Testing locally: 
When performing this for the first time, it might be safer to test merging of two sample databases locally first. 
The sample code below implements this: 

##### Start local database and access it from the terminal
Access local database engine from the terminal (For details, please refer to [Local MGKDB](https://github.com/Sapientai/MGKDB/wiki/Local-MGKDB) page on the wiki page of this repository)

##### Create first database 
```use mgk_test1
db.createUser({ user: "u1", pwd: "p1", roles: [{ role: "dbOwner", db: "mgk_test1" }] })
```
##### Upload sample data using python CLI tools
`python mgk_uploader.py -T test_data/TGLF/ -SIM TGLF`

Response to prompts 
- `localhost,27017,mgk_test1,u1,p1`
- `<path_to_save_authentication_1.pkl>`
##### Create copy of DB 1
`mongodump --db mgk_test1 --out <path_to_db1>`

##### Create second database 
```use mgk_test2
db.createUser({ user: "u2", pwd: "p2", roles: [{ role: "dbOwner", db: "mgk_test2" }] })
```
##### Upload sample data using python CLI tools
`python mgk_uploader.py -T test_data/TGLF/ -SIM TGLF`

Reponse to prompts:
- `localhost,27017,mgk_test2,u2,p2`
- `<path_to_save_authentication_2.pkl>`
 
`python mgk_uploader.py -T test_data/test_gene1_tracer_efit -SIM GENE`

##### Merge database 1 to database 2
`mongorestore --db mgk_test3 --dir <path_to_db1>`

## Merging to NERSC database (Use with caution)
Steps to merge local database to the main NERSC database: 
1. From the terminal, create a dump of the local database: \
   ```mongodump --db mgk_local --out <target_destination>```
2. Move this data (which will be much smaller than the original data) to NERSC 
3. Login to NERSC
4. Login to database from the terminal with database credentials
```
module load mongodb/4.0.28
mongo -u <db_username> -p <db_password> mongodb03.nersc.gov/mgk_fusion
```
5. Merge local databse to the NERSC database using \
   ``` mongorestore --db mgk_fusion --dir <path_to_mongodump_output>```

