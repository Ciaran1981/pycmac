#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 12:02:43 2019

@author: ciaran
A template script for upcoming all in one mspec


"""

from os import path

from pycmac.orientation import feature_match, bundle_adjust

from pycmac.dense_match import malt, tawny, pims, pims2mnt

from pycmac.mspec import stack_rasters

from shutil import move

from glob2 import glob


def mspec_sfm(folder, proj="30 +north", csv=None, sub=None, gpsAcc='1', sep=",",
              mode='PIMs', submode='Forest', dist="100", doFeat=True, doBundle=True,
              allIm=False, shpmask=None, subset=None, egal='1'):
    
    """
    A function for the complete structure from motion process using the micasense
    red edge camera. 
    
    The RGB imagery is used to generate DSMs, which are in turn used to orthorectify the remaining
    bands (Red edge, Nir)
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    
    This assumes you have already generated a working directory with RGB and RRENir folders
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
            
    gpsAcc : string
            the estimate of GPS accuracy
    
    dist : string
            the distance from each image centre to consider when feature
            detecting and matching 
            
    sep : string
            the csv delimiter if used (default ",")    

    doFeat : bool
            if repeating after debug/changes mis out early stages
            
    doBundle : bool
            if repeating after debug/changes mis out early stages  
            
    allIm : bool
            Exaustive feature search for image pairs (way slower!)
            
    shpmask : string
            a shapefile mask to constrain malt-based processing  

    subset : string
            a csv defining a subset of images to be processed during dense matching                        
    
    """

    # folders
    """
    #RGB
    Here process the RGB which forms the template for the other bands
    """
    # first we move all the RGB into the working directory
    
    if doFeat == True:
        folder1 = path.join(folder,'RGB')
        
        inList = glob(path.join(folder1, "*.tif"))
        
        [move(rgb, folder) for rgb in inList]
        
        
        # features
        # if required here for csv
        if allIm == True:
            feature_match(folder, csv=csv, ext='tif', allIm=True)
        else:    
            feature_match(folder, csv=csv, ext='tif', dist=dist) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext='tif', calib=sub, gpsAcc=gpsAcc, sep=sep)
    
    
    
    # For the RGB dataset
    
    if mode == 'Malt':    
        malt(folder, ext='tif', mask=shpmask, sub=subset)
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
    
    folder2 = path.join(folder,'RRENir')
    
    # get the niretc imagery in the folder
    # Here we join from the outgoing imagelist as images may have been rejected
    # by schnapps, tapas or manually etc along the way
    
    modList = [path.split(i)[1] for i in outList] 
    
    modList = [m.replace("RGB.tif", 'RRENir.tif') for m in modList]
    
    inList = [path.join(folder2, x) for x in modList]
    
    [move(i, folder) for i in inList]
    
    if mode == 'Malt':    
        malt(folder, DoMEC='0', ext='tif', mask=shpmask, sub=subset)
    elif mode == 'PIMs':
       # PIMs bloody deletes the previous folders so would have to rename them
       # But generation of merged DSM is rapid so doesn't make much difference

        pims2mnt(folder, mode=submode,  DoOrtho='1',
             DoMnt='1')
      
    tawny(folder,  mode=mode, Out="RRENir.tif")
    
    rgbIm = path.join(folder, "OUTPUT", "RGB.tif")
    nirIm = path.join(folder, "OUTPUT", "RRENir.tif") 
    stk = path.join(folder, "OUTPUT", "mstack.tif")
    
    stack_rasters(rgbIm, nirIm, stk)

def rgb_sfm(folder, proj="30 +north", ext='JPG', csv=None, sub=None, gpsAcc='1', sep=",",
              mode='PIMs', submode='Forest', dist="100", doFeat=True, doBundle=True,
              allIm=False, shpmask=None, subset=None):
    
    """
    A function for the complete structure from motion process using a RGB camera. 
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    
    This assumes you have already generated a working directory with RGB and RRENir folders
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
            
    gpsAcc : string
            the estimate of GPS accuracy
    
    dist : string
            the distance from each image centre to consider when feature
            detecting and matching 
            
    sep : string
            the csv delimiter if used (default ",")    

    doFeat : bool
            if repeating after debug/changes mis out early stages
            
    doBundle : bool
            if repeating after debug/changes mis out early stages  
            
    allIm : bool
            Exaustive feature search for image pairs (way slower!)
            
    shpmask : string
            a shapefile mask to constrain malt-based processing  

    subset : string
            a csv defining a subset of images to be processed during dense matching                        
    
    """

    # folders
    """
    #RGB
    Here process the RGB which forms the template for the other bands
    """
    # first we move all the RGB into the working directory
    
    
    if doFeat == True:               
        # features
        # if required here for csv
        if allIm == True:
            feature_match(folder, csv=csv, ext=ext, allIm=True)
        else:    
            feature_match(folder, csv=csv, ext=ext, dist=dist) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext=ext, calib=sub, gpsAcc=gpsAcc, sep=sep)
    
    
    
    # For the RGB dataset
    
    if mode == 'Malt':    
        malt(folder, ext=ext, mask=shpmask, sub=subset)
    elif mode == 'PIMs':
        pims(folder, mode=submode, ext=ext)
        pims2mnt(folder, mode=submode,  DoOrtho='1',
             DoMnt='1')
    
    tawny(folder, mode=mode, Out="RGB.tif")
    
    






