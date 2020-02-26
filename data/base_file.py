""" Base classes for file reading"""

import struct
from bisect import bisect_left, bisect_right
from os.path import getsize
import abc
import pathlib
import h5py
import numpy as np
import utils.averages as av


class File(abc.ABC):
    """ Base class to read files from GENE runs"""

    @abc.abstractmethod
    def __init__(self, file=None, run_data=None, varname=None, prepath=None,
                 spec=None, extensions=None, is_profile=False, is_complex=True):
        self.run_data = run_data
        self.spec = spec
        self.extensions = extensions
        self.varname = varname
        self.prepath = prepath
        self.time = None
        self.tind = -1
        self.file = file
        self.timeseries = None
        self._reset_tinds()

    @abc.abstractmethod
    def _redirect(self, extension):
        """ Call this routine to read from a new file"""

    @classmethod
    def __add_method__(cls, name, idx):

        def _method(self, time=None, step=None):
            if time:
                self.time = time
            if not self.loaded_time[idx] == time:
                self.loaded_time[idx] = time
                if step:
                    self.tind = step.step
                    if self.extension != step.file:
                        self.extension = step.file
                        self._redirect(self.extension)
                if not self.fid:
                    self._redirect()
                setattr(self, name + "3d", self._readvar(idx))

            return getattr(self, name + "3d")

        return _method

    # The following methods are general, for any file since is operation on time array

    def get_filename(self, extension=None):
        """ Construct the file name from information present in the object """
        if self.run_data:
            return self.run_data.in_folder +'/'+ (
                    (self.file + '_' + self.spec if self.spec else self.file) + (
                    extension if extension else self.extension))
        else:
            return None

    def set_times_and_inds(self):
        """ this is to be used for collecting all times from a series of extensions
            will return times, steps, and file extension.
            the whole time series is also set in the object"""
        self._reset_tinds()

        time_list = self.get_timearray(self.extensions[0])
        step_list = np.array(range(0, len(time_list), 1)).tolist()
        file_list = [self.extensions[0]]*len(time_list)

        for ext in self.extensions[1:]:
            t_loc = self.get_timearray(ext)
            time_list = np.concatenate((time_list, t_loc))
            step_list = np.concatenate((step_list, np.array(range(0, len(t_loc), 1))))
            file_list = file_list + [ext]*len(time_list)

        # Remove duplicates
        self.timeseries, inds = np.unique(time_list, return_index=True)
        time_list = np.array([time_list[i] for i in inds])
        step_list = np.array([step_list[i] for i in inds])
        file_list = [file_list[i] for i in inds]

        self._reset_tinds()

        return time_list, step_list, file_list

    def get_minmaxtime(self):
        """ Return the first and last time stamp in the file

        Fetch them from the file first if necessary
        """
        if not self.timearray:
            self.get_timearray()
        return self.timearray[0], self.timearray[-1]

    @abc.abstractmethod
    def get_timearray(self, extension=None):
        """ Fetch the time stamps from the file"""


    @abc.abstractmethod
    def _readvar(self, *args):
        """ Fetch a specific variable at the set time from the file"""

    def _find_nearest_time(self, time):
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

    def set_approximate_time(self, time):
        """ Set the internal time to the closest time stamp in the file"""
        exacttime = self._find_nearest_time(time)
        self.set_time(exacttime)

    def set_time(self, time):
        """ Set current timestep by value"""
        self.time = self._find_nearest_time(time)
        self.tind = self.timearray.index(self.time)

    def set_tind(self, tind):
        """ Set current timestep by index"""
        self.tind = tind
        self.time = self.timearray[tind]

    def get_var(self, name):
        """ Fetch the data at set time, only accessing file if necessary """
        varidx = {v: k for k, v in self.varname.items()}
        if not self.loaded_time[varidx[name]] == self.time:
            self.loaded_time[varidx[name]] = self.time
            setattr(self, name + "3d", self._readvar(varidx[name]))
        return getattr(self, name + "3d")

    def _reset_tinds(self):
        """ Reset time indices when reloading file"""
        self.loaded_time = [-1]*len(self.varname)
        self.tind = -1
        self.time = None
        self.timearray = None
        self.extension = self.extensions[0]
        self.filename = self.get_filename()
        self._redirect(self.extension)


