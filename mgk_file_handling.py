#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File handling script for formatting output files, getting file lists, and
reading and writing to database containing:
    get_file_list(out_dir,begin):       input GENE output directory and base filepath 
                                           (nrg, energy, etc), return full list of files 
                                           in directory
    get_suffixes(out_dir):            input GENE output directory, return list of run 
                                           suffixes in the directory
    gridfs_put(filepath):               input filepath, upload  file to database, and 
                                           return object_id of uploaded file
    gridfs_read(db_file):               input database filename, return contents of file
    upload_to_mongo   
    isLinear
@author: Austin Blackmon, Dongyang Kuang
"""

'''
ToDO:
    
    1: files with extention
    2: mom files with different type (linear run will only need the last frame)
    
'''

from mgk_post_processing import *
from ParIO import * 
import numpy as np
#from pymongo import MongoClient
from bson.objectid import ObjectId
#from bson import json_util
import os
from pathlib import Path
import gridfs
#import re
#from sshtunnel import SSHTunnelForwarder
import json
#=======================================================
# database specification. Local test
#=====================================================

# =============================================================================
# mgkdb_server = 'localhost'
# mgkdb_port = '27017'
# mgkdb_dbname = 'mgk_fusion'
# mgkdb_user = 'dykuang'
# mgkdb_pass = '1234'
# 
# mgkdb_connect = MongoClient(mgkdb_server)
# database = mgkdb_connect[mgkdb_dbname]
# mgkdb_client = database.authenticate(mgkdb_user, mgkdb_pass)	
# =============================================================================

# Default_Keys for summary files, keys should not contain '.' #
Default_Keys = ['scan_id',  'submit_id',  'eqdisk_id' ]

#==============================================================================
#standard files#
# Q: is geneerr with suffix? 
Docs = ['autopar', 'codemods', 'energy',  'nrg', 
              'parameters', 's_alpha', 'scan.log', 'scan_info.dat', 'geneerr.log']
Keys = ['autopar', 'codemods', 'energy',  'nrg', 
              'parameters', 's_alpha', 'scanlog', 'scaninfo', 'geneerr']

#Large files#
Docs_L = ['field', 'mom', 'vsp']
Keys_L = ['field', 'mom', 'vsp']



#User specified files#
Docs_ex = [] 
Keys_ex = []

    
meta = ["user", "run_collection_name" ,"run_suffix" ,"keywords", "confidence"]
    
file_related_keys = Keys + Keys_L + Keys_ex
file_related_docs = Docs + Docs_L + Docs_ex
    
#run_data_Nonlin = ["Qes", "kymin", "kx_center", "omt", "omn"]
#run_data_Linear = ["gamma","omega_num","kymin", "kx_center", "omt", "omn"]


def reset_docs_keys():
    global Default_Keys, Docs, Keys, Docs_L, Keys_L, Docs_ex, Keys_ex, meta, file_related_keys,\
           file_related_docs
    
    Default_Keys = ['scan_id',  'submit_id',  'eqdisk_id' ]

    Docs = ['autopar', 'codemods', 'energy', 'nrg',  
                  'parameters', 's_alpha', 'scan.log', 'scan_info.dat', 'geneerr.log']
    Keys = ['autopar', 'codemods', 'energy', 'nrg',  
                  'parameters', 's_alpha', 'scanlog', 'scaninfo', 'geneerr']
    
    #Large files#
    Docs_L = ['field', 'mom', 'vsp']
    Keys_L = ['field', 'mom', 'vsp']
    
    
    #User specified files#
    Docs_ex = [] 
    Keys_ex = []
    
        
    meta = ["user", "run_collection_name" ,"run_suffix" ,"keywords", "confidence"]
        
    file_related_keys = Keys + Keys_L + Keys_ex
    file_related_docs = Docs + Docs_L + Docs_ex
        
    print("File names and their key names are reset to default!")

def get_data(key, *args):
    '''
    Use to get data from default files with functions defined in func_dic
    '''
    return func_dic[key](*args)

def get_data_by_func(user_func, *args):
    '''
    user_func takes args and should return a dictionary having at least two keys: '_header_' and '_data_'
    an example is provided as below: get_data_from_energy()
    '''
    return user_func(*args)

def get_data_from_energy(db, filepath):
    '''
    read GENE energy output, parsed into header and datapart
    '''
    fs = gridfs.GridFS(db)
    if fs.exists({"filepath": filepath}):
        file = fs.find_one({"filepath": filepath}) # assuming only one
        contents = file.read().decode('utf8').split('\n')
        header = []
        data = []
        for line in contents:
            if '#' in line:
                header.append(line)
            else:
                d_str = line.split()
                if d_str:
                    data.append([float(num) for num in d_str])
        
#        data = np.array(data)
        return {'_header_': header[:-1], '_data_': np.array(data)}
    
    else:
        print("No entry in current database matches the specified filepath.")
        return None

def get_data_from_nrg(db, filepath):
    fs = gridfs.GridFS(db)
    if fs.exists({"filepath": filepath}):
        file = fs.find_one({"filepath": filepath}) # assuming only one
        contents = file.read().decode('utf8').split('\n')
        header = []
        data = []
        time = []
        count = 0
        for line in contents[:-1]: # last line is ''
            if count % 2 == 0:
#               print(count)
               time.append(float(line))
            else:
                d_str = line.split()
                if d_str:
                    data.append([float(num) for num in d_str])
            count += 1
        
#        data = np.array(data)
        return {'_header_': header, '_time_': np.array(time), '_data_': np.array(data)}
    
    else:
        print("No entry in current database matches the specified filepath.")
        return None

def isfloat(a):
    try:
        float(a)
        return True
    except ValueError:
        return False

def to_float(a):
    try:
        b = float(a)
    except ValueError:
        b = a
    return b

def get_data_from_parameters(db, filepath):
    fs = gridfs.GridFS(db)
    if fs.exists({"filepath": filepath}):
        file = fs.find_one({"filepath": filepath}) # assuming only one
        contents = file.read().decode('utf8').split('\n')
        summary_dict=dict()
        for line in contents:
            if '&' in line:
                category = line[1:]
                sub_dict = {}
            elif '=' in line:
                pars = line.split('=')
                sub_dict[pars[0].rstrip()] = to_float(pars[1]) 
            elif '/' in line:
                summary_dict[category] = sub_dict            
            else:
                continue
            
        return summary_dict
    
    else:
        print("No entry in current database matches the specified filepath.")
        return None
    
#def get_data_from_scaninfo(db, filepath):
#    '''
#    This may does NOT work for multiple suffixes.
#    '''
#    fs = gridfs.GridFS(db)
#    if fs.exists({"filepath": filepath}):
#        file = fs.find_one({"filepath": filepath}) # assuming only one
#        contents = file.read().decode('utf8').split('\n')
#
#        keys = ['kymin', 'x0', 'kx_center', 'n0_global', 'gamma(cs/a)', 'omega(cs/a)',
#                '<z>', 'lambda_z', 'parity(apar)', 'parity(phi)', 'QEM/QES', 'Epar cancelation',
#                'gamma_HB_avg', 'gamma_HB_min']
#
#        info = dict().fromkeys(keys)
#        for line in contents:
#            if '#' in line:
#                continue
#            else:
#                vals = line.split()
#                if vals:
#                    for ind, key in enumerate(keys):
#                          info[key] = to_float(vals[ind])
#
#        return info
#    
#    else:
#        print("No entry in current database matches the specified filepath.")
#        return None    

def get_data_from_tracer_efit(db, filepath):      
    fs = gridfs.GridFS(db)
    if fs.exists({"filepath": filepath}):
        file = fs.find_one({"filepath": filepath}) # assuming only one
        contents = file.read().decode('utf8').split('\n')
        header_dict = {}
        data = []
        for line in contents:
            if '=' in line:
                item = line.split('=')
#                if '_' in item[1] or ' \' ' in item[1]:
                if isfloat(item[1]):
                    header_dict[item[0]] = float(item[1])
                else:
                    header_dict[item[0]] = item[1]
                    
            elif '/' in line or '&' in line:
                continue

            else:
                d_str = line.split()
                if d_str:
                    data.append([float(num) for num in d_str])
        
#        data = np.array(data)
        return {'_header_': header_dict, '_data_': np.array(data)}
    
    else:
        print("No entry in current database matches the specified filepath.")
        return None
    
func_dic = {'energy': get_data_from_energy,
            'nrg': get_data_from_nrg,
            'parameters': get_data_from_parameters
            }        

def get_file_list(out_dir, begin):
    '''
    Get files from out_dir that begins with "begin"
    '''
    files_list = []
    
    #unwanted filetype suffixes for general list
    bad_ext = ('.ps','.png')
    
    #scan files in GENE output directory, ignoring files in '/in_par', and return list
    files = next(os.walk(out_dir))[2]
    for count, name in enumerate(files, start=0):
        if name.startswith(begin) and name.endswith(bad_ext) == False and not os.path.isdir('in_par'):
            file = os.path.join(out_dir, name)
            files_list.append(file)
    return files_list     


def get_suffixes(out_dir):
    suffixes = []
    
    #scan files in GENE output directory, find all run suffixes, return as list
    files = next(os.walk(out_dir))[2]
    for count, name in enumerate(files, start=0):
        if name.startswith('parameters_'):
            suffix = name.split('_',1)[1]
            if '_' not in suffix: # suffixes like "1_linear" will not be considered.
                suffix = '_' + suffix
                suffixes.append(suffix)
        elif name.lower().startswith('parameters.dat'):
            suffixes = ['.dat']                
    return suffixes


def gridfs_put(db, filepath):
    #set directory and filepath
    file = open(filepath, 'rb')

    #connect to 'ETG' database
#    db = mgkdb_client.mgk_fusion
#    db = database

    #upload file to 'fs.files' collection
    fs = gridfs.GridFS(db)
    dbfile = fs.put(file, encoding='UTF-8', 
                    filepath = filepath,
                    filename = filepath.split('/')[-1],
                    metadata = None)  # may also consider using upload_from_stream ?
    file.close()
    
    #grab '_id' for uploaded file
#    object_id = str(dbfile)  # why convert to string?
#    return(object_id)
    return dbfile
    
    
def gridfs_read(db, filepath):
    #connect to 'ETG' database
#    db = mgkdb_client.mgk_fusion
#    db = database
    #open 'filepath'
    fs = gridfs.GridFS(db)
    file = fs.find_one({"filepath": filepath})
    contents = file.read()
    return(contents)

def Array2Dict_dim1(npArray, key_names=None):
    '''
    Convert a 1d numpy array to dictionary
    '''
    assert len(npArray.shape) == 1, "Dimension of input numpy array should be 1."
    
    arraydict = dict()
    
    if key_names:
        for i in range(len(npArray)):
            arraydict[key_names[i]] = npArray[i]
    
    else:
        for i in range(len(npArray)):
            arraydict[str(i)] = npArray[i]
    
    return arraydict

def Array2Dict_dim2(npArray, row_keys=None, col_keys=None):
    '''
    Convert a 2d numpy array to dictionary
    '''
    assert len(npArray.shape) == 2, "Dimension of input numpy array should be 2."
    
    arraydict = dict()
    
    nrows, ncols = np.shape(npArray)
    if row_keys and col_keys:
        for i in range(nrows):
            row_dict = {}
            for j in range(ncols):
                row_dict[col_keys[j]] = npArray[i,j]
            arraydict[row_keys[i]] = row_dict
    
    else:
        for i in range(nrows):
            row_dict = {}
            for j in range(ncols):
                row_dict[str(j)] = npArray[i,j]
            arraydict[str(i)] = row_dict
        
    return arraydict
    
import pickle
from bson.binary import Binary
def _npArray2Binary(npArray):
    """Utility method to turn an numpy array into a BSON Binary string.
    utilizes pickle protocol 2 (see http://www.python.org/dev/peps/pep-0307/
    for more details).

    Called by stashNPArrays.

    :param npArray: numpy array of arbitrary dimension
    :returns: BSON Binary object a pickled numpy array.
    """
    return Binary(pickle.dumps(npArray, protocol=2), subtype=128 )

def _binary2npArray(binary):
    """Utility method to turn a a pickled numpy array string back into
    a numpy array.

    Called by loadNPArrays, and thus by loadFullData and loadFullExperiment.

    :param binary: BSON Binary object a pickled numpy array.
    :returns: numpy array of arbitrary dimension
    """
    return pickle.loads(binary)

def gridfs_put_npArray(db, value, filepath, filename):
    fs = gridfs.GridFS(db)
    obj_id=fs.put(_npArray2Binary(value),encoding='UTF-8',
                  filename = filename,
                  filepath = filepath)
    return obj_id  
    
    
def load(db, collection, query, projection={'Meta':1, 'Diagnostics':1}, getarrays=True):
    """Preforms a search using the presented query. For examples, see:
    See http://api.mongodb.org/python/2.0/tutorial.html
    The basic idea is to send in a dictionaries which key-value pairs like
    mdb.load({'basename':'ag022012'}).

    :param query: dictionary of key-value pairs to use for querying the mongodb
    :returns: List of full documents from the collection
    """
    
    results = collection.find(query, projection)
    
    if getarrays:
        allResults = [_loadNPArrays(db, doc) for doc in results]
    else:
        allResults = [doc for doc in results]
    
    if allResults:
#        if len(allResults) > 1:
#            return allResults
#        elif len(allResults) == 1:
#            return allResults[0]
#        else:
#            return None
        return allResults
    else:
        return None
    
def _loadNPArrays(db, document):
    """Utility method to recurse through a document and gather all ObjectIds and
    replace them one by one with their corresponding data from the gridFS collection

    Skips any entries with a key of '_id'.

    Note that it modifies the document in place.

    :param document: dictionary like-document, storable in mongodb
    :returns: document: dictionary like-document, storable in mongodb
    """
    fs = gridfs.GridFS(db)
    for (key, value) in document.items():
        if isinstance(value, ObjectId) and key != '_id':
            document[key] = _binary2npArray(fs.get(value).read())
        elif isinstance(value, dict):
            document[key] = _loadNPArrays(db, value)
    return document

from diag_plot import diag_plot
def query_plot(db, collection, query, projection = {'Meta':1, 'Diagnostics':1}):
    data_list = load(db, collection, query, projection)
    print('{} records found.'.format(len(data_list)))
    
    data_to_plot = [diag_plot(da) for da in data_list]
    
    for i in range(len(data_to_plot)):
         data_to_plot.plot_all()    
    
    
def isLinear(folder_name):
    linear = None
    #check parameters file for 'nonlinear' value
    if os.path.isfile(folder_name + '/parameters'):
        par = Parameters()
        par.Read_Pars(folder_name + '/parameters')
        pars = par.pardict
        linear = not pars['nonlinear']
        return(linear)
        
    #check folder name for nonlin
    elif folder_name.find('nonlin') != -1:
        linear = False
        return(linear)
    
    #check folder name for linear
    elif folder_name.find('linear') != -1:
        linear = True 
        return(linear)

    else:
        assert linear is None, "Can not decide, please include linear/nonlin as the suffix of your data folder!"
        
        
def isUploaded(out_dir,runs_coll):
    '''
    check if out_dir appears in the database collection.
    Assuming out_dir will appear no more than once in the database
    '''
    inDb = runs_coll.find({ "Meta.run_collection_name": out_dir })
#    print(inDb)
#    for run in inDb:
#        runIn = run["run_collection_name"]
##        print(runIn)
#        return(runIn == out_dir)
    uploaded = False
    for run in inDb:
        if run["Meta"]["run_collection_name"] == out_dir: # seems redundent?
            uploaded = True
            break
    
    return uploaded


def get_record(out_dir, runs_coll):
    '''
    Get a list of summary dictionary for 'out_dir' in the database
    '''
    inDb = runs_coll.find({ "Meta.run_collection_name": out_dir })
    record = []
    for run in inDb:
#        dic = dict()
#        for key, val in run.items():
#            dic[key] = val
#        record.append(dic)
        record.append(run)
    return record

#def retrieve_files(source_dir, target_dir, runs_coll, key_list=file_related_keys):
#    '''
#    Retrieve files stored in database taged with source_dir to target_dir
#    Current code is local -> local, will need remote -> local via sshtunnel as well
#    '''
#    
#    fs = gridfs.GridFS(database)
#
#    # get the summary
#    records = get_record(source_dir, runs_coll)
#    
#    # for each record in summary, save corresponding files to target_dir
#    count = 1
##    print(len(records))
#    for record in records:
#        for key in key_list:
#            if record[key] != 'None':
#                _id = ObjectId(record[key])
#                file = fs.find_one({"_id": _id}) # only one file with _id, only available by fs.download_to_stream(id, destination)
##                for file in files:
#                contents = file.read()
##                    file_name = file["filepath"].split('/')[-1] # this way is not supported
#                file_name = file.filepath.split('/')[-1]
#                with open(target_dir + '/' + file_name, 'wb') as f:
#                    f.write(contents)
#        # also save the record to json
#        to_json = json_util.dumps(record)
#        with open(target_dir + '/' + 'record_{}.json'.format(count), 'wb') as f:
#            f.write(to_json)
#            
#        count +=1  
#    
#    print("Retrieval completed")
    
def download_file_by_path(db, filepath, destination, revision=-1, session=None):
    '''
    db: database name
    filepath: filepath stored in database, that is "db.fs.files['filepath']"
    destination: local path to put the file
    
    Attention: filename may correspond to multiple entries in the database
    '''
    fs = gridfs.GridFSBucket(db)
    records = db.fs.files.find({"filepath": filepath})
    count = 0
    for record in records:
        _id = record['_id']
        filename = record['filepath'].split('/')[-1]
        with open(os.path.join(destination, filename+'_mgk{}'.format(count) ),'wb+') as f:
            fs.download_to_stream(_id, f)
            count +=1
#            fs.download_to_stream_by_name(filename, f, revision, session)
        
    print("Download completed! Downloaded: {}".format(count))
    
def download_file_by_id(db, _id, destination, fname=None, session = None):
    '''
    db: database name
    _id: object_id
    destionation: local path to put the file
    fname: name you want to call for the downloaded file
    '''

    fs = gridfs.GridFSBucket(db)
    if not fname:
        fname = db.fs.files.find_one(_id)['filename']
    if not os.path.exists(destination):
        Path(destination).mkdir(parents=True) 
    with open(os.path.join(destination, fname),'wb+') as f:   
        fs.download_to_stream(_id, f)
    print("Download completed!")
    
def download_dir_by_name(db, runs_coll, dir_name, destination):  
    '''
    db: database name
    dir_name: as appear in db.Meta['run_collection_name']
    destination: destination to place files
    '''
    path = os.path.join(destination, dir_name.split('/')[-1])
    if not os.path.exists(path):    
        try:
            #os.mkdir(path)
            Path(path).mkdir(parents=True) 
        except OSError:
            print ("Creation of the directory %s failed" % path)
    #else:
    fs = gridfs.GridFSBucket(db)
    inDb = runs_coll.find({ "Meta.run_collection_name": dir_name })

    if inDb[0]['Files']['scanlog'] != 'None':
        with open(os.path.join(path, 'scan.log'),'wb+') as f:
            fs.download_to_stream(inDb[0]['Files']['scanlog'], f, session=None)
            
    if inDb[0]['Files']['scaninfo'] != 'None':
        with open(os.path.join(path, 'scan_info.dat'),'wb+') as f:
            fs.download_to_stream(inDb[0]['Files']['scaninfo'], f, session=None)
    
    if inDb[0]['Files']['geneerr'] != 'None':    
        with open(os.path.join(path, 'geneerr.log'),'wb+') as f:
            fs.download_to_stream(inDb[0]['Files']['geneerr'], f, session=None)

    for record in inDb:
        '''
        Download 'files'
        '''
        for key, val in record['Files'].items():
            if val != 'None' and key not in ['scanlog', 'scaninfo', 'geneerr']:
                filename = db.fs.files.find_one(val)['filename']
                with open(os.path.join(path, filename),'wb+') as f:
#                    fs.download_to_stream_by_name(filename, f, revision=-1, session=None)
                    fs.download_to_stream(val, f, session=None)
                record['Files'][key] = str(val)
        record['Files']['scanlog'] = str(record['Files']['scanlog'])
        record['Files']['scaninfo'] = str(record['Files']['scaninfo'])
        record['Files']['geneerr'] = str(record['Files']['geneerr'])
        
        '''
        Deal with diagnostic data
        '''
        fsf=gridfs.GridFS(db)
        for key, val in record['Diagnostics'].items():
            if isinstance(val, ObjectId):
#                data = _loadNPArrays(db, val)
#                data = _binary2npArray(fsf.get(val).read()) # no need to store data
                record['Diagnostics'][key] = str(val)
                data = _binary2npArray(fsf.get(val).read()) 
                np.save( os.path.join(path,str(record['_id'])+'-'+key), data)
                
        record['_id'] = str(record['_id'])
        with open(os.path.join(path, 'mgkdb_summary_for_run'+record['Meta']['run_suffix']+'.json'), 'w') as f:
            json.dump(record, f)
           
    print ("Successfully downloaded to the directory %s " % path)


def download_runs_by_id(db, runs_coll, _id, destination):
    '''
    Download all files in collections by the id of the summary dictionary.
    '''
    
    fs = gridfs.GridFSBucket(db)
    record = runs_coll.find_one({ "_id": _id })
    dir_name = record['Meta']['run_collection_name']
    path = os.path.join(destination, dir_name.split('/')[-1])
    if not os.path.exists(path):
        try:
            path = os.path.join(destination, dir_name.split('/')[-1])
            #os.mkdir(path)
            Path(path).mkdir(parents=True)
        except OSError:
            print ("Creation of the directory %s failed" % path)
    #else:
    '''
    Download 'files'
    '''
    for key, val in record['Files'].items():
        if val != 'None':
            filename = db.fs.files.find_one(val)['filename']
            #print(db.fs.files.find_one(val)).keys()
            with open(os.path.join(path, filename),'wb+') as f:
#                    fs.download_to_stream_by_name(filename, f, revision=-1, session=None)
                fs.download_to_stream(val, f, session=None)
            record['Files'][key] = str(val)
            
    '''
    Deal with diagnostic data
    '''
    fsf=gridfs.GridFS(db)
    for key, val in record['Diagnostics'].items():
        if isinstance(val, ObjectId):
#                data = _binary2npArray(fsf.get(val).read()) # no need to store data
            record['Diagnostics'][key] = str(val)
            data = _binary2npArray(fsf.get(val).read()) 
            np.save( os.path.join(path,str(record['_id'])+'-'+key), data)

    #print(record)
    record['_id'] = str(_id)

    with open(os.path.join(path, 'mgkdb_summary_for_run'+record['Meta']['run_suffix']+'.json'), 'w') as f:
        json.dump(record, f)
    print("Successfully downloaded files in the collection to directory %s " % path)    
    


def update_Meta(out_dir, runs_coll, suffix):

    meta_list = ['user', 'run_collection_name', 'run_suffix', 'keywords', 'confidence']
    print("Keys available for update are {}".format(meta_list.sort()))
    
    keys = input('What entries do you like to update? separate your input by comma.\n').split(',')
    vals = input('type your values corresponding to those keys you typed. Separate each category by ; .\n').split(';')
    assert len(keys)==len(vals), 'Input number of keys and values does not match. Abort!'
    for key, val in zip(keys, vals):
    
        runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                         {"$set":{'Meta.'+key: val} }
                         )    
    print("Meta{} in {} updated correctly".format(suffix, out_dir))

    
def update_Parameter(out_dir, runs_coll, suffix):
    
    param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                     {"$set":{'Parameters': param_dict}}
                     )
    
    print("Parameters{} in {} updated correctly".format(suffix, out_dir))
    


def update_mongo(out_dir, db, runs_coll):
    '''
    only update file related entries, no comparison made before update

    '''

    fs = gridfs.GridFS(db)
    suffixes = get_suffixes(out_dir)        
    update_option = input('Enter options for update:\n 0: Files shared by all runs, usually do not have a suffix. \n 1: Unique files used per run. Specify the keywords and suffixes. \n ')
    if update_option == '0':
        files_to_update = input('Please type FULL file names to update, separated by comma.\n').split(',')
        keys_to_update = input('Please type key names for each file you typed, separated by comma.\n').split(',')
        affect_QoI = input('Will the file change QoIs/Diagnostics? (Y/N)')
        updated = []
        print('Uploading files .......')
        # update the storage chunk
        for doc, field in zip(files_to_update, keys_to_update):
            files = get_file_list(out_dir, doc) # get file with path
            assert len(files), "Files specified not found!"
            # delete ALL history
            for file in files:
                grid_out = fs.find({'filepath': file})
                for grid in grid_out:
                    print('File with path tag:\n{}\n'.format(grid['filepath']) )
                    fs.delete(grid._id)
                    print('deleted!')

            with open(file, 'rb') as f:
                _id = fs.put(f, encoding='UTF-8', filepath=file, filename=file.split('/')[-1])
#            _id = str(_id)
            updated.append([field, _id])
        
        # update the summary dictionary  
        print('Updating summary dictionary .....')              
        for entry in updated:
            for suffix in suffixes:
                if affect_QoI in ['Y', 'y']:
                    QoI_dir, Diag_dict = get_QoI_from_run(out_dir, suffix)
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                            { "$set": {'QoI': QoI_dir, 'Diagnostics':Diag_dict}} 
                                 )
                    
                runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                                 {"$set":{'Files.'+entry[0]: entry[1]}}
                                 )
        
        print("Update complete")
                
    elif update_option == '1':
        files_to_update = input('Please type filenames (without suffixes) for files to update, separated by comma.\n').split(',')
        suffixes.sort()
        print("suffixes availables are:{}".format(suffixes))
        runs_to_update = input('Please type which suffixes to update, separated by comma. If you need to update all runs, just hit ENTER. \n').split(',')      
        affect_QoI = input('Will the file change QoIs/Diagnostics? (Y/N)')
#        updated = []
        # update the storage chunk
        print('Uploading files .......')
        if len(runs_to_update[0]) != 0:
            run_suffixes = runs_to_update
        else:
            run_suffixes = suffixes
        
        for doc in files_to_update:
            for suffix in run_suffixes:
                if affect_QoI in ['Y', 'y']:
                    QoI_dir, Diag_dict = get_QoI_from_run(out_dir, suffix)
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix },
                            { "$set": {'QoI': QoI_dir, 'Diagnostics':Diag_dict}}
                                 )

                file = os.path.join(out_dir, doc  + suffix)
                grid_out = fs.find({'filepath': file})
                for grid in grid_out:
                    print('File with path tag:\n{}\n'.format(grid.filepath) )
                    fs.delete(grid._id)
                    print('deleted!')
                
                with open(file, 'rb') as f:
                    _id = fs.put(f, encoding='UTF-8', filepath=file, filename=file.split('/')[-1])
#                _id = str(_id)
                runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                                 { "$set": {'Files.'+ doc: _id} }
                                 )
        print("Update complete")
    
    else:
        print('Invalid input. Update aborted.')
        pass
    
def remove_from_mongo(out_dir, db, runs_coll):
    #find all documents containing collection name
#    if linear:
#        runs_coll = db.LinearRuns
#    else:
#        runs_coll = db.NonlinRuns
        
    inDb = runs_coll.find({ "Meta.run_collection_name": out_dir })        
    fs = gridfs.GridFS(db)
    for run in inDb:
        # delete the gridfs storage:
        for key, val in run['Files'].items():
#            print(val)
#            if (key in file_related_keys) and val != 'None':
##                print((key, val))
#                target_id = ObjectId(val)
#                print((key, target_id))
#                fs.delete(target_id)
#                print('deleted!')
            if val != 'None':
                print((key, val))
                fs.delete(val)
                print('deleted!')
#                if fs.exists(target_id):
#                    print("Deleting storage for entry \'{}\' deleted with id: {}").format(key, val)
#                    fs.delete(target_id)
#                    print("Deleted!")
                
        for key, val in run['Diagnostics'].items():
            if val != 'None':
                print((key, val))
                fs.delete(val)
                print('deleted!')
                    
                
#        delete the header file
        runs_coll.delete_one(run)
        

def upload_file_chunks(db, out_dir, large_files=False, extra_files=False):
    '''
    This function does the actual uploading of grifs chunks and
    returns object_ids for the chunk.
    '''
#    suffixes = get_suffixes(out_dir)
#    
#    '''
#    If there is a shared parameter file or these is only one parameter file
#    '''
#    if os.path.isfile(os.path.join(out_dir, 'parameters')):
#        par_file = os.path.join(out_dir, 'parameters')
#    elif len(suffixes)==1 and os.path.isfile(os.path.join(out_dir, 'parameters'+suffixes[0])):
#        par_file = os.path.join(out_dir, 'parameters'+suffixes[0])
#    else:
#        os.exit('Cannot locate or decide the parameter file!')
    
#    print(out_dir) 
    par_list = get_file_list(out_dir, 'parameters') # assuming parameter files start with 'parameters' 
#    print(par_list)
    if len(par_list) == 0:
        os.exit('Cannot locate parameter files in folder')
    elif len(par_list) == 1:
        par_file = par_list[0]
    elif os.path.join(out_dir, 'parameters') in par_list:
        par_file = os.path.join(out_dir, 'parameters')
    else: # assuming all these files share the same 'magn_geometry' and 'mom' info.
        print('There seems to be multiple parameter files detected:\n')
        count=0
        for par in par_list:
            print('{} : {}\n'.format(count, par.split('/')[-1]))
            count+=1
        choice = input('Which one do you want to scan for information.\n')
        choice = int(choice)
        par_file = os.path.join(out_dir, par_list[choice])
        print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_list[choice]))
#    par_file = os.path.join(out_dir, 'parameters')
#    print(par_file)
    par = Parameters()
    par.Read_Pars(par_file)
    pars = par.pardict
    n_spec = pars['n_spec']
    
    if 'magn_geometry' in pars:
        Docs.append(pars['magn_geometry'][1:-1])
        Keys.append('magn_geometry')
    if large_files:
        if 'name1' in pars and 'mom' in Docs_L:
            Docs_L.pop(Docs_L.index('mom'))
            Keys_L.pop(Keys_L.index('mom'))
            for i in range(n_spec): # adding all particle species
                Docs_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
                Keys_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
    
    output_files = [get_file_list(out_dir, Qname) for Qname in Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
    
        
    if large_files:
        output_files += [get_file_list(out_dir, Qname) for Qname in Docs_L if Qname]
    if extra_files:
        output_files += [get_file_list(out_dir, Qname) for Qname in Docs_ex if Qname]
        
    
    
    output_files = set([item for sublist in output_files for item in sublist]) # flat the list and remove possible duplicates
    
#    print(output_files)
      
    object_ids = {}
    for file in output_files:
        _id = gridfs_put(db, file)
        object_ids[_id] = file

#    print(object_ids)
    return object_ids

def upload_linear(db, out_dir, user, linear, confidence, input_heat, keywords, 
                  large_files=False, extra=False, verbose=True):
    #connect to linear collection
#    runs_coll = mgkdb_client.mgk_fusion.LinearRuns
    runs_coll = db.LinearRuns
    
    #generate scan_info.dat
#    suffixes = scan_info(out_dir)
    
    #update files dictionary
#    print(out_dir)
    object_ids = upload_file_chunks(db, out_dir, large_files, extra)  # it changes Docs and Keys globally 
#    print(object_ids)         
    suffixes = get_suffixes(out_dir)
#    print(suffixes)
    _docs = Docs.copy()
    _keys = Keys.copy()
    
    if large_files:
        _docs = _docs + Docs_L
        _keys = _keys + Keys_L
    if extra:
        _docs = _docs + Docs_ex
        _keys = _keys + Keys_ex
        
    files_dict = dict.fromkeys(Default_Keys+_keys, 'None')
    
    for suffix in suffixes:
        for _id, line in list(object_ids.items()):
            for Q_name, Key in zip(_docs, _keys):
#                if line.find(os.path.join(out_dir,Q_name + suffix) ) != -1:
#                if (Q_name + suffix) == line.split('/')[-1]:
                if os.path.join(out_dir,Q_name + suffix) == line:
#                    files_dict[Key] = line.split()[0]
                    if '.' in Key:
                        Key = '_'.join(Key.split('.'))

                    files_dict[Key] = _id
                    try:
                        object_ids.pop(_id)
                    except KeyError:
                        continue
                    
#            if line.find('geneerr.log') != -1:
#                files_dict['geneerrlog'] = line.split()[0]
#            if line.find(os.path.join(out_dir,'scan.log') ) != -1:
            if os.path.join(out_dir,'scan.log') == line:
#                files_dict['scanlog'] = line.split()[0]
                files_dict['scanlog'] = _id
                object_ids.pop(_id)
#            if line.find(os.path.join(out_dir,'scan_info.dat') ) != -1:
#                files_dict['scaninfo'] = line.split()[0]
            if os.path.join(out_dir,'scan_info.dat') == line:
                files_dict['scaninfo'] = _id
                object_ids.pop(_id)
#            if line.find(os.path.join(out_dir,'geneerr.log') ) != -1:
            if os.path.join(out_dir,'geneerr.log') == line:
                files_dict['geneerr'] = _id
                object_ids.pop(_id)
      
        
        #metadata dictonary
        meta_dict = {"user": user,
                     "run_collection_name": out_dir,
                     "run_suffix": '' + suffix,
                     "keywords": keywords,
                     "confidence": confidence
                    }  
               
        QoI_dict, Diag_dict = get_QoI_from_run(out_dir, suffix)
        
        for key, val in Diag_dict.items():
            Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)
        
        param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
        #combine dictionaries and upload
        run_data =  {'Meta': meta_dict, 'Files': files_dict, 'QoI': QoI_dict, 'Diagnostics': Diag_dict, 'Parameters': param_dict}
        runs_coll.insert_one(run_data).inserted_id  
        print('Files with suffix: {} in folder {} uploaded successfully'.format(suffix, out_dir))
        if verbose:
            print('A summary is generated as below:\n')
            print(run_data)
    
    
    
    '''
    Get a dictionary of what's left in object_ids
    '''
    ex_dict = dict()
    for _id, line in object_ids.items():
        if '.' in line:
            line = '_'.join(line.split('.'))  # if . appears in the key such as nrg_001.h5 -> nrg_001_h5
        ex_dict[line] = _id
    if ex_dict: 
        db.ex.Lin.insert_one(ex_dict)        
    reset_docs_keys()
#    print('Run collection \'' + out_dir + '\' uploaded succesfully.')
        
        
def upload_nonlin(db, out_dir, user, linear, confidence, input_heat, keywords, 
                  large_files=False, extra=False, verbose=True):
    #connect to nonlinear collection
    runs_coll = db.NonlinRuns
    
    #generate scan_info.dat
#    suffixes = scan_info(out_dir)  ### add check for file existence
    
    #update files dictionary
    object_ids = upload_file_chunks(db, out_dir, large_files, extra)   
    suffixes = get_suffixes(out_dir)
#    print(suffixes)
#    print(object_ids)
    _docs = Docs.copy()
    _keys = Keys.copy()
    
    if large_files:
        _docs = _docs + Docs_L
        _keys = _keys + Keys_L
    if extra:
        _docs = _docs + Docs_ex
        _keys = _keys + Keys_ex
        
    files_dict = dict.fromkeys(Default_Keys+_keys, 'None')
        
    for suffix in suffixes:
#        print(suffix)
        for _id, line in list(object_ids.items()):  
            for Q_name, Key in zip(_docs, _keys):
#                if line.find(os.path.join(out_dir, Q_name + suffix)) != -1:
                if os.path.join(out_dir,Q_name + suffix) == line:
#                if (Q_name + suffix) == line.split('/')[-1]:    
#                    files_dict[Key] = line.split()[0]
                    if '.' in Key:
                        Key = '_'.join(Key.split('.'))

                    files_dict[Key] = _id
                    try:
                        object_ids.pop(_id)
                    except KeyError:
                        continue
                    
#            if line.find(os.path.join(out_dir,'scan.log')) != -1:
            if os.path.join(out_dir,'scan.log') == line:
#                files_dict['scanlog'] = line.split()[0]
                files_dict['scanlog'] = _id
                object_ids.pop(_id)
#            if line.find(os.path.join(out_dir, 'scan_info.dat')) != -1:
            if os.path.join(out_dir,'scan_info.dat') == line:
#                files_dict['scaninfo'] = line.split()[0]
                files_dict['scaninfo'] = _id
                object_ids.pop(_id)
#            if line.find(os.path.join(out_dir , 'geneerr.log') ) != -1:
            if os.path.join(out_dir,'geneerr.log') == line:
                files_dict['geneerr'] = _id
                object_ids.pop(_id)
        #find relevant quantities from in/output
#        print(suffix)
        
        param_dict = get_parsed_params( os.path.join(out_dir, 'parameters' + suffix) )

       #metadata dictonary
        meta_dict = {"user": user,
                     "run_collection_name": out_dir,
                     "run_suffix": '' + suffix,
                     "keywords": keywords,
                     "confidence": confidence
                    }
        #data dictionary format for nonlinear runs
        QoI_dict, Diag_dict = get_QoI_from_run(out_dir, suffix)
        
        for key, val in Diag_dict.items():
            Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)

#        Qes = get_Qes(out_dir, suffix)
#        QoI_dict = {"Qes" : Qes, **QoI                        
#                    }
             
        #combine dictionaries and upload
#        
#        run_data =  {''meta_dict, **files_dict, **run_data_dict} 
        run_data =  {'Meta': meta_dict, 'Files': files_dict, 'QoI': QoI_dict, 'Diagnostics': Diag_dict, 'Parameters': param_dict}
        runs_coll.insert_one(run_data).inserted_id  

        print('Files with suffix: {} in folder {} uploaded successfully.'.format(suffix, out_dir))

        if verbose:
            print('A summary is generated as below:')
            print(run_data)
    

    '''
    Get a dictionary of what's left in object_ids
    '''
    
    ex_dict = dict()
    for _id, line in object_ids.items():
        if '.' in line:
            line = '_'.join(line.split('.'))
        ex_dict[line] = _id
    if ex_dict:
#        print(ex_dict.values())
        db.ex.Nonlin.insert_one(ex_dict)    
    reset_docs_keys()
            
def upload_to_mongo(db, out_dir, user, linear, confidence, input_heat, keywords, 
                    large_files = False, extra=False, verbose=True):
    #print(linear)
    #for linear runs
    if linear:
        #connect to linear collection
        runs_coll = db.LinearRuns
        #check if folder is already uploaded, prompt update?
        print('upload linear runs ******')
        if isUploaded(out_dir, runs_coll):
            update = input('Folder tag:\n {} \n exists in database.  You can:\n 0: Delete and reupload folder? \n 1: Run an update (if you have updated files to add) \n Press any other keys to abort.\n'.format(out_dir))
            if update == '0':
                #for now, delete and reupload instead of update - function under construction
                remove_from_mongo(out_dir, db, runs_coll)   
                upload_linear(db, out_dir, user, linear, confidence, input_heat, keywords,
                              large_files, extra, verbose)
            elif update == '1':
                update_mongo(out_dir, db, runs_coll)
            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_linear(db, out_dir, user, linear, confidence, input_heat, keywords, 
                          large_files, extra, verbose)
                
    #for nonlinear runs
    elif not linear:
        #connect to nonlinear collection
        runs_coll = db.NonlinRuns
        #check if folder is already uploaded, prompt update?
        print('upload nonlinear runs ******')
        if isUploaded(out_dir, runs_coll):
            update = input('Folder tag:\n {} \n exists in database.  You can:\n 0: Delete and reupload folder? \n 1: Run an update (if you have updated files to add) \n Press any other keys to abort.\n'.format(out_dir))
            if update == '0':
                #for now, delete and reupload instead of update - function under construction
                remove_from_mongo(out_dir, db, runs_coll)   
                upload_nonlin(db, out_dir, user, linear, confidence, input_heat, keywords, 
                              large_files, extra, verbose)
            elif update == '1':
                update_mongo(out_dir, db, runs_coll)

            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_nonlin(db, out_dir, user, linear, confidence, input_heat, keywords, 
                          large_files, extra, verbose)
    else:
        os.exit('Cannot decide if the folder is subject to linear or nonlinear runs.')
