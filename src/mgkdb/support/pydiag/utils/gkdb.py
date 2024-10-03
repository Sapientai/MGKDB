""" gkdb.py: class handling data conversion and writing to the GyroKineticDataBase (https://github.com/gkdb/gkdb) """
import re
import os
import datetime
import numpy as np
import warnings
from collections import OrderedDict
from  .geom import Geometry
# import .comm
from ..data.omega_eigenvalue import Eigenvaluedata
from ..diagplots.plot_ball import ModeStructure

import json
#import .averages as averages
import matplotlib.pyplot as plt #remove later

class GKDB_linear(object):
    """ GKDB class:

    Converts the results of a GENE run into a GKDB-style json file

    Currently restricted to rotationless linear fluxtube simulations"
    """

    def __init__(self,common,rundatafiles,creator):
        # dictionary for gkdb parameters: {parameter: value}
        self.creator = creator
        self.cm = common
#        self.precheck()
        self.geom = Geometry(self.cm)
        self.fields = ["phi"]
        if common.electromagnetic:
            self.fields += ["apar"]
            if common.bpar:
                self.fields += ["bpar"]

        self.rundatafiles = rundatafiles
        self.gkdict = OrderedDict()
        self.set_gkdb_shape()
        self.set_gene2gkdb_conversion()
        self.fill_gkdb_from_par()
        

    def precheck(self):
        """ Run some basic checks before actual execution """
        if self.cm.nonlinear:
            raise RuntimeError("Nonlinear simulations not yet supported")
        else:
            if self.cm.pars['comp_type']=="'IV'":
                if self.cm.starttime!=-2 or self.cm.endtime!=-2:
                    print("*** WARNING: Selecting l:l as time window could be more appropriate ***")
            else:
                if (self.cm.starttime!=-1 and self.cm.starttime!=1) or \
                   (self.cm.endtime!=-2 and self.cm.endtime!=self.cm.pars["n_ev"]):
                    raise RuntimeError("Select f:l as time window for EV simulations")
        if self.cm.pars['magn_geometry']!="'miller'":
            raise RuntimeError("Only Miller geometries supported for now")


    def set_gkdb_shape(self):
        """ Determines shape parameters for GKDB """

        print ("Determining flux surface shape ...")
        nz0 = self.cm.pnt.nz0

        #determine flux surface center
        self.R0 = 0.5*(max(self.geom.R)+min(self.geom.R))
        self.Z0 = 0.5*(max(self.geom.Z)+min(self.geom.Z))
        print ("(R0,Z0) = (", self.R0, ",", self.Z0,")")
