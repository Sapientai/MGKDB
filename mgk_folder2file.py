# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 15:04:25 2020

@author: dykua

support for leaf directory --> file before uploading
"""
from mgk_file_handling import get_suffixes, isLinear, get_diag_with_user_input, get_omega
from mgk_post_processing import get_gyrokinetics_from_run
import os
import pickle
from ParIO import *
#import h5py  # format issues (a list) not clear, leave it for future
#import numpy as np
#def save_dict_to_hdf5(dic, filename):
#    """
#    ....
#    """
#    with h5py.File(filename, 'w') as h5file:
#        recursively_save_dict_contents_to_group(h5file, '/', dic)
#
#def recursively_save_dict_contents_to_group(h5file, path, dic):
#    """
#    ....
#    """
#    for key, item in dic.items():
#        if isinstance(item, (np.ndarray, np.int64, np.float64, str, bytes)):
#            h5file[path + key] = item
#        elif isinstance(item, dict):
#            recursively_save_dict_contents_to_group(h5file, path + key + '/', item)
#        else:
#            raise ValueError('Cannot save %s type'%type(item))
#
#def load_dict_from_hdf5(filename):
#    """
#    ....
#    """
#    with h5py.File(filename, 'r') as h5file:
#        return recursively_load_dict_contents_from_group(h5file, '/')
#
#def recursively_load_dict_contents_from_group(h5file, path):
#    """
#    ....
#    """
#    ans = {}
#    for key, item in h5file[path].items():
#        if isinstance(item, h5py._hl.dataset.Dataset):
#            ans[key] = item.value
#        elif isinstance(item, h5py._hl.group.Group):
#            ans[key] = recursively_load_dict_contents_from_group(h5file, path + key + '/')
#    return ans

class folder_2_file():
    def __init__(self, out_dir, user = None, keywords=None, linear=None, confidence = -1, comments=None, 
                 img_dir=r'./mgk_diagplots', suffixes=None, run_shared = None, manual_time_flag = True):
        
        out_dir = os.path.abspath(out_dir)
        self.data_dict = {                
                'run_collection_name': out_dir,
                'user': user,
                'keywords': keywords,
                'confidence': confidence,
                'comments': comments
                }
        self.img_dir = img_dir
        
        if suffixes is None:
            suffixes = get_suffixes(out_dir)
        
        self.suffixes = suffixes
        self.suffixes.sort()
        
        self.run_shared = run_shared
        
        self.Docs = ['autopar', 'codemods', 'nrg', 'omega','parameters']
        self.linear = linear
        self.manual_time_flag = manual_time_flag
        
#        temp_dict = dict().fromkeys(self.suffixes, dict())
        
        self.full_dict={
                'Location': out_dir,
                'shared':None,
                'linear': linear
                }
        
        self._troubled_runs = []
    
    def get_meta(self, suffix):
        return {**self.data_dict, 'run_suffix': suffix}
        
    
    def get_shared(self):
        '''
        read shared files
        '''
        if isinstance(self.run_shared, list):
            self.shared = dict().fromkeys(self.run_shared, None)
            for share in self.run_shared:
                share_path = os.path.join(self.data_dict['run_collection_name'], share)
                if os.path.isfile(share_path):
