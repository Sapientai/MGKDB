import numpy as np
import matplotlib.pyplot as plt
from finite_differences import *
from interp import *

def construct_extended_ballooning(pars,field):
    ntot = pars['nx0']*pars['nz0']
    dz = float(2.0)/float(pars['nz0'])
    zgrid = np.arange(ntot)/float(ntot-1)*(2*pars['nx0']-dz)-pars['nx0']
    field_ext = np.zeros(ntot,dtype='complex128')

    if 'n0_global' in pars:
        phase_fac = -np.e**(-2.0*np.pi*(0.0+1.0J)*pars['n0_global']*pars['q0'])
    else:
        phase_fac = -1.0
    #print "phase_fac",phase_fac

    if pars['shat'] < 0.0:
        for i in range(int(pars['nx0']/2)+1):
            field_ext[(i+int(pars['nx0']/2))*pars['nz0']:(i+int(pars['nx0']/2)+1)*pars['nz0']]=field[-i,0,:]*phase_fac**i
            if i < int(pars['nx0']/2):
                field_ext[(int(pars['nx0']/2)-i-1)*pars['nz0'] : (int(pars['nx0']/2)-i)*pars['nz0'] ]=field[i+1,0,:]*phase_fac**(-(i+1))
    else:
        for i in range(int(pars['nx0']/2)):
            #print("phase_fac**i",phase_fac**i)
            #print("phase_fac**(-(i+1))",phase_fac**(-(i+1)))
            field_ext[(i+int(pars['nx0']/2))*pars['nz0']:(i+int(pars['nx0']/2)+1)*pars['nz0']]=field[i,0,:]*phase_fac**i
            if i < int(pars['nx0']/2):
                field_ext[(int(pars['nx0']/2)-i-1)*pars['nz0'] : (int(pars['nx0']/2)-i)*pars['nz0'] ]=field[-1-i,0,:]*phase_fac**(-(i+1))

    return zgrid,field_ext


def calc_epar(pars,phikx,aparkx,gamma,omega,gpars,geometry):

    #This routine calculates and returns E_parallel / (|grad phi| + |omega*Apar|)

    ntot = pars['nx0']*pars['nz0']
    zgrid, phi = construct_extended_ballooning(pars,phikx)
    zgrid, apar = construct_extended_ballooning(pars,aparkx)
    #plt.plot(zgrid,abs(phi))
    #plt.title('In calc_epar')
    #plt.show()
    
    zavg=np.sum(np.abs(phi)*np.abs(zgrid))/np.sum(np.abs(phi))
    phi = phi/phikx[0,0,int(pars['nz0']/2)]
    apar = apar/phikx[0,0,int(pars['nz0']/2)]
    
    if 1==0:
        plt.title(r'$\phi$')
        plt.plot(zgrid,np.real(phi),color='red',label=r'$Re[\phi]$')
        plt.plot(zgrid,np.imag(phi),color='blue',label=r'$Im[\phi]$')
        plt.plot(zgrid,np.abs(phi),color='black',label=r'$|\phi|$')
        ax=plt.axis()
        plt.axvline(zavg,ax[2],ax[3],color='yellow')
        plt.axvline(-zavg,ax[2],ax[3],color='yellow')
        plt.legend()
        plt.xlabel(r'$z/\pi$',size=18)
        plt.show()
    
        plt.title(r'$A_{||}$')
        plt.plot(zgrid,np.real(apar),color='red',label=r'$Re[A_{||}]$')
        plt.plot(zgrid,np.imag(apar),color='blue',label=r'$Im[A_{||}]$')
        plt.plot(zgrid,np.abs(apar),color='black',label=r'$|A_{||}|$')
        plt.legend()
        plt.xlabel(r'$z/\pi$',size=18)
        plt.savefig('phiapar.png')
        #np.savetxt('apar'+suffix,np.column_stack((zgrid,np.real(apar),np.imag(apar))))
    
    #parity_factor_apar = np.abs(np.sum(apar))/np.sum(np.abs(apar))
    #parity_factor_phi = np.abs(np.sum(phi))/np.sum(np.abs(phi))
    
    #Note:  the complex frequency is (gamma + i*omega)
    #print "Here"
    jacxBpi = geometry['gjacobian']*geometry['gBfield']*np.pi
    omega_complex = (omega*(0.0+1.0J) + gamma)
    omega_phase = np.log(omega_complex/np.abs(omega_complex))/(0.0+1.0J)
    phase_array = np.empty(len(zgrid))
    phase_array[:] = np.real(omega_phase)
    
    gradphi = fd_d1_o4(phi,zgrid)
    for i in range(pars['nx0']):
        gradphi[pars['nz0']*i:pars['nz0']*(i+1)] = gradphi[pars['nz0']*i:pars['nz0']*(i+1)]/jacxBpi[:]
    
    #ratio = gradphi/-apar
    #mode_phase = np.log(ratio / np.abs(ratio))/(0.0+1.0J)
    #plt.plot(zgrid,mode_phase)
    #plt.plot(zgrid,phase_array,'-.',color = 'black')
    #plt.show()
    
    if 1==2:
        plt.plot(zgrid,zgrid)
        plt.plot(zgrid,np.real(gradphi),'-',color = 'red',label=r'$Re[\nabla \phi]$')
        plt.plot(zgrid,np.imag(gradphi),'-.',color = 'red',label=r'$Im[\nabla \phi]$')
        plt.plot(zgrid,-np.real(omega_complex*apar),'-',color = 'black',label=r'$Re[\omega A_{||}]$')
        plt.plot(zgrid,-np.imag(omega_complex*apar),'-.',color = 'black',label=r'$Im[\omega A_{||}]$')
        plt.xlabel(r'$z/\pi$',size=18)
        plt.legend()
        plt.savefig("epar.png")
    
    diff = np.sum(np.abs(gradphi + omega_complex*apar))
    phi_cont = np.sum(np.abs(gradphi))
    apar_cont = np.sum(np.abs(omega_complex*apar))
    
    return diff/(phi_cont+apar_cont)

