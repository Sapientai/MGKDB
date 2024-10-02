""" geomfft.py: class preparing input for GENE's generalized Miller equilibrium from GENE outputs"""
import re
import os
import datetime
import numpy as np
import warnings
from collections import OrderedDict
import .geom
import .comm
import ..data.omega_eigenvalue as eigenvalue
import json
import .averages as averages
import matplotlib.pyplot as plt #remove later
import ..diagplots.plot_ball as ballooning
import ..data.nrgdata as nrg
from scipy import interpolate

class GEOMFFT(object):
    """ GEOMFFT class:

    Determines shape parameters for generalized Miller equilibrium

    """

    def __init__(self,common,rundatafiles):
        print ("Called flux surface parametrization tool ... ")
        self.cm = common
        self.geom = pydiag.utils.geom.Geometry(self.cm)
        self.get_shape()

    def get_flux_surface_distance(self,R0,Z0,R,Z):
        nz0 = len(R)
        #poloidal theta (COCOS=2/12); theta is running counter-clockwise
        #in a poloidal plain to the right of the magnetic axis
        theta = np.arctan((Z-Z0)/(R-R0))
        for iz in range(int(nz0/2),nz0-1):
            thetadiff = (theta[iz+1]-theta[iz])
            if thetadiff>0.5*np.pi:
                theta[iz+1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                theta[iz+1]+=np.pi
            thetadiff = (theta[nz0-1-iz-1]-theta[nz0-1-iz])
            if thetadiff>0.5*np.pi:
                theta[nz0-1-iz-1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                theta[nz0-1-iz-1]+=np.pi

        #sorted theta (starting at th=0)
        theta=np.where(abs(theta)<1E-12,0.0,theta)
#        print ('theta = ', theta)
        theta_sort = (theta+2.0*np.pi)%(2.0*np.pi)
        sort_ind = np.argsort(theta_sort)
#        print('sort_ind = ', sort_ind)
        theta_sort = theta_sort[sort_ind]
#        print('theta_sort = ', theta_sort)
        aN = np.sqrt((R[sort_ind]-R0)**2+(Z[sort_ind]-Z0)**2) #/R0

        #now extend aN and theta_sort to definitely cover >= [0.0,2*pi]
        theta_sort = np.append(theta_sort[-1]-2.0*np.pi,theta_sort)
        theta_sort = np.append(theta_sort,theta_sort[1]+2.0*np.pi)
        aN = np.append(aN[-1],aN)
        aN = np.append(aN,aN[1])

        return {"theta" : theta,          #poloidal angle for original data
                "sort_ind" : sort_ind,    #sort index for original data
                "aN" : aN,                #sorted+ext. flux surface radius funct.
                "theta_sort" : theta_sort #sorted+ext. theta
                }


    def get_shape(self):
        """ Determines shape parameters for generalized Miller equilibrium """

        print ("Determining flux surface shape ...")
        nz0 = self.cm.pnt.nz0

        #determine max/min indices (used several times)
        self.maxR_ind = np.argmax(self.geom.R)
        self.minR_ind = np.argmin(self.geom.R)

        #determine flux surface center
        self.R0 = 0.5*(max(self.geom.R)+min(self.geom.R))
        self.Z0 = 0.5*(max(self.geom.Z)+min(self.geom.Z))
        print ("(R0,Z0) = (", self.R0, ",", self.Z0,")")

        #minor radius of flux surface
        self.r = 0.5*(max(self.geom.R)-min(self.geom.R))

        #New reference length
        self.Lref = self.R0

        #conversion factor
        self.dxdr = 2.0/(self.geom.dxdR[self.maxR_ind]/self.geom.gxx[self.maxR_ind]-\
                         self.geom.dxdR[self.minR_ind]/self.geom.gxx[self.minR_ind])

        #center result (r0)
        res_c=self.get_flux_surface_distance(self.R0,self.Z0,self.geom.R,self.geom.Z)
        self.theta=res_c["theta"]
        aN = res_c["aN"]/self.Lref
        theta_sort=res_c["theta_sort"]
        sort_ind=res_c["sort_ind"]

        #delta_r for finite differences (should be small)
        delta_r = 0.00001 #*self.r/self.R0

        dRdr = self.geom.dxdR/self.geom.gxx*self.dxdr
        dZdr = self.geom.dxdZ/self.geom.gxx*self.dxdr

        #left: r0-dr
        res_l=self.get_flux_surface_distance(self.R0,self.Z0,
                (self.geom.R-delta_r*dRdr),(self.geom.Z-delta_r*dZdr))
        aNl = res_l["aN"]/self.Lref
        thetal = res_l["theta_sort"]

        #right: r0+dr
        res_r=self.get_flux_surface_distance(self.R0,self.Z0,
                (self.geom.R+delta_r*dRdr),(self.geom.Z+delta_r*dZdr))
        aNr = res_r["aN"]/self.Lref
        thetar = res_r["theta_sort"]


        #equidistant theta (COCOS=2/12) with somewhat higher resolution for fourier transforms etc
        nth = 10*nz0
        theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/nth

        #interpolate to this equidist. grid with proper order (interpol requires increasing arr)
        fc = interpolate.interp1d(theta_sort,aN,kind='cubic') #,fill_value='extrapolate')
        aN_th = fc(theta_grid)
        fl = interpolate.interp1d(thetal,aNl,kind='cubic') #,fill_value='extrapolate')
        aNl_th = fl(theta_grid)
        fr = interpolate.interp1d(thetar,aNr,kind='cubic') #,fill_value='extrapolate')
        aNr_th = fr(theta_grid)

        #using 2nd order centered scheme for derivative
        aN_dr_th = (aNr_th-aNl_th)/(2.0*delta_r)*self.Lref

        #Note: Using the following analytic expression for the derivative doesn't work
        #as it neglects variations of theta with increased R,Z
#        aN_dr = ((self.geom.R[sort_ind]-self.R0)*dRdr[sort_ind]+
#                 (self.geom.Z[sort_ind]-self.Z0)*dZdr[sort_ind])/\
#                 (aN*self.R0)


        #now fourier transform
        fft_aN = np.fft.fft(aN_th)
        fft_aN_dr = np.fft.fft(aN_dr_th)

        #keep up to nth_kept modes (typically around 8)
        nth_kept = min(nz0,30)
        self.cN = 2.0*np.real(fft_aN)[0:nth_kept]/nth
        self.cN[0] *= 0.5
        self.sN = -2.0*np.imag(fft_aN)[0:nth_kept]/nth
        self.sN[0] *= 0.5
        self.cN_dr = 2.0*np.real(fft_aN_dr)[0:nth_kept]/nth
        self.cN_dr[0] *= 0.5
        self.sN_dr = -2.0*np.imag(fft_aN_dr)[0:nth_kept]/nth
        self.sN_dr[0] *= 0.5

        #check parametrization
        nind = np.arange(0.0,nth_kept,1.0)
        a_check = []
        a_dr_check = []
        for iz in range(0,nth):
            a_check += [np.sum(self.cN*np.cos(nind*theta_grid[iz])+
                               self.sN*np.sin(nind*theta_grid[iz]))]
            a_dr_check += [np.sum(self.cN_dr*np.cos(nind*theta_grid[iz])+
                                  self.sN_dr*np.sin(nind*theta_grid[iz]))]

        a_dr_check = np.array(a_dr_check)
        err = np.sum(np.abs(a_check-aN_th)/aN_th)/nth
        print ("Relative error of flux surface parametrization: {0:12.6E}".format(err))
        err = np.sum(np.abs(a_dr_check-aN_dr_th)/aN_dr_th)/nth
        print ("Relative error of flux surface derivative parametrization: {0:12.6E}".format(err))


        #Write information to screen
        print("")
        print("&geometry")
        print("magn_geometry = 'miller_general'")
        print("q0   =    ", self.cm.pnt.q0)
        print("shat =    ", self.cm.pnt.shat*self.dxdr*self.r/(self.cm.pnt.x0*self.cm.pnt.Lref))
        print("trpeps =  ", self.r/self.R0)
        print("major_R = ", self.R0/self.Lref)
        print("major_Z = ", self.Z0/self.Lref)
        self.B0 = self.cm.pnt.Bref*self.cm.pnt.Lref*self.cm.pnt.major_R/self.R0
        print("amhd =    ", self.cm.pnt.q0**2*self.cm.pnt.dpdx_pm*\
              (self.cm.pnt.Bref/self.B0)**2*self.dxdr*self.Lref/self.cm.pnt.Lref)
#        print("dpdx_pm = ", self.cm.pnt.dpdx_pm*self.Lref/self.cm.pnt.Lref*(self.cm.pnt.Bref/self.B0)**2*self.dxdr)
        print("")

        print ("cN_m = ",end="")
        for mode in self.cN:
            print ("{0:15.8e},".format(mode),end="")
        print("")
        print ("sN_m = ",end="")
        for mode in self.sN:
            print ("{0:15.8e},".format(mode),end="")
        print("")
        print ("cNdr_m = ",end="")
        for mode in self.cN_dr:
            print ("{0:15.8e},".format(mode),end="")
        print("")
        print ("sNdr_m = ",end="")
        for mode in self.sN_dr:
            print ("{0:15.8e},".format(mode),end="")
        print("")

        print("")
        print("sign_Bt_CW = ", self.cm.pnt.sign_Bt_CW)
        print("sign_Ip_CW = ", self.cm.pnt.sign_Ip_CW)
        print("")

        print("rhostar = -1")
        print("/")
        print("")

        print("")
        print("Lref = ",self.Lref)
        print("Bref = ",self.B0)
        print ("!grad. conversion: ", self.dxdr*self.Lref/self.cm.pnt.Lref)
        print("")

        #Gradient conversions
        print ("Lref_GENE/R0 = ", self.cm.pnt.Lref/self.R0)
        print ("Bref_new/Bref_old = ", self.B0/self.cm.pnt.Bref)
        print ("dx/dr = ", self.dxdr)
        #For comparison with Miller script in GENE:
        print ("drho_tor/dr = ", self.dxdr/self.cm.pnt.Lref)


        #some plot diagnostics
        show_aN = True
        if show_aN:
            plt.plot(theta_sort,aN,'x-',markersize=5,label='aN_orig')
#            plt.plot(theta_grid,aN_th,label='aN_interpol')
            plt.plot(theta_grid,a_check,label='aN_final')
#            plt.plot(theta_sort,aN_dr,'o-',markersize=5,label='aN_dr_orig')
            plt.plot(theta_grid,aN_dr_th,'o-',markersize=5,label='aN_dr interpol')
            plt.plot(theta_grid,a_dr_check,label='aN_dr_final')
            plt.legend()
            plt.show()

        show_flux_surface = True
        if show_flux_surface:
            dr = 0.05*self.r  #radial extension for testing

            #original data
            plt.plot(self.geom.R[sort_ind],self.geom.Z[sort_ind],'o-',markersize=3,label="original")
            plt.plot((self.geom.R[sort_ind]+dr*dRdr[sort_ind]),
                     (self.geom.Z[sort_ind]+dr*dZdr[sort_ind]),
                     'x-',markersize=3,label="original+dr")

            #aN and aN_dr from original data
#            R_check = self.R0+aN*np.cos(theta_sort)*self.R0
#            Z_check = self.Z0+aN*np.sin(theta_sort)*self.R0
#            plt.plot(R_check,Z_check,label="aN")

            if (dr==delta_r):
                R_check = self.R0+aNr*np.cos(thetar)*self.Lref
                Z_check = self.Z0+aNr*np.sin(thetar)*self.Lref
                plt.plot(R_check,Z_check,label="aNr")

            #interpolated aN and aN_dr
#            R_check = self.R0+aN_th*np.cos(theta_grid)*self.R0
#            Z_check = self.Z0+aN_th*np.sin(theta_grid)*self.R0
#           plt.plot(R_check,Z_check,label="aN_th")
#            R_check = self.R0+(aN_th+dr/self.R0*aN_dr_th)*np.cos(theta_grid)*self.R0
#            Z_check = self.Z0+(aN_th+dr/self.R0*aN_dr_th)*np.sin(theta_grid)*self.R0
#            plt.plot(R_check,Z_check,label="aN_dr_th")

            #flux surface from Fourier coefficients
            theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/(nth-1)
            R_check = self.R0+a_check*np.cos(theta_grid)*self.Lref
            Z_check = self.Z0+a_check*np.sin(theta_grid)*self.Lref
            plt.plot(R_check,Z_check,label="Gen. Miller")
            R_check = self.R0+(a_check+dr/self.Lref*a_dr_check)*np.cos(theta_grid)*self.Lref
            Z_check = self.Z0+(a_check+dr/self.Lref*a_dr_check)*np.sin(theta_grid)*self.Lref
            plt.plot(R_check,Z_check,label="Gen. Miller+dr")

            #rest of plotting
            plt.plot(self.R0,self.Z0,'o',markersize=2,color='black')
            plt.xlabel('R/m')
            plt.ylabel('Z/m')
            plt.axis('equal')
            plt.legend()
            plt.show()
