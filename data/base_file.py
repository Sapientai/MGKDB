""" Base classes for file reading"""

import struct
from bisect import bisect_left, bisect_right
import os
from os.path import getsize
import abc
import h5py
import numpy as np
import types


class File(abc.ABC):
    """ Base class to read files from GENE runs"""

    @abc.abstractmethod
    def __init__(self, folder=None, extension=None, file_type=None, parameters=None, spec=None):
        """ call this to initialize the file"""
        
    @abc.abstractmethod
    def redirect(self, folder=None, extension=None, parameters=None):
        """ Call this routine to read from a new file of the same type"""

    @abc.abstractmethod
    def get_filename(self):
        """ Construct the file name from information present in the object """

    @abc.abstractmethod
    def get_timearray(self):
        """ Fetch the time stamps from the file""" 
        
    def get_minmaxtime(self):
        """ Return the first and last time stamp in the file
        """
        if not self.timearray:
            self.get_timearray()
        return self.timearray[0], self.timearray[-1]           
        
    def get_times_and_inds(self):
        """ this is to be used for collecting all times in the file
            will return times, steps, and file extension.
            """
        if not self.timearray:
            self.__reset_tinds()
            time_list = self.get_timearray()

        times = np.asarray(self.timearray)
        steps = np.arange(0, times.size, 1)
        file_list = [self.extension]*times.size

        return times, steps, file_list

    def _find_nearest_time(self, time):
        """ Convert an time to its nearest step """
        pos = bisect_left(self.timearray, time)
        if pos == 0:
            return self.timearray[0]
        if pos == len(self.timearray):
            return self.timearray[-1]
        before = self.timearray[pos - 1]
        after = self.timearray[pos]
        if after - time < time - before:
            return after
        else:
            return before
        
    def _time_to_step(self, idx):
        """ Convert an exact time to its step """
        if not self.timearray:
            self.get_timearray()
        self.loaded_step[idx]=np.where(self.timearray == self.loaded_time[idx])
        
    def _step_to_time(self, idx):
        """ Convert the step to its time """
        if not self.timearray:
            self.get_timearray()
        self.loaded_time[idx]=self.timearray[self.loaded_step[idx]]    
        
    def _fix_step(self, step):
        """ Allow for negative steps like python """
        if step<0 :
            if not self.timearray:
                self.get_timearray()
            step=np.arange(len(self.timearray))[step]  
        return step
    
    def __reset_tinds(self):
        """ Reset time indices """
        self.loaded_time = [None]*self._nfields
        self.loaded_step = [None]*self._nfields
        self.timearray = []

    @abc.abstractmethod
    def _readvar(self, *args):
        """ Fetch a specific variable at the set time from the file"""

    def get_var(self, name):
        """ Fetch the data at set time, only accessing file if necessary """
        varidx = {v: k for k, v in self.varname.items()}
        if not self.loaded_time[varidx[name]] == self.time:
            self.loaded_time[varidx[name]] = self.time
            setattr(self, name + "_data", self._readvar(varidx[name]))
        return getattr(self, name + "_data")

    def _define_variables(self, parameters):
        """ provided a file type (e.g. field) it will return the list of variables
            that are in that file"""

        VARS_TO_FILE_MAP = {'field': {0: 'phi', 
                                      1: 'A_par', 
                                      2: 'B_par'},
                            'mom':  {0: "dens",
                                     1: "T_par", 
                                     2: "T_perp",
                                     3: "q_par", 
                                     4: "q_perp", 
                                     5: "u_par",
                                     6: 'densI1', 
                                     7: 'TparI1', 
                                     8: 'TppI1'},
                            'srcmom':  {0: "ck_heat_M00", 
                                        1: "ck_heat_M10",
                                        2: "ck_heat_M22",
                                        3: "ck_part_M00",
                                        4: "ck_part_M10",
                                        5: "ck_part_M22",
                                        6: "f0_term_M00",
                                        7: "f0_term_M10",
                                        8: "f0_term_M22"},
                            'vsp':  {0: '<f_>',
                                     1: 'G_es', 
                                     2: 'G_em', 
                                     3: 'Q_es',
                                     4: 'Q_em'}}                       
        return dict(list(VARS_TO_FILE_MAP[self.file_type].items())[0: self._set_nfields(parameters)]) 


    def _set_nfields(self, parameters):
        NFIELDS_TO_FILE_MAP = {'field': int(parameters.pardict['n_fields']),
                               'mom': int(parameters.pardict['n_moms']),
                               'srcmom': 9,
                               'vsp': 5}
        return NFIELDS_TO_FILE_MAP[self.file_type]  

    def _is_complex(self):
        IS_COMPLEX_MAP = {'field' : True, 
                          'mom'   : True, 
                          'srcmom': False,
                          'vsp'   : False}

        return IS_COMPLEX_MAP[self.file_type]

    def _set_boxsize(self, parameters):
        BOX_SIZE_MAP = {'field' : np.array([parameters.pnt.nx0, parameters.pnt.nky0, parameters.pnt.nz0]),
                        'mom'   : np.array([parameters.pnt.nx0, parameters.pnt.nky0, parameters.pnt.nz0]),
                        'src'   : np.array([parameters.pnt.nx0]),
                        'vsp'   : np.array([parameters.pnt.nz0, parameters.pnt.nv0, parameters.pnt.nw0])}

        return BOX_SIZE_MAP[self.file_type]

    def _set_prepath(self, file_type, spec):
        PREPATH_TO_FILE_MAP = {'field': '/field/',
                               'mom': '/mom_{}/'.format(spec),
                               'srcmom': '/srcmom_{}/'.format(spec),
                               'vsp': '/vsp/'}

        return PREPATH_TO_FILE_MAP[file_type]

    def _check_for_trap_split(self, dic, run_data):
        # TODO
        return dic

