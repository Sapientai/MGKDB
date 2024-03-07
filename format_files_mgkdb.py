#from mgk_py_interface import *
import numpy as np

def get_spec_nums(pars):
    enum = False
    inum = False
    znum = False
    for i in range(pars['n_spec']):
        charge = 'charge'+str(i+1)
        if charge in pars:
            if pars[charge] == -1: 
                enum = str(i+1)
            elif pars[charge] == 1:
                inum = str(i+1)
            elif pars[charge] > 1:
                znum = str(i+1)
    return inum,enum,znum

def get_nrg(db,coll,oid):
    nrg_raw = get_file_by_id(db,coll,ObjectId(oid),'nrg')
    nrg_split = nrg_raw.split('\n')
    for i in range(2,10):
        if len(nrg_split[i]) < 100:
            it2 = i
            break
    nspec = it2-1
    #print("number of species:",nspec)
    time=np.empty(0,dtype='float')
    nrg1=np.empty((0,10),dtype='float')

    if nspec<=2:
        nrg2=np.empty((0,10),dtype='float')
    if nspec<=3:
        nrg2=np.empty((0,10),dtype='float')
        nrg3=np.empty((0,10),dtype='float')
    if nspec>=4:
        print( "nspec=",nspec)
        print( "Error, nspec must be less than 4")
        stop

    ncols = int(len(nrg_split[1])/12)

    nrg0=np.empty((1,ncols))
    #print nrg_in
    for j in range(len(nrg_split)):
        if nrg_split[j] and j % (nspec+1) == 0:
            time=np.append(time,float(nrg_split[j]))
        elif nrg_split[j] and j % (nspec+1) == 1:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg1=np.append(nrg1,nrg0,axis=0)
        elif nspec>=2 and nrg_split[j] and j % (nspec+1) ==2:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg2=np.append(nrg2,nrg0,axis=0)
        elif nspec==3 and nrg_split[j] and j % (nspec+1) ==3:
            nline=nrg_split[j].split()
            for i in range(ncols):
                nrg0[0,i]=nline[i]
            nrg3=np.append(nrg3,nrg0,axis=0)

    nrg_dict = {}
    nrg_dict['time'] = time
    nrg_dict['nrg1'] = nrg1
    if nspec==2:
        nrg_dict['nrg2'] = nrg2
    elif nspec==3:
        nrg_dict['nrg2'] = nrg2
        nrg_dict['nrg3'] = nrg3

    return nrg_dict

def get_magn_geometry(db,coll,oid):
    file_raw = get_file_by_id(db,coll,ObjectId(oid),'magn_geometry')
    file_lines = file_raw.split('\n')

    parameters = {}
    l = 1
    while '/' not in file_lines[l] and len(file_lines[l])>0:
        lsplit = file_lines[l].split('=')
    #    print lsplit[0].strip()
        if lsplit[0].strip() == 'gridpoints':
            parameters[lsplit[0].strip()] = int(float(lsplit[1].strip()))
        elif lsplit[0].strip() == 'magn_geometry':
            parameters[lsplit[0].strip()] = lsplit[1].strip()[1:-1]
        elif len(lsplit[0]) > 0:
            parameters[lsplit[0].strip()] = float(lsplit[1])
        l += 1
        #print "lsplit",lsplit
    
    #print parameters

    geometry = {}
    #1. ggxx(pi1,pj1,k) 
    geometry['ggxx'] = np.empty(0)
    #2. ggxy(pi1,pj1,k)
    geometry['ggxy'] = np.empty(0)
    #3. ggxz(pi1,pj1,k)
    geometry['ggxz'] = np.empty(0)
    #4. ggyy(pi1,pj1,k) 
    geometry['ggyy'] = np.empty(0)
    #5. ggyz(pi1,pj1,k)
    geometry['ggyz'] = np.empty(0)
    #6. ggzz(pi1,pj1,k)
    geometry['ggzz'] = np.empty(0)
    #7. gBfield(pi1,pj1,k) 
    geometry['gBfield'] = np.empty(0)
    #8. gdBdx(pi1,pj1,k)
    geometry['gdBdx'] = np.empty(0)
    #9. gdBdy(pi1,pj1,k)
    geometry['gdBdy'] = np.empty(0)
    #10. gdBdz(pi1,pj1,k)
    geometry['gdBdz'] = np.empty(0)
    #11. gjacobian(pi1,pj1,k)
    geometry['gjacobian'] = np.empty(0)
    #12. gl_R(pi1,k)
    geometry['gl_R'] = np.empty(0)
    #13. gl_phi(pi1,k)
    geometry['gl_phi'] = np.empty(0)
    #14. gl_z(pi1,k)
    geometry['gl_z'] = np.empty(0)
    #15. gl_dxdR(pi1,k)
    geometry['gl_dxdR'] = np.empty(0)
    #16. gl_dxdZ(pi1,k)
    geometry['gl_dxdZ'] = np.empty(0)

    if 'sign_Ip_CW' in file_raw: 
        l += 4
    else:
        l += 1
    while file_lines[l]:
        line = file_lines[l].split()
        geometry['ggxx'] = np.append(geometry['ggxx'],float(line[0].strip()))
        geometry['ggxy'] = np.append(geometry['ggxy'],float(line[1].strip()))
        geometry['ggxz'] = np.append(geometry['ggxz'],float(line[2].strip()))
        geometry['ggyy'] = np.append(geometry['ggyy'],float(line[3].strip()))
        geometry['ggyz'] = np.append(geometry['ggyz'],float(line[4].strip()))
        geometry['ggzz'] = np.append(geometry['ggzz'],float(line[5].strip()))
        geometry['gBfield'] = np.append(geometry['gBfield'],float(line[6].strip()))
        geometry['gdBdx'] = np.append(geometry['gdBdx'],float(line[7].strip()))
        geometry['gdBdy'] = np.append(geometry['gdBdy'],float(line[8].strip()))
        geometry['gdBdz'] = np.append(geometry['gdBdz'],float(line[9].strip()))
        geometry['gjacobian'] = np.append(geometry['gjacobian'],float(line[10].strip()))
        geometry['gl_R'] = np.append(geometry['gl_R'],float(line[11].strip()))
        geometry['gl_phi'] = np.append(geometry['gl_phi'],float(line[12].strip()))
        geometry['gl_z'] = np.append(geometry['gl_z'],float(line[13].strip()))
        geometry['gl_dxdR'] = np.append(geometry['gl_dxdR'],float(line[14].strip()))
        geometry['gl_dxdZ'] = np.append(geometry['gl_dxdZ'],float(line[15].strip()))
        #print "l",l,float(line[15])
        l += 1
        
    
    #for i in geometry:
    #    plt.title(i)
    #    plt.plot(geometry[i])
    #    plt.show()    

    return parameters, geometry

