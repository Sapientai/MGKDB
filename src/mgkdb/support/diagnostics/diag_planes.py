#!/usr/bin/env python3
from tkinter import END
import os
import matplotlib.pyplot as plt
import numpy as np
import scipy.interpolate as interp
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from ..putils.fourier import kx_to_x, ky_to_y
#from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagPlanes(Diagnostic):
    # pylint: disable=invalid-name
    def __init__(self, avail_vars=None, specnames=None):
        super().__init__()
        self.name = 'Poloidal_planes'
        self.tabs = ['fluxtube', 'xglobal']

        self.help_txt = """Plot contours on poloidal planes
                        \n
                        \nQuantity : quantity to plot
                        \nspec: which species to plot (def. all if spec dep)
                        \nz_res: resolution in poloidal direction (def. 400)
                        \nt avg : time averaged (def. False)"""

        self.avail_vars = avail_vars

        self.specnames = specnames

        self.opts = {"quant": {'tag': "Quant", 'values': None, 'files': ['field','mom']},
                     "spec": {'tag': "Spec", 'values': self.list_specnames()},
                     "torangle": {'tag': "position", 'values': [0]},
                     "z_res": {'tag': "z res", 'values': [400]},
                     "del_zonal": {'tag': "del zonal", 'values': [False, True]},
                     "only_zonal": {'tag': "only zonal", 'values': [False, True]},
                    "t_avg": {'tag': "t avg", 'values': [False, True]}}

        self.set_defaults()

        self.options_gui = Diagnostic.OptionsGUI()

    def set_options(self, run_data, avail_vars):
        self.avail_vars = avail_vars
        self.specnames = run_data.specnames
        if self.opts['quant']['value'] is None:
            raise RuntimeError("No quantities given for poloidal planes")
        self.torangle = self.opts['torangle']['value'] % 2*np.pi
        # Extend the z grid to pi
        self.z_full = np.append(run_data.spatialgrid.z, np.pi)
        self.z_full_fine = np.linspace(self.z_full[0], self.z_full[-1], self.opts['z_res']['value'])
        # TODO find how not to recompute is is another time
        self.triangulation = self._calc_triangulation(run_data)
        self.ny = 2*run_data.pnt.nky0
        self.dy = run_data.pnt.rhostar * run_data.pnt.minor_r*run_data.pnt.ly / self.ny

        if (run_data.pnt.x_local):
            self.q_prof = run_data.pnt.q0*(
                1 + run_data.pnt.shat/run_data.pnt.x0*(run_data.spatialgrid.x_a
                                                       - run_data.pnt.x0))
        else:
            self.q_prof = run_data.geometry.q
            
        self.Cy = run_data.geometry.Cy
        self.n0_global = run_data.pnt.n0_global
        self.get_needed_vars()
        self.get_spec_from_opts()
        return self.needed_vars

    def execute(self, data, step):
        for file in self.needed_vars:
            # loop over quaitites in that file
            for quant in self.needed_vars[file]:
                # loop over quaitites in that file
                if self.needed_vars[file][quant]:
                    if file == 'field':
                        # no species dependency
                        
                        data_in = getattr(getattr(data, file), quant)(step.time,
                                                                      getattr(step, file))
                        self.data_out = self._prepare_plane(data_in)

                    else:
                        # spec dependent
                        for spec in self.specnames:
                            data_in = getattr(getattr(data, file + '_' + spec), quant)(step.time,
                                                                                       getattr(step,
                                                                                               file))
                            self.data_out = self._prepare_plane(data_in)

    def save(self):
        print("nothing")



    def plot(self, time_requested=None, output=None, out_folder='', terminal=None):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.set_aspect('equal', 'box')
        ax.tricontourf(self.triangulation, self.data_out.flatten(), 50)
        ax.set_xlabel(r"$R[m]$")
        ax.set_ylabel(r"$Z[m]$")
        fig.tight_layout()
        fig.show()
        if output:
            outpath = os.path.join(out_folder, output)
            fig.savefig(outpath + '.jpeg')
        print("done")

    def _calc_triangulation(self, run, recalculate=False):
        """ Calculate the triangulation based on local/global

        :param recalculate: Force recalculation of the triangulation, otherwise
        a previous result is used
        """
        if not run.pnt.y_local:
            raise RuntimeError("y-global is not supported")
        if (not recalculate):
            if run.pnt.x_local:
                return self._calc_triangulation_local(run)
            else:
                return self._calc_triangulation_xglobal(run)
        else:
            return self.triangulation

    def _calc_triangulation_xglobal(self, run):
        """ Calculate a triangulation based on R(x,z), Z(x,z) recovered from
        global geometry"""
        # These are the values at x=x0 extended so that z covers [-pi, pi]

        ## JOHNS COMMENT:  I swapped the indicies on the pad function from ((0,0),(0,1)) to ((0,1), (0,0)) and added
        ## the transpose so that dimensions matched for RectBivariateSpline constructor.  Not sure of correctness
        Rz = np.pad(run.geometry.R, ((0, 1), (0, 0)), mode="wrap").transpose()
        Zz = np.pad(run.geometry.Z, ((0, 1), (0, 0)), mode="wrap").transpose()
       

        R_pos = interp.RectBivariateSpline(run.spatialgrid.x_a, self.z_full, Rz)(run.spatialgrid.x_a, self.z_full_fine)
        Z_pos = interp.RectBivariateSpline(run.spatialgrid.x_a, self.z_full, Zz)(run.spatialgrid.x_a, self.z_full_fine)
        # Calculate a triangulation based on R(x,z) and Z(x,z)
        RZtri = mtri.Triangulation(R_pos.flatten(), Z_pos.flatten())
        # Mask central hole
        centretri = mtri.Triangulation(R_pos[0, :], Z_pos[0, :])
        centermask = np.full(RZtri.triangles.shape[0], False)
        for ct in centretri.triangles:
            start = np.where(ct.mean() == RZtri.triangles.mean(axis=1))
            centermask[start] = True
        RZtri.set_mask(centermask)
        self.triangulation = RZtri
        return self.triangulation

    def _calc_triangulation_local(self, run):
        """ Calculate a triangulation based on R(x,z), Z(x,z) recovered from
        flux-tube geometry"""
        # These are the values at x=x0 extended so that z covers [-pi, pi]
        Rz = np.pad(self.geom.R, (0, 1), mode="wrap")
        Zz = np.pad(self.geom.Z, (0, 1), mode="wrap")
        # Interpolate for the x direction
        dxdR = np.pad(self.geom.dxdR/self.geom.gxx, (0, 1), mode="wrap")
        dxdZ = np.pad(self.geom.dxdZ/self.geom.gxx, (0, 1), mode="wrap")
        x_phys = (run.spatialgrid.x_a - run.pnt.x0)*run.pnt.Lref
        R_pos = interp.RectBivariateSpline(x_phys, self.z_full, Rz + np.outer(x_phys, dxdR))(x_phys,
                                                                                             self.z_full_fine)
        Z_pos = interp.RectBivariateSpline(x_phys, self.z_full, Zz + np.outer(x_phys, dxdZ))(x_phys,
                                                                                             self.z_full_fine)
        # Calculate a triangulation based on R(x,z) and Z(x,z)
        RZtri = mtri.Triangulation(R_pos.flatten(), Z_pos.flatten())
        # Mask central hole
        centretri = mtri.Triangulation(R_pos[0, :], Z_pos[0, :])
        centermask = np.full(RZtri.triangles.shape[0], False)
        for ct in centretri.triangles:
            start = np.where(ct.mean() == RZtri.triangles.mean(axis=1))
            centermask[start] = True
        RZtri.set_mask(centermask)
        self.triangulation = RZtri
        return self.triangulation

    def _prepare_plane(self, data):
        # remove zonal or nonzonal as needed
        data = self._manage_zonal(data)
        nx, nky, nz = data.shape
        data_ext_re = self.applyBC(data)
        data_out = np.empty((nx, len(self.z_full_fine)), dtype=float)
        for i_x in range(nx):
            y_in = self.Cy[i_x]*(self.q_prof[i_x]*self.z_full_fine -
                                 self.torangle)
            # now reduce y to get the correct index
            ny = y_in / self.dy # +numel(y_in)/2
            # linear interpolation hardcoded
            cl0 = ((ny % self.ny) + self.ny) % self.ny
            d_l = cl0 - np.fix(cl0)
            d_u = 1 - d_l
            cl = np.fix(cl0)
            i_u = (((cl+1 % self.ny) + self.ny) % self.ny).astype(int)
            i_l = (((cl % self.ny) + self.ny) % self.ny).astype(int)
            posyrange = np.arange(0, self.ny)
            data_interp = interp.RectBivariateSpline(posyrange, self.z_full, data_ext_re[i_x, ...])
            data_interp_2d=  data_interp(posyrange, self.z_full_fine)
            for i_z in range(len(self.z_full_fine)):
                data_out[i_x, i_z] = (d_u[i_z]*(data_interp_2d[i_l[i_z], i_z]) +
                        d_l[i_z] * (data_interp_2d[i_u[i_z],i_z]))
        return data_out


    def applyBC(self, data_in):
        # Apply // boundary condition
        nx, nky, nz = data_in.shape
        if nky == 1:
            data_ext = np.zeros([nx, 51, nz+1],dtype=np.cdouble)
            data_ext[:, 1, 0:-1] = data_in
        else:
            data_ext = np.zeros([nx, nky, nz+1],dtype=np.cdouble)
            data_ext[:, :, 0:-1] = data_in


        for i_y in np.arange(0, nky):
                # z=pi point
                #print("DEBUG:, ", self.q_prof)
        
                data_ext[:, i_y, -1] =  data_in[:, i_y, 0] * np.exp(-2.0j * np.pi *
                                self.n0_global * i_y * self.q_prof)

                #data_ext[:, i_y, -1] =  data_in[:, i_y, 0] * np.exp(-2.0j * np.pi *
                #                self.n0_global * i_y * self.q_prof)
        return ky_to_y(data_ext, nky)

    def _manage_zonal(self, data):
        if self.opts['del_zonal']['value']:
            data[:, 0, :] = 0.0
        if self.opts['only_zonal']['value']:
            data[:, 1:-1, :] = 0.0
        return data
