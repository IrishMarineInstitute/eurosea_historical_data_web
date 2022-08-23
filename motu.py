import motuclient
import os

# Set CMEMS credentials
USERNAME, PASSWORD = 'dpereiro1', 'Marciano7!'

class MotuOptions:
    def __init__(self, attrs: dict):
        super(MotuOptions, self).__setattr__("attrs", attrs)

    def __setattr__(self, k, v):
        self.attrs[k] = v

    def __getattr__(self, k):
        try:
            return self.attrs[k]
        except KeyError:
            return None
        
#! /usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Copernicus Marine User Support Team"
__copyright__ = "(C) 2021 E.U. Copernicus Marine Service Information"
__credits__ = ["E.U. Copernicus Marine Service Information"]
__license__ = "MIT License - You must cite this source"
__version__ = "202105"
__maintainer__ = "D. Bazin, E. DiMedio, J. Cedillovalcarce, C. Giordan"
__email__ = "servicedesk dot cmems at mercator hyphen ocean dot eu"

def motu_option_parser(script_template, usr, pwd, output_directory, output_filename):
    dictionary = dict(
        [e.strip().partition(" ")[::2] for e in script_template.split('--')])
    dictionary['variable'] = [value for (var, value) in [e.strip().partition(" ")[::2] for e in script_template.split('--')] if var == 'variable']  # pylint: disable=line-too-long
    for k, v in list(dictionary.items()):
        if v == '<OUTPUT_DIRECTORY>':
            dictionary[k] = output_directory
        if v == '<OUTPUT_FILENAME>':
            dictionary[k] = output_filename
        if v == '<USERNAME>':
            dictionary[k] = usr
        if v == '<PASSWORD>':
            dictionary[k] = pwd
        if k in ['longitude-min', 'longitude-max', 'latitude-min', 
                 'latitude-max', 'depth-min', 'depth-max']:
            dictionary[k] = float(v)
        if k in ['date-min', 'date-max']:
            dictionary[k] = v[1:-1]
        dictionary[k.replace('-','_')] = dictionary.pop(k)
    dictionary.pop('python')
    dictionary['auth_mode'] = 'cas'
    return dictionary

def motu(SERVICE, PRODUCT, OUTPUT_DIRECTORY, OUTPUT_FILENAME, 
         xmin, xmax, ymin, ymax, idate, edate, variable):
    
    # Set template
    script_template = ('python -m motuclient '
                       '--motu https://my.cmems-du.eu/motu-web/Motu '
                       f'--service-id {SERVICE} '
                       f'--product-id {PRODUCT} '
                       f'--longitude-min {xmin} --longitude-max {xmax} '
                       f'--latitude-min {ymin} --latitude-max {ymax} '
                       f'--date-min "{idate}" --date-max "{edate}" ' 
                       f'--variable {variable} '
                       '--out-dir <OUTPUT_DIRECTORY> '
                       '--out-name <OUTPUT_FILENAME> '
                       '--user <USERNAME> --pwd <PASSWORD>'
                       )

    # Prepare request
    data_request = motu_option_parser(script_template, 
        USERNAME, PASSWORD, OUTPUT_DIRECTORY, OUTPUT_FILENAME)
    
    while 1:         
        motuclient.motu_api.execute_request(MotuOptions(data_request))    
        # Check that file exists
        if not os.path.exists(OUTPUT_DIRECTORY + '/' + OUTPUT_FILENAME):
            continue # try again...
        else:
            break