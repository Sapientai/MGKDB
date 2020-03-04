# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 16:05:27 2020

@author: dykua

A Plotting class for visualizing the diagnostic plots from mgk_fusion
"""
import numpy as np
import matplotlib.pyplot as plt
from utils import averages
from diagnostics.baseplot import Plotting
import time
import os

class diag_plot():
    def __init__(self, data_dict, save_fig = True, save_dir = './'):
        '''
        data_dict retrieved from database via 'load_diag' method
        '''
        self.data = data_dict['Diagnostics']
        self._id = data_dict['_id']
        self.meta = data_dict['Meta'] if 'Meta' in data_dict else None
        self.save = save_fig
        self.save_dir = save_dir
        
    def diag_amplitude_spectra(self):
        
        kx = self.data['Grid']['kx_pos']
        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']
        
        for quant in self.data['Amplitude Spectra']['kx'].keys():

            fig = plt.figure(figsize=(6, 8))
#            fig_list.append(fig)

            ax_loglog_kx = fig.add_subplot(3, 2, 1)
            ax_loglin_kx = fig.add_subplot(3, 2, 3)
            ax_linlin_kx = fig.add_subplot(3, 2, 5)
            ax_loglog_ky = fig.add_subplot(3, 2, 2)
            ax_loglin_ky = fig.add_subplot(3, 2, 4)
            ax_linlin_ky = fig.add_subplot(3, 2, 6)

            amplitude_kx = averages.mytrapz(self.data['Amplitude Spectra']['kx'][quant], time_requested)
            amplitude_ky = averages.mytrapz(self.data['Amplitude Spectra']['ky'][quant], time_requested)

            # log-log plots, dashed lines for negative values
            baselogkx, = ax_loglog_kx.plot(kx, amplitude_kx)
            baselogky, = ax_loglog_ky.plot(ky, amplitude_ky)

            # lin-log plots, nothing fancy
            baseloglinkx, = ax_loglin_kx.plot(kx, amplitude_kx)
            baseloglinky, = ax_loglin_ky.plot(ky, amplitude_ky)

            # lin-lin plots, nothing fancy
            ax_linlin_kx.plot(kx, amplitude_kx)
            ax_linlin_ky.plot(ky, amplitude_ky)

            # set things
            ax_loglog_kx.loglog()
            ax_loglog_ky.loglog()

            ax_loglin_kx.set_xscale("log")
            ax_loglin_ky.set_xscale("log")

            # lin-lin plots, nothing fancy
            ax_linlin_kx.set_xlim(left=0)
            ax_linlin_kx.set_xlabel(r"$k_x \rho_{ref}$")
            ax_linlin_ky.set_xlabel(r"$k_y \rho_{ref}$")

            ind = quant.find('#')
            if ind == -1:
                ax_loglog_ky.set_title("{}".format(quant))
                ax_loglog_kx.set_title("{}".format(quant))
            else:
                ax_loglog_ky.set_title("{}".format(quant[0:ind] + " " + quant[ind + 1:]))
                ax_loglog_kx.set_title("{}".format(quant[0:ind] + " " + quant[ind + 1:]))
                
#            if self.meta is not None:
#                fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#            else:
            fig.suptitle( str(self._id) )
                
            fig.tight_layout()
            #plt.show()
            fig.show() 
            if self.save_fig:
                fig.savefig(os.path.join(self.save_dir, 'AmplitudeSpectra-{}-{}.png'.format(quant, time.strftime("%y%m%d-%H%M%S"))) )

    def diag_flux_spectra(self):
        
        kx = self.data['Grid']['kx_pos']
        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']
        
        self.plotbase = Plotting()
        self.plotbase.titles.update(
                {"Ges": r"$\Gamma_{es}$", "Qes": r"$Q_{es}$", "Pes": r"$\Pi_{es}$",
                 "Gem": r"$\Gamma_{em}$", "Qem": r"$Q_{em}$", "Pem": r"$\Pi_{em}$"})
        
        
        for spec in self.data['Flux Spectra'].keys():
            fig = plt.figure(figsize=(6, 8))

            ax_loglog_kx = fig.add_subplot(3, 2, 1)
            ax_loglin_kx = fig.add_subplot(3, 2, 3)
            ax_linlin_kx = fig.add_subplot(3, 2, 5)
            ax_loglog_ky = fig.add_subplot(3, 2, 2)
            ax_loglin_ky = fig.add_subplot(3, 2, 4)
            ax_linlin_ky = fig.add_subplot(3, 2, 6)

            spec_flux = self.data['Flux Spectra'][spec]
            
#            if self.meta is not None:
#                fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#            else:
            fig.suptitle( str(self._id) )

            for flux in spec_flux.keys():

                flux_kx = averages.mytrapz(spec_flux[flux]['kx'], time_requested)
                flux_ky = averages.mytrapz(spec_flux[flux]['ky'], time_requested)
                # Mask negative flux values for solid lines

                pos_flux_kx = np.ma.masked_where((flux_kx <= 0), flux_kx)
                # Mask zero flux for dashed lines, this takes care of the Nyquist mode in kx
                all_flux_kx = np.ma.masked_where((flux_kx == 0), flux_kx)

                pos_flux_ky = np.ma.masked_where((flux_ky <= 0), flux_ky)
                all_flux_ky = np.ma.masked_where((flux_ky == 0), flux_ky)

                # log-log =plots, dashed lines for negative values
                baselogkx, = ax_loglog_kx.plot(kx, pos_flux_kx, label=self.plotbase.titles[flux])
                ax_loglog_kx.plot(kx, np.abs(all_flux_kx), ls="--", color=baselogkx.get_color())
                baselogky, = ax_loglog_ky.plot(ky, pos_flux_ky, label=self.plotbase.titles[flux])
                ax_loglog_ky.plot(ky, np.abs(all_flux_ky), ls="--", color=baselogky.get_color())

                # lin-log plots, nothing fancy
                baseloglinkx, = ax_loglin_kx.plot(kx, all_flux_kx, label=self.plotbase.titles[flux])
                ax_loglin_kx.plot(kx, all_flux_kx*kx, ls="--", color=baseloglinkx.get_color())
                baseloglinky, = ax_loglin_ky.plot(ky, all_flux_ky, label=self.plotbase.titles[flux])
                ax_loglin_ky.plot(ky, all_flux_ky*ky, ls="--", color=baseloglinky.get_color())

                # lin-lin plots, nothing fancy
                ax_linlin_kx.plot(kx, all_flux_kx, label=self.plotbase.titles[flux])
                ax_linlin_ky.plot(ky, all_flux_ky, label=self.plotbase.titles[flux])

#                str_out = "{} {} = {:.4f} (kx intg.) - {:.4f} (ky intg.)".format(spec, flux,
#                                                                                 np.sum(flux_kx),
#                                                                                 np.sum(flux_ky))

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
            #plt.show()
            fig.show()
            if self.save_fig:
                fig.savefig(os.path.join(self.save_dir, 'FluxSpectra-{}-{}-{}.png'.format(spec,flux, time.strftime("%y%m%d-%H%M%S"))))
    
    def diag_shearing_rate(self):
        
        x = self.data['Grid']['x']
#        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']        
        
        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl):
            #cm1 = ax.pcolormesh(x, y, f)
            cm1 = ax.contourf(x, y, f, 100, cmap=self.plotbase.cmap_bidirect)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            #fig.colorbar(cm1)

        self.plotbase = Plotting()

        x_lbl = r'$x/\rho_{ref}$' if self.data['Shearing Rate']['x_local'] else r'x/a'

        if len(time_requested) > 1:
            # some maps
            fig = plt.figure()
#            if self.meta is not None:
#                fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#            else:
            fig.suptitle( str(self._id) )
                
            ax = fig.add_subplot(2, 2, 1)
            plot_a_map(ax, time_requested, x,
                       self.data['Shearing Rate']['phi_zonal_x'].T,
                       r'$ t c_{ref}/L_{ref}$ ', x_lbl, r'$ \langle\phi\rangle [c_{ref}/L_{ref}]$')

            ax = fig.add_subplot(2, 2, 2)
            plot_a_map(ax, time_requested, x,
                       self.data['Shearing Rate']['Er_x'].T, r'$t c_{ref}/L_{ref}$',
                       x_lbl, r'$E_r [eT_{ref}/ (\rho^*_{ref})^2 L_{ref}]$')

            ax = fig.add_subplot(2, 2, 3)
            plot_a_map(ax, time_requested, x,
                       self.data['Shearing Rate']['vExB_x'].T, r'$t c_{ref}/L_{ref}$',
                       x_lbl, r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

            ax = fig.add_subplot(2, 2, 4)
            plot_a_map(ax, time_requested, x,
                       self.data['Shearing Rate']['omegaExB_x'].T,
                       r'$t c_{ref}/L_{ref}$', x_lbl, r'$\omega_{ExB} [c_{ref}/L_{ref}]$')
            fig.show()
            if self.save_fig:
                fig.savefig(os.path.join(self.save_dir, 'ShearingRate-map-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
            #plt.show()

            # time traces
            my_pos = self.data['Shearing Rate']['my_pos']
#            print(my_pos)
            fig = plt.figure()
#            if self.meta is not None:
#                fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#            else:
            fig.suptitle( str(self._id) )
            ax = fig.add_subplot(2 + self.data['Shearing Rate']['x_local'], 1, 1)
#            print(self.data['Shearing Rate']['vExB_x'][my_pos].shape)
            ax.plot(time_requested, self.data['Shearing Rate']['vExB_x'][:,my_pos].T)
            ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
            ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

            ax = fig.add_subplot(2 + self.data['Shearing Rate']['x_local'], 1, 2)
            ax.plot(time_requested,
                    self.data['Shearing Rate']['omegaExB_x'][:,my_pos].T)
            ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
            ax.set_ylabel(r'$\omega_{ExB} [c_{ref} \rho^*_{ref}]$')

            if self.data['Shearing Rate']['x_local']:
                ax = fig.add_subplot(2 + self.data['Shearing Rate']['x_local'], 1, 3)
                ax.plot(time_requested, np.sqrt(np.mean(np.power(np.abs(self.data['Shearing Rate']['omegaExB_x']), 2),axis=1)).T) 
                         
                ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
                ax.set_ylabel(r'$\sqrt{|\omega_{ExB}|^2} [c_{ref}/L_{ref}]$')

#                shear_avg = averages.mytrapz(np.array(
#                        [np.sqrt(np.mean(np.power(np.abs(x.omegaExB_x), 2))) for x in
#                         self.shearing_rate]), time_requested)
#                str_out = "ExB shearing rate= {:.3f}".format(shear_avg)
#                if output:
#                    output.info_txt.insert(END, str_out + "\n")
#                    output.info_txt.see(END)

            fig.show()
            if self.save_fig:
                fig.savefig(os.path.join(self.save_dir, 'ShearingRate-TT.png'.format(time.strftime("%y%m%d-%H%M%S")) ))
            #plt.show()

        # zonal spectra
        if self.data['Shearing Rate']['x_local']:
            fig = plt.figure()
#            if self.meta is not None:
#                fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#            else:
            fig.suptitle( str(self._id) )
            ax = fig.add_subplot(3, 1, 1)
            ax.plot(self.data['Grid']['kx_pos'], averages.mytrapz(self.data['Shearing Rate']['abs_phi_fs'], time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')
            ax.set_title(r"$|\langle\phi\rangle|$")
            ax.loglog()

            ax = fig.add_subplot(3, 1, 2)
            ax.plot(self.data['Grid']['kx_pos'], averages.mytrapz(self.data['Shearing Rate']['abs_phi_fs'], time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')
            ax.set_xscale("log")

            ax = fig.add_subplot(3, 1, 3)
            ax.plot(self.data['Grid']['kx_pos'], averages.mytrapz(self.data['Shearing Rate']['abs_phi_fs'], time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')

            fig.show()
            if self.save_fig:
                fig.savefig(os.path.join(self.save_dir, 'ShearingRate-ZS-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
            #plt.show()

        # radial plots
        fig = plt.figure()
#        if self.meta is not None:
#            fig.suptitle(str(self._id) + ' from ' + str(self.meta))
#        else:
        fig.suptitle( str(self._id) )
        
        ax = fig.add_subplot(3, 1, 1)
        ax.plot(x,
                averages.mytrapz(self.data['Shearing Rate']['phi_zonal_x'],
                                 time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

        ax = fig.add_subplot(3, 1, 2)
        ax.plot(x,
                averages.mytrapz(self.data['Shearing Rate']['vExB_x'], time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

        ax = fig.add_subplot(3, 1, 3)
        ax.plot(x,
                averages.mytrapz(self.data['Shearing Rate']['omegaExB_x'],
                                 time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$\omega_{ExB} [c_{ref} \rho^*_{ref}]$')

        fig.tight_layout()    
        #plt.show()
        fig.show()
        if self.save_fig:
            fig.savefig(os.path.join(self.save_dir, 'ShearingRate-R-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
    
    
    def plot_all(self):
        self.diag_amplitude_spectra()
        self.diag_flux_spectra()
        self.diag_shearing_rate()
        
        
