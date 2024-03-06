# **MGKDB**
========

On this page:  

* [Test it locally](#markdown-header-play-it-locally)  

* [Test it on Cori](#markdown-header-test-it-on-cori)  
    * [Use command line](#markdown-header-test-it-on-cori)  
    * [Retrieving files from database](#markdown-header-retrieving-files-from-database)

---


## Test DB  locally

1. Download [MongoDB](https://www.mongodb.com/what-is-mongodb) and install it according to the [documentation](https://docs.mongodb.com/manual/administration/install-community/). If you would also like a gui, you can also download [MongoDB Compass](https://www.mongodb.com/products/compass)

2. If successfully installed, you are probably now in mongo shell environment. You can now create a local database (For test) by   
```
   use mgk_fusion  ----- % create an empty database with name 'mydb'   

   db.createUser(   
    {   
     user: "username",  % create user name  
     pwd: "password", % create user pass  
     roles: [ "dbOwner" ] % assign role  
    }   
   
   db.auth(username, pass)   % authenticate a user    
```  

3. [Cheat sheet](https://blog.codecentric.de/files/2012/12/MongoDB-CheatSheet-v1_0.pdf) and [a sql-comparison](https://docs.mongodb.com/manual/reference/sql-comparison/ )  

4. Update your created name and pass in the script `mgk_uploader.py` and run it to upload information from the test data into the database.  
   * You can check current uploaded collections by typing `show collections` in the mongo shell.   
   * You can check the summary dictionary by typing `db.LinearRuns.find().pretty()`.

5. The physical storage of large files are by [GRIDFS](https://docs.mongodb.com/manual/core/gridfs/). Since it is handled by Python in the backend in our case, [here](https://api.mongodb.com/python/current/api/gridfs/index.html) is the documentation for using it in pymongo

6. You can interacte with the database via at least 3 methods:  
   * [Mongo Shell](https://docs.mongodb.com/manual/mongo/)  
   * [Pymongo](https://api.mongodb.com/python/current/api/index.html)  
   * The GUI, such as MongoDB Compass.  
   

7. Some example queries:  
   * `db.LinearRuns.find({"Parameters.kymin": {$lt: 20}}).count()`   
   * `db.LinearRuns.find({"Parameters.kymin": 160},{"Parameters.kymin":1})`    
   * `db.fs.files.find({$text:{$search : "\"autopar_0013\""}}).pretty()`   
   (text index needs to be created first. In mongo shell, type `db.collection.createIndex( { "$**": "text" } )` check [here](https://docs.mongodb.com/v3.2/core/index-text/) for details) 
  
8. Many parts are still under construction.   
   * Default QoIs to get from each run.  Need update in `get_QoI_from_run` in `mgk_post_processing.py` for adding these quantities.    
   * Integrity check.  
   * Put the database in a remote server and authentication management for different users.    
   * Other user interfaces such as a web based frontend.    
   * Visualizations after the scan and visualization option after querying the database.  
   * Compatibilities with other tools.

## Test it on Cori

1. Cloning the repo via git.  
2. Load python3 via `module load python3` 

#### Use Command Line
1. Run the uploader by `python3 mgk-dev/mgk_uploader.py -T /global/homes/d/dykuang/mgk-dev/data_linear_multi`.  Option -T is for specifying your target folder. Use option --help for display other options information.  
2. If you encounter "module not found" error. You can use `conda install`. For example, `conda install pymongo`.  
3. If this is the first time you upload files, it will ask you to type login credentials. You need to get a username and pass for the database. (Just email me with your preferred name and pass, I will then create read/write access for you).  
The default value for server, port, database name are:  **mongodb03.nersc.gov, 27017, mgk_fusion**. You will have the option to save the credential after you finished manually entering these info.
After you choose to save it. You can use `-A` option to locate your saved `.pkl` file to make uploads next time. For example `python3 mgk-dev/mgk_uploader.py -T /global/homes/d/dykuang/mgk-dev/data_linear_multi -A DK_mgk_login_admin.pkl`
#### Use Gui
1. After installing MongoCompass locally, you can view the database locally following the instructions below.



### Using MongoDB Compass
Another method is to use a GUI such as MongDB Compass.
* Download [MongoDB Compass](https://www.mongodb.com/products/compass)
* On the terminal, forward the ssh tunnel port to a local port : `ssh -i .ssh/nersc -f <nersc_username>@perlmutter.nersc.gov -L 2222:mongodb03.nersc.gov:27017 -N
`. I used 2222 here, but you can use other port specifications.
    You will be asked to provide login credentials on perlmutter for this.
* Now in the MongoDB Compass application, paste the following connection string (add your database username and password appropriately) in the **URL** block:  
`mongodb://<db_username>:<db_password>@localhost:2222/?authSource=mgk_fusion&readPreference=primary&directConnection=true&ssl=false`
* Click connect 
* Once you're logged in, you can click on mgk_fusion on the left side panel to view the database 


#### Retrieving files from database    
* Save the file with tag ObjectId(5e150c312038695f1da2e956) to *directory/newname*  
`python3 mgk-dev/mgk_download.py -A My_mgk_login.pkl -OID 5e150c312038695f1da2e956 -D directory -S newname`  
* Save the file with tag *filepath* to *directory*:  
`python3 mgk-dev/mgk_download.py -A My_mgk_login.pkl -F filepath -D directory`    
* Save all files in the *collection* with the same *run_collection_name* to *directory* :  
`python3 mgk-dev/mgk_download.py -A My_mgk_login.pkl  -C collection -T run_collection_name -D directory`    
* Save all files related to the particular run of ObjectId(5e150c312038695f1da2ea10) in *collection* to *directory*:  
`python3 mgk-dev/mgk_download.py -A My_mgk_login.pkl  -C collection -OID 5e150c312038695f1da2ea10 -D directory`  

New directory will be created if it does not exist.

### Caution:
* If you have Read/Write access to the database, be careful while using mongodb compass, you may accidently modify the database.  
