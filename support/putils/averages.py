""" Module containing averaging functions for diagnostics"""
import numpy as np
import os


def mytrapz(yvar, timefld):
    """ Trapezoid rule, adjusted for single timestep

    Operates on the first dimension of yvar (typically time)
    hence the name timefld for the integration variable samples
    :param yvar: Variable to integrate over
    :param timefld: The integration variable (time)
    :returns: The integration result (dim(yvar)-1)
    """
    timefld = np.array(timefld)
    yvar = np.real_if_close(yvar)
    if timefld.size == 1:
        return np.atleast_2d(yvar)[0]
    else:
        if yvar.shape[0] != len(timefld):
            raise ValueError("First dimension of yvar and timefld do not match")
        tmpt = timefld/(timefld[-1] - timefld[0])
        return np.trapz(yvar, x=tmpt, axis=0)


def z_av3d(var, geom):
    """ Perform the average in z direction for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object

    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            return np.average(var, weights=geom.jacobian, axis=-1)
        else:
            return np.average(var, weights=geom.jaco3d.T, axis=-1)
    else:
        if geom.pnt.y_local:
            return np.average(var, weights=geom.jaco3d.T, axis=-1)
        else:
            return np.average(var, weights=geom.jacobian.T, axis=2)


def y_av3d(var, geom):
    """ Perform the average in y direction for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:  # Add the negative half of the Fourier space for ky
            var[:, 0, :] *= 0.5
            return np.sum(2*var, axis=1)
        else:
            return np.average(var, weights=geom.jaco3d.T, axis=1)
    else:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.sum(2*var, axis=1)
        else:
            return np.average(var, weights=geom.jacobian.T, axis=1)


def x_av3d(var, geom):
    """ Perform the average in x direction for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            return np.sum(var, axis=0)
        else:  # Mirror positive kx to negative kx
            var[0, :, :] *= 0.5
            return np.sum(2*var, axis=0)
    else:
        if geom.pnt.y_local:
            return np.sum(var, axis=0)
        else:
            return np.average(var, weights=geom.jacobian.T, axis=0)


def xz_av3d(var, geom):
    """ Perform the average in x and z direction for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            return np.average(np.sum(var, axis=0), weights=geom.jacobian, axis=-1)
        else:  # Mirror positive kx to negative kx
            var[0, :, :] *= 0.5
            return np.average(np.sum(2*var, axis=0), weights=geom.jacobian.T, axis=-1)
    else:
        if geom.pnt.y_local:
            return np.average(var, weights=geom.jaco3d.T, axis=(0, -1))
        else:
            return np.average(var, weights=geom.jacobian.T, axis=(0, 2))


def yz_av3d(var, geom):
    """ Perform the average in y and z direction for a 3d variable
    param var: Variable to average over
    param geom: GENE geometry object """
    if geom.pnt.x_local:
        if geom.pnt.y_local:  # Add the negative half of the Fourier space for ky
            var[:, 0, :] *= 0.5
            return np.average(np.sum(2*var, axis=1), weights=geom.jacobian.T, axis=-1)
        else:
            return np.average(var, weights=geom.jaco3d.T, axis=(1, -1))  # geom has (y, z)
    else:
        if geom.pnt.y_local:
            return np.average(np.sum(2*var, axis=1) - var[:, 0, :], weights=geom.jacobian.T,
                              axis=-1)
        else:
            return np.average(var, weights=geom.jacobian.T, axis=(1, 2))


def xy_av3d_zprofile(var, geom):
    """ Perform the average in x and y direction for a 3d variable.  Includes 1/gxx**0.5 to match GENE diagnostic tool

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.sum(2*var, axis=(0, 1))/geom.gxx**0.5
        else:  # Mirror positive kx to negative kx
            print("Error!  Only ready for local simulations.")
            os.exit()
    else:
        print("Error!  Only ready for local simulations.")
        os.exit()




def xy_av3d(var, geom):
    """ Perform the average in x and y direction for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.sum(2*var, axis=(0, 1))
        else:  # Mirror positive kx to negative kx
            var[0, :, :] *= 0.5
            return np.average(np.sum(2*var, axis=0), weights=geom.jacobian.T, axis=1)
    else:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.average(np.sum(2*var, axis=1), weights=geom.jacobian.T, axis=0)
        else:
            return np.average(var, weights=geom.jacobian.T, axis=(0, 1))


