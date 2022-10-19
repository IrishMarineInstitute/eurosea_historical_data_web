from Climatology import climatology
from Deenish import Deenish
from web import web
import warnings

warnings.filterwarnings('ignore')

class Deenish_Buoy_Observatory:
    
    def __init__(self):
        
        self.buoy = Deenish()     
      
        ''' Read climatology '''
        self.clim_x, self.clim_y, self.clim_time, self.seas, self.pc90, \
        self.Deenish_time, self.Deenish_seas, self.Deenish_pc90 = \
        climatology(self, 'Climatology/MUR-Climatology.nc', -10.2122, 51.7431)
          
        
def main():
    
    return Deenish_Buoy_Observatory()  
    
        
if __name__ == '__main__':
    
    DBO = main()
    # Launch webpage
    web(DBO)