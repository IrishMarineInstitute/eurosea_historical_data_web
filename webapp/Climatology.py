from datetime import timedelta
from netCDF4 import Dataset
import numpy as np

def climatology(DBO, file, x=None, y=None):
    ''' Read climatology from NetCDF file '''
       
    with Dataset(file, 'r') as nc:
        # Read longitude
        lon = nc.variables['longitude'][:]
        # Read latitude
        lat = nc.variables['latitude'][:]
        # Read time
        time = nc.variables['time'][:]
        # Read seasonal cycle (climatology)
        seas = nc.variables['seas'][:]
        # Read 90-th percentile (MHW threshold)
        pc90 = nc.variables['thresh'][:]
    
    u_time, u_seas, u_pc90 = [], [], []
    
    if ( x ) and ( y ):
    
        i, j = np.argmin(abs(lon - x)), np.argmin(abs(lat - y))
                        
        t0 = DBO.buoy['time'][0] - timedelta(hours=1); H = t0.hour
        while H != 12:
            t0 -= timedelta(hours=1); H = t0.hour
        t1 = DBO.buoy['time'][-1] + timedelta(hours=1); H = t1.hour
        while H != 12:
            t1 += timedelta(hours=1); H = t1.hour
        
    
        for t in [t0] + DBO.buoy['time'] + [t1]:
            if t.hour != 12: continue
            u_time.append(t)
            doy = t.timetuple().tm_yday
            if not t.year % 4:
                if doy > 60:
                    doy -= 1
                elif doy == 60:
                    u_seas.append(.5 * (seas[58, j, i] + seas[59, j, i]))
                    u_pc90.append(.5 * (pc90[58, j, i] + pc90[59, j, i]))
                    continue
            
            w = np.where(time == doy)[0][0]
            
            u_seas.append(seas[w, j, i])
            u_pc90.append(pc90[w, j, i])
        
        u_seas = np.asarray(u_seas)
        u_pc90 = np.asarray(u_pc90)
        
    return lon, lat, time, seas, pc90, u_time, u_seas, u_pc90
        