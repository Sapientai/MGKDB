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
#from global_var import *
#from global_var import _troubled_runs

import sys
sys.path.append('support')

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
from time import strftime
import pickle
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
#Default_Keys = ['scan_id',  'submit_id',  'eqdisk_id' ]

#==============================================================================
#standard files#
# Q: is geneerr with suffix? 
__version__ = '0.0.4'
print('Current version is {}.'.format(__version__))

Docs = ['autopar', 'codemods', 'nrg', 'omega','parameters']
Keys = ['autopar', 'codemods', 'nrg', 'omega','parameters']

#Large files#
Docs_L = ['field', 'mom', 'vsp']
Keys_L = ['field', 'mom', 'vsp']


#User specified files#
Docs_ex = [] 
Keys_ex = []

       
file_related_keys = Keys + Keys_L + Keys_ex
file_related_docs = Docs + Docs_L + Docs_ex


_troubled_runs = [] # a global list to collection runs where exception happens


def reset_docs_keys():
    global  Docs, Keys, Docs_L, Keys_L, Docs_ex, Keys_ex, file_related_keys,\
           file_related_docs
    
#    Default_Keys = ['scan_id',  'submit_id',  'eqdisk_id' ]

    Docs = ['autopar', 'codemods', 'nrg',  'omega', 'parameters']
    Keys = ['autopar', 'codemods', 'nrg',  'omega', 'parameters']
    
    #Large files#
    Docs_L = ['field', 'mom', 'vsp']
    Keys_L = ['field', 'mom', 'vsp']
    
    
    #User specified files#
    Docs_ex = [] 
    Keys_ex = []
    
        
#    meta = ["user", "run_collection_name" ,"run_suffix" ,"keywords", "confidence"]
        
    file_related_keys = Keys + Keys_L + Keys_ex
    file_related_docs = Docs + Docs_L + Docs_ex
        
    print("File names and their key names are reset to default!")
    

def get_omega(out_dir, suffix):
    try:
        with open(os.path.join(out_dir, 'omega'+suffix)) as f:
            val = f.read().split()
            
        val = [float(v) for v in val] 
        if len(val) < 3:
            val = val + [np.nan for _ in range(3-len(val))]
    
    except:
        print('Omega file not found. Fill with NaN')
        val = [np.nan for _ in range(3)]
        
    return val
        

def get_time_for_diag(run_suffix):
    option = input('Please enter the tspan information for {}\n 1: Type them in manually.\n 2: Use default settings.\n 3. Use default settings for rest.\n'.format(run_suffix))
    if option == '1':      
        tspan = input('Please type start time and end time, separated by comma.\n').split(',')
        tspan[0] = float(tspan[0])
        tspan[1] = float(tspan[1])
    elif option == '2':
        tspan = None
    else:
        tspan = -1
    
    return tspan

def get_diag_with_user_input(out_dir, suffix,  manual_time_flag, img_dir='./mgk_diagplots'):

    if manual_time_flag:
        tspan = get_time_for_diag(suffix)
        if tspan == -1:
            manual_time_flag = False
            Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, None, img_dir)
        else:
            Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, tspan, img_dir) 
    else:
        Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, None, img_dir)
        
    return Diag_dict, manual_time_flag, imag_dict

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
    bad_ext = ('.ps','.png', '.jpg', '.dat~', '.h5')
    
#    print('Searching in {} with key {}'.format(out_dir, begin))
    #scan files in GENE output directory, ignoring files in '/in_par', and return list
    
#    files = next(os.walk(out_dir))[2]
    files = os.listdir(out_dir)
    for count, name in enumerate(files, start=0):
        if name.startswith(begin) and name.endswith(bad_ext) == False: #and not os.path.isdir('in_par'):
            file = os.path.join(out_dir, name)
            if file not in  files_list:
                files_list.append(file)
            
    # print('{} files found in {} beginning with {}.'.format(len(files_list), out_dir, begin) )
    return files_list     


# def get_suffixes(out_dir):
#     suffixes = []
    
#     #scan files in GENE output directory, find all run suffixes, return as list
#     files = next(os.walk(out_dir))[2]
#     for count, name in enumerate(files, start=0):
#         if name.startswith('parameters_'):
#             suffix = name.split('_',1)[1]
#             if '_' not in suffix: # suffixes like "1_linear" will not be considered.
#                 suffix = '_' + suffix
#                 suffixes.append(suffix)
#         elif name.lower().startswith('parameters.dat'):
#             suffixes = ['.dat'] 
    