class BinaryFile(File):
    """ Base class to read Fortran binary (unformatted) files from GENE runs"""

    def __init__(self, file=None, run_data=None, varname=None, prepath=None, spec=None,
                 nfields=None, extensions=None, is_profile=None, is_complex=True):
        super().__init__(file=file, run_data=run_data, varname=varname, prepath=prepath,
                         spec=spec, extensions=extensions, is_profile=is_profile,
                         is_complex=is_complex)
        # I dont see the point of copying the run into the object,
        # unless we want to create all objects at initialization and use them as list
        self.fid = None
        self.timearray = []
        self.tind = -1
        self.time = None
        self.nfields = nfields
        self.extension = run_data.fileextension
        self.filename = self.get_filename(self.extension)
        self.loaded_time = [-1]*len(self.varname)
        self._set_datatypes()
        self.tentry, self.tesize = self.time_entry()
        self._set_sizes(is_profile, is_complex)

        for idx in self.varname:
            setattr(self, varname[idx] + "3d", None)

        self.loaded_tind = [-1]*len(self.varname)

        for idx in varname:
            new_method = File.__add_method__(varname[idx], idx)
            setattr(File, varname[idx], new_method)

    def _redirect(self, extension=None):
        """ Call this routine to read from a new file"""
        if extension:
            self.extension = extension
            self.filename = self.get_filename(self.extension)
        try:
            self.fid.close()
        except (AttributeError, OSError):
            pass
        self.fid = open(self.filename, 'rb')
        self.timearray = []

    #        self.get_timearray()
    #        self._reset_tinds()

    def get_timearray(self, extension=None):
        """ Get time array from file """
        # am I pointing to the right file?
        if extension and self.extension != extension:
            self._redirect(extension)
            self.extension = extension
        # if not pointing to anything
        if not self.fid:
            self._redirect()

        self.timearray = []
        self.fid.seek(0)
        for _ in range(int(getsize(self.filename)/(self.leapfld + self.tesize))):
            self.timearray.append(float(self.tentry.unpack(self.fid.read(self.tesize))[1]))
            self.fid.seek(self.leapfld, 1)
        return self.timearray

    def _set_datatypes(self):
        try:
            self.bigendian = self.run_data.pars['ENDIANNESS'] == 'BIG'
        except KeyError:
            self.bigendian = False
        if self.bigendian:
            self.nprt = (np.dtype(np.float64)).newbyteorder()
            self.npct = (np.dtype(np.complex128)).newbyteorder()
        else:
            self.nprt = np.dtype(np.float64)
            self.npct = np.dtype(np.complex128)

    def _set_sizes(self, is_profile, is_complex):
        self.intsize = 4
        try:
            self.realsize = 8 if self.run_data.pars['PRECISION'] == 'DOUBLE' else 4
        except KeyError:
            self.realsize = 8
        self.complexsize = 2*self.realsize
        # this is correct only for field asnd mom. other files are different
        self.entrysize = self.run_data.pnt.nx0 if is_profile else \
            self.run_data.pnt.nx0*self.run_data.pnt.nky0*self.run_data.pnt.nz0
        self.entrysize = self.entrysize * self.complexsize if is_complex else \
            self.entrysize * self.realsize
        # jump in bytes in field files
        self.leapfld = self.nfields*(self.entrysize + 2*self.intsize)

    def time_entry(self):
        """ Defines the struct for a time entry """
        # Fortran writes records as sizeof(entry) entry sizeof(entry)
        if self.bigendian:
            timeentry = struct.Struct('>idi')
        else:
            timeentry = struct.Struct('=idi')
        return timeentry, timeentry.size

    def offset(self, var):
        """Calculate offset in field file for a given self.time and variable"""
        if var in [i for i in range(self.nfields)]:
            return self.tesize + self.tind*(self.tesize + self.leapfld) + var*(
                self.entrysize + 2*self.intsize) + self.intsize

    def _readvar(self, var):
        """ Return 3d field data at the time set in self.time"""
        self.fid.seek(self.offset(var))
        var3d = np.fromfile(self.fid,
                            count=self.run_data.pnt.nx0*self.run_data.pnt.nky0*self.run_data.pnt
                            .nz0,
                            dtype=self.npct)
        # Bring array into x, y. z order
        if self.run_data.x_local and not self.run_data.y_local:  # y-global has yx order
            var3d = var3d.reshape(self.run_data.pnt.nky0, self.run_data.pnt.nx0,
                                  self.run_data.pnt.nz0, order="F")
            var3d = np.swapaxes(var3d, 0, 1)
        else:
            var3d = var3d.reshape(self.run_data.pnt.nx0, self.run_data.pnt.nky0,
                                  self.run_data.pnt.nz0, order="F")
        return var3d


