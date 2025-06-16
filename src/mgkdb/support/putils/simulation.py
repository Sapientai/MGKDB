# -*- coding: utf-8 -*-
from .run import Run
from ..data.data import Data
import os

class Simulation:
    ####################################################################
    ## The simulations class embeds the Run class,
    ##    meaning a simulation is a collection of runs
    ##    Aiming at something where a single run can be handled by itself
    ##   for cases to be used not in the GUI """
    ## in_folder [str/Path Obj]: directory gene output files reside
    ## out_folder [str]: directory to save results of diagnostics
    ## extensions [list(str/int)]: extensions of runs to include in diagnostics,
    ##                              pass as list iterable
    def __init__(self, in_folder=None, out_folder=None, extensions=None):
        # folder containing the simulation data
        self.in_folder = in_folder
        if in_folder:
            if not os.path.exists(in_folder):
                raise Exception("input folder does not exist")

        # extensions to be analyzed
        self.extensions = extensions

        # folder for output
        self.out_folder = out_folder
        if out_folder:
            if not os.path.exists(out_folder):
                raise Exception("output folder does not exist")

        # times to process
        self.starttime = -1
        self.endtime = -1

        # how often to step
        self.stepping = 1

        # how many steps to take
        self.max_steps = 'all'

        # this is the par_IO for each extension we have
        self.runs = []
        self.reset_runs()

    def reset_runs(self):
        """
        This method is meant for GUI usage mostly.
        If we already have a simulation object we will be changing folders
        (input, output) and runs to process). Each time we do that we need to
        redefine the object data
        """

        if not self.in_folder or not self.extensions:
            return

        if self.runs:
            self.runs.clear()

        for ext in self.extensions:
            self.runs.append(Run(self.in_folder, ext))


        """
         I put the data here in order to avoid memory duplication
         putting it inside runs, would make sense but continuation runs will
         keep track of data for nothing once they are processed.
         Still need to keep avail_vars and times per run.
         """
        
        self.data = Data(self.in_folder, self.extensions, self.runs)

    def __update_variables_and_times(self, variables, times):
        pass

