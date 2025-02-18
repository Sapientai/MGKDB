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

import sys
import numpy as np
from bson.objectid import ObjectId
import os
from pathlib import Path
import gridfs
import json
from time import strftime
import pickle
from bson.binary import Binary

from .pyro_gk import create_gk_dict_with_pyro
from .ParIO import Parameters
from .diag_plot import diag_plot
from .mgk_post_processing import get_parsed_params, get_suffixes, get_diag_from_run

#=======================================================

class Global_vars():
    '''
    Object to store global variables
    '''
    def __init__(self, sim_type='GENE'):

        if sim_type=="GENE":

            self.Docs = ['autopar', 'nrg', 'omega','parameters']
            self.Keys = ['autopar', 'nrg', 'omega','parameters']

            #Large files#
            self.Docs_L = ['field', 'mom', 'vsp']
            self.Keys_L = ['field', 'mom', 'vsp']

        elif sim_type=='CGYRO':

            self.Docs = ['input.cgyro', 'input.cgyro.gen', 'input.gacode', 'out.cgyro.info']    
            self.Keys = ['input_cgyro', 'input_cgyro_gen', 'input_gacode', 'out_cgyro_info']  

            #Large files#
            self.Docs_L = []
            self.Keys_L = []

        elif sim_type=='TGLF':

            self.Docs = ['input.tglf', 'input.tglf.gen', 'out.tglf.run']    
            self.Keys = ['input_tglf', 'input_tglf_gen', 'out_tglf_run']    

            #Large files#
            self.Docs_L = []
            self.Keys_L = []

        elif sim_type=='GS2':

            self.Docs = ['gs2.in','gs2.out.nc']    
            self.Keys = ['gs2_in','gs2_out_nc']    

            #Large files#
            self.Docs_L = []
            self.Keys_L = []
        else : 
            print("Invalid simulation type",sim_type)
            raise SystemError
        #User specified files#
        self.Docs_ex = [] 
        self.Keys_ex = []

        self.file_related_keys = self.Keys + self.Keys_L + self.Keys_ex
        self.file_related_docs = self.Docs + self.Docs_L + self.Docs_ex
        self.troubled_runs = [] # a global list to collection runs where exception happens

    def reset_docs_keys(self,sim_type):
        ## Reset values 
        self.__init__(sim_type)
        print("File names and their key names are reset to default!")



def f_set_metadata(user=None,out_dir=None,suffix=None,keywords=None,confidence=-1,comments='Uploaded with default settings.',time_upload=None,\
                   last_update=None, linked_ID=None, expt=None, scenario_runid=None, linear=None, quasiLinear=None, has_1dflux = None, sim_type=None,\
                   git_hash=None, platform=None, ex_date=None, workflow_type=None, archive_loc=None):

    metadata={
        'DBtag': { 
            'user': user,
            'run_collection_name': out_dir,
            'run_suffix': suffix,
            'keywords':keywords,
            'confidence': confidence,
            'comments': comments,
            'time_uploaded': time_upload,
            'last_updated': last_update,
            'linkedObjectID': linked_ID, 
            'archiveLocation': archive_loc,
        },
        'ScenarioTag': { 
                    'Name of actual of hypothetical experiment': expt,
                    'scenario_runid': scenario_runid,
            },
        'CodeTag': { 
                'sim_type': sim_type,
                'IsLinear': linear,
                'quasi_linear': quasiLinear,
                'Has1DFluxes': has_1dflux,
                'git_hash': git_hash,
                'platform': platform,
                'execution_date': ex_date,
                'workflow_type': workflow_type
            },
        'Publications': { 
                'doi': [] 
            }
    }
    
    return metadata

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

def get_diag_with_user_input(out_dir, suffix,  manual_time_flag):

    if manual_time_flag:
        tspan = get_time_for_diag(suffix)
        if tspan == -1:
            manual_time_flag = False
            Diag_dict = get_diag_from_run(out_dir, suffix, None)
        else:
            Diag_dict = get_diag_from_run(out_dir, suffix, tspan) 
    else:
        Diag_dict = get_diag_from_run(out_dir, suffix, None)
        
    return Diag_dict, manual_time_flag

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

