"""
Created on Wed Feb 26 15:08:36 2020

@author: dykuang

Make plots of some diagnostics
"""
from mgk_file_handling import load, _binary2npArray, _loadNPArrays, gridfs_put_npArray, clear_ex_lin, clear_ex_Nonlin, clear_ex, get_oid_from_query, get_omega
from mgk_post_processing import get_gyrokinetics_from_run, get_diag_from_run
import os
from mgk_login import mgk_login
import argparse
from sys import exit
from diag_plot import diag_plot
from bson.objectid  import ObjectId
import numpy as np
import pickle
#from bson import BSON
#import codec
import gridfs
from pathlib import Path
import json
import base64
import pandas as pd
from time import strftime

def get_spec_nums(pars):
    enum = False
    inum = False
    znum = False
    for i in range(pars['n_spec']):
        charge = 'charge'+str(i+1)
        if charge in pars:
            if pars[charge] == -1: 
                enum = str(i+1)
            elif pars[charge] == 1:
                inum = str(i+1)
            elif pars[charge] > 1:
                znum = str(i+1)
    return inum,enum,znum

def get_nrg(db,coll,oid):
    nrg_raw = get_file_by_id(db,coll,ObjectId(oid),'nrg')
    nrg_split = nrg_raw.split('\n')
    for i in range(2,10):
        if len(nrg_split[i]) < 100:
            it2 = i
            break
    nspec = it2-1
    #print("number of species:",nspec)
    time=np.empty(0,dtype='float')
    nrg1=np.empty((0,10),dtype='float')

    if nspec<=2:
        nrg2=np.empty((0,10),dtype='float')
    if nspec<=3:
        nrg2=np.empty((0,10),dtype='float')
        nrg3=np.empty((0,10),dtype='float')
    if nspec>=4:
        print( "nspec=",nspec)
        print( "Error, nspec must be less than 4")
#        stop

    ncols = int(len(nrg_split[1])/12)

    nrg0=np.empty((1,ncols))
    #print nrg_in
    for j in range(len(nrg_split)):
        if nrg_split[j] and j % (nspec+1) == 0:
            time=np.append(time,float(nrg_split[j]))
        elif nrg_split[j] and j % (nspec+1) == 1:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg1=np.append(nrg1,nrg0,axis=0)
        elif nspec>=2 and nrg_split[j] and j % (nspec+1) ==2:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg2=np.append(nrg2,nrg0,axis=0)
        elif nspec==3 and nrg_split[j] and j % (nspec+1) ==3:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg3=np.append(nrg3,nrg0,axis=0)

    nrg_dict = {}
    nrg_dict['time'] = time
    nrg_dict['nrg1'] = nrg1
    if nspec==2:
        nrg_dict['nrg2'] = nrg2
    elif nspec==3:
        nrg_dict['nrg2'] = nrg2
        nrg_dict['nrg3'] = nrg3

    return nrg_dict

