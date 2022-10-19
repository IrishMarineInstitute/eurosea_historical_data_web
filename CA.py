from netCDF4 import Dataset, num2date
from datetime import datetime, timedelta
from motu import motu
import numpy as np
import os

SERVICE = 'OCEANCOLOUR_ATL_BGC_L4_MY_009_118-TDS'

PRODUCT = 'cmems_obs-oc_atl_bgc-plankton_my_l4-gapfree-multi-1km_P1D'

# Set boundaries (W, E, S, N)
xmin, xmax, ymin, ymax = -11.6, -8, 50, 52.8

def oceancolour(edate):
    ''' Download requested OCEANCOLOUR data '''
        
    OUTPUT_DIRECTORY, OUTPUT_FILENAME = 'static/', 'OCEANCOLOUR.nc'
    # Remove file if older exists
    if os.path.exists(OUTPUT_DIRECTORY + OUTPUT_FILENAME):
        os.remove(OUTPUT_DIRECTORY + OUTPUT_FILENAME)
        
    dia = datetime.strptime(edate, '%Y-%m-%d').date()
    
    idate = (dia - timedelta(days=73)).strftime('%Y-%m-%d %H:%M:%S')
        
    motu(SERVICE, PRODUCT, OUTPUT_DIRECTORY, OUTPUT_FILENAME, 
         -11.6, -8, 50, 52.8, idate, edate, 'CHL', 'my')
    
    with Dataset(OUTPUT_DIRECTORY + OUTPUT_FILENAME) as nc:
        # Read coordinates
        lon, lat = nc.variables['lon'][:], nc.variables['lat'][:]        
        # Read time
        time = num2date(nc.variables['time'][:], nc.variables['time'].units)
        # Read chlorophyll
        data = np.squeeze(nc.variables['CHL'][:])
    
    anom = get_anom(data)
    
    return lon, lat, time[-1], data[-1, :, :], anom

def get_anom(data):
    ''' Get chlorophyll anomaly as the difference between present values and 
    the median of the 60-day period from 73 days to 14 days before present '''
    
    # Current values
    now = data[-1, :, :]
    # Array of 60-day past values
    past = data[0:-14, :, :]
    # Median
    med = np.nanmedian(past, axis=0)
    # Return difference (anomaly)
    return now - med  