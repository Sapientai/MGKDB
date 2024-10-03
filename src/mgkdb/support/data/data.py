""" Module containing the Data class"""
# -*- coding: utf-8 -*-

from .base_file import GENEfile
import numpy as np

class Data:
    """ Class to provide the data containers of a GENE parameters/simulation"""
    def __init__(self, in_folder, extensions, runs=None):  
        self.av_vars = {'field': False,
                        'mom': False}
    
        self.av_times={'field': None,
                        'mom': None}
        self.field=None
        self.mom=[]
        
        if runs:
            if not isinstance(runs, list):
                runs = [runs]
            if not isinstance(extensions, list):
                extensions = [extensions]
            for run,ext in zip(runs,extensions):
                self.__map_a_run(in_folder, ext, run.parameters)
                
                    
    def __map_a_run(self, folder, extension, parameters):
        """
        for each field that has been saved in this restart we
        1. create a file object if needed,
        2. update the available variables
        3. get the times
        """
        # field file
        if parameters.pnt.istep_field > 0:
            if not self.av_vars['field']:
                self.field=GENEfile(folder, extension, 'field', parameters)
                self.av_vars['field']=True
                t,s,f=self.field.get_times_and_inds()
                self.av_times['field']=TimeStep(t,s,f)
            else:    
                self.field.redirect(folder,extension, parameters)
                t,s,f=self.field.get_times_and_inds()
                self.av_times['field'].join_continuation(t,s,f)
                
        # mom files
        if parameters.pnt.istep_mom > 0:
            if not self.av_vars['mom']:
                self.av_vars['mom']=True
                for i_spec in np.arange(parameters.pnt.n_spec):
                    self.mom.append(GENEfile(folder, extension, 'mom', parameters,parameters.species[i_spec]['name']))
                
                t,s,f=self.mom[0].get_times_and_inds()
                self.av_times['mom']=TimeStep(t,s,f)
            else:    
                self.field.redirect(folder,extension,parameters)
                t,s,f=self.field.get_times_and_inds()
                self.av_times['mom'].join_continuation(t,s,f)
   


class AvailableTimes:
    pass


class TimeStep:
    def __init__(self, times, steps, files):
        self.times = times  # times in GENE units
        self.steps = steps  # step in the file 
        self.files = files  # file extension      
        
    def join_continuation(self, times, steps, files):
        self.steps = np.append(self.steps[self.times<times[0]], steps)
        for i, e in reversed(list(enumerate(self.files))):
            if not self.times[i] < times[0]:
                self.files.remove(e)
            else:
                break
        self.files.extend(files)
        self.times = np.append(self.times[self.times<times[0]], times)
        