def get_magn_geometry(db,coll,oid):
    file_raw = get_file_by_id(db,coll,ObjectId(oid),'magn_geometry')
    if file_raw != None:
        file_lines = file_raw.split('\n')

    parameters = {}
    l = 1
    while '/' not in file_lines[l] and len(file_lines[l])>0:
        lsplit = file_lines[l].split('=')
    #    print lsplit[0].strip()
        if lsplit[0].strip() == 'gridpoints':
            parameters[lsplit[0].strip()] = int(float(lsplit[1].strip()))
        elif lsplit[0].strip() == 'magn_geometry':
            parameters[lsplit[0].strip()] = lsplit[1].strip()[1:-1]
        elif len(lsplit[0]) > 0:
            parameters[lsplit[0].strip()] = float(lsplit[1])
        l += 1
        #print "lsplit",lsplit
    
    #print parameters

    geometry = {}
    #1. ggxx(pi1,pj1,k) 
    geometry['ggxx'] = np.empty(0)
    #2. ggxy(pi1,pj1,k)
    geometry['ggxy'] = np.empty(0)
    #3. ggxz(pi1,pj1,k)
    geometry['ggxz'] = np.empty(0)
    #4. ggyy(pi1,pj1,k) 
    geometry['ggyy'] = np.empty(0)
    #5. ggyz(pi1,pj1,k)
    geometry['ggyz'] = np.empty(0)
    #6. ggzz(pi1,pj1,k)
    geometry['ggzz'] = np.empty(0)
    #7. gBfield(pi1,pj1,k) 
    geometry['gBfield'] = np.empty(0)
    #8. gdBdx(pi1,pj1,k)
    geometry['gdBdx'] = np.empty(0)
    #9. gdBdy(pi1,pj1,k)
    geometry['gdBdy'] = np.empty(0)
    #10. gdBdz(pi1,pj1,k)
    geometry['gdBdz'] = np.empty(0)
    #11. gjacobian(pi1,pj1,k)
    geometry['gjacobian'] = np.empty(0)
    #12. gl_R(pi1,k)
    geometry['gl_R'] = np.empty(0)
    #13. gl_phi(pi1,k)
    geometry['gl_phi'] = np.empty(0)
    #14. gl_z(pi1,k)
    geometry['gl_z'] = np.empty(0)
    #15. gl_dxdR(pi1,k)
    geometry['gl_dxdR'] = np.empty(0)
    #16. gl_dxdZ(pi1,k)
    geometry['gl_dxdZ'] = np.empty(0)

    if 'sign_Ip_CW' in file_raw: 
        l += 4
    else:
        l += 1
    while file_lines[l]:
        line = file_lines[l].split()
        geometry['ggxx'] = np.append(geometry['ggxx'],float(line[0].strip()))
        geometry['ggxy'] = np.append(geometry['ggxy'],float(line[1].strip()))
        geometry['ggxz'] = np.append(geometry['ggxz'],float(line[2].strip()))
        geometry['ggyy'] = np.append(geometry['ggyy'],float(line[3].strip()))
        geometry['ggyz'] = np.append(geometry['ggyz'],float(line[4].strip()))
        geometry['ggzz'] = np.append(geometry['ggzz'],float(line[5].strip()))
        geometry['gBfield'] = np.append(geometry['gBfield'],float(line[6].strip()))
        geometry['gdBdx'] = np.append(geometry['gdBdx'],float(line[7].strip()))
        geometry['gdBdy'] = np.append(geometry['gdBdy'],float(line[8].strip()))
        geometry['gdBdz'] = np.append(geometry['gdBdz'],float(line[9].strip()))
        geometry['gjacobian'] = np.append(geometry['gjacobian'],float(line[10].strip()))
        geometry['gl_R'] = np.append(geometry['gl_R'],float(line[11].strip()))
        geometry['gl_phi'] = np.append(geometry['gl_phi'],float(line[12].strip()))
        geometry['gl_z'] = np.append(geometry['gl_z'],float(line[13].strip()))
        geometry['gl_dxdR'] = np.append(geometry['gl_dxdR'],float(line[14].strip()))
        geometry['gl_dxdZ'] = np.append(geometry['gl_dxdZ'],float(line[15].strip()))
        #print "l",l,float(line[15])
        l += 1
        
    
    #for i in geometry:
    #    plt.title(i)
    #    plt.plot(geometry[i])
    #    plt.show()    

    return parameters, geometry


def get_demo_data(db, collection, query={}, projection={'Meta':1, 'gyrokinetics':1, 'Diagnostics':1},
                  pkey = ['beta', 'debye2', 'hyp_z', 'hyp_v', 'minor_r', 'major_R', 'rhostar', 'dpdx_pm',
                          'lx', 'ly', 'nu_ei', 'Bref', 'Tref', 'nref', 'Lref', 'mref']):
    data = load(db, collection, query, projection)
    extracted_val = []
    extracted_cat = []
    for record in data:
        temp = [record['Meta']['run_collection_name'], record['Meta']['run_suffix'] ]
        
        # value in gyrokey
        for p in pkey:
            if p in record['gyrokinetics']['code']['parameters'].keys():
                temp.append(record['gyrokinetics']['code']['parameters'][p])
            else:
                temp.append(np.nan)
        # species
        spec_name=[]
        for spec in record['gyrokinetics']['species']:
             spec_name.append(spec['name']) 
        # omega
        temp.append(record['Diagnostics']['omega']['ky'])
        temp.append(record['Diagnostics']['omega']['gamma'])
        temp.append(record['Diagnostics']['omega']['omega'])
        
        extracted_val.append(temp)
        extracted_cat.append(spec_name)
        
    pd_val = pd.DataFrame(extracted_val, columns=pkey+['ky', 'gamma', 'omega'])
    pd_val.insert(0,'species', extracted_cat)
    
    
    return pd_val

