import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from cmocean.cm import thermal, algae, amp
from datetime import datetime, timedelta
from geopy.distance import distance
from PIL import Image
from urllib.request import urlopen, Request
import io

font = {'size' : 12}; matplotlib.rc('font', **font)

units = {'temp': '$^\circ$C', 'salt': '', 'pH': '', 'chl': '', 'DOX': '%'}  
names = {'temp': 'Temperature', 
         'salt': 'Salinity',
         'pH': 'pH',
         'chl': 'Reference Fluorescence Units',
         'DOX': 'Oxygen saturation'}


def image_spoof(DBO, tile):
    ''' This function reformats web requests from OSM for cartopy
    Heavily based on code by Joshua Hrisko at:
    https://makersportal.com/blog/2020/4/24/geographic-visualizations-in-python-with-cartopy'''

    url = DBO._image_url(tile)                # get the url of the street map API
    req = Request(url)                         # start request
    req.add_header('User-agent','Anaconda 3')  # add user agent to request
    fh = urlopen(req) 
    im_data = io.BytesIO(fh.read())            # get image
    fh.close()                                 # close url
    img = Image.open(im_data)                  # open image with PIL
    img = img.convert(DBO.desired_tile_form)  # set image format
    return img, DBO.tileextent(tile), 'lower' # reformat for cartopy  


def osm_image(x, y, data=None, vmin=None, vmax=None, 
        cmap=None, cbar=True, units=None, title=None, style='satellite'):
    '''This function makes OpenStreetMap satellite or map image with circle and random points.
    Change np.random.seed() number to produce different (reproducable) random patterns of points.
    Also review 'scale' variable'''
    
    if style=='map': # MAP STYLE
        cimgt.OSM.get_image = image_spoof # reformat web request for street map spoofing
        img = cimgt.OSM() # spoofed, downloaded street map
    elif style =='satellite': # SATELLITE STYLE
        cimgt.QuadtreeTiles.get_image = image_spoof # reformat web request for street map spoofing
        img = cimgt.QuadtreeTiles() # spoofed, downloaded street map
    else:
        print('no valid style')
    
    # Get coordinates of centre
    x0, y0 = x.mean(), y.mean()
    cx = (x.min(), x.min(), x.max(), x.max())
    cy = (y.min(), y.max(), y.max(), y.min())
    radius = sum([distance((y0, x0), (y,x)).m for x, y in zip(cx, cy)])/4

    plt.close('all')
    fig = plt.figure(figsize=(10,10)) # open matplotlib figure
    ax = plt.axes(projection=img.crs, zorder=0) # project using coordinate reference system (CRS) of street map
    
    # Set projection
    data_crs = ccrs.PlateCarree()
    
    # Set map scale
    scale = int(120/np.log(radius)); scale = (scale<20) and scale or 19

    # Add title
    ax.set_title(title)
    
    # Add OSM with zoom specification
    ax.add_image(img, int(scale)) 
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, crs=data_crs, color='k', lw=0.5)
    
    if data is not None:
        
        # Show data as a filled contour plot
        ax.contourf(x, y, data, levels=20, vmin=vmin, vmax=vmax,
            cmap=cmap, transform=ccrs.PlateCarree(), zorder=1)        
        
        if cbar: # For wide-scale maps of SW Ireland, display colorbar
            # Set colormap for colorbar
            m = plt.cm.ScalarMappable(cmap=cmap)
            # Set colorbar range (same as 2-D color plot)
            m.set_clim(vmin, vmax)
            # Set colorbar position (slightly to the right of main axes)
            P = ax.get_position(); P = [P.x1 + .02, P.y0,  .03, P.height] 
            # Add colorbar with given colormap, position and label
            fig.colorbar(m, cax=fig.add_axes(P), label=units)
                
    # Set axes limits    
    ax.set_extent(  [x.min(), x.max(), y.min(), y.max()]  ) 
   
    # Remove tick labels on top and right sides of the map
    gl.top_labels, gl.right_labels = False, False    
    
    if cbar:
        
        # Wide-scale maps of SW Ireland. Enough to show ticks every degree
        gl.xlocator = mticker.FixedLocator(np.arange(-12, -8, 1))
        gl.ylocator = mticker.FixedLocator(np.arange( 50, 53, 1))
        
    else:
        
        # LPTM localized maps around Kenmare Bay. Display ticks every .2 degrees
        gl.xlocator = mticker.FixedLocator(np.arange(-11.6, -8, .2))
        gl.ylocator = mticker.FixedLocator(np.arange(50, 52.8, .2))

    return fig, ax


