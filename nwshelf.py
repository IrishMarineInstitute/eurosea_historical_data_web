from datetime import datetime
from netCDF4 import Dataset, num2date
from motu import motu
import numpy as np
import os

SERVICE = 'NORTHWESTSHELF_ANALYSIS_FORECAST_PHY_004_013-TDS'

PRODUCT = 'MetO-NWS-PHY-hi-TEM'
           

def gregorian_to_datetime(time):
    return [datetime(i.year, i.month, i.day, i.hour) for i in time]

def NWSHELF_Deenish_profile(t0, t1):
    
    OUTPUT_DIRECTORY, OUTPUT_FILENAME = 'static/', 'nwshelf.nc'
    # Remove file if older exists
    if os.path.exists(OUTPUT_DIRECTORY + OUTPUT_FILENAME):
        os.remove(OUTPUT_DIRECTORY + OUTPUT_FILENAME)
        
    # Convert dates to strings
    t0, t1 = t0.strftime('%Y-%m-%d 00:00:00'), t1.strftime('%Y-%m-%d 00:00:00')
    
    # Download        
    motu(SERVICE, PRODUCT, 'static', 'NWSHELF.nc', 
         -10.2122, -10.2120, 51.7431, 51.7433, t0, t1, 'thetao', 'nrt')        
    
    with Dataset(OUTPUT_DIRECTORY + OUTPUT_FILENAME) as nc:
        # Read time
        time = num2date(nc.variables['time'][:], nc.variables['time'].units)
        # Read temperature profiles        
        temp = np.squeeze(nc.variables['thetao'][:])
        
    return gregorian_to_datetime(time), temp