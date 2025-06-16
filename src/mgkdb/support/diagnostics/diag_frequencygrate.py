# -*- coding: utf-8 -*-

from tkinter import END

import h5py
import matplotlib.pyplot as plt
import numpy as np
import scipy.linalg as linalg

import ..utils.aux_func as aux_func
from .baseplot import Plotting
from .diagnostic import Diagnostic
import os

class DiagFrequencyGrowthRate(Diagnostic):
    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Frequency & Growth-rate'
        self.tabs = ['fluxtube', 'xglobal', 'GENE3D']

        self.help_txt = """Frequency diagnostic
                        \n
                        \nWeight: weight with parallel mode structure (def. False)
                        \nky ind : comma separated |ky| fourier modes (e.g 0.5,1.0), default all range
                        \nz ind : comma separated z interval (e.g., -3,3), default all range
                        \nshow time traces : show time traces for different |ky|, default false
                        \nSave h5 : save hdf5 file (def. True)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"weight": {'tag': 'weight', 'values': [False, True]},
                     "kyind": {'tag': "ky ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None},
                     "show": {'tag': "Show time traces", 'values': [False, True]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run, specnames, out_folder):

        self.phi = []
#        self.geom = run_data.geometry
#        self.run_data = run_data
        self.specnames = specnames
        
        self.pnt = run.parameters[0].asnamedtuple()

        self.weight = 1 if self.opts['weight']['value'] else 0
        
        self.ky = run.spatialgrid[0].ky

        kyind = self.opts['kyind']['value']
        if not kyind or kyind == -1:
            self.kyind = 0.0, 100
        else:
            self.kyind = kyind.split(',')
        self.kyind_min = aux_func.find_nearest(run.spatialgrid[0].ky, float(self.kyind[0]))
        self.kyind_max = aux_func.find_nearest(run.spatialgrid[0].ky, float(self.kyind[1]))

        # z position, unset or -1 means all
        zind = self.opts['zind']['value']
        if not zind or zind == -1:
            self.zind = -100, 100  # this will choose the minimum and maximum values
        else:
            self.zind = zind.split(',')
        self.zind_min, self.zind_max = aux_func.find_nearest_points(run.spatialgrid[0].z, float(self.zind[0]), float(self.zind[1]))

        self.get_needed_vars(['field'])

        return self.needed_vars

    def execute(self, data, parameters, geometry, spatialgrid,  step):

        phi = getattr(getattr(data, 'field'), "phi")(step.time, step.field, parameters)
        renorm = 0.0

        if self.pnt.flux_tube:
            phi_ = np.zeros(len(range(self.kyind_min, self.kyind_max+1)), dtype=np.complex64)
            # loop over all ky modes
            for i_ky, j in enumerate(range(self.kyind_min, self.kyind_max+1)):
                for i in range(0, self.pnt.nx0-1):
                    renorm = renorm + np.dot(np.squeeze(phi[i, j, self.zind_min:self.zind_max+1]**(2 * self.weight)),
                                             geometry.jacobian[self.zind_min:self.zind_max+1])
                    phi_[i_ky] = phi_[i_ky] + \
                        np.dot(np.squeeze(phi[i, j, self.zind_min:self.zind_max+1]**(2 * self.weight) * phi[i, j, self.zind_min:self.zind_max+1]),
                               geometry.jacobian[self.zind_min:self.zind_max+1])
                phi_[i_ky] = phi_[i_ky] / renorm

        elif self.pnt.x_global:
            phi_ = np.zeros(len(range(self.kyind_min, self.kyind_max+1)), dtype=np.complex64)
            # loop over all ky modes
            for i_ky, j in enumerate(range(self.kyind_min, self.kyind_max+1)):
                for i in range(0, self.pnt.nx0-1):
                    renorm = renorm + np.dot(np.squeeze(phi[i, i_ky, self.zind_min:self.zind_max+1]**(2 * self.weight)),
                                             geometry.jacobian.T[i, self.zind_min:self.zind_max+1])
                    phi_[i_ky] = phi_[i_ky] + \
                        np.dot(np.squeeze(phi[i, i_ky, self.zind_min:self.zind_max+1]**(2 * self.weight) * phi[i, i_ky, self.zind_min:self.zind_max+1]),
                               geometry.jacobian.T[i, self.zind_min:self.zind_max+1])
                phi_[i_ky] = phi_[i_ky] / renorm

        elif self.pnt.is3d:
            phi_ = np.zeros(len(range(self.kyind_min, self.kyind_max+1)), dtype=np.complex64)
            phi_c = np.fft.fft(phi, axis=1)/self.pnt.ny0
            jaco_xz = np.mean(geometry.jacobian.T, axis=1)
                        # loop over all ky modes
            for i_ky, j in enumerate(range(self.kyind_min, self.kyind_max+1)):
                for i in range(0, self.pnt.nx0-1):
                    renorm = renorm + np.dot(np.squeeze(phi_c[i, i_ky, self.zind_min:self.zind_max+1]**(2 * self.weight)), jaco_xz[i, self.zind_min:self.zind_max+1])
                    phi_[i_ky] = phi_[i_ky] + \
                        np.dot(np.squeeze(phi_c[i, i_ky, self.zind_min:self.zind_max+1]**(2 * self.weight) * phi_c[i, i_ky, self.zind_min:self.zind_max+1]), jaco_xz[i, self.zind_min:self.zind_max+1])
                phi_[i_ky] = phi_[i_ky] / renorm
        else:
            raise NotImplementedError("Frequency calculation not implemented")

        self.phi.append(phi_)
        
    def dict_to_mgkdb(self):
        Diag_dict = {}
        Diag_dict['opts']=self.opts
        Diag_dict['ky'] = self.ky
        Diag_dict['kyind_min'] = self.kyind_min
        Diag_dict['kyind_max'] = self.kyind_max
        Diag_dict['phi'] = self.phi
        
        return Diag_dict
        
        

    def plot(self, time_requested, output=None, out_folder=None, terminal=None, suffix = None):

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
                
                if out_folder is not None:
                    fig.savefig(os.path.join(out_folder, 'FreqGrowthRate_phi{}.png'.format(suffix)), bbox_inches='tight')                  
                    plt.close(fig)
                else:
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
                
                if out_folder is not None:
                    fig_t.savefig(os.path.join(out_folder, 'FreqGrowthRate_OmegaGamma{}.png'.format(suffix)), bbox_inches='tight') 
                    plt.close(fig_t)
                else:
                    fig_t.show()

        self.plotbase = Plotting()
        plot_all = 1 if self.opts['show']['value'] else 0
        for ky in range(0, len(self.phi[0][:])):
            if (np.absolute(self.ky[ky]) <= np.absolute(self.ky[self.kyind_max])
                and np.absolute(self.ky[ky]) >= np.absolute(self.ky[self.kyind_min])):

                phi_trace = np.array([x[ky] for x in self.phi])
                act_ky = self.ky[ky]
                extract_freq(phi_trace, time_requested, act_ky, plot_all, output=None)
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
        
        if out_folder is not None:
            fig_f.savefig( os.path.join(out_folder, 'FreqGrowthRate_OmegaGamma_arr{}.png'.format(suffix)), bbox_inches='tight') 
            plt.close(fig_f)
        else:   
            fig_f.show()

#        if self.opts['save_h5']['value']:
#            file = h5py.File(out_folder / 'frequency_growth_rate.h5', 'w')
#            file["/ky"] = ky_arr
#            file["/gamma"] = Grate_arr
#            file["/omega"] = Freq_arr
#            file.close()
            
    def save(time_requested, output=None, out_folder=None):
        pass

    def finalize():
        pass
