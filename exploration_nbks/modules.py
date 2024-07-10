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


def f_code(old_gk_dict,new_gk_dict):
    ''' conversion for key: code '''

    main_key='code'
    old_gk,new_gk = old_gk_dict[main_key],new_gk_dict[main_key]

    dict1={}

    ## Keys present in old IMAS 
    for key in ['name','version']:
        dict1[key] = old_gk[key]
        
    ### parameters 
    ### Create xml string from dictionary.
    dict1['parameters'] = xmltodict.unparse({'root':old_gk['parameters']},pretty=True)
    # Alternative : json.dumps(old_gk['parameters'])
    
    ## Not present in old IMAS
    keys = ['commit', 'description', 'library', 'output_flag', 'repository']
    for key in keys: 
        dict1[key] = None
    
    ## Note version doesn't need to be added here. it is the GENE version
    dict1['max_repr_length'] = new_gk['max_repr_length']

    return dict1 

## In progress ## 

def f_linear(old_gk_dict,new_gk_dict): 
    
    def f_get_wavevector(old_gk_dict,new_gk_dict):
        ''' conversion for key: wavevector '''
        
        main_key = 'wavevector'
        old_gk,new_gk = old_gk_dict[main_key][0], new_gk_dict['linear'][main_key][0]
        
        dict1={}
        ## Old keys not present 
        # poloidal_turns is inside eigenmodes for new 
        
        ## New keys not present in old 
        keys = ['max_repr_length', 'version']
        for key in keys:
            dict1[key] = new_gk[key]
        
        ## Common keys 
        key_map = {'binormal_component_norm':'binormal_wavevector_norm', 
                   'radial_component_norm':'radial_wavevector_norm' }
        for key,val in key_map.items():
            dict1[val] = old_gk[key]
    
        ## Map subdict eigenmode 
        
        def f_get_eigenmode_dict(old_gk,new_gk):
    
            dict2={}
    
            ## Common keys
            keys = ['frequency_norm','growth_rate_norm','growth_rate_tolerance']
            for key in keys: 
                dict2[key]= old_gk['eigenmode'][0][key]
    
            ## Poloidal angle has different key name
            dict2['angle_pol'] = old_gk['eigenmode'][0]['poloidal_angle']
    
            ## poloidal_turns is outside eigenmodes in old 
            dict2['poloidal_turns'] = old_gk['poloidal_turns']
            
            #### linear weights obtained from fluxes_norm
            dict2['linear_weights']={}
    
            ## Common keys 
            keys = ['energy_a_field_parallel', 'energy_b_field_parallel', 'energy_phi_potential', 'momentum_tor_parallel_a_field_parallel', 'momentum_tor_parallel_b_field_parallel', 
                    'momentum_tor_parallel_phi_potential', 'momentum_tor_perpendicular_a_field_parallel', 'momentum_tor_perpendicular_b_field_parallel', 'momentum_tor_perpendicular_phi_potential', 
                    'particles_a_field_parallel', 'particles_b_field_parallel', 'particles_phi_potential']
    
            num_list = 3 ## size of list : corresponds to 3 types of particles
            for key in keys: 
                dict2['linear_weights'][key]= [old_gk['eigenmode'][0]['fluxes_norm'][i][key] for i in range(num_list)]
            
            ## Keys not in old for linear weights
            keys = ['max_repr_length', 'version']
            for key in keys:
                dict2['linear_weights'][key] = new_gk[key]
    
            ##### moments_norm_rotating_frame
            ## Not present in new IMAS 
            keys = ['density_imaginary', 'density_real', 'temperature_parallel_imaginary', \
                    'temperature_parallel_real', 'temperature_perpendicular_imaginary', \
                    'temperature_perpendicular_real', 'velocity_parallel_imaginary', 'velocity_parallel_real']
    
            ##### phi_potential_perturbed_norm 
            keys = ['phi_potential_perturbed_norm_imaginary','phi_potential_perturbed_norm_imaginary']
            
            ##### a_field_parallel_perturbed_norm
            keys = ['a_field_parallel_perturbed_norm_imaginary','a_field_parallel_perturbed_norm_real']
            
            ### fields
            keys = ['a_field_parallel_perturbed_norm', 'a_field_parallel_perturbed_parity', 'a_field_parallel_perturbed_weight', 'b_field_parallel_perturbed_norm', 'b_field_parallel_perturbed_parity', 'b_field_parallel_perturbed_weight', 'max_repr_length', 'phi_potential_perturbed_norm', 'phi_potential_perturbed_parity', 'phi_potential_perturbed_weight', 'version']
            fields=dict.fromkeys(keys,None)
            dict2['fields']=fields
            
            ### moments_norm_particle 
            keys = ['density', 'heat_flux_parallel', 'j_parallel', 'max_repr_length', 'pressure_parallel', 'pressure_perpendicular', 'v_parallel_energy_perpendicular', 'v_perpendicular_square_energy', 'version']
            mom_norm = dict.fromkeys(keys,None)
            dict2['moments_norm_particle']=mom_norm
        
            ### Not present in old 
            keys = ['initial_value_run','linear_weights_rotating_frame','moments_norm_gyrocenter','moments_norm_gyrocenter_bessel_0','moments_norm_gyrocenter_bessel_1',]
            for key in keys: 
                dict2[key]= None
            
            for key in ['version','max_repr_length']:
                dict2[key]= None
            
            ## time_norm present in model. Defined below

            ### code 
            dict2['code']={}
            dict2['code']['parameters'] = None # Same as the parameters in code field 
            
            for key in ['max_repr_length', 'output_flag', 'version']: 
                dict2['code'][key] = new_gk['eigenmode'][0]['code'][key]

            return [dict2] 
    
        ## eigenmode:
        dict1['eigenmode']= f_get_eigenmode_dict(old_gk,new_gk)
    
        dict1['eigenmode'][0]['time_norm'] = old_gk_dict['model']['time_interval_norm'] 

        return [dict1] 
        

    wavevector = f_get_wavevector(old_gk_dict,new_gk_dict)
    dict_c = {'wavevector': wavevector}

    for key in ['max_repr_length', 'version']: 
        dict_c[key] = new_gk_dict['linear'][key]

    ## Finally overwrite parameters to that from field 'code' 
    dict_c['wavevector'][0]['eigenmode'][0]['code']['parameters'] =\
    xmltodict.unparse({'root':old_gk_dict['code']['parameters']},pretty=True)
    
    return {'linear':dict_c} 


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
    f_code(gk_dict,GK_dict)
    f_linear(gk_dict,GK_dict)


    ## Full conversion 
    modified_gk = {} 
    key='collisions'
    modified_gk[key] = f_collisions(gk_dict,GK_dict)
    key='flux_surface'
    modified_gk[key] = f_flux_surface(gk_dict,GK_dict)
    key='species_all'
    modified_gk[key] = f_species_all(gk_dict,GK_dict)
    key='species'
    modified_gk[key] = f_species(gk_dict,GK_dict)
    key='ids_properties'
    modified_gk[key] = f_ids_properties(gk_dict,GK_dict)
    key='model'
    modified_gk[key] = f_model(gk_dict,GK_dict)
    key='code'
    modified_gk[key] = f_code(gk_dict,GK_dict)
    key='linear'
    modified_gk[key] = f_linear(gk_dict,GK_dict)

    print(modified_gk)
    
