# -*- coding: utf-8 -*-

from tkinter import END

import h5py
import matplotlib.pyplot as plt
import numpy as np

import ..utils.aux_func as aux_func
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagTimetracesgene3d(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Time Traces'
        self.tabs = ['GENE3D']
        self.help_txt = """Time traces of different quantities
        \n
        \nx ind : comma separated radial interval in x/a (e.g. 0.4,0.6), default all range
        \ny ind : comma separated y interval in terms of larmor radious (e.g. -10,10),
        default all range
        \nky ind : comma separated |ky| fourier modes (e.g 0.5,1.0), default 0.0, 0.0
        \nz ind : comma separated z interval (e.g., -3,3), default all range
        \nLog : log scale, default true
        \nSave h5 : save hdf5 file, only for time average plot (def. True)"""
        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"quant": {'tag': "Quant", 'values': None, 'files': ['mom', 'field']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "yind": {'tag': "y ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None},
                     "kyind": {'tag': "ky ind", 'values': None},
                     "log": {'tag': "Log", 'values': [False,True]},
                     "save_h5": {'tag': 'Save h5', 'values': [True, False]}}
        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, specnames=None):

        if self.opts['quant']['value'] is None:
            raise RuntimeError("No quantities given for contours")

        # radial position, unset or -1 means all
        xind = self.opts['xind']['value']
        if not xind or xind == -1:
            self.xind = 0, 100  # this will choose the minimum and maximum values
        else:
            self.xind = xind.split(',')
        self.xind_min, self.xind_max = aux_func.find_nearest_points(run_data.spatialgrid.x_a, float(self.xind[0]), float(self.xind[1]))

        # y position, unset or -1 means all
        yind = self.opts['yind']['value']
        if not yind or yind == -1:
            self.yind = -1000, 1000  # this will choose the minimum and maximum values
        else:
            self.yind = yind.split(',')
        self.yind_min, self.yind_max = aux_func.find_nearest_points(run_data.spatialgrid.y, float(self.yind[0]), float(self.yind[1]))

        kyind = self.opts['kyind']['value']
        if not kyind or kyind == -1:
            self.kyind = 0.0, 0.0
        else:
            self.kyind = kyind.split(',')
        self.kyind_min = aux_func.find_nearest(run_data.spatialgrid.ky, float(self.kyind[0]))
        self.kyind_max = aux_func.find_nearest(run_data.spatialgrid.ky, float(self.kyind[1]))

        # z position, unset or -1 means all
        zind = self.opts['zind']['value']
        if not zind or zind == -1:
            self.zind = -100, 100  # this will choose the minimum and maximum values
        else:
            self.zind = zind.split(',')
        self.zind_min, self.zind_max = aux_func.find_nearest_points(run_data.spatialgrid.z, float(self.zind[0]), float(self.zind[1]))

        self.myquant = self.opts['quant']['value']

        self.run_data = run_data
        self.get_spec_from_opts()
        self.geom = run_data.geometry
        self.get_needed_vars()

        self.time_traces = {}
        self.time_traces_ky = {}

        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        self.time_traces[quant] = []
                        self.time_traces_ky[quant] = []
                    else:
                        for spec in self.specnames:
                            self.time_traces[quant + '#' + spec] = []
                            self.time_traces_ky[quant + '#' + spec] = []

        return self.needed_vars

    def execute(self, data, step, last_step):
        """ not much to do other than appending data """

        # loop over files
        for file in self.needed_vars.keys():
            # loop over quaitites in that file
            for quant in self.needed_vars[file].keys():
                # loop over quaitites in that file
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        # no species dependency
                        data_in = getattr(getattr(data, file), quant)(step.time, getattr(step, file))

                        data_t = np.average(data_in[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1,
                                               self.zind_min:self.zind_max+1], weights=self.geom.jacobian.T[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1,
                                                       self.zind_min:self.zind_max+1])

                        temp = np.absolute(np.fft.fftshift(np.fft.fft(data_in, axis=1), axes=1)/self.run_data.pnt.ny0)**2
                        jac_xz = np.mean(self.geom.jacobian.T, axis=1)
                        jaco3d_xz = np.broadcast_to(jac_xz[:, np.newaxis, :], (self.run_data.pnt.nx0, self.run_data.pnt.ny0, self.run_data.pnt.nz0))

                        data_ky = np.average(temp[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1],
                                    weights=jaco3d_xz[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1], axis=(0, 2))


                        self.time_traces[quant].append(data_t)
                        self.time_traces_ky[quant].append(data_ky)

                    else:
                        # spec dependent
                        for spec in self.specnames:

                            data_in = getattr(getattr(data, file + '_' + spec), quant)(step.time, getattr(step, file))

                            data_t = np.average(data_in[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1,
                                               self.zind_min:self.zind_max+1], weights=self.geom.jacobian.T[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1,
                                                       self.zind_min:self.zind_max+1])

                            temp = np.absolute(np.fft.fftshift(np.fft.fft(data_in, axis=1), axes=1)/self.run_data.pnt.ny0)**2
                            jac_xz = np.mean(self.geom.jacobian.T, axis=1)
                            jaco3d_xz = np.broadcast_to(jac_xz[:, np.newaxis, :], (self.run_data.pnt.nx0, self.run_data.pnt.ny0, self.run_data.pnt.nz0))

                            data_ky = np.average(temp[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1],
                                    weights=jaco3d_xz[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1], axis=(0, 2))

                            self.time_traces[quant + '#' + spec].append(data_t)
                            self.time_traces_ky[quant + '#' + spec].append(data_ky)


    def plot(self, time_requested, output=None, out_folder=None):

        if output:
            output.info_txt.insert(END, "Time traces:\n")

        self.plotbase = Plotting()
        self.plotbase.titles.update(
                {"phi": r"$\phi$", "n": r"$n$", "u_par": r"$u_{\parallel}$", "T_par": r"$T_{\parallel}$",
                 "T_per": r"$T_{\perp}$", "Q_es": r"$Q_{es}$", "Q_em": r"$Q_{em}$",
                 "Gamma_es": r"$\Gamma_{es}$", "Gamma_em": r"$\Gamma_{em}$"})

        x_lbl = r'$t\; [c_{ref}/L_{ref}]$'

            # loop over file
        for quant in self.time_traces:

            ind_str = quant.find('#')
            if ind_str == -1:
                ttl = self.plotbase.titles[quant]
            else:
                ttl = self.plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

            fig = plt.figure(figsize=(15, 10), dpi=100)

            text_x = 'Avg. over x = [' + '{:.1f}'.format(self.run_data.spatialgrid.x_a[self.xind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.x_a[self.xind_max-1])+ ']  '
            text_y = 'y = [' + '{:.1f}'.format(self.run_data.spatialgrid.y[self.yind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.y[self.yind_max-1])+ ']  '
            text_z = 'z = [' + '{:.1f}'.format(self.run_data.spatialgrid.z[self.zind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.z[self.zind_max-1])+ ']'

            if self.opts['save_h5']['value']:
                file = h5py.File(out_folder / 'time_traces_{}.h5'.format(quant), 'w')
                file["/time"] = time_requested
                file["/ky"] = self.run_data.spatialgrid.ky
                file["/"+self.myquant] = self.time_traces[quant]
                file["/"+self.myquant + '_ky'] = self.time_traces_ky[quant]
                file.close()

            ax_1 = fig.add_subplot(1, 2, 1)
            if self.opts['log']['value']:
                ax_1.semilogy(time_requested, self.time_traces[quant])
            else:
                ax_1.plot(time_requested, self.time_traces[quant])
            average_quant = np.average(self.time_traces[quant])
            text_avg = ' Avg. ' + ttl +f' over time window = {average_quant:.2f}'
            ax_1.axhline(y=average_quant, color='k', linestyle=':')
            ax_1.set_xlabel(x_lbl)
            ax_1.set_title(ttl)

            ax_1 = fig.add_subplot(1, 2, 2)
            y = np.array(self.time_traces_ky[quant])
            for ky in range(0, len(y[0, :])):
                if (np.absolute(self.run_data.spatialgrid.ky[ky]) <= np.absolute(self.run_data.spatialgrid.ky[self.kyind_max])
                       and np.absolute(self.run_data.spatialgrid.ky[ky]) >= np.absolute(self.run_data.spatialgrid.ky[self.kyind_min])):
                    if self.opts['log']['value']:
                        ax_1.semilogy(time_requested, np.absolute(y[:, ky]), label=r'$k_y=$'+ str(self.run_data.spatialgrid.ky[ky]))
                    else:
                        ax_1.plot(time_requested, np.absolute(y[:, ky]), label=r'$k_y=$'+ str(self.run_data.spatialgrid.ky[ky]))
                    ax_1.set_xlabel(x_lbl)
                    ax_1.set_title(r'$|$' + ttl +'$|^2$')
                    ax_1.legend()

            fig.suptitle(text_x + text_y + text_z + text_avg)
            fig.show()
