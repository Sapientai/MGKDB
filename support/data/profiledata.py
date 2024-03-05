""" profiledata.py: handles background profile information"""
import numpy as np
import h5py
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm

class ProfileData:
    """Class handling the profile files of a run
    """
    def __init__(self,folder,extension,params):
        """ Read parameter file and create empty arrays for profile data """
        self.species=params.species
        self.nref=params.pnt.nref
        self.Tref=params.pnt.Tref
        self.xs = np.empty(params.pnt.nx0,dtype=float)
        self.x_a = np.empty(params.pnt.nx0,dtype=float)
        self.temp = np.empty(params.pnt.n_spec,dtype=float)
        self.dens = np.empty(params.pnt.n_spec,dtype=float)
        self.T0 = np.empty([params.pnt.n_spec, params.pnt.nx0],dtype=float)
        self.n0 = np.empty([params.pnt.n_spec, params.pnt.nx0],dtype=float)
        self.omt0 = np.empty([params.pnt.n_spec, params.pnt.nx0],dtype=float)
        self.omn0 = np.empty([params.pnt.n_spec, params.pnt.nx0],dtype=float)
        self.__set_background_profiles(folder,extension,params)
        
    def __set_background_profiles(self,folder,extension,params):
        for i_spec in range(params.pnt.n_spec):
            if params.pnt.x_local:
                self.T0[:,i_spec]=1.0
                self.n0[:,i_spec]=1.0
                self.omt0[:,i_spec]=params.species[i_spec]['omt']
                self.omn0[:,i_spec]=params.species[i_spec]['omn']
            else:
                self.__read_input_profile(folder,extension,i_spec, params)

    def __read_input_profile(self,folder,extension,i_spec, params):
        """Get the initial profiles from profiles_spec_fileextension"""
        if  params.pnt.write_h5:
            for n, spec in enumerate(self.specnames):
                proffile = self.folder / 'profiles_{}{}'.format(spec, extension)
                prof = h5py.File(proffile, 'r')
                self.x_a = prof.get("/position/x_o_a")[()]
                self.xs = prof.get("/position/x_o_rho_ref")[()]
                self.T0s[:, n] = prof.get('/temp/T')[()]
                self.omt0s[:, n] = prof.get('/temp/omt')[()]
                self.n0s[:, n] = prof.get('/density/n')[()]
                self.omn0s[:, n] = prof.get('/density/omn')[()]
                prof.close()
        else:
            self.dens[i_spec]=params.species[i_spec]['dens']
            self.temp[i_spec]=params.species[i_spec]['temp']
            file=os.path.join(folder,'profiles_{}{}'.format(params.species[i_spec]['name'],extension))
            with open(file,'r') as pfile:
                lines = pfile.readlines()
                for i in range(2, params.pnt.nx0+2):
                    self.x_a[i-2] = float(lines[i].split()[0])
                    self.xs[i-2] = float(lines[i].split()[1])
                    self.T0[i_spec,i-2] = float(lines[i].split()[2])/params.species[i_spec]['temp']/params.pnt.Tref
                    self.n0[i_spec,i-2] = float(lines[i].split()[3])/params.species[i_spec]['dens']/params.pnt.nref
                    self.omt0[i_spec,i-2] = float(lines[i].split()[4])
                    self.omn0[i_spec,i-2] = float(lines[i].split()[5])

    def show(self, use_SI=False, spec=None, specname=None):
        def specplot(i_spec):
            fig = plt.figure(figsize=(12,4), dpi= 100, facecolor='w', edgecolor='k')
            ax = fig.add_subplot(1,4,1)
            ax.plot(self.x_a, self.T0[i_spec,:]*self.species[i_spec]['temp']*(self.Tref if use_SI else 1),
                    '-b',label=(r"T [$keV$]" if use_SI else r'$T/T_{\rm ref}$'))
            ax.legend();ax.set_title(r"${}$".format(self.species[i_spec]['name']));ax.set_xlabel(r"$x/a$");
            ax = fig.add_subplot(1,4,2)
            ax.plot(self.x_a, self.n0[i_spec,:]*self.species[i_spec]['dens']*(self.nref if use_SI else 1),
                    '-b',label=(r"n [$10^{19}/m^3$]" if use_SI else r'$n/n_{\rm ref}$'))
            ax.legend();ax.set_title(r"${}$".format(self.species[i_spec]['name']));ax.set_xlabel(r"$x/a$");            
            ax.autoscale(tight=True);
            ax = fig.add_subplot(1,4,3)
            ax.plot(self.x_a, self.omt0[i_spec,:],'-b',label=r'$\omega_{T}$')
            ax.legend();ax.set_title(r"${}$".format(self.species[i_spec]['name']));ax.set_xlabel(r"$x/a$");
            ax.autoscale(tight=True);
            ax = fig.add_subplot(1,4,4)
            ax.plot(self.x_a, self.omn0[i_spec,:],'-b',label=r'$\omega_{n}$')
            ax.legend();ax.set_title(r"${}$".format(self.species[i_spec]['name']));ax.set_xlabel(r"$x/a$");
            ax.autoscale(tight=True);            
            fig.tight_layout()

        if spec and spec<len(self.species):
            specplot(spec)
        elif specname:
            for i_spec in range(self.T0.shape[0]):
                if self.species[i_s]['name']==specname:
                    specplot(i_spec)
        else:    
            for i_spec in range(self.T0.shape[0]):
                specplot(i_spec)