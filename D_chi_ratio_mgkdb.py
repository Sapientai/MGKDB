#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import optparse as op
from parIOWrapper import *
from nrgWrapper import *
from mgk_py_interface import get_spec_nums

def read_species_tempdens(q_charge, pars):

    if 'temp1' in pars:
        if pars['charge1'] == q_charge:
            return pars['temp1'], pars['dens1']
        elif 'temp2' in pars:
            if pars['charge2'] == q_charge:
                return pars['temp2'], pars['dens2']
            elif 'temp3' in pars:
                if pars['charge3'] == q_charge:
                    return pars['temp3'], pars['dens3']
                else:
                    return 0, 0
                    print( 'No species with charge = ' + \
                          str(q_charge) + ' iis found.' \
                          'temp = 0, dens = 0')


def read_species_gradients(q_charge, pars):

  if 'x_local' in pars:
      if pars['x_local']:
          x_local = True
      else:
          x_local = False
  else:
      x_local = True

  if x_local:
    if 'omn1' in pars:
        if pars['charge1'] == q_charge:
            return pars['omn1'], pars['omt1']
        elif 'omn2' in pars:
            if pars['charge2'] == q_charge:
                return pars['omn2'], pars['omt2']
            elif 'omn3' in pars:
                if pars['charge3'] == q_charge:
                    return pars['omn3'], pars['omt3']
                else:
                    return 0, 0
                    print( 'No species with charge = ' + \
                          str(q_charge) + ' is found.' \
                          'omn = 0, omt = 0')
  else:
    return 1.,1.

def D_over_chi(time,nrg,omn,omt,T,n):
    Gamma_es, Gamma_em, Q_es, Q_em = \
                        read_Gamma_Q(time,nrg,False)
    Gamma = Gamma_es + Gamma_em
    Qtot = Q_es + Q_em
    #Qtot = Qtot - 5./3.*Gamma
    Qtot = Qtot - 3./2.*Gamma*T
    Qes = Q_es - 3./2.*Gamma_es*T
    Qem = Q_em - 3./2.*Gamma_em*T
    D = Gamma / omn / n
    chi = Qtot / omt / n / T
    Dochi = Gamma/Qtot*omt/omn*T

    return Dochi, Qtot, Qes, Qem, Gamma, D, chi
    
def D_over_chi_tot(Gamma_s,omn_s,n_s,Q_e,omt_e,Q_i,omt_i,Ti,ni):
    Ds_chi_tot = Gamma_s/omn_s/n_s/(Q_e/omt_e+Q_i/omt_i/Ti/ni)
    return Ds_chi_tot

