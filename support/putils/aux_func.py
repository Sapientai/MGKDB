#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  6 16:29:16 2019

"""
import numpy as np


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def find_nearest_points(array, val_min, val_max):

    array = np.asarray(array)
    idx_min = (np.abs(array - val_min)).argmin()
    idx_max = (np.abs(array - val_max)).argmin()

    if idx_max == 0:
        idx_min = 0
        idx_max = 1

    if idx_min >= idx_max:
        if (idx_min + 1) == len(array):
            idx_min = idx_max - 1
        else:
            idx_max = idx_min + 1

    return idx_min, idx_max
