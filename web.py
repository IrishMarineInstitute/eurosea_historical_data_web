from flask import Flask, render_template, request, send_file
from datetime import date, datetime, timedelta
from nwshelf import NWSHELF_Deenish_profile
from CA import oceancolour
from SST import SST_request
from pytz import timezone
import numpy as np
from glob import glob
from PIL import Image
from math import atan2, pi
import Plot
import os

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
        times.append(t0)            
        
        if request.method == 'POST':
            
            if 'Display' in request.form:                                
                sub, t0, t1 = subs(DBO, request)  
                # Remove older images
                images = glob('static/Deenish*')
                for file in images:
                    os.remove(file) 
                # Date for surface currents information
                datestring = ''
                if request.form.get('times'):
                    datestring = request.form.get('times')
                    # Get date
                    fecha = datetime.strptime(datestring, '%Y-%m-%d')                         
                    # Get currents for the selected date
                    u, v, t = surface_currents_request(DBO, fecha)                      
                    # Plot surface currents
                    arrows = Plot.Plot_Arrows(u, v, t)                                        
                    # Resize
                    A = Image.open(f'static/{arrows}').resize((1520, 1520), Image.ANTIALIAS)
                    A.save(f'static/{arrows}', quality=95)
                else:
                    arrows = 'blank.png'                              
                # Read temperature profile from MetOffice's Northwest Shelf model
                time, temp = NWSHELF_Deenish_profile(t0, t1)                               
                # Plot time series
                name = Plot.Plot_Deenish_user_selection(sub, DBO, time, temp) 
                # Resize
                I = Image.open(f'static/{name}').resize((1520, 2267), Image.ANTIALIAS)
                I.save(f'static/{name}', quality=95)                
                # Reload page with new figure
                return render_template('index.html', times=times, graph=name,
                    arrows=arrows, time0=t0.date(), time1=t1.date()-timedelta(days=1),
                    time=datestring)                 
                
            elif 'Download' in request.form:
                sub, _, _ = subs(DBO, request)
                # Remove old CSV files
                lista = glob('static/*.csv')
                for file in lista:
                    os.remove(file)
                # Generate CSV file
                f = to_csv(sub)                
                # Download CSV file
                return send_file(f, as_attachment=True)
         
        else:
            return render_template('index.html', times=times, graph='blank.png',
                arrows='blank.png', time0=times[0], time1=times[-1], time='') 
        
    
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
    
    
def subs(DBO, request):
    ''' Get data buoy subset for the requested time period '''
    
    # Retrieve request
    t0, t1 = request.form.get('times0'), request.form.get('times1')
    # Make sure input times are withing available time list
    t0, t1 = fix_times(DBO, t0, t1)
    # Return subset
    return subset(DBO.buoy, t0, t1), t0, t1
    
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


def surface_currents_request(DBO, fecha):
    ''' Subset time and u, v components of current velocity for the selected date '''
    
    # Get selected date as a timezone-aware datetime
    fecha = timezone('UTC').localize(fecha)
        
    # Find corresponding time index in the Deenish buoy dataset
    index = np.where(fecha == np.array(DBO.buoy['time']))[0][0]
    
    # Get times for the selected date
    t = DBO.buoy['time'][index : index + 144]    
    # Subset u, v components of velocity for the selected date
    u, v = DBO.buoy['u'][index : index + 144], DBO.buoy['v'][index : index + 144]
    
    return u, v, t

def subset(buoy, t0, t1):
    ''' Subset buoy data for the requested time period '''
    
    # List of available times in the buoy dataset
    time = np.array(buoy['time'])
    
    # Find appropriate time indexes
    i0, i1 = np.argmin(abs(time - t0)), np.argmin(abs(time - t1)) + 1
    
    sub = {}
    for i in buoy.keys():
        # Subset each parameter for the requested time period
        sub[i] = buoy[i][i0 : i1]
        
    return sub


def to_csv(sub):
    ''' Write data subset into CSV file for download '''
    
    # Set output file name    
    f = 'static/Deenish-' + datetime.now().strftime('%Y%m%d%H%M%S') + '.csv'
    
    with open(f, 'w') as csvfile:       
        csvfile.write('Date\tTemperature (°C)\tSalinity\tpH\tRFU\tDissolved Oxygen Saturation (%)\tSpeed (cm/s)\tDirection\n')
        for i, time in enumerate(sub['time']):
            t = time.strftime('%d-%b-%Y %H:%M')
            T = sub['temp'][i]
            S = sub['salt'][i]
            p = sub['pH'][i]
            C = sub['chl'][i]
            O = sub['DOX'][i]
            u, v = sub['u'][i], sub['v'][i]
            V = (u**2 + v**2)**.5
            D = 90 - atan2(v, u) * 180 / pi
            if D < 0: D += 360
            
            try:
                l = '%s\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.1f\t%.03d\n' % (t, T, S, p, C, O, V, D)
            except ValueError:
                l = '%s\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.1f\t%f\n' % (t, T, S, p, C, O, V, D)
            csvfile.write(l)
        
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