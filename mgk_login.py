# -*- coding: utf-8 -*-
"""
Created on Thu Dec 12 12:49:43 2019

@author: dykua

Functions for handling credentials
"""

from pymongo import MongoClient
import pickle

class mgk_login(object):
    def __init__(self, server='mongodb03.nersc.gov', port='27017', dbname='mgk_fusion', 
                 user='user', pwd = 'pwd'):

        self.login = {'server': server.strip(),
                      'port': port.strip(),
                      'dbname': dbname.strip(),
                      'user': user.strip(),
                      'pwd': pwd.strip()
                      }
        
    def from_saved(self, file_path):
        with open(file_path, 'rb') as pkl:
            info = pickle.load(pkl)
        
        self.login = info
        
        
    def save(self, file_path):
        
        with open(file_path, 'wb') as pkl:
            pickle.dump(self.login, pkl, protocol = pickle.HIGHEST_PROTOCOL)
        print('Login info saved to {}'.format(file_path) )    
            
    def update(self, dict_to_update):
        for key, val in dict_to_update.items():
            if key in self.login:
                self.login[key] = val 
    #   self.login.update(dict_to_update)
                
    def connect(self):
        
        database = MongoClient(self.login['server'].strip())[self.login['dbname'].strip()]
        database.authenticate(self.login['user'].strip(), self.login['pwd'].strip())
        
        return database
        
        