""" Module containing fourier transform routines for GENE time series"""

import warnings
import numpy as np
from scipy.fftpack import fft, ifft, rfft, irfft


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
            var = kx_to_x(var, self.run_data.pnt.nx0, axis=xaxis)
        else:
            var = x_to_kx(var, axis=xaxis)
    if diagspace.y_fourier != self.run_data.y_local and not diagspace.yavg:
        if self.run_data.y_local:
            var = ky_to_y(var, self.run_data.pnt.nky0, axis=yaxis)
        else:
            if self.run_data.x_local:
                warnings.warn("y-global is not supported", RuntimeWarning)
            var = y_to_ky(var, geom, axis=yaxis)
    if diagspace.z_fourier:
        var = z_to_kz(var, geom, axis=zaxis)
    return var


def kx_to_x(var_kx, nx0, axis=-3):
    """ Perform inverse FFT on kx spectral direction of variable

    Note: The fft and ifft in python and GENE/IDL have the factor 1/N switched!
    :param var_kx: Variable in kx space
    :param nx0: Number of kx grid points
    :param axis: Which axis of var_kx is the x direction, by default the third last one
    :returns: variable in real x space
    """
    var_x = np.fft.ifft(nx0*var_kx, axis=axis)
    var_x = np.real_if_close(var_x, tol=1e5)
    return var_x


def ky_to_y(var_ky, nky0, axis=-2):
    """ Perform inverse FFT on ky spectral direction of variable

    The GENE data only include the non-negative ky components, so we need to use the real
    valued FFT routines
    Note: The fft and ifft in python and GENE/IDL have the factor 1/N switched!
    :param var_ky: Variable in kx space
    :param nky0: Number of ky grid points
    :param axis: Which axis of var_kx is the x direction, by default the third last one
    :returns: variable in real y space
    """
    # The GENE data only include the non-negative ky components, so we need to use the real
    # valued FFT routines
    var_y = np.fft.irfft(2*nky0*var_ky, n=2*nky0, axis=axis)
    var_y = np.real_if_close(var_y, tol=1e5)
    return var_y


def x_to_kx(var_x, axis=-3):
    """ Perform FFT on x direction of variable

    Note: The fft and ifft in python and GENE/IDL have the factor 1/N switched!
    :param var_x: Variable in real x space
    :param nx0: Number of x grid points
    :param axis: Which axis of var_kx is the x direction
    :returns: variable in fourier kx space
    """
    var_kx = np.fft.fft(var_x, axis=axis)
    return var_kx


def y_to_ky(var_y, axis=-2):
    """ Perform FFT on y direction of variable

    Note: The fft and ifft in python and GENE/IDL have the factor 1/N switched!
    :param var_y: Variable in real y space
    :param axis: Which axis of var_ky is the y direction
    :returns: variable in fourier ky space
    """
    var_ky = np.fft.fft(var_y, axis=axis)

    return var_ky


def z_to_kz(var_z, axis=-1):
    """ Perform FFT on z direction of variable

    Note: The fft and ifft in python and GENE/IDL have the factor 1/N switched!
    :param var_z: Variable in real z space
    :param nz0: Number of z grid points
    :param axis: Which axis of var_kz is the z direction
    :returns: variable in fourier kz space
    """
    var_kz = np.fft.fft(var_z, axis=axis)
    return var_kz
