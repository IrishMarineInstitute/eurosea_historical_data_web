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
from PIL import Image, ImageOps
from urllib.request import urlopen, Request
import io

lon, lat = -10.2122, 51.7431

font = {'size' : 12}; matplotlib.rc('font', **font)

units = {'Temperature': '$^\circ$C', 
         'Salinity': '', 
         'pH': '', 
         'RFU': '', 
         'Oxygen Saturation': '%',
         'Chlorophyll-a': '$mg m^{-3}$'}  

names = {'Temperature': 'Temperature', 
         'Salinity': 'Salinity',
         'pH': 'pH',
         'RFU': 'Raw Fluorescence Units',
         'Oxygen Saturation': 'Oxygen saturation',
         'Chlorophyll-a': 'Chlorophyll-a concentration'}


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
    ax.plot(lon, lat, 'w*', ms=6)
    if save:
        plt.savefig(f'{path}/' + filename, dpi=500, bbox_inches='tight')
    plt.close(fig) 
    return ax
        
def Plot_chla(x_chl, y_chl, time_chl, chl, save=True):
    title = 'Satellite Chlorophyll-a ' + datetime(time_chl.year, 
        time_chl.month, time_chl.day).strftime('%d-%b-%Y')       
    ax = plot2d(save, 'SWIRL-CHLA.jpg', x_chl, y_chl, chl, 0, 10, 
            algae, units=r'mg m$^{-3}$', title=title, path='static')  
    return ax    
    
def Plot_chla_anom(x_chl, y_chl, time_chl, anom, save=True):
    title = 'Satellite Chlorophyll-a anomaly ' + datetime(time_chl.year, 
        time_chl.month, time_chl.day).strftime('%d-%b-%Y')       
    plot2d(save, 'SWIRL-CHLAa.jpg', x_chl, y_chl, anom, -2, 2, 
            'bwr', units=r'mg m$^{-3}$', title=title, path='static')      
    
def Plot_SST(sst_x, sst_y, sst_time, sst, save=True):
    title = 'Satellite MUR-SST ' + datetime(sst_time.year, 
        sst_time.month, sst_time.day).strftime('%d-%b-%Y')   
    avg = sst.mean(); v_min, v_max = round(avg - 2), round(avg + 2)    
    ax = plot2d(save, 'SWIRL-SST.jpg', sst_x, sst_y, sst, v_min, v_max, 
            thermal, units='ºC', title=title, path='static')
    return ax
    
