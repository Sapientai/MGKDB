from tkinter import END

import os
import h5py
import matplotlib.pyplot as plt
import numpy as np
from ..putils.averages import flux_spectra_yz_av, flux_spectra_xz_av, xy_av3d_zprofile, mytrapz
from .baseplot import Plotting
from .diagnostic import Diagnostic
from copy import deepcopy


class DiagFluxSpectra(Diagnostic):
    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Flux spectra'
        self.tabs = ['fluxtube']

    def get_info(self):
        self.need_file={'field': True,
                        'mom': True}

        return self.need_file
    
    def setup_options(self, run):
        self.has_EM = run.parameters.pnt.n_fields>1
        self.specnames = run.parameters.pnt.specnames
        self.kx=run.spatialgrid.kx_pos
        self.ky=run.spatialgrid.ky
        self.z=run.spatialgrid.z
        self.flux_spectra_kx=[]
        self.flux_spectra_ky=[]
        self.flux_profile_z=[]
        self.time = []

    def execute(self, data, run, steps, extensions,time_point):
        #We use species, quantity kx y
        print("Executing flux spectra.")
        __spectra_kx=np.empty((len(self.specnames), 6 if self.has_EM else 3,
                               run.spatialgrid.kx_pos.size))
        __spectra_ky=np.empty((len(self.specnames), 6 if self.has_EM else 3,
                               run.spatialgrid.ky.size))
        __profile_z=np.empty((len(self.specnames), 6 if self.has_EM else 3,
                               run.spatialgrid.z.size))

        self.time.append(time_point)
        vE_x = -1.0j*run.spatialgrid.ky[np.newaxis, :, np.newaxis] \
            * data.field.phi(step=steps['field'], extension=extensions['field'])

        if run.parameters.pnt.n_fields>1:
            B_x = 1.0j*run.spatialgrid.ky[np.newaxis, :, np.newaxis] \
                * data.field.A_par(step=steps['field'], extension=extensions['field'])

            
        #print("56")
        for i_spec,spec in enumerate(run.parameters.specnames):
            n0 = run.parameters.pardict["dens{}".format(spec)]
            T0 = run.parameters.pardict["temp{}".format(spec)]
            mass = run.parameters.pardict["mass{}".format(spec)]
            charge = run.parameters.pardict["charge{}".format(spec)]

            dens = data.mom[i_spec].dens(step=steps['mom'], extension=extensions['mom'])
            T_par = data.mom[i_spec].T_par(step=steps['mom'], extension=extensions['mom'])
            T_perp = data.mom[i_spec].T_perp(step=steps['mom'], extension=extensions['mom'])
            u_par = data.mom[i_spec].u_par(step=steps['mom'], extension=extensions['mom'])

            G_es = vE_x*np.conj(dens)*n0/run.geometry.Cxy
            __spectra_kx[i_spec,0,:]=flux_spectra_yz_av(G_es, run.geometry)
            __spectra_ky[i_spec,0,:]=flux_spectra_xz_av(G_es, run.geometry)
            __profile_z[i_spec,0,:] = xy_av3d_zprofile(np.real(G_es),run.geometry)
            
            Q_es = (vE_x*np.conj(0.5*T_par + T_perp + 3./2.*dens)*n0*T0)/run.geometry.Cxy
            __spectra_kx[i_spec,1,:]=flux_spectra_yz_av(Q_es, run.geometry)
            __spectra_ky[i_spec,1,:]=flux_spectra_xz_av(Q_es, run.geometry)
            __profile_z[i_spec,1,:] = xy_av3d_zprofile(np.real(Q_es),run.geometry)
            #plt.plot(self.__spectra_ky[i_spec,1,:])
            #plt.title(str(time_point))
            #plt.show()
            #plt.plot(self.__spectra_kx[i_spec,1,:])
            #plt.title(str(time_point))
            #plt.show()
            
            P_es = (vE_x*np.conj(u_par)*n0*mass)/run.geometry.Cxy
            __spectra_kx[i_spec,2,:]=flux_spectra_yz_av(P_es, run.geometry)
            __spectra_ky[i_spec,2,:]=flux_spectra_xz_av(P_es, run.geometry)
            __profile_z[i_spec,2,:] = xy_av3d_zprofile(np.real(P_es),run.geometry)
            
            #print("89")
            if run.parameters.pnt.n_fields>1:
                Q_par = data.mom[i_spec].q_par(step=steps['mom'], extension=extensions['mom'])
                Q_perp = data.mom[i_spec].q_perp(step=steps['mom'], extension=extensions['mom'])

                G_em = B_x*np.conj(u_par)*n0/run.geometry.Cxy
                Q_em = B_x*np.conj(Q_par + Q_perp)*n0*T0/run.geometry.Cxy
                P_em = B_x*np.conj(T_par + dens)*n0*mass/run.geometry.Cxy
