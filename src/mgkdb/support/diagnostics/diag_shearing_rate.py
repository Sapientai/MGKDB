# -*- coding: utf-8 -*-

from tkinter import END

import matplotlib.pyplot as plt
import numpy as np

import ..putils.averages as averages
import ..putils.derivatives as deriv
from .baseplot import Plotting
from .diagnostic import Diagnostic
import os


class DiagShearingRate(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Shearing rate'
        self.tabs = ['fluxtube', 'xglobal']

        self.help_txt = """Analyze zonal flow and shearing rate.
                        \n
                        \nadd MRS: add MRS to radial plots (def. False)
                        \nx0: at whch position one takes traces (def. center)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {'MRS': {'tag': "add MRS", 'values': [False, True]},
                     'pos': {'tag': "x0", 'values': None},
                     'GAMs': {'tag': "GAM estimate", 'values': [False, True]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run, specnames, out_folder):
        
        self.x_local = run.parameters[0].pardict.get('x_local')
        self.y_local = run.parameters[0].pardict.get('y_local')
        if not self.y_local:
            raise NotImplementedError("Not yet implemented for y global simulations")

#        self.run_data = run_data
        self.specnames = specnames
#        self.geom = run_data.geometry
        self.dx = run.spatialgrid[0].x[1] - run.spatialgrid[0].x[0]
        self.x = run.spatialgrid[0].x
        # using the methods from diagspace and fourier is cumbersome, so by hand
        self.nx0 = run.spatialgrid[0].nx0

        self.kx_pos = run.spatialgrid[0].kx_pos

        self.mypos = self.opts['pos']['value']
        if not self.mypos:
            self.my_pos = np.argmin(np.abs(run.spatialgrid[0].x))

        self.shearing_rate = []

        # toggle the reader
        self.get_needed_vars(['field'])

        return self.needed_vars

    def execute(self, data, parameters, geometry, spatialgrid,  step):

        class ZonalStep:
            def __init__(self, phi_zonal_x, Er_x, vExB_x, omegaExB_x, abs_phi_fs):
                self.phi_zonal_x = phi_zonal_x
                self.Er_x = Er_x
                self.vExB_x = vExB_x
                self.omegaExB_x = omegaExB_x
                self.abs_phi_fs = abs_phi_fs

        data_kxky = data.field.phi(step.time, step.field, parameters)

        if self.x_local:
            # flux-tube version
            data_fsavg = np.squeeze(averages.z_av3d(data_kxky[:, 0, :], geometry))
            phi_zonal_x = self.nx0*np.real_if_close(np.fft.ifft(data_fsavg, axis=-1), tol=1e-14)
            # Er
            Er_x = self.nx0*np.real_if_close(
                np.fft.ifft(-1j*spatialgrid.kx_fftorder*data_fsavg, axis=-1),
                tol=1e-14)
            # ExB velocity
            vExB_x = -Er_x/geometry.Cxy
            # shearing rate
            omegaExB_x = -self.nx0*np.real_if_close(
                np.fft.ifft(np.power(spatialgrid.kx_fftorder, 2)*data_fsavg, axis=-1),
                tol=1e-14)/geometry.Cxy

            self.shearing_rate.append(
                ZonalStep(phi_zonal_x, Er_x, vExB_x, omegaExB_x, np.abs(data_fsavg)))

        elif not self.x_local and self.y_local:
            # global version
            # we compute the radial electric field, then we fsavg it, as in
            # Eq. 5.20 of X.Lapillonne thesis. Then divide by C_xy for ExB
            # velocity and further derive for shearing rate. q profile is taken
            # into account. This is correct for circular plasma only"""

            phi_zonal_x = np.squeeze(averages.z_av3d(data_kxky[:, 0, :], geometry))

            # Er
            Er_x = deriv.compute(self.dx, phi_zonal_x, 1)
            # ExB velocity
            vExB_x = -Er_x/geometry.Cxy
            # shearing rate
            omegaExB_x = spatialgrid[0].x/geometry.q*deriv.compute(
                geometry.q*Er_x/spatialgrid[0].x, 2)/self.dx
#            return  # TODO: This will raise an exception!
            self.shearing_rate.append(
                ZonalStep(phi_zonal_x, Er_x, vExB_x, omegaExB_x, np.abs(data_fsavg)))
    
    def dict_to_mgkdb(self):
        Diag_dict = {}
        Diag_dict['my_pos'] = self.my_pos
            
        Diag_dict['Er_x'] = np.array([x.Er_x for x in self.shearing_rate])
        Diag_dict['omegaExB_x'] = np.array([x.omegaExB_x for x in self.shearing_rate])
        Diag_dict['phi_zonal_x'] = np.array([x.phi_zonal_x for x in self.shearing_rate])
        Diag_dict['vExB_x'] = np.array([x.vExB_x for x in self.shearing_rate])
        
        if self.x_local:
            Diag_dict['x_local'] = 1
            Diag_dict['abs_phi_fs'] = np.array([x.abs_phi_fs[0:len(self.kx_pos)] for x in
                                                                 self.shearing_rate]) 
        else:
            Diag_dict['x_local'] = 0
            Diag_dict['abs_phi_fs'] = 'None'
            
        if self.y_local:
            Diag_dict['y_local'] = 1
        else:
            Diag_dict['y_local'] = 0
            
        return Diag_dict

    def plot(self, time_requested, output=None, out_folder=None, terminal=None, suffix = None):

        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl):
