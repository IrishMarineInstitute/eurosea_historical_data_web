import motuclient
import os

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
         xmin, xmax, ymin, ymax, idate, edate, variable, tipo):
    
    if 'OCEANCOLOUR_ATL_BGC_L4_' in SERVICE:
        
        # Set template
        script_template = ('python -m motuclient '
                           f'--motu https://{tipo}.cmems-du.eu/motu-web/Motu '
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
    
    elif SERVICE == 'NORTHWESTSHELF_ANALYSIS_FORECAST_PHY_004_013-TDS':
        
        # Set template
        script_template = ('python -m motuclient '
                           f'--motu https://{tipo}.cmems-du.eu/motu-web/Motu '
                           f'--service-id {SERVICE} '
                           f'--product-id {PRODUCT} '
                           f'--longitude-min {xmin} --longitude-max {xmax} '
                           f'--latitude-min {ymin} --latitude-max {ymax} '
                           f'--date-min "{idate}" --date-max "{edate}" ' 
                           '--depth-min 0 --depth-max 30 '
                           f'--variable {variable} '
                           '--out-dir <OUTPUT_DIRECTORY> '
                           '--out-name <OUTPUT_FILENAME> '
                           '--user <USERNAME> --pwd <PASSWORD>'
                           )
        
    else:
        
        raise ValueError('Unexpected service has been requested!')

    # Define where data and credentials are stored as an environment variable
    os.environ['DATA'] = 'H:\Diego\EuroSea\DATA'    
    
    # Read credentials from secrets file and save as environment variables
    secrets = os.environ.get('DATA') + '/secrets'
    
    # Read secrets (configuration) file
    with open(secrets, 'r') as f:
        for line in f:
            key, val = line.split()
            # Save as environment variable
            os.environ[key] = val
            
    # Set CMEMS credentials
    USERNAME, PASSWORD = os.environ.get('USERNAME'), os.environ.get('PASSWORD')

    # Prepare request
    data_request = motu_option_parser(script_template, 
        USERNAME, PASSWORD, OUTPUT_DIRECTORY, OUTPUT_FILENAME)
  
    motuclient.motu_api.execute_request(MotuOptions(data_request))      