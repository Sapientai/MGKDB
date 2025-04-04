import json, bson
import numpy as np
from pyrokinetics import Pyro, template_dir
from pyrokinetics.databases.imas import pyro_to_imas_mapping, ids_to_pyro
import idspy_toolkit as idspy
from idspy_dictionaries import ids_gyrokinetics_local as gkids
from pathlib import Path
import os
import tempfile
import dataclasses
from typing import Dict, Any, Optional, Type, TypeVar, get_type_hints
import xml.etree.ElementTree as ET

T = TypeVar('T')

def clean_xml_text(text: str) -> Optional[str]:
    """
    Clean XML text content by removing invalid characters and unescaping entities.
    
    Parameters
    ----------
    text : str
        The text content to clean
        
    Returns
    -------
    Optional[str]
        The cleaned text, or None if the text is None or empty
    """
    if text is None or text.strip() == '':
        return None
        
    # Remove any <n> tags that appear in the text
    text = text.replace('<n>', '')
    
    # Unescape XML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&apos;', "'")
    
    return text.strip() or None


def parse_xml_to_code(xml_str: str) -> gkids.Code:
    """
    Parse XML string to create a Code object.
    
    Parameters
    ----------
    xml_str : str
        XML string containing code information
        
    Returns
    -------
    gkids.Code
        Code object with parsed information
    """
    try:
        root = ET.fromstring(xml_str)
        
        # Extract basic fields with type information
        code_data = {}
        for field in ['name', 'version', 'commit', 'repository', 'parameters', 'description']:
            elem = root.find(field)
            if elem is not None:
                # Clean and process the text content
                text = clean_xml_text(elem.text)
                
                # Handle elements that might have type attributes
                if text is not None:
                    if 'type' in elem.attrib:
                        if elem.attrib['type'] == 'str':
                            code_data[field] = text
                        elif elem.attrib['type'] == 'int':
                            try:
                                code_data[field] = int(text)
                            except (ValueError, TypeError):
                                code_data[field] = None
                        else:
                            code_data[field] = text
                    else:
                        code_data[field] = text
        
        # Handle library items
        library_items = []
        library = root.find('library')
        if library is not None and library.attrib.get('type') == 'list':
            for item in library.findall('item'):
                if item.attrib.get('type') == 'dict':
                    lib_data = {}
                    for field in ['name', 'version', 'commit', 'repository', 'parameters', 'description']:
                        elem = item.find(field)
                        if elem is not None:
                            text = clean_xml_text(elem.text)
                            if text is not None:
                                if 'type' in elem.attrib and elem.attrib['type'] == 'str':
                                    lib_data[field] = text
                                else:
                                    lib_data[field] = text
                    if lib_data:  # Only add if we have data
                        library_items.append(gkids.Library(**lib_data))
        
        code_data['library'] = library_items
        
        # Create and return the Code object
        try:
            return gkids.Code(**code_data)
        except Exception as e:
            print(f"Warning: Failed to create Code object: {e}")
            print(f"Code data: {code_data}")
            return None
            
    except Exception as e:
        print(f"Warning: Failed to parse XML for code: {e}")
        print(f"XML string was: {xml_str[:200]}...")  # Print first 200 chars for debugging
        return None


def get_idspy_type(field_type: Type) -> Optional[Type]:
    """
    Get the IDSPY type for a given field type.
    
    Parameters
    ----------
    field_type : Type
        The type to check
        
    Returns
    -------
    Optional[Type]
        The IDSPY type if found, None otherwise
    """
    if hasattr(gkids, field_type.__name__):
        return getattr(gkids, field_type.__name__)
    return None


