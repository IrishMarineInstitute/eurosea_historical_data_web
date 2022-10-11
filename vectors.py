from datetime import datetime
from pytz import timezone
import numpy as np
from PIL import Image
import Plot

def arrows(DBO, images, request):
    ''' Retrieve date selection for surface currents '''  
    # Date for surface currents information
    datestring = ''
    if request.form.get('times'):
        # Get user's selection of vector variables (winds or currents)
        user_variables = request.form.getlist('vectors')
        # Get date selection as string
        datestring = request.form.get('times')
        # Get date selection as datetime
        fecha = datetime.strptime(datestring, '%Y-%m-%d')   

        for variable in user_variables:         
            var = variable.replace(' ', '-')
            # Get currents for the selected date
            u, v, t = vector_request(DBO, fecha, variable)                  
            # Get displacements around starting position
            Dx, Dy = get_displacements(u, v, t, var)                                          
            # Plot surface currents
            arrows = Plot.Plot_Arrows(u, v, t, variable)                                                           
            # Plot displacements
            circles = Plot.Plot_Displacements(u, v, Dx, Dy, t)
            # Concatenate vertically
            currents = Plot.add_border(get_concat_v(arrows, circles))                    
            # Save figure
            currents.save(f'static/Deenish-{var}.jpg', quality=95)   
            # Add new figure to figure list
            images.append(f'Deenish-{var}.jpg')
            
    return images, datestring

def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height), color='white')
    dst.paste(im1, (0, 0))
    dst.paste(im2, (int(.5*im1.width-.5*im2.width), im1.height))
    return dst    

def get_displacements(U, V, t, var):
    
    # Set factor to convert to kilometers
    f = 1e-3 if 'Wind' in var else 1e-5
        
    t = np.array(t)
    # Get time step
    dt = np.unique(t[1::] - t[0:-1])
    # Make sure time step is constant (TODO)
    if dt.size > 1: raise ValueError('Time step is not constant!')
    # Get time step [s]
    dt = dt[0].total_seconds()
    
    dx, dy, Dx, Dy = 0, 0, [], []
    
    for u, v in zip(U, V):
        dx += u * dt; Dx.append(dx)
        dy += v * dt; Dy.append(dy)
    return f*np.array(Dx), f*np.array(Dy)

def vector_request(DBO, fecha, variable):
    ''' Subset time and u, v components of velocity for the selected date '''
    
    # Get selected date as a timezone-aware datetime
    fecha = timezone('UTC').localize(fecha)
        
    # Find corresponding time index in the Deenish buoy dataset
    index = np.where(fecha == np.array(DBO.buoy['time']))[0][0]
    
    # Get times for the selected date
    t = DBO.buoy['time'][index : index + 145]    
    # Subset u, v components of velocity for the selected date
    if 'Surface' in variable:
        u, v = DBO.buoy['u0'][index : index + 145], DBO.buoy['v0'][index : index + 145]
    elif 'Mid-water' in variable:
        u, v = DBO.buoy['umid'][index : index + 145], DBO.buoy['vmid'][index : index + 145]
    elif 'Seabed' in variable:
        u, v = DBO.buoy['ubot'][index : index + 145], DBO.buoy['vbot'][index : index + 145]
    elif 'Wind' in variable:
        u, v = DBO.buoy['uwind'][index : index + 145], DBO.buoy['vwind'][index : index + 145]
    
    return u, v, t                                                