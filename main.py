from Climatology import climatology
from Deenish import Deenish
from web import web
from glob import glob
import warnings
import os

warnings.filterwarnings('ignore')

class Deenish_Buoy_Observatory:
    
    def __init__(self):
        
        self.buoy, self.NWSHELF = Deenish()   
                   
        ''' Read climatology '''
        self.clim_x, self.clim_y, self.clim_time, self.seas, self.pc90, \
        self.Deenish_time, self.Deenish_seas, self.Deenish_pc90 = \
        climatology(self, os.environ.get('DATA') + '/MUR-Climatology.nc', 
                    float(os.environ.get('lon')), 
                    float(os.environ.get('lat')))          
        
def main():
    
    # Define where data and credentials are stored as an environment variable
    os.environ['DATA'] = 'H:\Diego\EuroSea\DATA'    
    
    # Read credentials from secrets file and save as environment variables
    secrets = os.environ.get('DATA') + '/secrets'
    
    # Create 'static' folder for figures and data files
    static = os.environ['DATA'] + '/static/'
    if not os.path.isdir(static):
        os.mkdir(static)
        # If older 'static' exists, clean directory
    else:
        files = glob(static + '*')
        for f in files: 
            os.remove(f)
    os.environ['static'] = static
    
    # Read secrets (configuration) file
    with open(secrets, 'r') as f:
        for line in f:
            key, val = line.split()
            # Save as environment variable
            os.environ[key] = val
            
    return Deenish_Buoy_Observatory()  
    
        
if __name__ == '__main__':
    
    DBO = main()   
    # Launch webpage
    web(DBO)