#        self.R0 = np.sum(self.geom.R*self.geom.jacobian)/np.sum(self.geom.jacobian)
#        self.Z0 = np.sum(self.geom.Z*self.geom.jacobian)/np.sum(self.geom.jacobian)

        #minor radius of flux surface
        self.r = 0.5*(max(self.geom.R)-min(self.geom.R))

        #poloidal theta (COCOS=11)
        self.theta = np.arctan(-(self.geom.Z-self.Z0)/(self.geom.R-self.R0))
        for iz in range(int(nz0/2),nz0-1):
            thetadiff = (self.theta[iz+1]-self.theta[iz])
            if thetadiff>0.5*np.pi:
                self.theta[iz+1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                self.theta[iz+1]+=np.pi
            thetadiff = (self.theta[nz0-1-iz-1]-self.theta[nz0-1-iz])
            if thetadiff>0.5*np.pi:
                self.theta[nz0-1-iz-1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                self.theta[nz0-1-iz-1]+=np.pi

        #sorted theta (starting at th=0)
        theta_sort = (self.theta+2.0*np.pi)%(2.0*np.pi)
        sort_ind = np.argsort(theta_sort)
        theta_sort = theta_sort[sort_ind]

        #Flux surface distance (original grid and normalized)
        aN = np.sqrt((self.geom.R[sort_ind]-self.R0)**2+(self.geom.Z[sort_ind]-self.Z0)**2)/self.R0
        aN_dr = ((self.geom.R[sort_ind]-self.R0)*self.geom.dxdR[sort_ind]+
                 (self.geom.Z[sort_ind]-self.Z0)*self.geom.dxdZ[sort_ind])/\
            (aN*self.geom.gxx[sort_ind])/self.R0

        #equidistant theta (COCOS=11) with somewhat higher resolution for fourier transforms etc
        nth = 4*nz0
        theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/nth

        #interpolate to this equidist. grid with proper order (interpol requires increasing arr)
        aN_th = np.interp(theta_grid,theta_sort,aN,period=2.0*np.pi)
        aN_dr_th = np.interp(theta_grid,theta_sort,aN_dr,period=2.0*np.pi)

        #now fourier transform
        fft_aN = np.fft.fft(aN_th)
        fft_aN_dr = np.fft.fft(aN_dr_th)

        #keep up to nth_kept modes (typically around 8)
        nth_kept = 8 #nz0
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

        #some plot diagnostics
        show_aN = False
        if show_aN:
            plt.plot(theta_sort,aN,label='aN_orig')
            plt.plot(theta_grid,aN_th,label='aN_th,intermediate')
            plt.plot(theta_grid,a_check,label='aN_final')
            plt.plot(theta_sort,aN_dr,label='aN_dr_orig')
            plt.plot(theta_grid,a_dr_check,label='aN_dr_final')
            plt.legend()
            plt.show()

        show_flux_surface = False
        if show_flux_surface:
            dr = 0.04  #radial extension for testing

            plt.plot(self.geom.R[sort_ind],self.geom.Z[sort_ind],'o',label="original")
            plt.plot((self.geom.R[sort_ind]+dr*self.geom.dxdR[sort_ind]/self.geom.gxx[sort_ind]),
                     (self.geom.Z[sort_ind]+dr*self.geom.dxdZ[sort_ind]/self.geom.gxx[sort_ind]),
                     'x',label="original+dr")
            theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/(nth-1)
            # R_n_th = self.R0+aN_th*np.cos(theta_grid)
            # Z_n_th = self.Z0-aN_th*np.sin(theta_grid)
            # plt.plot(R_n_th,Z_n_th,label="intermediate")
            R_check = self.R0+a_check*np.cos(theta_grid)*self.R0
            Z_check = self.Z0-a_check*np.sin(theta_grid)*self.R0
            plt.plot(R_check,Z_check,label="gkdb")
            R_check = self.R0+(a_check+dr/self.R0*a_dr_check)*np.cos(theta_grid)*self.R0
            Z_check = self.Z0-(a_check+dr/self.R0*a_dr_check)*np.sin(theta_grid)*self.R0
            plt.plot(R_check,Z_check,label="gkdb+dr")
            plt.xlabel('R/m')
            plt.ylabel('Z/m')
            plt.axis('equal')
            plt.legend()
            plt.show()

    def set_gene2gkdb_conversion(self):
        """ set conversion factors for various quantities """

        print ("Setting conversion factors ...")

        #determine index of electron species
        ispec_electrons = -1111
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) + 1
            if self.cm.pars["charge{}".format(ispec)]==-1:
                ispec_electrons = ispec

        self.gene2gkdb = OrderedDict()
        self.gene2gkdb["Lref"] = self.cm.pnt.Lref/self.R0 #Lref_GENE/Lref_GKDB
        self.gene2gkdb["Bref"] = self.cm.pnt.Lref*self.cm.pnt.major_R/self.R0  #JUST 1/R correction for the moment
        print ("Bref_GENE/Bref_GKDB = ", self.gene2gkdb["Bref"])

        #CHECK THIS: x dimensionless, r dimensional
#        self.gene2gkdb["dxdr"] = np.sqrt(np.interp(0.0,self.theta,self.geom.gxx,period=2.0*np.pi)) #CHECK THIS
        self.gene2gkdb["dxdr"] = 1.0/(0.5*(self.geom.dxdR[np.argmax(self.geom.R)]/self.geom.gxx[np.argmax(self.geom.R)]-\
                                      self.geom.dxdR[np.argmin(self.geom.R)]/self.geom.gxx[np.argmin(self.geom.R)]))
#        self.gene2gkdb["dxdr"] = 2.0/(self.geom.gxx[np.argmax(self.geom.R)]/self.geom.dxdR[np.argmax(self.geom.R)]-
#                                      self.geom.gxx[np.argmin(self.geom.R)]/self.geom.dxdR[np.argmin(self.geom.R)])

        self.gene2gkdb["Tref"] = 1.0/self.cm.pars["temp{}".format(ispec_electrons)] #Tref_GENE/Tref_GKDB
        self.gene2gkdb["mref"] = self.cm.pnt.mref/1.999007501778479 #mref_GENE/mref_GKDB (in units of proton mass)
        self.gene2gkdb["nref"] = 1.0/self.cm.pars["dens{}".format(ispec_electrons)] #nref_GENE/nref_GKDB
        self.gene2gkdb["qref"] = 1.0

        print ("Lref_GENE/Lref_GKDB = ", self.gene2gkdb["Lref"])
        print ("dx_GENE/dr_GKDB = ", self.gene2gkdb["dxdr"])

        #derived quantity conversion
        self.gene2gkdb["vth"]  = np.sqrt(0.5*self.gene2gkdb["Tref"]/self.gene2gkdb["mref"]) #cref_GENE/vth_GKDB
        self.gene2gkdb["rho"]  = self.gene2gkdb["mref"]*self.gene2gkdb["vth"]/(self.gene2gkdb["qref"]*self.gene2gkdb["Bref"])
        self.gene2gkdb["rho_Lref"] = self.gene2gkdb["rho"]/self.gene2gkdb["Lref"]

        print ("rho_Lref_GENE/rho_Lref_GKDB = ", self.gene2gkdb["rho_Lref"])

        #field conversion
        self.gene2gkdb["phi"] = self.gene2gkdb["Tref"]/self.gene2gkdb["qref"]*self.gene2gkdb["rho_Lref"]
        self.gene2gkdb["apar"] = self.gene2gkdb["Lref"]*self.gene2gkdb["Bref"]*self.gene2gkdb["rho_Lref"]**2
        self.gene2gkdb["bpar"] = self.gene2gkdb["Bref"]*self.gene2gkdb["rho_Lref"]

        #moments conversions (may be species dependent)
        self.gene2gkdb["dens"] = []
        self.gene2gkdb["upar"] = []
        self.gene2gkdb["tpar"] = []
        self.gene2gkdb["tperp"] = []
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) + 1
            self.gene2gkdb["dens"] += [self.gene2gkdb["nref"]*self.gene2gkdb["rho_Lref"]*\
                                       self.cm.pars["dens{}".format(ispec)]]
            self.gene2gkdb["upar"] += [self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"]]
            self.gene2gkdb["tpar"] += [self.gene2gkdb["Tref"]*self.gene2gkdb["rho_Lref"]*\
                                       self.cm.pars["temp{}".format(ispec)]]
            self.gene2gkdb["tperp"] += [self.gene2gkdb["Tref"]*self.gene2gkdb["rho_Lref"]*\
                                        self.cm.pars["temp{}".format(ispec)]]

        #fluxes
        self.gene2gkdb["pflux"] = self.gene2gkdb["nref"]*self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"]**2
        self.gene2gkdb["mflux"] = self.gene2gkdb["nref"]*self.gene2gkdb["mref"]*self.gene2gkdb["Lref"]*\
                                  (self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"])**2   #LREF?
        self.gene2gkdb["qflux"] = self.gene2gkdb["Tref"]*self.gene2gkdb["pflux"]

    def fill_gkdb_from_par(self):
        """ Fill gkdb dict """
        pars = self.cm.pars
        geom = self.geom
        rat = self.gene2gkdb

        self.gkdict.clear()
        self.gkdict["ids_properties"] = {#"creator" : os.environ['USER'],
                                "creator" : self.creator,
                                "date" : str(datetime.date.today()),
                                "comment" : "json entry for testing only - note that "+\
                                "mode structure moments and flux-surface averaged fluxes "+\
                                "are given in particle space (i.e. incl. the full pullback operator)\n "+\
                                "EM flux contributions are for now *not* separated and all attributed "+\
                                "to the Apar term"
                            }
        self.gkdict["code"] = {"name": "GENE",
                               "version" : pars['RELEASE']+' - '+(pars['GIT_MASTER'])[0:9],
                               "parameters" : pars
                           }


        self.gkdict["model"] = {
            "initial_value_run": pars['comp_type']=="'IV'",
            "non_linear_run": self.cm.nonlinear,
            "time_interval_norm" : [], #FILL
            "include_a_field_parallel" : self.cm.electromagnetic,
            "include_b_field_parallel" : self.cm.bpar,
            "include_full_curvature_drift" : (True if pars['dpdx_pm']==0 else
                                              pars['dpdx_term']=='full_drift'),
            "include_centrifugal_effects" : pars['with_centrifugal'],
            "collision_pitch_only" : pars['collision_op']=="'pitch_angle'",
            "collision_ei_only" : False,
            "collision_momentum_conservation" : (pars['coll_cons_model']!='none'
                                                 if pars['coll'] > 0.0 else False),
            "collision_energy_conservation" :  (pars['coll_cons_model']!='none'
                                                if pars['coll'] > 0.0 else False),
            "collision_finite_larmor_radius" : pars['collision_op']=='sugama', #CHECK THIS (WITH_FLR = T ALSO?)
        }

        s_Ip = -pars['sign_Ip_CW']
        s_Bt = -pars['sign_Bt_CW']

        self.gkdict["flux_surface"] = {
            "r_minor_norm" : self.r/self.R0,
            "q" : s_Ip*s_Bt*np.abs(pars['q0']),
            "magnetic_shear_r_minor" : pars['shat']*self.r/rat["Lref"]/pars['x0']*rat["dxdr"], #CHECK Lref HERE
            "pressure_gradient_norm" : pars['dpdx_pm']/rat["Lref"]*rat["Bref"]**2*rat["dxdr"],
            "ip_sign" : s_Ip,
            "b_field_tor_sign" : s_Bt,
            # Original shape
            "shape_coefficients_c" : self.cN.tolist(), #NORMALIZATION?
            "shape_coefficients_s" : self.sN.tolist(), #NORMALIZATION?
            "dc_dr_minor_norm" : self.cN_dr.tolist(),
            "ds_dr_minor_norm" : self.sN_dr.tolist(),
            # Derived from Shape
            "elongation" : (pars['kappa'] if pars['magn_geometry']=="'miller'" else None),
            "triangularity_upper" : (pars['delta'] if pars['magn_geometry']=="'miller'" else None),
            "triangularity_lower" : (pars['delta'] if pars['magn_geometry']=="'miller'" else None),
        }


        self.gkdict["species_all"] = {
            "beta_reference" : pars['beta']/(rat["nref"]*rat["Tref"])*rat["Bref"]**2,
            "debye_length_reference" : np.sqrt(pars['debye2']), #ADD FACTORS
            "velocity_tor_norm" : pars["Omega0_tor"]*rat["vth"]/rat["Lref"],
            "shearing_rate_norm" : pars["ExBrate"]*self.r/pars["x0"]*\
                rat["vth"]/rat["Lref"]*rat["dxdr"],
            "zeff" : None #pars['Zeff'] #self-consistent computation by data base itself?
        }

        self.gkdict["species"] = []
        self.gkdict["collisions"] = {}
        self.gkdict["collisions"]["collisionality_norm"] = []

#        coulomb_log = 24.-np.log(np.sqrt(self.cm.pnt.nref*1E13)/
#                                self.cm.pnt.Tref*0.001)

        for ispec in range(1,pars['n_spec']+1):
            self.gkdict["species"] += [{
                "name" : self.cm.pars["name{}".format(ispec)],
                "charge_norm" : self.cm.pars["charge{}".format(ispec)],
                "mass_norm" : self.cm.pars["mass{}".format(ispec)]*rat["mref"],
                "density_norm" : (0.0 if self.cm.pars["passive{}".format(ispec)] else
                                  self.cm.pars["dens{}".format(ispec)]*rat["nref"]),
                "temperature_norm" : self.cm.pars["temp{}".format(ispec)]*rat["Tref"],
                "density_log_gradient_norm" : self.cm.pars["omn{}".format(ispec)]/rat["Lref"]*rat["dxdr"],
                "temperature_log_gradient_norm" : self.cm.pars["omt{}".format(ispec)]/rat["Lref"]*rat["dxdr"],
                "velocity_tor_gradient_norm" : pars["ExBrate"]*pars["q0"]/pars["x0"]*\
                rat["vth"]/rat["Lref"]*rat["dxdr"]
            }]

        for ispec in range(0,pars['n_spec']):
            ijcoll = []
            for jspec in range(0,pars['n_spec']):
                ijcoll += [(0.0 if self.cm.pars["passive{}".format(jspec+1)] else
                            rat["Tref"]**2/(np.sqrt(2.0)*np.pi*rat["qref"]**4*rat["Lref"]*rat["nref"])*\
                            self.gkdict["species"][ispec]["charge_norm"]**2*
                            self.gkdict["species"][jspec]["charge_norm"]**2*
                            self.gkdict["species"][jspec]["density_norm"]/\
                            np.sqrt(self.gkdict["species"][jspec]["mass_norm"]*
                                    self.gkdict["species"][jspec]["temperature_norm"]**3)*\
                            pars['coll'])]
            self.gkdict["collisions"]["collisionality_norm"] += [ijcoll]

        Cyq0_x0 = geom.Cy * self.cm.pnt.q0 / self.cm.pnt.x0
        if self.cm.pnt.adapt_lx:
            absnexc = 1
        else:
            absnexc = int(np.round(self.cm.pnt.lx*self.cm.pnt.n_pol*
                    np.abs(self.cm.pnt.shat)*self.cm.pnt.kymin*
                    np.abs(Cyq0_x0)))
            
#        nconn = int(int(int(self.cm.pnt.nx0-1)/2)/(absnexc*self.cm.pnt.ky0_ind))*2+1
        divisor = absnexc*self.cm.pnt.ky0_ind
        if divisor==0:
            nconn = 0
        else:
            nconn = int(int(int(self.cm.pnt.nx0-1)/2)/(absnexc*self.cm.pnt.ky0_ind))*2+1

        theta_full = []
        for iconn in range(-int(nconn/2),int(nconn/2)+1):
            theta_full += list(self.theta-np.sign(self.theta[0])*iconn*2.0*np.pi)
        fullsort_ind = np.argsort(theta_full)
        thetasort = np.array(theta_full)[fullsort_ind]


        #transformation of wavevector components on a z grid
        #following D. Told, PhD thesis, Sec. A.3, p. 167
        k1facx = np.sqrt(geom.gxx)
        k1facy = geom.gxy/np.sqrt(geom.gxx)
        k2fac = np.sqrt(geom.gyy-geom.gxy**2/geom.gxx)

        #now interpolate to theta = 0
        #interpolate to equidist. grid with proper order (interpol requires increasing arr)
        sort_ind = np.argsort(self.theta)
        k1facx_th0 = np.interp(0.0,self.theta[sort_ind],k1facx[sort_ind])/rat["rho"]
        k1facy_th0 = np.interp(0.0,self.theta[sort_ind],k1facy[sort_ind])/rat["rho"]
        k2fac_th0 = np.interp(0.0,self.theta[sort_ind],k2fac[sort_ind])/rat["rho"]

        ky = self.cm.pnt.kymin*self.cm.pnt.ky0_ind
        k1val = (self.cm.pnt.kx_center*k1facx_th0+ky*k1facy_th0)
        k2val = ky*k2fac_th0

        print ("k1facx_th0, k1facy_th0, k2fac_th0: ", k1facx_th0, k1facy_th0, k2fac_th0)

        # Finished writing physics inputs
        ###########################################################################################################
        # Now starting outputs

        eigendat = Eigenvaluedata(self.cm)

#        print('======{}========'.format(eigendat.growth_rate))
        if len(eigendat.growth_rate)>1 and max(eigendat.growth_rate) <= 0.0:
            raise RuntimeError("No unstable growth rate found - skipping file")

        nrgdat = self.rundatafiles.get_fileobject("nrg")
        nrgdat.generate_timeseries()

        newfieldnames = {"phi" : "phi_potential_perturbed_norm",
                         "apar" : "a_field_parallel_perturbed_norm",
                         "bpar" : "b_field_parallel_perturbed_norm"}

        newmomnames = { "dens" : "density",
                        "upar" : "velocity_parallel",
                        "tpar" : "temperature_parallel",
                        "tperp" : "temperature_perpendicular"}

        fieldmodestruct = ModeStructure(self.cm, self.rundatafiles,tavg=False)
        mommodestruct = []
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) #w/o +1
            mommodestruct += [ModeStructure(self.cm, self.rundatafiles, \
                                moms=list(newmomnames.keys()), species=spec,tavg=False)]

        eigenmodes = []

        if self.gkdict["model"]["initial_value_run"]:
            ievrange=[-1,]
        else:
            ievrange=range(len(eigendat.growth_rate))

        for iev in ievrange:
            if eigendat.growth_rate[iev] <= 0.0:
                continue

            eigenmode = {
                "growth_rate_norm" : eigendat.growth_rate[iev]*rat["vth"]/rat["Lref"],
                "frequency_norm" : eigendat.frequency[iev]*rat["vth"]/rat["Lref"],
                "growth_rate_tolerance": self.cm.pnt.omega_prec*rat["vth"]/rat["Lref"],
                "poloidal_angle" : thetasort.tolist()
            }

            #determine normalization amplitude and phase for parallel mode structures
            Af_gkdb = 0.0
            for field in self.fields:
                Af_gkdb += np.trapz(np.abs(fieldmodestruct.ballamps[field][iev][fullsort_ind]*rat[field])**2,thetasort)
            Af_gkdb = np.sqrt(Af_gkdb/(2.0*np.pi))
            alpha_gkdb = -np.interp(0.0,thetasort,np.angle(fieldmodestruct.ballamps["phi"][iev][fullsort_ind]))
            print ("Af_gkdb = ", Af_gkdb, ", alpha_gkdb = ", alpha_gkdb)

            for var in fieldmodestruct.ballamps.keys():
                print ("writing mode structure of ", var)
                eigenmode[newfieldnames[var]+"_real"]=np.real(fieldmodestruct.ballamps[var][iev][fullsort_ind]*
                                                        rat[var]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                eigenmode[newfieldnames[var]+"_imaginary"]=np.imag(fieldmodestruct.ballamps[var][iev][fullsort_ind]*
                                                            rat[var]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()

            eigenmode["moments_norm_rotating_frame"] = []
            for spec in self.cm.specnames:
                ispec = self.cm.specnames.index(spec) #w/o +1
#                mommodestruct = ModeStructure(self.cm, self.rundatafiles, moms=list(newmomnames.keys()), \
#                                                         species=spec,tavg=False)
                spec_moments_norm_rotating_frame = {}
                for var in newmomnames.keys():
                    spec_moments_norm_rotating_frame[newmomnames[var]+"_real"] = \
                                np.real(mommodestruct[ispec].ballamps[var][iev][fullsort_ind]*\
                                rat[var][ispec]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                    spec_moments_norm_rotating_frame[newmomnames[var]+"_imaginary"] = \
                                np.imag(mommodestruct[ispec].ballamps[var][iev][fullsort_ind]*\
                                rat[var][ispec]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                eigenmode["moments_norm_rotating_frame"] += [spec_moments_norm_rotating_frame]


            eigenmode["fluxes_norm"] = []
            #NOTE: GENE NRG-FILES DO NOT ALLOW FOR SEPARATION OF A/B_FIELD_PARALLEL CONTRIBUTIONS
            #CURRENTLY BOTH OF THEM ARE ATTRIBUTED TO A_FIELD_PARALLEL
            #ALTERNATIVE: RECOMPUTE FLUXES FROM MOM-FILES (Pullback will still contain both fields though)
            for spec in self.cm.specnames:
                ispec = self.cm.specnames.index(spec) #w/o +1
                eigenmode["fluxes_norm"] += [{
                    "particles_phi_potential": nrgdat.dataarray[iev,ispec,4]*rat["pflux"]*(1.0/Af_gkdb)**2,
                    "particles_a_field_parallel": nrgdat.dataarray[iev,ispec,5]*rat["pflux"]*(rat["rho_Lref"]/Af_gkdb)**2,      #FIX THIS
                    "particles_b_field_parallel": nrgdat.dataarray[iev,ispec,5]*rat["pflux"]*(1.0/Af_gkdb)**2*0.0,  #FIX THIS -- SET TO ZERO
                    "momentum_tor_parallel_phi_potential": nrgdat.dataarray[iev,ispec,8]*rat["mflux"]*(1.0/Af_gkdb)**2,
                    "momentum_tor_parallel_a_field_parallel": nrgdat.dataarray[iev,ispec,9]*rat["mflux"]*(1.0/Af_gkdb)**2,      #FIX THIS
                    "momentum_tor_parallel_b_field_parallel": nrgdat.dataarray[iev,ispec,9]*rat["mflux"]*(1.0/Af_gkdb)**2*0.0,  #FIX THIS -- SET TO ZERO
                    "momentum_tor_perpendicular_phi_potential": None,
                    "momentum_tor_perpendicular_a_field_parallel": None,
                    "momentum_tor_perpendicular_b_field_parallel": None,
                    "energy_phi_potential": nrgdat.dataarray[iev,ispec,6]*rat["qflux"]*(1.0/Af_gkdb)**2,
                    "energy_a_field_parallel": nrgdat.dataarray[iev,ispec,7]*rat["qflux"]*(1.0/Af_gkdb)**2,     #FIX THIS
                    "energy_b_field_parallel": nrgdat.dataarray[iev,ispec,7]*rat["qflux"]*(1.0/Af_gkdb)**2*0.0  #FIX THIS -- SET TO ZERO
                }]
            eigenmodes += [eigenmode]


        self.gkdict["wavevector"] = [{
            "radial_component_norm" : k1val,
            "binormal_component_norm" : k2val,
            "poloidal_turns" : nconn,
            "eigenmode" : eigenmodes
        }]

        self.gkdict["fluxes_integrated_norm"] = []

    def Write_json(self, path):
        """ Take the dict and write a gkdb json parameters file """
        #        print(json.dumps(self.gkdict, indent=4))
        filename = 'data{}.json'.format(self.cm.fileextension)
        with open(filename, 'w') as fp:
            json.dump(self.gkdict, fp, indent=4,separators=(',', ': '))



class GKDB_nonlin(object):
    """ GKDB class:

    Converts the results of a nonlinear GENE run into a GKDB-style json file

    """

    def __init__(self,common,rundatafiles,creator):
        # dictionary for gkdb parameters: {parameter: value}
        self.creator = creator
        self.cm = common
#        self.precheck()
        self.geom = Geometry(self.cm)
        self.fields = ["phi"]
        if common.electromagnetic:
            self.fields += ["apar"]
            if common.bpar:
                self.fields += ["bpar"]

        self.rundatafiles = rundatafiles
        self.gkdict = OrderedDict()
        self.set_gkdb_shape()
        self.set_gene2gkdb_conversion()
        self.fill_gkdb_from_par()
        

    def precheck(self):
        """ Run some basic checks before actual execution """
        if self.cm.nonlinear:
            raise RuntimeError("Nonlinear simulations not yet supported")
        else:
            if self.cm.pars['comp_type']=="'IV'":
                if self.cm.starttime!=-2 or self.cm.endtime!=-2:
                    print("*** WARNING: Selecting l:l as time window could be more appropriate ***")
            else:
                if (self.cm.starttime!=-1 and self.cm.starttime!=1) or \
                   (self.cm.endtime!=-2 and self.cm.endtime!=self.cm.pars["n_ev"]):
                    raise RuntimeError("Select f:l as time window for EV simulations")
        if self.cm.pars['magn_geometry']!="'miller'":
            raise RuntimeError("Only Miller geometries supported for now")


    def set_gkdb_shape(self):
        """ Determines shape parameters for GKDB """

        print ("Determining flux surface shape ...")
        nz0 = self.cm.pnt.nz0

        #determine flux surface center
        self.R0 = 0.5*(max(self.geom.R)+min(self.geom.R))
        self.Z0 = 0.5*(max(self.geom.Z)+min(self.geom.Z))
        print ("(R0,Z0) = (", self.R0, ",", self.Z0,")")
#        self.R0 = np.sum(self.geom.R*self.geom.jacobian)/np.sum(self.geom.jacobian)
#        self.Z0 = np.sum(self.geom.Z*self.geom.jacobian)/np.sum(self.geom.jacobian)

        #minor radius of flux surface
        self.r = 0.5*(max(self.geom.R)-min(self.geom.R))

        #poloidal theta (COCOS=11)
        self.theta = np.arctan(-(self.geom.Z-self.Z0)/(self.geom.R-self.R0))
        for iz in range(int(nz0/2),nz0-1):
            thetadiff = (self.theta[iz+1]-self.theta[iz])
            if thetadiff>0.5*np.pi:
                self.theta[iz+1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                self.theta[iz+1]+=np.pi
            thetadiff = (self.theta[nz0-1-iz-1]-self.theta[nz0-1-iz])
            if thetadiff>0.5*np.pi:
                self.theta[nz0-1-iz-1]-=np.pi
            elif thetadiff<-0.5*np.pi:
                self.theta[nz0-1-iz-1]+=np.pi

        #sorted theta (starting at th=0)
        theta_sort = (self.theta+2.0*np.pi)%(2.0*np.pi)
        sort_ind = np.argsort(theta_sort)
        theta_sort = theta_sort[sort_ind]

        #Flux surface distance (original grid and normalized)
        aN = np.sqrt((self.geom.R[sort_ind]-self.R0)**2+(self.geom.Z[sort_ind]-self.Z0)**2)/self.R0
        aN_dr = ((self.geom.R[sort_ind]-self.R0)*self.geom.dxdR[sort_ind]+
                 (self.geom.Z[sort_ind]-self.Z0)*self.geom.dxdZ[sort_ind])/\
            (aN*self.geom.gxx[sort_ind])/self.R0

        #equidistant theta (COCOS=11) with somewhat higher resolution for fourier transforms etc
        nth = 4*nz0
        theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/nth

        #interpolate to this equidist. grid with proper order (interpol requires increasing arr)
        aN_th = np.interp(theta_grid,theta_sort,aN,period=2.0*np.pi)
        aN_dr_th = np.interp(theta_grid,theta_sort,aN_dr,period=2.0*np.pi)

        #now fourier transform
        fft_aN = np.fft.fft(aN_th)
        fft_aN_dr = np.fft.fft(aN_dr_th)

        #keep up to nth_kept modes (typically around 8)
        nth_kept = 8 #nz0
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

        #some plot diagnostics
        show_aN = False
        if show_aN:
            plt.plot(theta_sort,aN,label='aN_orig')
            plt.plot(theta_grid,aN_th,label='aN_th,intermediate')
            plt.plot(theta_grid,a_check,label='aN_final')
            plt.plot(theta_sort,aN_dr,label='aN_dr_orig')
            plt.plot(theta_grid,a_dr_check,label='aN_dr_final')
            plt.legend()
            plt.show()

        show_flux_surface = False
        if show_flux_surface:
            dr = 0.04  #radial extension for testing

            plt.plot(self.geom.R[sort_ind],self.geom.Z[sort_ind],'o',label="original")
            plt.plot((self.geom.R[sort_ind]+dr*self.geom.dxdR[sort_ind]/self.geom.gxx[sort_ind]),
                     (self.geom.Z[sort_ind]+dr*self.geom.dxdZ[sort_ind]/self.geom.gxx[sort_ind]),
                     'x',label="original+dr")
            theta_grid = (np.arange(0.0,nth,1.0))*2.0*np.pi/(nth-1)
            # R_n_th = self.R0+aN_th*np.cos(theta_grid)
            # Z_n_th = self.Z0-aN_th*np.sin(theta_grid)
            # plt.plot(R_n_th,Z_n_th,label="intermediate")
            R_check = self.R0+a_check*np.cos(theta_grid)*self.R0
            Z_check = self.Z0-a_check*np.sin(theta_grid)*self.R0
            plt.plot(R_check,Z_check,label="gkdb")
            R_check = self.R0+(a_check+dr/self.R0*a_dr_check)*np.cos(theta_grid)*self.R0
            Z_check = self.Z0-(a_check+dr/self.R0*a_dr_check)*np.sin(theta_grid)*self.R0
            plt.plot(R_check,Z_check,label="gkdb+dr")
            plt.xlabel('R/m')
            plt.ylabel('Z/m')
            plt.axis('equal')
            plt.legend()
            plt.show()

    def set_gene2gkdb_conversion(self):
        """ set conversion factors for various quantities """

        print ("Setting conversion factors ...")

        #determine index of electron species
        ispec_electrons = -1111
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) + 1
            if self.cm.pars["charge{}".format(ispec)]==-1:
                ispec_electrons = ispec

        self.gene2gkdb = OrderedDict()
        self.gene2gkdb["Lref"] = self.cm.pnt.Lref/self.R0 #Lref_GENE/Lref_GKDB
        self.gene2gkdb["Bref"] = self.cm.pnt.Lref*self.cm.pnt.major_R/self.R0  #JUST 1/R correction for the moment
        print ("Bref_GENE/Bref_GKDB = ", self.gene2gkdb["Bref"])

        #CHECK THIS: x dimensionless, r dimensional
#        self.gene2gkdb["dxdr"] = np.sqrt(np.interp(0.0,self.theta,self.geom.gxx,period=2.0*np.pi)) #CHECK THIS
        self.gene2gkdb["dxdr"] = 1.0/(0.5*(self.geom.dxdR[np.argmax(self.geom.R)]/self.geom.gxx[np.argmax(self.geom.R)]-\
                                      self.geom.dxdR[np.argmin(self.geom.R)]/self.geom.gxx[np.argmin(self.geom.R)]))
#        self.gene2gkdb["dxdr"] = 2.0/(self.geom.gxx[np.argmax(self.geom.R)]/self.geom.dxdR[np.argmax(self.geom.R)]-
#                                      self.geom.gxx[np.argmin(self.geom.R)]/self.geom.dxdR[np.argmin(self.geom.R)])

        self.gene2gkdb["Tref"] = 1.0/self.cm.pars["temp{}".format(ispec_electrons)] #Tref_GENE/Tref_GKDB
        self.gene2gkdb["mref"] = self.cm.pnt.mref/1.999007501778479 #mref_GENE/mref_GKDB (in units of proton mass)
        self.gene2gkdb["nref"] = 1.0/self.cm.pars["dens{}".format(ispec_electrons)] #nref_GENE/nref_GKDB
        self.gene2gkdb["qref"] = 1.0

        print ("Lref_GENE/Lref_GKDB = ", self.gene2gkdb["Lref"])
        print ("dx_GENE/dr_GKDB = ", self.gene2gkdb["dxdr"])

        #derived quantity conversion
        self.gene2gkdb["vth"]  = np.sqrt(0.5*self.gene2gkdb["Tref"]/self.gene2gkdb["mref"]) #cref_GENE/vth_GKDB
        self.gene2gkdb["rho"]  = self.gene2gkdb["mref"]*self.gene2gkdb["vth"]/(self.gene2gkdb["qref"]*self.gene2gkdb["Bref"])
        self.gene2gkdb["rho_Lref"] = self.gene2gkdb["rho"]/self.gene2gkdb["Lref"]

        print ("rho_Lref_GENE/rho_Lref_GKDB = ", self.gene2gkdb["rho_Lref"])

        #field conversion
        self.gene2gkdb["phi"] = self.gene2gkdb["Tref"]/self.gene2gkdb["qref"]*self.gene2gkdb["rho_Lref"]
        self.gene2gkdb["apar"] = self.gene2gkdb["Lref"]*self.gene2gkdb["Bref"]*self.gene2gkdb["rho_Lref"]**2
        self.gene2gkdb["bpar"] = self.gene2gkdb["Bref"]*self.gene2gkdb["rho_Lref"]

        #moments conversions (may be species dependent)
        self.gene2gkdb["dens"] = []
        self.gene2gkdb["upar"] = []
        self.gene2gkdb["tpar"] = []
        self.gene2gkdb["tperp"] = []
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) + 1
            self.gene2gkdb["dens"] += [self.gene2gkdb["nref"]*self.gene2gkdb["rho_Lref"]*\
                                       self.cm.pars["dens{}".format(ispec)]]
            self.gene2gkdb["upar"] += [self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"]]
            self.gene2gkdb["tpar"] += [self.gene2gkdb["Tref"]*self.gene2gkdb["rho_Lref"]*\
                                       self.cm.pars["temp{}".format(ispec)]]
            self.gene2gkdb["tperp"] += [self.gene2gkdb["Tref"]*self.gene2gkdb["rho_Lref"]*\
                                        self.cm.pars["temp{}".format(ispec)]]

        #fluxes
        self.gene2gkdb["pflux"] = self.gene2gkdb["nref"]*self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"]**2
        self.gene2gkdb["mflux"] = self.gene2gkdb["nref"]*self.gene2gkdb["mref"]*self.gene2gkdb["Lref"]*\
                                  (self.gene2gkdb["vth"]*self.gene2gkdb["rho_Lref"])**2   #LREF?
        self.gene2gkdb["qflux"] = self.gene2gkdb["Tref"]*self.gene2gkdb["pflux"]

    def fill_gkdb_from_par(self):
        """ Fill gkdb dict """
        pars = self.cm.pars
        geom = self.geom
        rat = self.gene2gkdb

        self.gkdict.clear()
        self.gkdict["ids_properties"] = {#"creator" : os.environ['USER'],
                                "creator" : self.creator,
                                "date" : str(datetime.date.today()),
                                "comment" : "json entry for testing only - note that "+\
                                "mode structure moments and flux-surface averaged fluxes "+\
                                "are given in particle space (i.e. incl. the full pullback operator)\n "+\
                                "EM flux contributions are for now *not* separated and all attributed "+\
                                "to the Apar term"
                            }
        self.gkdict["code"] = {"name": "GENE",
                               "version" : pars['RELEASE']+' - '+(pars['GIT_MASTER'])[0:9],
                               "parameters" : pars
                           }


        self.gkdict["model"] = {
            "initial_value_run": pars['comp_type']=="'IV'",
            "non_linear_run": self.cm.nonlinear,
            "time_interval_norm" : [], #FILL
            "include_a_field_parallel" : self.cm.electromagnetic,
            "include_b_field_parallel" : self.cm.bpar,
            "include_full_curvature_drift" : (True if pars['dpdx_pm']==0 else
                                              pars['dpdx_term']=='full_drift'),
            "include_centrifugal_effects" : pars['with_centrifugal'],
            "collision_pitch_only" : pars['collision_op']=="'pitch_angle'",
            "collision_ei_only" : False,
            "collision_momentum_conservation" : (pars['coll_cons_model']!='none'
                                                 if pars['coll'] > 0.0 else False),
            "collision_energy_conservation" :  (pars['coll_cons_model']!='none'
                                                if pars['coll'] > 0.0 else False),
            "collision_finite_larmor_radius" : pars['collision_op']=='sugama', #CHECK THIS (WITH_FLR = T ALSO?)
        }

        s_Ip = -pars['sign_Ip_CW']
        s_Bt = -pars['sign_Bt_CW']

        self.gkdict["flux_surface"] = {
            "r_minor_norm" : self.r/self.R0,
            "q" : s_Ip*s_Bt*np.abs(pars['q0']),
            "magnetic_shear_r_minor" : pars['shat']*self.r/rat["Lref"]/pars['x0']*rat["dxdr"], #CHECK Lref HERE
            "pressure_gradient_norm" : pars['dpdx_pm']/rat["Lref"]*rat["Bref"]**2*rat["dxdr"],
            "ip_sign" : s_Ip,
            "b_field_tor_sign" : s_Bt,
            # Original shape
            "shape_coefficients_c" : self.cN.tolist(), #NORMALIZATION?
            "shape_coefficients_s" : self.sN.tolist(), #NORMALIZATION?
            "dc_dr_minor_norm" : self.cN_dr.tolist(),
            "ds_dr_minor_norm" : self.sN_dr.tolist(),
            # Derived from Shape
            "elongation" : (pars['kappa'] if pars['magn_geometry']=="'miller'" else None),
            "triangularity_upper" : (pars['delta'] if pars['magn_geometry']=="'miller'" else None),
            "triangularity_lower" : (pars['delta'] if pars['magn_geometry']=="'miller'" else None),
        }


        self.gkdict["species_all"] = {
            "beta_reference" : pars['beta']/(rat["nref"]*rat["Tref"])*rat["Bref"]**2,
            "debye_length_reference" : np.sqrt(pars['debye2']), #ADD FACTORS
            "velocity_tor_norm" : pars["Omega0_tor"]*rat["vth"]/rat["Lref"],
            "shearing_rate_norm" : pars["ExBrate"]*self.r/pars["x0"]*\
                rat["vth"]/rat["Lref"]*rat["dxdr"],
            "zeff" : None #pars['Zeff'] #self-consistent computation by data base itself?
        }

        self.gkdict["species"] = []
        self.gkdict["collisions"] = {}
        self.gkdict["collisions"]["collisionality_norm"] = []

#        coulomb_log = 24.-np.log(np.sqrt(self.cm.pnt.nref*1E13)/
#                                self.cm.pnt.Tref*0.001)

        for ispec in range(1,pars['n_spec']+1):
            self.gkdict["species"] += [{
                "name" : self.cm.pars["name{}".format(ispec)],
                "charge_norm" : self.cm.pars["charge{}".format(ispec)],
                "mass_norm" : self.cm.pars["mass{}".format(ispec)]*rat["mref"],
                "density_norm" : (0.0 if self.cm.pars["passive{}".format(ispec)] else
                                  self.cm.pars["dens{}".format(ispec)]*rat["nref"]),
                "temperature_norm" : self.cm.pars["temp{}".format(ispec)]*rat["Tref"],
                "density_log_gradient_norm" : self.cm.pars["omn{}".format(ispec)]/rat["Lref"]*rat["dxdr"],
                "temperature_log_gradient_norm" : self.cm.pars["omt{}".format(ispec)]/rat["Lref"]*rat["dxdr"],
                "velocity_tor_gradient_norm" : pars["ExBrate"]*pars["q0"]/pars["x0"]*\
                rat["vth"]/rat["Lref"]*rat["dxdr"]
            }]

        for ispec in range(0,pars['n_spec']):
            ijcoll = []
            for jspec in range(0,pars['n_spec']):
                ijcoll += [(0.0 if self.cm.pars["passive{}".format(jspec+1)] else
                            rat["Tref"]**2/(np.sqrt(2.0)*np.pi*rat["qref"]**4*rat["Lref"]*rat["nref"])*\
                            self.gkdict["species"][ispec]["charge_norm"]**2*
                            self.gkdict["species"][jspec]["charge_norm"]**2*
                            self.gkdict["species"][jspec]["density_norm"]/\
                            np.sqrt(self.gkdict["species"][jspec]["mass_norm"]*
                                    self.gkdict["species"][jspec]["temperature_norm"]**3)*\
                            pars['coll'])]
            self.gkdict["collisions"]["collisionality_norm"] += [ijcoll]

        Cyq0_x0 = geom.Cy * self.cm.pnt.q0 / self.cm.pnt.x0
        if self.cm.pnt.adapt_lx:
            absnexc = 1
        else:
            absnexc = int(np.round(self.cm.pnt.lx*self.cm.pnt.n_pol*
                    np.abs(self.cm.pnt.shat)*self.cm.pnt.kymin*
                    np.abs(Cyq0_x0)))
            
#        nconn = int(int(int(self.cm.pnt.nx0-1)/2)/(absnexc*self.cm.pnt.ky0_ind))*2+1
        divisor = absnexc*self.cm.pnt.ky0_ind
        if divisor==0:
            nconn = 0
        else:
            nconn = int(int(int(self.cm.pnt.nx0-1)/2)/(absnexc*self.cm.pnt.ky0_ind))*2+1

        theta_full = []
        for iconn in range(-int(nconn/2),int(nconn/2)+1):
            theta_full += list(self.theta-np.sign(self.theta[0])*iconn*2.0*np.pi)
        fullsort_ind = np.argsort(theta_full)
        thetasort = np.array(theta_full)[fullsort_ind]


        #transformation of wavevector components on a z grid
        #following D. Told, PhD thesis, Sec. A.3, p. 167
        k1facx = np.sqrt(geom.gxx)
        k1facy = geom.gxy/np.sqrt(geom.gxx)
        k2fac = np.sqrt(geom.gyy-geom.gxy**2/geom.gxx)

        #now interpolate to theta = 0
        #interpolate to equidist. grid with proper order (interpol requires increasing arr)
        sort_ind = np.argsort(self.theta)
        k1facx_th0 = np.interp(0.0,self.theta[sort_ind],k1facx[sort_ind])/rat["rho"]
        k1facy_th0 = np.interp(0.0,self.theta[sort_ind],k1facy[sort_ind])/rat["rho"]
        k2fac_th0 = np.interp(0.0,self.theta[sort_ind],k2fac[sort_ind])/rat["rho"]

        ky = self.cm.pnt.kymin*self.cm.pnt.ky0_ind
        k1val = (self.cm.pnt.kx_center*k1facx_th0+ky*k1facy_th0)
        k2val = ky*k2fac_th0

        print ("k1facx_th0, k1facy_th0, k2fac_th0: ", k1facx_th0, k1facy_th0, k2fac_th0)

        # Finished writing physics inputs
        ###########################################################################################################
        # Now starting outputs

#        eigendat = Eigenvaluedata(self.cm)
#
#        if max(eigendat.growth_rate) <= 0.0:
#            raise RuntimeError("No unstable growth rate found - skipping file")

        nrgdat = self.rundatafiles.get_fileobject("nrg")
        nrgdat.generate_timeseries()

        newfieldnames = {"phi" : "phi_potential_perturbed_norm",
                         "apar" : "a_field_parallel_perturbed_norm",
                         "bpar" : "b_field_parallel_perturbed_norm"}

        newmomnames = { "dens" : "density",
                        "upar" : "velocity_parallel",
                        "tpar" : "temperature_parallel",
                        "tperp" : "temperature_perpendicular"}

        fieldmodestruct = ModeStructure(self.cm, self.rundatafiles,tavg=False)
        mommodestruct = []
        for spec in self.cm.specnames:
            ispec = self.cm.specnames.index(spec) #w/o +1
            mommodestruct += [ModeStructure(self.cm, self.rundatafiles, \
                                moms=list(newmomnames.keys()), species=spec,tavg=False)]

        eigenmodes = []

        if self.gkdict["model"]["initial_value_run"]:
            ievrange=[-1,]
        else:
#            ievrange=range(len(eigendat.growth_rate))
            ievrange=range(1)

        for iev in ievrange:
#            if eigendat.growth_rate[iev] <= 0.0:
#                continue

            eigenmode = {
#                "growth_rate_norm" : eigendat.growth_rate[iev]*rat["vth"]/rat["Lref"],
#                "frequency_norm" : eigendat.frequency[iev]*rat["vth"]/rat["Lref"],
                "growth_rate_tolerance": self.cm.pnt.omega_prec*rat["vth"]/rat["Lref"],
                "poloidal_angle" : thetasort.tolist()
            }

            #determine normalization amplitude and phase for parallel mode structures
            Af_gkdb = 0.0
            for field in self.fields:
                Af_gkdb += np.trapz(np.abs(fieldmodestruct.ballamps[field][iev][fullsort_ind]*rat[field])**2,thetasort)
            Af_gkdb = np.sqrt(Af_gkdb/(2.0*np.pi))
            alpha_gkdb = -np.interp(0.0,thetasort,np.angle(fieldmodestruct.ballamps["phi"][iev][fullsort_ind]))
            print ("Af_gkdb = ", Af_gkdb, ", alpha_gkdb = ", alpha_gkdb)

            for var in fieldmodestruct.ballamps.keys():
                print ("writing mode structure of ", var)
                eigenmode[newfieldnames[var]+"_real"]=np.real(fieldmodestruct.ballamps[var][iev][fullsort_ind]*
                                                        rat[var]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                eigenmode[newfieldnames[var]+"_imaginary"]=np.imag(fieldmodestruct.ballamps[var][iev][fullsort_ind]*
                                                            rat[var]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()

            eigenmode["moments_norm_rotating_frame"] = []
            for spec in self.cm.specnames:
                ispec = self.cm.specnames.index(spec) #w/o +1
#                mommodestruct = ModeStructure(self.cm, self.rundatafiles, moms=list(newmomnames.keys()), \
#                                                         species=spec,tavg=False)
                spec_moments_norm_rotating_frame = {}
                for var in newmomnames.keys():
                    spec_moments_norm_rotating_frame[newmomnames[var]+"_real"] = \
                                np.real(mommodestruct[ispec].ballamps[var][iev][fullsort_ind]*\
                                rat[var][ispec]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                    spec_moments_norm_rotating_frame[newmomnames[var]+"_imaginary"] = \
                                np.imag(mommodestruct[ispec].ballamps[var][iev][fullsort_ind]*\
                                rat[var][ispec]*np.exp(1j*alpha_gkdb)/Af_gkdb).tolist()
                eigenmode["moments_norm_rotating_frame"] += [spec_moments_norm_rotating_frame]


            eigenmode["fluxes_norm"] = []
            #NOTE: GENE NRG-FILES DO NOT ALLOW FOR SEPARATION OF A/B_FIELD_PARALLEL CONTRIBUTIONS
            #CURRENTLY BOTH OF THEM ARE ATTRIBUTED TO A_FIELD_PARALLEL
            #ALTERNATIVE: RECOMPUTE FLUXES FROM MOM-FILES (Pullback will still contain both fields though)
            for spec in self.cm.specnames:
                ispec = self.cm.specnames.index(spec) #w/o +1
                eigenmode["fluxes_norm"] += [{
                    "particles_phi_potential": nrgdat.dataarray[iev,ispec,4]*rat["pflux"]*(1.0/Af_gkdb)**2,
                    "particles_a_field_parallel": nrgdat.dataarray[iev,ispec,5]*rat["pflux"]*(rat["rho_Lref"]/Af_gkdb)**2,      #FIX THIS
                    "particles_b_field_parallel": nrgdat.dataarray[iev,ispec,5]*rat["pflux"]*(1.0/Af_gkdb)**2*0.0,  #FIX THIS -- SET TO ZERO
                    "momentum_tor_parallel_phi_potential": nrgdat.dataarray[iev,ispec,8]*rat["mflux"]*(1.0/Af_gkdb)**2,
                    "momentum_tor_parallel_a_field_parallel": nrgdat.dataarray[iev,ispec,9]*rat["mflux"]*(1.0/Af_gkdb)**2,      #FIX THIS
                    "momentum_tor_parallel_b_field_parallel": nrgdat.dataarray[iev,ispec,9]*rat["mflux"]*(1.0/Af_gkdb)**2*0.0,  #FIX THIS -- SET TO ZERO
                    "momentum_tor_perpendicular_phi_potential": None,
                    "momentum_tor_perpendicular_a_field_parallel": None,
                    "momentum_tor_perpendicular_b_field_parallel": None,
                    "energy_phi_potential": nrgdat.dataarray[iev,ispec,6]*rat["qflux"]*(1.0/Af_gkdb)**2,
                    "energy_a_field_parallel": nrgdat.dataarray[iev,ispec,7]*rat["qflux"]*(1.0/Af_gkdb)**2,     #FIX THIS
                    "energy_b_field_parallel": nrgdat.dataarray[iev,ispec,7]*rat["qflux"]*(1.0/Af_gkdb)**2*0.0  #FIX THIS -- SET TO ZERO
                }]
            eigenmodes += [eigenmode]


        self.gkdict["wavevector"] = [{
            "radial_component_norm" : k1val,
            "binormal_component_norm" : k2val,
            "poloidal_turns" : nconn,
            "eigenmode" : eigenmodes
        }]

        self.gkdict["fluxes_integrated_norm"] = []




    def Write_json(self, path):
        """ Take the dict and write a gkdb json parameters file """
        #        print(json.dumps(self.gkdict, indent=4))
        filename = 'data{}.json'.format(self.cm.fileextension)
        with open(filename, 'w') as fp:
            json.dump(self.gkdict, fp, indent=4,separators=(',', ': '))
            #json.dump(self.gkdict, fp, sort_keys=True,indent=4,separators=(',', ': '))
