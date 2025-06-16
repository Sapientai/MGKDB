#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import h5py
import matplotlib.pyplot as plt
import numpy as np

import ..utils.averages as averages
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagProfiles(Diagnostic):
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Profiles'
        self.tabs = ['xglobal', 'GENE3D']

        self.help_txt = """Plots profiles for each species
                        \nSave h5 : save hdf5 file (def. True)"""

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "t_avg": {'tag': "t avg", 'values': [True, False]},
                     "save_h5": {"tag": "Save h5", "values": [True, False]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, species):

        class ProfilesStep:
            def __init__(self, specnames):
                for spec in specnames:
                    setattr(self, spec, self.__Specprofiles())

            class __Specprofiles:
                def __init__(self):
                    self.T = []
                    self.n = []
                    self.u = []

        self.run_data = run_data

        self.geom = run_data.geometry

        self.rhostarref = self.run_data.pars["rhostar"] * self.run_data.pars["minor_r"]

        self.profiles_step = ProfilesStep(self.specnames)

        self.get_needed_vars(['mom'])

        self.get_spec_from_opts()

        return self.needed_vars

    def execute(self, data, step):
        for spec in self.specnames:

            profiles_step = getattr(self.profiles_step, spec)

            if self.run_data.flux_tube:
                #   flux tube
                dens = getattr(getattr(data, 'mom_' + spec), "dens")(step.time, step.mom)
                T_par = getattr(getattr(data, 'mom_' + spec), "T_par")(step.time, step.mom)
                T_perp = getattr(getattr(data, 'mom_' + spec), "T_perp")(step.time, step.mom)
                u_par = getattr(getattr(data, 'mom_' + spec), "u_par")(step.time, step.mom)

                profiles_step.T.append(np.average(np.squeeze(1/3*T_par[:, 0, :]+2/3*T_perp[:, 0, :]),
                                              weights=self.J_norm, axis=-1))

                profiles_step.n.append(np.average(np.squeeze(dens[:, 0, :]),
                                                  weights=self.J_norm, axis=-1))

                profiles_step.u.append(np.average(np.squeeze(u_par[:, 0, :]),
                                                  weights=self.J_norm, axis=-1))
            elif self.run_data.x_global:
                # x global
                dens = getattr(getattr(data, 'mom_' + spec), "dens")(step.time, step.mom)
                T_par = getattr(getattr(data, 'mom_' + spec), "T_par")(step.time, step.mom)
                T_perp = getattr(getattr(data, 'mom_' + spec), "T_perp")(step.time, step.mom)
                u_par = getattr(getattr(data, 'mom_' + spec), "u_par")(step.time, step.mom)

                profiles_step.T.append(np.average(np.squeeze(1/3 * T_par[:, 0, :] + 2/3 * T_perp[:, 0, :]),
                                                  weights=self.geom.jacobian.T, axis=-1))

                profiles_step.n.append(np.average(np.squeeze(dens[:, 0, :]),
                                                  weights=self.geom.jacobian.T, axis=-1))

                profiles_step.u.append(np.average(np.squeeze(u_par[:, 0, :]),
                                                  weights=self.geom.jacobian.T, axis=-1))
            elif self.run_data.is3d:
                # 3D
                dens = getattr(getattr(data, 'mom_' + spec), "n")(step.time, step.mom)
                T_par = getattr(getattr(data, 'mom_' + spec), "T_par")(step.time, step.mom)
                T_perp = getattr(getattr(data, 'mom_' + spec), "T_per")(step.time, step.mom)
                u_par = getattr(getattr(data, 'mom_' + spec), "u_par")(step.time, step.mom)

                profiles_step.T.append(np.average(np.squeeze(1/3 * T_par + 2/3 * T_perp),
                                                  weights=self.geom.jacobian.T, axis=(1, 2)))

                profiles_step.n.append(np.average(np.squeeze(dens),
                                                  weights=self.geom.jacobian.T, axis=(1, 2)))

                profiles_step.u.append(np.average(np.squeeze(u_par),
                                                  weights=self.geom.jacobian.T, axis=(1, 2)))
            else:
                raise NotImplementedError("Profiles calculation ")

    def plot(self, time_requested, output=None, out_folder=None):
        def plot_a_map(ax, x, y, f, x_lbl, y_lbl, ttl):
            cm1 = ax.pcolormesh(x, y, f)
            ax.set_rasterization_zorder(z=-10)
            ax.set_xlabel(x_lbl)
            ax.set_ylabel(y_lbl)
            ax.set_title(ttl)
            fig.colorbar(cm1)

        self.plotbase = Plotting()

        if self.run_data.x_global or self.run_data.is3d:
            y_lbl = r'$x/a$'
            y_ax = self.run_data.spatialgrid.x_a
        else:
            y_lbl = r'$x/\rho_{ref}$'
            y_ax = self.run_data.spatialgrid.x

        x_lbl = r'$t\;c_{ref}/L_{ref}$'

        for i_s, spec in enumerate(self.specnames):
            omn_b = self.run_data.profilesdata.omn0s[:, i_s]
            omt_b = self.run_data.profilesdata.omt0s[:, i_s]
            T_b = self.run_data.profilesdata.T0s[:, i_s]/self.run_data.pars["temp" + spec]/self.run_data.pars["Tref"]
            n_b = self.run_data.profilesdata.n0s[:, i_s]/self.run_data.pars["dens" + spec]/self.run_data.pars["nref"]

            temp = np.array(getattr(getattr(self.profiles_step, spec), 'T')) * self.rhostarref
            n = np.array(getattr(getattr(self.profiles_step, spec), 'n')) * self.rhostarref
            u = np.array(getattr(getattr(self.profiles_step, spec), 'u')) * self.rhostarref

            omt = -np.gradient(np.log(T_b + temp), self.run_data.spatialgrid.x_a, axis=1) / \
                self.run_data.pars["minor_r"]
            omn = -np.gradient(np.log(n_b + n), self.run_data.spatialgrid.x_a, axis=1) / \
                self.run_data.pars["minor_r"]


            if len(time_requested) > 1:
                fig = plt.figure(figsize=(15, 10))
                ax = fig.add_subplot(2, 3, 1)
                plot_a_map(ax, time_requested, y_ax,
                           n.T, x_lbl, y_lbl, r"$\delta n " + spec + "$")
                ax = fig.add_subplot(2, 3, 4)
                plot_a_map(ax, time_requested, y_ax,
                           omn.T, x_lbl, y_lbl, r"$omn " + spec + "$")

                ax = fig.add_subplot(2, 3, 2)
                plot_a_map(ax, time_requested, y_ax,
                           temp.T, x_lbl, y_lbl, r"$\delta T " + spec + "$")
                ax = fig.add_subplot(2, 3, 5)
                plot_a_map(ax, time_requested, y_ax,
                           omt.T, x_lbl, y_lbl, r"$ omt " + spec + "$")
                ax = fig.add_subplot(2, 3, 3)
                plot_a_map(ax, time_requested, y_ax,
                           u.T, x_lbl, y_lbl, r"$\delta u_{//} " + spec + "$")

                fig.tight_layout()
                fig.show()

            if self.opts['t_avg']['value'] and len(time_requested) > 1:
                # time averaged values
                fig = plt.figure(figsize=(15, 10))
                ax = fig.add_subplot(2, 3, 1)
                ax.plot(y_ax, n_b + averages.mytrapz(n, time_requested))
                ax.plot(y_ax, n_b, ls='--')
                ax.set_xlabel(y_lbl)
                ax.set_title(r"$n {}$".format(spec))

                ax = fig.add_subplot(2, 3, 2)
                ax.plot(y_ax, T_b + averages.mytrapz(temp, time_requested))
                ax.plot(y_ax, T_b, ls='--')
                ax.set_xlabel(y_lbl)
                ax.set_title(r"$T {}$".format(spec))

                ax = fig.add_subplot(2, 3, 3)
                ax.plot(y_ax, averages.mytrapz(u, time_requested))
                ax.set_xlabel(y_lbl)
                ax.set_title(r"$\delta u {}$".format(spec))

                ax = fig.add_subplot(2, 3, 4)
                ax.plot(y_ax, averages.mytrapz(omn, time_requested))
                ax.plot(y_ax, omn_b, ls="--")
                ax.set_xlabel(y_lbl)
                ax.set_title(r"$omn {}$".format(spec))

                ax = fig.add_subplot(2, 3, 5)
                ax.plot(y_ax, averages.mytrapz(omt, time_requested))
                ax.plot(y_ax, omt_b, ls="--")
                ax.set_xlabel(y_lbl)
                ax.set_title(r"$omT {}$".format(spec))

                fig.tight_layout()
                fig.show()

                if self.opts['save_h5']['value']:
                    file = h5py.File(out_folder / 'profile_{}.h5'.format(spec), 'w')
                    file["/x_a"] = y_ax
                    file["/n_" + spec] = n_b + averages.mytrapz(n, time_requested)
                    file["/T_" + spec] = n_b + averages.mytrapz(temp, time_requested)
                    file["/omn_" + spec] = averages.mytrapz(omn, time_requested)
                    file["/omT_" + spec] = averages.mytrapz(omt, time_requested)
                    file.close()