def gridfs_put(db, filepath,sim_type):
    #set directory and filepath
    file = open(filepath, 'rb')

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
    
    
def load(db, collection, query, projection={'Metadata':1, 'gyrokineticsIMAS':1, 'Diagnostics':1}, getarrays=True):
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

def query_plot(db, collection, query, projection = {'Metadata':1, 'Diagnostics':1}):
    data_list = load(db, collection, query, projection)
    print('{} records found.'.format(len(data_list)))
    
    data_to_plot = [diag_plot(da) for da in data_list]
    
    for i in range(len(data_to_plot)):
         data_to_plot.plot_all()    
    
    
def isLinear(folder_name, sim_type):
    linear = None

    #check file for 'nonlinear' value
    suffixes = get_suffixes(folder_name, sim_type)
    
    if len(suffixes):
        suffixes.sort()
        suffix = suffixes[0] #assuming all parameters files are of the same linear/nonlinear type
        print('Scanning parameters{} for deciding linear/Nonlinar.')
    else:
        suffix = ''

    if sim_type=='GENE': 
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
        
    elif sim_type=='CGYRO':
        fname=os.path.join(folder_name+'/{0}/input.cgyro'.format(suffix))
        assert os.path.isfile(fname),"File %s does not exist"%(fname)

        non_lin = None
        with open(fname,'r') as f:
            for line in f: 
                if line.split('=')[0].strip()=='NONLINEAR_FLAG':
                    non_lin = int(line.split('=')[1].strip()) # Remove blank space to just get 0 or 1
        
        assert non_lin is not None, "Didn't find NONLINEAR_FLAG in file(%s)"%(fname) 

        linear = False if non_lin else True
        return linear
    
    elif sim_type=='TGLF':

        fname=os.path.join(folder_name+'/{0}/input.tglf'.format(suffix))
        assert os.path.isfile(fname),"File %s does not exist"%(fname)

        with open(fname,'r') as f:
            for line in f: 
                val = line.split('=')

                if val[0].strip()=='USE_TRANSPORT_MODEL':
                    true_present  = [strg in val[1].strip() for strg in ['true','T','t']]
                    false_present = [strg in val[1].strip() for strg in ['false','F','f']]
                    if any(true_present): 
                        linear = False ## run is non linear
                    elif any(false_present):
                        linear = True 
                    else : 
                        print("Unknown entry in parameter file for field \"USE_TRANSPORT_MODEL\" ",line)
                        raise SystemError
                    break
        return linear
    
    elif sim_type=='GS2':
        return True
    

def isUploaded(out_dir,runs_coll):
    '''
    check if out_dir appears in the database collection.
    Assuming out_dir will appear no more than once in the database
    '''
    inDb = runs_coll.find({ "Metadata.DBtag.run_collection_name": out_dir })

    entries = list(inDb)
    uploaded = True if len(entries)>0 else False 
    
    # uploaded = False
    # for run in inDb:
    #     if run["Metadata"]["run_collection_name"] == out_dir: # seems redundent?
    #         uploaded = True
    #         break
    
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
    inDb = runs_coll.find({ "Metadata.DBtag.run_collection_name": out_dir })
    record = []
    for run in inDb:
#        dic = dict()
#        for key, val in run.items():
#            dic[key] = val
#        record.append(dic)
        record.append(run)
    return record
   


    ## Extract linked_ID

def f_check_id_exists(db, _id):
    ''' Given an object ID, check if it exists in linear or nonlinear collections
    '''

    for collection in ['LinearRuns','NonlinRuns']:
        runs_coll =  getattr(db,collection)

        try: 
            record = runs_coll.find_one({"_id": _id})
        except Exception as e:
            # print(e)
            print("Invalid object ID",_id)
            return False
    
        if record is not None: return True

    print("Entry %s not found in database, please double check the id"%(_id))
    return False

