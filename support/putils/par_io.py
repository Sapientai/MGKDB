""" par_io.py: Contains the class to handle reading and writing of parameter files """
import re
from collections import namedtuple, OrderedDict
import numpy as np
import os

class Parameters:
    """ Parameters class:

    Converts a GENE parameters file to a python dictionary and vice versa
    Usually an instance of this object is used to create a named tuple with
    .asnamedtuple()
    """

    def __init__(self, in_folder, extension):
        # dictionary for parameters: {parameter: value}
        self.pardict = OrderedDict()
        # dictionary for recording the namelists the parameters belong to: {parameter: namelist}
        self.nmldict = OrderedDict()
        # keep track of all namelists that have been found
        self.namelists = []
        self.spec_nl = (
            'omn', 'omt', 'mass', 'charge', 'dens', 'temp', 'name', 'passive', 'kappa_n', 'kappa_T',
            'LT_center', 'Ln_center', 'LT_width', 'Ln_width', 'prof_type', 'src_prof_type',
            'src_amp', 'src_width', 'src_x0', 'delta_x_n', 'delta_x_T', 'prof_file')
        self.specnames = []
        self.extension = extension
        self.in_folder = in_folder
        read_path = os.path.join( in_folder, 'parameters{}'.format(extension) )
        self.read_pars( read_path )
        self.pnt = self.asnamedtuple()

    @staticmethod
    def _clearcomments(variable):
        regex = re.compile(r'\s*([-+\'\"\[\];.,/a-zA-Z0-9_\s*]*)\s*!?\s*(.*)')
        result = regex.search(variable)
        if result and result.group(2)[:4] != 'scan':
            return regex.search(variable).group(1)
        else:
            return variable

    def read_pars(self, path):
        """ Read parameters file and make it a dict """
        self.pardict.clear()
        self.nmldict.clear()
        # counts species namelists
        countspec = 0
        ispec=-1
        self.species=[]
        try:
            with open(path, "r") as parfile:
                # Search file for parameters using regular expressions
                for line in parfile:
                    # Exclude commented lines
                    if re.search(r'\s*!\w*\s*=.*', line) is None:
                        # Check for and count species namelists
                        if re.search(r'^\s*&(.*)', line):
                            # if namelist belongs to a species, append its number to the namelist
                            if re.search(r'^\s*&(.*)', line).group(1) == 'species':
                                countspec += 1
                                nml = re.search(r'^\s*&(.*)', line).group(1) + str(countspec)
                            else:
                                nml = re.search(r'^\s*&(.*)', line).group(1)
                            if nml not in self.namelists:
                                self.namelists.append(nml)
                    # Search lines for <parameter> = <value> patterns
                    par = re.compile(r'^\s*(.*)\s*=\s*(.*)')
                    match = par.search(line)
                    # Pick matching lines and build parameter dictionary
                    if match:
                        # need to sort species by name and not by appending a number
                        if match.group(1).strip() in self.spec_nl:
                            # the first output of GENE is the name, so this should be always fine
                            if match.group(1).strip() == 'name':
                                myname = match.group(2).strip().replace("'", "")
                                ispec+=1
                                self.specnames.append(myname)
                                self.species.insert(ispec,{"name": myname})
                            else:
                                #cast all to doubles
                                self.species[ispec].update({match.group(1).strip(): np.array(match.group(2),dtype=np.float64)})
                            self.pardict[match.group(1).strip() + myname] = match.group(2)
                            self.nmldict[match.group(1).strip() + myname] = nml
                            
                        else:
                            self.pardict[match.group(1).strip()] = match.group(2)
                            self.nmldict[match.group(1).strip()] = nml


        except IOError:
            print("Could not read parameters file")
            raise
        self._clean_parameters()
        self.add_defaults()

    def _clean_parameters(self):
        """ Clear the comments from all variables,

        Cast some strings to integers and floats
        """
        boolstr_t = [".T.", ".t.", "T", "t", ".true."]
        boolstr_f = [".F.", ".f.", "F", "f", ".false."]
        for item in self.pardict:
            self.pardict[item] = self._clearcomments(self.pardict[item])
            try:  # Can it be converted to int?
                self.pardict[item] = int(self.pardict[item])
            except ValueError:
                try:  # No, but can it be converted to float?
                    self.pardict[item] = float(self.pardict[item])
                except ValueError:
                    pass
            if self.pardict[item] in boolstr_t:  # cast switches to boolean values
                self.pardict[item] = True
            elif self.pardict[item] in boolstr_f:
                self.pardict[item] = False

    def add_defaults(self):
        """ Set default values GENE does not write

        Some diagnostics require these to exist at least in the named tuple
        """
        # defpars = {"x0": 0.5, "ky0_ind": 0, "Tref": 1.0, "nref": 1.0, "Bref": 1.0, "mref": 1.0,
        #           "Lref": 1.0, "sign_Ip_CW": 1, "sign_Bt_CW": 1,}
        defpars = {"x0": 0.5, "ky0_ind": 0, "kx_center": 0.0, "n0_global": 0,
                   "lx" : 0.0, "mu_grid_type": "gau_lag",
                   "omega_prec": 1E-3,
                   "coll": 0.0, "Omega0_tor": 0.0, "ExBrate": 0.0, "with_coriolis": False,
                   "with_centrifugal": False, "with_comoving_other": False, "with_bxphi0": False,
                   "sign_Ip_CW": 1, 
                   "sign_Bt_CW": 1, 
                   "n_pol": 1, 
                   "Tref": 1.0, 
                   "nref": 1.0,
                   "Bref": 1.0, 
                   "mref": 1.999, 
                   "Lref": 1.0, 
                   "write_h5": False,
                   "write_adios": False,
                   "istep_srcmom": 0, 
                   "ck_heat": 0.0, 
                   "ck_part": 0.0,
                   "PRECISION": "DOUBLE",
                   "ENDIANNESS": "LITTLE"}
        defpnml = {"x0": "box", 
                   "ky0_ind": "box", 
                   "kx_center": "box",
                   "n0_global": "box",
                   "lx": "box",
                   "mu_grid_type": "box",
                   "omega_prec": "general",
                   "coll": "general", 
                   "istep_srcmom": "in_out", 
                   "write_h5": "in_out",
                   "write_adios": "in_out",
                   "Omega0_tor": "external_contr",
                   "ExBrate": "external_contr", 
                   "with_coriolis": "external_contr",
                   "with_centrifugal": "external_contr",
                   "with_comoving_other": "external_contr",
                   "with_bxphi0": "external_contr",
                   "sign_Ip_CW": "geometry",
                   "sign_Bt_CW": "geometry",
                   "n_pol": "geometry",
                   "Tref": "units",
                   "nref": "units",
                   "Bref": "units",
                   "mref": "units",
                   "Lref": "units", 
                   "ck_heat": "nonlocal_x", 
                   "ck_part": "nonlocal_x",
                   "PRECISION": "info",
                   "ENDIANNESS": "info"}
        for defkey in defpars:
            self.pardict.setdefault(defkey, defpars[defkey])
            self.nmldict.setdefault(defkey, defpnml[defkey])
        try:
            minor_r = self.pardict["minor_r"]
        except KeyError:
            minor_r = 1
        try:
            rhostar = self.pardict["rhostar"]
        except KeyError:
            rhostar = np.sqrt(
                self.pardict["Tref"]*self.pardict["mref"]*1.e3/1.60217733E-19*1.67262e-27)/ \
                  self.pardict["Bref"]/minor_r/self.pardict["Lref"]
            self.pardict["rhostar"] = rhostar
        if self.pardict.get("lx_a", 0.0) == 0.0 and self.pardict.get("lx", 0.0) == 0.0:
            raise ValueError('Cannot determine lx')
        if self.pardict.get("lx", 0.0) == 0.0:
            self.pardict["lx"] = self.pardict["lx_a"] / rhostar
        

        ################################
        ## these should all disappear ##
        ################################
        self.pardict['x_local'] = self.pardict['x_local'] if 'x_local' in self.pardict else True
        self.pardict['y_local'] = self.pardict['y_local'] if 'y_local' in self.pardict else True
        self.pardict['is3d'] = not self.pardict['x_local'] and not self.pardict['y_local']
        self.pardict['x_global'] = not self.pardict['x_local'] and self.pardict['y_local']
        self.pardict['flux_tube'] = self.pardict['x_local'] and self.pardict['y_local']
        self.pardict['is_adios'] = self.pardict['write_hac'] if 'write_hac' in self.pardict else False
        self.pardict['electromagnetic'] = (self.pardict.get('beta', False) != 0)
        self.pardict['bpar'] = self.pardict['bpar'] if 'bpar' in self.pardict else False
        self.pardict['specnames'] = self.specnames

    def write_pars(self, path):
        """ Take the dict and write a GENE parameters file """
        parfileout = open(path, "w")
        specflag = False
        for item in self.namelists:
            specflag = False
            if item[0:-1] == 'species':
                specflag = True
                parfileout.write('&' + item[0:-1] + '\n')
            else:
                parfileout.write('&' + item + '\n')
            for par in self.pardict.keys():
                if self.nmldict[par] == item:
                    self._writeparameter(par, parfileout, specflag)
            parfileout.write('/\n\n')

    def _writeparameter(self, par, parfile, specflag):
        parvalue = str(self.pardict[par])
        # Take care of the different form of logic states in Python and Fortran
        if parvalue == "True":
            parvalue = ".T."
        elif parvalue == "False":
            parvalue = ".F."
        if specflag:
            # Get rid of the species names at the end
            for sname in self.specnames:
                strippar = par.replace(sname, "")
            parfile.write(strippar + ' = ' + parvalue + '\n')
        else:
            parfile.write(par + ' = ' + parvalue + '\n')

    def asnamedtuple(self):
        """ Return Parameters as a named tuple for easier usage """
        # We have to ignore parameters with whitespace (in info nml)
        valid = {}
        for item in self.pardict:
            if " " not in item:
                valid[item] = self.pardict[item]
        return namedtuple('ParTuple', valid.keys())(*valid.values())