class BinaryFile(File):
    """ Base class to read Fortran binary (unformatted) files from GENE runs        
    """
    def __init__(self, folder=None, extension=None, file_type=None, parameters=None, spec=None):
        super().__init__(folder=None, extension=None, file_type=None, parameters=None, spec=None)
        
        # these are public so we can reuse the object if we have to by redirecting it to a new folder/extension
        self.folder = parameters.in_folder                   # current folder we are pointing at
        self.extension = parameters.extension                # current extension we are pointing at
        self.file_type=file_type
        self.__spec=spec
        self.varnames = None
        
        # fid for reading
        self.__fid = None                                    # file identifier for reading 
   
        # point the object to folder/file_type+extension, setting fid, variables and sizes.
        self.redirect(folder, extension, parameters)      
    
        self.timearray = []                                 # time series saved in the file      
 
    def get_filename(self):          
        rstring = self.file_type
        if self.__spec:
            rstring += '_' + self.__spec
        rstring+=self.extension
        
        return os.path.join(self.folder, rstring)
            
    def redirect(self, folder=None, extension=None, parameters=None):
        """ Call this routine to read from a new file. To allow for precision change
            must reset all size."""
        
        if folder == self.folder and self.extension==extension:
            #already athe right file
            pass
        
        if folder:
            self.folder = folder
        if extension:
            self.extension = extension
            
        # make sure the file is closed
        try:
            self.__fid.close()
        except (AttributeError, OSError):
            pass        
        
        # get the filename we want
        self.filename = self.get_filename()
        
        # now oen the file
        try:
            self.__fid = open(self.filename, 'rb')
        except:
            raise Exception(self.filename + " does not exist")
        
        # now set the content of the file
        # do it only if is the first time
        if not self.varnames:
            self.varnames = self._define_variables(parameters)
        
            # data size
            self.boxsize = self._set_boxsize(parameters)
            self._nfields = self._set_nfields(parameters)
        
            # data properties for reading
            self.__set_datatypes(parameters)
            self.__set_sizes(parameters)
            self.__tentry, self.__tesize = self.__set_time_entry(parameters)
        
        #reset times and ind
        self.timearray = [] 
        self.loaded_time = [None]*self._nfields              # time step currently loaded for a given variable
        self.loaded_step = [None]*self._nfields              # timestep at which fid is pointing       


    def __set_datatypes(self, parameters):
        if parameters.pardict['PRECISION'] == 'DOUBLE':
            self.__nprt = np.dtype(np.float64)
            self.__npct = np.dtype(np.complex128)
        else:
            self.__nprt = np.dtype(np.float32)
            self.__npct = np.dtype(np.complex64)
            
        if  parameters.pardict['ENDIANNESS'] == 'BIG':
            self.__nprt=self.__nprt.newbitorder()
            self.__npct=self.__npct.newbitorder()
                

    def __set_sizes(self, parameters):
        """we must set based on current file precision"""
        self.__intsize = 4
        self.__realsize = 8 if parameters.pardict['PRECISION'] == 'DOUBLE' \
                        else 4
        self.__complexsize = 2*self.__realsize
        
        if self._is_complex():
            self.__entrysize = np.prod(self.boxsize) * self.__complexsize
        else:    
            self.__entrysize = np.prod(self.boxsize) * self.__realxsize   
        self.__leapfld = self._nfields*(self.__entrysize + 2*self.__intsize)

    def __set_time_entry(self,parameters):
        """ Defines the struct for a time entry """
        # Fortran writes records as sizeof(entry) entry sizeof(entry)
        if parameters.pardict['PRECISION'] == 'DOUBLE':
            if parameters.pardict['ENDIANNESS'] == 'BIG':
                timeentry = struct.Struct('>idi')
            else:
                timeentry = struct.Struct('=idi')
        else:
            if parameters.pardict['ENDIANNESS'] == 'BIG':
                timeentry = struct.Struct('>ifi')
            else:
                timeentry = struct.Struct('=ifi')

        return timeentry, timeentry.size

    def offset(self, idx):
        """Calculate offset in field file for a given self.time and variable"""
        if idx in range(self._nfields):
            return self.__tesize + self.loaded_step[idx]*(self.__tesize + self.__leapfld) + idx*(
                self.__entrysize + 2*self.__intsize) + self.__intsize
        else:
            print("Something went terribly wrong here")

    def _readvar(self, idx):
        """ Return 3d field data at the time set in self.time"""
        self.__fid.seek(self.offset(idx))       
        var3d = np.fromfile(self.__fid, count=np.prod(self.boxsize),
                            dtype=self.__npct)
        
        return var3d.reshape(tuple(self.boxsize), order="F")

    def get_timearray(self):
        """ Get time array from file """
        self.timearray = []
        self.__fid.seek(0)
        for _ in range(int(getsize(self.filename)/(self.__leapfld + self.__tesize))):
            self.timearray.append(float(self.__tentry.unpack(self.__fid.read(self.__tesize))[1]))
            self.__fid.seek(self.__leapfld, 1)
        return self.timearray   
    
