""" Module with the container objects for single simulation data"""
# -*- coding: utf-8 -*-
from pathlib import Path
from .par_io import Parameters
from .vsp_grid import VspGrid
from .spatial_grid import SpatialGrid
from ..data.profiledata import ProfileData
from .geom import Geometry
from .units import Units
import numpy as np
import os


class Run:
    ### Class containing basic information on a simulation run parameters. ###
    ##  in_folder [str]: directory containing gene output files
    ##  extension [str]: extension of run being processed, ex) 0001 or .dat
    ##
    ###################################################################

    def __init__(self, in_folder=None, extension='.dat'):
        if not os.path.isdir(in_folder):
            raise Exception(os.path.abspath(in_folder) + " does not exist or is undefined")
        
        self.in_folder = Path(in_folder)
        self.extension = extension
        self.parameters = Parameters(self.in_folder,self.extension)
        self.geometry = Geometry(self.in_folder,self.extension,self.parameters)
        self.spatialgrid = SpatialGrid(self.parameters)
        self.vspgrid = VspGrid(self.parameters)
        self.units = Units(self.parameters)
        self.profiles = ProfileData(self.in_folder,self.extension,self.parameters)
        omega_path = str(self.in_folder)+'/omega'+self.extension
        if os.path.isfile(omega_path):
            a = np.genfromtxt(omega_path)
            self.gamma = a[1]
            self.omega = a[2]
        else:
            self.gamma = False
            self.omega = False
