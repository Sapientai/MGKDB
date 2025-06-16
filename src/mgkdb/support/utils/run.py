""" Module with the container objects for simulation data"""
# -*- coding: utf-8 -*-

import numpy as np
from .par_io import Parameters
from .geom import Geometry
from ...data.nrgdata import NrgFile
from ...data.data import Data
from ...data.profiledata import ProfileData

class Run:
    """ Class containing basic information on a simulation data set"""

    def __init__(self, in_folder, fileextension):
        self.in_folder = in_folder
        self.fileextension = fileextension
        # parameters is read always from the ascii file
        params = Parameters()
        print('fileextension')
        params.read_pars(self.in_folder + '/parameters{}'.format(fileextension))

        self.pars = params.pardict
        self.pnt = params.asnamedtuple()
        # Determine if we are in one of the global versions
        self.x_local = self.pars.get('x_local', True)  # By default, x_local = T is not written
        self.y_local = self.pars.get('y_local', True)  # By default, y_local = T is not written
        self.is3d = not self.x_local and not self.y_local
        self.x_global = not self.x_local and self.y_local
        self.flux_tube = self.x_local and self.y_local
        self.nonlinear = self.pars.get('nonlinear')
        self.electromagnetic = (self.pars.get('beta', False) != 0)
        self.bpar = self.pars.get("bpar", False)

        # which output we are handling
        self.is_h5 = self.pars.get('write_h5', False)
        self.is_adios = self.pars.get('write_hac', False)

        # Here we patch the extension adding the right suffix
        if self.is_h5:
            self.fileextension = fileextension + ".h5"
        elif self.is_adios:
            self.fileextension = fileextension + ".bp"

        # each run contians its own geometry info, for e.g. change of resolution
        self.geometry = Geometry(self)

        # each run contains also species. For changes or just for completeness
        self.specnames = params.specnames

        # spatial grids
        self.spatialgrid = SpatialGrid(self.pnt, self.x_local, self.y_local)

        self.vspgrid = VspGrid(self.pnt)

        if not self.flux_tube:
            self.profilesdata = ProfileData(self.pnt, self.is_h5,
                                            self.specnames, self.fileextension,
                                            self.in_folder)


class Simulation:
    """ The simulations class embeds the Run class, meaning a simulation is a collection
        of runs. Aiming at something where a single run can be handled by itself
        for cases to be used not in the GUI """

    def __init__(self, in_folder=None, out_folder=None, extensions=None):
        self.in_folder = in_folder
        self.extensions = extensions
        self.out_folder = out_folder
        self.starttime = -1
        self.endtime = -2
        self.stepping = 1
        self.max_steps = 'all'
        self.data = Data()
        self.specnames = None
        self.run = []
        self.nrgdata = []

    def prepare(self):
        """ Sort extensions in time ascending

         We dont really need it, but looks better on the GUI
        """

        first_time = []

        if self.run:
            self.run.clear()
        if self.nrgdata:
            self.nrgdata.clear()

        for i_ext, ext in enumerate(self.extensions):
            # there is a lot to cleanup
            # run contains each of the restart we want to process
            act_run = Run(self.in_folder, ext)
            self.extensions[i_ext] = act_run.fileextension
            self.run.append(act_run)

        # calling Set fills out the nrg info only
        for irun, ext in enumerate(self.extensions):
            # list all nrg
            nrg = NrgFile(self.in_folder+ '/nrg{}'.format(self.extensions[irun]), self.run[irun])
            self.nrgdata.append(nrg)
            nrg.generate_timeseries()
            first_time.append(nrg.timearray[0])

        self.run = [x for _, x in sorted(
                zip(sorted(range(len(first_time)), key=lambda k: first_time[k]), self.run))]
        self.extensions = [x for _, x in sorted(
                zip(sorted(range(len(first_time)), key=lambda k: first_time[k]), self.extensions))]
        self.nrgdata = [x for _, x in sorted(
                zip(sorted(range(len(first_time)), key=lambda k: first_time[k]), self.nrgdata))]

        self.data.load_in(self.run[0], self.extensions)
        self.specnames = self.run[0].specnames


