#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 12:02:43 2019

@author: ciaran robb

Complete Sfm piplines using the micmac lib. 



"""

from os import path

from pycmac.orientation import feature_match, bundle_adjust

from pycmac.dense_match import malt, tawny, pims, pims2mnt

from pycmac.mspec import stack_rasters

from shutil import move

from glob2 import glob


def mspec_sfm(folder, proj="30 +north", csv=None, sub=None, gpsAcc='1', sep=",",
              mode='PIMs', submode='Forest',  doFeat=True, doBundle=True, doDense=True, 
              pointmask=True, cleanpoints=True,
              fmethod=None, shpmask=None, subset=None, rep_dsm='0', egal=1, DegRap="0", 
              slantr=False):
    
    """
    A function for the complete structure from motion process using the micasense
    red edge camera or Slant view camera.
    
    The RGB imagery is used to generate DSMs, which are in turn used to orthorectify the remaining
    bands (Red edge, Nir).
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    
    This assumes you have already generated a working directory with RGB and RRENir folders
    in it using the pycmac.mspec_proc function
    
    This assumes certain parameters, if want fine-grained control, use the individual commands.
    
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
            
    gpsAcc : string
            the estimate of GPS accuracy
    
            
    sep : string
            the csv delimiter if used (default ",")    

    doFeat : bool
            if repeating after debug/changes mis out early stages
            
    doBundle : bool
            if repeating after debug/changes mis out early stages  
            
    fmethod : bool
            feature search for image pairs strategy eg Line All
            
    shpmask : string
            a shapefile mask to constrain malt-based processing
    
    pointmask : bool
            use the micmac SaisieMasq3D (need QT compiled) to define a mask
            on the sparse cloud to constrain processing - this is VERY useful
            and will save a lot of time

    subset : string
            a csv defining a subset of images to be processed during dense matching                        
    
    rep_dsm : string
            sometimes it is necessary to redo the DSM (MEC folder) on the second
            3-band composite run due to some sort of bug within MicMac, 
            though most of the time this is not necessary
            def is '0' change to '1' if redoing dsm 
            
    cleanpoints: bool
            if true use the schnaps tie point cleaning tool for a evenly distributed
            
            and reduced tie point set  
    slantr: bool
            if processing slantrange imagery change to true otherwise leave false for micasense           
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
        if fmethod != None:
            feature_match(folder, proj=proj, csv=csv, ext='tif', 
                          method=fmethod, schnaps=cleanpoints)
        else:    
            feature_match(folder, proj=proj, csv=csv, ext='tif', 
                          schnaps=cleanpoints) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext='tif', proj=proj, calib=sub, gpsAcc=gpsAcc, 
                      sep=sep)
    
    
    
    # For the RGB dataset
    if doDense==True:
    
        if mode == 'Malt':    
            malt(folder, proj=proj, ext='tif', mask=shpmask, sub=subset)
        elif mode == 'PIMs':
            pims(folder, mode=submode, ext='tif')
            pims2mnt(folder, proj=proj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
        
        tawny(folder, proj=proj, mode=mode, DegRap=DegRap, Out="RGB.tif")
        
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
    
        
        inList = [path.join(folder2, x) for x in modList]
        
        [move(i, folder) for i in inList]
        
        if mode == 'Malt':    
            malt(folder, proj=proj, DoMEC=rep_dsm, ext='tif', mask=shpmask, sub=subset)
        elif mode == 'PIMs':
           # PIMs bloody deletes the previous folders so would have to rename them
           # But generation of merged DSM is rapid so doesn't make much difference
    
            pims2mnt(folder, proj=proj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
          
        tawny(folder, proj=proj,  mode=mode, Out="RRENir.tif", DegRap=DegRap, 
              RadiomEgal=egal)
        
        rgbIm = path.join(folder, "OUTPUT", "RGB.tif")
        nirIm = path.join(folder, "OUTPUT", "RRENir.tif") 
        stk = path.join(folder, "OUTPUT", "mstack.tif")
        
        stack_rasters(rgbIm, nirIm, stk, slantr=slantr)
    else:
        pass

def rgb_sfm(folder, proj="30 +north", ext='JPG', csv=None, sub=None, gpsAcc='1', sep=",",
              mode='PIMs', submode='Forest', doFeat=True, doBundle=True,
              doDense=True, fmethod=None, useGps=True, pointmask=True, shpmask=None, 
              subset=None, egal=1, resize=None, cleanpoints=True):
    
    """
    A function for the complete structure from motion process using a RGB camera. 
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    

    This assumes certain parameters, if want fine-grained control, use the individual commands.
    
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
            
    gpsAcc : string
            the estimate of GPS accuracy

            
    sep : string
            the csv delimiter if used (default ",")    

    doFeat : bool
            if repeating after debug/changes mis out early stages
            
    doBundle : bool
            if repeating after debug/changes mis out early stages  
            
    fmethod : bool
            select a feature detection strategy eg Line All etc
            
    shpmask : string
            a shapefile mask to constrain malt-based processing
            
    pointmask : bool
            use the micmac SaisieMasq3D (need QT compiled) to define a mask
            on the sparse cloud to constrain processing - this is VERY useful
            and will save a lot of time and is recommended over shpmask

    subset : string
            a csv defining a subset of images to be processed during dense matching
            
    cleanpoints: bool
            if true use the schnaps tie point cleaning tool for a evenly distributed
            and reduced tie point set                         
    
    """

    # folders
    """
    #RGB
    Here process the RGB which forms the template for the other bands
    """

    
    if doFeat == True:               
        # features
        # if required here for csv
        if fmethod != None:
            feature_match(folder, csv=csv, ext=ext, method=fmethod, resize=resize,
                          schnaps=cleanpoints)
        else:    
            feature_match(folder, csv=csv, ext=ext, resize=resize, schnaps=cleanpoints) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext=ext, calib=sub, gpsAcc=gpsAcc, sep=sep, 
                      useGps=useGps)
    
    
    
    # For the RGB dataset
    if doDense==True:
        
        if mode == 'Malt':    
            malt(folder, proj=proj, ext=ext, mask=shpmask, sub=subset)
        elif mode == 'PIMs':
            pims(folder, mode=submode, ext=ext, mask=pointmask)
            pims2mnt(folder, proj=proj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
        
        tawny(folder, proj=proj, mode=mode, Out="RGB.tif", RadiomEgal=egal)
    else:
        pass
    
    