def f_get_linked_oid(database, linked_id_file, linked_id_string):
    '''
    Get linked ObjectID
    '''

    if ((linked_id_file is not None) and (linked_id_string is not None)): 
        print("Both linked_id_file and linked_id_string specified. Please choose any one and re-upload")
        raise SystemError

    elif linked_id_file is not None:
        fname = linked_id_file
        assert os.path.exists(fname), "File %s does not exist"%(fname)
        print("Input file for OID is %s",fname)

        ## Get OID from file 
        with open(fname, 'r') as f:
            data_dict = json.load(f)

        oid = ObjectId(data_dict['_id'])

    elif linked_id_string is not None: 
        oid = ObjectId(linked_id_string)

    else:  oid = None

    if oid is not None: 
        id_exists = f_check_id_exists(database, oid)

        if id_exists:
            print("Linked OID %s"%(oid))
            return oid
        else : 
            return None
    else: return None


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
    destination: local path to put the file
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
    dir_name: as appear in db.Metadata['run_collection_name']
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
    inDb = runs_coll.find({ "Metadata.DBtag.run_collection_name": dir_name })

    if 'generr' in inDb[0]['Files'].keys(): ## Fix for when 'generr' doesn't exist
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
        if 'generr' in record['Files'].keys():  ## Fix for when 'generr' doesn't exist 
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
        with open(os.path.join(path, 'mgkdb_summary_for_run'+record['Metadata']['run_suffix']+'.json'), 'w') as f:
            json.dump(record, f)
           
    print ("Successfully downloaded to the directory %s " % path)


def download_runs_by_id(db, runs_coll, _id, destination):
    '''
    Download all files in collections by the id of the summary dictionary.
    '''
    
    fs = gridfs.GridFSBucket(db)
    record = runs_coll.find_one({ "_id": _id })
    try:
        dir_name = record['Metadata']['DBtag']['run_collection_name']
    except TypeError:
        print("Entry not found in database, please double check the id")
        raise SystemExit
        
    path = os.path.join(destination, dir_name.split('/')[-1])

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

    with open(os.path.join(path, 'mgkdb_summary_for_run'+record['Metadata']['DBtag']['run_suffix']+'.json'), 'w') as f:
        json.dump(record, f)
    print("Successfully downloaded files in the collection {} to directory {}".format( record['_id'],path) )   
    


# def update_Meta(out_dir, runs_coll, suffix):

#     meta_list = ['user', 'run_collection_name', 'run_suffix', 'keywords', 'confidence']
#     print("Keys available for update are {}".format(meta_list.sort()))
    
#     keys = input('What entries do you like to update? separate your input by comma.\n').split(',')
#     vals = input('type your values corresponding to those keys you typed. Separate each category by ; .\n').split(';')
#     assert len(keys)==len(vals), 'Input number of keys and values does not match. Abort!'
#     for key, val in zip(keys, vals):
    
#         runs_coll.update_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix}, 
#                          {"$set":{'Metadata.DBtag.'+key: val, "Metadata.DBtag.last_updated": strftime("%y%m%d-%H%M%S")} }
#                          )    
#     print("Metadata{} in {} updated correctly".format(suffix, out_dir))

    
#def update_Parameter(out_dir, runs_coll, suffix):
#    
#    param_dict = get_parsed_params(os.path.join(out_dir, 'parameters' + suffix) )
#    runs_coll.update_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix}, 
#                     {"$set":{'Parameters': param_dict}}
#                     )
#    
#    print("Parameters{} in {} updated correctly".format(suffix, out_dir))
    