'''
Getting some derived quantities
'''
#from format_files_mgkdb import *
from D_chi_ratio_mgkdb import *
from mode_tools_mgkdb import *

def get_demo_derived_data(db, collection, query={}, projection={'Meta':1, 'gyrokinetics':1, 'Diagnostics':1}):
    
    data = load(db, collection, query, projection)
    derived = []
    
    for record in data:
        try:
            specs = []
            ename = 'none'
            pardict = record['gyrokinetics']['code']['parameters']
            for i in range(5):
                name = 'name'+str(i+1)
                if name in pardict:
                    specs.append(pardict[name][1:-1])
                    if pardict[name][1:-1] == 'e' or pardict[name][1:-1] == 'electrons' or pardict[name][1:-1]== 'Electrons':
                        ename = name
                        enum = str(i+1)
            
    #        print("ename",ename)
    #        print(specs)
            if ename == 'none':
                print("Electrons not found.  This script only operates with an electron species.")
    #            os.exit()
                enum = '1'
                
            ky = record['Diagnostics']['omega']['ky']
            gamma = record['Diagnostics']['omega']['gamma']
            omega = record['Diagnostics']['omega']['omega']
            
            omegastar = ky*(pardict['omn'+enum] + pardict['omt'+enum])
            _oid = record['_id']
            
            nrgdict = get_nrg(mgk_fusion,mgk_fusion.LinearRuns,ObjectId(_oid))
            try:
                gpars,geom = get_magn_geometry(mgk_fusion,mgk_fusion.LinearRuns,ObjectId(_oid))
            except:
                print("Geometry files not found in this record \n {}. \n Skipping it.".format(record['Meta']['run_collection_name']))
                break
            
            ratios = transport_ratios(pardict,nrgdict)
            
            field = record['Diagnostics']['field']
            #print(a[0]['Diagnostics']['field'].keys())
            phi = field['phi']
            apar = field['A_par']
            
            kperp, omd_curv, omd_gradB  = calc_kperp_omd(pardict,geom)
            kperp_avg = np.sqrt(eigenfunction_average(kperp**2,phi,pardict,geom))
            omd_avg = eigenfunction_average(omd_curv,phi,pardict,geom)
            
            kz_avg = kz_from_dfielddz_bessel(kperp,phi,pardict,geom)
            kz_vthe = kz_avg*pardict['mass'+enum]**-0.5
            
            epar_cancel = calc_epar(pardict,phi,apar,gamma,omega,gpars,geom)
            
            temp = [record['Meta']['run_collection_name'], record['Meta']['run_suffix'],
                    epar_cancel, omd_avg/omega, kz_vthe/omega, omegastar/omega,
                    ky, gamma, omega, omega/abs(omega), ratios['chie_o_chitot'],
                    ratios['chii_o_chitot'], ratios['chiz_o_chitot'], ratios['De_o_chitot'],
                    ratios['Di_o_chitot'], ratios['Dz_o_chitot'],ratios['QEMe_o_Qtot']]    
            
            derived.append(temp)
        except:
            print('record {} skipped'.format(str(record['_id'])))
            continue
    
    pd_val = pd.DataFrame(derived, columns=['location', 'suffix',
                                            'E_par','omega_drift/omega', 'kz_vthe/omega',
                                            'omegastar/omega', 
                                            'ky', 'gamma', 'omega', 'sign of omega',
                                            'chie/chitot', 'chii/chitot', 'chiz/chitot',
                                            'De/chitot', 'Di/chitot', 'Dz/chitot', 'QEMe/Qtot'])   
    
    return pd_val
        
        
