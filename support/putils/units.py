#!/usr/bin/env python3
import math

class Units:
    '''
    pnt: Parameters object

    '''
    def __init__(self, parameters):
        self.mp = 1.672621637E-27
        self.e = 1.6021766208E-19
        self.c = 2.99792458e10
    
        self.Bref = parameters.pardict["Bref"]  # (in T)
        self.nref = parameters.pardict["nref"]  # (in 10^19)
        self.Tref = parameters.pardict["Tref"]  # (in ev)
        self.Lref = parameters.pardict["Lref"]  # (in m)
        self.mref = parameters.pardict["mref"]  # in proton masses
        self.qref = 1.0
        # Coulomb logarithm
        self.lnlambda = 24. - math.log(math.sqrt(self.nref * 1e13) /\
                                       self.Tref * 1e3)
        # electron beta
        self.beta = 403e-5 * self.nref * self.Tref / self.Bref** 2
        # Collisionlity
        self.coll = 2.3031e-5 * self.nref / self.Tref**2 * self.Lref * \
            self.lnlambda*1e2  # assume Tref=Te

        self.cref = math.sqrt(self.Tref * 1e3 * self.e/ (self.mref * self.mp))
        self.gyrofreq = self.qref * self.e * self.Bref / (self.mref * self.mp)
        self.rhoref = self.cref / self.gyrofreq
        self.inv_rhostar = self.Lref / self.rhoref
        self.pref = self.nref * 1e19 * self.Tref * 1e3 * self.e
        self.GGB = self.nref * 1e19* self.cref * (self.rhoref / self.Lref)**2
        self.QGB = self.pref * self.cref * (self.rhoref / self.Lref)**2
        self.PGB = self.mref *self.mp * self.nref * 1e19 * self.cref**2 * (self.rhoref / self.Lref)**2

        try:
            Zeff_in = parameters.pardict['Zeff']
        except:
            Zeff_in = 1.0

        qi = 1.
        ne = 1.
        te = 1.
        ti = 1.
        self.tau = 1.
        self.mi = 1.
        self.Zeff = 0.
        for spec in parameters.specnames:
            if parameters.pardict['charge' + spec] < 0:  # for electrons
                ne = parameters.pardict['dens' + spec]
                te = parameters.pardict['temp' + spec]
            else:
                if (parameters.pardict['charge' + spec] == 1): # for main ion species
                    ti = parameters.pardict['temp' + spec]
                    qi = parameters.pardict['charge' + spec]
                    mi = parameters.pardict['mass' + spec]
                self.Zeff = self.Zeff + parameters.pardict['charge' + spec]**2 * \
                    parameters.pardict['dens' + spec]      
        self.Zeff = self.Zeff / ne
        
        '''at this point self. Zeff is either the Zeff or 0 if adiabatic ions.
            Fix latter case'''
        if self.Zeff ==0:
            self.Zeff = Zeff_in
        
        self.tau = ti / te