class SpatialGrid:
    """ The numerical grid based on the parameters of a GENE run

    :param pnt: NamedTuple of the run parameters
    :param x_local: Is the run local in radial direction?
    :param y_local: Is the run local in "binormal" direction?
    """

    def __init__(self, pnt, x_local, y_local):
        try:
            kx_center = pnt.kx_center
        except AttributeError:
            kx_center = 0

        self._calc_kxgrid(x_local, y_local, pnt.lx, pnt.nx0, kx_center)
        self._calc_xgrid(x_local, pnt.lx, pnt.nx0, pnt.rhostar, pnt.x0)
        self._calc_kygrid(x_local, y_local, pnt)
        self._calc_ygrid(x_local, y_local, pnt)
        self.z = np.array([-np.pi + 2*np.pi*k/pnt.nz0 for k in range(pnt.nz0)], dtype=np.float64)
        self.nx0 = pnt.nx0
        if not y_local:
            self.ny0 = pnt.ny0
        self.nz0 = pnt.nz0


    def _calc_xgrid(self, x_local, lx, nx0, rhostar, x0):
        if x_local:
            xgrid = np.fft.fftfreq(nx0, d=1.0/lx)
            self.x = np.fft.fftshift(xgrid)
        else:
            self.x = np.array([-lx/2. + lx/(nx0 - 1)*i for i in range(0, nx0)])
            self.x_a = self.x*rhostar + x0

    def _calc_kxgrid(self, x_local, y_local, lx, nx0, kx_center=0):

        self.kxmin = 2*np.pi/lx

        if x_local:
            if y_local:
                kxgridp = [self.kxmin*i for i in range(int((nx0 + 1)/2) + (1 - nx0%2))]
                kxgridn = [self.kxmin*i for i in range(int(-(nx0 - 1)/2), 0)]
                # positive kx modes
                self.kx_pos = np.array(kxgridp) + kx_center
                self.kx_fftorder = np.array(kxgridp + kxgridn, dtype=np.float64) + kx_center
                # ordered kx array
                self.kx = np.array(kxgridn + kxgridp, dtype=np.float64) + kx_center
            else:
                self.kx = np.array([self.kxmin*i for i in range(nx0)])
        else:
            self.kx_fftorder = 2*np.pi*np.fft.fftfreq(nx0, d=lx/nx0)
            self.kx = np.fft.ifftshift(self.kx_fftorder)
            self.kx_pos = self.kx_fftorder[:int(nx0/2 + 1)]

    def _calc_ygrid(self, x_local, y_local, pnt):
        ly = 2*np.pi/pnt.kymin
        if y_local:
            self.y = np.fft.fftshift(np.fft.fftfreq(2*pnt.nky0, d=1/ly))
        else:
            if x_local:
                self.y = np.array([-ly/2. + ly/pnt.nky0*i for i in range(0, pnt.nky0)])
            else:
                self.y = np.array([ly/pnt.ny0*i for i in range(0, pnt.ny0)])

    def _calc_kygrid(self, x_local, y_local, pnt):
        if y_local:
            self.ky = np.array([pnt.kymin*(j + pnt.ky0_ind) for j in range(pnt.nky0)],
                               dtype=np.float64)
        else:
            ly = 2*np.pi/pnt.kymin
            if x_local:
                self.ky = 2*np.pi*np.fft.ifftshift(np.fft.fftfreq(pnt.nky0, d=ly/pnt.nky0))
            else:
                self.ky = np.fft.fftfreq(pnt.ny0)*pnt.ny0*pnt.kymin

    def kx_grid_slice(self, kxslice):
        """Get a full kx grid in FFT order from a slice for positive kx"""
        sliced_kxpos = self.kx_pos[kxslice]
        if self.nx0 % 2 == 1:
            sliced_kxneg = -sliced_kxpos[-1::-1]
        else:
            if kxslice.stop is None:  # Nyquist mode must be ignored
                sliced_kxneg = -sliced_kxpos[-2::-1]
            else:
                sliced_kxneg = -sliced_kxpos[-1::-1]
        if kxslice.start is None:
            sliced_kxneg = sliced_kxneg[:-1]
        sliced_kx = np.concatenate((sliced_kxpos, sliced_kxneg))
        return sliced_kx


class VspGrid:
    def __init__(self, pnt):
        self._calc_vgrid(pnt.lv, pnt.nv0)
        if pnt.mu_grid_type == 'gau_lag':
            self._calc_mugrid_gaulag(pnt.lw, pnt.nw0)
        else:
            raise NotImplementedError("This mu grid is not implemented")

    def _calc_vgrid(self, lv, nv):
        dv = 2.0*lv/(nv-1.0)
        self.vp = np.zeros(nv)
        for iv in range(0, nv):
            self.vp[iv] = -lv + iv*dv

    def _calc_mugrid_gaulag(self, lw, nw):
        self.mu, dmu = np.polynomial.laguerre.laggauss(nw)
        dmu = dmu * np.exp(self.mu)
        fac = lw / np.sum(dmu)
        self.mu = self.mu*fac