def diag_plot_from_query(db, collection, query, projection={'Meta':1, 'Diagnostics':1}, diag=[], save_fig = True, save_dir = './'):

    data = load(db, collection, query, projection)
    if data is not None:
        n_records = len(data)
        print('{} records returned from your query.'.format(n_records) )
        
        p = [diag_plot(data[i], save_fig, save_dir) for i in range(n_records)]
        avail_diags = p[0].avail_diags
        print("Available diagnostics plot are {}".format(avail_diags) )
        
        if diag in ['all', 'All', 'ALL']:
            for i in range(n_records):
                p[i].plot_all()
                print('Plotting found record {}'.format(i+1) )
                input('Press ENTER to continue ...')
        else:
            if len(diag):
                for i in range(n_records):
                    for key in diag:
                        if key in avail_diags:
                            p[i].plot_diag(key)
                            print('Plotting {} in found record {}'.format(key, i+1) )
                            input('Press ENTER to continue ...')
                        else:
                            print('{} not supported, skipping..'.format(key))
                            continue
            else:
                print('You must select at least one diagnostic.')
                
    else:
        print('The database returns None for your query.')
        
def remove_from_mongo_by_query(db, runs_coll, query):
    inDb = runs_coll.find(query)        
    fs = gridfs.GridFS(db)
    for run in inDb:
        # delete the gridfs storage:
        for key, val in run['Files'].items():
            if val != 'None':
                print((key, val))
                fs.delete(val)
                print('deleted!')

        # delete the gridfs storage        
        for key, val in run['Diagnostics'].items():
            if val != 'None':
                print((key, val))
                fs.delete(val)
                print('deleted!')
                
#        delete the header file
        runs_coll.delete_one(run)

def download_from_query(db, collection, query, destination='./'):
    '''
    Collection must be LinearRuns or NonlinRuns, at current stage.
    '''
    fs = gridfs.GridFSBucket(db)
    fsf = gridfs.GridFS(db)
    records_found = collection.find(query)
    
    for record in records_found:
        
        dir_name = record['Meta']['run_collection_name']
        path = os.path.join(destination, dir_name.split('/')[-1])
        print(path)
        if not os.path.exists(path):
            try:
#                path = os.path.join(destination, dir_name.split('/')[-1])
                #os.mkdir(path)
                Path(path).mkdir(parents=True)
            except OSError:
                print ("Creation of the directory %s failed" % path)
        #else:
        
        '''
        Download saved files
        '''
        for key, val in record['Files'].items():
            if val != 'None':
                filename = db.fs.files.find_one(val)['filename']
                #print(db.fs.files.find_one(val)).keys()
                with open(os.path.join(path, filename),'wb+') as f:
    #                    fs.download_to_stream_by_name(filename, f, revision=-1, session=None)
                    fs.download_to_stream(val, f, session=None)
                    
                record['Files'][key] = str(val)
        #print(record)
        
        '''
        Download diagnostics
        '''
        fsf=gridfs.GridFS(db)
        diag_dict = {}
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
            
        '''
        Download plots
        '''
        for key,val in record['Plots'].items():
            with open(os.path.join(path, str(record['_id']) + '_' +key+
                                   record['Meta']['run_suffix']+'.png'), "wb") as imageFile:
                
                decoded = base64.decodebytes(val.encode('utf-8'))
                imageFile.write(decoded)
#            with open(os.path.join(destination, str(record['_id']) + '_' +key+
#                                                    record['Meta']['run_suffix']), "wb") as imageFile:
#                imageFile.write(val)

        
                
        record['_id'] = str(record['_id'])
        
        f_path = os.path.join(path, 'mgkdb_summary_for_run'+record['Meta']['run_suffix']+'.json')
        if os.path.isfile(f_path):
            exit('File exists already!')
        else:
            with open(f_path, 'w') as f:
                json.dump(record, f)
#                pickle.dump(record, f, protocol=pickle.HIGHEST_PROTOCOL)
            print("Successfully downloaded files in the collection to directory %s " % path)


def Write_json(data_dict, filename):
    """ Take the `gyrokinetic` dict and write to a json file """
    #        print(json.dumps(self.gkdict, indent=4))
    with open(filename, 'w') as fp:
        json.dump(data_dict, fp, indent=4,separators=(',', ': '))
        

def get_file_by_id(db, collection, objId, key):
    record =  collection.find_one({"_id":objId}, {"Files": 1})