def plot2d(save, filename, x, y, data, vmin, vmax,
           cmap, units='', title='', path='IMAGES'):
    fig, ax = osm_image(x, y, data=data, vmin=vmin, vmax=vmax, 
        cmap=cmap, units=units, title=title)
    if save:
        plt.savefig(f'{path}/' + filename, dpi=500, bbox_inches='tight')
    plt.close(fig) 
    return ax
        
def Plot_chla(x_chl, y_chl, time_chl, chl, save=True):
    title = 'Chlorophyll-a ' + datetime(time_chl.year, 
        time_chl.month, time_chl.day).strftime('%d-%b-%Y')       
    ax = plot2d(save, 'SWIRL-CHLA.jpg', x_chl, y_chl, chl, 0, 10, 
            algae, units=r'mg m$^{-3}$', title=title, path='static')  
    return ax    
    
def Plot_chla_anom(x_chl, y_chl, time_chl, anom, save=True):
    title = 'Chlorophyll-a anomaly ' + datetime(time_chl.year, 
        time_chl.month, time_chl.day).strftime('%d-%b-%Y')       
    plot2d(save, 'SWIRL-CHLAa.jpg', x_chl, y_chl, anom, -2, 2, 
            'bwr', units=r'mg m$^{-3}$', title=title, path='static')      
    
def Plot_SST(sst_x, sst_y, sst_time, sst, save=True):
    title = 'MUR-SST ' + datetime(sst_time.year, 
        sst_time.month, sst_time.day).strftime('%d-%b-%Y')   
    avg = sst.mean(); v_min, v_max = round(avg - 2), round(avg + 2)    
    ax = plot2d(save, 'SWIRL-SST.jpg', sst_x, sst_y, sst, v_min, v_max, 
            thermal, units='ºC', title=title, path='static')
    return ax
    
def Plot_anom(sst_x, sst_y, sst_time, anom, save=True):
    title = 'MUR-SST Anomaly ' + datetime(sst_time.year, 
        sst_time.month, sst_time.day).strftime('%d-%b-%Y')     
    # Plot anomaly
    ax = plot2d(save, 'SWIRL-SSTa.jpg', sst_x, sst_y, anom, -2, 2, 
            'bwr', units='ºC', title=title, path='static')    
    return ax

def Plot_MHS(sst_x, sst_y, sst_time, MHS, tipo, name, save=True):
    title = f'Marine Heat {tipo} ' + datetime(sst_time.year, 
        sst_time.month, sst_time.day).strftime('%d-%b-%Y')     
    # Plot MHW
    ax = plot2d(save, f'SWIRL-{name}.jpg', sst_x, sst_y, MHS, 0, 3, 
            cmap=amp, units='ºC', title=title, path='static')
    return ax
        
def Plot_Request(colour, temperature):
    ''' SST & Chlorophyll plots from web request '''
   
    lon, lat, time, SST, ANOM, MHS, MHW, MHT = temperature
    # Plot SST (MUR)
    Plot_SST(lon, lat, time, SST)
    # Plot SST anomaly (20-year 2002-2022 reference baseline from MUR)
    Plot_anom(lon, lat, time, ANOM)
    
    # Plot MHS    
    Plot_MHS(lon, lat, MHT, MHS, 'Spikes', 'MHS')
    # Plot MHW
    Plot_MHS(lon, lat, MHT, MHW, 'Waves', 'MHW')
    
    lon, lat, time, CHLA, ANOM = colour    
    # Plot chlorophyll-a concentration
    Plot_chla(lon, lat, time, CHLA)
    # Plot anomaly (determined with the 60-day median method)
    Plot_chla_anom(lon, lat, time, ANOM)
                
    
def Plot_Deenish_temperature(ax, DBO, time, T):    
    ''' Plot Deenish Island temperature series highlighting Marine Heat Spikes '''
    
    l1, = ax.plot(time, T, linewidth=.5, label='Buoy')
    ax.set_title('Temperature at Deenish Island', fontsize=6)
    ax.set_ylabel('$^\circ$C', fontsize=6)
    ax.grid()
    ax.set_xlim([min(time), max(time)])
    trange = time[-1] - time[0]
    C = [np.datetime64(i) for i in DBO.Deenish_time]
    l2, = ax.plot(C, DBO.Deenish_seas, color='C2', linewidth=.5, label='Climatology')
    l3, = ax.plot(C, DBO.Deenish_pc90, color='C3', linewidth=.5, label='90-th pctl')
    y0, y1 = ax.get_ylim()
    ax.fill_between(time, 17, 19, color='y', alpha=.3)
    ax.fill_between(time, 19, 50, color='r', alpha=.3)
    ax.set_ylim([y0, y1])
    ax.legend(handles=[l1, l2, l3], fontsize=4)
    fill_mhw(ax, [np.datetime64(i) for i in time], T, C, DBO.Deenish_pc90)
    
    
    if trange > timedelta(days=4):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%b"))          
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d %H:%M")) 
    
    ax.tick_params(axis='both', labelsize=4)
 
    
