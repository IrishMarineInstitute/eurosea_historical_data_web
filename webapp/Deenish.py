from datetime import datetime
from dateutil.parser import parse
from paramiko import SSHException
import pickle
import os
import pysftp

def Deenish():
    
    # Puertos del Estado INSTAC SFTP hostname and credentials
    host, user, password = 'enoc.puertos.es', 'marine_instac', 'NwP3MU%oV5Fu'
    
    # Create output directory to download *.xml files
    localpath = os.getcwd() + '/xml'
    if not os.path.isdir(localpath):
        os.mkdir(localpath)
    
    # Retrieve names of *.xml files already downloaded and save to list
    local = update_local_directory(localpath)
   
    # Download files
    try:
        xml_file_download(local, localpath, host, user, password)         
    except SSHException:
        pass
    
    # Update list of names of *.xml files already downloaded
    local = update_local_directory(localpath)
   
    if os.path.isfile('Deenish.pkl'):
        # Load buoy data from older download        
        with open('Deenish.pkl', 'rb') as file:
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
            'time': [], 'temp': [], 'salt': [], 'pH': [], 'chl':  [], 'DOX':  []       
            }           
    
    print('\n')
    for file in local:
        tempo = datetime.strptime(file[0:13], '%Y%m%dT%H%M')
        if not tempo.hour and not tempo.minute:
            print('Deenish Island: Reading ' + tempo.strftime('%d-%b-%Y'))
        read_xml_file(localpath + '/' + file, var)
        
    # Update pickle file
    with open('Deenish.pkl', 'wb') as file:
        pickle.dump(var, file)
        
    return var

def read_xml_file(file, var):
    ''' Read an *.xml file and updates the fields of interest '''
    with open(file, 'r') as f:
        # Discard header
        for i in range(5): f.readline()
        line = f.readline()
        while len(line):
            if '<Time>' in line:
                var['time'].append(find_time(line))
            elif 'Descr="Temperature"' in line:
                var['temp'].append(find_value(f.readline()))
            elif 'Descr="Salinity"' in line:
                var['salt'].append(find_value(f.readline()))
            elif 'Descr="Dissolved Oxygen"' in line:
                var['DOX'].append(sat_to_c(find_value(f.readline())))
            elif 'Descr="pH"' in line:
                var['pH'].append(find_value(f.readline()))
            elif 'Descr="Chlorophyll RFU"' in line:
                var['chl'].append(rfu_to_c(find_value(f.readline())))
            # Read next line
            line = f.readline()
    
            
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
            
def update_local_directory(localpath):
    ''' Get a list with the names of *.xml files already downloaded '''
    local = []
    for file in os.listdir(localpath):
        if file.endswith('.xml'):
            local.append(file)
    return local
         
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
                        sftp.get(file); break
                    except SSHException: continue
                while True:
                    try: 
                        os.rename(file, localpath + '/' + file); break
                    except PermissionError: continue