def update_mongo(db, metadata, out_dir, runs_coll, linear, suffixes=None):

    '''
    only update file related entries, no comparison made before update
    '''
    
    # user = metadata['DBtag']['user']
    # linked_id = metadata['DBtag']['linkedObjectID']
    sim_type = metadata['CodeTag']['sim_type']

    fs = gridfs.GridFS(db)
    if suffixes is None:
        suffixes = get_suffixes(out_dir, sim_type)  
        
    update_option = input('Enter options for update:\n 0: Files shared by all runs, usually do not have a suffix. \n 1: Unique files used per run. Specify the keywords and suffixes. \n ')
    if update_option == '0':
        files_to_update = input('Please type FULL file names to update, separated by comma.\n').split(',')
        keys_to_update = input('Please type key names for each file you typed, separated by comma.\n').split(',')

        updated = []
        print('Uploading files .......')
        # update the storage chunk
        for doc, field in zip(files_to_update, keys_to_update):
            
            file = os.path.join(out_dir, doc)
            assert os.path.exists(file), "File %s not found"%(file)
            
            # delete ALL history
            grid_out = fs.find({'filepath': file})
            for grid in grid_out:
                print('File with path tag:\n{}\n'.format(grid.filepath) )
                fs.delete(grid._id)
                print('deleted!')

            with open(file, 'rb') as f:
                _id = fs.put(f, encoding='UTF-8', filepath=file, filename=file.split('/')[-1])
            
            updated.append([field, _id])
        
        # update the summary dictionary  
        print('Updating Metadata')              
        for entry in updated:
            for suffix in suffixes:                    
                runs_coll.update_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix}, 
                                 {"$set":{'Files.'+entry[0]: entry[1], 
                                          "Metadata.DBtag.last_updated": strftime("%y%m%d-%H%M%S")}}
                                 )
        print("Update complete")
                
    elif update_option == '1':
        files_to_update = input('Please type filenames (without suffixes) for files to update, separated by comma.\n').split(',')
        print("suffixes availables are:{}".format(suffixes))
        runs_to_update = input('Please type which suffixes to update, separated by comma. If you need to update all runs, just hit ENTER. \n').split(',')      
        # affect_QoI = input('Will the file change QoIs/Diagnostics? (Y/N)')
        affect_QoI = True

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
                if affect_QoI:
                    input_fname = f_get_input_fname(out_dir, suffix, sim_type)
                    GK_dict, quasi_linear = create_gk_dict_with_pyro(input_fname, sim_type)   

                    if sim_type in ['CGYRO','TGLF','GS2']:
                        Diag_dict = {}
                    elif sim_type=='GENE': 
                        Diag_dict, manual_time_flag = get_diag_with_user_input(out_dir, suffix, manual_time_flag)

                    run = runs_coll.find_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix})
                    for key, val in run['Diagnostics'].items():
                        if val != 'None':
                            # print((key, val))
                            fs.delete(val)
                            # print('deleted!')

                    for key, val in Diag_dict.items():
                        Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)

                    runs_coll.update_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix },
                            { "$set": {'gyrokineticsIMAS': GK_dict, 'Diagnostics':Diag_dict}}
                                 )

                file = os.path.join(out_dir, doc  + suffix)
                grid_out = fs.find({'filepath': file})
                for grid in grid_out:
                    print('File with path tag:\n{}\n'.format(grid.filepath) )
                    fs.delete(grid._id)
                    print('deleted!')
                
                with open(file, 'rb') as f:
                    _id = fs.put(f, encoding='UTF-8', filepath=file, filename=file.split('/')[-1])

                runs_coll.update_one({ "Metadata.DBtag.run_collection_name": out_dir, "Metadata.DBtag.run_suffix": suffix }, 
                                 { "$set": {'Files.'+ doc: _id, "Metadata.DBtag.last_updated": strftime("%y%m%d-%H%M%S")} }
                                 )
        print("Update complete")
    
    else:
        print('Invalid input. Update aborted.')
        pass
    
def remove_from_mongo(out_dir, db, runs_coll):
    #find all documents containing collection name
        
    inDb = runs_coll.find({ "Metadata.DBtag.run_collection_name": out_dir })        
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
        
