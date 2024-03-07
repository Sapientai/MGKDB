# **MGKDB**
========

On this page:  

* [Test it locally](#markdown-test-it-locally)  

* [Test it on Cori](#markdown-header-test-it-on-cori)  

---
## Test DB  locally
You can build and interact with the database via at least 3 methods:  
   * [Mongo Shell](https://docs.mongodb.com/manual/mongo/)  
   * [Pymongo](https://api.mongodb.com/python/current/api/index.html)  
   * The GUI, such as MongoDB Compass.  

Please refer to this [Wiki](https://github.com/Sapientai/MGKDB/wiki/MGKDB-at-NERSC) for step-by-step instructions on building MGKDB locally

## Connecting to MGKDB on NERSC
Users can interact with the database in 3 ways: 

### Using Command Line tools
Command line tools can be used to download data from the database and upload data to the database.

1. Clone the repo : `git@github.com:Sapientai/MGKDB.git`  
2. Load python3 :  `module load python3` 

##### Supplying Credentials
When using these command line scripts, users will need to provide credentials to access the database in one of two ways:  
* Provide a .pkl file with credentials \
or \
* Enter the credentials manually
Here is a sample string : (server location,port,database name,username,password)
`mongodb03.nersc.gov,27017,mgk_fusion,<db_username>,<db_password> `

* If you save the credentials file, you can use it subsequently with the `-A` option 
#### Retrieving files from database    
For downloads, users need to execute the script `mgk_download.py`. 

* Save the file with tag ObjectId(5e150c312038695f1da2e956) to *directory/newname*  
`python3 MGKDB/mgk_download.py -A <user_credentials.pkl> -OID 5e150c312038695f1da2e956 -D directory -S newname`  

The directory will be created if it does not exist.

#### Upload to database : 
For uploads, users need to execute the script `mgk_upload.py`. 

Run the uploader by `python3 mgk-dev/mgk_uploader.py -T /global/homes/d/dykuang/mgk-dev/data_linear_multi`.  Option -T is for specifying your target folder. Use option --help for display other options information.  

### Directly using the terminal
Another method to interact with the database is directly from the terminal
1. From a terminal, `ssh` to Perlmutter using `ssh -l <nersc_username> perlmutter.nersc.gov`.
2. Connect to the database using : 
```
module load mongodb/4.0.28
mongo -u <db_username> -p <db_password> mongodb03.nersc.gov/mgk_fusion
```
3. Now, one can use `db` commands.

Please refer to this [Wiki](https://github.com/Sapientai/MGKDB/wiki/MGKDB-at-NERSC) for step-by-step instructions for these

### GUI : Using MongoDB Compass
* On your laptop terminal, forward the ssh tunnel port to a local port : ssh -i .ssh/nersc -f <nersc_username>@perlmutter.nersc.gov -L 2222:mongodb03.nersc.gov:27017 -N . You can use any other port instead of 2222 above. You will be asked to provide login credentials on perlmutter for this.
* Now in the MongoDB Compass application, paste the following connection string (add your database username and password appropriately) in the URL block: * mongodb://<db_username>:<db_password>@localhost:2222/?authSource=mgk_fusion&readPreference=primary&directConnection=true&ssl=false
* Click connect
* Once you're logged in, you can click on mgk_fusion on the left side panel to view the database

### Caution:
* If you have Read/Write access to the database, be careful while using mongodb compass, you may accidently modify the database.  