def get_jacxBpi_extended(zgrid,jacxBpi):
    nx0 = int(len(zgrid)/len(jacxBpi))
    nz0 = len(jacxBpi)
    jacxBpi_extended = np.empty(len(zgrid))
    for i in range(nx0):
        jacxBpi_extended[i*nz0:(i+1)*nz0] = jacxBpi[:]
    return jacxBpi_extended

def get_vdrift_coefficients(pars,geometry):

    ggxx = geometry['ggxx']
    ggxy = geometry['ggxy']
    ggxz = geometry['ggxz']
    ggyy = geometry['ggyy']
    ggyz = geometry['ggyz']
    ggzz = geometry['ggzz']

    gamma1 = ggxx * ggyy - ggxy ** 2
    gamma2 = ggxx * ggyz - ggxy * ggxz
    gamma3 = ggxy * ggyz - ggyy * ggxz

    gdBdx = geometry['gdBdx']
    gdBdy = geometry['gdBdy']
    gdBdz = geometry['gdBdz']

    gBfield = geometry['gBfield']

    Kx = - gdBdy - gamma2 / gamma1 * gdBdz
    Ky = gdBdx - gamma3 / gamma1 * gdBdz

    if (pars['magn_geometry'] == 's_alpha'):
        Kx = Kx / gBfield
        Ky = Ky / gBfield

    return Kx, Ky