#TODO verify PEM something is wrong in either GENE or here
                if run.parameters.pnt.bpar:
                    # todo check if the normalization is correct
                    dBpar_dy_norm = -1j*run.spatialgrid.ky[np.newaxis,:,np.newaxis]* \
                            data.field.B_par(step=steps['field'], extension=extensions['field'])/ \
                            run.geometry.Bfield[np.newaxis, np.newaxis,:]*T0/charge
                            
                    densI1 = data.mom[i_spec].densI1(step=steps['mom'], extension=extensions['mom'])
                    TparI1 = data.mom[i_spec].TparI1(step=steps['mom'], extension=extensions['mom'])
                    TppI1 = data.mom[i_spec].TppI1(step=steps['mom'], extension=extensions['mom'])

                    G_em = G_em + (dBpar_dy_norm*np.conj(densI1))*n0/run.geometry.Cxy
                    Q_em = Q_em + (dBpar_dy_norm*np.conj(TparI1 + TppI1))*n0*T0/run.geometry.Cxy
                    
                __spectra_kx[i_spec,3,:]=flux_spectra_yz_av(G_em, run.geometry)
                __spectra_ky[i_spec,3,:]=flux_spectra_xz_av(G_em, run.geometry)
                __profile_z[i_spec,3,:] = xy_av3d_zprofile(np.real(G_em),run.geometry)
                __spectra_kx[i_spec,4,:]=flux_spectra_yz_av(Q_em, run.geometry)
                __spectra_ky[i_spec,4,:]=flux_spectra_xz_av(Q_em, run.geometry)
                __profile_z[i_spec,4,:] = xy_av3d_zprofile(np.real(Q_em),run.geometry)
                __spectra_kx[i_spec,5,:]=flux_spectra_yz_av(P_em, run.geometry)
                __spectra_ky[i_spec,5,:]=flux_spectra_xz_av(P_em, run.geometry)
                __profile_z[i_spec,5,:] = xy_av3d_zprofile(np.real(P_em),run.geometry)
                           
        #plt.plot(self.ky,__spectra_ky[1,1,:])
        #plt.title(str(time_point))
        #plt.show()
        #print("124")
        #if len(self.flux_spectra_ky) > 0:
        #    plt.plot(self.flux_spectra_ky[0][1,1,:])
        #    plt.show()
        self.flux_spectra_kx.append((__spectra_kx))
        self.flux_spectra_ky.append((__spectra_ky))
        self.flux_profile_z.append(__profile_z)


    def dict_to_mgkdb(self):
        self.flux = {}
        self.flux['Description'] = 'Spectra of all fluxes as a function of kx or ky (averaged over other variables).  The structure is [species][which_flux][kx or ky][time list][data on the kx or ky grid]. The z profiles of fluxes (averaged over kx, ky and with a factor of 1/gxx**0.5) are in [species][which flux][z][time list][data on z grid]. The time points are in [time].  The appropriate grids are in [kxgrid], [kygrid], and [zgrid].'  
        #plt.plot(self.flux_spectra_kx[0][0,0,:])
        #plt.show()
        self.flux['kxgrid'] = self.kx
        self.flux['kygrid'] = self.ky
        self.flux['zgrid'] = self.z
        self.flux['time'] = self.time
        for i in range(len(self.specnames)):
            self.flux[self.specnames[i]]={}
            self.flux[self.specnames[i]]['Qes']={}
            self.flux[self.specnames[i]]['Pes']={}
            self.flux[self.specnames[i]]['Ges']={}
            self.flux[self.specnames[i]]['Ges']['kx'] = []
            self.flux[self.specnames[i]]['Qes']['kx'] = []
            self.flux[self.specnames[i]]['Pes']['kx'] = []
            self.flux[self.specnames[i]]['Ges']['ky'] = []
            self.flux[self.specnames[i]]['Qes']['ky'] = []
            self.flux[self.specnames[i]]['Pes']['ky'] = []
            self.flux[self.specnames[i]]['Ges']['z'] = []
            self.flux[self.specnames[i]]['Qes']['z'] = []
            self.flux[self.specnames[i]]['Pes']['z'] = []
                    
            #print('dfs 120')
            if self.has_EM:
                #print('dfs 122')
                self.flux[self.specnames[i]]['Gem']={}
                self.flux[self.specnames[i]]['Qem']={}
                self.flux[self.specnames[i]]['Pem']={}
                self.flux[self.specnames[i]]['Gem']['kx'] = []
                self.flux[self.specnames[i]]['Qem']['kx'] = []
                self.flux[self.specnames[i]]['Pem']['kx'] = []
                self.flux[self.specnames[i]]['Gem']['ky'] = []
                self.flux[self.specnames[i]]['Qem']['ky'] = []
                self.flux[self.specnames[i]]['Pem']['ky'] = []
                self.flux[self.specnames[i]]['Gem']['z'] = []
                self.flux[self.specnames[i]]['Qem']['z'] = []
                self.flux[self.specnames[i]]['Pem']['z'] = []
            for j in range(len(self.flux_spectra_kx)):
                #print('len(self.flux_spectra_kx)',len(self.flux_spectra_kx))
                #print('dfs 133')
                self.flux[self.specnames[i]]['Ges']['kx'].append( self.flux_spectra_kx[j][i,0,:])
                self.flux[self.specnames[i]]['Qes']['kx'].append( self.flux_spectra_kx[j][i,1,:])
                self.flux[self.specnames[i]]['Pes']['kx'].append( self.flux_spectra_kx[j][i,2,:])
                self.flux[self.specnames[i]]['Ges']['ky'].append( self.flux_spectra_ky[j][i,0,:])
                self.flux[self.specnames[i]]['Qes']['ky'].append( self.flux_spectra_ky[j][i,1,:])
                self.flux[self.specnames[i]]['Pes']['ky'].append( self.flux_spectra_ky[j][i,2,:])
                self.flux[self.specnames[i]]['Ges']['z'].append(self.flux_profile_z[j][i,0,:])
                self.flux[self.specnames[i]]['Qes']['z'].append(self.flux_profile_z[j][i,1,:])
                self.flux[self.specnames[i]]['Pes']['z'].append(self.flux_profile_z[j][i,2,:])
                if self.has_EM:
                    self.flux[self.specnames[i]]['Gem']['kx'].append(self.flux_spectra_kx[j][i,3,:])
                    self.flux[self.specnames[i]]['Qem']['kx'].append(self.flux_spectra_kx[j][i,4,:])
                    self.flux[self.specnames[i]]['Pem']['kx'].append(self.flux_spectra_kx[j][i,5,:])
                    self.flux[self.specnames[i]]['Gem']['ky'].append(self.flux_spectra_ky[j][i,3,:])
                    self.flux[self.specnames[i]]['Qem']['ky'].append(self.flux_spectra_ky[j][i,4,:])
                    self.flux[self.specnames[i]]['Pem']['ky'].append(self.flux_spectra_ky[j][i,5,:])
                    self.flux[self.specnames[i]]['Gem']['z'].append(self.flux_profile_z[j][i,3,:])
                    self.flux[self.specnames[i]]['Qem']['z'].append(self.flux_profile_z[j][i,4,:])
                    self.flux[self.specnames[i]]['Pem']['z'].append(self.flux_profile_z[j][i,5,:])
        return self.flux
        
    def plot(self, time_requested, output=None, out_folder=None):
        """ For each selected species we have one figure with six subplots.
            Left is vs. kx, right vs. ky; columnwise we plot, log-log, log-lin, lin-in
            Dashed lines are negative values in log-log plot
            Dashed lines are k multiplied values in log-lin plot"""

        if output:
            output.info_txt.insert(END, "Flux spectra:\n")

        self.plotbase = Plotting()
        self.plotbase.titles={"Ges": r"$\Gamma_{es}$",
                              "Qes": r"$Q_{es}$", 
                              "Pes": r"$\Pi_{es}$"}
        if self.has_EM:
                 self.plotbase.titles.update({"Gem": r"$\Gamma_{em}$", 
                                              "Qem": r"$Q_{em}$", 
                                              "Pem": r"$\Pi_{em}$"})


        for i_spec,spec in enumerate(self.specnames):
            fig = plt.figure(figsize=(6, 8))

            ax_loglog_kx = fig.add_subplot(3, 2, 1)
            ax_loglin_kx = fig.add_subplot(3, 2, 3)
            ax_linlin_kx = fig.add_subplot(3, 2, 5)
            ax_loglog_ky = fig.add_subplot(3, 2, 2)
            ax_loglin_ky = fig.add_subplot(3, 2, 4)
            ax_linlin_ky = fig.add_subplot(3, 2, 6)
            
            for i_flux,flux in enumerate(self.plotbase.titles.keys()):
                if time_requested.size>1:
                    flux_kx = mytrapz(np.asarray(self.flux_spectra_kx)[:,i_spec,i_flux,:], time_requested)
                    flux_ky = mytrapz(np.asarray(self.flux_spectra_ky)[:,i_spec,i_flux,:], time_requested)
                else:
                    flux_kx = np.asarray(self.flux_spectra_kx)[0,i_spec,i_flux,:]
                    flux_ky = np.asarray(self.flux_spectra_ky)[0,i_spec,i_flux,:]
                
                # Mask negative flux values for solid lines
                pos_flux_kx = np.ma.masked_where((flux_kx <= 0), flux_kx)
                # Mask zero flux for dashed lines, this takes care of the Nyquist mode in kx
                all_flux_kx = np.ma.masked_where((flux_kx == 0), flux_kx)

                pos_flux_ky = np.ma.masked_where((flux_ky <= 0), flux_ky)
                all_flux_ky = np.ma.masked_where((flux_ky == 0), flux_ky)

                # log-log =plots, dashed lines for negative values
                baselogkx, = ax_loglog_kx.plot(self.kx, pos_flux_kx, label=self.plotbase.titles[flux])
                ax_loglog_kx.plot(self.kx, np.abs(all_flux_kx), ls="--", color=baselogkx.get_color())
                baselogky, = ax_loglog_ky.plot(self.ky, pos_flux_ky, label=self.plotbase.titles[flux])
                ax_loglog_ky.plot(self.ky, np.abs(all_flux_ky), ls="--", color=baselogky.get_color())

                # lin-log plots, nothing fancy
                baseloglinkx, = ax_loglin_kx.plot(self.kx, all_flux_kx, label=self.plotbase.titles[flux])
                ax_loglin_kx.plot(self.kx, all_flux_kx*self.kx, ls="--", color=baseloglinkx.get_color())
                baseloglinky, = ax_loglin_ky.plot(self.ky, all_flux_ky, label=self.plotbase.titles[flux])
                ax_loglin_ky.plot(self.ky, all_flux_ky*self.ky, ls="--", color=baseloglinky.get_color())

                # lin-lin plots, nothing fancy
                ax_linlin_kx.plot(self.kx, all_flux_kx, label=self.plotbase.titles[flux])
                ax_linlin_ky.plot(self.ky, all_flux_ky, label=self.plotbase.titles[flux])

                str_out = "{} {} = {:.14f} (kx intg.) - {:.14f} (ky intg.)".format(spec, flux,
                                                                                 np.sum(flux_kx),
                                                                                 np.sum(flux_ky))
                if output:
                    output.info_txt.insert(END, str_out + "\n")
                    output.info_txt.see(END)
                else:
                    print(str_out)

            # set things
            ax_loglog_kx.loglog()
            ax_loglog_kx.set_xlabel(r"$k_x \rho_{ref}$")

            ax_loglog_ky.loglog()
            ax_loglog_ky.set_xlabel(r"$k_y \rho_{ref}$")

            ax_loglin_kx.set_xscale("log")
            ax_loglin_ky.set_xscale("log")

            # lin-lin plots, nothing fancy
            ax_linlin_kx.set_xlim(left=0)
            ax_linlin_kx.set_xlabel(r"$k_x \rho_{ref}$")

            ax_linlin_ky.set_xlabel(r"$k_y \rho_{ref}$")

            for ax in [ax_loglog_kx, ax_loglin_kx, ax_linlin_kx, ax_loglog_ky, ax_loglin_ky,
                       ax_linlin_ky, ]:
                # ax.set_ylabel(r"$<|A|^2>$")
                ax.legend()
            ax_loglog_ky.set_title("{}".format(spec))
            ax_loglog_kx.set_title("{}".format(spec))
            #            fig.tight_layout()
            fig.show()

    def save(time_requested, output=None, out_folder=None):
        pass
