from Climatology import climatology
from Deenish import Deenish
from web import web
import warnings
import os

warnings.filterwarnings('ignore')

class Deenish_Buoy_Observatory:
    
    def __init__(self):
        
        self.buoy, self.NWSHELF, self.OCEANCOLOUR = Deenish()   
                   
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