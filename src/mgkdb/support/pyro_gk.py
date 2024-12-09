import json, bson
import numpy as np
from pyrokinetics import Pyro,template_dir
from pyrokinetics.databases.imas import pyro_to_imas_mapping
import idspy_toolkit as idspy
from idspy_dictionaries import ids_gyrokinetics_local as gkids
from pathlib import Path
import os

# 
def convert_to_json(obj,separate_real_imag = False):
    """
    This function to recursively goes through GyrokineticsLocal class, and writes to json compatible dictionary

    Parameters
    ----------
    obj : GyrokineticsLocal
        GyrokineticsLocal object with data loaded
    separate_real_imag : bool
        If true, move real and imaginary parts to separate dictionary keys. 
        If False, encode complex np.array

    Returns
    -------
    json compatible dictionary.

    """
    
    if '__dataclass_fields__' in dir(obj):
        tmpdict = {}
        for item in obj.__dataclass_fields__.keys():
            
            value =  eval(f"obj.{item}")
            if separate_real_imag and isinstance(value, np.ndarray) and 'complex' in str(value.dtype).lower():
                #print(value)
                tmpdict[item + "_real"] = convert_to_json(value.real)
                tmpdict[item + "_imaginary"] = convert_to_json(value.imag)
            else:
                tmpdict[item] = convert_to_json(value)
        return tmpdict
    elif isinstance(obj, np.ndarray):
        if 'complex' in str(obj.dtype).lower():
                return dict(
                    __ndarray_tolist_real__=obj.real.tolist(),
                    __ndarray_tolist_imag__=obj.imag.tolist(),
                    dtype=str(obj.dtype),
                    shape=obj.shape,
                )
        else:
            return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json(item) for item in obj]
    else:
        return obj

def update_key_values(data, mod_key, new_value):
    '''
    Module to iteratively scan for entries in a dictionary or sub dictionaries or sublists
    with a specific key and repalce it with a given value
    '''
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key == mod_key:
                data[key] = new_value
            else:
                update_key_values(value, mod_key, new_value)
    elif isinstance(data, list):
        for item in data:
            update_key_values(item, mod_key, new_value)


def prune_imas_gk_dict(gk_dict, pyro, linear):
    ''' Remove 4d files for linear and non-linear runs  
    Also set value of max_repr_length using input values 
    '''

    if linear: # If linear, drop entries in ['linear']['wavevector'][0]['eigenmode'][i]['fields'][key] 
        if gk_dict['non_linear']['fields_4d'] is not None:   
            assert gk_dict['non_linear']['fields_4d']['phi_potential_perturbed_norm']==[], "phi_potential_perturbed_norm field in non_linear, fields_4d is not empty"

        keys_list = ['phi_potential_perturbed_norm','a_field_parallel_perturbed_norm','b_field_parallel_perturbed_norm']
        if gk_dict['linear']['wavevector'] !=[]: 
            for i in range(len(gk_dict['linear']['wavevector'][0]['eigenmode'])): ## For each particle species, delete fields
                if gk_dict['linear']['wavevector'][0]['eigenmode'][0]['fields']: 
                    for key in keys_list:
                        gk_dict['linear']['wavevector'][0]['eigenmode'][i]['fields'][key]=None

    else: # If non-linear, drop  ['non_linear']['fields_4d]
        assert (gk_dict['linear']['wavevector']==[]),"wavevector field in linear is not empty"

        gk_dict['non_linear']['fields_4d']=None

    ## Setup max_repr_length
    if pyro._gk_code=='GENE':
        prec = pyro.gk_input.data["info"]["PRECISION"] 
        prec_dict = {'SINGLE':32, 'DOUBLE':64}
        max_repr_length = prec_dict[prec]

        update_key_values(gk_dict, 'max_repr_length', max_repr_length)
    
    return gk_dict

def create_gk_dict_with_pyro(fname,gkcode):
    '''
    Create gyrokinetics dictionary to be upload to database
    '''

    assert gkcode in ['GENE','CGYRO','TGLF','GS2'], "invalid gkcode type %s"%(gkcode)
    
    try: 
        pyro = Pyro(gk_file=fname, gk_code=gkcode)
        linear = not pyro.numerics.nonlinear

        if gkcode=='TGLF':   
            quasi_linear = pyro.numerics.nonlinear
            linear = True
        else:      
            linear = not pyro.numerics.nonlinear
            quasi_linear = False 

        if linear: 
            pyro.load_gk_output(load_fields=True)
        else: # Loading fields for non-linear runs can take too long, so do not read them 
            pyro.load_gk_output(load_fields=False)

        gkdict = gkids.GyrokineticsLocal()
        idspy.fill_default_values_ids(gkdict)
        gkdict = pyro_to_imas_mapping(
                pyro,
                comment=f"Computing IMAS for %s"%(gkcode),
                ids=gkdict
            )
        
        json_data = convert_to_json(gkdict)

        json_data = prune_imas_gk_dict(json_data, pyro, linear)

        ## Confirm IMAS size is less than 2MB
        bson_data = bson.BSON.encode(json_data)
        imas_size = len(bson_data)/1e6 # IMAS size in Megabytes
        if imas_size  > 2.0 : 
            print("Size of IMAS dict: ",imas_size,"MB")
            print("IMAS size is larger than 2MB. Need to check IMAS content")
            raise SystemError
    
    except Exception as e: 
        print(e)
        raise SystemError
    
    return json_data,quasi_linear