class H5File(File):
    """ Base class to read HDF5 files from GENE runs"""

    def __init__(self, file=None, run_data=None, varname=None, prepath=None, spec=None,
                 nfields=None, extensions=None):
        super().__init__(file=file, run_data=run_data, varname=varname, prepath=prepath, spec=spec,
                         extensions=extensions)
        self.timearray = []
        self.tind = -1
        self.time = None
        self.nfields = nfields
        self.fid = None
        self.extension = run_data.fileextension
        self.filename = self.get_filename(run_data.fileextension if run_data else None)
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

    #        self.get_timearray()
    #        self._reset_tinds()

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
        if self.run_data.x_local and not self.run_data.y_local:
            # y-global has yx order
            out = np.swapaxes(out, 0, 1)
        else:
            pass
        return out


# pylint: disable=invalid-name
def create_GENEfile(file_type, run_data, spec=None, extensions=None):
    """ Return a File object appropriate to the GENE output present"""

    def _check_for_em(dic, run_data):
        """ check if we really have EM parts"""
        if not run_data.electromagnetic:
            dic['field'] = {0: 'phi'}
            if not run_data.is3d:
                dic['mom'] = dict((k, (dic['mom'])[k]) for k in range(6))
        elif not run_data.bpar:
            dic['field'] = {0: 'phi', 1: 'A_par'}
            dic['mom'] = dict((k, dic['mom'][k]) for k in range(6))
        # TODO add trap-passing splitting
        return dic

    VARS_TO_FILE_MAP = {'field': {0: 'phi', 1: 'A_par', 2: 'B_par'},
                        'mom': ({0: "n", 1: "u_par", 2: "T_par", 3: "T_per",
                                 4: "Q_es", 5: "Q_em", 6: 'Gamma_es',
                                 7: 'Gamma_em'}
                                if run_data.is3d else
                                {0: "dens", 1: "T_par", 2: "T_perp",
                                 3: "q_par", 4: "q_perp", 5: "u_par",
                                 6: 'densI1', 7: 'TparI1', 8: 'TppI1'}),
                        'srcmom': ({0: "ck_heat_M00", 1: "ck_heat_M10",
                                    2: "ck_heat_M22", 3: "ck_part_M00",
                                    4: "ck_part_M10", 5: "ck_part_M22",
                                    6: "f0_term_M00", 7: "f0_term_M10",
                                    8: "f0_term_M22"}),
                        #Todo: The Q_es name interferes with the Q_es name of mom
                        'vsp':({0: '<f_>', 1: 'G_es', 2: 'G_em', 3: 'Q_ese',
                                4: 'Q_em'})}

    VARS_TO_FILE_MAP = _check_for_em(VARS_TO_FILE_MAP, run_data)
    PREPATH_TO_FILE_MAP = {'field': '/field/',
                           'mom': '/mom_{}/'.format(spec),
                           'srcmom': '/srcmom_{}/'.format(spec),
                           'vsp': '/vsp/'}
    # TODO does this inherit the trap_passing splitting?
    # can simply count the variables.
    NFIELDS_TO_FILE_MAP = {'field': int(run_data.pars['n_fields']),
                           'mom': int(run_data.pars['n_moms']),
                           'srcmom': 9,
                           'vsp': 5}
    IS_PROFILE_MAP = {'field': False, 'mom': False, 'srcmom': True, 'vsp': False}
    IS_COMPLEX_MAP = {'field': True, 'mom': True, 'srcmom': False, 'vsp': False}


    if run_data.is_h5:
        try:
            return H5File(file=file_type, run_data=run_data,
                          varname=VARS_TO_FILE_MAP[file_type],
                          prepath=PREPATH_TO_FILE_MAP[file_type],
                          spec=spec,
                          nfields=NFIELDS_TO_FILE_MAP[file_type],
                          extensions=extensions)
        except KeyError as kerr:
            raise ValueError('Bad file type {}'.format(file_type)) from kerr

    elif run_data.is_adios:
        raise NotImplementedError('ADIOS not yet implemented')
    else:
        try:
            return BinaryFile(file=file_type, run_data=run_data,
                              varname=VARS_TO_FILE_MAP[file_type],
                              prepath=PREPATH_TO_FILE_MAP[file_type],
                              spec=spec,
                              nfields=NFIELDS_TO_FILE_MAP[file_type],
                              extensions=extensions,
                              is_profile=IS_PROFILE_MAP[file_type],
                              is_complex=IS_COMPLEX_MAP[file_type])
        except KeyError as kerr:
            raise ValueError('Bad file type {}'.format(file_type)) from kerr


