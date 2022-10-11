from flask import Flask, render_template, request, send_file
from opendrift.readers import reader_netCDF_CF_generic
from opendrift.readers import reader_global_landmask
from opendrift.models.oceandrift import OceanDrift # Import OceanDrift module
from datetime import date, datetime, timedelta
from netCDF4 import Dataset
from CA import oceancolour
from SST import SST_request
from pytz import timezone
import numpy as np
from glob import glob
from PIL import Image
from math import pi
import Plot
import os

static = os.environ.get('static')

units = {'Temperature': '°C', 'Salinity': '', 'pH': '', 'RFU': '', 'Oxygen Saturation': '%'}

def web(DBO):
    # Start application
    app = Flask(__name__)
    
    @app.route('/',  methods=['GET', 'POST'])
    def index():
        # Get list of dates available in the Deenish buoy dataset
        t0, t1 = DBO.buoy['time'][0].date(), DBO.buoy['time'][-1].date()
        times = []
        while t0 < t1:
            times.append(t0)
            t0 += timedelta(days=1)
        times += [t0, '']

        # Get list of layers available in the Northwest Shelf model
        layers = DBO.NWSHELF[0]
        
        variables = ['Temperature', 'Salinity', 'pH', 'Oxygen Saturation', 'RFU', '']
        
        if request.method == 'POST':
            
            if 'Display' in request.form:   
                
                ''' Remove older images '''
                images = glob('static/*.jpg')
                for file in images:
                    os.remove(file) 
                images = []
                           
                images += subs(DBO, request)  
                
                ''' Get user's temperature layer selection '''
                z = request.form.getlist('layers')
                
                '''' Plot temperature profile from MetOffice's Northwest Shelf model '''
                if z: profile = subset_nwshelf(DBO, z); images += profile
                
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
                   
                ''' Reload page with new figures '''                
                return render_template('index.html', times=times, graph=images,
                   time=datestring, layers=layers, variables=variables)                 
                
            elif 'Download' in request.form:
                sub, _, _ = get_requested_data(DBO, request)
                user_variables = request.form.getlist('selection')
                if sub:
                    # Remove old CSV files
                    lista = glob('static/*.csv')
                    for file in lista:
                        os.remove(file)
                    # Generate CSV file
                    f = to_csv(sub, user_variables)                
                    # Download CSV file
                    return send_file(f, as_attachment=True)
                else:
                    return render_template('index.html', times=times, graph=['blank.png'],
                        time0=times[-1], time1=times[-1], time='', 
                        layers=layers, variables=variables) 
         
        else:          
            return render_template('index.html', times=times, graph=['blank.png'],
                arrows='blank.png', time0=times[-1], time1=times[-1], 
                time='', layers=layers, variables=variables) 
        
    
    @app.route('/swirl', methods=['GET', 'POST'])
    def swirl():
        
        # Get list of dates available in the Deenish buoy dataset
        t0, t1 = date(2022, 1, 1), date.today()
        times = []
        while t0 < t1:
            times.append(t0)
            t0 += timedelta(days=1)
        
        if request.method == 'POST':  
            
            fecha = request.form.get('times')
            # Read chlorophyll for chosen date and compute anomaly    
            colour = oceancolour(fecha)
            # Read SST for chosen date and compute anomaly            
            SST = SST_request(DBO, fecha)
            # Plot
            images = glob('static/SWIRL*')
            for file in images:
                os.remove(file)     
            Plot.Plot_Request(colour, SST)
            # Merge figures
            name = merge()    
            # Resize
            #I = Image.open(f'static/{name}').resize((1200, 1200), Image.ANTIALIAS)
            #I.save(f'static/{name}', quality=95)    
            # Reload page with new figure            
            return render_template('swirl.html', times=times, graph=name, 
                time=datetime.strptime(fecha, '%Y-%m-%d').date())        
            
        else:
            return render_template('swirl.html', times=times, graph='blank.png',
                                   time=times[-1])
    
    app.run(debug=False)
    
def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height), color='white')
    dst.paste(im1, (0, 0))
    dst.paste(im2, (int(.5*im1.width-.5*im2.width), im1.height))
    return dst    
    
def subset_nwshelf(DBO, Z):
    ''' Subset data from NORTHWEST SHELF model for given times and depth '''
    
    image = []
    
    depth, time, temp = DBO.NWSHELF
    
    _, t0, t1 = get_requested_data(DBO, request)
        
    if t0 and t1:
        
        # Find time indexes (start and end)
        t0, t1 = np.argmin(abs(t0 - time)), np.argmin(abs(t1 - time))
        # Subset time
        time = time[t0 : t1]
    
        temperature = []
        for z in Z:
            z = int(z)
            # Find depth index
            z = np.argmin(abs(z - depth))
            # Subset time and temperature    
            temperature.append(temp[t0 : t1, z])
           
        
        image += Plot.Plot_NWSHELF_Profile((time, Z, temperature))
        
            
    return image