def fill_mhw(ax, x1, y1, x2, y2):
    
    x1 = [i.astype('float') for i in x1]
    x2 = [i.astype('float') for i in x2]
    xfill = np.sort(np.concatenate([x1, x2]))
    y1fill = np.interp(xfill, x1, y1)
    y2fill = np.interp(xfill, x2, y2)
    xfill = [datetime.fromtimestamp(i/1000000) for i in xfill]
    # ax.fill_between(xfill, y1fill, y2fill, where=y1fill < y2fill, interpolate=True, color='dodgerblue', alpha=0.2)
    ax.fill_between(xfill, y1fill, y2fill, where=y1fill > y2fill, interpolate=True, color='crimson', alpha=0.9)

    
def single_time_series_plot(ax, time, var, y):
    
    trange = time[-1] - time[0]
    
    l1, = ax.plot(time, y, linewidth=.5, label='Buoy')    
    ax.set_title(f'{names[var]} at Deenish Island', fontsize=6)        
    ax.set_ylabel(units[var], fontsize=6)  
    if var == 'chl': ax.set_ylim([0, max(y) + .1])    
    ax.grid()
    ax.set_xlim([min(time), max(time)])
    
    if trange > timedelta(days=4):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%b"))          
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d %H:%M")) 
    
    ax.tick_params(axis='both', labelsize=4)
    
def yy_plot(ax, time, var1, var2, y1, y2):
    
    trange = time[-1] - time[0]
    
    ax.plot(time, y1, linewidth=.5, color='C0')    
    ax.grid()    
    ax2 = ax.twinx()
    ax2.plot(time, y2, linewidth=.5, color='C1')
    ax.set_title(f'{names[var1]} & {names[var2]} at Deenish Island', fontsize=6)
    ax.set_ylabel(units[var1], fontsize=6, color='C0')
    ax2.set_ylabel(units[var2], fontsize=6, color='C1')
    ax.tick_params(axis='y', color='C0', labelcolor='C0')
    ax2.tick_params(axis='y', color='C1', labelcolor='C1')
    ax.set_xlim([min(time), max(time)])
    if var1 == 'chl':
        ax.set_ylim([0, max(y1) + .1])
    if var2 == 'chl':
        ax2.set_ylim([0, max(y2) + .1])       
    
    if trange > timedelta(days=4):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%b"))          
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d %H:%M"))
        
    
    ax.tick_params(axis='both', labelsize=4)
    ax2.tick_params(axis='both', labelsize=4)
    

def Plot_Deenish_user_selection(buoy, DBO):
    ''' Generate Deenish Island Data Portal user's requested image '''
    
    fig, axes = plt.subplots(4, 2)
    W, H = fig.get_size_inches()
    fig.set_size_inches(W, 2*H); 
    fig.tight_layout()
    
    params = np.array([
        [('chl',),      ('DOX',)],
        [('pH',),       ('salt',)],
        [('temp',),     ('temp', 'DOX')],
        [('temp', 'chl'), ('temp', 'salt')],
        ], dtype=object)
    
    for j in range(2):
        for i in range(4):            
            ax, var = axes[i, j], params[i, j]
            
            if len(var) == 1:    # Single time series plot
            
                if var[0] == 'temp':
                    Plot_Deenish_temperature(ax, DBO, buoy['time'], buoy[var[0]])
                else:                    
                    single_time_series_plot(ax, buoy['time'], var[0], buoy[var[0]])
            
            elif len(var) == 2:  # YY plot
                yy_plot(ax, buoy['time'], var[0], var[1], 
                        buoy[var[0]], buoy[var[1]])
                
    # Save figure
    T = datetime.now().strftime('%Y%m%d%H%M%S')
    imagename = f'Deenish-{T}.jpg'
    plt.savefig('static/' + imagename, dpi=500, bbox_inches='tight')
    # Close figure
    plt.close(fig) 
    
    return imagename