def read_method(afile, name, idx):
    def __my_read_method(self, time=None, step=None, extension=None):
        if extension and not extension==self.extension:
            #this does not support change in precision
            self.redirect(self.folder, extension)
        
        if time is not None and not self.loaded_time[idx] == time:
            # loading by time but the data is not what we have been asked
            self.loaded_time[idx] = time
            # convert to step
            self._time_to_step(idx)
            #load the step
            setattr(self, name + "_data", self._readvar(idx))
        elif step is not None and not self.loaded_step[idx] == step:            
            # loading by step but the data is not what we have been asked
            self.loaded_step[idx] = self._fix_step(step)
            # convert to time
            self._step_to_time(idx)
            # load the step  
            setattr(self, name + "_data", self._readvar(idx))
        return getattr(self, name + "_data")
     
    setattr(afile, name, types.MethodType(__my_read_method, afile))
    

class H5File(File):
    """ Base class to read HDF5 files from GENE runs"""

    def __init__(self, file=None, run_data=None, varname=None, prepath=None, spec=None,
                 nfields=None, extension=None):
        super().__init__(file=file, run_data=run_data, varname=varname, prepath=prepath, spec=spec,
                         extension=extension)
        self.timearray = []
        self.step = None
        self.time = None
        self.nfields = nfields
        self.fid = None
        self.extension = run_data.pnt.extension
        self.filename = self.get_filename(run_data.pnt.extension if run_data else None)
        for idx in self.varname:
            setattr(self, varname[idx] + "3d", None)

        self.loaded_tind = [-1]*len(self.varname)
        self.loaded_time = [-1]*len(self.varname)

        for idx in varname:
            new_method = File.__add_method__(self.varname[idx], idx)
            setattr(File, varname[idx], new_method)

    def _redirect(self, extension=None):
        """ Call this routine to read from a new file"""
        if extension:
            self.extension = extension
        self.filename = self.get_filename(self.extension)
        try:
            self.h5file.close()
        except (AttributeError, OSError):
            pass
        self.fid = h5py.File(self.filename, 'r')
        self.timearray = []
        self._reset_tinds()

    def get_timearray(self, extension=None):
        """ Fetch time stamps from the HDF5 file"""
        # am I pointing to the right file?
        if extension and self.extension != extension:
            self._redirect(extension)
            self.extension = extension
        if not self.fid:
            self._redirect()
        # Get time array for field file
        self.timearray = self.fid.get(self.prepath + "time")[()].tolist()
        return self.timearray

    def _readvar(self, var):
        """ Return 3d field data at the time set in self.time"""
        out = self.fid.get(
            self.prepath + self.varname[var] + "/" + '{:010d}'.format(self.tind))[()]
        # TODO convert in a different way?
        if len(out.dtype) == 2:
            out = out['real'] + 1.0j*out['imaginary']
        if len(out.shape) == 3:
            out = np.swapaxes(out, 0, 2)
        elif len(out.shape) == 4:
            np.swapaxes(out, 1, 3)
        else:
            np.swapaxes(out, 0, 1)
        if self.run_data.pnt.x_local and not self.run_data.pnt.y_local:
            # y-global has yx order
            out = np.swapaxes(out, 0, 1)
        else:
            pass
        return out


# pylint: disable=invalid-name


def GENEfile(folder, extension, file_type, parameters, spec=None):
    if parameters.pnt.write_h5:
        raise NotImplementedError('ADIOS not yet implemented')
    elif parameters.pnt.write_adios:
        raise NotImplementedError('ADIOS not yet implemented')
    else:
        try:        
            afile = BinaryFile(folder, extension, file_type, parameters, spec=spec)
            for idx, name in afile.varnames.items():
                read_method(afile, name, idx)            
            return afile
        except KeyError as kerr:
            raise ValueError('Bad file type {}'.format(file_type)) from kerr