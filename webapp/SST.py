from datetime import datetime
from netCDF4 import Dataset, num2date
from cftime import DatetimeGregorian
from pydap.cas.get_cookies import setup_session
from pydap.client import open_url
from mhw import mhw_processing
from webob import exc
import xarray as xr
import numpy as np

# Set boundaries (W, E, S, N)
xmin, xmax, ymin, ymax = -11.6, -8, 50, 52.8

def SST_request(DBO, dia):
    ''' Retrieves SST requested from the web for given date '''
    
    dia = datetime.strptime(dia, '%Y-%m-%d')
    dia = DatetimeGregorian(dia.year, dia.month, dia.day, 9)
    
    url = 'https://thredds.jpl.nasa.gov/thredds/dodsC/OceanTemperature/MUR-JPL-L4-GLOB-v4.1.nc'

    with Dataset(url) as nc:
         
         while True:
         
             try:
                                 
                 lon = nc.variables['lon'][:]
                 x0, x1 = nearest(lon, xmin), nearest(lon, xmax) + 1
                 
                 lat = nc.variables['lat'][:]
                 y0, y1 = nearest(lat, ymin), nearest(lat, ymax) + 1
                 
                 # Read latest time
                 time = num2date(nc.variables['time'][:], nc.variables['time'].units)
                 
                 i = np.where(time == dia)[0][0]
                 
                 # Read SST
                 SST = nc.variables['analysed_sst'][i - 4 : i + 1, y0 : y1, x0 : x1] - 273.15
                 
                 break
             
             except RuntimeError: continue
         
             except exc.HTTPError: continue
         
    # Subset time for 5 days before selected date
    time = time[i - 4 : i + 1]
    # Convert to Python datetime
    time = [datetime(i.year, i.month, i.day, i.hour) for i in time]
        
    # Get day of year of selected date
    latest = time[-1].timetuple().tm_yday
    # Find time index in climatology
    i = np.where(DBO.clim_time == latest)[0][0]
    # Get climatology SST distribution for selected day of the year    
    seas = DBO.seas[i, :, :]
    # Get 90-th percentile SST distribution for selected day of the year
    pc90 = DBO.pc90[i - 4 : i + 1, :, :]
    # Get SST anomaly as the difference between actual SST and climatology
    ANOM = SST[-1, :, :] - seas
    
    # Marine Heat Waves
    MHS, MHW, MHT = mhw_processing(lon[x0 : x1], lat[y0 : y1], np.array(time), SST, pc90)
    print(MHT)
             
    return lon[x0 : x1], lat[y0 : y1], time[-1], SST[-1, :, :], ANOM, MHS, MHW, MHT
    
def copernicusmarine_datastore(dataset, username, password):    
    cas_url = 'https://cmems-cas.cls.fr/cas/login'
    session = setup_session(cas_url, username, password)
    session.cookies.set("CASTGC", session.cookies.get_dict()['CASTGC'])
    database = ['my', 'nrt']
    url = f'https://{database[0]}.cmems-du.eu/thredds/dodsC/{dataset}'
    try:
        data_store = xr.backends.PydapDataStore(open_url(url, session=session))
    except:
        url = f'https://{database[1]}.cmems-du.eu/thredds/dodsC/{dataset}'
        data_store = xr.backends.PydapDataStore(open_url(url, session=session))
    return data_store    

def nearest(lista, valor):
    return np.argmin(abs(lista - valor))