""" Module containing the contour diagnostics"""
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import putils.averages as averages

from .diagnostic import Diagnostic
from .baseplot import Plotting
from .diagspace import DiagSpace


class DiagContours(Diagnostic):
    """ Diagnostic for contours in the xy and xz plane"""

    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Contours'
        self.tabs = ['fluxtube', 'xglobal']

        self.help_txt = """Plot contours on xy and xz planes
                        \n
                        \nQuantity : quantity to plot
                        \nx ind : index of radial position (def. all)
                        \ny ind : index of binormal position (def. 0)
                        \nz ind : index of parallel position (def. outboard midplane)
                        \nspec: which species to plot (def. all if spec dependent)
                        \nFourier x : spectral in x direction (def. False)
                        \nFourier y : spectral in y direction (def. False)
                        \nSave h5 : save hdf5 file (def. False)
                        \nt avg : time averaged (def. False)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"quant": {'tag': "Quant", 'values': None, 'files': ['mom', 'field']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "yind": {'tag': "y ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None},
                     "f_x": {'tag': "Fourier x", 'values': [False, True]},
                     "f_y": {'tag': "Fourier y", 'values': [False, True]},
                     'save_h5': {'tag': "Save h5", 'values': [False, True]},
                     't_avg': {'tag': "t avg", 'values': [False, True]}, }

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()
        self.contours = {}
        self.contours_parallel = {}

    def set_options(self, run_data, specnames=None):

        if self.opts['quant']['value'] is None:
            raise RuntimeError("No quantities given for contours")

        # parallel position, unset mean outboard midplane, -1 all
        self.z_ind = self.opts['zind']['value']
        self.z_avg = False
        if self.zind == -1:
            self.z_avg = True

        # radial position, unset or -1 means all
        self.x_ind = self.opts['xind']['value']
        self.x_avg = False
        if self.x_ind == -1:
            self.x_avg = True

        # radial position, unset or -1 means all
        self.y_ind = self.opts['yind']['value']
        self.y_avg = False
        if self.y_ind == -1:
            self.y_avg = True

        # Fourier in x
        self.x_fourier = self.opts['f_x']['value']
        # Fourier in y
        self.y_fourier = self.opts['f_y']['value']

        self.run_data = run_data

        # This is special since we dont save stuff by default, so just do what we need
        self.get_spec_from_opts()

        # toggle the reader
        self.get_needed_vars()

        # cast the output as a dictionary of lists to ease the rest
        #        TODO there is probably a best structure for this....
        self.contours = {}
        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        self.contours[quant] = []
                    else:
                        for spec in self.specnames:
                            self.contours[quant + '#' + spec] = []

        return self.needed_vars

    def execute(self, data, parameters, geometry, spatialgrid,  step):
        """ not much to do other than appending data """

        # loop over files
        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                # loop over quaitites in that file
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        # no species dependency
                        data_in = getattr(data.field,'quant')(step.time, step.field, parameters)
                        data_in = self._apply_fouriertransforms(data_in, geometry)
                        self.contours[quant].append(data_in)
                    else:
                        # spec dependent
                        for spec in self.specnames:
                            data_in = getattr(getattr(data, file + '_' + spec), quant)(
                                    step.time, step.field, parameters)

                            data_in = self._apply_fouriertransforms(data_in, geometry)
                            self.contours[quant + '#' + spec].append(data_in)

    def plot(self, time_requested, output=None, out_folder=None):
        """ Not much to explain """

        plotbase = Plotting()
        if self.run_data.is3d:
            plotbase.titles.update(
                    {"phi": r"$\phi$", "n": r"$n$", "u_par": r"u_{//}", "T_par": r"T_{//}",
                     "T_perp": r"T_{\perp}", "Q_es": r"$Q_{es}$", "Q_em": r"$Q_{em}$",
                     "Gamma_es": r"$\Gamma_{es}$", "Gamma_em": r"$\Gamma_{em}$"})
        else:
            plotbase.titles.update(
                    {"phi": r"$\phi$", "A_par": r"$A_{//}$", "B_par": r"$B_{//}$", "dens": r"$n$",
                     "T_par": r"T_{//}", "T_perp": r"T_{\perp}", "u_par": r"u_{//}",
                     "q_par": r"q_{//}", "q_perp": r"q_{\perp}"})

        z_lbl = r"$z$"
        z = self.run_data.spatialgrid.z

        if self.opts['f_x']['value']:
            x_lbl = r"$k_x\rho_{ref}$"
            x = self.run_data.spatialgrid.kx_fftorder
        else:
            x_lbl = r"$x/\rho_{ref}$"
            x = self.run_data.spatialgrid.x

        if self.opts['f_y']['value']:
            y_lbl = r"$k_y\rho_{ref}$"
            y = self.run_data.spatialgrid.ky
        else:
            y_lbl = r"$y/\rho_{ref}$"
            y = self.run_data.spatialgrid.y

        is_f = self.opts['f_x']['value'] or self.opts['f_y']['value']

        if self.opts['t_avg']['value']:
            # loop over file
            for quant in self.contours:
                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                fig = plt.figure()
                ax = fig.add_subplot(111)
                plotbase.plot_contour_quant(ax, fig, x, y,
                                            averages.mytrapz(self.contours[quant], time_requested),
                                            is_f, x_lbl, y_lbl, ttl, is_bidirect=True)

        else:
            for quant in self.contours:
                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                fig = plt.figure()
                ax = fig.add_subplot(111)
                plotbase.plot_contour_quant_timeseries(ax, fig, x, y, self.contours[quant], is_f,
                                                       time_requested, x_lbl, y_lbl, ttl, is_bidirect=True)

                fig = plt.figure()
                ax = fig.add_subplot(111)
                print(np.size(self.contours_parallel[quant]))
                plotbase.plot_contour_quant_timeseries(ax, fig, x, z, self.contours_parallel[quant], is_f,
                                                       time_requested, x_lbl, z_lbl, ttl, is_bidirect=True)

        plt.show()

    def _apply_foutier_Transforms(self, data, geometry):
        