#     suffixes.sort()    # sort in place, sort() returns None if success
            
#     return suffixes


def gridfs_put(db, filepath,sim_type):
    #set directory and filepath
    file = open(filepath, 'rb')

    #connect to 'ETG' database
#    db = mgkdb_client.mgk_fusion
#    db = database

    #upload file to 'fs.files' collection
    fs = gridfs.GridFS(db)
    dbfile = fs.put(file, encoding='UTF-8', 
                    filepath = filepath,
                    filename = os.path.basename(filepath),
                    simulation_type = sim_type,
                    metadata = None)  # may also consider using upload_from_stream ?
    file.close()
    
    #grab '_id' for uploaded file
#    object_id = str(dbfile)  # why convert to string?
#    return(object_id)
    return dbfile
    
    
def gridfs_read(db, query):
    #connect to 'ETG' database
#    db = mgkdb_client.mgk_fusion
#    db = database
    #open 'filepath'
    fs = gridfs.GridFS(db)
    file = fs.find_one(query)
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

def Rep_OID(dic):
    '''
    Check a dictionary tree and replace any 'ObjectId' string to ObjectId object
    '''
    for key, val in dic.items():
        if isinstance(val, str) and 'ObjectId' in val:
#            oid_str = val[8:-1]
            oid_str = val[val.find('(')+1: val.find(')')].strip()
            dic[key] = ObjectId(oid_str)

        elif isinstance(val, dict):
            dic[key] = Rep_OID(val)
    return dic

def Str2Query(s):
    '''
    Convert a string s to python dictionary for querying the database
    '''
    q_dict = json.loads(s)
    q_dict = Rep_OID(q_dict)
    
    return q_dict

def get_oid_from_query(db, collection, query):
    
    records_found = collection.find(query)
    
    oid_list = []
    
    for record in records_found:
        oid_list.append(record['_id'])
        
    
    return oid_list

def clear_ex_lin(db):
    fs = gridfs.GridFS(db)
    for record in db.ex.Lin.find():
        for key, val in record.items():
            if key != '_id':
                print((key, val))
                fs.delete(val)
                print('deleted!')
        
        db.ex.Lin.remove(record['_id'])
        
    print("Documents in ex.Lin cleared !")

        
def clear_ex_Nonlin(db):
    fs = gridfs.GridFS(db)
    for record in db.ex.Nonlin.find():
        for key, val in record.items():
            if key != '_id':
                print((key, val))
                fs.delete(val)
                print('deleted!') 
                
        db.ex.Nonlin.remove(record['_id'])
    
    print("Documents in ex.Lin cleared !")
           
def clear_ex(db):
    clear_ex_lin(db)
    clear_ex_Nonlin(db)
    
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

def gridfs_put_npArray(db, value, filepath, filename, sim_type):
    fs = gridfs.GridFS(db)
    obj_id=fs.put(_npArray2Binary(value),encoding='UTF-8',
                  filename = filename,
                  simulation_type = sim_type,
                  filepath = filepath)
    return obj_id  
    
    
def load(db, collection, query, projection={'Meta':1, 'gyrokinetics':1, 'Diagnostics':1}, getarrays=True):
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
    suffixes = get_suffixes(folder_name)
    
    if len(suffixes):
        suffixes.sort()
        suffix = suffixes[0] #assuming all parameters files are of the same linear/nonlinear type
        print('Scanning parameters{} for deciding linear/Nonlinar.')
    else:
        suffix = ''
    
#    print(folder_name) 
    fname = os.path.join(folder_name, 'parameters' + suffix)
    if os.path.isfile( fname ):
        par = Parameters()
        par.Read_Pars( fname )
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
#            print(run["Meta"]["run_collection_name"])
            uploaded = True
            break
#    if inDb is not None:
#        uploaded=True
#        for run in inDb:
#            print(run["Meta"]["run_collection_name"])
#    else:
#        uploaded = False
    
    return uploaded

def not_uploaded_list(out_dir, runs_coll, write_to = None):
    '''
    Get all subfolders in out_dir that are not in the database yet
    '''
    not_uploaded = []
    for dirpath, dirnames, files in os.walk(out_dir):
        if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1:
            if not isUploaded(dirpath, runs_coll):
                not_uploaded.append(dirpath)
    
    if write_to is not None and len(not_uploaded):
        with open(os.path.abspath(write_to),'w') as f:
            f.write('\n'.join(not_uploaded))
    
    return not_uploaded

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
   
    if inDb[0]['Files']['geneerr'] != 'None':    
        with open(os.path.join(path, 'geneerr.log'),'wb+') as f:
            fs.download_to_stream(inDb[0]['Files']['geneerr'], f, session=None)

    for record in inDb:
        '''
        Download 'files'
        '''
        for key, val in record['Files'].items():
            if val != 'None' and key not in ['geneerr']:
                filename = db.fs.files.find_one(val)['filename']
                with open(os.path.join(path, filename),'wb+') as f:
