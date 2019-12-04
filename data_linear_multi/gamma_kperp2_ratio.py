#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy
M=25
N=M/3+1
ky=[0]*N
k_perp2=[0]*N
ratio=[0]*N
gamma=[0]*N

for i in range(1,N+1):
    L=(i-1)*3+1
    suffix='%02d'%L
    avg_kperp=numpy.loadtxt('avg3_kz_kperp_omd_00'+suffix)
    ky[i-1]=avg_kperp[0]
    k_perp2[i-1]=avg_kperp[2]**2
    ratio[i-1]=avg_kperp[4]
    omega=numpy.loadtxt('omega_00'+suffix)
    gamma[i-1]=omega[1]

g=open('gamma_kperp2_ratio_kxcenter0','w')
g.write('#   1.ky   2.gamma   3.<k_perp^2> 4.gamma/<k_perp^2>   5.comments\n')
numpy.savetxt(g,numpy.column_stack((ky,gamma,k_perp2,ratio)),fmt='%10.4f',delimiter=' ')
g.close()
    
