# -*- coding: utf-8 -*-

from tkinter import END
import matplotlib.pyplot as plt
import numpy as np
from .baseplot import Plotting
from .diagnostic import Diagnostic


class DiagFieldMomSnapshots(Diagnostic):

    def __init__(self):
        super().__init__()
        print("Initializing Field Mom Snapshots")
        self.name = 'Field Moment Snapshots'
        self.tabs = ['fluxtube']

    def get_info(self):
        self.need_file={'field': True,
                        'mom': True}

        return self.need_file
    
    def setup_options(self, run):
        self.specnames = run.parameters.pnt.specnames
        self.time = []
        self.n_fields = run.parameters.pnt.n_fields
        self.fm_snapshots = []
        self.fm_final = {}
        self.n_moms = run.parameters.pnt.n_moms
        self.n_spectra = int(run.parameters.pnt.n_fields + run.parameters.pnt.n_moms*len(self.specnames))
        self.kx=run.spatialgrid.kx
        self.ky=run.spatialgrid.ky
        self.zgrid = run.spatialgrid.z
        self.momlist = ["dens", "tpar", "tperp", "qpar", "qperp", "upar", 'densI1', 'TparI1', 'TppI1']
        self.field_mom_names=[]
        self.field_mom_names.append('phi')
        if run.parameters.pnt.nonlinear == 'T' or run.parameters.pnt.nonlinear == True:
            self.nonlinear = True
        else:
            self.nonlinear = False
        if self.n_fields > 1:
            self.field_mom_names.append('apar')
        if self.n_fields > 2:
            self.field_mom_names.append('bpar')
        for i in self.specnames:
            for j in range(self.n_moms):
                self.field_mom_names.append(self.momlist[j]+i)
        
        
    def execute(self, data, run, steps, extensions,time_point):
        #print('fms 47')
        self.time.append(time_point)
        nz0 = run.parameters.pnt.nz0
        #print(run.parameters.pnt.nonlinear)
        #print('nonlinear',nonlinear)
        #dummy = input("press key")
        self.zgrid_sparse = [self.zgrid[0],self.zgrid[int(nz0/4)],self.zgrid[int(nz0/2)],self.zgrid[int(3*nz0/4)]]
        if self.nonlinear:
            fm_sparse = np.empty((self.n_spectra,run.parameters.pnt.nx0,run.parameters.pnt.nky0,4),dtype='complex')
   
        #print('fms 54')
        #print('shape of fm_sparse',np.shape(fm_sparse))
        tmp=data.field.phi(step=steps['field'], extension=extensions['field'])
        #print('shape of tmp',np.shape(tmp))
        self.fm_final[self.field_mom_names[0]] = tmp
        if self.nonlinear:
            fm_sparse[0,:,:,0] = tmp[:,:,0]
            fm_sparse[0,:,:,1] = tmp[:,:,int(nz0/4)]
            fm_sparse[0,:,:,2] = tmp[:,:,int(nz0/2)]
            fm_sparse[0,:,:,3] = tmp[:,:,int(3*nz0/4)]
        #print('fms 60')
        if self.n_fields>1:
            tmp=data.field.A_par(step=steps['field'], extension=extensions['field'])
            if self.nonlinear:
                fm_sparse[1,:,:,0] = tmp[:,:,0]
                fm_sparse[1,:,:,1] = tmp[:,:,int(nz0/4)]
                fm_sparse[1,:,:,2] = tmp[:,:,int(nz0/2)]
                fm_sparse[1,:,:,3] = tmp[:,:,int(3*nz0/4)]
            self.fm_final[self.field_mom_names[1]] = tmp
        if self.n_fields>2:
            tmp=data.field.B_par(step=steps['field'], extension=extensions['field'])
            if self.nonlinear:
                fm_sparse[2,:,:,0] = tmp[:,:,0]
                fm_sparse[2,:,:,1] = tmp[:,:,int(nz0/4)]
                fm_sparse[2,:,:,2] = tmp[:,:,int(nz0/2)]
                fm_sparse[2,:,:,3] = tmp[:,:,int(3*nz0/4)]
            self.fm_final[self.field_mom_names[2]] = tmp
             
        #print('fms 73')
        for i_spec, spec in enumerate(run.parameters.specnames):
            for i_quant, quant in enumerate(data.mom[i_spec].varnames.values()):
                tmp = getattr(data.mom[i_spec],quant)(step=steps['mom'], extension=extensions['mom'])
                if self.nonlinear:
                    fm_sparse[self.n_fields+len(self.specnames)*i_spec+i_quant,:,:,0] = tmp[:,:,0]
                    fm_sparse[self.n_fields+len(self.specnames)*i_spec+i_quant,:,:,1] = tmp[:,:,int(nz0/4)]
                    fm_sparse[self.n_fields+len(self.specnames)*i_spec+i_quant,:,:,2] = tmp[:,:,int(nz0/2)]
                    fm_sparse[self.n_fields+len(self.specnames)*i_spec+i_quant,:,:,3] = tmp[:,:,int(3*nz0/4)]
                self.fm_final[self.field_mom_names[self.n_fields+len(self.specnames)*i_spec+i_quant]] = tmp
                        
        #print('fms 82')
        if self.nonlinear:
            self.fm_snapshots.append(fm_sparse)
                
    def dict_to_mgkdb(self):
        
        #print('fms 83')
        fm_out = {}
        if self.nonlinear:
            fm_out['Description'] = 'All fields and moments at selected time points at z = -pi,-pi/2,0,pi/2.  The structure is [field_or_moment][time list][kx,ky,four z points]. The time points are in [time].  The names of the fields and moments are in [field_mom_names].  The appropriate grids are in [kxgrid], [kygrid], and [zgrid_sparse].  The full 3D data for each field and moment at the final time point is stored in [field_mom_final][name]'
        else:
            fm_out['Description'] = 'For linear: The final time point is in [time].  The names of the fields and moments are in [field_mom_names].  The appropriate grids are in [kxgrid], [kygrid], and [zgrid].  The full 3D data for each field and moment at the final time point is stored in [field_mom_final][name]'
        fm_out['time'] = self.time
        fm_out['field_mom_names'] = self.field_mom_names
        fm_out['kxgrid'] = np.roll(self.kx,int(len(self.kx)/2)+1)
        fm_out['kygrid'] = self.ky
        if self.nonlinear:
            fm_out['zgrid_sparse'] = self.zgrid_sparse
        fm_out['zgrid'] = self.zgrid
        fm_out['field_mom_final'] = self.fm_final
        #print('fms 91')
        if self.nonlinear:
            for i in range(len(self.field_mom_names)):
                fm_out[self.field_mom_names[i]] = []
                for j in range(len(self.fm_snapshots)):
                    fm_out[self.field_mom_names[i]].append(self.fm_snapshots[j][i,:,:,:])
        return fm_out
        
    def plot(self, time_requested, output=None, out_folder=None):
        """ For each selected species we have one figure with six subplots.
            Left is vs. kx, right vs. ky; columnwise we plot, log-log, log-lin, lin-in
            Dashed lines are negative values in log-log plot
            Dashed lines are k multiplied values in log-lin plot"""
        pass


