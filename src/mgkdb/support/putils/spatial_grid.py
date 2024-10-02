""" Module with the container objects defining velocitry grid and weights"""
# -*- coding: utf-8 -*-
import numpy as np
from .par_io import Parameters

class SpatialGrid:
    """ The numerical grid based on the parameters of a GENE run

    :param pnt: NamedTuple of the run parameters
    """

    def __init__(self, parameters):
        if isinstance(parameters, Parameters):
            pnt = parameters.asnamedtuple()
        elif isinstance(parameters, tuple):
            pnt = parameters
        
        try:
            kx_center = pnt.kx_center
        except AttributeError:
            kx_center = 0

        self._calc_kxgrid(pnt.x_local, pnt.y_local, pnt.lx, pnt.nx0, kx_center)
        self._calc_xgrid(pnt.x_local, pnt.lx, pnt.nx0, pnt.rhostar, pnt.x0)
        self._calc_kygrid(pnt)
        self._calc_ygrid(pnt)
        self.z = np.array([-np.pi + 2*np.pi*k/pnt.nz0
                           for k in range(pnt.nz0)], dtype=np.float64)
        self.nx0 = pnt.nx0
        if not pnt.y_local:
            self.ny0 = pnt.ny0
        self.nz0 = pnt.nz0

    def _calc_xgrid(self, x_local, lx, nx0, rhostar, x0):
        if x_local:
            xgrid = np.fft.fftfreq(nx0, d=1.0/lx)
            self.x = np.fft.fftshift(xgrid)
        else:
            self.x = np.array([-lx/2. + lx/(nx0 - 1)*i for i in range(0, nx0)])
            self.x_a = self.x*rhostar + x0

    def _calc_kxgrid(self, x_local, y_local, lx, nx0, kx_center):
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

    def _calc_ygrid(self, pnt):
        ly = 2*np.pi/pnt.kymin
        if pnt.y_local:
            self.y = np.fft.fftshift(np.fft.fftfreq(2*pnt.nky0, d=1/ly))
        else:
            if pnt.x_local:
                self.y = np.array([-ly/2. + ly/pnt.nky0*i for i in range(0, pnt.nky0)])
            else:
                self.y = np.array([ly/pnt.ny0*i for i in range(0, pnt.ny0)])

    def _calc_kygrid(self, pnt):
        if pnt.y_local:
            self.ky = np.array([pnt.kymin*(j + pnt.ky0_ind) for j in range(pnt.nky0)],
                               dtype=np.float64)
        else:
            ly = 2*np.pi/pnt.kymin
            if pnt.x_local:
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