#                    fs.download_to_stream_by_name(filename, f, revision=-1, session=None)
                    fs.download_to_stream(val, f, session=None)
                record['Files'][key] = str(val)
        record['Files']['geneerr'] = str(record['Files']['geneerr'])
        
        '''
        Deal with diagnostic data
        '''
        diag_dict={}
        fsf=gridfs.GridFS(db)
        for key, val in record['Diagnostics'].items():
            if isinstance(val, ObjectId):
#                data = _loadNPArrays(db, val)
#                data = _binary2npArray(fsf.get(val).read()) # no need to store data
                record['Diagnostics'][key] = str(val)
#                data = _binary2npArray(fsf.get(val).read()) 
#                np.save( os.path.join(path,str(record['_id'])+'-'+key), data)
                diag_dict[key] = _binary2npArray(fsf.get(val).read())
            
        with open(os.path.join(path,str(record['_id'])+'-'+'diagnostics.pkl'), 'wb') as handle:
            pickle.dump(diag_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
                
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
    try:
        dir_name = record['Meta']['run_collection_name']
    except TypeError:
        print("Entry not found in database, please double check the id")
        
    path = os.path.join(destination, dir_name.split('/')[-1])
#    path = destination
#    print(destination)
#    print(path)
    if not os.path.exists(path):
        try:
#            path = os.path.join(destination, dir_name.split('/')[-1])
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
    diag_dict = {}
    for key, val in record['Diagnostics'].items():
        if isinstance(val, ObjectId):
#                data = _binary2npArray(fsf.get(val).read()) # no need to store data
            record['Diagnostics'][key] = str(val)
#            data = _binary2npArray(fsf.get(val).read()) 
#            np.save( os.path.join(path,str(record['_id'])+'-'+key), data)
            diag_dict[key] = _binary2npArray(fsf.get(val).read())
            
    with open(os.path.join(path,str(record['_id'])+'-'+'diagnostics.pkl'), 'wb') as handle:
        pickle.dump(diag_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)        

    #print(record)
    record['_id'] = str(_id)

    with open(os.path.join(path, 'mgkdb_summary_for_run'+record['Meta']['run_suffix']+'.json'), 'w') as f:
        json.dump(record, f)
    print("Successfully downloaded files in the collection {} to directory {}".format( record['_id'],path) )   
    


def update_Meta(out_dir, runs_coll, suffix):

    meta_list = ['user', 'run_collection_name', 'run_suffix', 'keywords', 'confidence']
    print("Keys available for update are {}".format(meta_list.sort()))
    
    keys = input('What entries do you like to update? separate your input by comma.\n').split(',')
    vals = input('type your values corresponding to those keys you typed. Separate each category by ; .\n').split(';')
    assert len(keys)==len(vals), 'Input number of keys and values does not match. Abort!'
    for key, val in zip(keys, vals):
    
        runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                         {"$set":{'Meta.'+key: val, "Meta.last_updated": strftime("%y%m%d-%H%M%S")} }
                         )    
    print("Meta{} in {} updated correctly".format(suffix, out_dir))

    
#def update_Parameter(out_dir, runs_coll, suffix):
#    
#    param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
#    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
#                     {"$set":{'Parameters': param_dict}}
#                     )
#    
#    print("Parameters{} in {} updated correctly".format(suffix, out_dir))
    


def update_mongo(out_dir, db, runs_coll, user, linear, sim_type, img_dir = './mgk_diagplots', suffixes=None):
    '''
    only update file related entries, no comparison made before update

    '''

    fs = gridfs.GridFS(db)
    if suffixes is None:
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
            files = []
            files = files + [get_file_list(out_dir, doc+s) for s in suffixes] # get file with path
            assert len(files), "Files specified not found!"
            # delete ALL history
            for file in files:
                grid_out = fs.find({'filepath': file})
                for grid in grid_out:
                    print('File with path tag:\n{}\n'.format(grid.filepath) )
                    fs.delete(grid._id)
                    print('deleted!')

            with open(file, 'rb') as f:
                _id = fs.put(f, encoding='UTF-8', filepath=file, filename=file.split('/')[-1])
