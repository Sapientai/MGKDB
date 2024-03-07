# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 20:03:58 2020

@author: dykua
"""

'''
Any command from pymongo:
    https://api.mongodb.com/python/current/tutorial.html
can be used.

mgk_fusion is the database name, 

the collection LinearRuns and NonlinRuns are the most frequently used.
'''
import os
import pymongo
import gridfs
from bson.objectid import ObjectId
from mgk_py_interface import *
#login = mgk_login(server='mongodb03.nersc.gov',
#                  port='27017',
#                  dbname='mgk_fusion',
#                  user='username',   # relace with actual username
#                  pwd = 'password')  # replace with actual pass
##  or login with the saved .pkl credential with the following two lines.
login = mgk_login()
login.from_saved(os.path.abspath('/global/homes/d/dykuang/Mymgk_login.pkl'))
#
mgk_fusion = login.connect()
# this prints out all entries in NonlinRuns (Only _id and Meta info are printted) 
for x in mgk_fusion.NonlinRuns.find({}, {"_id": 1, "Meta": 1}):
    print(x)
    

'''
Some functions are pre-defined for the interaction
'''

# load the data with some query
# by default, _id, Meta, gyrokinetics and diagnostics are loaded.
# category files are not loaded. 

a = load(mgk_fusion, mgk_fusion.NonlinRuns, {"_id":ObjectId("5ef23d8fcc84f3d3245eef90")})

# a is a list whose members dictionary 
print('{} record found.'.format(len(a)))

# check the parameters used for the run found above
print(a[0]['gyrokinetics']['code']['parameters'])

# check some diagnostics
print("available arrays are {}".format(a[0]['Diagnostics'].keys()))
print(a[0]['Diagnostics']['Time'])  # time steps stored.
ballamp_data = a[0]['Diagnostics']['Ballamp'] # you can make copy of part of the data for further processes

# make some plots 
p = diag_plot(a[0])
print("Avalable plots are {}".format(p.avail_diags))
# plot the Ballamp
p.avail_plts['Ballamp']()


# If user only wants to check out some plot:
#diag_plot_from_query(mgk_fusion, mgk_fusion.NonlinRuns, # database and collections
#                     {"_id":ObjectId("5ef23d8fcc84f3d3245eef90")},  # other queries are also ok
#                     diag=['Amplitude Spectra']) # type of diagnostics to plot.

# If the user wnat to load some files into ram:
record =  mgk_fusion.NonlinRuns.find_one({"_id":ObjectId("5ef23d8fcc84f3d3245eef90")}, 
                                         {"Files": 1})
print(record)

# Now load the nrg file for example
# Be careful that the content read are strings like `a, b, c, d\n` with possible headers
# users can use other tools to parse it to numpy array or convert it to other formats after the decoding.
fs = gridfs.GridFS(mgk_fusion)
file = fs.find_one({"_id":ObjectId('5ef23d27cc84f3d3245ee7ae')})
content = file.read() 
print('first few lines in nrg file is: {}'.format(content.decode('utf8').split('\n')[:4])) # decoded by 'utf8'

# Now if the user want to examine all data belonging to this entry locally.
download_from_query(mgk_fusion, mgk_fusion.NonlinRuns, # database and collections
                     {"_id":ObjectId("5ef23d8fcc84f3d3245eef90")},  # mongo query
                     destination='./from_mgkdb') # directory to download to

# Files that are maybe too large to load into ram now is downloaded to the specified destimation.


#===================================================================================