def Plot_anom(sst_x, sst_y, sst_time, anom, save=True):
    title = 'Satellite MUR-SST Anomaly ' + datetime(sst_time.year, 
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
                
    
def Plot_Deenish_temperature(ax, seas, pc90, climtime, time, T, l4=None):    
    ''' Plot Deenish Island temperature series highlighting Marine Heat Spikes '''
    
    l1, = ax.plot(time, T, linewidth=1, label='Buoy', color='b')
    ax.set_title('In-Situ Temperature at Deenish Island', fontsize=6)
    ax.set_ylabel('$^\circ$C', fontsize=6)
    ax.grid()
    ax.set_xlim([min(time), max(time)])
    trange = time[-1] - time[0]
    C = [np.datetime64(i) for i in climtime]
    l2, = ax.plot(C, seas, color='C2', linewidth=.5, label='Climatology')
    l3, = ax.plot(C, pc90, color='C3', linewidth=.5, label='90-th pctl')
    y0, y1 = ax.get_ylim()
    ax.fill_between(time, 17, 19, color='y', alpha=.3)
    ax.fill_between(time, 19, 50, color='r', alpha=.3)
    ax.set_ylim([y0, y1])
    if l4:
        ax.legend(handles=[l1, l2, l3, l4], fontsize=4)
    else:
        ax.legend(handles=[l1, l2, l3], fontsize=4)
    fill_mhw(ax, [np.datetime64(i) for i in time], T, C, pc90)
    
    
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

    
def single_time_series_plot(ax, time, var, y, color=None):
    
    trange = time[-1] - time[0]
    
    if color:
        line, = ax.plot(time, y, linewidth=.5, label='Model', color=color)    
    else:
        line, = ax.plot(time, y, linewidth=.5, label='Buoy')    
    ax.set_title(f'In-Situ {names[var]} at Deenish Island', fontsize=6)        
    ax.set_ylabel(units[var], fontsize=6)  
    if var == 'RFU': 
        ax.set_ylim([0, max(y) + .1])   
        
    elif var == 'Oxygen Saturation':
        y0, y1 = ax.get_ylim()
        ax.fill_between(time, 0, 70, color='r', alpha=.3)
        ax.set_ylim([y0, y1])
    elif var == 'Chlorophyll-a':
        y0, y1 = ax.get_ylim()
        ax.fill_between(time, 10, 1000, color='r', alpha=.3)
        ax.set_ylim([y0, y1])
    ax.set_xlim([min(time), max(time)])
    ax.grid()
    
    if trange > timedelta(days=4):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%b"))          
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d %H:%M")) 
    
    ax.tick_params(axis='both', labelsize=6)
    return line
    
def yy_plot(ax, time, var1, var2, y1, y2):
    
    trange = time[-1] - time[0]
    
    ax.plot(time, y1, linewidth=.5, color='C0')    
    ax.grid()    
    ax2 = ax.twinx()
    ax2.plot(time, y2, linewidth=.5, color='C1')
    ax.set_title(f'In-Situ {names[var1]} & {names[var2]} at Deenish Island', fontsize=6)
    ax.set_ylabel(units[var1], fontsize=6, color='C0')
    ax2.set_ylabel(units[var2], fontsize=6, color='C1')
    ax.tick_params(axis='y', color='C0', labelcolor='C0')
    ax2.tick_params(axis='y', color='C1', labelcolor='C1')
    ax.set_xlim([min(time), max(time)])
    if var1 == 'RFU':
        ax.set_ylim([0, max(y1) + .1])
    if var2 == 'RFU':
        ax2.set_ylim([0, max(y2) + .1])       
    
    if trange > timedelta(days=4):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%b"))          
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d %H:%M"))
        
    
    ax.tick_params(axis='both', labelsize=4)
    ax2.tick_params(axis='both', labelsize=4)
    
def Plot_Deenish_user_selection(buoy, DBO, variable):
    ''' Generate Deenish Island Data Portal user's requested image '''
    
    images = []
    
    fig, ax = plt.subplots(1)
   
    
    fig.tight_layout()
    
  
    if variable == 'Temperature':
        
        seas, pc90, climtime = DBO.Deenish_seas, DBO.Deenish_pc90, DBO.Deenish_time
            
        Plot_Deenish_temperature(ax, seas, pc90, climtime, buoy['time'], buoy[variable])
        
    elif variable == 'Chlorophyll-a':
        
        single_time_series_plot(ax, DBO.OCEANCOLOUR[0], variable, DBO.OCEANCOLOUR[1])
                        
    else:
        
        single_time_series_plot(ax, buoy['time'], variable, buoy[variable])
            
    images.append(save_figure(fig, f'Deenish-{variable}'))
    
    return images
       
        
   
        
def Plot_Deenish_YY(buoy, YY):
    
    images = []
    
    for i in 'ABC':
        var1, var2 = YY[i + '1'], YY[ i + '2']
        if var1 and var2:
            fig, ax = plt.subplots(1)
            yy_plot(ax, buoy['time'], var1, var2, buoy[var1], buoy[var2])
            images.append(save_figure(fig, f'Deenish-{var1}-vs-{var2}'))
    
    return images


def save_figure(fig, imagename):
    
    T = datetime.now().strftime('%Y%m%d%H%M%S')
    
    fig.set_size_inches(5.00, 3.75)
    
    plt.savefig(f'static/{imagename}-{T}.jpg', dpi=250, bbox_inches='tight')
    
    plt.close(fig) 
    
    return f'{imagename}-{T}.jpg'

def Plot_NWSHELF_Profile(NWSHELF):
    
   
    
    image = []
    
    fig, ax = plt.subplots(1)
    
    time, Z, temp = NWSHELF
        
    for y in temp:
        single_time_series_plot(ax, time, 'Temperature', y, color='k')
    
    ax.set_title('Temperature profile at Deenish Island from Northwest Shelf Model',
                        fontsize=6)
    label = ''
    for level in Z:
        label += str(level) + ', '
    label = label[0:-2]
    
    ax.set_xlabel('Model predictions at multiple depths, from top to bottom: ' 
                  + label + ' [m]', fontsize=5)
    
    image.append(save_figure(fig, 'Deenish-NWSHELF'))
    
    return image
    
def plot_velocity(ax, t, u, v):
    
    speed = (u**2 + v**2)**.5; f = .03*speed**-1   
    try:
        value = round(speed)
    except ValueError: # NaN
        return
    
    ax.arrow(.5, .5, f*u, f*v, color='tab:gray', 
        head_width=.103, head_length=.05)
    
    ax.add_patch(plt.Circle((.5, .5), .06, color='tab:gray'))
    ax.add_patch(plt.Circle((.5, .5), .04, color='w'))
    if value < 10:
        ax.text(.48, .48, '%d' % value, fontsize=12)
    elif value < 100:
        ax.text(.47, .48, '%d' % value, fontsize=12)
    else:
        ax.text(.46, .48, '%d' % value, fontsize=10)
    # ax.text(.275, .37, t.strftime('%H:%M'), fontsize=12)
    ax.set_xlabel(t.strftime('%H:%M'), fontsize=12)
    
    
def Plot_Arrows(u, v, time):
    image = [] 
    
    fecha = time[0].strftime('%d-%b-%Y')
    fig, axes = plt.subplots(1, 24, figsize=(24, 6))
    
    b = 0.01
    k = 1/25
    
    for j in range(24):
        pos = [k*j+b, .1, .02, .1]
        axes[j].set_position(pos)
   
    c = -1
    
        
    for j in range(24):
        c += 1; ax = axes[j]; #ax.axis('off')    
        
        if c == 11:
            ax.set_title(f'In-Situ Surface currents (cm/s) for {fecha}', fontsize=24)                            
        
        #try:
        plot_velocity(ax, time[6*c], u[6*c], v[6*c])
        ax.axis('equal')
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
        
        ax.spines['bottom'].set_color('#dddddd')
        ax.spines['top'].set_color('#dddddd') 
        ax.spines['right'].set_color('#dddddd')
        ax.spines['left'].set_color('#dddddd')
          
   
  
    plt.savefig('static/Deenish-Arrows.jpg', dpi=500, bbox_inches='tight')
    
    I = Image.open('static/Deenish-Arrows.jpg').resize((1800, 100), Image.ANTIALIAS)
    #I = add_border(I)
    #I.save('static/Deenish-Arrows.jpg', quality=95)   
     
    #image.append('Deenish-Arrows.jpg')
    
    #return image
    return I

def circular_axes(ax, R, s, label):
    
    
   
    f = 2**.5/2
    
    ax.axis('equal')
    ax.set(xlim=(-R, R), ylim=(-R, R))
    
    for i in range(s, R, s):            
        circle = plt.Circle((0, 0), i, color='gray')
        circle.set_fill(False)
        circle.set_linewidth(.5)
    
        ax.add_patch(circle)
        ax.text(i*f, i*f, str(i), fontsize=6)
    
    ax.plot([-R, R], [0, 0], color='gray', linewidth=.5)
    ax.plot([0, 0], [-R, R], color='gray', linewidth=.5)
    
    ax.text(-1.1*R, -.025*R, 'W', fontsize=6)
    ax.text(1.05*R, -.025*R, 'E', fontsize=6)
    ax.text(-.025*R, 1.05*R, 'N', fontsize=6)
    ax.text(-.025*R, -1.1*R, 'S', fontsize=6)
    
    ax.axis('off')
    
    ax.text(-0.85*R, -1.2*R, label, fontsize=6)
    
    return ax

def Plot_Displacements(u, v, Dx, Dy, t):
    image = []
    
    # Get date as string to be shown in x-labels
    fecha = t[0].strftime('%d-%b-%Y')
    
    # Convert times to NumPy datetimes as required by the colorbar
    times = np.array([np.datetime64(i) for i in t])
    # Convert to Matplotlib date numbers    
    c=mdates.date2num(times)
    
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(24, 12))
    # Create circular axes for scatter plot
    circular_axes(axes[0], 55, 10, f'Surface current velocities for {fecha} in cm/s')
    # Create circular axes for vector regression plot
    circular_axes(axes[1], 25, 5, f'Water displacement for {fecha} in km')
    
    # Set color scale with 'viridis' colormap and proper data range
    m = plt.cm.ScalarMappable(cmap='viridis'); m.set_clim(c[0], c[-1])
    
    # Draw scatter plot
    axes[0].scatter(u, v, s=4, c=c)    
    
    cb = plt.colorbar(m, ax=axes[0], fraction=0.046, pad=0.04)
    loc = mdates.AutoDateLocator()
    cb.ax.yaxis.set_major_locator(loc)
    cb.ax.yaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    cb.ax.tick_params(labelsize=4)
    
    cb.ax.yaxis.get_offset_text().set_color('w')
    cb.ax.yaxis.get_offset_text().set_fontsize(0)
    
    # Draw vector regression
    axes[1].plot(Dx, Dy)
    
    axes[0].set_position([0.01, 0.1, 0.4, 0.8])
    
    axes[1].set_position([0.56, 0.1, 0.4, 0.8])
       
    # fig.tight_layout()
    
    #I = Image.frombytes('RGB', fig.canvas.get_width_height(),
    #                    fig.canvas.tostring_rgb())
    name = save_figure(fig, 'Deenish-Displacements')
    #image.append(save_figure(fig, 'Deenish-Displacements'))
    I = Image.open(f'static/{name}')
    #width, height = I.size
    #im = I.crop((0, height/6, width, 6*height/7))
    # im = add_border(I)
    # im.save('static/Deenish-Displacements.jpg', quality=95)  
    #return ['Deenish-Displacements.jpg']
    return I
            
def add_border(im):
    return ImageOps.expand(im, border=(1, 1, 1, 1), fill='black')

   