#            _id = str(_id)
            updated.append([field, _id])
        
        # update the summary dictionary  
        print('Updating summary dictionary .....')              
        for entry in updated:
            manual_time_flag = True
            for suffix in suffixes:
                if affect_QoI in ['Y', 'y']:
                    GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear) 
                    
                    Diag_dict, manual_time_flag, imag_dict = get_diag_with_user_input(out_dir, suffix,  manual_time_flag, img_dir)
                        
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')
                            
#                    for key, val in run['Plots'].items():
#                        if val != 'None':
#                            print((key, val))
#                            fs.delete(val)
#                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix }, 
                            { "$set": {'gyrokinetics': GK_dict, 'Diagnostics':Diag_dict, 'Plots': imag_dict}} 
                                 )
                    
                runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix}, 
                                 {"$set":{'Files.'+entry[0]: entry[1], 
                                          "Meta.last_updated": strftime("%y%m%d-%H%M%S")}}
                                 )
        
        print("Update complete")
                
    elif update_option == '1':
        files_to_update = input('Please type filenames (without suffixes) for files to update, separated by comma.\n').split(',')
#        suffixes.sort()
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
            manual_time_flag = True
            for suffix in run_suffixes:
                if affect_QoI in ['Y', 'y']:
                    GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear)  
                    
#                    tspan = get_time_for_diag(suffix)
#                    Diag_dict = get_diag_from_run(out_dir, suffix, tspan) 
                    Diag_dict, manual_time_flag, imag_dict = get_diag_with_user_input(out_dir, suffix, manual_time_flag, img_dir)
                    run = runs_coll.find_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            print((key, val))
                            fs.delete(val)
                            print('deleted!')
                            
#                    for key, val in run['Plots'].items():
#                        if val != 'None':
#                            print((key, val))
#                            fs.delete(val)
#                            print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)

                    runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix },
                            { "$set": {'gyrokinetics': GK_dict, 'Diagnostics':Diag_dict, 'Plots': imag_dict}}
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
                                 { "$set": {'Files.'+ doc: _id, "Meta.last_updated": strftime("%y%m%d-%H%M%S")} }
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
                
#        for key, val in run['Plots'].items():
#            if val != 'None':
#                print((key, val))
#                fs.delete(val)
#                print('deleted!')
                    
                
#        delete the header file
        runs_coll.delete_one(run)
        

# =============================================================================
# def upload_file_chunks(db, out_dir, large_files=False, extra_files=False, suffixes = None):
#     '''
#     This function does the actual uploading of grifs chunks and
#     returns object_ids for the chunk.
#     '''
# #    suffixes = get_suffixes(out_dir)
# #    
# #    '''
# #    If there is a shared parameter file or these is only one parameter file
# #    '''
# #    if os.path.isfile(os.path.join(out_dir, 'parameters')):
# #        par_file = os.path.join(out_dir, 'parameters')
# #    elif len(suffixes)==1 and os.path.isfile(os.path.join(out_dir, 'parameters'+suffixes[0])):
# #        par_file = os.path.join(out_dir, 'parameters'+suffixes[0])
# #    else:
# #        os.exit('Cannot locate or decide the parameter file!')
#     
# #    print(out_dir)
# #    if suffixes is None:
# #        par_list = get_file_list(out_dir, 'parameters') # assuming parameter files start with 'parameters' 
# #    else:
# #        par_list = []
# #        par_list = par_list + [get_file_list(out_dir, 'parameters'+s) for s in suffixes]
#     par_list = get_file_list(out_dir, 'parameters') # assuming parameter files start with 'parameters' 
#     if suffixes is not None:
#         for par in par_list:
#             for s in suffixes:
#                 if 'parameters'+ s not in par:
#                     try:
#                         par_list.remove(par) # remove parameter file if no suffix corresponds to it
#                     except:
#                         continue
#         
# #    print(par_list)
#     if len(par_list) == 0:
#         exit('Cannot locate parameter files in folder {}.'.format(out_dir))
#     elif len(par_list) == 1:
#         par_file = par_list[0]
#     elif os.path.join(out_dir, 'parameters') in par_list:
#         par_file = os.path.join(out_dir, 'parameters')
#     else: # assuming all these files share the same 'magn_geometry' and 'mom' info.
#         print('There seems to be multiple parameter files detected:\n')
#         count=0
#         for par in par_list:
#             print('{} : {}\n'.format(count, par.split('/')[-1]))
#             count+=1
#         choice = input('Which one do you want to scan for information.\n')
#         choice = int(choice)
#         par_file = os.path.join(out_dir, par_list[choice])
#         print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_list[choice]))
# 
#     par = Parameters()
#     par.Read_Pars(par_file)
#     pars = par.pardict
#     n_spec = pars['n_spec']
#     
#     if 'magn_geometry' in pars:
#         Docs.append(pars['magn_geometry'][1:-1])
#         Keys.append('magn_geometry')
#     if large_files:
#         if 'name1' in pars and 'mom' in Docs_L:
#             Docs_L.pop(Docs_L.index('mom'))
#             Keys_L.pop(Keys_L.index('mom'))
#             for i in range(n_spec): # adding all particle species
#                 Docs_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
#                 Keys_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
#     
#     output_files = [get_file_list(out_dir, Qname) for Qname in Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
#     
#         
#     if large_files:
#         output_files += [get_file_list(out_dir, Qname) for Qname in Docs_L if Qname]
#     if extra_files:
#         output_files += [get_file_list(out_dir, Qname) for Qname in Docs_ex if Qname]
#         
#     
#     
#     output_files = set([item for sublist in output_files for item in sublist]) # flat the list and remove possible duplicates
#     
# #    print(output_files)
#       
#     object_ids = {}
#     for file in output_files:
#         _id = gridfs_put(db, file)
#         object_ids[_id] = file
# 
# #    print(object_ids)
#     return object_ids
# =============================================================================
        
