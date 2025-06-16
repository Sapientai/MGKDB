"""Module containing the treatment of GENE's geometry output"""
import numpy as np
import h5py
from .par_io import Parameters
import os
import matplotlib.pyplot as plt


class Geometry:
    """ Class to handle geometry input from GENE runs
        parameters: either Parameters object or parameters as a namedtuple
    """
   
    def __init__(self,folder,extension,parameters):
        ##self.pnt is the parameter dictionary as a namedtuple
        if isinstance(parameters, Parameters):
            self.pnt = parameters.asnamedtuple()
        elif isinstance(parameters, tuple):
            self.pnt = parameters

        self.geomtype = self.pnt.magn_geometry

        ##get geometry from file
        if self.pnt.write_h5:
            self.getgeom_h5(folder,extension)
        elif self.pnt.write_adios:
            raise NotImplementedError("ADIOS not supported")
        else:
            self._getgeom_std(folder,extension)
            
        self.t=1
        ##set plot attribute 
        if self.pnt.x_local:
            setattr(self, 'plot', self.__plot_geom_local)
        if self.pnt.x_global:
            setattr(self, 'plot', self.__plot_geom_xglobal)
        if self.pnt.is3d:
            setattr(self, 'plot', self.__plot_geom_xyglobal)
        
    def _getgeom_std(self,folder,extension):
        geom = self.getgeom(folder,extension)
        if not self.pnt.x_local:
            self.jaco3d = self.jacobian[:,np.newaxis,:]
        elif not self.pnt.y_local:
            raise NotImplementedError("y_local not supported")
        return geom

    @staticmethod
    def untangle_1d(arrlist, start, nxorny):
        """ Process a geometry file section that contains a 1d (x or y) field

        :param arrlist: The entire file as a list of lines
        :param start: The starting index of the quantity in arrlist
        :param nxorny: nx0 or nky0 depending on the type of simulation
        :returns: A 1d numpy array
        """
        arr_1d = np.zeros(nxorny)
        i = 0
        for line in arrlist[start:-1]:
            for j in range(len(line.split())):
                arr_1d[i + j] = line.split()[j]
            i += len(line.split())
            if i >= nxorny:
                break
        return arr_1d

    @staticmethod
    def untangle_2d(arrlist, start, nxorny, nz):
        """ Process a geometry file section that contains a 2d (x or y, z) field

        :param arrlist: The entire file as a list of lines
        :param start: The starting index of the quantity in arrlist
        :param nxorny: nx0 or nky0 depending on the type of simulation
        :param nz: nz0, number of z grid points
        :returns: A 2d numpy array
        """
        arr_2d = np.zeros((nz, nxorny))
        ik = 0
        for line in arrlist[start:-1]:
            arr = line.split()[:]
            lb = ik % nxorny
            ub = min(lb + 16, nxorny)
            k = int(ik/nxorny)
            dim = ub - lb
            arr_2d[k, lb:ub] = arr[0:dim]
            if dim < 16:
                arr_2d[k + 1, 0:16 - dim] = arr[dim:]
            ik += 16
            if ik >= nz*nxorny:
                break
        return arr_2d.T         # want (nx,nz) order

    def getgeom(self,folder,extension,):
        """ Returns the geometry from a non-hdf5 file """
        local = self.pnt.x_local

        with open(os.path.join(folder, "{}{}".format(self.geomtype.strip("'"), \
                                                extension)), "r") as geomfile:
            if local:
                geom = self.getgeom_loc(geomfile, self.pnt.nz0)
            elif self.pnt.y_local:  # x-global
                geom = self.getgeom_glob(geomfile, self.pnt.nz0, self.pnt.nx0)
            elif self.pnt.x_local:  # y-global
                raise NotImplementedError("x_local (y global) not supported")
            else:
                raise NotImplementedError("fully global not supported")
        return geom

    def getgeom_loc(self, geomfile, nz):
        geom = np.empty((16, nz), dtype=np.float64)
        k = 0
        for line in geomfile:
            if len(line.split()) == 16:
                geom[:, k] = line.split()[:]
                k += 1
            elif line.startswith('Cy'):
                self.Cy = float(line.split()[-1])
            elif line.startswith('Cxy'):
                self.Cxy = float(line.split()[-1])
            elif line.startswith('q0'):
                self.q = float(line.split()[-1])
        self.gxx = geom[0]
        self.gxy = geom[1]
        self.gxz = geom[2]
        self.gyy = geom[3]
        self.gyz = geom[4]
        self.gzz = geom[5]
        self.Bfield = geom[6]
        self.dBdx = geom[7]
        self.dBdy = geom[8]
        self.dBdz = geom[9]
        self.jacobian = geom[10]
        self.R = geom[11]
        self.Z = geom[13]
        self.dxdR = geom[14]
        self.dxdZ = geom[15]
        gamma1 = self.gxx*self.gyy - self.gxy**2
        gamma2 = self.gxx*self.gyz - self.gxy*self.gxz
        gamma3 = self.gxy*self.gyz - self.gyy*self.gxz
        self.Kx = -self.dBdy - gamma2/gamma1*self.dBdz
        self.Ky = self.dBdx - gamma3/gamma1*self.dBdz
        if not hasattr(self, 'Cxy'):
            self.Cxy=1.0
        return geom

    def getgeom_glob(self, geomfile, nz0, nxorny):
        """ Subroutine for geometry files from global runs """
        NUMFIELDS = 19
        geom = []

        geomdict = {'q': 0, 'gxx': 1, 'gxy': 2, 'gxz': 3, 'gyy': 4, 'gyz': 5,
                    'gzz': 6, 'Bfield': 7, 'dBdx': 8, 'dBdy': 9, 'dBdz': 10,
                    'jacobian': 11, 'C_y': 12, 'C_xy': 13, 'geo_R': 14,
                    'geo_Z': 15, 'geo_c1': 16, 'geo_c2': 17, 'dpdx_pm_arr': 18}
        pos_start = np.zeros(NUMFIELDS, dtype=int)  # where a field starts
        num = 0
        parheader = True
        geomlist = geomfile.readlines()
        for linnum, line in enumerate(geomlist):
            if parheader:  # ignore the top part of the file (copy of the geometry namelist)
                if line.startswith(r'/'):
                    parheader = False
                continue
            if len(line.split()) == 1:  # the variable names
                try:
                    num = geomdict[line.strip()]
                    pos_start[num] = linnum + 1
                except KeyError:
                    try:  # Test if it is a single number (can occur for 1d arrays)
                        float(line.strip())
                    except ValueError:
                        raise RuntimeError("Unknown entry name in geometry file")
        for num in range(NUMFIELDS):
            if pos_start[num] == 0:  # This should only occur if a field does not exist
                continue
            if num in [0, 12, 13, 18]:  # We have a 1d field following
                tmp = self.untangle_1d(geomlist, pos_start[num], nxorny)
            else:
                tmp = self.untangle_2d(geomlist, pos_start[num], nxorny, nz0)
            geom.append(tmp)
        for key in geomdict:
            setattr(self, key, geom[geomdict[key]])
        self.Cy = self.C_y
        self.Cxy = self.C_xy
        self.q = self.q
        self.R = self.geo_R
        self.Z = self.geo_Z

        self.dxdR = self.geo_c1
        self.dxdZ = self.geo_c2
        del self.C_y
        del self.C_xy
        del self.geo_R
        del self.geo_Z
        del self.geo_c1
        del self.geo_c2
        self.dpdx_pm_arr
        return geom

    def getgeom_h5(self,folder,extension):
        """ Returns the geometry from a hdf5 file """

        geomfile = folder / "{}{}".format(self.geomtype.strip("'"), extension)
        geom = h5py.File(geomfile, 'r')

        self.gxx = geom.get('/metric/g^xx').value
        self.gxy = geom.get('/metric/g^xy').value
        self.gxz = geom.get('/metric/g^xz').value
        self.gyy = geom.get('/metric/g^yy').value
        self.gyz = geom.get('/metric/g^yz').value
        self.gzz = geom.get('/metric/g^zz').value
        self.Cy = geom.get('/metric/C_y').value
        self.Cxy = geom.get('/metric/C_xy').value

        self.Bfield = geom.get('/Bfield_terms/Bfield').value
        self.dBdx = geom.get('/Bfield_terms/dBdx').value
        self.dBdy = geom.get('/Bfield_terms/dBdy').value
        self.dBdz = geom.get('/Bfield_terms/dBdz').value
        self.jacobian = geom.get('/Bfield_terms/Jacobian').value

        if self.pnt.x_local:
            self.R = geom.get('/shape/R').value
            self.Z = geom.get('/shape/Z').value
            self.dxdR = geom.get('/shape/dxdR').value
            self.dxdZ = geom.get('/shape/dxdZ').value

        try:
            self.x_cart = geom.get('/cartesian_cords/x_cart').value
            self.y_cart = geom.get('/cartesian_cords/y_cart').value
            self.z_cart = geom.get('/cartesian_cords/z_cart').value
        except AttributeError:
            pass

        try:
            self.q = geom.get('/profile/q_prof').value
        except AttributeError:
            self.q = self.pnt.q0

        try:
            self.dpdx_arr = geom.get('/profile/dpdx_pm_arr').value
        except AttributeError:
            self.dpdx_arr = self.pnt.dpdx_pm
        geom.close()
        

    def __plot_geom_local(self, spatial_grid):
        self.names = {'gxx': r"$g^{xx}$", 'gxy': r"$g^{xy}$", 'gxz': r"$g^{xz}$",
                      'gyy': r"$g^{yy}$", 'gyz': r"$g^{yz}$", 'gzz': r"$g^{zz}$",
                      'dBdx': r"$dB/dx$", 'dBdy': r"$dB/dy$", 'dBdz': r"$dB/dz$",
                      'jacobian': r"$Jacobian$",
                      'dxdR': r"$dx/dR$", 'dxdZ': r"$dx/dZ$", }
        n_rows = 2
        n_cols = 8

        figure = plt.figure(figsize=(5, 5), dpi=100)
        i_plt = 0

        for fld, lbl in self.names.items():
            i_plt += 1
            a = figure.add_subplot(n_rows, n_cols, i_plt)
            a.plot(spatial_grid.z/np.pi, getattr(self, fld))
            a.set_title(lbl)
            a.set_xlabel(r'$z/\pi$')
            a.tick_params(axis='both', which='major', labelsize=8)
            a.tick_params(axis='both', which='minor', labelsize=8)

        """surface"""
        a = figure.add_subplot(n_rows, n_cols, i_plt+1)
        a.plot(self.R, self.Z)
        a.set_ylabel(r'$Z$ [m]')
        a.set_xlabel(r'$R$ [m]')
        a.tick_params(axis='both', which='major', labelsize=8)
        a.tick_params(axis='both', which='minor', labelsize=8)
        a.set_aspect('equal', adjustable='box')

        """k theta"""
        g_yy = (self.gxx * self.gzz -
                self.gxz**2) * self.jacobian**2
        g_yz = ((self.gxy * self.gxz -
                self.gxx * self.gyz) *
                self.jacobian**2)
        g_zz = ((self.gxx * self.gyy -
                self.gxy**2) * self.jacobian**2)
        e_theta = np.sqrt(
                (self.q * self.Cy)**2 * g_yy +
                2 * self.q * self.Cy * g_yz +
                g_zz)
        k2 = np.sqrt((self.gxx * self.gyy - self.gxy**2)/self.gxx)

        a = figure.add_subplot(n_rows, n_cols, i_plt+2)
        a.plot(spatial_grid.z, self.q * self.Cy / e_theta)
        a.plot(spatial_grid.z, k2)
        a.set_xlabel(r'$z/\pi$', fontsize=8)
        a.legend([r'$k_{\theta}$', r'$k_{2}$'])
        a.tick_params(axis='both', which='major')
        a.tick_params(axis='both', which='minor')
        return [figure]

    def __plot_geom_xglobal(self, spatial_grid=None):
        if not spatial_grid:
            raise ("Missing grids for plotting")
            
        self.names = {'gxx': r"$g^{xx}$", 'gxy': r"$g^{xy}$", 'gxz': r"$g^{xz}$",
                  'gyy': r"$g^{yy}$", 'gyz': r"$g^{yz}$", 'gzz': r"$g^{zz}$",
                  'dBdx': r"$dB/dx$", 'dBdy': r"$dB/dy$", 'dBdz': r"$dB/dz$",
                  'jacobian': r"$Jacobian$",
                  'dxdR': r"$dx/dR$", 'dxdZ': r"$dx/dZ$", }    
            
        n_rows = 2
        n_cols = 6

        figure_1 = plt.figure(figsize=(15, 15), dpi=100)
        figure_2 = plt.figure(figsize=(15, 15), dpi=100)
        i_plt = 0

        x, z = np.meshgrid(spatial_grid.x_a, spatial_grid.z)
        for fld, lbl in self.names.items():
            i_plt += 1

            a = figure_1.add_subplot(n_rows, n_cols, i_plt)
            a.pcolormesh(z, x, getattr(self, fld)[:, :], 
                         cmap=plt.get_cmap('jet'))
            a.set_title(lbl,)
            a.set_xlabel(r'$z/\pi$')
            a.set_ylabel(r'$x/a$')

            b = figure_2.add_subplot(n_rows, n_cols, i_plt)
            b.pcolormesh(self.R, self.Z, getattr(self, fld)[:, :], 
                         cmap=plt.get_cmap('jet'))
            b.set_aspect('equal', 'box')
            b.set_title(lbl)
            b.set_xlabel(r'$R$')
            b.set_xlabel(r'$Z$')

        """k theta"""
        g_yy = (self.gxx * self.gzz -
                self.gxz**2) * self.jacobian**2
        g_yz = ((self.gxy * self.gxz -
                self.gxx * self.gyz) *
                self.jacobian**2)
        g_zz = ((self.gxx * self.gyy -
                self.gxy**2) * self.jacobian**2)

        self.k_theta = np.zeros(self.gxx.shape, dtype=np.float64)
        for i_z in range(self.gxx.shape[0]):
            self.k_theta[i_z, :] =  self.q * self.Cy / np.sqrt(np.abs(     
                (self.q * self.Cy)**2 * g_yy[i_z, :] +
                2 * self.q * self.Cy * g_yz[i_z, :] +
                g_zz[i_z, :]))

        figure_3 = plt.figure(figsize=(5, 5), dpi=100)
        ax = figure_3.add_subplot(1, 1, 1)
        im = ax.pcolormesh(self.R, self.Z, self.k_theta, 
                      cmap=plt.get_cmap('jet'))
        figure_3.colorbar(im, ax=ax)
        ax.set_aspect('equal', 'box')
        ax.set_title(r'$k_{\theta}$')
        ax.set_xlabel(r'$R$')
        ax.set_xlabel(r'$Z$')
        
        figure_1.tight_layout()
        figure_2.tight_layout()
        figure_3.tight_layout()

        return [figure_1, figure_2, figure_3]

    def __plot_geom_xyglobal(self, sim):

        names = {'gxx': r"$g^{xx}$", 'gxy': r"$g^{xy}$", 'gxz': r"$g^{xz}$",
                 'gyy': r"$g^{yy}$", 'gyz': r"$g^{yz}$", 'gzz': r"$g^{zz}$",
                 'Bfield': "Bfield",
                 'dBdx': r"$dB/dx$", 'dBdy': r"$dB/dy$", 'dBdz': r"$dB/dz$",
                 'jacobian': r"$Jacobian$"}

        n_rows = 2
        n_cols = 6

        figure_1 = plt.figure(figsize=(5, 5), dpi=100)
        figure_2 = plt.figure(figsize=(5, 5), dpi=100)
        figure_3 = plt.figure(figsize=(5, 5), dpi=100)

        i_plt = 0

        for fld, lbl in names.items():

            x = sim.runs[0].spatialgrid.x_a
            y = sim.runs[0].spatialgrid.y
            z = sim.runs[0].spatialgrid.z/np.pi
            xind = sim.runs[0].spatialgrid.nx0
            yind = sim.runs[0].spatialgrid.ny0
            zind = sim.runs[0].spatialgrid.nz0

            i_plt += 1

            a = figure_1.add_subplot(n_rows, n_cols, i_plt)
            a.plot(z, getattr(self, fld)[:, int(yind/2), int(xind/2)])
            a.set_title(lbl, fontsize=8)
            a.set_xlabel(r'$z/\pi$', fontsize=8)

            a = figure_2.add_subplot(n_rows, n_cols, i_plt)
            a.plot(x, getattr(self, fld)[int(zind/2), int(yind/2), :])
            a.set_title(lbl, fontsize=8)
            a.set_xlabel(r'$x/a$', fontsize=8)

            a = figure_3.add_subplot(n_rows, n_cols, i_plt)
            a.plot(y, getattr(self, fld)[int(zind/2), :, int(xind/2)])
            a.set_title(lbl, fontsize=8)
            a.set_xlabel(r'$y/\rho_{ref}$', fontsize=8)

        figure_4 = plt.figure(figsize=(5, 5), dpi=100)

        a = figure_4.add_subplot(1, 2, 1)
        a.plot(sim.runs[0].spatialgrid.x_a, getattr(self, 'q'))
        a.set_title('q', fontsize=8)
        a.set_xlabel(r'$x/a$', fontsize=8)

        a = figure_4.add_subplot(1, 2, 2)
        a.plot(sim.runs[0].spatialgrid.x_a, getattr(self, 'dpdx_arr'))
        a.set_title('dpdx_arr', fontsize=8)
        a.set_xlabel(r'$x/a$', fontsize=8)

        return [figure_1, figure_2, figure_3, figure_4]
