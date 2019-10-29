#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 12:02:43 2019

@author: ciaran
A template script for upcoming all in one mspec


"""

from os import path

from pycmac.orientation import feature_match, bundle_adjust

from pycmac.dense_match import malt, tawny, feather, pims, pims2mnt

#from pycmac.utilities import mv_subset

from pycmac.mspec import stack_rasters


#import matplotlib.pyplot as plt


from shutil import move

from glob2 import glob




def mspec_sfm(folder, proj="30 +north", csv=None, sub=None, sep=",", mode='PIMs', submode='Forest'):
    
    """
    A function for the complete structure from motion process using the micasense
    red edge camera. 
    
    The RGB imagery is used to generate DSMs, which are in turn used to orthorectify the remaining
    bands (Red edge, Nir)
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    
    This assumes you have already generated a working directory with RGB and RReNir folders
    in it using the pycmac.mspec_proc function
    
    This assumes certain parameters, if want fine-grained control, use the individual commands.
    
    The absolute path needs to be provided for csv's representing image data or calibration subsets
    
    Using Malt doesn't always guarantee perfect aligment
    PIMs Forest may be the best bet with a processing time penalty over Malt
    
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
        
    mode : string
             either Malt or PIMs
             
    submode : string
             PIMs submode e.g. Forest, BigMac etc.
             
    csv : string
            path to csv containing image xyz info in the micmac format

    sub : string
            path to csv containing an image subset in the micmac format

    sep : string
            the csv delimiter if used (default ",")    

    
    """

    # folders
    """
    #RGB
    Here process the RGB which forms the template for the other bands
    """
    # first we move all the RGB into the working directory
    
    
    folder1 = path.join(folder,'RGB')
    
    inList = glob(path.join(folder1, "*.tif"))
    
    [move(rgb, folder) for rgb in inList]
    
    
    # features
    # if required here for csv
    feature_match(folder, csv=csv, ext='tif') 
    
    # bundle adjust
    # if required here for calib
    bundle_adjust(folder,  ext='tif', calib=sub, sep=sep)
    
    
    
    # For the RGB dataset
    
    if mode == 'Malt':    
        malt(folder, ext='tif')
    elif mode == 'PIMs':
        pims(folder, mode=submode, ext='tif')
        pims2mnt(folder, mode=submode,  DoOrtho='1',
             DoMnt='1')
    
    tawny(folder, mode=mode, Out="RGB.tif")
    
    outList = glob(path.join(folder, "*.tif"))
    
    # now we move it all out again - micmac doesn't like it being anywhere 
    # other than the working dir (yes this is an ugly solution)
    [move(t, path.join(folder, "RGB")) for t in outList]
    
    
    # Nir etc
    
    folder2 = path.join(folder,'RReNir')
    
    # get the niretc imagery in the folder
    
    inList = glob(path.join(folder2, "*.tif"))
    
    [move(i, folder) for i in inList]
    
    if mode == 'Malt':    
        malt(folder, DoMEC='0', ext='tif')
    elif mode == 'PIMs':
        pims(folder, mode=submode, ext='tif')
        pims2mnt(folder, mode=submode,  DoOrtho='1',
             DoMnt='0')
      
    tawny(folder,  mode=mode, Out="RReNir.tif")
    
    rgbIm = path.join(folder, "OUTPUT", "RGB.tif")
    nirIm = path.join(folder, "OUTPUT", "RReNir.tif") 
    stk = path.join(folder, "OUTPUT", "mstack.tif")
    
    stack_rasters(rgbIm, nirIm, stk)

def rgb_sfm(folder, proj="30 +north", csv=None, sub=None, sep=",", mode='PIMs', submode='Forest'):
    
    """
    A function for the complete structure from motion process using a 
    RGB or grayscale camera
    
    The RGB imagery is used to generate DSMs an mosaics
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    
    This assumes certain parameters, if want fine-grained control to debug 
    (as acquisitions may throw up issues) use the individual commands.
    
    The absolute path needs to be provided for csv's representing image data or calibration subsets
    
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
        
    mode : string
             either Malt or PIMs
    submode : string
             PIMs submode e.g. Forest, BigMac etc.
                
    csv : string
            path to csv containing image xyz info in the micmac format

    sub : string
            path to csv containing an image subset in the micmac format

    sep : string
            the csv delimiter if used (default ",")    

    
    """

    # folders
    """
    #RGB
    Here process the RGB which forms the template for the other bands
    """
      
    # features
    # if required here for csv
    feature_match(folder, csv=csv, ext='tif') 
    
    # bundle adjust
    # if required here for calib
    bundle_adjust(folder,  ext='tif', calib=sub, sep=sep)
    
    
    
    # For the RGB dataset
    
    if mode == 'Malt':    
        malt(folder, ext='tif')
    elif mode == 'PIMs':
        pims(folder, mode=submode, ext='tif')
        pims2mnt(folder, mode=submode,  DoOrtho='1',
             DoMnt='1')
    
    tawny(folder, mode=mode, Out="RGB.tif")
    