def upload_file_chunks(db, out_dir, sim_type, large_files=False, extra_files=False, suffix = None, run_shared=None):
    '''
    This function does the actual uploading of grifs chunks and
    returns object_ids for the chunk.
    '''
    
    if suffix is not None:
        par_list = get_file_list(out_dir, 'parameters' + suffix) # assuming parameter files start with 'parameters' 
    else:
        print("Suffix is not provided!")
        
#    print(par_list)
    if len(par_list) == 0:
        exit('Cannot locate parameter files in folder {}.'.format(out_dir))
    elif len(par_list) == 1:
        par_file = par_list[0]
    elif os.path.join(out_dir, 'parameters') in par_list:
        par_file = os.path.join(out_dir, 'parameters')
    else: 
        print('There seems to be multiple files detected starting with parameters{}:\n'.format(suffix))
        count=0
        for par in par_list:
            print('{} : {}\n'.format(count, par.split('/')[-1]))
            count+=1
#        choice = input('Which one do you want to scan for information.\n')
#        choice = int(choice)
#        par_file = os.path.join(out_dir, par_list[choice])
#        print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_list[choice]))
            
        par_list.sort()
        par_file = par_list[0]
        print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_file))

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
    
    output_files = [get_file_list(out_dir, Qname+suffix) for Qname in Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
    
        
    if large_files:
        output_files += [get_file_list(out_dir, Qname+suffix) for Qname in Docs_L if Qname]
    if extra_files:
        output_files += [get_file_list(out_dir, Qname+suffix) for Qname in Docs_ex if Qname]
        
    '''
    Adding files not subject to suffixes, non_suffix should be a list 
    '''
    if isinstance(run_shared,list):
        output_files += [get_file_list(out_dir, ns) for ns in run_shared]
        
#    if 'omega.dat~' in output_files and suffix != '.dat~':
#        output_files.remove('omega.dat~')
    
    output_files = set([item for sublist in output_files for item in sublist]) # flat the list and remove possible duplicates
    
#    print(output_files)
    object_ids = {}
    for file in output_files:
        if os.path.isfile(file):
            _id = gridfs_put(db, file, sim_type)
            object_ids[_id] = file
            
#    reset_docs_keys()
#    print(object_ids)
    return object_ids

def upload_linear(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type,
                  img_dir = './mgk_diagplots', suffixes = None, run_shared = None,
                  large_files=False, extra=False, verbose=True, manual_time_flag = True):
    #connect to linear collection
#    runs_coll = mgkdb_client.mgk_fusion.LinearRuns
    runs_coll = db.LinearRuns
       
    #update files dictionary
#    print(out_dir)
#    print(object_ids)
    if suffixes is None:         
        suffixes = get_suffixes(out_dir)
        
#    object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffixes)  # it changes Docs and Keys globally 


#    print(suffixes)
#    _docs = Docs.copy()
#    _keys = Keys.copy()
#    
#    if large_files:
#        _docs = _docs + Docs_L
#        _keys = _keys + Keys_L
#    if extra:
#        _docs = _docs + Docs_ex
#        _keys = _keys + Keys_ex
#        
#    files_dict = dict.fromkeys(_keys, 'None')
    
#    manual_time_flag = True
        
    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}

        
    for count, suffix in enumerate(suffixes):
        try:
            print('='*40)
            print('Working on files with suffix: {} in folder {}.......'.format(suffix, out_dir))           
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, run_shared)
            else:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, None)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            
            '''
            managing attributes
            '''
            _docs = Docs.copy()
            _keys = Keys.copy()
            
            if large_files:
                _docs = _docs + Docs_L
                _keys = _keys + Keys_L
            if extra:
                _docs = _docs + Docs_ex
                _keys = _keys + Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None') # this removes duplicated keys           
            # _docs = set(_docs)
            # _keys = set(_keys)
            
            print('='*60)
            print('Following files are uploaded.')
            # print(object_ids)
            for _id, line in list(object_ids.items()):  # it is necessary because the dict changes size during loop.
                for Q_name, Key in zip(_docs, _keys):
                    if os.path.join(out_dir,Q_name+suffix) == line:
                        print(Q_name+suffix)
                        if '.' in Key:
                            Key = '_'.join(Key.split('.'))
    
                        files_dict[Key] = _id
                        print("{} file uploaded with id {}".format(Key, _id))
                        try:
                            object_ids.pop(_id)
                        except KeyError:
                            continue
                        break
                
                    if True in shared_not_uploaded and count==0:
                        for S_ind, S_name in enumerate(run_shared):
                            if os.path.join(out_dir,S_name) == line and shared_not_uploaded[S_ind]:
                                print(S_name)
                                if '.' in S_name:
                                    S_name = '_'.join(S_name.split('.'))
                                shared_file_dict[S_name] = _id
                                shared_not_uploaded[S_ind] = False
                            try:
                                object_ids.pop(_id)
                            except KeyError:
                                continue
                    elif count>0 and run_shared is not None:
                        for S_ind, S_name in enumerate(run_shared):
                            print(S_name)
                                           
            files_dict = {**files_dict, **shared_file_dict}
