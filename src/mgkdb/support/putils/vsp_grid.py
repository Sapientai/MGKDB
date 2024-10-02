""" Module with the container objects defining velocitry grid and weights"""
# -*- coding: utf-8 -*-
import numpy as np
from .par_io import Parameters

class VspGrid:
    def __init__(self, parameters):
        if isinstance(parameters, Parameters):
            pnt = parameters.asnamedtuple()
        elif isinstance(parameters, tuple):
            pnt = parameters

        self._calc_vgrid(pnt.lv, pnt.nv0)

        if pnt.mu_grid_type == 'gau_lag' or pnt.mu_grid_type == "'gau_lag'":
            self._calc_mugrid_gaulag(pnt.lw, pnt.nw0)
        elif pnt.mu_grid_type == "'eq_vperp'":
            self._calc_mugrid_eq_vperp(pnt.lw, pnt.nw0)
        else:
            print("mu grid " + pnt.mu_grid_type + " is not yet implemented")

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

    def _calc_mugrid_eq_vperp(self, lw, nw):
        """Sugama needs this"""
        dmu = lw / nw**2
        self.mu = np.zeros(nw)
        self.muweights = np.zeros(nw)
        for iw in range(1, nw+1):
            self.mu[iw-1] = (iw + 0.5)**2 * dmu
            self.muweights[iw-1] = (2.*iw - 1.) * dmu
