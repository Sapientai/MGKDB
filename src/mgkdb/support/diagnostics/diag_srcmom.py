# -*- coding: utf-8 -*-

import h5py
import matplotlib.pyplot as plt
import numpy as np

import ..utils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagSrc(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Sources'
        self.tabs = ['xglobal', "GENE3D"]

        self.help_txt = """ Analyze sources
        \nt avg : time averaged (def. True)
        \nSave h5 : save hdf5 file (def.True) """

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {'t_avg': {'tag': "t avg", 'values': [True, False]},
                     "save_h5": {'tag': 'Save h5', 'values': [True, False]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, specnames=None):
        class SrcStep:
            def __init__(self, specnames, src_types):
                for spec in specnames:
                    for src_type in src_types:
                        setattr(self, spec + src_type, self.__SrcMoms())

            class __SrcMoms:
                def __init__(self):
                    self.M00 = []
                    self.M10 = []
                    self.M22 = []

        self.run_data = run_data

        self.geom = run_data.geometry

        # select which source is active
        self.src_type = []
        if self.run_data.pnt.ck_part > 0.:
            self.src_type.append('ck_part')
        if self.run_data.pnt.ck_heat > 0.:
            self.src_type.append('ck_heat')
        for spec in self.specnames:
            if "src_amp" + spec in self.run_data.pnt:
                #               I think this is wrong
                if self.run_data.pardict["src_amp" + spec] > 0.:
                    self.src_type.append('f0_term')
                    break

        self.src_step = SrcStep(self.specnames, self.src_type)

        # toggle the reader
        self.get_needed_vars(['srcmom'])

        return self.needed_vars

    def execute(self, data, step):
        for spec in self.specnames:
            for src_type in self.src_type:
                src_step = getattr(self.src_step, spec + src_type)

                src_step.M00.append(getattr(getattr(data, 'srcmom_' + spec), src_type + "_M00")(step.time, step.srcmom))
                src_step.M10.append(getattr(getattr(data, 'srcmom_' + spec), src_type + "_M10")(step.time, step.srcmom))
                src_step.M22.append(getattr(getattr(data, 'srcmom_' + spec), src_type + "_M22")(step.time, step.srcmom))

    def plot(self, time_requested, output=None, out_folder=None):

        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl):
            cm1 = ax.pcolormesh(x, y, f)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            fig.colorbar(cm1)

        self.plotbase = Plotting()

        y_lbl = r'x/a'
        x_lbl = r'$t\;c_{ref}/L_{ref}$'

        if len(time_requested) > 1:
            n_col = len(self.src_type)
            for spec in self.specnames:
                fig = plt.figure(figsize=(15, 10), dpi=100)
                for isrc, src in enumerate(self.src_type):
                    ax = fig.add_subplot(3, n_col, 1 + isrc)
                    ttl = r"$" + spec + src.replace('_', '_{') + r"}\; M00$"
                    plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a, np.squeeze(
                        np.array(getattr(getattr(self.src_step, spec + src), 'M00')).T), x_lbl, y_lbl, ttl)
                    ax = fig.add_subplot(3, n_col, 1 + n_col + isrc)
                    ttl = r"$" + spec + src.replace('_', '_{') + r"}\; M10$"
                    plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a, np.squeeze(
                        np.array(getattr(getattr(self.src_step, spec + src), 'M10')).T), x_lbl, y_lbl, ttl)
                    ax = fig.add_subplot(3, n_col, 1 + 2*n_col + isrc)
                    ttl = r"$" + spec + src.replace('_', '_{') + r"}\; M22$"
                    plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a, np.squeeze(
                        np.array(getattr(getattr(self.src_step, spec + src), 'M22')).T), x_lbl, y_lbl, ttl)
                fig.show()

        if self.opts['t_avg']['value']:
            # time averaged values
            for spec in self.specnames:
                fig = plt.figure(figsize=(15, 10), dpi=100)
                ax_M00 = fig.add_subplot(3, 1, 1)
                ax_M10 = fig.add_subplot(3, 1, 2)
                ax_M22 = fig.add_subplot(3, 1, 3)
                M00 = np.zeros(self.run_data.spatialgrid.x.shape)
                M10 = np.zeros(self.run_data.spatialgrid.x.shape)
                M22 = np.zeros(self.run_data.spatialgrid.x.shape)
                for isrc, src in enumerate(self.src_type):

                    tmp = averages.mytrapz(getattr(getattr(self.src_step, spec + src), 'M00'),
                                           time_requested)
                    ax_M00.plot(self.run_data.spatialgrid.x_a, tmp, label=src)
                    M00 = M00 + np.squeeze(tmp)

                    tmp = averages.mytrapz(getattr(getattr(self.src_step, spec + src), 'M10'),
                                           time_requested)
                    ax_M10.plot(self.run_data.spatialgrid.x_a, tmp, label=src)
                    M10 = M10 + np.squeeze(tmp)

                    tmp = averages.mytrapz(getattr(getattr(self.src_step, spec + src), 'M22'),
                                           time_requested)
                    ax_M22.plot(self.run_data.spatialgrid.x_a, tmp, label=src)
                    M22 = M22 + np.squeeze(tmp)

                ax_M00.plot(self.run_data.spatialgrid.x_a, M00.T, label='Total')
                ax_M00.set_xlabel(y_lbl)
                ax_M00.set_ylabel("M00")
                ax_M00.set_title(r"${}$".format(spec))
                ax_M00.legend()
                ax_M10.plot(self.run_data.spatialgrid.x_a, M10.T, label='Total')
                ax_M10.set_xlabel(y_lbl)
                ax_M10.set_ylabel("M10")
                ax_M10.legend()
                ax_M22.plot(self.run_data.spatialgrid.x_a, M22.T, label='Total')
                ax_M22.set_xlabel(y_lbl)
                ax_M22.set_ylabel("M22")
                ax_M22.legend()
                fig.show()

                if self.opts['save_h5']['value']:
                    file = h5py.File(out_folder / 'sources_{}.h5'.format(spec), 'w')
                    file["/x_a"] = self.run_data.spatialgrid.x_a
                    file["/M00"] = M00
                    file["/M10"] = M10
                    file["/M22"] = M22
                    file.close()