#                if os.path.join(out_dir,'geneerr.log') == line and count==0:
#                    files_dict['geneerr'] = _id
#                    object_ids.pop(_id)
            print('='*60)
            
          
            #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            meta_dict = {"user": user,
                         "run_collection_name": out_dir,
                         "run_suffix": '' + suffix,
                         "keywords": keywords,
                         "simulation_type": sim_type,
                         "confidence": confidence,
                         "comments": comments,
                         "time_uploaded": time_upload,
                         "last_updated": time_upload
                        }  
                   
#            try:
            print('='*60)
            print('\n Working on diagnostics with user specified tspan .....\n')
            Diag_dict, manual_time_flag, imag_dict = get_diag_with_user_input(out_dir, suffix, manual_time_flag, img_dir)
            print('='*60)
            
            print('='*60)
            print('\n Working on OMAS gyrokinetics dictionary using tspan detected from nrg file......\n')
            GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear=True)
            
            ## Save IMAS for any potential tests 
            # with open("gyrokinetics.json", "w") as json_file:
            #     json.dump(GK_dict, json_file, indent=4)

            for key, val in Diag_dict.items():
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)
            
            '''
            Adding omega info to Diag_dict for linear runs
            '''
            omega_val = get_omega(out_dir, suffix)
            Diag_dict['omega'] = {}
            Diag_dict['omega']['ky'] = omega_val[0]
            Diag_dict['omega']['gamma'] = omega_val[1]
            Diag_dict['omega']['omega'] = omega_val[2]
            
    #        param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
            #combine dictionaries and upload
    #        run_data =  {'Meta': meta_dict, 'Files': files_dict, 'QoI': QoI_dict, 'Diagnostics': Diag_dict, 'Parameters': param_dict}
            run_data =  {'Meta': meta_dict, 'Files': files_dict, 'gyrokinetics': GK_dict, 'Diagnostics': Diag_dict, 'Plots': imag_dict}
            runs_coll.insert_one(run_data).inserted_id  
            print('Files with suffix: {} in folder {} uploaded successfully'.format(suffix, out_dir))
            print('='*40)
            if verbose:
                print('A summary is generated as below:\n')
                print(run_data)
        
            '''
            Get a dictionary of what's left in object_ids for possible delayed delete
            '''
            ex_dict = dict()
            for _id, line in object_ids.items():
                if '.' in line:
                    line = '_'.join(line.split('.'))  # if . appears in the key such as nrg_001.h5 -> nrg_001_h5
                ex_dict[line] = _id
                
            if ex_dict: 
                ex_dict['simulation_type']=sim_type
                db.ex.Lin.insert_one(ex_dict)
            
        except Exception as exception:
            print(exception)
            print("Skip suffix {} in \n {}. \n".format(suffix, out_dir))
            _troubled_runs.append(out_dir + '##' + suffix)
            print('cleaning ......')
            fs = gridfs.GridFS(db)
            try:
                for _id, _ in id_copy.items():
                    fs.delete(_id)
                    print('{} deleted.'.format(_id))
            except Exception as eee:
                print(eee)
                pass
            
            continue
                
    reset_docs_keys()
