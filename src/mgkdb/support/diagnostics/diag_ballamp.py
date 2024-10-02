# -*- coding: utf-8 -*-

import warnings
from tkinter import END

import matplotlib.pyplot as plt
import numpy as np

import ..putils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic
from ..putils.derivatives import derivativeO1
from scipy import integrate

class DiagBallamp(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Ballooning representation'
        self.tabs = ['fluxtube']
        
        self.help_txt = """Plot the ballooning structure of fields
                        \n
                        \nPlot real/imag : plot real and imaginary part (def. True)
                        \nNormalize :  normalize with max amplitude (def. False)
                        \nky ind : index of the mode to plot (def. first non zero)
                        \nt avg : time averaged values (def. False)
                        """

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {'re_im': {'tag': "Plot real/imag", 'values': [True, False]},
                     'norm': {'tag': "Normalize", 'values': [False, True]},
                     't_avg': {'tag': "t avg", 'values': [False, True]},
                     'kyind': {'tag': "ky ind", 'values': None}}
        self.set_defaults()                     

    def get_kperp(self,run):
        nx = run.parameters.pnt.nx0
        ikx_grid = np.arange(- nx // 2 + 1, nx // 2 + 1)
        ky = float(run.parameters.pnt.kymin)
        dkx = 2. * np.pi * float(run.parameters.pnt.shat) * float(ky)

        nz = int(run.parameters.pnt.nz0)
        lx = float(run.parameters.pnt.lx)
        dkx = 2. * np.pi * float(run.parameters.pnt.shat) * float(ky)

        #print('\n\n\n\n\n\n\n')
        #print('kx_center' in run.parameters.pnt)
        #print(type(run.parameters.pnt))
        #print('\n\n\n\n\n\n\n')
        if run.parameters.pnt.kx_center:
            kx_center = run.parameters.pnt.kx_center
        else:
            kx_center = 0.

        self.kperp = np.zeros(nx*nz,dtype='float128')

        #print('kx_center',kx_center)
        #print('run.parameters.pnt.kx_center',run.parameters.pnt.kx_center)
        for i in ikx_grid:
            kx = i*dkx+kx_center
            #print('kx',kx)
            this_kperp = np.sqrt(self.geom.gxx*kx**2+2.*self.geom.gxy*kx*ky+self.geom.gyy*ky**2)
            self.kperp[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_kperp

    def get_omd(self,run,which_field = 0,mass_ratio = 1,charge = 1,plot = False):
        #Note: mass ratio only affects the kperp normalization for the Bessel functions
        #Default field is phi
        nx = run.parameters.pnt.nx0
        ikx_grid = np.arange(- nx // 2 + 1, nx // 2 + 1)
        nz = run.parameters.pnt.nz0
        lx = run.parameters.pnt.lx
        ky = run.parameters.pnt.kymin
        dkx = 2. * np.pi * run.parameters.pnt.shat * ky
    
        total_omnt = 0
        for i in run.parameters.species:
            total_omnt += i['omn']+i['omt']     
        dpdx_tot = run.parameters.pnt.beta * total_omnt
                ##print 'Debug: ', 'dpdx_pm =', pars['dpdx_pm'], \
        ##      'should be equal to beta*(omni+omti+omne+omte) =', dpdx_tot
    
        if run.parameters.pnt.kx_center:
            kx_center = run.parameters.pnt.kx_center
        else:
            kx_center = 0.

        omd_curv = np.zeros(nx*nz,dtype='float128')
        omd_gradB = np.zeros(nx*nz,dtype='float128')
    
        for i in ikx_grid:
            kx = i*dkx+kx_center
            this_omegad_gradB = -(self.geom.Kx*kx+self.geom.Ky*ky)/self.geom.Bfield
            this_omegad_curv = this_omegad_gradB + \
                               ky * float(run.parameters.pnt.dpdx_pm)/self.geom.Bfield**2/2.
            #this_omegad_curv = 2.*this_omegad
    
            omd_curv[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_omegad_curv
            omd_gradB[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_omegad_gradB
            #plt.plot(self.geom.Kx)
            #plt.plot(self.geom.Ky)
            #plt.show()
    
        self.omd_curv = omd_curv
        self.omd_gradB = omd_gradB

        #print(run.parameters.pnt.magn_geometry)
        if run.parameters.pnt.magn_geometry == 's_alpha' or run.parameters.pnt.magn_geometry == 'slab':
            a=input("WARNING!!! omd calculation has not been verified for s_alpha or slab!!!!! (press any key to continue)")
        #    if run.parameters.pnt.amhd:
        #        amhd = pars['amhd']
        #    else:
        #        amhd = 0.
        #    z_grid = np.linspace(-np.pi,np.pi, nz, endpoint = False)
        #    Kx0 = -np.sin(z_grid)/run.parameters.pnt.major_R
        #    Ky0 = -(np.cos(z_grid)+np.sin(z_grid)*\
        #          (run.parameters.pnt.shat*z_grid-amhd*\
        #          np.sin(z_grid)))/run.parameters.pnt.major_R
        #    omega_d0 = -(Kx0*kx_center+Ky0*ky)
        #    omega_d00 = omega_d0+amhd/run.parameters.pnt.q0**2/run.parameters.pnt.major_R/2.*ky/run.parameters.pnt.gBfield**2
        #    gxx0 = 1.
        #    gxy0 = run.parameters.pnt.shat*z_grid-amhd*np.sin(z_grid)
        #    gyy0 = 1+(run.parameters.pnt.shat*z_grid-amhd*np.sin(z_grid))**2
        #    kperp0 = np.sqrt(gxx0*kx_center**2+2.*gxy0*kx_center*ky+gyy0*ky**2)
        #plot=True
        if plot:
            plt.plot(self.kperp,label='kperp')
            plt.title('entire simulation domain')
            plt.legend()
            plt.show()
            plt.plot(omd_curv,label='omd_curv')
            plt.plot(omd_gradB,label='omd_gradB')
            plt.title('entire simulation domain')
            plt.legend()
            plt.show()
            #np.savetxt('omd_curv_gradB',np.column_stack((self.chi_ext,omd_curv,omd_gradB)))

        avg_omd_curv = self.eigenfunction_average_bessel(self.omd_curv,self.ballamps[0][which_field,:],run,mass_ratio=mass_ratio,charge = charge)
        avg_omd_gradB = self.eigenfunction_average_bessel(self.omd_gradB,self.ballamps[0][which_field,:],run,mass_ratio=mass_ratio,charge = charge)
        return avg_omd_curv,avg_omd_gradB

    def dfielddz(self,run,which_field=0):
        field = self.ballamps[0][which_field,:]
        dz = self.chi_ext[1]-self.chi_ext[0]  
        dfielddz = derivativeO1(dz,field,4)
        dfielddz = dfielddz / self.jacxB_ext
        #plt.plot(self.chi_ext,dfielddz)
        #plt.show()
        return dfielddz

    def eigenfunction_average_bessel(self,quantity,field,run, mass_ratio = 1,charge = 1, field_weighted = True, zstart = 0, zend = -1):
        kperp = self.kperp*np.sqrt(mass_ratio)/abs(charge)
        alpha = 2./3.
        bessel_factor = 1. / np.sqrt(1. + 2. * (kperp**2 + np.pi * alpha * kperp**4) /
                    (1. + alpha * kperp**2))
        show_plots = False
        if mass_ratio == 1 and show_plots:
            plt.plot(bessel_factor)
            plt.title('bessel_factor')
            plt.show()
            plt.plot(self.jacxB_ext)
            plt.title('jacxB_ext')
            plt.show()
            np.savetxt('bessel_jacxB.dat',np.column_stack((self.chi_ext,bessel_factor,self.jacxB_ext)))
        sum_ddz = 0
        denom = 0
        if zend == -1:
            zend = len(self.chi_ext) - 1
        if field_weighted:
            weight = field
        else:
            weight = np.ones_like(field)

        sum_ddz = 0.5*integrate.simps(quantity[zstart:zend] *abs(weight[zstart:zend])**2* bessel_factor[zstart:zend]*self.jacxB_ext[zstart:zend],self.chi_ext[zstart:zend])
        denom =  0.5*integrate.simps(abs(field[zstart:zend])**2 * bessel_factor[zstart:zend] *self.jacxB_ext[zstart:zend],self.chi_ext[zstart:zend])
        #print('sum_ddz',sum_ddz)
        #print('denom',denom)
        avg_quantity = sum_ddz/denom
        return avg_quantity

    def eigenfunction_average_bessel_old(self,quantity,field,run, mass_ratio = 1,charge = 1,field_weighted = True, zstart = 0, zend = -1):
        kperp = self.kperp*np.sqrt(mass_ratio)/abs(charge)
        alpha = 2./3.
        bessel_factor = 1. / np.sqrt(1. + 2. * (kperp**2 + np.pi * alpha * kperp**4) /
                    (1. + alpha * kperp**2))
        sum_ddz = 0
        denom = 0
        if zend == -1:
            zend = len(self.chi_ext) - 2
        if field_weighted:
            weight = field
        else:
            weight = np.ones_like(field)
        for i in range(zstart,zend):
            sum_ddz = sum_ddz + 0.5*((quantity[i]) *abs(weight[i])**2* bessel_factor[i] \
                  + quantity[i+1] * abs(weight[i+1])**2*bessel_factor[i+1])*\
                  (self.chi_ext[i+1]-self.chi_ext[i])*self.jacxB_ext[i]
            denom = denom + 0.5*(abs(field[i])**2 * bessel_factor[i] \
                  + abs(field[i+1])**2* bessel_factor[i+1])*\
                  (self.chi_ext[i+1]-self.chi_ext[i])*self.jacxB_ext[i]
        #print('sum_ddz',sum_ddz)
        #print('denom',denom)
        avg_quantity = sum_ddz/denom
        return avg_quantity

    def get_kpar(self,run,which_field = 0,mass_ratio = 1,charge = 1):
        #note: mass ratio is species mass over reference

        field = self.ballamps[0][which_field,:]
        imax = np.argmax(abs(field))
        field0 = field / abs(field[imax])

        dfielddz = self.dfielddz(run,which_field = which_field)
        dfielddz = dfielddz / abs(field[imax])
        avg_kz = np.sqrt(self.eigenfunction_average_bessel(abs(dfielddz)**2,field0,run,mass_ratio=mass_ratio,charge=charge,field_weighted = False))

        avg_kz = avg_kz * np.sqrt(1/mass_ratio)
        return avg_kz

    def calc_epar(self,run,show_plots = False):
        gradphi = self.dfielddz(run)
        apar = self.ballamps[0][1,:]
        #print(self.opts)
        if self.opts['norm']['value']:
            raise RuntimeError("Can't calculate E parallel with the normalized option.")
        if run.omega and run.gamma and run.omega != 0 and run.gamma != 0:
            omega_complex = run.omega*1J + run.gamma
        else:
            raise RuntimeError("Can't calculate E parallel without gamma and omega")
        #print('omega_complex',omega_complex)
        if show_plots:
            plt.plot(self.chi_ext,np.real(gradphi),'--',color = 'red')
            plt.plot(self.chi_ext,np.imag(gradphi),color = 'red')
            plt.plot(self.chi_ext,np.real(-omega_complex*apar),'--',color = 'black')
            plt.plot(self.chi_ext,np.imag(-omega_complex*apar),color = 'black')
            plt.show()
        diff = np.sum(np.abs(gradphi+omega_complex*apar)/self.jacxB_ext)
        diff_norm = diff/(np.sum(np.abs(gradphi)/self.jacxB_ext)+np.sum(np.abs(omega_complex*apar)/self.jacxB_ext))
        print("E_par/(abs(gradphi) + abs(omega Apar))",diff_norm)
        self.epar = diff_norm

    def get_info(self):
        self.need_file={'field': True,
                        'mom': False}

        return self.need_file
    
    def setup_options(self, run):
        self.geom=run.geometry
        if self.opts['kyind']['value'] is None:
            # default: 1st finite ky
            self.kyind = (1 if run.parameters.pnt.nonlinear else 0)  
        else:
            self.kyind = self.opts['kyind']['value']
            
        self.kyval = run.spatialgrid.ky[self.kyind]    
        self.n_fields = run.parameters.pnt.n_fields
        
        # we can set the phase factor here once and for all at intialization
        Cyq0_x0 = 1
        sign_shear = (-1 if run.parameters.pnt.shat < 0 else 1)
        nexc_sign = sign_shear*run.parameters.pnt.sign_Ip_CW*run.parameters.pnt.sign_Bt_CW

        if run.parameters.pnt.adapt_lx:
            nexc = 1
        else:
            nexc = int(np.round(run.parameters.pnt.lx*run.parameters.pnt.n_pol*np.absolute(
                run.parameters.pnt.shat)*run.parameters.pnt.kymin*np.absolute(Cyq0_x0)))
        nexc *= nexc_sign
        self.nexcj = nexc*(run.parameters.pnt.ky0_ind + self.kyind)
        self.nconn = int(int(int(run.parameters.pnt.nx0 - 1)/2)/np.abs(self.nexcj))*2 + 1
        try:
            self.phasefac = (-1) ** self.nexcj*np.exp(
                2.0*np.pi*1j*run.parameters.pnt.n0_global*run.parameters.pnt.q0*(
                            run.parameters.pnt.ky0_ind + self.kyind))
        except AttributeError:
            self.phasefac = 1.0

        self.chi_ext = []
        self.jacxB_ext = []
        for ncind in range(-int(self.nconn/2), int(self.nconn/2) + 1):
            self.chi_ext = np.concatenate(
                    [self.chi_ext, (run.spatialgrid.z + ncind*2.0*np.pi)])
            self.jacxB_ext = np.concatenate([self.jacxB_ext,self.geom.jacobian*self.geom.Bfield])
        self.nz0_2=int(run.parameters.pnt.nz0/2)
        self.get_kperp(run)
        self.ballamps = []

        
    def execute(self, data, run, steps, extensions):

        def __cast_ball(data_in):
            if self.opts['norm']['value']:
                normval = np.array(data_in[0, self.kyind, self.nz0_2],dtype=np.complex128)
                normphase = np.angle(normval)
                normval = np.absolute(normval)
            else:
                normphase = 0.0
                normval = 1.0
            
            balloon = np.array([], dtype=np.complex128)
            
            for ncind in range(-int(self.nconn/2), int(self.nconn/2) + 1):
                balloon = np.concatenate([balloon, np.conj(self.phasefac) ** ncind*data_in[
                    ncind*self.nexcj, self.kyind]])
             
            return balloon*np.exp(-1j*normphase)/normval

        eigenfunction=np.zeros((self.n_fields, self.chi_ext.size), dtype=np.complex128)
        #0=phi, 1=Apar, 2=Bpar
        eigenfunction[0,:]=__cast_ball(data.field.phi(step=steps['field'], extension=extensions['field']))
        if self.n_fields>1:
            eigenfunction[1,:]=__cast_ball(data.field.A_par(step=steps['field'], extension=extensions['field']))
        if self.n_fields>2:
            eigenfunction[2,:]=__cast_ball(data.field.B_par(step=steps['field'], extension=extensions['field']))   

        self.ballamps.append(eigenfunction)

        print("#############")
        #jacxB = geom.jacobian*geom.Bfield
         
        #omega_complex = omega*1.0J + gamma
        #gradphi = 
        self.calc_epar(run)
        self.kpar = {}
        self.omd = {}
        self.kperp_avg = {}

        print(run.parameters.pnt.dpdx_term)
        if(run.parameters.pnt.dpdx_term[1:-1] != 'full_drift' and run.parameters.pnt.dpdx_term[1:-1] != 'gradB_eq_curv' and run.parameters.pnt.dpdx > 0):
           raise RuntimeError("Error! This diagnostic only works for full_drift and gradB_eq_curv at the moment (easy to fix).")
        for i in run.parameters.species:
            print(i['name'])
            print(i)
            for j in range(run.parameters.pnt.n_fields):
                if j == 0:
                    field0 = 'phi'
                elif j==1:
                    field0 = 'apar'
                elif j==2:
                    field0 = 'bpar'
                self.kpar['kpar_'+field0+'_'+i['name']] = self.get_kpar(run,which_field = j,mass_ratio = i['mass'],charge = i['charge'])
                avg_omd_curv,avg_omd_gradB = self.get_omd(run,which_field = j, mass_ratio = i['mass'],charge = i['charge'])
                print(i['name'],field0,avg_omd_curv,avg_omd_gradB)
                self.omd['omd_'+field0+'_'+i['name']] = avg_omd_curv
                self.kperp_avg['kperp_avg_'+field0+'_'+i['name']] = np.sqrt(self.eigenfunction_average_bessel((self.kperp*i['mass']**0.5/i['charge'])**2,self.ballamps[0][j,:],run,mass_ratio = i['mass'],charge = i['charge']))
                #if(run.parameters.pnt.dpdx_term == 'full_drift'):
                #    self.omd['omd_'+field0+'_'+i['name']] += avg_omd_curv
                savetext = True
                if savetext:
                    np.savetxt('omd_curv_gradB_'+i['name']+field0,np.column_stack((self.chi_ext,self.kperp,self.omd_curv,self.omd_gradB)))
                #self.omd['omd_gradB_'+field0+'_'+i['name']] = avg_omd_gradB
        print("#############")


    def plot(self, time_requested, output=None, out_folder=None):
        self.plotbase = Plotting()
        lbl=['phi','apar','bpar']
        def plot_one_quant(fig, ncols, i_c, x, y, ttl, quant):

            # lin-lin plots
            ax_lin = fig.add_subplot(2, ncols, 1 + i_c)
            ax_lin.plot(x, np.absolute(y), label="|{}|".format(self.plotbase.titles[quant]),
                        color='black')
            if self.opts['re_im']['value']:
                ax_lin.plot(x, np.real(y), label="Re({})".format(self.plotbase.titles[quant]),
                            color='blue', lw=1)
                ax_lin.plot(x, np.imag(y), label="Im({})".format(self.plotbase.titles[quant]),
                            color='red', lw=1)
            ax_lin.set_xlabel(r"$\chi/\pi$")
            ax_lin.set_title(ttl)
            ax_lin.axhline(y=0, color='black', lw=1, ls='--')
            ax_lin.legend()

            # log-log plots
            ax_log = fig.add_subplot(2, ncols, ncols+1+i_c)
            ax_log.plot(x, np.absolute(y), label="|{}|".format(self.plotbase.titles[quant]),
                        color='black')
            if self.opts['re_im']['value']:
                ax_log.plot(x, np.real(y), label="Re({})".format(self.plotbase.titles[quant]),
                            color='blue', lw=1)
                ax_log.plot(x, np.imag(y), label="Im({})".format(self.plotbase.titles[quant]),
                            color='red', lw=1)
            ax_log.set_xlabel(r"$\chi/\pi$")
            ax_log.axhline(y=0, color='black', lw=1, ls='--')
            ax_log.set_yscale('log')
            ax_log.legend()

        chi_pi = self.chi_ext/np.pi
        
        ttl_ky = r"$k_y\rho={:6.3f} $".format(self.kyval)

        if self.opts['t_avg']['value']:
            fig = plt.figure()
            for i_q, quant in self.n_fields:
                plot_one_quant(fig, self.n_fields, i_q, chi_pi,
                             averages.mytrapz(np.asarray(self.ballamps)[:,i_q,:], time_requested), ttl_ky,
                             self.plotbase.titles[i_q])
            fig.show()


        elif len(time_requested) < 12:
            # allow max 12 spearate figures
            for i_t, time in enumerate(time_requested):
                fig = plt.figure()
                for i_q in np.arange(self.n_fields):
                    plot_one_quant(fig, self.n_fields, i_q, chi_pi, self.ballamps[i_t][i_q,:],
                                     ttl_ky + "@ t={:.3f}".format(time),lbl[i_q])
                fig.show()

        else:
            warnings.warn("Too many timesteps selected", RuntimeWarning)
            if output:
                output.info_txt.insert(END, "Too many timesteps selected\n")
                output.info_txt.see(END)