def upload_file_chunks(db, out_dir, sim_type, large_files=False, extra_files=False, suffix = None, run_shared=None, global_vars=None):
    '''
    This function does the actual uploading of gridfs chunks and
    returns object_ids for the chunk.
    '''

    if sim_type=='GENE': 
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
             
            par_list.sort()
            par_file = par_list[0]
            print('File {} selected for scanning [magn_geometry] and [mom] information.'.format(par_file))

        par = Parameters()
        par.Read_Pars(par_file)
        pars = par.pardict
        n_spec = pars['n_spec']
        
        ## Get geometry from parameters file and add that to list of files to save
        if 'magn_geometry' in pars:
            global_vars.Docs.append(pars['magn_geometry'][1:-1])
            global_vars.Keys.append(pars['magn_geometry'][1:-1])
        if large_files:
            if 'name1' in pars and 'mom' in global_vars.Docs_L:
                global_vars.Docs_L.pop(global_vars.Docs_L.index('mom'))
                global_vars.Keys_L.pop(global_vars.Keys_L.index('mom'))
                for i in range(n_spec): # adding all particle species
                    global_vars.Docs_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
                    global_vars.Keys_L.append('mom_'+pars['name{}'.format(i+1)][1:-1])
    

    if sim_type=='GENE':
        output_files = [get_file_list(out_dir, Qname+suffix) for Qname in global_vars.Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
        
        if large_files:
            output_files += [get_file_list(out_dir, Qname+suffix) for Qname in global_vars.Docs_L if Qname]
        if extra_files:
            output_files += [get_file_list(out_dir, Qname+suffix) for Qname in global_vars.Docs_ex if Qname]
    
    elif sim_type in ['CGYRO','TGLF','GS2']:
        output_files = [get_file_list(out_dir+'/%s/'%(suffix),Qname) for Qname in global_vars.Docs if Qname] # get_file_list may get more files than expected if two files start with the same string specified in Doc list
        
        if large_files:
            output_files += [get_file_list(out_dir+'/%s/'%(suffix),Qname) for Qname in global_vars.Docs_L if Qname]
        if extra_files:
            output_files += [get_file_list(out_dir+'/%s/'%(suffix),Qname) for Qname in global_vars.Docs_ex if Qname]
    
    ## Adding files not subject to suffixes, non_suffix should be a list 
    if isinstance(run_shared,list):
        output_files += [get_file_list(out_dir, ns) for ns in run_shared]
 
    output_files = set([item for sublist in output_files for item in sublist]) # flat the list and remove possible duplicates
    
    object_ids = {}
    for file in output_files:
        if os.path.isfile(file):
            _id = gridfs_put(db, file, sim_type)
            object_ids[_id] = file
            
    return object_ids

def f_get_input_fname(out_dir, suffix, sim_type):
    ''''
    Get the name of the input file with suffix for the simluation type
    '''
    fname_dict = {'CGYRO':out_dir+'/{0}/input.cgyro'.format(suffix),\
                    'TGLF':out_dir+'/{0}/input.tglf'.format(suffix),\
                    'GENE':out_dir+'/parameters{0}'.format(suffix),
                    'GS2': out_dir+'/{0}/gs2.in'.format(suffix)
                }

    return fname_dict[sim_type]

def upload_linear(db, metadata, out_dir, suffixes = None, run_shared = None,
                  large_files=False, extra=False, verbose=True, manual_time_flag = True, global_vars=None):
    
    # user = metadata['DBtag']['user']
    sim_type = metadata['CodeTag']['sim_type']

    #connect to linear collection
    runs_coll = db.LinearRuns
       
    #update files dictionary
    if suffixes is None:         
        suffixes = get_suffixes(out_dir, sim_type)

    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}

    for count, suffix in enumerate(suffixes):
        try:
            print('='*40)
            print('Working on files with suffix: {} in folder {}.......'.format(suffix, out_dir))           

            ### First compute gyrokinetics IMAS using pyrokinetics package
            print("Computing gyrokinetics IMAS using pyrokinetics")
            input_fname = f_get_input_fname(out_dir, suffix, sim_type)
            GK_dict, quasi_linear = create_gk_dict_with_pyro(input_fname, sim_type)

            ### Upload files to DB 
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, run_shared, global_vars)
            else:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, None,global_vars)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            
            '''
            managing attributes
            '''
            _docs = global_vars.Docs.copy()
            _keys = global_vars.Keys.copy()
            
            if large_files:
                _docs = _docs + global_vars.Docs_L
                _keys = _keys + global_vars.Keys_L
            if extra:
                _docs = _docs + global_vars.Docs_ex
                _keys = _keys + global_vars.Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None') # this removes duplicated keys           
            
            print('='*60)
            print('Following files are uploaded.')
            # print(object_ids)
            for _id, line in list(object_ids.items()):  # it is necessary because the dict changes size during loop.
                for Q_name, Key in zip(_docs, _keys):
                    if sim_type=='GENE' :     fname = os.path.join(out_dir,Q_name+suffix)
                    elif sim_type in ['CGYRO','TGLF','GS2'] :  fname = os.path.join(out_dir+'/%s/'%(suffix),Q_name)
                    
                    if fname == line:
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
            

            #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            
            metadata['DBtag']['run_collection_name'] = out_dir
            metadata['DBtag']['run_suffix']=''+ suffix
            metadata['DBtag']['time_uploaded'] = time_upload
            metadata['DBtag']['last_updated']  = time_upload
            metadata['CodeTag']['IsLinear'] = True
            metadata['CodeTag']['quasi_linear'] = quasi_linear
            metadata['CodeTag']['Has1DFluxes'] = GK_dict['non_linear']['fluxes_1d']['particles_phi_potential']!=0

            meta_dict = metadata

            if sim_type in ['CGYRO','TGLF','GS2']:
                Diag_dict = {}
            elif sim_type=='GENE': 
                print('='*60)
                print('\n Working on diagnostics with user specified tspan .....\n')
                Diag_dict, manual_time_flag = get_diag_with_user_input(out_dir, suffix, manual_time_flag)
                print('='*60)
                for key, val in Diag_dict.items():
                    Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)

                ## Adding omega info to Diag_dict for linear runs
                omega_val = get_omega(out_dir, suffix)
                Diag_dict['omega'] = {}
                Diag_dict['omega']['ky'] = omega_val[0]
                Diag_dict['omega']['gamma'] = omega_val[1]
                Diag_dict['omega']['omega'] = omega_val[2]


            run_data =  {'Metadata': meta_dict, 'Files': files_dict, 'gyrokineticsIMAS': GK_dict, 'Diagnostics': Diag_dict}
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
            global_vars.troubled_runs.append(out_dir + '##' + suffix)
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
                
    global_vars.reset_docs_keys(sim_type)
        
        
