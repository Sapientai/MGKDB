# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 16:05:27 2020

@author: dykua

A Plotting class for visualizing the diagnostic plots from mgk_fusion
"""
import numpy as np
#import matplotlib
#matplotlib.use('GTK') # uncomment if using MAC
import scipy.linalg as linalg
import matplotlib.pyplot as plt
from .putils import averages
from .diagnostics.baseplot import Plotting
import time
import os

class diag_plot():
    def __init__(self, data_dict, save_fig = False, save_dir = './'):
        '''
        data_dict retrieved from database via 'load_diag' method
        '''
        self.data = data_dict['Diagnostics']
        self._id = data_dict['_id']
        self.meta = data_dict['Metadata'] if 'Metadata' in data_dict else None
        self.save_fig = save_fig
        self.save_dir = save_dir

        self.avail_plts = {"Amplitude Spectra": self.diag_amplitude_spectra,
                           "Flux Spectra": self.diag_flux_spectra,
                           "Shearing Rate": self.diag_shearing_rate,
                           "Freq Growth Rate": self.diag_freqgrowrate,
                           "Contours": self.diag_contours,
                           #"Ballamp": self.diag_ballamp,
                           "Cross Phase": self.diag_crossphase}
        
        self.avail_diags = self.avail_plts.keys()
        
    def diag_amplitude_spectra(self):
        
        kx = self.data['Grid']['kx_pos']
        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']
        
        plotbase = Plotting()
        plotbase.titles.update(
                {"Ges": r"$\Gamma_{es}$", "Qes": r"$Q_{es}$", "Pes": r"$\Pi_{es}$",
                 "Gem": r"$\Gamma_{em}$", "Qem": r"$Q_{em}$", "Pem": r"$\Pi_{em}$"})
    
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
            #if self.save_fig:
            #    fig.savefig(os.path.join(self.save_dir, 'AmplitudeSpectra-{}-{}.png'.format(quant, time.strftime("%y%m%d-%H%M%S"))) )

    def diag_flux_spectra(self):
        
        kx = self.data['Grid']['kx_pos']
        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']
        
        plotbase = Plotting()
        plotbase.titles={"Ges": r"$\Gamma_{es}$", "Qes": r"$Q_{es}$", "Pes": r"$\Pi_{es}$"}
#        if self.has_EM:
        plotbase.titles.update({"Gem": r"$\Gamma_{em}$", "Qem": r"$Q_{em}$", "Pem": r"$\Pi_{em}$"})
        
        
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
                baselogkx, = ax_loglog_kx.plot(kx, pos_flux_kx, label=plotbase.titles[flux])
                ax_loglog_kx.plot(kx, np.abs(all_flux_kx), ls="--", color=baselogkx.get_color())
                baselogky, = ax_loglog_ky.plot(ky, pos_flux_ky, label=plotbase.titles[flux])
                ax_loglog_ky.plot(ky, np.abs(all_flux_ky), ls="--", color=baselogky.get_color())

                # lin-log plots, nothing fancy
                baseloglinkx, = ax_loglin_kx.plot(kx, all_flux_kx, label=plotbase.titles[flux])
                ax_loglin_kx.plot(kx, all_flux_kx*kx, ls="--", color=baseloglinkx.get_color())
                baseloglinky, = ax_loglin_ky.plot(ky, all_flux_ky, label=plotbase.titles[flux])
                ax_loglin_ky.plot(ky, all_flux_ky*ky, ls="--", color=baseloglinky.get_color())

                # lin-lin plots, nothing fancy
                ax_linlin_kx.plot(kx, all_flux_kx, label=plotbase.titles[flux])
                ax_linlin_ky.plot(ky, all_flux_ky, label=plotbase.titles[flux])

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
            #if self.save_fig:
            #    fig.savefig(os.path.join(self.save_dir, 'FluxSpectra-{}-{}-{}.png'.format(spec,flux, time.strftime("%y%m%d-%H%M%S"))))
    
    def diag_shearing_rate(self):
        
        x = self.data['Grid']['x']
#        ky = self.data['Grid']['ky']
        
        time_requested = self.data['Time']        
#        plotbase = Plotting()
        
        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl, plotbase=Plotting()):
            cm1 = ax.pcolormesh(x, y, f)
#            cm1 = ax.contourf(x, y, f, 100, cmap=plotbase.cmap_bidirect)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            fig.colorbar(cm1)

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
            #if self.save_fig:
            #    fig.savefig(os.path.join(self.save_dir, 'ShearingRate-map-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
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
            #if self.save_fig:
            #    fig.savefig(os.path.join(self.save_dir, 'ShearingRate-TT.png'.format(time.strftime("%y%m%d-%H%M%S")) ))
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
            #if self.save_fig:
            #    fig.savefig(os.path.join(self.save_dir, 'ShearingRate-ZS-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
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
        #if self.save_fig:
        #    fig.savefig(os.path.join(self.save_dir, 'ShearingRate-R-{}.png'.format(time.strftime("%y%m%d-%H%M%S"))))
    
#    def diag_ballamp(self):
#        plotbase = Plotting()
#        plotbase.titles.update(
#                {"phi": r"$\phi$", "A_par": r"$A_{\parallel}$", "B_par": r"$B_{\parallel}$",
#                 "dens": r"$n$", "T_par": r"T_{\parallel}", "T_perp": r"T_{\perp}",
#                 "u_par": r"u_{\parallel}", "q_par": r"q_{\parallel}",
#                 "q_perp": r"q_{\perp}"})
#
#        def plot_a_quant(fig, ncols, i_c, x, y, ttl, quant):
#
#            # lin-lin plots
#            ax_lin = fig.add_subplot(2, ncols, 1 + 2*(i_c - 1))
#            ax_lin.plot(x, np.absolute(y), label="|{}|".format(plotbase.titles[quant]),
#                        color='black')
#            if self.data['Ballamp']['opts']['re_im']['value']:
#                ax_lin.plot(x, np.real(y), label="Re({})".format(plotbase.titles[quant]),
#                            color='blue', lw=1)
#                ax_lin.plot(x, np.imag(y), label="Im({})".format(plotbase.titles[quant]),
#                            color='red', lw=1)
#            ax_lin.set_xlabel(r"$\chi/\pi$")
#            ax_lin.set_title(ttl)
#            ax_lin.axhline(y=0, color='black', lw=1, ls='--')
#            ax_lin.legend()
#
#            # log-log plots
#            ax_log = fig.add_subplot(2, ncols, 2 + 2*(i_c - 1))
#            ax_log.plot(x, np.absolute(y), label="|{}|".format(plotbase.titles[quant]),
#                        color='black')
#            if self.data['Ballamp']['opts']['re_im']['value']:
#                ax_log.plot(x, np.real(y), label="Re({})".format(plotbase.titles[quant]),
#                            color='blue', lw=1)
#                ax_log.plot(x, np.imag(y), label="Im({})".format(plotbase.titles[quant]),
#                            color='red', lw=1)
#            ax_log.set_xlabel(r"$\chi/\pi$")
#            ax_log.axhline(y=0, color='black', lw=1, ls='--')
#            ax_log.set_yscale('log')
#            ax_log.legend()
#
#        chi_pi = self.data['Ballamp']['chi_pi']
#        kyval = self.data['Ballamp']['kyval']
#        ttl_ky = r"$k_y\rho={:6.3f} $".format(kyval)
#
#        if self.data['Ballamp']['opts']['t_avg']['value']:
#            # loop over file
#            if self.data['Ballamp']['only field']:
#                nc = len(self.data['Ballamp']['ballamps'].keys() )
#                fig = plt.figure()
#                for i_q, quant in enumerate(self.data['Ballamp']['ballamps'].keys()):
#                    plot_a_quant(fig, nc, i_q + 1, chi_pi,
#                                 averages.mytrapz(self.data['Ballamp']['ballamps'][quant], self.data['Time']  ), ttl_ky,
#                                 quant)
#                    fig.suptitle( str(self._id) )
#                    fig.show()
#            else:
#                for quant in self.data['Ballamp']['ballamps'].keys():
#                    fig = plt.figure()
#                    #                    ttl = self.plotbase.titles[quant] if quant.find('#')==-1
#                    #                    else self.plotbase.titles[quant[0:quant.find(
#                    #                    '#')==-1]]+" "+quant[quant.find('#')==-1+1:]
#                    if quant.find('#') == -1:
#                        ttl = plotbase.titles[quant]
#                    else:
#                        ttl = quant[quant.find('#') + 1:]
#                    plot_a_quant(fig, 1, 1, chi_pi,
#                                 averages.mytrapz(self.data['Ballamp']['ballamps'][quant], self.data['Time'] ), ttl,
#                                 quant[0:quant.find('#')])
#                    fig.suptitle( str(self._id) )
#                    fig.show()
#
#        elif len(self.data['Time']) < 12:
#            # in this case we plot on a single figure for each quantity
#            if self.data['Ballamp']['only field']:
#                nc = len(self.data['Ballamp']['ballamps'].keys() )
#                for i_t, time in enumerate(self.data['Time']):
#                    fig = plt.figure()
#                    for i_q, quant in enumerate(self.data['Ballamp']['ballamps'].keys()):
#                        plot_a_quant(fig, nc, i_q + 1, chi_pi, self.data['Ballamp']['ballamps'][quant][i_t].T,
#                                     ttl_ky + "@ t={:.3f}".format(time), quant)
#                    fig.suptitle( str(self._id) )
#                    fig.show()
#            else:
#                for quant in self.data['Ballamp']['ballamps'].keys():
#                    ind = quant.find('#')
#                    if ind == -1:
#                        ttl = plotbase.titles[quant]
#                        leg = quant
#                    else:
#                        leg = quant[0:ind]
#                        ttl = quant[ind + 1:] + " "
#                    for i_t, time in enumerate(self.data['Time']):
#                        fig = plt.figure()
#                        plot_a_quant(fig, 1, 1, chi_pi, self.data['Ballamp']['ballamps'][quant][i_t].T,
#                                     ttl + ttl_ky + "@ t={:.3f}".format(time), leg)
#                        fig.suptitle( str(self._id) )
#                        fig.show()
    
    def diag_freqgrowrate(self):
        Freq_arr = []
        Grate_arr = []
        ky_arr = []

        def extract_freq(phi_pt, times_req, act_ky, plot_all, output=None):
            #   Amplitude and phase
            freq_trace = np.imag(np.diff(np.log(phi_pt)) / np.diff(times_req))
            gamma_trace = np.real(np.diff(np.log(phi_pt)) / np.diff(times_req))

            ph_f = np.angle(phi_pt)
            ampl_f = np.abs(phi_pt)

            #   linear regression of phase
            M = np.column_stack((np.ones(times_req.size), times_req))

            coeffsFreq = linalg.lstsq(M, ph_f)[0]
            coeffsAmp = linalg.lstsq(M, np.log(ampl_f))[0]

            Freq = coeffsFreq[1]
            Grate = coeffsAmp[1]

            Freq_arr.append(Freq)
            Grate_arr.append(Grate)

            if output:
                str_out = "ky mode {}: (Frequency, GrowthRate) {} {}\n".format(act_ky, Freq, Grate)
                output.info_txt.insert(END, str_out)

            if plot_all:
                ttl = r"$k_y\rho={:6.3f} $".format(act_ky)

                fig = plt.figure()

                ax_1 = fig.add_subplot(3, 1, 1)
                ax_1.plot(times_req, ampl_f, ls="-", color='b')
                ax_1.plot(times_req, np.exp(coeffsAmp[0] +
                                            coeffsAmp[1] * times_req),
                          ls="-", color='r')
                ax_1.set_xlabel(r"$t  c_{ref} / L_{ref}$")
                ax_1.set_yscale("log")
                ax_1.set_ylabel(r'$|\phi|$')
                ax_1.set_title(ttl)
                ax_1.text(0.05, 0.8, r'$\gamma={:4.3f}'.format(Grate) +
                          ' c_{ref}/L_{ref}$', transform=ax_1.transAxes)

                ax_2 = fig.add_subplot(3, 1, 2)
                ax_2.plot(times_req, ph_f, ls="-", color='b')
                ax_2.plot(times_req, coeffsFreq[0] + coeffsFreq[1] * times_req,
                          ls="--", color='r')
                ax_2.set_xlabel(r"$t  c_{ref} / L_{ref}$")
                ax_2.set_ylabel(r'$arg(\phi)$')
                ax_2.text(0.05, 0.8, r'$\omega={:4.3f}'.format(Freq) +
                          ' c_{ref}/L_{ref}$', transform=ax_2.transAxes)

                ax_3 = fig.add_subplot(3, 1, 3)
                ax_3.plot(times_req, np.abs(np.real(phi_pt)), ls='-',
                          color='b', label=r"$Re(|\phi|)$")
                ax_3.plot(times_req, np.abs(np.imag(phi_pt)), ls='--',
                          color='r', label=r"$Imag(|\phi|)$")
                ax_3.set_xlabel(r"$t  c_{ref} / L_{ref}$")
                ax_3.set_yscale("log")
                ax_3.legend()
                
                fig.suptitle( str(self._id) )
                fig.show()

                fig_t = plt.figure()
                a_1 = fig_t.add_subplot(2, 1, 1)
                a_1.plot(times_req[:-1], freq_trace, ls="-", color='b')
                a_1.set_xlabel(r"$t c_{ref}/L_{ref}$")
                a_1.set_ylabel(r"$\omega_r c_{ref}/L_{ref}$")
                a_1.set_title(ttl)

                a_2 = fig_t.add_subplot(2, 1, 2)
                a_2.plot(times_req[:-1], gamma_trace, ls="-", color='b')
                a_2.set_xlabel(r"$t c_{ref}/L_{ref}$")
                a_2.set_ylabel(r"$\gamma c_{ref}/L_{ref}$")
                
                fig_t.suptitle( str(self._id) )
                fig_t.show()

        plotbase = Plotting()
        plot_all = 1 if self.data['Freq Growth Rate']['opts']['show']['value'] else 0
        for ky in range(0, len(self.data['Freq Growth Rate']['phi'][0][:])):
            if (np.absolute(self.data['Freq Growth Rate']['ky'][ky]) <= np.absolute(self.data['Freq Growth Rate']['ky'][self.data['Freq Growth Rate']['kyind_max']])
                and np.absolute(self.data['Freq Growth Rate']['ky'][ky]) >= np.absolute(self.data['Freq Growth Rate']['ky'][self.data['Freq Growth Rate']['kyind_min']])):

                phi_trace = np.array([x[ky] for x in self.data['Freq Growth Rate']['phi']])
                act_ky = self.data['Freq Growth Rate']['ky'][ky]
                extract_freq(phi_trace, self.data['Time'], act_ky, plot_all, output=None)
                ky_arr.append(act_ky)

        fig_f = plt.figure()
        a_1 = fig_f.add_subplot(2, 1, 1)
        a_1.plot(ky_arr, Grate_arr, 'bo')
        a_1.set_xlabel(r"$k_y$")
        a_1.set_ylabel(r"$\gamma c_{ref}/L_{ref}$")
        a_2 = fig_f.add_subplot(2, 1, 2)
        a_2.plot(ky_arr, Freq_arr, 'bo')
        a_2.set_xlabel(r"$k_y$")
        a_2.set_ylabel(r"$\omega c_{ref}/L_{ref}$")
        
        fig_f.suptitle( str(self._id) )
        fig_f.show()
        
        
    def diag_crossphase(self):
        nbins = 64

        out = np.zeros((len(self.data['Grid']['ky']), nbins))

#        plotbase = Plotting()

        for spec in self.data['Cross Phase']['cross_phase'].keys():
            array = np.array(self.data['Cross Phase']['cross_phase'][spec])           
            for i_ky in range(len(self.data['Grid']['ky'])):
                phase_ky = array[:,:,i_ky,...].flatten()
#                phase_ky = self.cross_phase[spec][:][:][i_ky][:][:].flatten()
                hist, bin_edges = np.histogram(phase_ky/self.data['Cross Phase']['nx0']/self.data['Cross Phase']['nz0'],
                                               bins=nbins, range=(-np.pi, np.pi))
                out[i_ky, :] = hist

            fig = plt.figure()
            plt.xlabel('Phase angle/rad', fontsize=14)
            plt.ylabel(r'$k_y\rho_s$', fontsize=16)
            # cm1 = plt.contourf(bin_edges[1:],ky[1:],out[1:,:],50,cmap=self.plotbase.cmap_bidirect)
            cm1 = plt.pcolormesh(bin_edges[1:], self.data['Grid']['ky'][1:], out[1:, :])
            fig.colorbar(cm1)
            fig.tight_layout()
            fig.suptitle( str(self._id) )
            fig.show()
            
    def diag_contours(self):
        plotbase = Plotting()
        if self.data['Contours']['is3d']:
            plotbase.titles.update(
                    {"phi": r"$\phi$", "n": r"$n$", "u_par": r"u_{//}", "T_par": r"T_{//}",
                     "T_perp": r"T_{\perp}", "Q_es": r"$Q_{es}$", "Q_em": r"$Q_{em}$",
                     "Gamma_es": r"$\Gamma_{es}$", "Gamma_em": r"$\Gamma_{em}$"})
        else:
            plotbase.titles.update(
                    {"phi": r"$\phi$", "A_par": r"$A_{//}$", "B_par": r"$B_{//}$", "dens": r"$n$",
                     "T_par": r"T_{//}", "T_perp": r"T_{\perp}", "u_par": r"u_{//}",
                     "q_par": r"q_{//}", "q_perp": r"q_{\perp}"})
        
        if self.data['Contours']['opts']['f_x']['value']:
            x_lbl = r"$k_x\rho_{ref}$"
            x = self.data['Grid']['kx_fftorder']
        else:
            x_lbl = r"$x/\rho_{ref}$"
            x = self.data['Grid']['x']

        if self.data['Contours']['opts']['f_y']['value']:
            y_lbl = r"$k_y\rho_{ref}$"
            y = self.data['Grid']['ky']
        else:
            y_lbl = r"$y/\rho_{ref}$"
            y = self.data['Grid']['y']

        is_f = self.data['Contours']['opts']['f_x']['value'] or self.data['Contours']['opts']['f_y']['value']

        if self.data['Contours']['opts']['t_avg']['value']:
            # loop over file
            for quant in self.data['Contours']['contours'].keys():
                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                fig = plt.figure()
                ax = fig.add_subplot(111)
                plotbase.plot_contour_quant(ax, fig, x, y,
                                            averages.mytrapz(self.data['Contours']['contours'][quant], self.data['Time']),
                                            is_f, x_lbl, y_lbl, ttl)
                fig.suptitle( str(self._id) )
                fig.show()
        else:
            for quant in self.data['Contours']['contours'].keys():
                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                fig = plt.figure()
                ax = fig.add_subplot(111)
                plotbase.plot_contour_quant_timeseries(ax, fig, x, y, self.data['Contours']['contours'][quant], is_f,
                                                       self.data['Time'], x_lbl, y_lbl, ttl)
                fig.suptitle( str(self._id) )
                fig.show()
#        plt.show()
       
                
    def plot_all(self):
        for p in self.avail_plts.keys():
            self.avail_plts[p]()
    
    def print_avail_diags(self):
        print("Available diagnostics are: {}".format(self.avail_diags) )
        
    def plot_diag(self, key):
        if key in self.avail_plts.keys():
            self.avail_plts[key]()
        else:
            print("The specified diagnostic is not supported.")
            
#        self.diag_amplitude_spectra()
#        self.diag_flux_spectra()
#        self.diag_shearing_rate()
#        self.diag_contours()
#        self.diag_ballamp()
#        self.diag_crossphase()
#        self.diag_freqgrowrate()
        
    
        
        
        