class TimeSeries(abc.ABC):
    """ Base class for for any time series

    This is used for formatted (ascii) GENE output as well as derived data
    from GENE diagnostics
    :param objectname: Either a file name (e.g. profile_Ions.dat) or a (freely choosable) name for
     a derived dataset
    :param run_data: CommonData object of the current run
    """

    def __init__(self, objectname, run_data):
        self.objectname = objectname
        self.cm = run_data
        self.timearray = []
        self.dataarray = []
        self.timeaverage = None

    @abc.abstractmethod
    def generate_timeseries(self):
        """ Method to fetch data into the object"""

    def generate_timeaverage(self):
        """ Average over the time series and generate it if no data is present"""
        if self.dataarray:
            self.timeaverage = av.mytrapz(self.dataarray, self.timearray)
        else:
            self.generate_timeseries()
            self.timeaverage = av.mytrapz(self.dataarray, self.timearray)

    def get_minmaxtime(self):
        """ Return first and last time in the object

        If self.fileobject is set, try to get it from there
        """
        if np.array(self.timearray).size == 0:
            try:
                self.timearray = self.fileobject.timearray
            except AttributeError:
                raise RuntimeError("Time array not available or empty")
        return self.timearray[0], self.timearray[-1]

    def check_times(self):
        """ Set the boundaries of the time window to read"""
        first_time, last_time = self.get_minmaxtime()
        if len(self.timearray) != len(set(self.timearray)):
            raise RuntimeError("Error: {} contains 2 blocks with "
                               "identical timestamp".format(self.objectname))
        if self.starttime == -1 or (0 < self.starttime < first_time):
            print("Using first time present in {} for starttime".format(self.objectname))
            self.starttime = first_time
        if self.endtime == -1:
            print("Using first time present in {} for endtime".format(self.objectname))
            self.endtime = first_time
        if self.starttime == -2:
            print("Using last time present in {} for starttime".format(self.objectname))
            self.starttime = last_time
        if (self.endtime == -2) or (self.endtime > last_time):
            print("Using last time present in {} for endtime".format(self.objectname))
            self.endtime = last_time
        if (self.endtime < first_time) or (self.starttime > last_time):
            raise RuntimeError("Time window not contained in {}".format(self.objectname))
        print(("starttime={}, endtime={},"
               " first_time={}, last_time={}".format(self.starttime, self.endtime, first_time,
                                                     last_time)))

    def calc_positions(self):
        """ For a single time, find element closest to given input time"""
        timearray = self.timearray
        if self.starttime == self.endtime:
            pos = np.array([bisect_left(timearray, self.starttime)])
        else:
            startpos = bisect_left(timearray, self.starttime)
            endpos = bisect_right(timearray, self.endtime)
            pos = np.arange(startpos, endpos)
        return pos

    def calc_nearest(self, target):
        """ For a single time, find element closest to given input time"""
        timearray = self.timearray
        if target >= timearray[-1]:
            return len(timearray) - 1
        elif target <= timearray[0]:
            return 0
        else:
            return bisect_right(timearray, target)


def gluetimetraces(tserieslist):
    """ Function to concatenate a list of time series (continuation runs) into one single object

    for continuation runs
    :param tserieslist: List of TimeSeries objects to connect
    :returns: One connected TimeSeries object
    """
    # TODO: Consistency checks if runs match
    if len(tserieslist) == 1:
        return tserieslist[0]
    # Use first TimeSeries as basis for the construction of the glued object
    result = tserieslist.pop(0)
    # If the timefield has been converted to a np array before we need to undo it
    try:
        result.timearray = result.timearray.tolist()
    except AttributeError:
        pass
    for tseries in tserieslist:
        # When times overlap, give following TimeSeries preference
        while result.timearray[-1] > tseries.timearray[0]:
            del result.timearray[-1]
            del result.dataarray[-1]
        result.timearray = np.concatenate((result.timearray, tseries.timearray))
        result.dataarray = np.concatenate((result.dataarray, tseries.dataarray))
    result.endtime = tserieslist[-1].endtime
    del tserieslist
    return result
