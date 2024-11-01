# -*- coding: utf-8 -*-

from tkinter import END
import h5py
import matplotlib.pyplot as plt
import numpy as np
import ..utils.aux_func as aux_func
import ..utils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagAmplitudeSpectragene3d(Diagnostic):

    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Amplitude spectra'
        self.tabs = ['GENE3D']

        self.help_txt = """Plot amplitude spectra in ky space,
                        \naveraged over the remaining coordinates and times.
                        \n
                        \nQuantity : quantity to plot
                        \nspec: which species to plot (def. all if spec dependent)
                        \nx ind : comma separated radial averaged interval in x/a (e.g. 0.4,0.6),
                        \nz ind : comma separated z interval (e.g., -3,3), default all range
                        default all range
                        \nSave h5 : save hdf5 file (def. True)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"quant": {'tag': "Quant", 'values': None, 'files': ['mom', 'field']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None},
                     'save_h5': {'tag': "Save h5", 'values': [True, False]}, }

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, specnames):

        if self.opts['quant']['value'] is None:
            raise RuntimeError("No quantities given for contours")

        # radial position, unset or -1 means all
        xind = self.opts['xind']['value']
        if not xind or xind == -1:
            self.xind = 0, 100  # this will choose the minimum and maximum values
        else:
            self.xind = xind.split(',')
        self.xind_min, self.xind_max = aux_func.find_nearest_points(run_data.spatialgrid.x_a,
                                                                    float(self.xind[0]),
                                                                    float(self.xind[1]))

        # z position, unset or -1 means all
        zind = self.opts['zind']['value']
        if not zind or zind == -1:
            self.zind = -100, 100  # this will choose the minimum and maximum values
        else:
            self.zind = zind.split(',')
        self.zind_min, self.zind_max = aux_func.find_nearest_points(run_data.spatialgrid.z,
                                                                    float(self.zind[0]),
                                                                    float(self.zind[1]))

        self.geom = run_data.geometry
        self.run_data = run_data

        self.myquant = self.opts['quant']['value']

        # This is special since we dont save stuff by default, so just do what we need
        self.get_spec_from_opts()

        # toggle the reader
        self.get_needed_vars()
        self.amplitude_ky = {}

        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        self.amplitude_ky[quant] = []
                    else:
                        for spec in self.specnames:
                            self.amplitude_ky[quant + '#' + spec] = []

        return self.needed_vars

    def execute(self, data, step):

        for file in self.needed_vars.keys():
            # loop over quaitites in that file
            for quant in self.needed_vars[file].keys():
                # loop over quaitites in that file
                if self.needed_vars[file][quant]:

                    if file == 'field':
                        # no species dependency
                        data_in = getattr(getattr(data, file), quant)(step.time,
                                                                      getattr(step, file))

                        temp = np.absolute(np.fft.fft(data_in, axis=1)/self.run_data.pnt.ny0) ** 2
                        jac_xz = np.mean(self.geom.jacobian.T, axis=1)
                        jaco3d_xz = np.broadcast_to(jac_xz[:, np.newaxis, :], (
                        self.run_data.pnt.nx0, self.run_data.pnt.ny0, self.run_data.pnt.nz0))

                        data_ky = np.average(temp[self.xind_min:self.xind_max + 1, :,
                                             self.zind_min:self.zind_max + 1],
                                             weights=jaco3d_xz[self.xind_min:self.xind_max + 1, :,
                                                     self.zind_min:self.zind_max + 1], axis=(0, 2))

                        self.amplitude_ky[quant].append(data_ky)

                    else:
                        # spec dependent
                        for spec in self.specnames:

                            data_in = getattr(getattr(data, file + '_' + spec), quant)(step.time,
                                                                                       getattr(step,
                                                                                               file))

                            temp = np.absolute(
                                np.fft.fft(data_in, axis=1)/self.run_data.pnt.ny0) ** 2
                            jac_xz = np.mean(self.geom.jacobian.T, axis=1)
                            jaco3d_xz = np.broadcast_to(jac_xz[:, np.newaxis, :], (
                            self.run_data.pnt.nx0, self.run_data.pnt.ny0, self.run_data.pnt.nz0))

                            data_ky = np.average(temp[self.xind_min:self.xind_max + 1, :,
                                                 self.zind_min:self.zind_max + 1],
                                                 weights=jaco3d_xz[self.xind_min:self.xind_max + 1,
                                                         :, self.zind_min:self.zind_max + 1],
                                                 axis=(0, 2))

                            self.amplitude_ky[quant + '#' + spec].append(data_ky)

    def plot(self, time_requested, output=None, out_folder=None):

        if output:
            output.info_txt.insert(END, "Amplitude specta:\n")

        self.plotbase = Plotting()
        self.plotbase.titles.update(
                {"phi": r"$\phi$", "n": r"$n$", "u_par": r"u_{//}", "T_par": r"T_{//}",
                 "T_perp": r"T_{\perp}", "Q_es": r"$Q_{es}$", "Q_em": r"$Q_{em}$",
                 "Gamma_es": r"$\Gamma_{es}$", "Gamma_em": r"$\Gamma_{em}$"})

        ky = self.run_data.spatialgrid.ky
        ny0_kymax = int(self.run_data.pnt.ny0/2)

        text_x = 'Avg. over x = [' + '{:.1f}'.format(
                self.run_data.spatialgrid.x_a[self.xind_min]) + ',' + '{:.1f}'.format(
                self.run_data.spatialgrid.x_a[self.xind_max - 1]) + ']  '

        for quant in self.amplitude_ky:

            ind_str = quant.find('#')
            if ind_str == -1:
                ttl = self.plotbase.titles[quant]
            else:
                ttl = self.plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

            amplitude_ky = averages.mytrapz(self.amplitude_ky[quant], time_requested)

            fig = plt.figure(figsize=(15, 10), dpi=100)

            ax_1 = fig.add_subplot(1, 3, 1)
            ax_1.loglog(ky[0:ny0_kymax], amplitude_ky[0:ny0_kymax])
            ax_1.set_xlabel(r"$k_y$")
            ax_1.set_ylabel(ttl)

            ax_2 = fig.add_subplot(1, 3, 2)
            ax_2.plot(ky[0:ny0_kymax], amplitude_ky[0:ny0_kymax])
            ax_2.set_xlabel(r"$k_y$")
            ax_2.set_ylabel(ttl)

            ax_3 = fig.add_subplot(1, 3, 3)
            ax_3.semilogx(ky[0:ny0_kymax], ky[0:ny0_kymax]*amplitude_ky[0:ny0_kymax])
            ax_3.set_xlabel(r"$k_y$")
            ax_3.set_ylabel(r"$k_y$" + ttl)

            fig.suptitle(text_x)
            fig.tight_layout()
            fig.show()

            if self.opts['save_h5']['value']:
                file = h5py.File(out_folder/'amplitude_spectra_{}.h5'.format(quant), 'w')
                file["/ky"] = ky
                file["/" + self.myquant] = self.amplitude_ky[quant]
                file.close()