#                    if '.' in share:
#                            share = '_'.join(share.split('.')) # need this when uploading.
                    with open(share_path, 'r') as f: # read file or binary or other format ?
                        self.shared[share] = f.read()
                else:
                    self.shared.pop(share)
            
            if self.shared == {}:
                self.shared = None
        else:
            self.shared = None
                    
        
    def get_file(self, suffix):
        file_dict = dict().fromkeys(self.Docs, None)
        
        '''
        read files per suffix
        '''
        for doc in self.Docs:
            file_path = os.path.join(self.data_dict['run_collection_name'], doc+suffix)
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    file_dict[doc] = f.read()
                    
        '''
        geometry file
        '''
        par_file = os.path.join(self.data_dict['run_collection_name'], 'parameters'+suffix)
        par = Parameters()
        par.Read_Pars(par_file)
        pars = par.pardict    
    
        if 'magn_geometry' in pars:
            geofile = pars['magn_geometry'][1:-1]
            #self.Docs.append(geofile)
            filepath = os.path.join(self.data_dict['run_collection_name'], geofile+suffix)
            with open(filepath, 'r') as f:
                file_dict['magn_geometry'] = f.read()
                
        
        return file_dict
        
    def get_gyrokinetics(self, suffix):
        GK_dict = get_gyrokinetics_from_run(self.data_dict['run_collection_name'], 
                                            suffix, self.data_dict['user'], self.linear)
        return GK_dict
        
        
    def get_diagnostics(self, suffix):
        Diag_dict, self.manual_time_flag, imag_dict = get_diag_with_user_input(self.data_dict['run_collection_name'],
                                                                               suffix, self.manual_time_flag, 
                                                                               self.img_dir)
        '''
        also the omega triplets
        '''
        omega_val = get_omega(self.data_dict['run_collection_name'], suffix)
        Diag_dict['omega'] = {}
        Diag_dict['omega']['ky'] = omega_val[0]
        Diag_dict['omega']['gamma'] = omega_val[1]
        Diag_dict['omega']['omega'] = omega_val[2]
        
        return Diag_dict, imag_dict
            
            
    def get_full_dict(self):
        out_dir = self.data_dict['run_collection_name']
        print('\n Working on folder: {}.'.format(out_dir))
        self.get_shared()
        self.full_dict['shared'] = self.shared
        self.full_dict['suffixes'] = self.suffixes
        
        for suffix in self.suffixes:
            print('+'*60)
            print('Working on suffix {}'.format(suffix))
            temp_dict = {}
            try:
#                self.full_dict[suffix]['Meta'] = self.get_meta(suffix)
                temp_dict['Meta'] = self.get_meta(suffix)
#                print(temp_dict['Meta'])
                print('='*60)
                print('\n Working on reading files......\n')
                temp_dict['Files'] = self.get_file(suffix)
#                self.full_dict[suffix]['Files'] = self.get_file(suffix)
                print('='*60)
                print('\n Working on OMAS gyrokinetics dictionary using tspan detected from nrg file......\n')
                temp_dict['gyrokinetics'] = self.get_gyrokinetics(suffix) 
#                self.full_dict[suffix]['gyrokinetics'] = self.get_gyrokinetics(suffix)
                print('='*60)
                print('\n Working on diagnostics with user specified tspan .....\n')
                Diag_dict, Imag_dict = self.get_diagnostics(suffix)
                temp_dict['Diagnostics'] = Diag_dict
                temp_dict['Plots'] = Imag_dict
#                self.full_dict[suffix]['Diagnostics'] = Diag_dict
#                self.full_dict[suffix]['Plots'] = Imag_dict
#                print(temp_dict['Diagnostics']['omega'])
                self.full_dict[suffix] = temp_dict
                print('='*60)
                
            except Exception as ee:
                print(ee)
                print('cleaning......')
#                self.full_dict.pop(suffix)
                self.suffixes.remove(suffix)
                self._troubled_runs.append('{}###{}'.format(out_dir, suffix))
            
#    def to_h5(self, filename):
#        h = h5py.File(filename+'.hdf5')
#        for k, v in self.full_dict.items():
#            h.create_dataset(k, data=v)
        
    def to_pkl(self, filename):
        with open(filename+'_mgk.pkl', 'wb') as handle:
            pickle.dump(self.full_dict, handle, protocol=pickle.HIGHEST_PROTOCOL) 
        print('Files are saved to {}'.format(filename+'_mgk.pkl') )

from time import strftime
def get_mgkfile(output_folder, user, exclude_folders, default, img_dir, save_dir = None, show_dict = False):
    data_dict = dict()
    _troubled_runs = []
    for dirpath, dirnames, files in os.walk(output_folder):
#        try:
            if str(dirpath).find('in_par') == -1 and str(files).find('parameters') != -1 and str(dirpath) not in exclude_folders:    
                print('Scanning in {} *******************\n'.format( str(dirpath)) )
                linear = isLinear(dirpath)
                if linear == None:
                    linear_input = input('Cannot decide if this folder is a linear run or not. Please make the selection manually by typing:\n 1: Linear\n 2: Nonlinear \n 3: Skip this folder \n')
                    if linear_input.strip() == '1':
                        linear = True
                    elif linear_input.strip() == '2':
                        linear = False
                    elif linear_input.strip() == '3':
                        print('Folder skipped.')
                        continue
                    else:
                        exit('Invalid input encountered!')            
                if linear:
                    lin = ['linear']
                else:
                    lin = ['nonlin']