def get_requested_data(DBO, request):
    
    t0, t1 = request.form.get('times0'), request.form.get('times1')
    
    sub = None
    
    if t0 and t1:
        
        # Make sure input times are within available time list
        t0, t1 = fix_times(DBO, t0, t1)
            
        # Return subset
        sub = subset(DBO.buoy, t0, t1)
        
    return sub, t0, t1

    
def subs(DBO, request):
    ''' Get data buoy subset for the requested time period '''
    
    images = []
        
    ''' Get user's variable selection '''
    user_variables = request.form.getlist('selection')
    
    sub, t0, t1 = get_requested_data(DBO, request)
    
    ''' Get user's YY-Plots selection '''
    A1, A2 = request.form.get('A1'), request.form.get('A2')
    B1, B2 = request.form.get('B1'), request.form.get('B2')
    C1, C2 = request.form.get('C1'), request.form.get('C2')
    YY = {'A1': A1, 'A2': A2, 'B1': B1, 'B2': B2, 'C1': C1, 'C2': C2}
    
    if t0 and t1:
        
        ''' Plot single time series of user's selection '''
        for variable in user_variables:
            name = Plot.Plot_Deenish_user_selection(sub, DBO, variable) 
            images += name
            
                    
        names = Plot.Plot_Deenish_YY(sub, YY)
        
        images += names
        
    return images
    
def fix_times(DBO, t0, t1):
    ''' Make sure that input times are within the available time list '''
    
    # List of available times in the buoy dataset
    time = DBO.buoy['time']
    
    # Convert strings to timezone-aware datetimes
    t0 = timezone('UTC').localize(datetime.strptime(t0, '%Y-%m-%d'))
    t1 = timezone('UTC').localize(datetime.strptime(t1, '%Y-%m-%d'))
    
    # Swap start and end times if needed (t1 must be greater than t0)
    if t0 > t1: t0, t1 = t1, t0
    
    # Start time is the input time at 00:00. Also, make sure is within list.
    t0 = max( t0, min(time) )
    # End time is the input time at 00:00 +1. Also, make sure is within list.
    t1 = min( t1 + timedelta(days=1), max(time) )
    
    return t0, t1


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

def subset(buoy, t0, t1):
    ''' Subset buoy data for the requested time period '''
    
    # List of available times in the buoy dataset
    time = np.array(buoy['time'])
    
    # Find appropriate time indexes
    i0, i1 = np.argmin(abs(time - t0)), np.argmin(abs(time - t1)) + 1
    
    sub = {'time': buoy['time'][i0 : i1]}
    for i in buoy.keys():        
        # Subset each parameter for the requested time period
        sub[i] = buoy[i][i0 : i1]
        
    return sub


def to_csv(sub, user_variables):
    ''' Write data subset into CSV file for download '''
    
    # Set output file name    
    f = 'static/Deenish-' + datetime.now().strftime('%Y%m%d%H%M%S') + '.csv'
    
    # Initialize header
    header = 'Date\t'
    
    with open(f, 'w') as csvfile:  
        # Write header
        for k in sub.keys():
            if k != 'time' and k in user_variables:
                # Append columns to header
                header += ( k + ' ' + units[k] + '\t' )
        # Write header
        csvfile.write(header + '\n')
        for i, time in enumerate(sub['time']):
            l = time.strftime('%d-%b-%Y %H:%M') + '\t'
            for k in sub.keys():
                if k != 'time' and k in user_variables:
                    l += '%.3f\t' % sub[k][i]
                
                    # u, v = sub['u'][i], sub['v'][i]
                    # V = (u**2 + v**2)**.5
                    # D = 90 - atan2(v, u) * 180 / pi
                    # if D < 0: D += 360
                
            csvfile.write(l + '\n')
        
    return f

def merge():
    
    files = glob('static/SWIRL*.jpg')
    
    result = Image.new("RGB", (1600, 2400), color='white')

    for index, file in enumerate(files):
      path = os.path.expanduser(file)
      img = Image.open(path)
      img.thumbnail((700, 700), Image.ANTIALIAS)
      x = index % 2 * 750
      y = index // 2 * 750
      w, h = img.size
      
      result.paste(img, (x, y, x + w, y + h))
      
    name = 'SWIRL.jpg'

    result.save(f'static/{name}')    
    
    return name

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
                                                   
def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)                                                    