def upload_nonlin(db, metadata, out_dir, suffixes = None, run_shared=None,
                  large_files=False, extra=False, verbose=True, manual_time_flag = True , global_vars=None):
    
    # user = metadata['DBtag']['user']
    sim_type = metadata['CodeTag']['sim_type']

    #connect to nonlinear collection
    runs_coll = db.NonlinRuns
        
    #update files dictionary
    if suffixes is None:
        suffixes = get_suffixes(out_dir, sim_type)
    if isinstance(run_shared, list):
        shared_not_uploaded = [True for _ in run_shared]
    else:
        shared_not_uploaded = [False]
    shared_file_dict = {}
#    manual_time_flag = True 
    for count, suffix in enumerate(suffixes):
        try:
            print('='*40)
            print('Working on files with suffix: {} in folder {}.......'.format(suffix, out_dir))

            ### First compute gyrokinetics IMAS using pyrokinetics package
            print("Computing gyrokinetics IMAS using pyrokinetics")
            input_fname = f_get_input_fname(out_dir, suffix, sim_type)
            GK_dict, quasi_linear = create_gk_dict_with_pyro(input_fname, sim_type)

            ### Upload files to DB 
            print('Uploading files ....')
            if count == 0:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, run_shared, global_vars)
            else:
                object_ids = upload_file_chunks(db, out_dir, sim_type, large_files, extra, suffix, None, global_vars)
            id_copy = object_ids.copy() # make a copy to delete from database if following routine causes exceptions
            '''
            managing attributes
            '''
            _docs = global_vars.Docs.copy()
            _keys = global_vars.Keys.copy()
            
            if large_files:
                _docs = _docs + global_vars.Docs_L
                _keys = _keys + global_vars.Keys_L
            if extra:
                _docs = _docs + global_vars.Docs_ex
                _keys = _keys + global_vars.Keys_ex
                
            files_dict = dict.fromkeys(_keys, 'None')          
            
            print('='*60)
            print('Following files are uploaded.')
            # print(object_ids)
            for _id, line in list(object_ids.items()):  
                for Q_name, Key in zip(_docs, _keys):
                    if sim_type=='GENE' :  fname = os.path.join(out_dir,Q_name+suffix)
                    elif sim_type in ['CGYRO','TGLF','GS2'] :  fname = os.path.join(out_dir+'/%s/'%(suffix),Q_name)
                    
                    if fname == line:
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
    
           #metadata dictonary
            time_upload = strftime("%y%m%d-%H%M%S")
            
            metadata['DBtag']['run_collection_name'] = out_dir
            metadata['DBtag']['run_suffix']=''+ suffix
            metadata['DBtag']['time_uploaded'] = time_upload
            metadata['DBtag']['last_updated']  = time_upload
            metadata['CodeTag']['IsLinear'] = False
            metadata['CodeTag']['quasi_linear'] = quasi_linear
            metadata['CodeTag']['Has1DFluxes'] = GK_dict['non_linear']['fluxes_1d']['particles_phi_potential']!=0

            meta_dict = metadata

            #data dictionary format for nonlinear runs
            if sim_type in ['CGYRO','TGLF','GS2']:
                Diag_dict = {}
            elif sim_type=='GENE':
                print('='*60)
                print('\n Working on diagnostics with user specified tspan .....\n')
                Diag_dict, manual_time_flag = get_diag_with_user_input(out_dir, suffix, manual_time_flag)
                print('='*60)
                for key, val in Diag_dict.items():
                    Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], out_dir, key, sim_type)

            #combine dictionaries and upload
            run_data =  {'Metadata': meta_dict, 'Files': files_dict, 'gyrokineticsIMAS': GK_dict, 'Diagnostics': Diag_dict}
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
            global_vars.troubled_runs.append(out_dir + '##' + suffix)
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
    
    global_vars.reset_docs_keys(sim_type)
            
