from tkinter import END

import os
import h5py
import matplotlib.pyplot as plt
import numpy as np
import ..putils.averages as averages
import ..putils.fourier as fourier
from .baseplot import Plotting
from .diagnostic import Diagnostic

class DiagCorrelations(Diagnostic):
    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Correlations'
        self.tabs = ['fluxtube']

        self.help_txt = """Makes correlation functions in x and y.\n
                        Saves z=-pi,+-pi/2, 0, and weighted average over those points.\n
                        \nSave pdf : save pdf file (def. False)
                        """

        self.avail_vars = avail_vars

        self.specnames = specnames

        self.opts = {"spec": {'tag': "Spec", 'values': self.list_specnames()}}

        self.set_defaults()
        self.save_meta_file = True
        self.save_meta_fname = 'correlations.h5'

        self.options_gui = Diagnostic.OptionsGUI()
        self.times = np.empty(0)

    def set_options(self, run, specnames, out_folder):
        self.has_EM = any(x.pnt.electromagnetic for x in run.parameters)
        self.get_needed_vars(['field', 'mom'])
        
        ##This is called in loader
        self.get_spec_from_opts()
        self.taux = np.empty((int(run.parameters[0].pardict['nx0'])))
        self.tauy = np.empty((int(2.0*run.parameters[0].pardict['nky0'])))
        
        if self.save_meta_file:
            self.setup_save_meta_h5(out_folder, run)
        self.corr_funcs = {}
        self.corr_lengths_x = {}
        self.corr_lengths_y = {}
        self.corr_funcs['phi']=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
        self.corr_lengths_x['phi']=np.empty(5)
        self.corr_lengths_y['phi']=np.empty(5)
        if self.has_EM: 
            self.corr_funcs['A_par']=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
            self.corr_lengths_x['A_par']=np.empty(5)
            self.corr_lengths_y['A_par']=np.empty(5)
        for spec in run.specnames:
            self.corr_funcs['dens_'+spec]=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
            self.corr_lengths_x['dens_'+spec]=np.empty(5)
            self.corr_lengths_y['dens_'+spec]=np.empty(5)
            self.corr_funcs['u_par_'+spec]=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
            self.corr_lengths_x['u_par_'+spec]=np.empty(5)
            self.corr_lengths_y['u_par_'+spec]=np.empty(5)
            self.corr_funcs['T_par_'+spec]=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
            self.corr_lengths_x['T_par_'+spec]=np.empty(5)
            self.corr_lengths_y['T_par_'+spec]=np.empty(5)
            self.corr_funcs['T_perp_'+spec]=np.zeros((run.parameters[0].pardict['nx0'],2*run.parameters[0].pardict['nky0'],5))
            self.corr_lengths_x['T_perp_'+spec]=np.empty(5)
            self.corr_lengths_y['T_perp_'+spec]=np.empty(5)
        return self.needed_vars

    def execute(self, data, parameters, geometry, spatialgrid,  step):

        self.times =  np.append(self.times,step.time)
        xgrid,ygrid = fourier.xy_grids(data.field.phi(step.time,step.field,parameters),parameters)
        phi_xyz = fourier.fouriertransform_k2x_2D(data.field.phi(step.time,step.field,parameters),parameters)
        if self.has_EM:
            apar_xyz = fourier.fouriertransform_k2x_2D(data.field.A_par(step.time,step.field,parameters),parameters)
        dens_xyz = {}
        T_par_xyz = {}
        T_perp_xyz = {}
        u_par_xyz = {}
        for spec in self.specnames:
            dens = getattr(getattr(data, 'mom_' + spec), "dens")(step.time, step.mom, parameters)
            dens_xyz[spec] = fourier.fouriertransform_k2x_2D(dens,parameters)
            T_par = getattr(getattr(data, 'mom_' + spec), "T_par")(step.time, step.mom, parameters)
            T_par_xyz[spec] = fourier.fouriertransform_k2x_2D(T_par,parameters)
            T_perp = getattr(getattr(data, 'mom_' + spec), "T_perp")(step.time, step.mom, parameters)
            T_perp_xyz[spec] = fourier.fouriertransform_k2x_2D(T_perp,parameters)
            u_par = getattr(getattr(data, 'mom_' + spec), "u_par")(step.time, step.mom, parameters)
            u_par_xyz[spec] = fourier.fouriertransform_k2x_2D(u_par,parameters)
        #plt.contourf(ygrid,xgrid,abs(phi_xyz[:,:,int(parameters.pardict['nz0']/2.0)])) 
        #plt.show()
        #sample at z = -pi, -pi/2, 0, pi/2 correcting for edge_opt

        zindices = np.empty(4,dtype = 'int')
        zindices[0] = 0
        zindices[1] = translate_edge_opt(-np.pi/2.0,parameters.pardict['nz0'],parameters.pardict['edge_opt'])
        zindices[2] = translate_edge_opt(0.0,parameters.pardict['nz0'],parameters.pardict['edge_opt'])
        zindices[3] = translate_edge_opt(np.pi/2.0,parameters.pardict['nz0'],parameters.pardict['edge_opt'])

        for k in range(len(zindices)):
            print("k",k)
            self.taux,self.tauy,temp = corr_func_2D(phi_xyz[:,:,zindices[k]],phi_xyz[:,:,zindices[k]],xgrid,ygrid)
            self.corr_funcs['phi'][:,:,k] += temp
            self.corr_funcs['phi'][:,:,4] += np.sum(np.sum(abs(phi_xyz[:,:,zindices[k]]**2),axis=0),axis=0)*temp
            if self.has_EM:
                self.taux,self.tauy,self.corr_funcs['A_par'][:,:,k] = corr_func_2D(apar_xyz[:,:,zindices[k]],apar_xyz[:,:,zindices[k]],xgrid,ygrid)
                self.corr_funcs['A_par'][:,:,k] += temp
                self.corr_funcs['A_par'][:,:,4] += np.sum(np.sum(abs(apar_xyz[:,:,zindices[k]]**2),axis=0),axis=0)*temp

            specnum = 0
            for spec in self.specnames:

                self.taux,self.tauy,temp = corr_func_2D(dens_xyz[spec][:,:,zindices[k]],dens_xyz[spec][:,:,zindices[k]],xgrid,ygrid)
                self.corr_funcs['dens_'+spec][:,:,k] += temp
                self.corr_funcs['dens_'+spec][:,:,4] += np.sum(np.sum(abs(dens_xyz[spec][:,:,zindices[k]]**2),axis=0),axis=0)*temp

                self.taux,self.tauy,temp = corr_func_2D(T_par_xyz[spec][:,:,zindices[k]],T_par_xyz[spec][:,:,zindices[k]],xgrid,ygrid)
                self.corr_funcs['T_par_'+spec][:,:,k] += temp
                self.corr_funcs['T_par_'+spec][:,:,4] += np.sum(np.sum(abs(T_par_xyz[spec][:,:,zindices[k]]**2),axis=0),axis=0)*temp

                self.taux,self.tauy,temp = corr_func_2D(T_perp_xyz[spec][:,:,zindices[k]],T_perp_xyz[spec][:,:,zindices[k]],xgrid,ygrid)
                self.corr_funcs['T_perp_'+spec][:,:,k] += temp
                self.corr_funcs['T_perp_'+spec][:,:,4] += np.sum(np.sum(abs(T_perp_xyz[spec][:,:,zindices[k]]**2),axis=0),axis=0)*temp

                self.taux,self.tauy,temp = corr_func_2D(u_par_xyz[spec][:,:,zindices[k]],u_par_xyz[spec][:,:,zindices[k]],xgrid,ygrid)
                self.corr_funcs['u_par_'+spec][:,:,k] += temp
                self.corr_funcs['u_par_'+spec][:,:,4] += np.sum(np.sum(abs(u_par_xyz[spec][:,:,zindices[k]]**2),axis=0),axis=0)*temp
            specnum += 1
           
        #if self.save_meta_file:
        #    self.save_meta_h5(step.time)
    def calc_corr_length(self,tau,cfunc):
        max_corr = max(np.abs(cfunc))
        corr_len = 0.0
        i = 0
        while corr_len==0.0:
            if (abs(cfunc[i])-max_corr/np.e) > 0.0 and \
               (abs(cfunc[i+1])-max_corr/np.e) <= 0.0:
                slope=(cfunc[i+1]-cfunc[i])/(tau[i+1]-tau[i])
                zero=cfunc[i]-slope*tau[i]
                corr_len=(max_corr/np.e-zero)/slope
            i+=1
        return corr_len

    def finalize(self):

        for k in range(5):
            self.corr_lengths_x['phi'][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['phi'][:,:,k],axis=1))
            self.corr_lengths_y['phi'][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['phi'][:,:,k],axis=0))
            if self.has_EM:
                self.corr_lengths_x['A_par'][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['A_par'][:,:,k],axis=1))
                self.corr_lengths_y['A_par'][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,k],axis=0))
            for spec in self.specnames:
                self.corr_lengths_x['dens_'+spec][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,k],axis=1))
                self.corr_lengths_y['dens_'+spec][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,k],axis=0))
                self.corr_lengths_x['T_par_'+spec][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,k],axis=1))
                self.corr_lengths_y['T_par_'+spec][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,k],axis=0))
                self.corr_lengths_x['u_par_'+spec][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,k],axis=1))
                self.corr_lengths_y['u_par_'+spec][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,k],axis=0))
                self.corr_lengths_x['T_perp_'+spec][k] = self.calc_corr_length(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,k],axis=1))
                self.corr_lengths_y['T_perp_'+spec][k] = self.calc_corr_length(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,k],axis=0))
        if self.save_meta_file:
            self.save_meta_h5()
                
    def setup_save_meta_h5(self, folder, run):
        if not os.path.isdir(folder):
            raise Exception(os.path.abspath(folder) + " does not exist or is undefined")

        nx = int(run.parameters[0].pardict['nx0'])
        ny = int(run.parameters[0].pardict['nky0']*2)
        self.h5_meta = os.path.join(folder, self.save_meta_fname)
        ##self.nkx_2 = len(run.spatialgrid[0].kx_pos)
        ##self.nky = len(run.spatialgrid[0].ky)
        if os.path.isfile(self.h5_meta):
            os.remove(self.h5_meta)
        if os.path.isfile(self.h5_meta):    
            # file exist, simply open it
            self.h5_meta = h5py.File(self.h5_meta, 'a')
        else:
            # file does not exit 
            self.h5_meta = h5py.File(self.h5_meta, 'w')

    def save_meta_h5(self ):
        #self.meta_file_pos += 1
        self.h5_meta.create_dataset('deltax',data = self.taux)
        self.h5_meta.create_dataset('deltay',data = self.tauy)
        self.h5_meta.create_dataset('times',data = self.times)
        self.h5_meta.create_dataset('Corr func phi',data = self.corr_funcs['phi'])
        self.h5_meta.create_dataset('lambda_x phi',data = self.corr_lengths_x['phi'])
        self.h5_meta.create_dataset('lambda_y phi',data = self.corr_lengths_y['phi'])
        if self.has_EM:
            self.h5_meta.create_dataset('Corr func A_par',data = self.corr_funcs['A_par'])
            self.h5_meta.create_dataset('lambda_x A_par',data = self.corr_lengths_x['A_par'])
            self.h5_meta.create_dataset('lambda_y A_par',data = self.corr_lengths_y['A_par'])
        for spec in self.specnames:
            self.h5_meta.create_dataset('Corr func dens_'+spec,data = self.corr_funcs['dens_'+spec])
            self.h5_meta.create_dataset('lambda_x dens_'+spec,data = self.corr_lengths_x['dens_'+spec])
            self.h5_meta.create_dataset('lambda_y dens_'+spec,data = self.corr_lengths_y['dens_'+spec])
            self.h5_meta.create_dataset('Corr func T_par_'+spec,data = self.corr_funcs['T_par_'+spec])
            self.h5_meta.create_dataset('lambda_x T_par_'+spec,data = self.corr_lengths_x['T_par_'+spec])
            self.h5_meta.create_dataset('lambda_y T_par_'+spec,data = self.corr_lengths_y['T_par_'+spec])
            self.h5_meta.create_dataset('Corr func T_perp_'+spec,data = self.corr_funcs['T_perp_'+spec])
            self.h5_meta.create_dataset('lambda_x T_perp_'+spec,data = self.corr_lengths_x['T_perp_'+spec])
            self.h5_meta.create_dataset('lambda_y T_perp_'+spec,data = self.corr_lengths_y['T_perp_'+spec])
            self.h5_meta.create_dataset('Corr func u_par_'+spec,data = self.corr_funcs['u_par_'+spec])
            self.h5_meta.create_dataset('lambda_x u_par_'+spec,data = self.corr_lengths_x['u_par_'+spec])
            self.h5_meta.create_dataset('lambda_y u_par_'+spec,data = self.corr_lengths_y['u_par_'+spec])
                #self.h5_meta['/time'].resize((self.meta_file_pos), axis=0)
        #self.h5_meta['/time'][-1] = time
        self.h5_meta.flush()
        
    def close_meta_h5(self):
        self.h5_meta.close()

    def load_meta_h5(self, out_folder):
        self.h5_meta = os.path.join(out_folder, self.save_meta_fname)
        self.h5_meta = h5py.File(self.h5_meta, 'a')
        list(self.h5_meta.keys())
        
        self.corr_lengths_x['phi']=self.h5_meta['lambda_x phi'][:]
        self.corr_lengths_y['phi']=self.h5_meta['lambda_y phi'][:]
        self.corr_funcs['phi']=self.h5_meta['Corr func phi'][:,:,:]
        if self.has_EM:
            self.corr_lengths_x['A_par']=self.h5_meta['lambda_x A_par'][:]
            self.corr_lengths_y['A_par']=self.h5_meta['lambda_y A_par'][:]
            self.corr_funcs['A_par']=self.h5_meta['Corr func A_par'][:,:,:]
        for spec in self.specnames:
            self.corr_lengths_x['dens_'+spec]=self.h5_meta['lambda_x dens_'+spec][:]
            self.corr_lengths_y['dens_'+spec]=self.h5_meta['lambda_y dens_'+spec][:]
            self.corr_funcs['dens_'+spec]=self.h5_meta['Corr func dens_'+spec][:,:,:]
            self.corr_lengths_x['u_par_'+spec]=self.h5_meta['lambda_x u_par_'+spec][:]
            self.corr_lengths_y['u_par_'+spec]=self.h5_meta['lambda_y u_par_'+spec][:]
            self.corr_funcs['u_par_'+spec]=self.h5_meta['Corr func u_par_'+spec][:,:,:]
            self.corr_lengths_x['T_perp_'+spec]=self.h5_meta['lambda_x T_perp_'+spec][:]
            self.corr_lengths_y['T_perp_'+spec]=self.h5_meta['lambda_y T_perp_'+spec][:]
            self.corr_funcs['T_perp_'+spec]=self.h5_meta['Corr func T_perp_'+spec][:,:,:]
            self.corr_lengths_x['T_par_'+spec]=self.h5_meta['lambda_x T_par_'+spec][:]
            self.corr_lengths_y['T_par_'+spec]=self.h5_meta['lambda_y T_par_'+spec][:]
            self.corr_funcs['T_par_'+spec]=self.h5_meta['Corr func T_par_'+spec][:,:,:]
        self.h5_meta.close()
        
    def plot(self, time_requested, output=None, out_folder=None, terminal=None):
        """ 
            Plot."""

        self.load_meta_h5(out_folder)
        #plt.figure(figsize = (18,9))
        plt.figure(figsize = (18,8))
        zind = 0
        plt.subplot(3,5,1)
        plt.title(r'$|\phi|^2(\Delta x, \Delta y)(z=-\pi)$')
        plt.contourf(self.tauy,self.taux,self.corr_funcs['phi'][:,:,zind])
        plt.colorbar()
        plt.ylabel(r'$\Delta x(\rho_s)$')
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.subplot(3,5,6)
        plt.plot(self.taux,np.sum(self.corr_funcs['phi'][:,:,zind],axis=1))
        plt.axvline(self.corr_lengths_x['phi'][zind],color = 'black',label=str(self.corr_lengths_x['phi'][zind])[:6])
        plt.xlabel(r'$\Delta x(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta x)(z=-\pi)$')
        plt.legend()
        plt.subplot(3,5,11)
        plt.plot(self.tauy,np.sum(self.corr_funcs['phi'][:,:,zind],axis=0))
        plt.axvline(self.corr_lengths_y['phi'][zind],color = 'black',label=str(self.corr_lengths_y['phi'][zind])[:6])
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta y)(z=-\pi)$')
        plt.legend()

        zind = 1
        plt.subplot(3,5,2)
        plt.title(r'$|\phi|^2(\Delta x, \Delta y)(z=-\pi/2)$')
        plt.contourf(self.tauy,self.taux,self.corr_funcs['phi'][:,:,zind])
        plt.colorbar()
        plt.ylabel(r'$\Delta x(\rho_s)$')
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.subplot(3,5,7)
        plt.plot(self.taux,np.sum(self.corr_funcs['phi'][:,:,zind],axis=1))
        plt.axvline(self.corr_lengths_x['phi'][zind],color = 'black',label=str(self.corr_lengths_x['phi'][zind])[:6])
        plt.xlabel(r'$\Delta x(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta x)(z=-\pi/2)$')
        plt.legend()
        plt.subplot(3,5,12)
        plt.plot(self.tauy,np.sum(self.corr_funcs['phi'][:,:,zind],axis=0))
        plt.axvline(self.corr_lengths_y['phi'][zind],color = 'black',label=str(self.corr_lengths_y['phi'][zind])[:6])
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta y)(z=-\pi/2)$')
        plt.legend()

        zind = 2
        plt.subplot(3,5,3)
        plt.title(r'$|\phi|^2(\Delta x, \Delta y)(z=0)$')
        plt.contourf(self.tauy,self.taux,self.corr_funcs['phi'][:,:,zind])
        plt.colorbar()
        plt.ylabel(r'$\Delta x(\rho_s)$')
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.subplot(3,5,8)
        plt.plot(self.taux,np.sum(self.corr_funcs['phi'][:,:,zind],axis=1))
        plt.axvline(self.corr_lengths_x['phi'][zind],color = 'black',label=str(self.corr_lengths_x['phi'][zind])[:6])
        plt.xlabel(r'$\Delta x(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta x)(z=0)$')
        plt.legend()
        plt.subplot(3,5,13)
        plt.plot(self.tauy,np.sum(self.corr_funcs['phi'][:,:,zind],axis=0))
        plt.axvline(self.corr_lengths_y['phi'][zind],color = 'black',label=str(self.corr_lengths_y['phi'][zind])[:6])
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta y)(z=0)$')
        plt.legend()

        zind = 3
        plt.subplot(3,5,4)
        plt.title(r'$|\phi|^2(\Delta x, \Delta y)(z=\pi/2)$')
        plt.contourf(self.tauy,self.taux,self.corr_funcs['phi'][:,:,zind])
        plt.colorbar()
        plt.ylabel(r'$\Delta x(\rho_s)$')
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.subplot(3,5,9)
        plt.plot(self.taux,np.sum(self.corr_funcs['phi'][:,:,zind],axis=1))
        plt.axvline(self.corr_lengths_x['phi'][zind],color = 'black',label=str(self.corr_lengths_x['phi'][zind])[:6])
        plt.xlabel(r'$\Delta x(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta x)(z=\pi/2)$')
        plt.legend()
        plt.subplot(3,5,14)
        plt.plot(self.tauy,np.sum(self.corr_funcs['phi'][:,:,zind],axis=0))
        plt.axvline(self.corr_lengths_y['phi'][zind],color = 'black',label=str(self.corr_lengths_y['phi'][zind])[:6])
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta y)(z=\pi/2)$')
        plt.legend()

        zind = 4
        plt.subplot(3,5,5)
        plt.title(r'$|\phi|^2(\Delta x, \Delta y)(z=avg)$')
        plt.contourf(self.tauy,self.taux,self.corr_funcs['phi'][:,:,zind])
        plt.colorbar()
        plt.ylabel(r'$\Delta x(\rho_s)$')
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.subplot(3,5,10)
        plt.plot(self.taux,np.sum(self.corr_funcs['phi'][:,:,zind],axis=1))
        plt.axvline(self.corr_lengths_x['phi'][zind],color = 'black',label=str(self.corr_lengths_x['phi'][zind])[:6])
        plt.xlabel(r'$\Delta x(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta x)(z=avg)$')
        plt.legend()
        plt.subplot(3,5,15)
        plt.plot(self.tauy,np.sum(self.corr_funcs['phi'][:,:,zind],axis=0))
        plt.axvline(self.corr_lengths_y['phi'][zind],color = 'black',label=str(self.corr_lengths_y['phi'][zind])[:6])
        plt.xlabel(r'$\Delta y(\rho_s)$')
        plt.ylabel(r'$|\phi|^2(\Delta y)(z=avg)$')
        plt.legend()
        plt.tight_layout()
        plt.show()

        if self.has_EM:
            plt.figure(figsize = (18,8))
            zind = 0
            plt.subplot(3,5,1)
            plt.title(r'$|A_{||}|^2(\Delta x, \Delta y)(z=-\pi)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['A_par'][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,6)
            plt.plot(self.taux,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['A_par'][zind],color = 'black',label=str(self.corr_lengths_x['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(r'$|A_{||}^2(\Delta x)(z=-\pi)$')
            plt.legend()
            plt.subplot(3,5,11)
            plt.plot(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['A_par'][zind],color = 'black',label=str(self.corr_lengths_y['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta y)(z=-\pi)$')
            plt.legend()
    
            zind = 1
            plt.subplot(3,5,2)
            plt.title(r'$|A_{||}|^2(\Delta x, \Delta y)(z=-\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['A_par'][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,7)
            plt.plot(self.taux,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['A_par'][zind],color = 'black',label=str(self.corr_lengths_x['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta x)(z=-\pi/2)$')
            plt.legend()
            plt.subplot(3,5,12)
            plt.plot(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['A_par'][zind],color = 'black',label=str(self.corr_lengths_y['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta y)(z=-\pi/2)$')
            plt.legend()
    
            zind = 2
            plt.subplot(3,5,3)
            plt.title(r'$|A_{||}|^2(\Delta x, \Delta y)(z=0)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['A_par'][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,8)
            plt.plot(self.taux,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['A_par'][zind],color = 'black',label=str(self.corr_lengths_x['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta x)(z=0)$')
            plt.legend()
            plt.subplot(3,5,13)
            plt.plot(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['A_par'][zind],color = 'black',label=str(self.corr_lengths_y['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta y)(z=0)$')
            plt.legend()
    
            zind = 3
            plt.subplot(3,5,4)
            plt.title(r'$|A_{||}|^2(\Delta x, \Delta y)(z=\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['A_par'][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,9)
            plt.plot(self.taux,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['A_par'][zind],color = 'black',label=str(self.corr_lengths_x['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta x)(z=\pi/2)$')
            plt.legend()
            plt.subplot(3,5,14)
            plt.plot(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['A_par'][zind],color = 'black',label=str(self.corr_lengths_y['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta y)(z=\pi/2)$')
            plt.legend()
    
            zind = 4
            plt.subplot(3,5,5)
            plt.title(r'$|A_{||}|^2(\Delta x, \Delta y)(z=avg)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['A_par'][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,10)
            plt.plot(self.taux,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['A_par'][zind],color = 'black',label=str(self.corr_lengths_x['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta x)(z=avg)$')
            plt.legend()
            plt.subplot(3,5,15)
            plt.plot(self.tauy,np.sum(self.corr_funcs['A_par'][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['A_par'][zind],color = 'black',label=str(self.corr_lengths_y['A_par'][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(r'$|A_{||}|^2(\Delta y)(z=avg)$')
            plt.legend()
            plt.tight_layout()
            plt.show()
            
        for spec in self.specnames:
            #density
            plt.figure(figsize = (18,8))
            zind = 0
            plt.subplot(3,5,1)
            plt.title(spec+' '+r'$|n|^2(\Delta x, \Delta y)(z=-\pi)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['dens_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,6)
            plt.plot(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n^2(\Delta x)(z=-\pi)$')
            plt.legend()
            plt.subplot(3,5,11)
            plt.plot(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta y)(z=-\pi)$')
            plt.legend()
    
            zind = 1
            plt.subplot(3,5,2)
            plt.title(spec+' '+r'$|n|^2(\Delta x, \Delta y)(z=-\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['dens_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,7)
            plt.plot(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta x)(z=-\pi/2)$')
            plt.legend()
            plt.subplot(3,5,12)
            plt.plot(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta y)(z=-\pi/2)$')
            plt.legend()
    
            zind = 2
            plt.subplot(3,5,3)
            plt.title(spec+' '+r'$|n|^2(\Delta x, \Delta y)(z=0)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['dens_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,8)
            plt.plot(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta x)(z=0)$')
            plt.legend()
            plt.subplot(3,5,13)
            plt.plot(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta y)(z=0)$')
            plt.legend()
    
            zind = 3
            plt.subplot(3,5,4)
            plt.title(spec+' '+r'$|n|^2(\Delta x, \Delta y)(z=\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['dens_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,9)
            plt.plot(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta x)(z=\pi/2)$')
            plt.legend()
            plt.subplot(3,5,14)
            plt.plot(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta y)(z=\pi/2)$')
            plt.legend()
    
            zind = 4
            plt.subplot(3,5,5)
            plt.title(spec+' '+r'$|n|^2(\Delta x, \Delta y)(avg)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['dens_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,10)
            plt.plot(self.taux,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta x)(z=avg)$')
            plt.legend()
            plt.subplot(3,5,15)
            plt.plot(self.tauy,np.sum(self.corr_funcs['dens_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['dens_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['dens_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|n|^2(\Delta y)(z=avg)$')
            plt.legend()
            plt.tight_layout()
            plt.show()

            #T_par
            plt.figure(figsize = (18,8))
            zind = 0
            plt.subplot(3,5,1)
            plt.title(spec+' '+r'$|T_{||}|^2(\Delta x, \Delta y)(z=-\pi)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,6)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}^2(\Delta x)(z=-\pi)$')
            plt.legend()
            plt.subplot(3,5,11)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta y)(z=-\pi)$')
            plt.legend()
    
            zind = 1
            plt.subplot(3,5,2)
            plt.title(spec+' '+r'$|T_{||}|^2(\Delta x, \Delta y)(z=-\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,7)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta x)(z=-\pi/2)$')
            plt.legend()
            plt.subplot(3,5,12)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta y)(z=-\pi/2)$')
            plt.legend()
    
            zind = 2
            plt.subplot(3,5,3)
            plt.title(spec+' '+r'$|T_{||}|^2(\Delta x, \Delta y)(z=0)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,8)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta x)(z=0)$')
            plt.legend()
            plt.subplot(3,5,13)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta y)(z=0)$')
            plt.legend()
    
            zind = 3
            plt.subplot(3,5,4)
            plt.title(spec+' '+r'$|T_{||}|^2(\Delta x, \Delta y)(z=\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,9)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta x)(z=\pi/2)$')
            plt.legend()
            plt.subplot(3,5,14)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta y)(z=\pi/2)$')
            plt.legend()
    
            zind = 4
            plt.subplot(3,5,5)
            plt.title(spec+' '+r'$|T_{||}|^2(\Delta x, \Delta y)(avg)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,10)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta x)(z=avg)$')
            plt.legend()
            plt.subplot(3,5,15)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{||}|^2(\Delta y)(z=avg)$')
            plt.legend()
            plt.tight_layout()
            plt.show()

            #T_perp
            plt.figure(figsize = (18,8))
            zind = 0
            plt.subplot(3,5,1)
            plt.title(spec+' '+r'$|T_{\perp}|^2(\Delta x, \Delta y)(z=-\pi)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_perp_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,6)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{\perp}^2(\Delta x)(z=-\pi)$')
            plt.legend()
            plt.subplot(3,5,11)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta y)(z=-\pi)$')
            plt.legend()
    
            zind = 1
            plt.subplot(3,5,2)
            plt.title(spec+' '+r'$|T_{\perp}|^2(\Delta x, \Delta y)(z=-\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_perp_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,7)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta x)(z=-\pi/2)$')
            plt.legend()
            plt.subplot(3,5,12)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta y)(z=-\pi/2)$')
            plt.legend()
    
            zind = 2
            plt.subplot(3,5,3)
            plt.title(spec+' '+r'$|T_{\perp}|^2(\Delta x, \Delta y)(z=0)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_perp_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,8)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta x)(z=0)$')
            plt.legend()
            plt.subplot(3,5,13)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta y)(z=0)$')
            plt.legend()
    
            zind = 3
            plt.subplot(3,5,4)
            plt.title(spec+' '+r'$|T_{\perp}|^2(\Delta x, \Delta y)(z=\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_perp_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,9)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta x)(z=\pi/2)$')
            plt.legend()
            plt.subplot(3,5,14)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta y)(z=\pi/2)$')
            plt.legend()
    
            zind = 4
            plt.subplot(3,5,5)
            plt.title(spec+' '+r'$|T_{\perp}|^2(\Delta x, \Delta y)(avg)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['T_perp_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,10)
            plt.plot(self.taux,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta x)(z=avg)$')
            plt.legend()
            plt.subplot(3,5,15)
            plt.plot(self.tauy,np.sum(self.corr_funcs['T_perp_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['T_perp_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['T_perp_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|T_{/perp}|^2(\Delta y)(z=avg)$')
            plt.legend()
            plt.tight_layout()
            plt.show()

            #u_par
            plt.figure(figsize = (18,8))
            zind = 0
            plt.subplot(3,5,1)
            plt.title(spec+' '+r'$|u_{||}|^2(\Delta x, \Delta y)(z=-\pi)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['u_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,6)
            plt.plot(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}^2(\Delta x)(z=-\pi)$')
            plt.legend()
            plt.subplot(3,5,11)
            plt.plot(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta y)(z=-\pi)$')
            plt.legend()
    
            zind = 1
            plt.subplot(3,5,2)
            plt.title(spec+' '+r'$|u_{||}|^2(\Delta x, \Delta y)(z=-\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['u_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,7)
            plt.plot(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta x)(z=-\pi/2)$')
            plt.legend()
            plt.subplot(3,5,12)
            plt.plot(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta y)(z=-\pi/2)$')
            plt.legend()
    
            zind = 2
            plt.subplot(3,5,3)
            plt.title(spec+' '+r'$|u_{||}|^2(\Delta x, \Delta y)(z=0)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['u_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,8)
            plt.plot(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta x)(z=0)$')
            plt.legend()
            plt.subplot(3,5,13)
            plt.plot(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta y)(z=0)$')
            plt.legend()
    
            zind = 3
            plt.subplot(3,5,4)
            plt.title(spec+' '+r'$|u_{||}|^2(\Delta x, \Delta y)(z=\pi/2)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['u_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,9)
            plt.plot(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta x)(z=\pi/2)$')
            plt.legend()
            plt.subplot(3,5,14)
            plt.plot(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta y)(z=\pi/2)$')
            plt.legend()
    
            zind = 4
            plt.subplot(3,5,5)
            plt.title(spec+' '+r'$|u_{||}|^2(\Delta x, \Delta y)(avg)$')
            plt.contourf(self.tauy,self.taux,self.corr_funcs['u_par_'+spec][:,:,zind])
            plt.colorbar()
            plt.ylabel(r'$\Delta x(\rho_s)$')
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.subplot(3,5,10)
            plt.plot(self.taux,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=1))
            plt.axvline(self.corr_lengths_x['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_x['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta x(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta x)(z=avg)$')
            plt.legend()
            plt.subplot(3,5,15)
            plt.plot(self.tauy,np.sum(self.corr_funcs['u_par_'+spec][:,:,zind],axis=0))
            plt.axvline(self.corr_lengths_y['u_par_'+spec][zind],color = 'black',label=str(self.corr_lengths_y['u_par_'+spec][zind])[:6])
            plt.xlabel(r'$\Delta y(\rho_s)$')
            plt.ylabel(spec+' '+r'$|u_{||}|^2(\Delta y)(z=avg)$')
            plt.legend()
            plt.tight_layout()
            plt.show()


        
    def save(time_requested, output=None, out_folder=None):
        pass

def corr_func_2D(v1,v2,xgrid,ygrid,show_plot=False):
        dx=xgrid[1]-xgrid[0]
        dy=ygrid[1]-ygrid[0]
        Nx=len(xgrid)
        Ny=len(ygrid)
        cfunc=np.zeros((Nx,Ny))
        for i in range(Nx):
            for j in range(Ny):
                i0=i+1
                j0=j+1
                cfunc[-i0,-j0]=np.sum( np.sum( np.conj(v1[-i0:,-j0:])*v2[:i0,:j0],axis = 0),axis=0)
        cfunc = cfunc / np.sum(np.sum(np.conj(v1[:,:])*v2[:,:],axis = 0),axis=0)
        cfuncx = np.sum(cfunc,axis=1)
        cfuncy = np.sum(cfunc,axis=0)
        taux=np.arange(Nx)
        taux=taux*dx
        tauy=np.arange(Ny)
        tauy=tauy*dy
        corr_time_x = 0.0
        max_corr_x=max(np.abs(cfuncx))
        max_corr_y=max(np.abs(cfuncy))
        corr_time_y = 0.0
        i=0
        while corr_time_x==0.0:
            if (abs(cfuncx[i])-max_corr_x/np.e) > 0.0 and \
               (abs(cfuncx[i+1])-max_corr_x/np.e) <= 0.0:
                slope=(cfuncx[i+1]-cfuncx[i])/(taux[i+1]-taux[i])
                zero=cfuncx[i]-slope*taux[i]
                corr_time_x=(max_corr_x/np.e-zero)/slope
            i+=1
        i=0
        while corr_time_y==0.0:
            if (abs(cfuncy[i])-max_corr_y/np.e) > 0.0 and \
               (abs(cfuncy[i+1])-max_corr_y/np.e) <= 0.0:
                slope=(cfuncy[i+1]-cfuncy[i])/(tauy[i+1]-tauy[i])
                zero=cfuncy[i]-slope*tauy[i]
                corr_time_y=(max_corr_y/np.e-zero)/slope
            i+=1
        if show_plot:
            plt.title('taux: '+str(corr_time_x)[:6]+' tauy: '+str(corr_time_y)[:6])
            plt.contourf(tauy,taux,cfunc)
            plt.colorbar()
            plt.show()
            plt.plot(taux,cfuncx,'x-')
            ax=plt.axis()
            plt.vlines(corr_time_x,ax[2],ax[3])
            plt.show()
            plt.plot(tauy,cfuncy,'x-')
            ax=plt.axis()
            plt.vlines(corr_time_y,ax[2],ax[3])
            plt.show()

        return taux,tauy,cfunc


def corr_func_1D(v1,v2,grid,show_plot=True):
        dt=grid[1]-grid[0]
        N=len(grid)
        cfunc=np.zeros(N,dtype='complex')
        for i in range(N):
            i0=i+1
            cfunc[-i0]=np.sum(np.conj(v1[-i0:])*v2[:i0])
        tau=np.arange(N)
        tau=tau*dt
        max_corr=max(np.abs(cfunc))
        corr_time=0.0
        i=0
        while corr_time==0.0:
            if (abs(cfunc[i])-max_corr/np.e) > 0.0 and \
               (abs(cfunc[i+1])-max_corr/np.e) <= 0.0:
                slope=(cfunc[i+1]-cfunc[i])/(tau[i+1]-tau[i])
                zero=cfunc[i]-slope*tau[i]
                corr_time=(max_corr/np.e-zero)/slope
            i+=1
        if show_plot:
            plt.plot(tau,cfunc,'x-')
            ax=plt.axis()
            plt.vlines(corr_time,ax[2],ax[3])
            plt.show()
        return cfunc,tau,corr_time

def corr_func_1D_full_domain(v1,v2,grid,show_plot=True):
        dt=grid[1]-grid[0]
        N=len(grid)
        print("N",N)
        cfunc=np.zeros(2*N-1)
        cfunc[N-1]=np.sum(np.conj(v1[:])*v2[:])
        for i in range(N-1):
            i0=i+1
            cfunc[-i0]=np.sum(np.conj(v1[-i0:])*v2[:i0])
            cfunc[N-1-i0]=np.sum(np.conj(v1[:-i0])*v2[i0:])
        tau=np.arange(2*N-1)
        tau=tau*dt
        tau = tau-tau[-1]/2.0
        max_corr=max(np.abs(cfunc))
        corr_time=0.0
        i=0
        while corr_time==0.0:
            if (abs(cfunc[i])-max_corr/np.e) > 0.0 and \
               (abs(cfunc[i+1])-max_corr/np.e) <= 0.0:
                slope=(cfunc[i+1]-cfunc[i])/(tau[i+1]-tau[i])
                zero=cfunc[i]-slope*tau[i]
                corr_time=(max_corr/np.e-zero)/slope
            i+=1
        if show_plot:
            plt.plot(tau,cfunc,'x-')
            ax=plt.axis()
            plt.vlines(corr_time,ax[2],ax[3])
            plt.show()
        print("corr_time",corr_time)
        return cfunc,tau,corr_time

def translate_edge_opt(zval,nz,edge_opt):
    """Given a value of z (e.g. pi/2), this routine returns the nearest z index for an edge_opt-ed zgrid given nz0 and edge_opt."""
    dz = 2.0*np.pi/nz
    zprime_even = np.arange(nz)/float(nz-1)*(2.0*np.pi-dz)-np.pi
    N = np.arcsinh(edge_opt*zprime_even[-1])/zprime_even[-1]
    if edge_opt == 0.0:
        zind = np.argmin(abs(zprime_even-zval))
    else:
        zgrid = 1/edge_opt*np.sinh(N*zprime_even)
        zind = np.argmin(abs(zgrid-zval))
    return zind
