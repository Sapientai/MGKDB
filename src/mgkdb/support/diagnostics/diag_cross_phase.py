# -*- coding: utf-8 -*-

import warnings
from tkinter import END
import matplotlib.pyplot as plt
import numpy as np
from ..putils import fourier
from .diagnostic import Diagnostic
from .baseplot import Plotting
from .diagspace import DiagSpace
import os

class DiagCrossPhase(Diagnostic):
    """Diagnostic for the cross phases between pairs of variables in ky space."""
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Cross phase'
        self.tabs = ['fluxtube']

        self.help_txt = """Plots the PDFs of the cross phases between pairs of variables in ky space.
                        \nQuantity 1: First quantity for the cross phase
                        \nQuantity 2: Second quantity for the cross phase
                        \nxind: x indices for cross phase calculation; default: -1 (average)
                        \nzind: z point for cross phase calculation; default: -1 (average)
                        \nspec: which species to plot (def. all if spec dependent)
                        \nSave h5 : save hdf5 file (def. False)
                        """

        self.avail_vars = avail_vars
        self.specnames = specnames

        self.opts = {"quant_1": {'tag': "Quant 1", 'values': None, 'files': ['field']},
                     "quant_2": {'tag': "Quant 2", 'values': None, 'files': ['mom']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "xind": {'tag': "x ind", 'values': None},
                     "zind": {'tag': "z ind", 'values': None}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run, specnames, out_folder):
        
        self.ky = run.spatialgrid[0].ky
        self.pnt = run.parameters[0].asnamedtuple()

        if self.opts['quant_1']['value'] is None:
            raise RuntimeError("No quantity 1 given for cross phase")
        if self.opts['quant_2']['value'] is None:
            raise RuntimeError("No quantity 2 given for cross phase")

        # parallel position, unset or -1, average all
        zind = self.opts['zind']['value']
        if not zind or zind == -1:
            zind = None
            zrange = (None, None)
            zavg = True
        else:
            zrange = (zind, zind + 1)
            zavg = False

        # radial position, unset or -1 means all
        xind = self.opts['xind']['value']
        if not xind or xind == -1:
            xind = None
            xrange = (None, None)
            xavg = True
        else:
            xrange = (xind, xind + 1)
            xavg = False

        # binormal position, for all
        yind = None
        yrange = (None, None)
        yavg = False

        # diagspace is unique for each call, so it can be here
        # it should however be outside, since we can construct all grids
        # and have them in common for all diagnostics and select here only
        # the indexes we weant to plot
        self.diagspace = DiagSpace(run.spatialgrid[0], False, True, False, xrange, yrange, zrange,
                                   xavg, yavg, zavg)

#        self.geom = run.geometry
#        self.run_data = run_data

        # This is special since we dont save stuff by default, so just do what we need
        self.get_spec_from_opts()
        # toggle the reader
        for file_key in self.avail_vars.keys():
            self.needed_vars[file_key] = {}
            for data_value in self.avail_vars[file_key].values():
                if data_value in self.opts['quant_1']['value']:
                    self.needed_vars[file_key][data_value] = True
                elif data_value in self.opts['quant_2']['value']:
                    self.needed_vars[file_key][data_value] = True
                else:
                    self.needed_vars[file_key][data_value] = False

        self.cross_phase = {}
        for spec in self.specnames:
            self.cross_phase[spec] = []

        return self.needed_vars

    def execute(self, data, parameters, geometry, spatialgrid,  step):

        # loop over quaitites in that file
        for quant_1 in self.needed_vars["field"].keys():
            # loop over quaitites in that file
            if self.needed_vars["field"][quant_1]:
                data_in_1 = getattr(getattr(data, "field"), quant_1)(step.time,
                                                                     getattr(step, "field"), geometry)
                data_in_1 = fourier.apply_fouriertransforms(self.pnt, self.diagspace, data_in_1, geometry)

        # loop over quaitites in that file
        for quant_2 in self.needed_vars["mom"].keys():
            # loop over quaitites in that file
            if self.needed_vars["mom"][quant_2]:
                # spec dependent
                for spec in self.specnames:
                    data_in_2 = getattr(getattr(data, "mom" + '_' + spec), quant_2)(step.time,
                                                                                    getattr(step,
                                                                                            "mom"), geometry)
                    data_in_2 = fourier.apply_fouriertransforms(self.pnt, self.diagspace, data_in_2, geometry)

                    angle = np.angle(data_in_1/data_in_2)

                    # not where when we have to do the averages
                    # cross_phase = averages.av3d_by_switch(self.diagspace.xavg,
                    #                         self.diagspace.yavg,
                    #                         self.diagspace.zavg)(angle, self.geom)

                    self.cross_phase[spec].append(angle[self.diagspace.diagslice])
    
    def dict_to_mgkdb(self):
        Diag_dict = {}
        Diag_dict['nx0'] = self.pnt.nx0
        Diag_dict['nz0'] = self.pnt.nz0
        Diag_dict['cross_phase'] = self.cross_phase
        
        return Diag_dict

    def plot(self, time_requested, output=None, out_folder=None, terminal=None, suffix = None):
        """ Cross-phases """

        if output:
            output.info_txt.insert(END, "Cross phase:\n")

#        ky = self.ky
        nbins = 64

        out = np.zeros((len(self.ky), nbins))

        self.plotbase = Plotting()

        for spec in self.specnames:
            array = np.array(self.cross_phase[spec])           
            for i_ky in range(len(self.ky)):
                phase_ky = array[:,:,i_ky,...].flatten()
#                phase_ky = self.cross_phase[spec][:][:][i_ky][:][:].flatten()
                hist, bin_edges = np.histogram(phase_ky/self.pnt.nx0/self.pnt.nz0,
                                               bins=nbins, range=(-np.pi, np.pi))
                out[i_ky, :] = hist

            fig = plt.figure()
            plt.xlabel('Phase angle/rad', fontsize=14)
            plt.ylabel(r'$k_y\rho_s$', fontsize=16)
            # cm1 = plt.contourf(bin_edges[1:],ky[1:],out[1:,:],50,cmap=self.plotbase.cmap_bidirect)
            cm1 = plt.pcolormesh(bin_edges[1:], self.ky[1:], out[1:, :])
            fig.colorbar(cm1)
            fig.tight_layout()
            if out_folder is not None:
                fig.savefig(os.path.join(out_folder, 'CrossPhase_{}{}.png'.format(spec, suffix)), bbox_inches='tight')
                plt.close(fig)
            else:
                fig.show()
            
    def save(time_requested, output=None, out_folder=None):
        pass

    def finalize():
        pass