#    print(record)
    
    # Now load the nrg file for example
    # Be careful that the content read are strings like `a, b, c, d\n` with possible headers
    # users can use other tools to parse it to numpy array or convert it to other formats after the decoding.
    fs = gridfs.GridFS(db)
    content = None
    if key in record['Files'].keys() and record['Files'][key] != 'None':
        file = fs.find_one({"_id":record['Files'][key]})
        content = file.read().decode('utf8')
        
    elif key not in record['Files'].keys():
        print("Key not correct. availables are {}.".format(record['Files'].keys()) )
        
    
    elif record['Files'][key] == 'None':
        
        print("None returned from the queried key. Not none entries are {}.".format([k for k in record['Files'].keys() if record['Files'][k] != 'None']) )
    
    else:
    
        print("File retrieval Failed.")
    
    
    return content


def update_calculations(db, runs_coll, linear, query = {}, 
                        projection={'Meta':1, 'Diagnostics':1},  img_dir='./mgk_diagplots'):
    '''
    This function will update records in 'db' with collection 'runs_coll'
    
    Gyrokinetics and Diagnostics
    
    
    from query
    '''
    fs = gridfs.GridFS(db)
    records_to_update = runs_coll.find(query)
    for record in records_to_update:
        try:
            print('Updating data {} from: \n{}.'.format(record['Meta']['run_suffix'], record['Meta']['run_collection_name']))
            print('='*60)
            time = _binary2npArray(fs.get(record['Diagnostics']['Time']).read())
            out_dir = record['Meta']['run_collection_name']
            suffix = record['Meta']['run_suffix']
            user = record['Meta']['user']
            
            # get new gyrokinetics dictionary
            GK_dict = get_gyrokinetics_from_run(out_dir, suffix, user, linear)
            # get new diag dictionary
            Diag_dict, imag_dict = get_diag_from_run(out_dir, suffix, time, img_dir)
            
            
            # delete old saved chunks
            for key, val in record['Diagnostics'].items():
                if val != 'None':
                    print((key, val))
                    fs.delete(val)
                    print('deleted!')
                        
    #        for key, val in record['Plots'].items():
    #            if val != 'None':
    #                print((key, val))
    #                fs.delete(val)
    #                print('deleted!')
                        
            # upload new chunks
            for key, val in Diag_dict.items():
                Diag_dict[key] = gridfs_put_npArray(db, Diag_dict[key], key, out_dir)
                
            # update omega
            omega_val = get_omega(out_dir, suffix)
            Diag_dict['omega'] = {}
            Diag_dict['omega']['ky'] = omega_val[0]
            Diag_dict['omega']['gamma'] = omega_val[1]
            Diag_dict['omega']['omega'] = omega_val[2]
    
            runs_coll.update_one({ "Meta.run_collection_name": out_dir, "Meta.run_suffix": suffix },
                    { "$set": {"Meta.last_updated": strftime("%y%m%d-%H%M%S"),
                               'gyrokinetics': GK_dict, 
                               'Diagnostics':Diag_dict, 
                               'Plots': imag_dict}
                     }
                         )
        except Exception as e:
            print('='*70)
            print('Exception encountered: \n {} \n Skip!'.format(e))
            print('='*70)
            continue

    
    print("Update complete")



#==========================================================
# argument parser
#==========================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Plotting diagnositcs')
    
    parser.add_argument('-A', '--authenticate', default = None, help='locally saved login info, a .pkl file')
    
    args = parser.parse_args()
    
    info = args.authenticate
    
    if info is None:
        O1 = input("You did not enter credentials for accessing the database.\n You can \n 0: Enter it manually. \n 1: Enter the full path of the saved .pkl file\n")
        if O1 == '0':
            O2 = input("Please enter the server location, port, database name, username, password in order and separated by comma.\n").split(',')
            login = mgk_login(server= O2[0], port= O2[1], dbname=O2[2], user=O2[3], pwd = O2[4])
            O2_1 = input("You can save it by entering a target path, press ENTER if you choose not to save it\n")
            if len(O2_1)>1:
                login.save(os.path.abspath(O2_1) )
            else:
                print('Info not saved!')
                pass
        elif O1 == '1':
            O2= input("Please enter the target path\n")
            login = mgk_login()
            login.from_saved(os.path.abspath(O2))
        
        else:
            exit("Invalid input. Abort")
        
                   
    else:
        login = mgk_login()
        try:
            login.from_saved(os.path.abspath(info))
        except OSError:
            exit("The specified credential file is not found!")
            
    
    
    mgk_fusion = login.connect()
    
    user = login.login['user']





        




