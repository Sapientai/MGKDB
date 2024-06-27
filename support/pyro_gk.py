import json
import numpy as np
from pyrokinetics import Pyro,template_dir
from pyrokinetics.databases.imas import pyro_to_imas_mapping
import idspy_toolkit as idspy
from idspy_dictionaries import ids_gyrokinetics_local as gkids
from pathlib import Path

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


def create_gk_dict_with_pyro(fname,gkcode):
    '''
    Create gyrokinetics dictionary to be upload to database
    '''

    assert gkcode in ['GENE','CGYRO'], "invalid gkcode type %s"%(gkcode)

    pyro = Pyro(gk_file=fname, gk_code=gkcode)
    pyro.load_gk_output()

    gkdict = gkids.GyrokineticsLocal()
    idspy.fill_default_values_ids(gkdict)
    gkdict = pyro_to_imas_mapping(
            pyro,
            comment=f"Testing IMAS %s"%(gkcode),
            ids=gkdict
        )
    
    json_data = convert_to_json(gkdict)

    return json_data