#                keywords_lin = keywords.split('#') + lin
#                keywords_lin = lin
                                              
                if not default:
                    suffixes = get_suffixes(dirpath)
                    print("Found in {} these suffixes:\n {}".format(dirpath, suffixes))
                    
                    suffixes = input('Which run do you want to upload? Separate them by comma. \n Press q to skip. Press ENTER to upload ALL.\n')
                    if suffixes == 'q':
                        print("Skipping the folder {}.".format(dirpath))
                        continue
                    elif len(suffixes):
                        suffixes = suffixes.split(',')
                    else:
                        suffixes = None  
                    
                    keywords = input("Any keywords for these runs? Separate them by comma. \n Press ENTER to skip.")  
                    if len(keywords):
                        keywords = keywords.split(',') + lin
                    else:
                        keywords = lin
                    
                                                  
                    confidence = input('What is your confidence (1-10) for the run? Press ENTER to use default value -1.0\n')
                    if len(confidence):
                        confidence = float(confidence)
                    else:
                        confidence = -1.0
                        print("Using default confidence -1.\n")
                    comments = input('Any comments for data in this folder?Press Enter to skip.\n')
                    run_shared = input('Any other files to upload than the default? Separate them by comma. Press Enter to skip.\n')
                    if len(run_shared):
                        run_shared = run_shared.split(',')
                    else:
                        run_shared = None
                    
                    manual_time_flag = True
                
                else:
                    suffixes = None
                    confidence = -1
                    comments = 'Uploaded with default settings.'
                    run_shared = None
                    manual_time_flag = False
                    keywords = lin
                
                mgk_file = folder_2_file(dirpath, user = user, keywords=keywords, linear=linear, 
                                         confidence = confidence, comments=comments, 
                                         img_dir=img_dir, suffixes=suffixes, run_shared = run_shared, 
                                         manual_time_flag = manual_time_flag)
                
                mgk_file.get_full_dict()
                if show_dict:
                    data_dict[dirpath] = mgk_file.full_dict
                if save_dir is not None:
                    save_dir = os.path.abspath(save_dir)
                    time_processed = strftime("%y%m%d-%H%M%S")
                    mgk_file.to_pkl(os.path.join(save_dir, time_processed) )
                if len(mgk_file._troubled_runs):
                    _troubled_runs.append(mgk_file._troubled_runs)
        
#        except Exception as ee:
#            print(ee)
#            print('Skipping {} ...'.format(dirpath))
#            continue
        
    return data_dict, _troubled_runs

if __name__ == '__main__':
    
#    a, b = get_mgkfile(r'D:\test_data\data_linear_multi', 
#                       'dykuang', [], False, r'D:\test_data\data_linear_multi\mgk_diagplots', save_dir=None,
#                       show_dict=True) 
#    if a['D:\\test_data\\data_linear_multi']['shared'] is not None:
#        print(a['D:\\test_data\\data_linear_multi']['shared'].keys())
#    print(a['D:\\test_data\\data_linear_multi']['_0001']['Meta'].keys())
#    print(a['D:\\test_data\\data_linear_multi']['_0001']['Files'].keys())
#    print(a['D:\\test_data\\data_linear_multi']['_0001']['gyrokinetics'].keys())    
#    print(a['D:\\test_data\\data_linear_multi']['_0001']['Diagnostics'].keys()) 
    import argparse
    parser = argparse.ArgumentParser(description='Process input for uploading files')

    parser.add_argument('-T', '--target', help='Target GENE output folder')
    parser.add_argument('-X', '--exclude', default = None, help='folders to exclude')
    parser.add_argument('-Img', '--image_dir', default = r'./', help='folders to save temporal image files.')
    parser.add_argument('-S', '--save', default = None, help='folders to save file to.')    
    parser.add_argument('-D', '--default', default = False, help='Using default inputs for all.')
    
    args = parser.parse_args()
    
    output_folder = os.path.abspath(args.target)
       
    img_dir = os.path.abspath(args.image_dir)
    save_dir = os.path.abspath(args.save)
            
    if args.exclude is not None:
        exclude_folders = args.exclude.split(',')
        exclude_folders = [os.path.join(output_folder, fname) for fname in exclude_folders]
        print('Scanning will skip specified folders:\n {}\n'.format(exclude_folders) )
    else:
        exclude_folders = []        
        
    if args.default in ['T', 'True', '1', 't', 'true']:
        default = True
        manual_time_flag = False
    
    else:
        default = False
        manual_time_flag = True
    
    user = os.getlogin()
        
    a, b = get_mgkfile(output_folder, user, exclude_folders, default, img_dir, save_dir = save_dir, show_dict = False)

    
    