def calc_kperp_omd(pars,geom_coeff):

    nx = int(pars['nx0'])
    ikx_grid = np.arange(- nx // 2 + 1, nx // 2 + 1)
    nz = int(pars['nz0'])
    lx = float(pars['lx'])
    ky = float(pars['kymin'])
    dkx = 2. * np.pi * float(pars['shat']) * float(ky)

    dpdx_tot = float(pars['beta']) * \
               (float(pars['omn1']) + float(pars['omt1']))
    if  int(pars['n_spec']) > 1:
        dpdx_tot = dpdx_tot + float(pars['beta']) * \
                   (float(pars['omn2']) + float(pars['omt2']))
        if int(pars['n_spec']) > 2:
           dpdx_tot = dpdx_tot + float(pars['beta']) * \
                      (float(pars['omn3']) + float(pars['omt3']))

    if 'kx_center' in pars:
        kx_center = float(pars['kx_center'])
    else:
        kx_center = 0.

    Kx, Ky = get_vdrift_coefficients(pars,geom_coeff)
    ggxx = geom_coeff['ggxx'].astype(float)
    ggxy = geom_coeff['ggxy'].astype(float)
    ggyy = geom_coeff['ggyy'].astype(float)
    gBfield = geom_coeff['gBfield'].astype(float)

#    kperp = np.zeros(nx*nz,dtype='longdouble') # changed to longdouble?
#    omd_curv = np.zeros(nx*nz,dtype='longdouble')
#    omd_gradB = np.zeros(nx*nz,dtype='longdouble')
    
    kperp = np.zeros(nx*nz,dtype='float128') # changed to longdouble ..
    omd_curv = np.zeros(nx*nz,dtype='float128')
    omd_gradB = np.zeros(nx*nz,dtype='float128')

    for i in ikx_grid:
        kx = i*dkx+kx_center
        this_kperp = np.sqrt(ggxx*kx**2+2.*ggxy*kx*ky+ggyy*ky**2)
        this_omegad_gradB = -(Kx*kx+Ky*ky)/gBfield
        this_omegad_curv = this_omegad_gradB + \
                           ky * float(pars['dpdx_pm'])/gBfield**2/2.
        #this_omegad_curv = 2.*this_omegad

        #print("len(kperp)",len(kperp))
        #print("len(this_kperp)",len(this_kperp))
        kperp[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_kperp
        omd_curv[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_omegad_curv
        omd_gradB[(i-ikx_grid[0])*nz:(i-ikx_grid[0]+1)*nz]=this_omegad_gradB

    if pars['magn_geometry'] == 's_alpha' or pars['magn_geometry'] == 'slab':
        if 'amhd' in pars:
            amhd = pars['amhd']
        else:
            amhd = 0.
        z_grid = np.linspace(-1.,1., nz, endpoint = False)
        Kx0 = -np.sin(z_grid*np.pi)/pars['major_R']
        Ky0 = -(np.cos(z_grid*np.pi)+np.sin(z_grid*np.pi)*\
              (pars['shat']*z_grid*np.pi-amhd*\
              np.sin(z_grid*np.pi)))/pars['major_R']
        omega_d0 = -(Kx0*kx_center+Ky0*ky)
        omega_d00 = omega_d0+amhd/pars['q0']**2/pars['major_R']/2.*ky/gBfield**2
        gxx0 = 1.
        gxy0 = pars['shat']*z_grid*np.pi-amhd*np.sin(z_grid*np.pi)
        gyy0 = 1+(pars['shat']*z_grid*np.pi-amhd*np.sin(z_grid*np.pi))**2
        kperp0 = np.sqrt(gxx0*kx_center**2+2.*gxy0*kx_center*ky+gyy0*ky**2)


    return kperp, omd_curv, omd_gradB

def kz_from_dfielddz_bessel(kperp, field, pars,geom,mass_ratio=1):


    #for i in range(pars['nx0']):
    #    plt.plot(abs(field[i,0,:]))
    #    plt.plot(np.real(field[i,0,:]))
    #    plt.plot(np.imag(field[i,0,:]))
    #plt.show()

    zgrid,field_ext = construct_extended_ballooning(pars,field)
    #plt.plot(zgrid, np.abs(field_ext), label = 'field')
    #plt.plot(zgrid, np.real(field_ext), label = 'Re field')
    #plt.plot(zgrid, np.imag(field_ext), label = 'Im field')
    #plt.legend()
    #plt.xlabel('z')
    #plt.show()

    jacxBpi = geom['gjacobian']*geom['gBfield']*np.pi
    jacxBpi_extended = get_jacxBpi_extended(zgrid,jacxBpi)
    alpha = 2./3.
    #mass_ratio = 9.1094e-31/(pars['mref']*1.6726e-27)
    kperp_bessel = kperp*np.sqrt(mass_ratio)

    bessel_factor = 1. / np.sqrt(1. + 2. * (kperp_bessel**2 + np.pi * alpha * kperp_bessel**4) /
                    (1. + alpha * kperp_bessel**2))
    if 1 == 0:
        plt.plot(zgrid, bessel_factor, label = 'bessel_factor')
        plt.legend()
        plt.show()

    #dfielddz = np.empty(len(field_ext),dtype='complex128')
    #for i in range(len(field_ext)-1):
    #    dfielddz[i] = (field_ext[i+1]-field_ext[i])/\
    #        (zgrid[i+1]-zgrid[i])/jacxBpi_extended[i]
    dfielddz = fd_d1_o4(field_ext,zgrid)
    for i in range(pars['nx0']):
        dfielddz[pars['nz0']*i:pars['nz0']*(i+1)] = dfielddz[pars['nz0']*i:pars['nz0']*(i+1)]/jacxBpi[:]

    if 1==0:
        plt.plot(zgrid[:-1], np.abs(dfielddz[:-1]), label = 'abs dfield/dz')
        plt.plot(zgrid[:-1], np.real(dfielddz[:-1]), label = 'real dfield/dz')
        plt.plot(zgrid[:-1], np.imag(dfielddz[:-1]), label = 'imag dfield/dz')
        plt.legend()
        plt.xlabel('z')
        plt.show()
    sum_ddz = 0.
    denom = 0.
    
    zstart = 5
    zend = len(zgrid)-5
    #print("len(zgrid)",len(zgrid))
    #zstart = int(input("Enter zstart index:"))
    #zend = int(input("Enter zend index:"))
    #startInd = np.argmin(abs(zgrid - zstart))
    #endInd = np.argmin(abs(zgrid - zend))
    #for i in (startInd, endInd + 1):
    for i in range(zstart,zend):
        sum_ddz = sum_ddz + 0.5*(abs(dfielddz[i])**2 * bessel_factor[i] \
                  + abs(dfielddz[i+1])**2 * bessel_factor[i+1])*\
                  (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
        denom = denom + 0.5*(abs(field_ext[i])**2 * bessel_factor[i] \
                + abs(field_ext[i+1])**2* bessel_factor[i+1])*\
                (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
    ave_kz = np.sqrt(sum_ddz/denom)
    #print ('Input to SKiM kz = ', ave_kz)
    return ave_kz

def eigenfunction_average(quantity,field,pars,geometry):

    zgrid, field_ext = construct_extended_ballooning(pars,field)

    jacxBpi = geometry['gjacobian']*geometry['gBfield']*np.pi
    jacxBpi_extended = get_jacxBpi_extended(zgrid,jacxBpi)

    ave_quant = 0.
    denom = 0.
    for i in np.arange(len(field_ext)-1):
        ave_quant = ave_quant + (quantity[i]*abs(field_ext[i])**2 +\
            quantity[i+1]*abs(field_ext[i+1])**2)/2.*\
            (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
        denom = denom + (abs(field_ext[i])**2 +abs(field_ext[i+1])**2)/2.*\
            (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
    ave_quant = ave_quant/denom

    return ave_quant

def eigenfunction_average_bessel(kperp,quantity,field,pars,geometry,mass_ratio = 1):

    zgrid, field_ext = construct_extended_ballooning(pars,field)

    jacxBpi = geometry['gjacobian']*geometry['gBfield']*np.pi
    jacxBpi_extended = get_jacxBpi_extended(zgrid,jacxBpi)
    #mass_ratio = 9.1094e-31/(pars['mref']*1.6726e-27)
    kperp_bessel = kperp*np.sqrt(mass_ratio)

    alpha = 2./3.
    bessel_factor = 1. / np.sqrt(1. + 2. * (kperp_bessel**2 + np.pi * alpha * kperp_bessel**4) /
                    (1. + alpha * kperp_bessel**2))

    ave_quant = 0.
    denom = 0.

    #plt.plot(bessel_factor)
    #plt.title('bessel')
    #plt.show()
    #plt.plot(kperp)
    #plt.title('kperp')
    #plt.show()
    #plt.plot(quantity)
    #plt.title('omd')
    #plt.show()
    #plt.plot(np.real(field_ext))
    #plt.plot(np.imag(field_ext))
    #plt.title('field')
    #plt.show()

    for i in np.arange(len(field_ext)-1):
        ave_quant = ave_quant + (quantity[i]*abs(field_ext[i])**2 * bessel_factor[i]+\
            quantity[i+1]*abs(field_ext[i+1])**2 * bessel_factor[i+1])/2.*\
            (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
        denom = denom + (abs(field_ext[i])**2 * bessel_factor[i] \
            +abs(field_ext[i+1])**2 * bessel_factor[i+1])/2.*\
            (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]

    #for i in np.arange(len(field_ext)-1):
    #    ave_quant = ave_quant + (quantity[i]*abs(field_ext[i])**2 +\
    #        quantity[i+1]*abs(field_ext[i+1])**2)/2.*\
    #        (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
    #    denom = denom + (abs(field_ext[i])**2 +abs(field_ext[i+1])**2)/2.*\
    #        (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]

    ave_quant = ave_quant/denom

    return ave_quant

def eigenfunction_width(field,pars,geometry):

    zgrid, field_ext = construct_extended_ballooning(pars,field)

    jacxBpi = geometry['gjacobian']*geometry['gBfield']*np.pi
    jacxBpi_extended = get_jacxBpi_extended(zgrid,jacxBpi)

    field2_integral = 0.
    denom = np.max(abs(field_ext)**2)
    for i in np.arange(len(field_ext)-1):
        #field2_integral +=  abs(field_ext[i])**2*jacxBpi_extended[i]
        field2_integral +=  (abs(field_ext[i])**2 +\
            abs(field_ext[i+1])**2)/2.*\
            (zgrid[i+1]-zgrid[i])*jacxBpi_extended[i]
    width = field2_integral / denom
    #print('width',width)

    #print(zgrid[1]-zgrid[0])
    #plt.plot(jacxBpi_extended)
    #plt.show()
    #plt.plot(abs(field_ext)**2)
    #plt.show()
    #plt.plot(np.real(field_ext)**2)
    #plt.plot(np.imag(field_ext)**2)
    #plt.show()

    return width

#def npeaks(zgrid,field,nz0):
def npeaks_old(field,pars,width):

    zgrid, field_ext = construct_extended_ballooning(pars,field)

    ntot = len(zgrid)
    nz0 = pars['nz0']
    field2 = abs(field_ext)**2
    field2 = field2/np.max(field2)
    field2avg = np.empty(ntot)
    print('nz0',nz0)
    for i in range(ntot):
        field2avg[i] = np.sum(field2[max(0,i-int(nz0/8)):min(ntot-1,i+int(nz0/8))])/nz0
    field2avg = field2avg / np.max(field2avg)
    df2a = fd_d1_o4(field2avg,zgrid)
    zeros = []
    last_zero = zgrid[0] - 2
    for i in range(1,(ntot-1)):
        if np.sign(df2a[i]) != np.sign(df2a[i-1]) and field2avg[i] > 0.5 and abs(zgrid[i] - last_zero) > 2:
            #print('zgrid[i],last_zero',zgrid[i],last_zero)
            zeros.append(zgrid[i])
            last_zero = zgrid[i]
    #print('locations of peaks',zeros)
    peakplot = False
    if peakplot:
        plt.plot(zgrid,field2)
        for i in zeros:
            plt.axvline(i,color='red')
        plt.plot(zgrid,field2avg)
        plt.title('npeaks 1: '+str(len(zeros))+' peaks, width '+str(width)[0:5])
        plt.show()
    return len(zeros)

def npeaks(field,pars,width):

    zgrid, field_ext = construct_extended_ballooning(pars,field)
    width = width/7

    ntot = len(zgrid)
    nz0 = pars['nz0']
    field2 = abs(field_ext)**2
    field2 = field2/np.max(field2)
    df2a = fd_d1_o4(field2,zgrid)
    zeros = []
    last_zero = zgrid[0] - 2
    for i in range(1,(ntot-1)):
        if np.sign(df2a[i]) != np.sign(df2a[i-1]) and field2[i] > 0.5 and abs(zgrid[i] - last_zero) > width:
            #print('zgrid[i],last_zero',zgrid[i],last_zero)
            zeros.append(zgrid[i])
            last_zero = zgrid[i]
    #print('locations of peaks',zeros)
    #plt.plot(zgrid,df2a)
    #plt.show()
    peakplot = False
    if peakplot:
        plt.plot(zgrid,field2)
        for i in zeros:
            plt.axvline(i,color='red')
        plt.title('npeaks 2: '+str(len(zeros))+' peaks, width '+str(width)[0:5])
        plt.show()
    return len(zeros)