#    print('Run collection \'' + out_dir + '\' uploaded succesfully.')
        
        
def upload_nonlin(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type,
                  img_dir = './mgk_diagplots', suffixes = None, run_shared=None,
                  large_files=False, extra=False, verbose=True, manual_time_flag = True ):
    #connect to nonlinear collection
    runs_coll = db.NonlinRuns
        
    #update files dictionary
    if suffixes is None:
        suffixes = get_suffixes(out_dir)
#    object_ids = upload_file_chunks(db, out_dir, large_files, extra, suffixes)   

#    print(suffixes)
#    print(object_ids)
#    _docs = Docs.copy()
#    _keys = Keys.copy()
#    
#    if large_files:
#        _docs = _docs + Docs_L
#        _keys = _keys + Keys_L
#    if extra:
#        _docs = _docs + Docs_ex
#        _keys = _keys + Keys_ex
#        
#    files_dict = dict.fromkeys(_keys, 'None')
    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}
#    manual_time_flag = True 
    for count, suffix in enumerate(suffixes):
        try:
#        print(suffix)
            print('='*40)
            print('Working on files with suffix: {} in folder {}.......'.format(suffix, out_dir))
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, run_shared)
            else:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, None)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            '''
            managing attributes
            '''
            _docs = Docs.copy()
            _keys = Keys.copy()
            
            if large_files:
                _docs = _docs + Docs_L
                _keys = _keys + Keys_L
            if extra:
                _docs = _docs + Docs_ex
                _keys = _keys + Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None')            
            # _docs = sorted(set(_docs))
            # _keys = sorted(set(_keys))
            # print(_docs)
            # print(_keys)
            
            print('='*60)
            print('Following files are uploaded.')
            # print(object_ids)
            for _id, line in list(object_ids.items()):  
                for Q_name, Key in zip(_docs, _keys):
    #                if line.find(os.path.join(out_dir, Q_name + suffix)) != -1:
                    if os.path.join(out_dir,Q_name+suffix) == line:
    #                if (Q_name + suffix) == line.split('/')[-1]:    
    #                    files_dict[Key] = line.split()[0]
                        print(Q_name+suffix)
                        if '.' in Key:
                            Key = '_'.join(Key.split('.'))
    
                        files_dict[Key] = _id
                        print("{} file uploaded with id {}".format(Key, _id))
                        try:
                            object_ids.pop(_id)
                        except KeyError:
                            continue
                        break
                        
                    if True in shared_not_uploaded and count==0:
                        for S_ind, S_name in enumerate(run_shared):
                            if os.path.join(out_dir,S_name) == line and shared_not_uploaded[S_ind]:
                                print(S_name)
                                if '.' in S_name:
                                    S_name = '_'.join(S_name.split('.'))
                                shared_file_dict[S_name] = _id
                                shared_not_uploaded[S_ind] = False
                            try:
                                object_ids.pop(_id)
                            except KeyError:
                                continue
                    elif count>0 and run_shared is not None:
                        for S_ind, S_name in enumerate(run_shared):
                            print(S_name)
                                           
            files_dict = {**files_dict, **shared_file_dict}
            print('='*60)
            #find relevant quantities from in/output
    #        print(suffix)
            
    #        param_dict = get_parsed_params( os.path.join(out_dir, 'parameters' + suffix) )
    
           #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            meta_dict = {"user": user,
                         "run_collection_name": out_dir,
                         "run_suffix": '' + suffix,
                         "keywords": keywords,
                         "simulation_type": sim_type,
                         "confidence": confidence,
                         "comments": comments,
                         "time uploaded": time_upload,
                         "last_updated": time_upload
                        }
            #data dictionary format for nonlinear runs
    #        QoI_dict, Diag_dict = get_QoI_from_run(out_dir, suffix)
    
    #        tspan = get_time_for_diag(suffix)
    #        Diag_dict = get_diag_from_run(out_dir, suffix, tspan) 
            print('='*60)
            print('\n Working on diagnostics with user specified tspan......\n')
            
            Diag_dict, manual_time_flag, imag_dict = get_diag_with_user_input(out_dir, suffix, manual_time_flag, img_dir)
            
            print('='*60)
            print('\n Working on OMAS gyrokinetics dictionary using tspan detected from nrg file......\n')
            GK_dict = get_gyrokinetics_from_run(out_dir,suffix, user, linear=False)
            
            for key, val in Diag_dict.items():
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)
    
    #        Qes = get_Qes(out_dir, suffix)
    #        QoI_dict = {"Qes" : Qes, **QoI                        
    #                    }
                 
            #combine dictionaries and upload
    #        
    #        run_data =  {''meta_dict, **files_dict, **run_data_dict} 
            run_data =  {'Meta': meta_dict, 'Files': files_dict, 'gyrokinetics': GK_dict, 'Diagnostics': Diag_dict, 'Plots': imag_dict}
            runs_coll.insert_one(run_data).inserted_id  
    
            print('Files with suffix: {} in folder {} uploaded successfully.'.format(suffix, out_dir))
            print('='*40)
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
                ex_dict['simulation_type']=sim_type
                db.ex.Nonlin.insert_one(ex_dict) 
                
        except Exception as exception:
            print(exception)
            print("Skip suffix {} in \n {}. \n".format(suffix, out_dir))
            _troubled_runs.append(out_dir + '##' + suffix)
            print('cleaning ......')
            fs = gridfs.GridFS(db)
            try:
                for _id, _ in id_copy.items():
                    fs.delete(_id)
                    print('{} deleted.'.format(_id))
            except Exception as eee:
                print(eee)
                pass
                
            continue
    
    reset_docs_keys()
            
