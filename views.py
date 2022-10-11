from app import app
from flask import render_template, request, send_file
from datetime import date, datetime, timedelta
from CA import oceancolour
import Deenish
from SST import SST_request
from pytz import timezone
import numpy as np
from glob import glob
from PIL import Image
import Plot
import os
from vectors import arrows

DBO = Deenish.Deenish_Buoy_Observatory()

@app.route('/',  methods=['GET', 'POST'])
def index():
    
    # Get time list to show in drop-down lists
    times = Deenish.get_time_list(DBO)
    
    # Get list of temperature z-layers  
    layers = DBO.NWSHELF[0]
    
    # List of variables in buoy
    variables = ['Temperature', 'Salinity', 'pH', 'Oxygen Saturation', 'RFU', '']
    
    if request.method == 'POST':     
        
        if 'Display' in request.form: # User has requested the 'Display' option
                      
            clean('static')
            
            # List of figures to be displayed
            images = []
                                  
            # Add buoy time-series figures
            images += subs(DBO, request)  
            
            # Get user's temperature layer selection 
            z = request.form.getlist('layers')
            
            # Plot temperature profile from MetOffice's Northwest Shelf model 
            if z: profile = subset_nwshelf(DBO, z); images += profile
            
            # Arrow plots
            images, datestring = arrows(DBO, images, request)
               
            # Reload page with new figures 
            return render_template('index.html', times=times, graph=images,
               time=datestring, layers=layers, variables=variables)                 
            
        elif 'Download' in request.form: # User has requested the 'Download' option
        
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
        # Reload page with new figure            
        return render_template('swirl.html', times=times, graph=name, 
            time=datetime.strptime(fecha, '%Y-%m-%d').date())        
        
    else:
        return render_template('swirl.html', times=times, graph='blank.png',
                               time=times[-1])

def secrets(folder):
    ''' Get app configuration from "secrets" file '''
    config, secrets = {}, folder + '/secrets'    
    with open(secrets, 'r') as f:
        for line in f:
            key, val = line.split()            
            config[key] = val
    
    # Create 'data' folder for data files
    data = folder + '/data/'
    if not os.path.isdir(data):
        os.mkdir(data)
        # If older 'data' exists, clean directory
    else:
        files = glob(data + '*')
        for f in files: 
            os.remove(f)
    config['data'] = data 
    return config

def clean(folder):
     images = glob(f'{folder}/*.jpg')
     for file in images:
         os.remove(file)      
         
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
    
    # Set parameter units
    units = {'Temperature': '°C', 
             'Salinity': '', 
             'pH': '', 
             'RFU': '', 
             'Oxygen Saturation': '%'}
    
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