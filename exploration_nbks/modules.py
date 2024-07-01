import numpy as np
import datetime
import os

import pymongo
import pprint
from bson.objectid import ObjectId

import yaml
import json
import xmltodict




def f_collisions(old_gk_dict,new_gk_dict):
    ''' conversion for key: collisions '''

    main_key='collisions'
    old_gk,new_gk=old_gk_dict[main_key],new_gk_dict[main_key]
    
    dict1={}
    for key in ['max_repr_length','version']: 
        dict1[key] = new_gk[key]
    
    dict1['collisionality_norm']=old_gk['collisionality_norm']
    
    return dict1

def f_flux_surface(old_gk_dict,new_gk_dict):
    ''' conversion for key: flux_surface '''

    main_key='flux_surface'
    old_gk,new_gk=old_gk_dict[main_key],new_gk_dict[main_key]
    
    dict1={}
    ## Old keys not present 
    keys = ['triangularity_lower', 'triangularity_upper']
    
    ## New keys not present in old 
    keys = ['delongation_dr_minor_norm', 'dgeometric_axis_r_dr_minor', 'dgeometric_axis_z_dr_minor', 'max_repr_length', 'version']
    for key in keys:
        dict1[key] = new_gk[key]
    
    ## Common keys 
    common_keys = ['b_field_tor_sign', 'dc_dr_minor_norm', 'ds_dr_minor_norm', 'elongation', 'ip_sign', 'magnetic_shear_r_minor', 'pressure_gradient_norm', 'q', 'r_minor_norm', 'shape_coefficients_c', 'shape_coefficients_s']
    
    for key in common_keys:
        dict1[key] = old_gk[key]
        
    return dict1

def f_species_all(old_gk_dict,new_gk_dict):
    ''' conversion for key: species_all '''
    
    main_key='species_all'
    old_gk,new_gk=old_gk_dict[main_key],new_gk_dict[main_key]
    
    dict1={}
    ## Old keys not present 
    keys =  ['debye_length_reference', 'zeff'] 
    
    ## New keys not present in old 
    keys = ['angle_pol', 'debye_length_norm', 'max_repr_length', 'version']
    for key in keys:
        dict1[key] = new_gk[key]
    
    ## Common keys 
    common_keys = ['beta_reference', 'shearing_rate_norm', 'velocity_tor_norm'] 

    for key in common_keys:
        dict1[key] = old_gk[key]
        
    return dict1

def f_species(old_gk_dict, new_gk_dict):
    ''' conversion for key: species '''

    main_key='species'
    old_gk,new_gk=old_gk_dict[main_key][0],new_gk_dict[main_key][0]

    dict1={}
    ## Old keys not present 
    keys =  ['name'] 

    ## New keys not present in old 
    keys = ['max_repr_length', 'potential_energy_gradient_norm', 'potential_energy_norm', 'version']
    for key in keys:
        dict1[key] = new_gk[key]

    ## Common keys 
    common_keys = ['charge_norm', 'density_log_gradient_norm', 'density_norm', 'mass_norm', 'temperature_log_gradient_norm', 'temperature_norm', 'velocity_tor_gradient_norm'] 

    for key in common_keys:
        dict1[key] = old_gk[key]
    
    return [dict1]

def f_ids_properties(old_gk_dict,new_gk_dict):
    ''' conversion for key: ids_properties '''

    main_key='ids_properties'
    old_gk,new_gk=old_gk_dict[main_key],new_gk_dict[main_key]
    
    dict1={}
    ## Old keys not present 
    keys = ['creator', 'date'] 
    
    ## New keys not present in old 
    keys = ['creation_date', 'homogeneous_time', 'max_repr_length', 'name', 'occurrence_type', 'provenance', 'provider', 'version']
    for key in keys:
        dict1[key] = new_gk[key]
    
    ## Common keys 
    common_keys = ['comment'] 

    for key in common_keys[:]:
        dict1[key] = old_gk[key]
        
    ## Special fixes
    dict1['creation_data']=old_gk['date']
    dict1['provider'] = 'manual'
    
    ## Note: 'creator' not used. Should it be stored in 'name' ? 
    # dict1['name'] = old_gk['creator']

    return dict1

def f_model(old_gk_dict,new_gk_dict):
    ''' conversion for key: model '''

    ## To Do : Confirm what NoneType means for the True case in the new schema
    
    main_key='model'
    old_gk,new_gk=old_gk_dict[main_key],new_gk_dict[main_key]
    
    dict1={}
    ## Old keys not present 
    keys =  ['collision_ei_only','initial_value_run', 'non_linear_run', 'time_interval_norm']
    
    ## New keys not present in old 
    keys = ['adiabatic_electrons', 'include_coriolis_drift']
    for key in keys: 
        dict1[key] = None
    
    keys = ['max_repr_length', 'version']
    for key in keys:
        dict1[key] = new_gk[key]
    
    ## Common keys 
    common_keys = ['include_a_field_parallel', 'include_b_field_parallel']
    for key in common_keys: # Integer dtype
        dict1[key] = 1 if old_gk[key] else 0

    common_keys = ['include_centrifugal_effects', 'include_full_curvature_drift'] 
    for key in common_keys: ## None type
        dict1[key] = 1 if old_gk[key] else None
        
    ## common keys with slight modification in key name
    collision_suffix = ['energy_conservation', 'finite_larmor_radius', 'momentum_conservation', 'pitch_only']
    for suffix in collision_suffix: # old : collision_ (Bool) , new: collisions_ (None type)
        dict1['collisions_'+suffix] = 1 if gk_dict[main_key]['collision_'+suffix] else None 
        
    return dict1


if __name__=="__main__":
    ## Load file data 
    fname='gyro_imas_old.yaml'
    with open(fname,'r') as f:
        gk_dict = yaml.safe_load(f)
        
    fname='gyro_imas_new.yaml'
    with open(fname,'r') as f:
        GK_dict = yaml.safe_load(f)

    print(gk_dict.keys(),'\n',GK_dict.keys())

    ## Test modules 
    f_collisions(gk_dict,GK_dict)
    f_flux_surface(gk_dict,GK_dict)
    f_species_all(gk_dict,GK_dict)
    f_species(gk_dict,GK_dict)
    f_ids_properties(gk_dict,GK_dict)
    f_model(gk_dict,GK_dict)