def upload_to_mongo(db, linear, metadata, out_dir, suffixes = None, run_shared=None,
                    large_files = False, extra=False, verbose=True, manual_time_flag = True, global_vars=None):
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
                upload_linear(db, metadata, out_dir, suffixes, run_shared,
                              large_files, extra, verbose, manual_time_flag, global_vars)
            elif update == '1':
                update_mongo(db, metadata, out_dir, runs_coll, linear)
            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_linear(db, metadata, out_dir, suffixes, run_shared,
                          large_files, extra, verbose, manual_time_flag, global_vars)
                
    #for nonlinear runs
    elif not linear:
        #connect to nonlinear collection
        runs_coll = db.NonlinRuns
        #check if folder is already uploaded, prompt update?
        print('upload nonlinear runs ******')
        if isUploaded(out_dir, runs_coll):
            update = input('Folder tag:\n {} \n exists in database.  You can:\n 0: Delete and reupload folder? \n 1: Run an update (if you have updated files to add) \n Press any other keys to skip this folder.\n'.format(out_dir))
            if update == '0':
                remove_from_mongo(out_dir, db, runs_coll)   
                upload_nonlin(db, metadata, out_dir, suffixes, run_shared,
                              large_files, extra, verbose,manual_time_flag, global_vars)
            elif update == '1':
                update_mongo(db, metadata, out_dir, runs_coll, linear)

            else:
                print('Run collection \'' + out_dir + '\' skipped.')
        else:
            print('Folder tag:\n{}\n not detected, creating new.\n'.format(out_dir))
            upload_nonlin(db, metadata, out_dir, suffixes, run_shared,
                          large_files, extra, verbose,manual_time_flag, global_vars)
    else:
        exit('Cannot decide if the folder is subject to linear or nonlinear runs.')

