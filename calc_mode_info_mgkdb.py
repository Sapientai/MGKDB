# -*- coding: utf-8 -*-
"""
"""

'''
Any command from pymongo:
    https://api.mongodb.com/python/current/tutorial.html
can be used.

mgk_fusion is the database name, 

the collection LinearRuns and NonlinRuns are the most frequently used.
'''
import os
import pymongo
import gridfs
from bson.objectid import ObjectId
from mgk_py_interface import *
import matplotlib.pyplot as plt
#from format_files_mgkdb import *
from D_chi_ratio_mgkdb import *
from mode_tools_mgkdb import *
#login = mgk_login(server='mongodb03.nersc.gov',
#                  port='27017',
#                  dbname='mgk_fusion',
#                  user='username',   # relace with actual username
#                  pwd = 'password')  # replace with actual pass
##  or login with the saved .pkl credential with the following two lines.

login = mgk_login()
login.from_saved(os.path.abspath('/global/u2/d/drhatch/mgk-dev/dhatch_mgkdb.pkl'))

mgk_fusion = login.connect()
print(mgk_fusion.list_collection_names())
lr = mgk_fusion.LinearRuns.find({}, {"_id": 1, "Meta": 1})
print(lr[0]['_id'])
print("Linear keys lr[0].keys()",format(lr[0].keys()))
print("Linear keys lr[0]['Meta'].keys()",format(lr[0]['Meta'].keys()))

#for x in mgk_fusion.LinearRuns.find({}, {"_id": 1, "Meta": 1}):
#    if x['Meta']['run_collection_name'] == '/global/project/projectdirs/m2116/hatch/ETG/JET2_B18_Zeff2C_ETG/scanfiles0000':
#        print(x)
#for x in mgk_fusion.NonlinRuns.find({}, {"_id": 1, "Meta": 1}):
#    if x['Meta']['run_collection_name'] == '/global/project/projectdirs/m2116/hatch/ETG/JET2_B18_Zeff2C_ETG/':
#        print(x)
#    #print(x['Meta']['run_collection_name'])

#objectID = '5f373025520e88603784f50c'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_0019
#The following are various from JET2_B18_Zeff2C_ETG/scanfiles0000
#objectID = '5f372fb0520e88603784f3da'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fb6520e88603784f3eb'    #JET2_B18_Zeff2C_ETG/scanfiles0000/
#objectID = '5f372fbc520e88603784f3fc'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fc3520e88603784f40d'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fc9520e88603784f41e'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fd0520e88603784f42f'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fd7520e88603784f440'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fdd520e88603784f451'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fe3520e88603784f462'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372fea520e88603784f473'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372ff0520e88603784f484'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372ff7520e88603784f495'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_
#objectID = '5f372ffe520e88603784f4a6'    #JET2_B18_Zeff2C_ETG/scanfiles0000/_

#objectID = '5f3ca1763a1e15347ba3b2dd'    #Core tests
#objectID = '5f3ca1803a1e15347ba3b2ec'    #Core tests
#objectID = '5f3ca1893a1e15347ba3b2fb'    #Core tests
objectID = '5f3ca1933a1e15347ba3b30a'    #Core tests
#objectID = '5f3ca19e3a1e15347ba3b319'    #Core tests

#objectID = '5f3c5d89c4b0a871953ac34c'   #/global/cscratch1/sd/drhatch/J7MTM/scanfiles0002/_0007   MHD mode
#objectID = '5f3c5ef7c4b0a871953ac430'   #/global/cscratch1/sd/drhatch/J7MTM/scanfiles0002/_0021   MTM 
#objectID = '5f3c5f95c4b0a871953ac483'   #/global/cscratch1/sd/drhatch/J7MTM/scanfiles0002/_0026   MTM 



a = load(mgk_fusion, mgk_fusion.LinearRuns, {'_id': ObjectId(objectID)})

pardict = a[0]['gyrokinetics']['code']['parameters']

ky = a[0]['Diagnostics']['omega']['ky']
gamma = a[0]['Diagnostics']['omega']['gamma']
omega = a[0]['Diagnostics']['omega']['omega']

specs = []
ename = 'none'
for i in range(5):
    name = 'name'+str(i+1)
    if name in pardict:
        specs.append(pardict[name][1:-1])
        if pardict[name][1:-1] == 'e' or pardict[name] == 'electrons' or pardict[name]== 'Electrons':
            ename = name
            enum = str(i+1)

print("ename",ename)
if ename == 'none':
    print("Electrons not found.  This script only operates with an electron species.")
    os._exit()
    enum = '1'

omegastar = ky*(pardict['omn'+enum] + pardict['omt'+enum])

nrgdict = get_nrg(mgk_fusion,mgk_fusion.LinearRuns,ObjectId(objectID))
print('nrgdict keys()')
print(nrgdict.keys())
gpars,geom = get_magn_geometry(mgk_fusion,mgk_fusion.LinearRuns,ObjectId(objectID))

ratios = transport_ratios(pardict,nrgdict)

field = a[0]['Diagnostics']['field']
#print(a[0]['Diagnostics']['field'].keys())
phi = field['phi']
apar = field['A_par']

kperp, omd_curv, omd_gradB  = calc_kperp_omd(pardict,geom)

kperp_avg = np.sqrt(eigenfunction_average(kperp**2,phi,pardict,geom))
omd_avg = eigenfunction_average(omd_curv,phi,pardict,geom)
#kperp_avg_bes = np.sqrt(eigenfunction_average_bessel(kperp,kperp**2,phi,pardict,geom))
#omd_avg_bes = eigenfunction_average_bessel(kperp,omd_curv,phi,pardict,geom)
kz_avg = kz_from_dfielddz_bessel(kperp,phi,pardict,geom)
kz_vthe = kz_avg*pardict['mass'+enum]**-0.5

epar_cancel = calc_epar(pardict,phi,apar,gamma,omega,gpars,geom)

#print("kperp",kperp)
#print("len(kperp)",len(kperp))
#print("np.shape(kperp)",np.shape(kperp))

print("diagdir",pardict['diagdir'])
print("kx_center",pardict['kx_center'])
print("kperp_avg",kperp_avg)
print("\nMode Info:\n")
print("omega_drift",omd_avg)
print("kz_avg",kz_avg)
print("E_par",epar_cancel)
print("kz vthe",kz_vthe)
print("omegastar",omegastar)
print("ky,gamma,omega",ky,gamma,omega)
print('\n\n\n\n',a[0]['Meta']['run_collection_name'],a[0]['Meta']['run_suffix'],'\n\n')

print("Train on the following:\n")
print("E_par",epar_cancel)
print("omega_drift/omega",omd_avg/omega)
print("kz_vthe/omega",kz_vthe/omega)
print("omegastar/omega",omegastar/omega)
print("ky",ky)
print("gamma",gamma)
print("omega",omega)
print("sign of omega",omega/abs(omega))
print("chie/chitot",ratios['chie_o_chitot'])
print("chii/chitot",ratios['chii_o_chitot'])
print("chiz/chitot",ratios['chiz_o_chitot'])
print("De/chitot",ratios['De_o_chitot'])
print("Di/chitot",ratios['Di_o_chitot'])
print("Dz/chitot",ratios['Dz_o_chitot'])
print("QEMe/Qtot",ratios['QEMe_o_Qtot'])




