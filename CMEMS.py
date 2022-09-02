from datetime import datetime, timedelta
from netCDF4 import MFDataset, num2date
from pytz import timezone
from motu import motu
import numpy as np
import os

names = {
    'MetO-NWS-PHY-hi-TEM':            'NORTHWEST-SHELF-',
    'cmems_obs-oc_atl_bgc-plankton_': 'OCEANCOLOUR-'
    }

def download_oceancolour(SERVICE, PRODUCT, key, time):
    
    # Create output directory to download *.nc files
    localpath = os.getcwd() + '/oceancolour'
    if not os.path.isdir(localpath):
        os.mkdir(localpath)
        
    # Retrieve names of *.nc files already downloaded and save to list
    local = update_local_directory(localpath, '.nc')
   
    # Download files (MY)    
    cmems_file_download(time, local, localpath, SERVICE[0], PRODUCT[0], key,
                        variable='CHL', dataset='my', checktime=True)         
    # Download files (NRT)
    cmems_file_download(time, local, localpath, SERVICE[1], PRODUCT[1], key,
                        variable='CHL', dataset='nrt', checktime=False)
    
    # Update list of names of *.nc files already downloaded
    local = update_local_directory(localpath, '.nc')
    local = ['oceancolour/' + i for i in local]
    
    # Read from NetCDF collection
    with MFDataset(local, aggdim='time') as nc:
        # Read time
        time = num2date(nc.variables['time'][:], nc.variables['time'].units)        
        # Read chlorophyll
        chlorophyll = np.squeeze(nc.variables['CHL'][:])
    # Convert time to datetime object
    time = np.array(gregorian_to_datetime(time))   
   
    return time, chlorophyll

def download_nwshelf(SERVICE, PRODUCT, time):
            
    # Create output directory to download *.nc files
    localpath = os.getcwd() + '/nwshelf'
    if not os.path.isdir(localpath):
        os.mkdir(localpath)
        
    # Retrieve names of *.nc files already downloaded and save to list
    local = update_local_directory(localpath, '.nc')
   
    # Download files  
    cmems_file_download(time, local, localpath, SERVICE, PRODUCT, PRODUCT)         
    
    # Update list of names of *.nc files already downloaded
    local = update_local_directory(localpath, '.nc')
    local = ['nwshelf/' + i for i in local]
    
    # Read from NetCDF collection
    with MFDataset(local, aggdim='time') as nc:
        # Read time
        time = num2date(nc.variables['time'][:], nc.variables['time'].units)
        # Read depth
        depth = nc.variables['depth'][:]
        # Read temperature
        temperature = np.squeeze(nc.variables['thetao'][:])
    # Convert time to datetime object
    time = np.array(gregorian_to_datetime(time))   
    # Convert depths to intergers
    depth = np.array([int(i) for i in depth])
    
    return depth, time, temperature
   
    
def cmems_file_download(time, local, localpath, SERVICE, PRODUCT, key,
        variable='thetao', dataset='nrt', checktime=False):
    
    # Convert dates to strings
    t0, t1 = time[0].date(), time[-1].date()
    
    # Build daily time array
    t = []
    while t0 <= t1:
        t.append(t0); t0 += timedelta(days=1)    
        
    # Download files day by day
    for i in t:
        # Set file name
        file = names[key] + i.strftime('%Y%m%d') + '.nc'
        if ( file not in local ):
            print(f'Downloading {file} from {PRODUCT}...')
            if variable == 'thetao':
                t0 = i.strftime('%Y-%m-%d 00:00:00')
                t1 = i.strftime('%Y-%m-%d 23:00:00')
            elif variable == 'CHL':
                t0 = i.strftime('%Y-%m-%d 00:00:00')
                t1 = i.strftime('%Y-%m-%d 00:00:00')
            motu(SERVICE, PRODUCT, localpath, file, -10.2122, -10.2120, 
                 51.7431, 51.7433, t0, t1, variable, dataset)  
            
            # Check that file exists
            if not os.path.exists(localpath + '/' + file):
                return
            
def update_local_directory(localpath, extension):
    ''' Get a list with the names of *.xml files already downloaded '''
    local = []
    for file in os.listdir(localpath):
        if file.endswith(extension):
            local.append(file)
    return local            

def gregorian_to_datetime(time):
    return [timezone('UTC').localize(datetime(i.year, i.month, i.day, i.hour)) for i in time]