# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import END
from tkinter import Toplevel, BOTTOM, BOTH, TOP

import h5py
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

import ..utils.aux_func as aux_func
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagChivsGradientgene3d(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Chi vs. Gradient'
        self.tabs = ['GENE3D']
        self.help_txt = """Plots chi vs. gradient
                        \nx ind : comma separated radial interval in terms of minor radious (e.g. 
                        0.4,0.6)
                        \ndefault all range
                        \nSave h5 : save hdf5 file (def. True)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "save_h5": {"tag": "Save h5", "values": [True, False]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, species):

        # radial position, unset or -1 means all
        xind = self.opts['xind']['value']
        if not xind or xind == -1:
            self.xind = 0, 100  # this will choose the minimum and maximum values
        else:
            self.xind = xind.split(',')
        self.xind_min, self.xind_max = aux_func.find_nearest_points(run_data.spatialgrid.x_a,
                                                                    float(self.xind[0]),
                                                                    float(self.xind[1]))

        class ChiStep:
            def __init__(self, specnames):
                for spec in specnames:
                    setattr(self, spec, self.__Chiprofiles())

            class __Chiprofiles:
                def __init__(self):
                    self.omt = []
                    self.omn = []
                    self.chi_es = []

        self.run_data = run_data

        self.geom = run_data.geometry

        self.chi_step = ChiStep(self.specnames)

        self.get_needed_vars(['mom'])

        self.get_spec_from_opts()

        return self.needed_vars

    def execute(self, data, step):

        for ispec, spec in enumerate(self.specnames):

            chi_step = getattr(self.chi_step, spec)

            n = np.average(getattr(getattr(data, 'mom_' + spec), "n")(step.time, step.mom),
                           weights=self.geom.jacobian.T, axis=(1, 2))
            T_par = np.average(getattr(getattr(data, 'mom_' + spec), "T_par")(step.time, step.mom),
                               weights=self.geom.jacobian.T, axis=(1, 2))
            T_per = np.average(getattr(getattr(data, 'mom_' + spec), "T_per")(step.time, step.mom),
                               weights=self.geom.jacobian.T, axis=(1, 2))
            Q_es = np.average(getattr(getattr(data, 'mom_' + spec), "Q_es")(step.time, step.mom),
                              weights=self.geom.jacobian.T, axis=(1, 2))
            T_total = 1/3*T_par + 2/3*T_per

            T0 = self.run_data.profilesdata.T0s[:, ispec]/self.run_data.pars["temp" + spec]/ \
                 self.run_data.pars["Tref"]
            N0 = self.run_data.profilesdata.n0s[:, ispec]/self.run_data.pars["dens" + spec]/ \
                 self.run_data.pars["nref"]

            Temp = T0 + T_total*self.run_data.pnt.rhostar*self.run_data.pnt.minor_r
            Dens = N0 + n*self.run_data.pnt.rhostar*self.run_data.pnt.minor_r

            omt = -np.gradient(np.log(Temp),
                               self.run_data.spatialgrid.x_a)/self.run_data.pnt.minor_r
            omn = -np.gradient(np.log(Dens),
                               self.run_data.spatialgrid.x_a)/self.run_data.pnt.minor_r

            chi_step.chi_es.append(np.mean(Q_es[self.xind_min:self.xind_max + 1]/(
                        Dens[self.xind_min:self.xind_max + 1]*Temp[self.xind_min:self.xind_max + 1]
                        *omt[self.xind_min:self.xind_max + 1])))
            chi_step.omt.append(np.mean(omt[self.xind_min:self.xind_max + 1]))
            chi_step.omn.append(np.mean(omn[self.xind_min:self.xind_max + 1]))

    def plot(self, time_requested, output=None, out_folder=None):

        if output:
            output.info_txt.insert(END, "Chi vs. gradient:\n")

        self.plotbase = Plotting()

        x_lbl = r'$t\; [c_{ref}/L_{ref}]$'
        text_x = ', Avg. over x = [' + '{:.1f}'.format(
                self.run_data.spatialgrid.x_a[self.xind_min]) + ',' + '{:.1f}'.format(
                self.run_data.spatialgrid.x_a[self.xind_max - 1]) + ']  '

        # time averaged values
        for spec in self.specnames:

            spec_chi = getattr(self.chi_step, spec)

            fig = plt.figure(figsize=(15, 10), dpi=100)
            fig.suptitle(r"${}    $".format(spec) + text_x)

            ax_1 = fig.add_subplot(2, 2, 1)
            ax_2 = fig.add_subplot(2, 2, 2)
            ax_3 = fig.add_subplot(2, 2, 3)
            ax_4 = fig.add_subplot(2, 2, 4)

            chi_es = getattr(spec_chi, "chi_es")
            omt = getattr(spec_chi, "omt")
            omn = getattr(spec_chi, "omn")

            ax_1.plot(time_requested, omt)
            ax_1.set_xlabel(x_lbl)
            ax_1.set_ylabel(r"$a/L_{T}$")

            ax_2.plot(time_requested, omn)
            ax_2.set_xlabel(x_lbl)
            ax_2.set_ylabel(r"$a/L_{n}$")

            ax_3.plot(time_requested, chi_es)
            ax_3.set_xlabel(x_lbl)
            ax_3.set_ylabel(r"$<\chi_{es}>_{V}$")

            ax_4.plot(omt, chi_es)
            ax_4.set_xlabel(r'$a/L_{T}$')
            ax_4.set_ylabel(r"$<\chi_{es}>_{V}$")

            # this was an idea, but not sure if it is worh it
            window = Toplevel()
            tk.Tk.wm_title(window, "Chi vs. Gradient")
            ShowThis(window, fig)

        if self.opts['save_h5']['value']:
            file = h5py.File(out_folder/'chi_gradient_vs_time.h5', 'w')
            file["/time"] = time_requested
            file["/omt"] = omt
            file["/omn"] = omn
            file["/chi_es"] = chi_es
            file.close()


class ShowThis:
    def __init__(self, window, f):
        canvas = FigureCanvasTkAgg(f, window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=True)

        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar = NavigationToolbar2Tk(canvas, window)
            toolbar.update()
            canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)
        except:  # TODO Really swallow all exceptions without saying something?
            pass
