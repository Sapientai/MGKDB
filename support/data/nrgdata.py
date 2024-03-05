import glob
import os
import csv
import numpy as np
import h5py
import pathlib
from putils.par_io import Parameters
from putils.plotter import *

import matplotlib.pyplot as plt
from putils.time_traces import find_nearest, mytrapz


class NrgData():
    """NrgData: Class to read a nrg file from GENE
    """
    def __init__(self, folder=None, extensions=None):       
        self.data = []
        self.time = []
        self.dsets = []
        self.params = []
        
        if folder:
            self.folder = folder
        else:
            raise Exception("Don't know where to read from, provide a path")    
            
        if extensions:
            self.extensions=extensions if type(extensions) is list else [extensions]    
        else:
            self.extensions=self.__find_runs()
            
        for ext in self.extensions:
            self.params.append(Parameters(self.folder, ext))
            self.dsets.append(self.__set_dsets(self.params[-1]))
            self.__load_single(ext, self.params[-1])
            
        
        if self.__should_concatenate():
            self.__concatenate()
        
    def __find_runs(self):
        """parse the folder for all files with extension nrg 
        Could do the same for hdf5, but nrg is always written
        """
        ext=[]
        for file in glob.glob(self.folder+'/nrg*'):
            head, tail = os.path.split(file)
            ext.append(tail.replace('nrg',''))
        return ext
                       
    def __should_concatenate(self):
        """ Decide if I should concatenate multiple files
        """        
        if isinstance(self.folder, str):
            file = pathlib.Path(self.folder+"scan.log")
        else:
            file = self.folder / ("scan.log")
        return (not file.exists()) and len(self.extensions)>1

    def __set_dsets(self, params):
        """set content for plotting and h5 read
        """
        dsets = {0: ['n2', r"$n^2$"],
                 1: ['u_par2',r'$u_{||}^2$'],
                 2: ['T_par',r'$T_{||}$'],
                 3: ['T_par',r'$T_{\perp}$'],
                 4: ['Gamma_es',r'$\Gamma_{es}$'],
                 5: ['Gamma_em',r'$\Gamma_{em}$'],
                 6: ['Q_es',r'$Q_{es}$'],
                 7: ['Q_em',r'$Q_{em}$'],
                 8: ['P_es',r'$\Pi_{es}$'], 
                 9: ['P_em',r'$\Pi_{em}$']}
                     
        return dict(list(dsets.items())[0:params.pnt.nrgcols] )
    
    def __load_single(self, extension, parameters):
        """ load a single file
        """
        if parameters.pnt.write_adios:
            raise NotImplementedError('ADIOS not yet implemented')
        if parameters.pnt.write_h5:
            fname = os.path.join(self.folder, 'nrg' + extension + '.h5')
            if not os.path.isfile(fname):
                raise Exception(os.path.abspath(fname) + " does not exist")
            dsets = self.__set_dsets(parameters.pnt.nrgcols)
            nrgfile = h5py.File(fname, 'r')
            timearray = nrgfile.get("/nrg{}".format(parameters.specs[0]) +
                                    "/time")[()]
            dataarray = np.zeros(timearray.size, parameters.pnt.n_spec,
                                 parameters.pnt.nrgcols)
            for i_d, dset in enumerate(dsets):
                for ispec, spec in enumerate(self.specnames):
                    self.data[:, ispec, i_d] = nrgfile.get("/nrg" + spec + "/" + dset)[()]
            nrgfile.close()
        else:
            #open file read as csv, build numpy arrays.
            fname = os.path.join(self.folder, 'nrg' + extension)
            if not os.path.isfile(fname):
                raise Exception(os.path.abspath(fname) + " does not exist")
            data = []
            time = []   
            with open(fname) as nrgfile:
                csvnrg = csv.reader(nrgfile, delimiter=' ', skipinitialspace=True)
                for line in csvnrg:
                    if len(line) == 0:
                        continue
                    if len(line) == 1:
                        time.append(float(line[0]))
                        data.append([[] for _ in range(parameters.pnt.n_spec)])
                        ispec = 0
                    elif len(line) == parameters.pnt.nrgcols:
                        data[-1][ispec] = line
                        ispec += 1
                    else:
                        raise IOError("Incorrect number of columns")
            self.data.append(np.array(data).astype(float, copy=False))
            self.time.append(np.array(time).astype(float, copy=False))         

    def __concatenate(self):
        """ sort and concatenate traces"""             
        self.__sort_extensions()                              
                     
        time = self.time[0]
        data = self.data[0]
        for i_ext in np.arange(1,len(self.extensions)):
            # When times overlap, throw away repeats from previous
            mask = time < self.time[i_ext][0]
            time = time[mask]
            data = data[mask, ...]
            time = np.concatenate((time, self.time[i_ext]))
            data = np.concatenate((data, self.data[i_ext]))
        self.data=[data]
        self.time=[time]
        # this will not support version jumps
        self.dsets=[self.dsets[0]]
        self.params=[self.params[0]]               
                        
    def __sort_extensions(self):
        """ sort the extensions in ascending order"""           
        t_start=np.empty([0])    
        for i_ext, ext in enumerate(self.extensions):
            t_start=np.append(t_start,self.time[i_ext][0]) if t_start.size else self.time[i_ext][0]
        ordered = np.argsort(t_start)
        self.params = [x for _, x in sorted(zip(ordered, self.params))]
        self.extensions = [x for _, x in sorted(zip(ordered, self.extensions))]
        self.dsets = [x for _, x in sorted(zip(ordered, self.dsets))]
        self.data = [x for _, x in sorted(zip(ordered, self.data))]
        self.time = [x for _, x in sorted(zip(ordered, self.time))]

    def plot_fluxes(self, window=None):
        def plot_single(time, data, params, data_lbl):
            n_rows = 2 + int(params.pnt.nrgcols == 10)
            n_cols = params.pnt.n_spec
            if window:
                figure = window
            else:
                figure = plt.figure(figsize=(14,6), dpi= 100, facecolor='w', edgecolor='k')
            for i_sp in range(0, n_cols):
                # heat flux
                ax = figure.add_subplot(n_rows, n_cols, i_sp + 1)
                ax.plot(time, data[:,i_sp,6],'-b',label=data_lbl[6][1])
                if params.pnt.beta>0:
                    ax.plot(time, data[:,i_sp,7],'-m',label=data_lbl[7][1])
                    ax.plot(time, np.zeros_like(time),color='black', linewidth=1)
                set_scales(ax,params)
                ax.autoscale(enable=True, axis='x',tight=True)
                ax.legend(); ax.set_title(params.pnt.specnames[i_sp])
                # particle flux
                ax = figure.add_subplot(n_rows, n_cols, i_sp + n_cols +1)
                ax.plot(time, data[:,i_sp,4],'-b',label=data_lbl[4][1])
                if params.pnt.beta>0:
                    ax.plot(time, data[:,i_sp,5],'-m',label=data_lbl[5][1])
                    ax.plot(time, np.zeros_like(time),color='black', linewidth=1)
                set_scales(ax,params)
                ax.autoscale(enable=True, axis='x',tight=True)
                ax.legend();
                if params.pnt.nrgcols == 10:
                    # parallel momentum flux
                    ax = figure.add_subplot(n_rows, n_cols, i_sp + 2*n_cols + 1)
                    ax.plot(time, data[:,i_sp,8],'-b',label=data_lbl[8][1])
                    if params.pnt.beta>0:
                        ax.plot(time,data[:,i_sp,9],'-m',label=data_lbl[9][1])
                        ax.plot(time,np.zeros_like(time),color='black',linewidth=1)
                    set_scales(ax,params)
                    ax.legend();
            figure.tight_layout()
            return figure
        for (a,b,c,d) in zip(self.time, self.data, self.params, self.dsets): 
            fig=plot_single(a,b,c,d) 
        
    
    def plot_fluctuations(self, window=None):
        if window:
            figure = window
        else:
            figure = plt.figure(figsize=(14,6), dpi= 100, facecolor='w', edgecolor='k')
        def plot_single(time, data, params, data_lbls):
            n_rows = 1
            n_cols = params.pnt.n_spec
            figure = plt.figure(figsize=set_figsize(), dpi= 100, facecolor='w', edgecolor='k')
            for i_sp in range(0, n_cols):  
                ax = figure.add_subplot(n_rows, n_cols, i_sp + 1)
                for i_dset in range(0,4):
                    ax.plot(time, data[:, i_sp, i_dset],label=data_lbls[i_dset][1])
                ax.set_xlabel(time_lbl(params)); ax.legend();ax.set_title(params.pnt.specnames[i_sp])
                set_scales(ax,params)
                ax.autoscale(enable=True, axis='y', tight=True)  
            figure.tight_layout()
            return figure
        for (a,b,c,d) in zip(self.time, self.data, self.params, self.dsets): 
            fig=plot_single(a,b,c,d) 
        
                     
    ## takes hyperparameters from first pnt, if hyperparameters vary through run, will need to pass extension of continuation
    def show_stats(self, ext=0, t_s=None, t_e=None, units=None):
        if not t_s:
            t_s=self.time[0]
        if not t_e:
            t_e=self.time[-1]
        t_s, i_s = find_nearest(self.time, t_s)     
        t_r, i_e = find_nearest(self.time, t_e)     
        for i_spec in range(self.pnt[ext].n_spec):
            print(self.pnt[ext].specnames[i_spec])
            for i_q, quant in enumerate(self.__set_dsets(self.pnt[ext].nrgcols)):
                res_tavg = mytrapz(self.data[i_s:i_e+1, i_spec, i_q], self.time[i_s:i_e+1])
                print("  {} = {:.2f}".format(quant, res_tavg))
                
        if units:
#            TODO
            for i_spec in range(self.pnt.n_spec):
                print(self.specnames[i_spec])
            for i_q, quant in enumerate(self.__set_dsets(self.pnt[ext].nrgcols)):
                res_tavg = mytrapz(self.data[i_s:i_e+1, i_spec, i_q], self.time[i_s:i_e+1])
                print("  {} = {:.2f}".format(quant, res_tavg)) 