def xyz_av3d(var, geom):
    """ Perform the average in all spatial directions for a 3d variable

    :param var: Variable to average over
    :param geom: GENE geomtry object
    """
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.average(np.sum(2*var, axis=(0, 1)), weights=geom.jacobian)
        else:  # Mirror positive kx to negative kx
            var[0, :, :] *= 0.5
            temp = np.sum(2*var, axis=0)
            return np.average(temp, weights=geom.jacobian.T, axis=(0, -1))
    else:
        if geom.pnt.y_local:
            var[:, 0, :] *= 0.5
            return np.average(np.sum(2*var, axis=1), weights=geom.jacobian.T, axis=(0, -1))
        else:
            return np.average(var, weights=geom.jacobian.T)


def av3d_by_switch(xavg, yavg, zavg):
    """ Map the required averaging function by binary switches for the averages

    :returns: Reference to the appropriate function from this module
    """
    # pylint: disable=too-many-return-statements
    if not (xavg or yavg or zavg):
        return lambda var, geom: var  # Return an identity function
    if xavg and not (yavg or zavg):
        return x_av3d
    if xavg and yavg and not zavg:
        return xy_av3d
    if xavg and not yavg and zavg:
        return xz_av3d
    if xavg and yavg and zavg:
        return xyz_av3d
    if not (xavg or yavg) and zavg:
        return z_av3d
    if not xavg and yavg and zavg:
        return yz_av3d
    if not xavg and yavg and not zavg:
        return y_av3d
    # Something must go very wrong to end here
    raise ValueError("Inconsistent averaging information")


def flux_spectra_xz_av(var, geom):
    """ Perform xz average in the form required for ky flux spectra (see diagplots.plot_spectra)"""
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            temp = np.empty((geom.pnt.nky0, geom.pnt.nz0),dtype=np.float64)
            temp[0, :] = np.real(np.real(np.sum(var[:, 0, :], axis=0)))
            temp[1:, :] = 2*np.real(np.real(np.sum(var[:, 1:, :], axis=0)))
            
            return np.average(temp, weights=geom.jacobian, axis=-1)
        else:
            raise NotImplementedError("No support for y-global")
    else:
        raise NotImplementedError("No support for x-global yet")


def flux_spectra_yz_av(var, geom):
    """ Perform yz average in the form required for kx flux spectra (see diagplots.plot_spectra)"""
    if not geom.pnt.y_local:
        raise NotImplementedError("No support for y-global")
    if geom.pnt.x_local:
        nx0o2 = int(geom.pnt.nx0/2)
        temp = np.zeros((nx0o2 + 1, geom.pnt.nz0))
        temp[0, :] = np.real_if_close(var[0, 0, :]) + 2*np.sum(np.real(var[0, 1:, :]), axis=0)
        if geom.pnt.nx0%2 == 0:
            temp[1:nx0o2, :] = 2*np.real_if_close(var[1:nx0o2, 0, :]) + 2*np.sum(
                    np.real(var[1:nx0o2, 1:, :] + var[2*nx0o2:nx0o2:-1, 1:, :]), axis=1)
            temp[nx0o2, :] = np.real_if_close(var[nx0o2, 0, :]) + 2*np.sum(
                    np.real(var[nx0o2, 1:, :]), axis=0)
        else:
            temp[1:nx0o2 + 1, :] = 2*np.real_if_close(var[1:nx0o2 + 1, 0, :]) + 2*np.sum(
                    np.real(var[1:nx0o2 + 1, 1:, :] + var[2*nx0o2:nx0o2:-1, 1:, :]), axis=1)

        return np.average(temp, weights=geom.jacobian, axis=-1)
    else:
        raise NotImplementedError("No support for x-global yet")


def get_area(geom):
    """ Calculate flux surface area"""
    if geom.pnt.x_local:
        if geom.pnt.y_local:
            raise NotImplementedError("No support for x local yet")
        else:
            raise NotImplementedError("No support for y-global yet")
    else:
        if geom.pnt.y_local:
            raise NotImplementedError("No support for x-global yet")
        else:
            area_fs = np.zeros((geom.pnt.nx0))
            for z in range(0, geom.pnt.nz0):
                for y in range(0, geom.pnt.ny0):
                    area_fs = area_fs + np.sqrt(geom.gxx.T[:, y, z])*geom.jacobian.T[:, y, z]
            return area_fs*(2*np.pi) ** 2*abs(geom.Cy)/geom.pnt.ny0/geom.pnt.nz0

        
def flux_surface_avg(field, geometry):
    if geometry.jacobians.ndim==1:
       raise NotImplementedError("No support for x local yet") 
    elif geometry.jacobians.ndim==1:
        if field.dim==3:
            return np.average(np.sum(field,axis=1), weights=geom.jacobian, axis=-1)
        elif field.dim==2 and field.shape==geom.jacobian.shape:
            return np.average(field, weights=geom.jacobian, axis=-1)
        else:
            raise NotImplementedError("Operation not allowed")
