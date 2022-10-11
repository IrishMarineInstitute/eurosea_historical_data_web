from datetime import datetime, timedelta
from Climatology import climatology
from dateutil.parser import parse
from paramiko import SSHException
from numpy import nan as NaN
import CMEMS
import numpy as np
import pickle
import os
import pysftp
from math import sin, cos, pi

DEG2RAD = pi/180 # Conversion factor from degrees to radians

class Deenish_Buoy_Observatory:
    
    def __init__(self):
        
        self.buoy, self.NWSHELF = Deenish()   
                   
        ''' Read climatology '''
        self.clim_x, self.clim_y, self.clim_time, self.seas, self.pc90, \
        self.Deenish_time, self.Deenish_seas, self.Deenish_pc90 = \
        climatology(self, os.environ.get('DATA') + '/MUR-Climatology.nc', 
                    float(os.environ.get('lon')), 
                    float(os.environ.get('lat')))  

def Deenish():
    
    # Puertos del Estado INSTAC SFTP hostname and credentials    
    host, user, pswd = os.environ.get('host'), os.environ.get('user'), os.environ.get('pswd')
    
    # Create output directory to download *.xml files
    localpath = os.environ.get('DATA') + '/xml'
    if not os.path.isdir(localpath):
        os.mkdir(localpath)
    
    # Retrieve names of *.xml files already downloaded and save to list
    local = update_local_directory(localpath, '.xml')
   
    # Download files
    try:
        xml_file_download(local, localpath, host, user, pswd)         
    except SSHException:
        pass
    
    # Update list of names of *.xml files already downloaded
    local = update_local_directory(localpath, '.xml')
   
    pickle_file = os.environ.get('DATA') + '/Deenish.pkl'
    if os.path.isfile(pickle_file):
        # Load buoy data from older download        
        with open(pickle_file, 'rb') as file:
            var = pickle.load(file)
        # Get latest time
        latest = var['time'][-1].strftime('%Y%m%dT%H%M')
        # Find index of file matching latest time
        i = -1 # ... in case local directory is empty
        for i, file in enumerate(local):
            if file[0:13] == latest: 
                break
        local = local[i+1:]
    else:       
        # Initialize dictionary of output variables    
        var = {
            'time': [], 'Temperature': [], 'Salinity': [], 'pH': [], 
            'RFU':  [], 'Oxygen Saturation':  [], 
            'u0':    [], 'v0':  [],
            'umid':    [], 'vmid':  [],
            'ubot':    [], 'vbot':  [],
            'uwind':    [], 'vwind':  [],
            }            
        
    for file in local:
        tempo = datetime.strptime(file[0:13], '%Y%m%dT%H%M')
        if not tempo.hour and not tempo.minute:
            print('Deenish Island: Reading ' + tempo.strftime('%d-%b-%Y'))
        read_xml_file(localpath + '/' + file, var)
        
    # Apply a quality control (mask missing data)
    var = quality_control(var)    
        
    # Update pickle file
    with open(pickle_file, 'wb') as file:
        pickle.dump(var, file)
      
    # Download CMEMS data for the buoy period
    NWSHELF = CMEMS.download_nwshelf('NORTHWESTSHELF_ANALYSIS_FORECAST_PHY_004_013-TDS',
             'MetO-NWS-PHY-hi-TEM', var['time'])
    
    # OCEANCOLOUR = CMEMS.download_oceancolour(
    #     ('OCEANCOLOUR_ATL_BGC_L4_MY_009_118-TDS', 'OCEANCOLOUR_ATL_BGC_L4_NRT_009_116-TDS'),        
    #     ('cmems_obs-oc_atl_bgc-plankton_my_l4-gapfree-multi-1km_P1D', 
    #      'cmems_obs-oc_atl_bgc-plankton_nrt_l4-gapfree-multi-1km_P1D'),        
    #     'cmems_obs-oc_atl_bgc-plankton_', var['time'])
        
    return var, NWSHELF # OCEANCOLOUR

def get_time_list(DBO):
    # Get list of dates available in the buoy dataset
    t0, t1 = DBO.buoy['time'][0].date(), DBO.buoy['time'][-1].date()
    times = []
    while t0 < t1:
        times.append(t0)
        t0 += timedelta(days=1)
    times += [t0, '']

