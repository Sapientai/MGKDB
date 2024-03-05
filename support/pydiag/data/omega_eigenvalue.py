# -*- coding: utf-8 -*-
""" Module for reading omega and eigenvalue output files """
import numpy as np

class Eigenvaluedata(object):
    """ Collect the data of an omega or eigenvalue file and store it in a nice numpy array"""

    def __init__(self,common):
        if common.pnt.nonlinear:
            raise RuntimeError("Not a linear simulation - won't read eigenvalues")

        if common.pars["comp_type"]=="'IV'":
            self.parseomegafile(common.fileextension)
        else:
            self.parseeigenvaluesfile(common.fileextension)

    def parseomegafile(self,fileextension):
        """ Parse omega.dat """
        try:
            with open("omega"+fileextension, 'r') as omegafile:
                data = omegafile.readline().split()
                if len(data) < 3:
                    data = data + [np.nan for _ in range(3-len(data))]
                self.growth_rate = [float(data[-2])]
                self.frequency = [float(data[-1])]
        except IOError:
            print("Could not read omega"+fileextension+" file."+ "Fill with NaN!")
            self.growth_rate = [np.nan]
            self.frequency = [np.nan]
#            raise

    def parseeigenvaluesfile(self,fileextension):
        """ Parse eigenvalues.dat """
        try:
            self.growth_rate = []
            self.frequency = []
            with open("eigenvalues"+fileextension, 'r') as evfile:
                header = evfile.readline()
                for line in evfile:
                    data = line.split()
                    self.growth_rate += [float(data[-2])]
                    self.frequency += [float(data[-1])]
        except IOError:
            print("Could not read eigenvalues"+fileextension+" file")
            raise
