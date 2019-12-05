## To start up

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
   * `db.LinearRuns.find({"Parameters_dict.kymin": {$lt: 20}}).count()`   
   * `db.LinearRuns.find({"Parameters_dict.kymin": 160},{"Parameters_dict.kymin":1})`    
   * `db.fs.files.find({$text:{$search : "\"autopar_0013\""}}).pretty()`   
   (text index needs to be created first. In mongo shell, type `db.collection.createIndex( { "$**": "text" } )` check [here](https://docs.mongodb.com/v3.2/core/index-text/) for details) 
  
8. Many parts are still under construction.   
   * Default QoIs to get from each run.  Need update in `get_QoI_from_run` in `mgk_post_processing.py` for adding these quantities.    
   * Integrity check.  
   * Put the database in a remote server and authentication management for different users.    
   * Other user interfaces such as a web based frontend.    
   * Visualizations after the scan and visualization option after querying the database.  
   * Compatibilities with other tools.