def quality_control(var):
    
    # Mask missing data
    for key in var.keys():
        var[key] = [i if i != 68. else NaN for i in var[key]]
        
    # Initialize dictionary of output variables    
    new = {
        'time': [], 'Temperature': [], 'Salinity': [], 'pH': [], 
        'RFU':  [], 'Oxygen Saturation':  [], 
        'u0':    [], 'v0':  [],
        'umid':    [], 'vmid':  [],
        'ubot':    [], 'vbot':  [],
        'uwind':    [], 'vwind':  [],
        }   
    
    time = np.array(var['time'])
    #  Get start and end available dates
    idate, edate = time[0], time[-1]
    while idate <= edate:
        # Make sure all times between idate and edate are in the new dictionary
        new['time'].append(idate)
        try: 
            i = np.where(idate == time)[0][0] # If time exists in dataset...
            for key in new.keys():
                if key != 'time':
                    new[key].append(var[key][i]) # ... append existing data, of course
        except IndexError: # If time does not exist in dataset...
            for key in new.keys():
                if key != 'time':
                    new[key].append(NaN) # ... append NaN
        idate += timedelta(minutes=10)
            
    return new
    

def read_xml_file(file, var):
    ''' Read an *.xml file and updates the fields of interest '''
    
    # SET MID-WATER AND SEABED DCPS CELL INDEXES AS PER "SECRETS" FILE
    MID, BOT = int(os.environ.get('MID')), int(os.environ.get('BOT'))
    
    with open(file, 'r') as f:
        # Discard header
        for i in range(5): f.readline()
        line = f.readline()
        while len(line):
            if '<Time>' in line:
                var['time'].append(find_time(line))
            elif 'Descr="Temperature"' in line:
                var['Temperature'].append(find_value(f.readline()))
            elif 'Descr="Salinity"' in line:
                var['Salinity'].append(find_value(f.readline()))
            elif 'Descr="Dissolved Oxygen"' in line:
                var['Oxygen Saturation'].append(sat_to_c(find_value(f.readline())))
            elif 'Descr="pH"' in line:
                var['pH'].append(find_value(f.readline()))
            elif 'Descr="Chlorophyll RFU"' in line:
                var['RFU'].append(rfu_to_c(find_value(f.readline())))
            elif 'Descr="East"' in line:
                var['u0'].append(find_value(f.readline()))
            elif 'Descr="North"' in line:
                var['v0'].append(find_value(f.readline()))
            elif f'Cell Index="{MID}"' in line:
                u, v = get_cartesian(f)
                var['umid'].append(u); var['vmid'].append(v);
            elif f'Cell Index="{BOT}"' in line:
                u, v = get_cartesian(f)
                var['ubot'].append(u); var['vbot'].append(v);
            elif 'Average Wind Speed' in line:
                wind_speed = find_value(f.readline())
            elif 'Average Wind Direction' in line:
                wind_direction = find_value(f.readline())
                var['uwind'].append(wind_speed * cos ( DEG2RAD * ( 90 - wind_direction ) ))
                var['vwind'].append(wind_speed * sin ( DEG2RAD * ( 90 - wind_direction ) ))
            # Read next line
            line = f.readline()
    
def get_cartesian(f):
    ''' Extract u, v components from .xml file '''    
    C = 0
    while 1:
        line = f.readline()
        if 'Value' in line:
            C += 1
            if C == 3:
                r = find_value(line)
            elif C == 4:
                D = find_value(line); break
        if 'Cell Index' in line:
            raise RuntimeError('Could not find velocity components in .xml file')
            
    if ( r == 68 ) and ( D == 68 ): r, D = NaN, NaN
    u = r * cos ( DEG2RAD * ( 90 - D ) ) # Get u-component
    v = r * sin ( DEG2RAD * ( 90 - D ) ) # Get v-component
    return u, v
        
def find_value(line):
    ''' Get numeric value from line of text '''
    i = line.find('e>') + 2
    e = line.find('</') 
    return float(line[i:e])    

def find_time(line):
    ''' Get time from line of text '''
    i = line.find('e>') + 2
    e = line.find('</') 
    return parse(line[i:e])    

def sat_to_c(sat):
    ''' TODO: Convert Dissolved Oxygen Saturation (%) to
            Dissolved Oxygen Concentration '''
    return sat

def rfu_to_c(rfu):
    ''' TODO: Convert Reference Fluorescence Units to
            actual Chlorophyll-a Concentration '''
    return rfu
            
def update_local_directory(localpath, extension):
    ''' Get a list with the names of *.xml files already downloaded '''
    local = []
    for file in os.listdir(localpath):
        if file.endswith(extension):
            local.append(file)
    return sorted(local)
         
def xml_file_download(local, localpath, host, user, pswd):
    ''' Download *.xml files to local path using SFTP credentials '''
    cnopts = pysftp.CnOpts(); cnopts.hostkeys = None
    # Open SFTP connection and start the download
    with pysftp.Connection(host=host, username=user, password=pswd, cnopts=cnopts) as sftp:
        sftp.cwd('/CMS-INSTAC/DeenishIslandBuoy')
        for file in sftp.listdir():
            if ( file not in local ) and file[-4:] == '.xml':
                print(f'Download Deenish Island {file}'); 
                while True:
                    try: 
                        sftp.get(file, localpath=localpath + '/' + file); break
                    except SSHException: continue