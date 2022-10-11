from opendrift.readers import reader_netCDF_CF_generic
from opendrift.readers import reader_global_landmask
from opendrift.models.oceandrift import OceanDrift # Import OceanDrift module
from datetime import datetime, timedelta
from netCDF4 import Dataset
from pytz import timezone
import numpy as np
from PIL import Image
from math import pi
import Plot
import os

def arrows(DBO, images, request):
    ''' Retrieve date selection for surface currents '''  
    # Date for surface currents information
    datestring = ''
    if request.form.get('times'):
        # Get user's selection of vector variables (winds or currents)
        user_variables = request.form.getlist('vectors')
        # Get date selection as string
        datestring = request.form.get('times')
        # Get date selection as datetime
        fecha = datetime.strptime(datestring, '%Y-%m-%d')   

        for variable in user_variables:         
            var = variable.replace(' ', '-')
            # Get currents for the selected date
            u, v, t = vector_request(DBO, fecha, variable)      
            # Create NetCDF for OpenDrift
            fname = uvcdf(u, v, t, var)    
            # Run OpenDrift
            fout = Deenish_opendrift(fname, t, var)
            # Get displacements around starting position
            Dx, Dy = get_displacements(fout)                                          
            # Plot surface currents
            arrows = Plot.Plot_Arrows(u, v, t, variable)                                                           
            # Plot displacements
            circles = Plot.Plot_Displacements(u, v, Dx, Dy, t)
            # Concatenate vertically
            currents = Plot.add_border(get_concat_v(arrows, circles))                    
            # Save figure
            currents.save(f'static/Deenish-{var}.jpg', quality=95)   
            # Add new figure to figure list
            images.append(f'Deenish-{var}.jpg')
            
    return images, datestring

def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height), color='white')
    dst.paste(im1, (0, 0))
    dst.paste(im2, (int(.5*im1.width-.5*im2.width), im1.height))
    return dst    

def Deenish_opendrift(file, time, var):
    # Artificial, extended domain
    x0, x1, y0, y1 = -12, -8, 50, 53
    
    landmask = reader_global_landmask.Reader(
    extent=[x0, y0,  # min. longitude, min. latitude, 
            x1, y1]) # max. longitude, max.latitude
    
    fileOut = os.environ.get('static') + 'OpenDrift-' + time[0].strftime('%Y%m%d') + f'-{var}.nc' 
    
    x, y = float(os.environ.get('lon')), float(os.environ.get('lat'))
    
    o = OceanDrift(loglevel=50)
    
    ocean = reader_netCDF_CF_generic.Reader(file)
    
    o.add_reader([landmask, ocean])
    
    o.set_config('general:coastline_action', 'none')
    
    ''' Seed elements '''   
    o.seed_elements(lon=x, lat=y, time=make_naive(time[0], time[0].tzinfo))
    
    ''' Run '''
    o.run(end_time=ocean.end_time, # Run until the latest available oceanic forecast
          time_step=timedelta(minutes=4),         # Time step
          time_step_output=timedelta(minutes=4), # Output frequency
          outfile=fileOut,           # Output NetCDF file name
          export_variables=['lon', 'lat', 'time']) # Output variables 
                                                   # (just lon, lat and time)
                                                   
    return fileOut

def get_displacements(fout):
    x0, y0 = -10.2122, 51.7431 # longitude and latitude
    with Dataset(fout, 'r') as nc:
        lon = nc.variables['lon'][:]
        lat = nc.variables['lat'][:]
    
    Dx, Dy = [], []
    for x, y in zip(lon, lat):
        dx, dy = sw_dist(y0, y, x0, x)
        Dx.append(dx); Dy.append(dy)
    
    return np.squeeze(np.array(Dx)), np.squeeze(np.array(Dy))

def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)    