def upload_to_mongo(db, out_dir, user, linear, confidence, input_heat, keywords, comments, sim_type, 
                    img_dir= './mgk_diagplots', suffixes = None, run_shared=None,
                    large_files = False, extra=False, verbose=True, manual_time_flag = True):
    #print(linear)
    #for linear runs
    if linear:
        #connect to linear collection
        runs_coll = db.LinearRuns
        #check if folder is already uploaded, prompt update?
        print('upload linear runs ******')
        if isUploaded(out_dir, runs_coll):
            update = input('Folder tag:\n {} \n exists in database.  You can:\n 0: Delete and reupload folder? \n 1: Run an update (if you have updated files to add) \n Press any other keys to skip this folder.\n'.format(out_dir))
            if update == '0':
                #for now, delete and reupload instead of update - function under construction
                remove_from_mongo(out_dir, db, runs_coll)   
                upload_linear(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type,
                              img_dir, suffixes, run_shared,
                              large_files, extra, verbose, manual_time_flag)
            elif update == '1':
                update_mongo(out_dir, db, runs_coll, user, linear, sim_type, img_dir)
            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_linear(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type,
                          img_dir, suffixes, run_shared,
                          large_files, extra, verbose, manual_time_flag)
                
    #for nonlinear runs
    elif not linear:
        #connect to nonlinear collection
        runs_coll = db.NonlinRuns
        #check if folder is already uploaded, prompt update?
        print('upload nonlinear runs ******')
        if isUploaded(out_dir, runs_coll):
            update = input('Folder tag:\n {} \n exists in database.  You can:\n 0: Delete and reupload folder? \n 1: Run an update (if you have updated files to add) \n Press any other keys to skip this folder.\n'.format(out_dir))
            if update == '0':
                #for now, delete and reupload instead of update - function under construction
                remove_from_mongo(out_dir, db, runs_coll)   
                upload_nonlin(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type, 
                              img_dir, suffixes, run_shared,
                              large_files, extra, verbose,manual_time_flag)
            elif update == '1':
                update_mongo(out_dir, db, runs_coll, user, linear, sim_type, img_dir)

            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_nonlin(db, out_dir, user, confidence, input_heat, keywords, comments, sim_type,
                          img_dir, suffixes, run_shared,
                          large_files, extra, verbose,manual_time_flag)
    else:
        exit('Cannot decide if the folder is subject to linear or nonlinear runs.')

