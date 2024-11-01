# -*- coding: utf-8 -*-

from tkinter import END

import h5py
import matplotlib.pyplot as plt
import numpy as np

import ..utils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagFluxesgene3d(Diagnostic):

    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Flux profiles'
        self.tabs = ['GENE3D']

        self.help_txt = """Displays radial fluxes vs. x (averaged over time) as well as vs. x
                        \n
                        \nspec: which species to plot (def. all if spec dependent)
                        \nSave h5 : save hdf5 file (def. True)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"spec": {'tag': "Spec", 'values': self.list_specnames()},
                     'save_h5': {'tag': 'Save h5', 'values': [True, False]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, species):

        class FluxStep:
            def __init__(self, specnames, electromagnetic):
                self.__em__ = electromagnetic
                for spec in specnames:
                    setattr(self, spec, self.__SpecSpectra(self.__em__))

            class __SpecSpectra:
                def __init__(self, em):
                    self.Qes = []
                    self.Ges = []

                    if em:
                        self.Qem = []
                        self.Gem = []

        self.geom = run_data.geometry
        self.run_data = run_data
        self.specnames = self.run_data.specnames

        self.flux_step = FluxStep(self.specnames, self.run_data.electromagnetic)

        self.get_needed_vars(['mom'])

        self.get_spec_from_opts()

        return self.needed_vars

    def execute(self, data, step):

        for spec in self.specnames:

            flux_step = getattr(self.flux_step, spec)

            Qes_yz_av = np.average(getattr(getattr(data, 'mom_' + spec), "Q_es")(step.time, step.mom), weights=self.geom.jacobian.T, axis=(1, 2))
            Ges_yz_av = np.average(getattr(getattr(data, 'mom_' + spec), "Gamma_es")(step.time, step.mom), weights=self.geom.jacobian.T, axis=(1, 2))

            flux_step.Qes.append(Qes_yz_av)
            flux_step.Ges.append(Ges_yz_av)

            if self.run_data.electromagnetic:

                Qem_yz_av = np.average(getattr(getattr(data, 'mom_' + spec), "Q_em")(step.time, step.mom), weights=self.geom.jacobian.T, axis=(1, 2))
                Gem_yz_av = np.average(getattr(getattr(data, 'mom_' + spec), "Gamma_em")(step.time, step.mom), weights=self.geom.jacobian.T, axis=(1, 2))

                flux_step.Qem.append(Qem_yz_av)
                flux_step.Gem.append(Gem_yz_av)

    def plot(self, time_requested, output=None, out_folder=None):

        if output:
            output.info_txt.insert(END, "Radial fluxes:\n")

        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl):
            cm1 = ax.pcolormesh(x, y, f)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            fig.colorbar(cm1)

        def plot_a_quant(ax, x, f, x_lbl, ttl):
            ax.plot(x, f.T)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_title(ttl)

        self.plotbase = Plotting()

        self.norm_q = self.plotbase.gyrobohm_SI(self.run_data, quantity="Qturb")*\
                      self.run_data.pars["Lref"] ** 2*1E-06
        self.area = averages.get_area(self.geom)

        x_lbl = r'x/a'
        t_lbl = r'$t\; [c_{ref}/L_{ref}]$'

        for spec in self.specnames:
            spec_flux = getattr(self.flux_step, spec)

            fig = plt.figure(figsize=(15, 10), dpi=100)
            ax_1 = fig.add_subplot(1, 2, 1)
            ttl = r"$" + spec + r"\,\,Q_{es}$"
            plot_a_map(ax_1, time_requested, self.run_data.spatialgrid.x_a,
                       np.squeeze(np.array(getattr(spec_flux, 'Qes')).T), t_lbl, x_lbl, ttl)
            ax_2 = fig.add_subplot(1, 2, 2)
            ttl = r"$" + spec + r"\,\,\Gamma_{es}$"
            plot_a_map(ax_2, time_requested, self.run_data.spatialgrid.x_a,
                       np.squeeze(np.array(getattr(spec_flux, 'Ges')).T), t_lbl, x_lbl, ttl)
            fig.show()

            fig = plt.figure(figsize=(15, 10), dpi=100)
            ax_1 = fig.add_subplot(2, 2, 1)
            tmp = averages.mytrapz(getattr(spec_flux, "Qes"), time_requested)
            tt1 = r"$<Q_{es}>_{FS,t}$"
            plot_a_quant(ax_1, self.run_data.spatialgrid.x_a, tmp, x_lbl, tt1)

            ax_2 = fig.add_subplot(2, 2, 2)
            tmp = averages.mytrapz(getattr(spec_flux, "Ges"), time_requested)
            tt1 = r"$<\Gamma_{es}>_{FS,t}$"
            plot_a_quant(ax_2, self.run_data.spatialgrid.x_a, tmp, x_lbl, tt1)

            ax_3 = fig.add_subplot(2, 2, 3)
            tmp = averages.mytrapz(getattr(spec_flux, "Qes"), time_requested)
            tt1 = r"$<Q_{es}>_{FS,t} * dVdx$"
            plot_a_quant(ax_3, self.run_data.spatialgrid.x_a, tmp*self.area, x_lbl, tt1)

            ax_4 = fig.add_subplot(2, 2, 4)
            tmp = averages.mytrapz(getattr(spec_flux, "Ges"), time_requested)
            tt1 = r"$<\Gamma_{es}>_{FS,t} * dVdx$"
            plot_a_quant(ax_4, self.run_data.spatialgrid.x_a, tmp*self.area, x_lbl, tt1)

            plt.tight_layout()
            fig.show()

            if self.opts['save_h5']['value']:
                file = h5py.File(out_folder / 'flux_profile_{}.h5'.format(spec), 'w')
                file["/x_a"] = self.run_data.spatialgrid.x_a
                file["/time"] = time_requested
                file["/Q_es_" + spec] = np.array(getattr(spec_flux, 'Qes')).T
                file["/G_es_" + spec] = np.array(getattr(spec_flux, 'Ges')).T
                if self.run_data.electromagnetic:
                    file["/Q_em_" + spec] = np.array(getattr(spec_flux, 'Qem')).T
                    file["/G_em_" + spec] = np.array(getattr(spec_flux, 'Gem')).T
                file.close()
