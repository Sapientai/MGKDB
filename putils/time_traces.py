""" Module containing functions for manipulating 1D timetraces"""
import numpy as np
import math

def autocorr_time(time, series, tau = 3):
    z = np.autocorr(series)
    return np.where(z<np.exp(-1) - time[0])


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
    
    
def find_nearest(array, value):
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
        return array[idx-1], idx-1
    else:
        return array[idx], idx
    