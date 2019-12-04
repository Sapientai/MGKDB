import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

def interp(xin,yin,xnew):
    """
    xin: x variable input
    yin: y variable input
    xnew: new x grid on which to interpolate
    yout: new y interpolated on xnew
    """

    #splrep returns a knots and coefficients for cubic spline
    rho_tck = interpolate.splrep(xin,yin)
    #Use these knots and coefficients to get new y
    yout = interpolate.splev(xnew,rho_tck,der=0)

    return yout

def full_interp(func_xin,xin,xconv,yconv,yout,verify_interp = False):
    """
    Takes function func_xin on grid xin and outputs the function on yout grid
    func_xin: function to interpolate
    xin: grid corresponding to func_xin
    xconv: xgrid for conversion
    yconv: ygrid for conversion
    yout: output grid
    """

    #If necessary truncate func_xin onto correct range
    #if xin[0] < xconv[0]:
    #    low_index = np.argmin(abs(xconv-xin[0]))
    #else:
    #    low_index = 0
    #if xin[-1] > xconv[-1]:
    #    high_index = np.argmin(abs(xconv-xin[-1]))
    #else:
    #    high_index = -1
#
#    if high_index == -1:
#        func_xin = func_xin[low_index:]
#        xin = xin[low_index:]
#    else:
#        func_xin = func_xin[low_index:high_index]
#        xin = xin[low_index:high_index]

    #print len(xin),len(func_xin),len(xconv)
    #plt.plot(xin)
    #plt.plot(xconv)
    #plt.show()
    func_xconv = interp(xin,func_xin,xconv)
    func_yout = interp(yconv,func_xconv,yout)
    xout = interp(yconv,xconv,yout) 
    if verify_interp:
        plt.plot(xin,func_xin,'x',label='Original')
        plt.plot(xout,func_yout,label='New')
        plt.legend()
        plt.show()
    
    return func_yout