#            cm1 = ax.pcolormesh(x, y, f)
            #            cm1 = ax.contourf(x, y, f,
            #                            100, cmap=self.plotbase.cmap_bidirect)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
#            fig.colorbar(cm1)

        self.plotbase = Plotting()

        x_lbl = r'$x/\rho_{ref}$' if self.x_local else r'x/a'

        if len(time_requested) > 1:
            # some maps
            fig = plt.figure()
            ax = fig.add_subplot(2, 2, 1)
            plot_a_map(ax, time_requested, self.x,
                       np.array([x.phi_zonal_x for x in self.shearing_rate]).T,
                       r'$ t c_{ref}/L_{ref}$ ', x_lbl, r'$ \langle\phi\rangle [c_{ref}/L_{ref}]$')

            ax = fig.add_subplot(2, 2, 2)
            plot_a_map(ax, time_requested, self.x,
                       np.array([x.Er_x for x in self.shearing_rate]).T, r'$t c_{ref}/L_{ref}$',
                       x_lbl, r'$E_r [eT_{ref}/ (\rho^*_{ref})^2 L_{ref}]$')

            ax = fig.add_subplot(2, 2, 3)
            plot_a_map(ax, time_requested, self.x,
                       np.array([x.vExB_x for x in self.shearing_rate]).T, r'$t c_{ref}/L_{ref}$',
                       x_lbl, r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

            ax = fig.add_subplot(2, 2, 4)
            plot_a_map(ax, time_requested, self.x,
                       np.array([x.omegaExB_x for x in self.shearing_rate]).T,
                       r'$t c_{ref}/L_{ref}$', x_lbl, r'$\omega_{ExB} [c_{ref}/L_{ref}]$')

            if out_folder is not None:
                try:
                    fig.savefig( os.path.join(out_folder, 'ShearingRate_Map{}.png'.format(suffix)) , bbox_inches='tight')
                    plt.close(fig)
                except:
                    pass
            else:
                fig.show()


            # time traces
            fig = plt.figure()
            ax = fig.add_subplot(2 + self.x_local, 1, 1)
            ax.plot(time_requested, np.array([x.vExB_x[self.my_pos] for x in self.shearing_rate]).T)
            ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
            ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

            ax = fig.add_subplot(2 + self.x_local, 1, 2)
            ax.plot(time_requested,
                    np.array([x.omegaExB_x[self.my_pos] for x in self.shearing_rate]).T)
            ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
            ax.set_ylabel(r'$\omega_{ExB} [c_{ref} \rho^*_{ref}]$')

            if self.x_local:
                ax = fig.add_subplot(2 + self.x_local, 1, 3)
                ax.plot(time_requested, np.array(
                        [np.sqrt(np.mean(np.power(np.abs(x.omegaExB_x), 2))) for x in
                         self.shearing_rate]).T)
                ax.set_xlabel(r'$t c_{ref}/L_{ref}$')
                ax.set_ylabel(r'$\sqrt{|\omega_{ExB}|^2} [c_{ref}/L_{ref}]$')

                shear_avg = averages.mytrapz(np.array(
                        [np.sqrt(np.mean(np.power(np.abs(x.omegaExB_x), 2))) for x in
                         self.shearing_rate]), time_requested)
                str_out = "ExB shearing rate= {:.3f}".format(shear_avg)
                
                if output:
                    output.info_txt.insert(END, str_out + "\n")
                    output.info_txt.see(END)
                if terminal:
                    print(str_out)
            
            if out_folder is not None:
                fig.savefig( os.path.join(out_folder, 'ShearingRate_TimeTraces{}.png'.format(suffix) ), bbox_inches='tight')
                plt.close(fig)
            else:
                fig.show()

        # zonal spectra
        if self.x_local:
            fig = plt.figure()
            ax = fig.add_subplot(3, 1, 1)
            ax.plot(self.kx_pos, averages.mytrapz(np.array(
                    [x.abs_phi_fs[0:len(self.kx_pos)] for x in
                     self.shearing_rate]), time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')
            ax.set_title(r"$|\langle\phi\rangle|$")
            ax.loglog()

            ax = fig.add_subplot(3, 1, 2)
            ax.plot(self.kx_pos, averages.mytrapz(np.array(
                    [x.abs_phi_fs[0:len(self.kx_pos)] for x in
                     self.shearing_rate]), time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')
            ax.set_xscale("log")

            ax = fig.add_subplot(3, 1, 3)
            ax.plot(self.kx_pos, averages.mytrapz(np.array(
                    [x.abs_phi_fs[0:len(self.kx_pos)] for x in
                     self.shearing_rate]), time_requested))
            ax.set_xlabel(r'$k_x \rho_{ref}$')
            
            if out_folder is not None:
                fig.savefig( os.path.join(out_folder, 'ShearingRate_ZonalSpectra{}.png'.format(suffix) ), bbox_inches='tight')
                plt.close(fig)
            else:
                fig.show()

        # radial plots
        fig = plt.figure()
        ax = fig.add_subplot(3, 1, 1)
        ax.plot(self.x,
                averages.mytrapz(np.array([x.phi_zonal_x for x in self.shearing_rate]),
                                 time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

        ax = fig.add_subplot(3, 1, 2)
        ax.plot(self.x,
                averages.mytrapz(np.array([x.vExB_x for x in self.shearing_rate]), time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$v_{ExB} [c_{ref} \rho^*_{ref}]$')

        ax = fig.add_subplot(3, 1, 3)
        ax.plot(self.x,
                averages.mytrapz(np.array([x.omegaExB_x for x in self.shearing_rate]),
                                 time_requested))
        ax.set_xlabel(x_lbl)
        ax.set_ylabel(r'$\omega_{ExB} [c_{ref} \rho^*_{ref}]$')

        fig.tight_layout()
        
        if out_folder is not None:
            fig.savefig(os.path.join(out_folder, 'ShearingRate_Radial{}.png'.format(suffix)), bbox_inches='tight')
            plt.close(fig)
        else:
            fig.show()

    def save(time_requested, output=None, out_folder=None):
        pass

    def finalize():
        pass
