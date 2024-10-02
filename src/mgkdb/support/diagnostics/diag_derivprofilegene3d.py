# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import h5py
import ..utils.averages as averages
from .diagnostic import Diagnostic
from .baseplot import Plotting


class DiagDerivprofilegene3d(Diagnostic):

    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Deriv. Potential'
        self.tabs = ['GENE3D']

        self.help_txt = """Displays the 0th, 1st and 2nd radial derivative of the flux surface
                        \naverage of the potential vs x and t
                        \n
                        \nSave h5 : save hdf5 file (def.True) """

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"save_h5": {'tag': 'Save h5', 'values': [True, False]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, species):
        class Derivphiprof:
            def __init__(self):
                self.Phi = []
                self.Phidx = []
                self.Phi2dx2 = []

        self.geom = run_data.geometry
        self.run_data = run_data
        self.specnames = self.run_data.specnames

        self.derivphiprof_step = Derivphiprof()

        self.get_needed_vars(['field'])

        return self.needed_vars

    def execute(self, data, step):
        phi_yz_av = averages.yz_av3d(getattr(getattr(data, 'field'), "phi")(step.time, step.field),
                                     self.geom)

        x_ind = self.run_data.spatialgrid.x_a/self.run_data.pnt.rhostar

        phi_yz_av_dev = -np.gradient(phi_yz_av, x_ind, axis=0)
        phi_yz_av_2dev = np.gradient(phi_yz_av_dev, x_ind, axis=0)

        self.derivphiprof_step.Phi.append(phi_yz_av)
        self.derivphiprof_step.Phidx.append(phi_yz_av_dev)
        self.derivphiprof_step.Phi2dx2.append(phi_yz_av_2dev)

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
        x_lbl = r'$t\; [c_{ref}/L_{ref}]$'

        fig = plt.figure(figsize=(15, 10), dpi=100)

        ax = fig.add_subplot(1, 3, 1)
        ttl = r"$<\phi>_{FS}$"
        plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a,
                   np.squeeze(np.array(self.derivphiprof_step.Phi).T), x_lbl, y_lbl, ttl)

        ax = fig.add_subplot(1, 3, 2)
        ttl = r"$-\partial_{x} <\phi>_{FS}$"
        plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a,
                   np.squeeze(np.array(self.derivphiprof_step.Phidx).T), x_lbl, y_lbl, ttl)

        ax = fig.add_subplot(1, 3, 3)
        ttl = r"$-\partial^2_x <\phi>_{FS}$"
        plot_a_map(ax, time_requested, self.run_data.spatialgrid.x_a,
                   np.squeeze(np.array(self.derivphiprof_step.Phi2dx2).T), x_lbl, y_lbl, ttl)

        fig.tight_layout()
        fig.show()

        if self.opts['save_h5']['value']:
            file = h5py.File(out_folder / 'deriv_potential.h5', 'w')
            file["/x_a"] = self.run_data.spatialgrid.x_a
            file["/time"] = time_requested
            file["/phi_fs"] = np.array(self.derivphiprof_step.Phi).T
            file["/dphidx_fs"] = np.array(self.derivphiprof_step.Phidx).T
            file["/dphidx2_fs"] = np.array(self.derivphiprof_step.Phi2dx2).T
            file.close()
