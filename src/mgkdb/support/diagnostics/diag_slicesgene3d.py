# -*- coding: utf-8 -*-

from tkinter import END

import h5py
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

import ..utils.aux_func as aux_func
import ..utils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagSlicesgene3d(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Slices'
        self.tabs = ['GENE3D']
        self.help_txt = """Slices in different dimensions
        \n
        \nx ind : comma separated radial interval in x/a (e.g. 0.4,0.6), default all range
        \ny ind : comma separated y interval in terms of larmor radious (e.g. -10,10),
        default all range
        \nz ind : comma separated z interval (e.g., -3,3), default all range
        \nFourier x : spectral in x direction (def. False)
        \nFourier y : spectral in y direction (def. False)
        \nSquare value : square quantity (def. False)
        \nAbs. value : absolute value (def. False)
        \nt avg : time averaged (def. False)
        \nSave h5 : save hdf5 file (def. True)
        \nSave pdf : save pdf file (def. False)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"quant": {'tag': "Quant", 'values': None, 'files': ['mom', 'field']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "yind": {'tag': "y ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None},
                     "f_x": {'tag': "Fourier x", 'values': [False, True]},
                     "f_y": {'tag': "Fourier y", 'values': [False, True]},
                     "abs": {'tag': "Abs. value", 'values': [False, True]},
                     "square": {'tag': "square value", 'values': [False, True]},
                     't_avg': {'tag': "t avg", 'values': [False, True]},
                     'save_h5': {'tag': "Save h5", 'values': [True, False]},
                     "save_pdf": {'tag': 'Save pdf', 'values': [False, True]}}

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

        # z position, unset or -1 means all
        zind = self.opts['zind']['value']
        if not zind or zind == -1:
            self.zind = -100, 100  # this will choose the minimum and maximum values
        else:
            self.zind = zind.split(',')
        self.zind_min, self.zind_max = aux_func.find_nearest_points(run_data.spatialgrid.z, float(self.zind[0]), float(self.zind[1]))
        # Fourier in x
        self.x_fourier = self.opts['f_x']['value']

        # Fourier in y
        self.y_fourier = self.opts['f_y']['value']

        self.run_data = run_data

        self.get_spec_from_opts()

        self.geom = run_data.geometry

        self.get_needed_vars()

        self.slice_xy = {}
        self.slice_xz = {}
        self.slice_yz = {}
        self.slice_x = {}
        self.slice_y = {}
        self.slice_z = {}

        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file].keys():
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        self.slice_xy[quant] = []
                        self.slice_xz[quant] = []
                        self.slice_yz[quant] = []
                        self.slice_x[quant] = []
                        self.slice_y[quant] = []
                        self.slice_z[quant] = []
                    else:
                        for spec in self.specnames:
                            self.slice_xz[quant + '#' + spec] = []
                            self.slice_xy[quant + '#' + spec] = []
                            self.slice_yz[quant + '#' + spec] = []
                            self.slice_x[quant + '#' + spec] = []
                            self.slice_y[quant + '#' + spec] = []
                            self.slice_z[quant + '#' + spec] = []

        return self.needed_vars

    def execute(self, data, step):
        """ not much to do other than appending data """

        # loop over files
        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                # loop over quaitites in that file
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        # no species dependency
                        data_in = getattr(getattr(data, file), quant)(step.time, getattr(step, file))

                        if self.x_fourier:
                            if self.y_fourier:
                                data_xyz = np.fft.fftshift(np.fft.fft2(data_in, axes=(0, 1))*np.conj(np.fft.fft2(self.geom.jacobian.T, axes=(0, 1))), axes=(0, 1))/np.mean(self.geom.jacobian.T)/self.run_data.pnt.nx0**2/self.run_data.pnt.ny0**2
                            else:
                                data_xyz = np.fft.fftshift(np.fft.fft(data_in, axis=0)*np.conj(np.fft.fft(self.geom.jacobian.T, axis=0)), axis=0)/np.mean(self.geom.jacobian.T)/self.run_data.pnt.nx0**2
                        else:
                            if self.y_fourier:
                                data_xyz = np.fft.fftshift(np.fft.fft(data_in, axis=1)*np.conj(np.fft.fft(self.geom.jacobian.T, axis=1)), axis=1)/np.mean(self.geom.jacobian.T)/self.run_data.pnt.ny0**2
                            else:
                                data_xyz = data_in*self.geom.jacobian.T/np.mean(self.geom.jacobian.T)

                        if self.opts['square']['value']: data_xyz = np.absolute(data_xyz)**2

                        data_xy = np.average(data_xyz[:, :, self.zind_min:self.zind_max+1], axis=2)
                        data_xz = np.average(data_xyz[:, self.yind_min:self.yind_max+1, :], axis=1)
                        data_yz = np.average(data_xyz[self.xind_min:self.xind_max+1, :, :], axis=0)

                        data_x = np.average(data_xyz[:, self.yind_min: self.yind_max+1, self.xind_min:self.xind_max+1], axis=(1, 2))
                        data_y = np.average(data_xyz[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1], axis=(0, 2))
                        data_z = np.average(data_xyz[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1, :], axis=(0, 1))

                        self.slice_xy[quant].append(data_xy)
                        self.slice_xz[quant].append(data_xz)
                        self.slice_yz[quant].append(data_yz)
                        self.slice_x[quant].append(data_x)
                        self.slice_y[quant].append(data_y)
                        self.slice_z[quant].append(data_z)

                    else:
                        # spec dependent
                        for spec in self.specnames:

                            data_in = getattr(getattr(data, file + '_' + spec), quant)(step.time, getattr(step, file))

                            if self.x_fourier:
                                if self.y_fourier:
                                    data_xyz = np.fft.fftshift(np.fft.fft2(data_in, axes=(0, 1))*np.conj(np.fft.fft(self.geom.jacobian.T, axes=(0, 1))), axes=(0, 1))/np.mean(self.geom.jacobian.T)/self.run_data.pnt.nx0**2/self.run_data.pnt.ny0**2
                                else:
                                    data_xyz = np.fft.fftshift(np.fft.fft(data_in, axis=0)*np.conj(np.fft.fft(self.geom.jacobian.T, axis=0)), axis=0)/np.mean(self.geom.jacobian.T)/self.run_data.pnt.nx0**2
                            else:
                                if self.y_fourier:
                                    data_xyz = np.fft.fftshift(np.fft.fft(data_in, axis=1)*np.conj(np.fft.fft(self.geom.jacobian.T, axis=1)), axis=1)/np.mean(self.geom.jacobian.T)/self.run_data.pnt.ny0**2
                                else:
                                    data_xyz = data_in*self.geom.jacobian.T/np.mean(self.geom.jacobian.T)

                            if self.opts['square']['value']: data_xyz = np.absolute(data_xyz)**2

                            data_xy = np.average(data_xyz[:, :, self.zind_min:self.zind_max+1], axis=2)
                            data_xz = np.average(data_xyz[:, self.yind_min:self.yind_max+1, :], axis=1)
                            data_yz = np.average(data_xyz[self.xind_min:self.xind_max+1, :, :], axis=0)

                            data_x = np.average(data_xyz[:, self.yind_min: self.yind_max+1, self.xind_min:self.xind_max+1], axis=(1, 2))
                            data_y = np.average(data_xyz[self.xind_min:self.xind_max+1, :, self.zind_min:self.zind_max+1], axis=(0, 2))
                            data_z = np.average(data_xyz[self.xind_min:self.xind_max+1, self.yind_min:self.yind_max+1, :], axis=(0, 1))

                            self.slice_xy[quant + '#' + spec].append(data_xy)
                            self.slice_xz[quant + '#' + spec].append(data_xz)
                            self.slice_yz[quant + '#' + spec].append(data_yz)
                            self.slice_x[quant + '#' + spec].append(data_x)
                            self.slice_y[quant + '#' + spec].append(data_y)
                            self.slice_z[quant + '#' + spec].append(data_z)


    def plot(self, time_requested, output=None, out_folder=None):

        if output:
            output.info_txt.insert(END, "Slice:\n")

        plotbase = Plotting()
        plotbase.titles.update(
                {"phi": r"$\phi$", "n": r"$n$", "u_par": r"u_{//}", "T_par": r"T_{//}",
                 "T_perp": r"T_{\perp}", "Q_es": r"$Q_{es}$", "Q_em": r"$Q_{em}$",
                 "Gamma_es": r"$\Gamma_{es}$", "Gamma_em": r"$\Gamma_{em}$"})

        def plot_a_map(ax, x, y, f, is_f, x_lbl, y_lbl, ttl):
            cm1 = ax.pcolormesh(x, y, np.abs(np.squeeze(f)).T if is_f else np.squeeze(f).T)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            cm1.cmap_bidirect

        def plot_a_quant(ax, x, data, is_complex, xlabel=None, title=None):
            ax.plot(x, np.absolute(data.T) if is_complex else data.T, color='b')
            ax.set_rasterization_zorder(z=-10)
            if xlabel:
                ax.set_xlabel(xlabel)
            if title:
                ax.set_title(title)

        if self.opts['f_x']['value']:
            x_lbl = r"$k_x\rho_{ref}$"
            x = np.fft.fftshift(self.run_data.spatialgrid.kx_fftorder)
            x_p = np.fft.fftshift(self.run_data.spatialgrid.kx_fftorder)

        else:
            x_lbl = r"$x/a$"
            x = self.run_data.spatialgrid.x_a
            x_p = x

        if self.opts['f_y']['value']:
            y_lbl = r"$k_y\rho_{ref}$"
            y = np.fft.fftshift(self.run_data.spatialgrid.ky)
            y_p = np.fft.fftshift(self.run_data.spatialgrid.ky)

        else:
            y_lbl = r"$y/\rho_{ref}$"
            y = self.run_data.spatialgrid.y
            y_p = y

        is_f = self.opts['f_x']['value'] or self.opts['f_y']['value'] or self.opts['abs']['value']


        z_lbl = r"$z/L_{ref}$"
        z = self.run_data.spatialgrid.z

        text_x = 'Avg. over x = [' + '{:.1f}'.format(self.run_data.spatialgrid.x_a[self.xind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.x_a[self.xind_max-1])+ ']  '
        text_y = 'y = [' + '{:.1f}'.format(self.run_data.spatialgrid.y[self.yind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.y[self.yind_max-1])+ ']  '
        text_z = 'z = [' + '{:.1f}'.format(self.run_data.spatialgrid.z[self.zind_min]) + ',' + '{:.1f}'.format(self.run_data.spatialgrid.z[self.zind_max-1])+ ']'
        text = text_x + text_y + text_z

        if self.opts['t_avg']['value']:
            # loop over file
            for quant in self.slice_xy:

                if self.opts['save_pdf']['value']:
                    pp2d = PdfPages(out_folder / 'slices2d_{}.pdf'.format(quant))
                    pp1d = PdfPages(out_folder / 'slices1d_{}.pdf'.format(quant))
                    plt.ioff()

                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                fig = plt.figure(figsize=(15, 10))
                ax_1 = fig.add_subplot(1, 3, 1)
                plotbase.plot_contour_quant(ax_1, fig, x, y, averages.mytrapz(self.slice_xy[quant], time_requested), is_f, x_lbl, y_lbl, ttl)
                ax_2 = fig.add_subplot(1, 3, 2)
                plotbase.plot_contour_quant(ax_2, fig, x, z, averages.mytrapz(self.slice_xz[quant], time_requested), is_f, x_lbl, z_lbl, ttl)
                ax_3 = fig.add_subplot(1, 3, 3)
                plotbase.plot_contour_quant(ax_3, fig, y, z, averages.mytrapz(self.slice_yz[quant], time_requested), is_f, y_lbl, z_lbl, ttl)
                fig.suptitle(text)

                if self.opts['save_pdf']['value']:
                    fig.savefig(pp2d, format='pdf', bbox_inches='tight')
                    pp2d.close()
                else:
                    fig.show()

                fig = plt.figure(figsize=(15, 10))
                ax_1 = fig.add_subplot(1, 3, 1)
                plotbase.plot_1d_quant(ax_1, fig, x_p, averages.mytrapz(self.slice_x[quant], time_requested), is_f, x_lbl, ttl)
                ax_2 = fig.add_subplot(1, 3, 2)
                plotbase.plot_1d_quant(ax_2, fig, y_p, averages.mytrapz(self.slice_y[quant], time_requested), is_f, y_lbl, ttl)
                ax_3 = fig.add_subplot(1, 3, 3)
                plotbase.plot_1d_quant(ax_3, fig, z, averages.mytrapz(self.slice_z[quant], time_requested), is_f, z_lbl, ttl)
                fig.suptitle(text)

                if self.opts['save_pdf']['value']:
                    fig.savefig(pp1d, format='pdf', bbox_inches='tight')
                    pp1d.close()
                else:
                    fig.show()

                if self.opts['save_h5']['value']:
                    file = h5py.File(out_folder / 'slices_{}.h5'.format(quant), 'w')
                    file["/x"] = x
                    file["/y"] = y
                    file["/z"] = z
                    file["/" + quant + "_xy"] = averages.mytrapz(self.slice_xy[quant], time_requested)
                    file["/" + quant + "_xz"] = averages.mytrapz(self.slice_xz[quant], time_requested)
                    file["/" + quant + "_yz"] = averages.mytrapz(self.slice_yz[quant], time_requested)
                    file["/" + quant + "_x"] = averages.mytrapz(self.slice_x[quant], time_requested)
                    file["/" + quant + "_y"] = averages.mytrapz(self.slice_y[quant], time_requested)
                    file["/" + quant + "_z"] = averages.mytrapz(self.slice_z[quant], time_requested)
                    file.close()

        else:

            for quant in self.slice_xy:

                ind_str = quant.find('#')
                if ind_str == -1:
                    ttl = plotbase.titles[quant]
                else:
                    ttl = plotbase.titles[quant[0:ind_str]] + " " + quant[ind_str + 1:]

                if self.opts['save_pdf']['value']:

                    pp2d = PdfPages(out_folder / 'slices2d_{}.pdf'.format(quant))
                    pp1d = PdfPages(out_folder / 'slices1d_{}.pdf'.format(quant))
                    plt.ioff()
                    for i_t, tm in enumerate(time_requested):

                        fig = plt.figure(figsize=(15, 10))
                        ax_1 = fig.add_subplot(1, 3, 1)
                        plot_a_map(ax_1, x, y, self.slice_xy[quant][i_t], is_f, x_lbl, y_lbl, ttl + ', t = {:.2f}'.format(tm))
                        ax_2 = fig.add_subplot(1, 3, 2)
                        plot_a_map(ax_2, x, z, self.slice_xz[quant][i_t], is_f, x_lbl, z_lbl, ttl + ', t = {:.2f}'.format(tm))
                        ax_3 = fig.add_subplot(1, 3, 3)
                        plot_a_map(ax_3, y, z, self.slice_yz[quant][i_t], is_f, y_lbl, z_lbl, ttl + ', t = {:.2f}'.format(tm))
                        fig.suptitle(text)
                        fig.savefig(pp2d, format='pdf', bbox_inches='tight')

                        fig = plt.figure(figsize=(15, 10))
                        ax_1 = fig.add_subplot(1, 3, 1)
                        plot_a_quant(ax_1, x_p, self.slice_x[quant][i_t], is_f, x_lbl, ttl + ', t = {:.2f}'.format(tm))
                        ax_2 = fig.add_subplot(1, 3, 2)
                        plot_a_quant(ax_2, y_p, self.slice_y[quant][i_t], is_f, y_lbl, ttl + ', t = {:.2f}'.format(tm))
                        ax_3 = fig.add_subplot(1, 3, 3)
                        plot_a_quant(ax_3, z, self.slice_z[quant][i_t], is_f, z_lbl, ttl + ', t = {:.2f}'.format(tm))
                        fig.suptitle(text)
                        fig.savefig(pp1d, format='pdf', bbox_inches='tight')
                    pp2d.close()
                    pp1d.close()

                else:

                    fig = plt.figure(figsize=(15, 10))
                    ax_1 = fig.add_subplot(1, 3, 1)
                    plotbase.plot_contour_quant_timeseries(ax_1, fig, x, y, self.slice_xy[quant],
                                        is_f, time_requested, x_lbl, y_lbl, ttl, True)
                    ax_2 = fig.add_subplot(1, 3, 2)
                    plotbase.plot_contour_quant_timeseries(ax_2, fig, x, z, self.slice_xz[quant],
                                        is_f, time_requested, x_lbl, z_lbl, ttl, True)
                    ax_3 = fig.add_subplot(1, 3, 3)
                    plotbase.plot_contour_quant_timeseries(ax_3, fig, y, z, self.slice_yz[quant],
                                        is_f, time_requested, y_lbl, z_lbl, ttl, True)
                    fig.suptitle(text)
                    fig.show()


                    fig = plt.figure(figsize=(15, 10))
                    ax_1 = fig.add_subplot(1, 3, 1)
                    plotbase.plot_1d_quant_timeseries(ax_1, fig, x_p, self.slice_x[quant],
                                                      is_f, time_requested, x_lbl, ttl)
                    ax_2 = fig.add_subplot(1, 3, 2)
                    plotbase.plot_1d_quant_timeseries(ax_2, fig, y_p, self.slice_y[quant],
                                                      is_f, time_requested, y_lbl, ttl)
                    ax_3 = fig.add_subplot(1, 3, 3)
                    plotbase.plot_1d_quant_timeseries(ax_3, fig, z, self.slice_z[quant],
                                                      is_f, time_requested, z_lbl, ttl)
                    fig.suptitle(text)

                    fig.show()
