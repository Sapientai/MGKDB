""" Module containing the Data class"""
# -*- coding: utf-8 -*-

import warnings
from data.base_file import create_GENEfile
import utils.fourier as fourier


class Data:
    """ Class to provide the data of a simulation run from the different GENE files"""
    def __init__(self):
        self.avail_vars = {}
        self.run_data = None
        self.field = None
        self.avail_times = None

    def load_in(self, run_data, extensions=None):
        """ Load the GENE files that are present"""
        class AvailableTimes:
            pass

        class TimeStep:
            def __init__(self, times, steps, files):
                self.times = times
                self.steps = steps
                self.files = files

        self.avail_times = AvailableTimes()

        self.run_data = run_data

        # **********************************
        # add other outputs here  once coded
        # **********************************
#TODO: embed this into a method

        # Field file
        if run_data.pnt.istep_field > 0:
            self.field = create_GENEfile('field', run_data, spec=None,
                                         extensions=extensions)
            self.avail_vars = {'field': self.field.varname}
            times, steps, files = self.field.set_times_and_inds()
            self.avail_times.field = TimeStep(times, steps, files)

        # mom are same for all species, so we create an object for each species
        # but one entry for times
        if run_data.pnt.istep_mom > 0:
            for specname in run_data.specnames:
                setattr(self, 'mom_' + specname,
                        create_GENEfile('mom', run_data, spec=specname,
                                        extensions=extensions))

            self.avail_vars.update(
                    {'mom':
                        getattr(getattr(self, 'mom_' + run_data.specnames[0]),
                                'varname')})
            times, steps, files = getattr(getattr(self, 'mom_' +
                                                  run_data.specnames[0]), 'set_times_and_inds')()
            setattr(self.avail_times, 'mom', TimeStep(times, steps, files))

        if run_data.pnt.istep_srcmom > 0:
            for specname in run_data.specnames:
                setattr(self, 'srcmom_' + specname,
                        create_GENEfile('srcmom', run_data, spec=specname,
                                        extensions=extensions))
            self.avail_vars.update(
                    {'srcmom':
                        getattr(getattr(self, 'srcmom_' +
                                        run_data.specnames[0]), 'varname')})
            times, steps, files = getattr(getattr(self, 'srcmom_' +
                                                  run_data.specnames[0]),
                                            'set_times_and_inds')()
            setattr(self.avail_times, 'srcmom', TimeStep(times, steps, files))

        if run_data.pnt.istep_vsp > 0:
            self.vsp = create_GENEfile('vsp', run_data, spec=None,
                                       extensions=extensions)
            self.avail_vars.update({'vsp': self.vsp.varname})
            times, steps, files = self.vsp.set_times_and_inds()
            setattr(self.avail_times, 'vsp', TimeStep(times, steps, files))

    def apply_fouriertransforms(self, diagspace, var, geom):
        """ Fourier transform the data as required by a diagnostic"""
        if diagspace.xavg and diagspace.yavg:  # Nothing to do if both are averaged
            return var
        xaxis = -3  # By default the last three dimensions of var are x, y, z.
        yaxis = -2  # This is changed if averages are applied
        zaxis = -1
        if diagspace.yavg:
            xaxis += 1
            yaxis += 1
        if diagspace.zavg:
            xaxis += 1
            yaxis += 1

        if diagspace.x_fourier != self.run_data.x_local and not diagspace.xavg:
            if self.run_data.x_local:
                var = fourier.kx_to_x(var, self.run_data.pnt.nx0, axis=xaxis)
            else:
                var = fourier.x_to_kx(var, axis=xaxis)
        if diagspace.y_fourier != self.run_data.y_local and not diagspace.yavg:
            if self.run_data.y_local:
                var = fourier.ky_to_y(var, self.run_data.pnt.nky0, axis=yaxis)
            else:
                if self.run_data.x_local:
                    warnings.warn("y-global is not supported", RuntimeWarning)
                var = fourier.y_to_ky(var, geom, axis=yaxis)
        if diagspace.z_fourier:
            var = fourier.z_to_kz(var, geom, axis=zaxis)
        return var
