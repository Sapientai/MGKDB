# -*- coding: utf-8 -*-

from tkinter import END
import matplotlib.pyplot as plt
import numpy as np
from ..putils.averages import mytrapz, xy_av3d
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagAmplitudeSpectra(Diagnostic):

    def __init__(self):
        super().__init__()
        self.name = 'Amplitude spectra'
        self.tabs = ['fluxtube']

    def get_info(self):
        self.need_file={'field': True,
                        'mom': True}

        return self.need_file
    
    def setup_options(self, run):
        self.specnames = run.parameters.pnt.specnames
        self.time = []
        self.n_fields = run.parameters.pnt.n_fields
        self.n_moms = run.parameters.pnt.n_moms
        self.n_spectra = int(run.parameters.pnt.n_fields + run.parameters.pnt.n_moms*len(self.specnames))
        self.kx=run.spatialgrid.kx_pos
        self.ky=run.spatialgrid.ky
        self.z=run.spatialgrid.z
        self.amplitude_spectra_kx=[]
        self.amplitude_spectra_ky=[]
        self.amplitude_profiles_z=[]
        self.amplitude_profiles_z_ky0=[]
        self.momlist = ["dens", "tpar", "tperp", "qpar", "qperp", "upar", 'densI1', 'TparI1', 'TppI1']
        self.field_mom_names=[]
        self.field_mom_names.append('phi')
        if self.n_fields > 1:
            self.field_mom_names.append('apar')
        if self.n_fields > 2:
            self.field_mom_names.append('bpar')
        for i in self.specnames:
            for j in range(self.n_moms):
                self.field_mom_names.append(self.momlist[j]+i)
        
        
    def execute(self, data, run, steps, extensions,time_point):
        self.time.append(time_point)
        def kx_spectra(a_field):
            #sum ky modes accounting for the complx conj.
            spectra=np.zeros((self.kx.size,a_field.shape[-1]))
            # kx=0 mode
            spectra[0,:] = 2.0*np.sum(np.abs(a_field[0,1:,:])**2,axis=0) + np.abs(a_field[0,0,:])**2
            #finite kx\
            spectra[1:,:] = np.abs(a_field[1:self.kx.size,0,:])**2 + \
                   np.sum(np.abs(a_field[1:self.kx.size,1:,:])**2 + 
                   np.abs(a_field[-1:self.kx.size-2:-1,1:,:])**2,axis=1)
            return spectra
   
        amplitude_kx=np.empty((self.n_spectra, run.spatialgrid.kx_pos.size))
        amplitude_ky=np.empty((self.n_spectra, run.spatialgrid.ky.size))
        amplitude_z=np.empty((self.n_spectra, run.spatialgrid.z.size))
        amplitude_z_ky0=np.empty((self.n_spectra, run.spatialgrid.z.size))
        tmp=data.field.phi(step=steps['field'], extension=extensions['field'])

        amplitude_ky[0,:]=np.average(np.sum(np.abs(tmp)**2,axis=0), weights=run.geometry.jacobian, axis=-1)
        amplitude_kx[0,:]=np.average(kx_spectra(tmp), weights=run.geometry.jacobian, axis=-1)
        amplitude_z[0,:] = xy_av3d(abs(tmp)**2,run.geometry) 
        amplitude_z_ky0[0,:] = np.sum(abs(tmp[:,0,:])**2,axis=0) 
        #plt.plot(self.z,amplitude_z[0,:])
        #plt.plot(self.z,amplitude_z_ky0[0,:])
        #plt.title('amplitude_z')
        #plt.show()
        
        if self.n_fields>1:
            tmp=data.field.A_par(step=steps['field'], extension=extensions['field'])
            amplitude_ky[1,:]=np.average(np.sum(np.abs(tmp)**2,axis=0), weights=run.geometry.jacobian, axis=-1)
            amplitude_kx[1,:]=np.average(kx_spectra(tmp), weights=run.geometry.jacobian, axis=-1)
            amplitude_z[1,:] = xy_av3d(abs(tmp)**2,run.geometry) 
            amplitude_z_ky0[1,:] = np.sum(abs(tmp[:,0,:])**2,axis=0) 
            
        if self.n_fields>2:
            tmp=data.field.B_par(step=steps['field'], extension=extensions['field'])
            amplitude_ky[2,:]=np.average(np.sum(np.abs(tmp)**2,axis=0), weights=run.geometry.jacobian, axis=-1)
            amplitude_kx[2,:]=np.average(kx_spectra(tmp), weights=run.geometry.jacobian, axis=-1)
            amplitude_z[2,:] = xy_av3d(abs(tmp)**2,run.geometry) 
            amplitude_z_ky0[2,:] = np.sum(abs(tmp[:,0,:])**2,axis=0) 
             
        for i_spec, spec in enumerate(run.parameters.specnames):
            for i_quant, quant in enumerate(data.mom[i_spec].varnames.values()):
                tmp = getattr(data.mom[i_spec],quant)(step=steps['mom'], extension=extensions['mom'])
                amplitude_ky[self.n_fields+len(self.specnames)*i_spec+i_quant,:]=np.average(
                        np.sum(np.abs(tmp)**2,axis=0), weights=run.geometry.jacobian, axis=-1)
                amplitude_kx[self.n_fields+len(self.specnames)*i_spec+i_quant,:]=np.average(
                        kx_spectra(tmp), weights=run.geometry.jacobian, axis=-1) 
                amplitude_z[self.n_fields+len(self.specnames)*i_spec+i_quant,:] = xy_av3d(abs(tmp)**2,run.geometry) 
                amplitude_z_ky0[self.n_fields+len(self.specnames)*i_spec+i_quant,:] = np.sum(abs(tmp[:,0,:])**2,axis=0) 
                
        self.amplitude_spectra_ky.append(amplitude_ky)
        self.amplitude_spectra_kx.append(amplitude_kx)
        self.amplitude_profiles_z.append(amplitude_z)
        self.amplitude_profiles_z_ky0.append(amplitude_z_ky0)
                
    def dict_to_mgkdb(self):
        
        amp_spect = {}
        amp_spect['Description'] = 'Spectra of the squares of all available fields and moments as a function of kx or ky (averaged over other variables).  The structure is [field_or_moment][kx or ky][time list][data on the kx or ky grid]. The time points are in [time].  The names of the fields and moments are in [field_mom_names].  The appropriate grids are in [kxgrid] and [kygrid] and  [zgrid].'
        amp_spect['time'] = self.time
        amp_spect['field_mom_names'] = self.field_mom_names
        amp_spect['kxgrid'] = self.kx
        amp_spect['kygrid'] = self.ky
        amp_spect['zgrid'] = self.z
        for i in range(len(self.field_mom_names)):
            amp_spect[self.field_mom_names[i]] = {}
            amp_spect[self.field_mom_names[i]]['kx'] = []
            amp_spect[self.field_mom_names[i]]['ky'] = []
            amp_spect[self.field_mom_names[i]]['z'] = []
            amp_spect[self.field_mom_names[i]]['z_ky0'] = []
            for j in range(len(self.amplitude_spectra_ky)):
                amp_spect[self.field_mom_names[i]]['kx'].append(self.amplitude_spectra_kx[j][i,:])
                amp_spect[self.field_mom_names[i]]['ky'].append(self.amplitude_spectra_ky[j][i,:])
                amp_spect[self.field_mom_names[i]]['z'].append(self.amplitude_profiles_z[j][i,:])
                amp_spect[self.field_mom_names[i]]['z_ky0'].append(self.amplitude_profiles_z_ky0[j][i,:])
        return amp_spect
        
    def plot(self, time_requested, output=None, out_folder=None):
        """ For each selected species we have one figure with six subplots.
            Left is vs. kx, right vs. ky; columnwise we plot, log-log, log-lin, lin-in
            Dashed lines are negative values in log-log plot
            Dashed lines are k multiplied values in log-lin plot"""

        if output:
            output.info_txt.insert(END, "Amplitude specta:\n")

        self.plotbase = Plotting()
        #this is not nice,but kind of only way of not doing it redundantly
        fld_lbl=['phi','apar','bpar']
        mom_lbl=["dens", "tpar", "tperp", "qpar", "qperp", "upar", 'densI1', 'TparI1', 'TppI1']
        
        ''' fields first'''
        fig = plt.figure(figsize=(6, 8))
        ax_loglog_kx = fig.add_subplot(3, 2, 1)
        ax_loglin_kx = fig.add_subplot(3, 2, 3)
        ax_linlin_kx = fig.add_subplot(3, 2, 5)
        ax_loglog_ky = fig.add_subplot(3, 2, 2)
        ax_loglin_ky = fig.add_subplot(3, 2, 4)
        ax_linlin_ky = fig.add_subplot(3, 2, 6)        
        for i_quant in np.arange(self.n_fields):
            if time_requested.size>1:
                ampl_ky = mytrapz(np.asarray(self.amplitude_spectra_ky)[:,i_quant,:], time_requested)
                ampl_kx = mytrapz(np.asarray(self.amplitude_spectra_kx)[:,i_quant,:], time_requested)
            else:
                ampl_ky = np.asarray(self.amplitude_spectra_ky)[0,i_quant,:]
                ampl_kx = np.asarray(self.amplitude_spectra_kx)[0,i_quant,:]
            #print('ky')
            #print(ampl_ky)
            #print('kx')
            #print(ampl_kx)           
            
            # log-log plots, dashed lines for negative values
            baselogkx, = ax_loglog_kx.plot(self.kx, ampl_kx, label=self.plotbase.titles[fld_lbl[i_quant]])
            baselogky, = ax_loglog_ky.plot(self.ky, ampl_ky, label=self.plotbase.titles[fld_lbl[i_quant]])
            # lin-log plots, nothing fancy
            baseloglinkx, = ax_loglin_kx.plot(self.kx, ampl_kx)
            baseloglinky, = ax_loglin_ky.plot(self.ky, ampl_ky)
            # lin-lin plots, nothing fancy
            ax_linlin_kx.plot(self.kx, ampl_kx);
            ax_linlin_ky.plot(self.ky, ampl_ky)

        # set things
        ax_loglog_kx.legend(); ax_loglog_ky.legend()
        ax_loglog_kx.loglog(); ax_loglog_ky.loglog()
        ax_loglin_kx.set_xscale("log"); ax_loglin_ky.set_xscale("log")
        ax_loglin_kx.set_ylim(bottom=0); ax_loglin_ky.set_ylim(bottom=0)
        ax_linlin_kx.set_xlim(left=0); ax_linlin_kx.set_ylim(bottom=0)
        ax_linlin_ky.set_xlim(left=0); ax_linlin_ky.set_ylim(bottom=0)
        ax_linlin_kx.set_xlabel(r"$k_x \rho_{ref}$")
        ax_linlin_ky.set_xlabel(r"$k_y \rho_{ref}$")
        fig.tight_layout()
        fig.show()
  
    
        for i_spec,spec in enumerate(self.specnames):
            fig = plt.figure(figsize=(6, 8))
            ax_loglog_kx = fig.add_subplot(3, 2, 1)
            ax_loglin_kx = fig.add_subplot(3, 2, 3)
            ax_linlin_kx = fig.add_subplot(3, 2, 5)
            ax_loglog_ky = fig.add_subplot(3, 2, 2)
            ax_loglin_ky = fig.add_subplot(3, 2, 4)
            ax_linlin_ky = fig.add_subplot(3, 2, 6)
            
            for i_quant in np.arange(self.n_fields,self.n_fields+self.n_moms):
                if time_requested.size>1:
                    ampl_kx = mytrapz(np.asarray(self.amplitude_spectra_kx)[:,i_quant,:], time_requested)
                    ampl_ky = mytrapz(np.asarray(self.amplitude_spectra_ky)[:,i_quant,:], time_requested)
                else:
                    ampl_kx = np.asarray(self.amplitude_spectra_kx)[0,i_quant,:]
                    ampl_ky = np.asarray(self.amplitude_spectra_ky)[0,i_quant,:]
            
                # log-log plots, dashed lines for negative values
                baselogkx, = ax_loglog_kx.plot(self.kx, ampl_kx, label=self.plotbase.titles[mom_lbl[i_quant-self.n_fields]])
                baselogky, = ax_loglog_ky.plot(self.ky, ampl_ky, label=self.plotbase.titles[mom_lbl[i_quant-self.n_fields]])
                # lin-log plots, nothing fancy
                baseloglinkx, = ax_loglin_kx.plot(self.kx, ampl_kx)
                baseloglinky, = ax_loglin_ky.plot(self.ky, ampl_ky)
                # lin-lin plots, nothing fancy
                ax_linlin_kx.plot(self.kx, ampl_kx)
                ax_linlin_ky.plot(self.ky, ampl_ky)

            # set things
            ax_loglog_kx.loglog(); ax_loglog_ky.loglog()
            ax_loglog_kx.legend(); ax_loglog_ky.legend()
            ax_loglin_kx.set_xscale("log"); ax_loglin_ky.set_xscale("log")
            ax_loglin_kx.set_ylim(bottom=0); ax_loglin_ky.set_ylim(bottom=0)
            ax_linlin_kx.set_xlim(left=0); ax_linlin_kx.set_ylim(bottom=0)
            ax_linlin_ky.set_xlim(left=0); ax_linlin_ky.set_ylim(bottom=0)
            ax_linlin_kx.set_xlabel(r"$k_x \rho_{ref}$")
            ax_linlin_ky.set_xlabel(r"$k_y \rho_{ref}$")
            ax_loglog_kx.set_title("{}".format(spec))
            fig.tight_layout()
            fig.show()
