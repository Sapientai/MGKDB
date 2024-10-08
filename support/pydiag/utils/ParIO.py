""" ParIO.py: Contains the class to handle reading and writing of parameter files """
import re
import numpy as np
from collections import namedtuple, OrderedDict


class Parameters(object):
    """ Parameters class:

    Converts a GENE parameters file to a python dictionary and vice versa
    """

    def __init__(self):
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

    @staticmethod
    def clearcomments(variable):
        regex = re.compile(r'\s*([-+\'\"\[\];.,/a-zA-Z0-9_\s*]*)\s*!?\s*(.*)')
        result = regex.search(variable)
        if result and result.group(2)[:4] != 'scan':
            return regex.search(variable).group(1)
        else:
            return variable

    def Read_Pars(self, path):
        """ Read parameters file and make it a dict """
        self.pardict.clear()
        self.nmldict.clear()
        # counts species namelists
        countspec = 0
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
                    p = re.compile(r'^\s*(.*)\s*=\s*(.*)')
                    m = p.search(line)
                    # Pick matching lines and build parameter dictionary
                    if m:
                        if m.group(1).strip() in self.spec_nl:
                            self.pardict[m.group(1).strip() + str(countspec)] = m.group(2)
                            self.nmldict[m.group(1).strip() + str(countspec)] = nml
                        else:
                            self.pardict[m.group(1).strip()] = m.group(2)
                            self.nmldict[m.group(1).strip()] = nml
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
            self.pardict[item] = self.clearcomments(self.pardict[item])
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
        defpars = {"x0": 0.5, "ky0_ind": 0, "kx_center": 0.0,
                   "n0_global": 0,
                   "omega_prec": 1E-3, "coll": 0.0,
                   "Omega0_tor": 0.0, "ExBrate": 0.0,
                   "with_coriolis" : False, "with_centrifugal" : False,
                   "with_comoving_other" : False, "with_bxphi0" : False,
                   "sign_Ip_CW": 1, "sign_Bt_CW": 1, "n_pol": 1,
                   "Tref": 1.0, "nref": 1.0, "Bref": 1.0, "mref": 1.999,
                   "Lref": 1.0, "passive" : False,
                   "GIT_MASTER": '', "GIT_BRANCH": ''
               }
        defpnml = {"x0": "box", "ky0_ind": "box", "kx_center": "box",
                   "n0_global": "box",
                   "omega_prec": "general", "coll": "general",
                   "Omega0_tor" : "external_contr", "ExBrate" : "external_contr",
                   "with_coriolis" : "external_contr", "with_centrifugal" : "external_contr",
                   "with_comoving_other" : "external_contr", "with_bxphi0" : "external_contr",
                   "sign_Ip_CW": "geometry", "sign_Bt_CW": "geometry", "n_pol": "geometry",
                   "Tref": "units", "nref": "units", "Bref": "units", "mref": "units",
                   "Lref": "units", "passive": "species",
                   "GIT_MASTER": "info", "GIT_BRANCH": "info"
               }

        for defkey in defpars.keys():
            #special treatment for species namelist defaults
            if defpnml[defkey]=="species":
                for ispec in range(1,self.pardict['n_spec']+1):
                    self.pardict.setdefault(defkey+"{}".format(ispec), defpars[defkey])
                    self.nmldict.setdefault(defkey+"{}".format(ispec), defpnml[defkey]+"{}".format(ispec))
            else:
                self.pardict.setdefault(defkey, defpars[defkey])
                self.nmldict.setdefault(defkey, defpnml[defkey])
        try:
            minor_r = self.pardict["minor_r"]
        except KeyError:
            minor_r = 1
        rhostar = np.sqrt(
                self.pardict["Tref"]*self.pardict["mref"]*1.e3/1.60217733E-19*1.67262e-27) / \
                self.pardict["Bref"]/minor_r/self.pardict["Lref"]
        self.pardict.setdefault("rhostar", rhostar)

    def Write_Pars(self, path):
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
            parfile.write(par[0:-1] + ' = ' + parvalue + '\n')
        else:
            parfile.write(par + ' = ' + parvalue + '\n')

    def asnamedtuple(self):
        """ Return Parameters as a named tuple for easier usage """
        # We have to ignore parameters with whitespace (in info nml)
        valid = {}
        for item in self.pardict:
            if " " not in item:
                if '(' in item or ')' in item:
                    item_reduced = item.replace('(', '_')
                    item_reduced = item_reduced.replace(')', '_')
                    valid[item_reduced] = self.pardict[item]
                else:
                    valid[item] = self.pardict[item]
        return namedtuple('ParTuple', valid.keys())(*valid.values())