def initialize_dataclass_with_defaults(cls: Type[T]) -> T:
    """
    Initialize a dataclass with default values for all fields.
    
    Parameters
    ----------
    cls : Type[T]
        The dataclass type to initialize
    
    Returns
    -------
    T
        Instance of the dataclass with default values
    """
    field_values = {}
    for field in dataclasses.fields(cls):
        if field.default is not dataclasses.MISSING:
            field_values[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            field_values[field.name] = field.default_factory()
        else:
            # Handle nested dataclasses
            if dataclasses.is_dataclass(field.type):
                field_values[field.name] = initialize_dataclass_with_defaults(field.type)
            # Handle lists of dataclasses
            elif hasattr(field.type, '__origin__') and field.type.__origin__ is list:
                element_type = field.type.__args__[0]
                if dataclasses.is_dataclass(element_type):
                    field_values[field.name] = []
                else:
                    field_values[field.name] = []
            else:
                # For primitive types, use None or appropriate default
                field_values[field.name] = None
    
    return cls(**field_values)


def convert_from_json(json_dict: Dict[str, Any], target_class: Optional[Type] = None, separate_real_imag: bool = False) -> Any:
    """
    This function recursively converts a JSON dictionary back to a Pyro object or other target class.
    
    Parameters
    ----------
    json_dict : dict
        JSON dictionary to convert back to an object
    target_class : Type, optional
        The target class to instantiate. If None, will try to determine from the data.
    separate_real_imag : bool
        If true, expects real and imaginary parts to be in separate dictionary keys.
        If False, expects complex arrays to be encoded with __ndarray_tolist_real__ and __ndarray_tolist_imag__.
        
    Returns
    -------
    Any
        Converted object
    """
    if isinstance(json_dict, dict):
        # Check if this is a complex numpy array representation
        if '__ndarray_tolist_real__' in json_dict and '__ndarray_tolist_imag__' in json_dict:
            real_part = np.array(json_dict['__ndarray_tolist_real__'])
            imag_part = np.array(json_dict['__ndarray_tolist_imag__'])
            dtype = json_dict.get('dtype', 'complex128')
            shape = tuple(json_dict.get('shape', real_part.shape))
            return np.array(real_part + 1j * imag_part, dtype=dtype).reshape(shape)
        
        # Check if this is a dataclass representation
        if target_class is not None and dataclasses.is_dataclass(target_class):
            # Initialize with defaults first
            instance = initialize_dataclass_with_defaults(target_class)
            field_values = {}
            
            # Get type hints for the class
            type_hints = get_type_hints(target_class)
            
            # Process each field
            for field in dataclasses.fields(target_class):
                if field.name in json_dict:
                    field_type = type_hints.get(field.name, field.type)
                    
                    # Special handling for code field
                    if field.name == 'code' and isinstance(json_dict[field.name], str):
                        parsed_code = parse_xml_to_code(json_dict[field.name])
                        if parsed_code is not None:
                            field_values[field.name] = parsed_code
                        else:
                            print(f"Warning: Failed to parse code field, skipping...")
                            # Try to create an empty Code object with just the name
                            try:
                                field_values[field.name] = gkids.Code(name="GX")
                            except Exception as e:
                                print(f"Warning: Failed to create empty Code object: {e}")
                        continue
                    
                    # Check if this is an IDSPY type
                    idspy_type = get_idspy_type(field_type)
                    if idspy_type is not None:
                        field_type = idspy_type
                    
                    # Handle lists of dataclasses
                    if hasattr(field_type, '__origin__') and field_type.__origin__ is list:
                        element_type = field_type.__args__[0]
                        if dataclasses.is_dataclass(element_type):
                            field_values[field.name] = [
                                convert_from_json(item, element_type, separate_real_imag)
                                for item in json_dict[field.name]
                            ]
                        else:
                            field_values[field.name] = convert_from_json(json_dict[field.name])
                    
                    # Handle nested dataclasses
                    elif dataclasses.is_dataclass(field_type):
                        field_values[field.name] = convert_from_json(
                            json_dict[field.name], field_type, separate_real_imag
                        )
                    
                    # Handle complex numbers with separate real/imag parts
                    elif separate_real_imag:
                        real_key = f"{field.name}_real"
                        imag_key = f"{field.name}_imaginary"
                        if real_key in json_dict and imag_key in json_dict:
                            real_val = convert_from_json(json_dict[real_key])
                            imag_val = convert_from_json(json_dict[imag_key])
                            field_values[field.name] = real_val + 1j * imag_val
                        else:
                            field_values[field.name] = convert_from_json(json_dict[field.name])
                    
                    # Handle regular values
                    else:
                        field_values[field.name] = convert_from_json(json_dict[field.name])
            
            # Update instance with converted values
            for name, value in field_values.items():
                if value is not None:  # Only set non-None values
                    try:
                        setattr(instance, name, value)
                    except dataclasses.FrozenInstanceError:
                        # If the instance is frozen, we need to create a new one with all values
                        all_values = {f.name: getattr(instance, f.name) for f in dataclasses.fields(target_class)}
                        all_values.update(field_values)
                        return target_class(**all_values)
            
            return instance
        else:
            # Regular dictionary
            return {key: convert_from_json(value, target_class, separate_real_imag) 
                    for key, value in json_dict.items()}
    
    elif isinstance(json_dict, list):
        # List of items
        return [convert_from_json(item, target_class, separate_real_imag) for item in json_dict]
    
    else:
        # Primitive type (int, float, str, bool, None)
        return json_dict


def initialize_idspy_fields(gkdict: gkids.GyrokineticsLocal) -> None:
    """
    Initialize all IDSPY dataclass fields with minimal instances.
    
    Parameters
    ----------
    gkdict : gkids.GyrokineticsLocal
        The GyrokineticsLocal object to initialize fields for
    """
    # Create minimal instances for all IDSPY dataclass fields
    field_initializers = {
        'code': lambda: gkids.Code(
            name="GX",
            version=None,
            commit=None,
            repository=None,
            parameters=None,
            library=[]
        ),
        'collisions': lambda: gkids.Collisions(),
        'flux_surface': lambda: gkids.FluxSurface(),
        'species': lambda: [],  # List of Species objects
        'numerics': lambda: gkids.Numerics(),
        'coordinates': lambda: gkids.Coordinates(),
        'fields': lambda: gkids.Fields(),
        'diagnostics': lambda: gkids.Diagnostics(),
        'time': lambda: gkids.Time(),
    }
    
    # Set each field
    for field_name, initializer in field_initializers.items():
        try:
            if hasattr(gkdict, field_name):
                setattr(gkdict, field_name, initializer())
        except Exception as e:
            print(f"Warning: Failed to initialize {field_name} field: {e}")


def json_to_gkdict(json_dict: Dict[str, Any], separate_real_imag: bool = False) -> gkids.GyrokineticsLocal:
    """
    Convert a JSON dictionary back to a GyrokineticsLocal object.
    
    Parameters
    ----------
    json_dict : dict
        JSON dictionary representing a GyrokineticsLocal object
    separate_real_imag : bool
        If true, expects real and imaginary parts to be in separate dictionary keys.
        If False, expects complex arrays to be encoded with __ndarray_tolist_real__ and __ndarray_tolist_imag__.
        
    Returns
    -------
    GyrokineticsLocal object
    """
    # Create a base GyrokineticsLocal object with default values
    gkdict = gkids.GyrokineticsLocal()
    idspy.fill_default_values_ids(gkdict)
    
    # Initialize all IDSPY dataclass fields
    initialize_idspy_fields(gkdict)
    
    # Convert JSON data and update the object
    converted_data = convert_from_json(json_dict, target_class=gkids.GyrokineticsLocal, separate_real_imag=separate_real_imag)
    
    # Update fields from converted data, skipping IDSPY dataclass fields
    special_fields = {
        'code', 'collisions', 'flux_surface', 'species',
        'numerics', 'coordinates', 'fields', 'diagnostics', 'time'
    }
    
    for field in dataclasses.fields(gkids.GyrokineticsLocal):
        if field.name not in special_fields and hasattr(converted_data, field.name):
            value = getattr(converted_data, field.name)
            if value is not None:
                try:
                    setattr(gkdict, field.name, value)
                except dataclasses.FrozenInstanceError:
                    # If we can't set attributes, create a new instance
                    field_values = {f.name: getattr(gkdict, f.name) for f in dataclasses.fields(gkids.GyrokineticsLocal)}
                    field_values[field.name] = value
                    gkdict = gkids.GyrokineticsLocal(**field_values)
    
    return gkdict


def json_to_pyro(json_dict: Dict[str, Any], gk_code: Optional[str] = None, separate_real_imag: bool = False) -> Pyro:
    """
    Convert a JSON dictionary back to a Pyro object.
    
    Parameters
    ----------
    json_dict : dict
        JSON dictionary representing a Pyro object
    gk_code : str, optional
        The gyrokinetic code type (e.g., 'GENE', 'CGYRO', 'TGLF', 'GS2', 'GX')
        If provided, will be used to initialize the Pyro object
    separate_real_imag : bool
        If true, expects real and imaginary parts to be in separate dictionary keys.
        If False, expects complex arrays to be encoded with __ndarray_tolist_real__ and __ndarray_tolist_imag__.
        
    Returns
    -------
    Pyro object
    """
    temp_dir = None
    temp_file = None
    
    try:
        # First convert JSON to GyrokineticsLocal object
        gkdict = json_to_gkdict(json_dict, separate_real_imag=separate_real_imag)
        
        # Create a temporary file to store the IDS
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "temp_ids.h5")
        
        # Save the IDS to a temporary HDF5 file
        try:
            idspy.ids_to_hdf5(gkdict, filename=temp_file)
        except Exception as e:
            print(f"Warning: Failed to write to HDF5 file: {e}")
            # Try to create a new instance with minimal data
            gkdict = gkids.GyrokineticsLocal()
            idspy.fill_default_values_ids(gkdict)
            initialize_idspy_fields(gkdict)
            idspy.ids_to_hdf5(gkdict, filename=temp_file)
        
        # Convert the IDS to a Pyro object
        pyro = ids_to_pyro(temp_file, file_format="hdf5")
        
        return pyro
    
    finally:
        # Clean up temporary files
        if temp_file is not None and os.path.exists(temp_file):
            os.remove(temp_file)
        if temp_dir is not None and os.path.exists(temp_dir):
            os.rmdir(temp_dir)


def demonstrate_reverse_conversion(json_file_path: str, gk_code: Optional[str] = None) -> Pyro:
    """
    Demonstrate how to convert a JSON file back to a Pyro object.
    
    Parameters
    ----------
    json_file_path : str
        Path to the JSON file containing the Pyro object data
    gk_code : str, optional
        The gyrokinetic code type (e.g., 'GENE', 'CGYRO', 'TGLF', 'GS2', 'GX')
    
    Returns
    -------
    Pyro object
    """
    # Read the JSON file
    with open(json_file_path, 'r') as f:
        json_dict = json.load(f)
    
    # Convert JSON to Pyro object
    pyro = demonstrate_reverse_conversion(json_file_path, gk_code) 