def transport_ratios(pars,nrgdict):

    inum, enum, znum = get_spec_nums(pars)

    ratios = {}
    ratios['De_o_chitot'] = 0.0
    ratios['Di_o_chitot'] = 0.0
    ratios['Dz_o_chitot'] = 0.0
    ratios['chie_o_chitot'] = 0.0
    ratios['chii_o_chitot'] = 0.0
    ratios['chiz_o_chitot'] = 0.0
    ratios['QEMe_o_Qtot'] = 0.0

    if pars['n_spec'] == 1 and enum:
        q_e = -1.
        omn_e, omt_e = read_species_gradients(q_e,pars)
        temp_e, dens_e = read_species_tempdens(q_e,pars)
        time = nrgdict['time']
        nrge = nrgdict['nrg'+enum]
        Doche, Q, Qes, Qem, Gamma, D, chi = \
            D_over_chi(time,nrge,omn_e,omt_e,temp_e,dens_e)
        #print( 'electron: Q_em/Q_es = %12.5f' % float(Qem/Qes))
        ratios['QEMe_o_Qtot'] = Qem/(Qes+Qem)
        ratios['chie_o_chitot'] = 1.0

    elif pars['n_spec'] == 2:
        q_i = 1.
        omn_i, omt_i = read_species_gradients(q_i,pars)
        temp_i, dens_i = read_species_tempdens(q_i,pars)
        q_e = -1.
        omn_e, omt_e = read_species_gradients(q_e,pars)
        temp_e, dens_e = read_species_tempdens(q_e,pars)

        time = nrgdict['time']
        nrge = nrgdict['nrg'+enum]
        nrgi = nrgdict['nrg'+inum]

        Dochi_i, Q_i, Qes_i, Qem_i, Gamma_i, D_i, chi_i = \
            D_over_chi(time,nrgi,omn_i,omt_i,temp_i,dens_i)
        Dochi_e, Q_e, Qes_e, Qem_e, Gamma_e, D_e, chi_e = \
            D_over_chi(time,nrge,omn_e,omt_e,temp_e,dens_e)
        ratios['Di_o_chitot'] = D_over_chi_tot(Gamma_i,omn_i,dens_i,Q_e,omt_e,Q_i,omt_i,temp_i, dens_i)
        ratios['De_o_chitot'] = D_over_chi_tot(Gamma_e,omn_e,dens_e,Q_e,omt_e,Q_i,omt_i,temp_i, dens_i)

        ratios['chie_o_chitot'] = chi_e / (chi_e+chi_i)
        ratios['chie_o_chitot'] = chi_e/(chi_e+chi_i)
        ratios['chii_o_chitot'] = chi_i/(chi_e+chi_i)
        ratios['QEMe_o_Qtot'] = Qem_e/(Qem_e + Qem_i+Qes_e+Qes_i)

    elif pars['n_spec'] ==3:
        q_i = 1.
        omn_i, omt_i = read_species_gradients(q_i,pars)
        temp_i, dens_i = read_species_tempdens(q_i,pars)
        q_e = -1.
        omn_e, omt_e = read_species_gradients(q_e,pars)
        temp_e, dens_e = read_species_tempdens(q_e,pars)
        q_z = pars['charge3']
        omn_z, omt_z = read_species_gradients(q_z,pars)
        temp_z, dens_z = read_species_tempdens(q_z,pars)
    
        print(nrgdict.keys())
        time = nrgdict['time']
        nrge = nrgdict['nrg'+enum]
        nrgi = nrgdict['nrg'+inum]
        nrgz = nrgdict['nrg'+znum]

        Dochi_i, Q_i, Qes_i, Qem_i, Gamma_i, D_i, chi_i = \
            D_over_chi(time,nrgi,omn_i,omt_i,temp_i,dens_i)
        Dochi_e, Q_e, Qes_e, Qem_e, Gamma_e, D_e, chi_e = \
            D_over_chi(time,nrge,omn_e,omt_e,temp_e,dens_e)
        Dochi_z, Q_z, Qes_z, Qem_z, Gamma_z, D_z, chi_z = \
            D_over_chi(time,nrgz,omn_z,omt_z,temp_z,dens_z)

        ratios['chie_o_chitot'] = chi_e/(chi_e+chi_i+chi_z)
        ratios['chii_o_chitot'] = chi_i/(chi_e+chi_i+chi_z) 
        ratios['chiz_o_chitot'] = chi_z/(chi_e+chi_i+chi_z) 
        ratios['QEMe_o_Qtot'] = Qem_e/(Qem_e+Qem_i+Qem_z+Qes_e+Qes_i+Qes_z)
        ratios['Di_o_chitot'] = D_over_chi_tot(Gamma_i,omn_i,dens_i,Q_e,omt_e,Q_i,omt_i,temp_i, dens_i)
        ratios['De_o_chitot'] = D_over_chi_tot(Gamma_e,omn_e,dens_e,Q_e,omt_e,Q_i,omt_i,temp_i, dens_i)
        ratios['Dz_o_chitot'] = D_over_chi_tot(Gamma_z,omn_z,dens_z,Q_e,omt_e,Q_i,omt_i,temp_i, dens_i)

    return ratios
