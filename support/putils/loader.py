# -*- coding: utf-8 -*-

from bisect import bisect_left, bisect_right
from copy import deepcopy
import numpy as np


class Loader:
    """ This does the nasty job. We need for a given timestep to be able to load
        any kind of data. The idea is the following:
            1- the user sets folder and runs
            2- GUI determines which files and variables are available
            3- GUI fetches all times from all the files
            4- user selects a time window and a series of diagnostics
            5- GUI takes the subset of files that are needed
            5- GUI takes the requested subinterval in time
            6- loop over all times

            -- I win.
            """

    def __init__(self):
        pass
    
    def set_interval(self, diagnostics, data, run, t_start, t_end, step):    
        self.need_file={'field': False,
                        'mom': False}

        #print("in loader data.av_times['field'].times",data.av_times['field'].times)
        #dummy = input('press key')
        #trigger the file needed from all diagnostic        
        for diag in diagnostics:
            my_files=diag.get_info()
            for k in self.need_file.keys():
                self.need_file[k]=self.need_file[k] or my_files[k]
            diag.setup_options(run)
        
        #append all times together
        #TODO this is bad. shoould rather use istep here to simplify
        times=np.array([])
        for k in self.need_file.keys():
            if self.need_file[k]:
                if times.size==0:
                    times=data.av_times[k].times
                else:
                    times=np.intersect1d(times, data.av_times[k].times)
                
        times=np.unique(times)
        
        i_s = bisect_left(times, t_start)
        i_e = bisect_right(times, t_end)
        if i_s == len(times):
            i_s -= 1
        self.times = times[i_s:i_e:step]
        self.t_start = times[0]
        self.t_end = times[-1]
        
        self.steps=[{}]*self.times.size
        self.files=[{}]*self.times.size

        #TODO extension is the same, no need of dictionary
        for k in self.need_file.keys():
            if self.need_file[k]:
                dum, dum2, inds=np.intersect1d(self.times,data.av_times[k].times, return_indices=True)
                for i_st,st in enumerate(inds):
                
                    if not self.steps[i_st]:
                        self.steps[i_st]={k: data.av_times[k].steps[st]} 
                        self.files[i_st]={k: data.av_times[k].files[st]} 
                    else:
                        self.steps[i_st].update({k: data.av_times[k].steps[st]})
                        self.files[i_st].update({k: data.av_times[k].files[st]}) 
                