def sw_dist(lat1, lat2, lon1, lon2):
    """
        Get distance between points A and B. Coordinates of A (origin) are
  specified by arrays LAT1 (latitude) and LON1 (longitude). Coordinates of 
  B (destino) are specified by arrays LAT2 (latitude) and LON2 (longitude).
  Input arrays must have the same dimensions. Units are in kilometers.
    """
       
    from numpy import cos
        
    """ Set constants """
    DEG2RAD = pi / 180
    DEG2NM  = 60
    NM2KM   = 1.8520    
    """ Get longitude difference """
    dlon = lon2 - lon1
    """ Convert latitude to radians """
    latrad1 = abs(lat1 * DEG2RAD)
    latrad2 = abs(lat2 * DEG2RAD)
    """ Correct longitude according to cosine of latitude """
    dep = cos(.5 * (latrad1 + latrad2)) * dlon
    """ Get latitude difference """
    dlat = lat2 - lat1
    """ Get distance """    
    Dx = NM2KM * DEG2NM * dep
    Dy = NM2KM * DEG2NM * dlat
    """ Return distance """
    return Dx, Dy

def uvcdf(u, v, t, var):
    ''' Create simple NetCDF to extend buoy currents to a wider area used as
        input for the OpenDrift run. This is a preprocessing step before 
        producing the progressive vector diagram. '''
        
    # Convert cm/s to m/s
    u, v = np.array([.01 * i  for i in u]), np.array([.01 * i  for i in v])
        
    # Artificial, extended domain
    x0, x1, y0, y1 = -12, -8, 50, 53
        
    fileOut = os.environ.get('static') + 'uv-' + t[0].strftime('%Y%m%d') + f'-{var}.nc'
    with Dataset(fileOut, 'w', format='NETCDF4') as nc:
        
        # Create NetCDF dimensions
        nc.createDimension('lon', 2)
        nc.createDimension('lat', 2)
        nc.createDimension('time', len(t))
        
        # Longitude
        lon = nc.createVariable('longitude', 'f4', dimensions=('lon'))
        lon.standard_name = 'longitude'; lon.units = 'degree_east'
        lon[:] = np.array([x0, x1]) 
        
        # Latitude
        lat = nc.createVariable('latitude', 'f4', dimensions=('lat'))
        lat.standard_name = 'latitude'; lat.units = 'degree_north'
        lat[:] = np.array([y0, y1])
        
        # Time
        time = nc.createVariable('time', 'f8', dimensions=('time'))
        time.standard_name = 'time'; time.units = 'seconds since 1970-01-01'
        time[:] = np.array([i.timestamp() for i in t])   
        
        # u
        uvar = nc.createVariable('u', 'f4', dimensions=('time', 'lat', 'lon'))
        uvar.standard_name = 'eastward_sea_water_velocity'
        uvar.units = 'm s-1'
                
        # v
        vvar = nc.createVariable('v', 'f4', dimensions=('time', 'lat', 'lon'))
        vvar.standard_name = 'northward_sea_water_velocity'
        vvar.units = 'm s-1'
        
        for i in range(2):
            for j in range(2):
                uvar[:, j, i], vvar[:, j, i] = u, v
        
        return fileOut

def vector_request(DBO, fecha, variable):
    ''' Subset time and u, v components of velocity for the selected date '''
    
    # Get selected date as a timezone-aware datetime
    fecha = timezone('UTC').localize(fecha)
        
    # Find corresponding time index in the Deenish buoy dataset
    index = np.where(fecha == np.array(DBO.buoy['time']))[0][0]
    
    # Get times for the selected date
    t = DBO.buoy['time'][index : index + 145]    
    # Subset u, v components of velocity for the selected date
    if 'Surface' in variable:
        u, v = DBO.buoy['u0'][index : index + 145], DBO.buoy['v0'][index : index + 145]
    elif 'Mid-water' in variable:
        u, v = DBO.buoy['umid'][index : index + 145], DBO.buoy['vmid'][index : index + 145]
    elif 'Seabed' in variable:
        u, v = DBO.buoy['ubot'][index : index + 145], DBO.buoy['vbot'][index : index + 145]
    elif 'Wind' in variable:
        u, v = DBO.buoy['uwind'][index : index + 145], DBO.buoy['vwind'][index : index + 145]
    
    return u, v, t                                                