#!/usr/bin/env python
# coding: utf-8

# ### Import necessary libraries

# In[1]:


import numpy as np
import geopandas as gpd
import rasterio
from rasterio.plot import show
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
#get_ipython().run_line_magic('matplotlib', 'inline')
import os
from geopy.geocoders import Nominatim

import time
start = time.perf_counter()


# ### Get the address of the building

# In[12]:


address = 'Andreas Vesaliusstraat 13 3000 Leuven'  #input("Enter an address in Flanders:")
'''
Tried addresses: 'Monseigneur Ladeuzeplein 21, 3000 Leuven' 
    'Sint-Pietersvliet 7, 2000 Antwerpen' 
    'Schoenmarkt 21 Antwerp' 
    'Sint-Paulusstraat 22, 2000 Antwerpen'
    'Andreas Vesaliusstraat 13 3000 Leuven' 
    'Jozef Vandaleplein, 8500 Kortrijk', 
    'Sint-Paulusstraat 22, 2000 Antwerpen'
    'Monseigneur Ladeuzeplein 21, 3000 Leuven'
    
    '''

# Check if it is a correct address
df = gpd.tools.geocode(address)
df


# ### Read the `csv` file containing the data of bounds values of the raster images and clean the data

# In[13]:


# Locate the coresponding Tiff file where the address lies
import pandas as pd
df = pd.read_csv('Data/bound_data.csv', sep='\t')
del df['Unnamed: 0']
df = df.set_index('i')


# ### Using `Nominatim`, get the coordinates of the area of interest in `crs EPSG:31370`.

# In[14]:


from shapely.geometry import Point, LineString, Polygon
import requests 
def get_coordinates(address: str):
    req = requests.get(f"https://loc.geopunt.be/v4/Location?q={address}").json()
    info = {'address' : address, 
                'x_value' : req['LocationResult'][0]['Location']['X_Lambert72'],
                'y_value' : req['LocationResult'][0]['Location']['Y_Lambert72'],
                'street' : req['LocationResult'][0]['Thoroughfarename'],
                'house_number' : req['LocationResult'][0]['Housenumber'], 
                'postcode': req['LocationResult'][0]['Zipcode'], 
                'municipality' : req['LocationResult'][0]['Municipality']}
    
    detail = requests.get("https://api.basisregisters.vlaanderen.be/v1/adresmatch", 
                          params={"postcode": info['postcode'], 
                                  "straatnaam": info['street'],
                                  "huisnummer": info['house_number']}).json()
    building = requests.get(detail['adresMatches'][0]['adresseerbareObjecten'][0]['detail']).json()
    build = requests.get(building['gebouw']['detail']).json()
    info['polygon'] = [build['geometriePolygoon']['polygon']]
    points = info['polygon'][0]['coordinates'][0] 
    return info

info = get_coordinates(address)
pointList = info['polygon'][0]['coordinates'][0] 
X, Y = info['x_value'], info['y_value']
# pointList
poly = Polygon([[p[0], p[1]] for p in pointList])
Area  = poly.area


# ### Find the index number of the raster file where the area of interest is located

# In[15]:


#Find the index of the rasterfile

df = df[(df['left'] <= X) & (X <= df['right'])] 
df = df[(df['bottom'] <= Y) & (Y <= df['top'])]

i = df.index.item()
i


# ### Open the DSM and DTM `Geotiff` images corresponding to the area of interest and `clip` them with the polygon of the house using `rasterio`. Get the clipped CHM array

# In[16]:


import rioxarray as rxr
 
geometries = [{'type': 'Polygon','coordinates': [pointList]}] # the shape of the polygon

# Open the DSM and DTM Geotiff images corresponding to the area of interest
DSM = rxr.open_rasterio(f'zip+https://downloadagiv.blob.core.windows.net/dhm-vlaanderen-ii-dsm-raster-1m/DHMVIIDSMRAS1m_k{i}.zip!/GeoTIFF/DHMVIIDSMRAS1m_k{i}.tif', masked=True)
#DSM = rxr.open_rasterio('Data/DSM_Data/DHMVIIDSMRAS1m_k32.tif', masked=True)
# Clip the DSM and DTM Geotiff images with the plygon
clipped_DSM = DSM.rio.clip(geometries, from_disk = True)


DTM = rxr.open_rasterio(f'zip+https://downloadagiv.blob.core.windows.net/dhm-vlaanderen-ii-dtm-raster-1m/DHMVIIDTMRAS1m_k{i}.zip!/GeoTIFF/DHMVIIDTMRAS1m_k{i}.tif', masked=True)
#DTM = rxr.open_rasterio('Data/DTM_Data/DHMVIIDTMRAS1m_k32.tif', masked=True)

clipped_DTM = DTM.rio.clip(geometries, from_disk = True)
 
# Get the clipped CHM array
clipped_CHM = clipped_DSM - clipped_DTM
a = clipped_CHM

# Replace the nan values with 0
clipped_CHM = np.where(np.isnan(a), 0, a)
z = clipped_CHM[0]

# The maximum value of the clipped CHM corresponds to the height of the building
z.max()


# In[17]:


# Create the meshgrid

X1,Y1 = clipped_CHM[0].shape
x = range(X1+2)
y = range (Y1+2)
x,y = np.meshgrid(x, y, indexing='ij')

z = clipped_CHM[0]

# Padding the z value
z = np.pad(z, 1, mode='constant')
z.shape
x.shape, y.shape, z.shape

finish = time.perf_counter()
print(f'Complete in {round(finish - start, 2)}, seconds')


# ### Plot the 3D image with `mayavi`

# In[19]:


#import mayavi
from mayavi import mlab
mlab.figure(size=(500, 500), bgcolor=(0.16, 0.28, 0.46))
mlab.mesh(x,y,z) 
mlab.colorbar(orientation='vertical', title='Height')
mlab.colorbar.font_size = 8
mlab.show()


# In[18]:


import plotly.graph_objects as go
fig = plt.figure(figsize=(60, 60))
fig = go.Figure(data=[go.Surface(z=z)])
fig.show()

import streamlit as st
st.plotly_chart(fig)