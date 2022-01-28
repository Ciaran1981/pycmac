#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: ciaran robb

Complete Sfm piplines using the micmac lib. 



"""

from os import path, chdir, rename
from pycmac.orientation import feature_match, bundle_adjust, rel_orient, _imresize, _callit
from pycmac.dense_match import malt, tawny, pims, pims2mnt, c3dc, mesh, dense_pcl
from pycmac.mspec import stack_rasters
from shutil import move
from glob2 import glob
from PIL import Image
from joblib import Parallel, delayed

def mspec_sfm(folder, proj="30 +north", utmproj=True, csv=None, sub=None, gpsAcc='1',gcp=None, 
              gcpAcc=["0.03", "1"], sep=",",
              mode='PIMs', submode='Forest', ResolTerrain=None, doFeat=True, doBundle=True, doDense=True, 
              pointmask=True, cleanpoints=True,
              fmethod=None, shpmask=None, subset=None, rep_dsm='0', egal="1", 
              DegRap="0", slantr=False):
    
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
    
    folder: string
           working directory
    proj: string
           a UTM zone eg "30 +north" 
        
    mode: string
             either Malt or PIMs
             
    submode: string
             PIMs submode e.g. Forest, BigMac etc.
             
    csv: string
            path to csv containing image xyz info in the micmac format

    sub: string
            path to csv containing an image subset in the micmac format
            
    ResolTerrain: string
            size of a the side of a pixel in the output dsm in metres
            (only with Malt!)
            
    gpsAcc: string
        an estimate in metres of the onboard GPS accuracy
        
    gcp: string
        whether to process gcps - you MUST have a GCP file in the MM format of
        #F=N X Y Z Ix Iy Iz and MUST be in the working dir (where Ix is uncertainty)   
        
    gcpAcc: list (of strings)
        an estimate of the GCP measurment uncertainty
        [on the ground in metres, in pixels]        
            
    sep: string
            the csv delimiter if used (default ",")    

    doFeat: bool
            if repeating after debug/changes mis out early stages       
    doBundle: bool
            if repeating after debug/changes mis out early stages  
    doDense: bool
            if repeating after debug/changes mis out early stages      
            
    fmethod: bool
            feature search for image pairs strategy eg Line All
            
    shpmask: string
            a shapefile mask to constrain malt-based processing
    
    pointmask: bool
            use the micmac SaisieMasq3D (need QT compiled) to define a mask
            on the sparse cloud to constrain processing - this is VERY useful
            and will save a lot of time

    subset: string
            a csv defining a subset of images to be processed during dense matching                        
    
    rep_dsm: string
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


    
    if doFeat == True:
        folder1 = path.join(folder,'RGB')
        
        inList = glob(path.join(folder1, "*.tif"))
        
        [move(rgb, folder) for rgb in inList]
        

        if fmethod != None:
            feature_match(folder, proj=proj, utmproj=utmproj, csv=csv, ext='tif', 
                          method=fmethod, schnaps=cleanpoints)
        else:    
            feature_match(folder, proj=proj, csv=csv, ext='tif', 
                          schnaps=cleanpoints) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext='tif', proj=proj, utmproj=utmproj, calib=sub, gpsAcc=gpsAcc, 
                      gcp=gcp, gcpAcc=gcpAcc, sep=sep)
    
    
    
    # For the RGB dataset
    if doDense==True:
        
        # first check if the main dir has no tif files in it
        # this would be the case potentially if the other processing options
        # are false or a dense match needs to be redone
        
        if not glob(path.join(folder, "*.tif")):
        
            folder1 = path.join(folder,'RGB')
            
            inList = glob(path.join(folder1, "*.tif"))
            
            [move(rgb, folder) for rgb in inList]
        
        if mode == 'Malt':
            if ResolTerrain != None:
                malt(folder, proj=proj, utmproj=utmproj, ext='tif', mask=shpmask, sub=subset,
                     ResolTerrain=ResolTerrain)
            else:               
                malt(folder, proj=proj, utmproj=utmproj, ext='tif', mask=shpmask, sub=subset)
        if mode == 'PIMs':
            pims(folder, mode=submode, ext='tif')
            pims2mnt(folder, proj=proj, utmproj=utmproj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
        
        tawny(folder, proj=proj, utmproj=utmproj, mode=mode, DegRap=DegRap, Out="RGB.tif")
        if mode == 'Malt':
            dense_pcl(folder, mode="Malt", out="rgb.ply")
        if mode == 'PIMs':
            dense_pcl(folder, mode="PIMs", out="rgb.ply")
        
        
        outList = glob(path.join(folder, "IMG*.tif"))
        
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
            if ResolTerrain != None:
                malt(folder, proj=proj, utmproj=utmproj, DoMEC=rep_dsm, ext='tif', mask=shpmask, sub=subset,
                     ResolTerrain=ResolTerrain)
            else:                
                malt(folder, proj=proj, utmproj=utmproj, DoMEC=rep_dsm, ext='tif', mask=shpmask, sub=subset)
        if mode == 'PIMs':
           # PIMs bloody deletes the previous folders so would have to rename them
           # But generation of merged DSM is rapid so doesn't make much difference
    
            pims2mnt(folder, proj=proj, utmproj=utmproj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
          
        tawny(folder, proj=proj, utmproj=utmproj,  mode=mode, Out="RRENir.tif", DegRap=DegRap, 
              RadiomEgal=egal)
        
        if mode == 'Malt':
            dense_pcl(folder, mode="Malt", out="rrenir.ply")
        if mode == 'PIMs':
            dense_pcl(folder, mode="PIMs", out="rrenir.ply")
        
        rgbIm = path.join(folder, "OUTPUT", "RGB.tif")
        nirIm = path.join(folder, "OUTPUT", "RRENir.tif") 
        stk = path.join(folder, "OUTPUT", "mstack.tif")
        
        stack_rasters(rgbIm, nirIm, stk, slantr=slantr)
        
        outList = glob(path.join(folder, "IMG*.tif"))
        
        # move it all back to keep things tidy
        [move(t, path.join(folder, "RRENir")) for t in outList]
        
    else:
        pass

def rgb_sfm(folder, proj="30 +north", utmproj=True, ext='JPG', csv=None, sub=None, gpsAcc='1',
            gcp=None, gcpAcc=["0.03", "1"], sep=",", 
              mode='PIMs', submode='Forest', ResolTerrain=None, doFeat=True, doBundle=True,
              doDense=True, fmethod=None, useGps=True, pointmask=True, shpmask=None, 
              subset=None, egal=1, resize=None, cleanpoints=True):
    
    """
    A function for the complete structure from motion process using a RGB camera. 
    
    Obviously the Malt and PIMs algorithms will perform better/worse than each other
    on certain datasets. 

            
    Notes
    -----------
    

    This assumes certain parameters, if you want fine-grained control, use the individual commands.
    
    The absolute path needs to be provided for csv's representing image data or calibration subsets
    
        
    Parameters
    -----------
    
    folder: string
           working directory
    proj: string
           a UTM zone eg "30 +north" 
        
    mode: string
             either Malt or PIMs
             
    submode: string
             PIMs submode e.g. Forest, BigMac etc.
             
    csv: string
            path to csv containing image xyz info in the micmac format

    sub: string
            path to csv containing an image subset in the micmac format 
            
    ResolTerrain: string
        size of a the side of a pixel in the output dsm in metres
        (only with Malt!)          
        
    gpsAcc: string
        an estimate in metres of the onboard GPS accuracy
        
    gcp: string
        whether to process gcps - you MUST have a GCP file in the MM format of
        #F=N X Y Z Ix Iy Iz and MUST be in the working dir (where Ix is uncertainty)   
        
    gcpAcc: list (of strings)
        an estimate of the GCP measurment uncertainty
        [on the ground in metres, in pixels]        
            
    sep: string
            the csv delimiter if used (default ",")    

    doFeat: bool
            if repeating after debug/changes mis out early stages
            
    doFeat: bool
            if repeating after debug/changes mis out early stages    
            
    doBundle: bool
            if repeating after debug/changes mis out early stages  
            
    doDense: bool
            if repeating after debug/changes mis out early stages    
            
    shpmask: string
            a shapefile mask to constrain malt-based processing
    
    resize: int
         The long axis in pixels to optionally resize the imagery
            
    pointmask: bool
            use the micmac SaisieMasq3D (need QT compiled) to define a mask
            on the sparse cloud to constrain processing - this is VERY useful
            and will save a lot of time and is recommended over shpmask

    subset: string
            a csv defining a subset of images to be processed during dense matching
            
    cleanpoints: bool
            if true use the schnaps tie point cleaning tool for a evenly distributed
            and reduced tie point set                         
    
    """


    
    if doFeat == True:               
        # features
        # if required here for csv
        if fmethod != None:
            feature_match(folder, proj=proj, utmproj=utmproj, csv=csv, ext=ext, method=fmethod, resize=resize,
                          schnaps=cleanpoints)
        else:    
            feature_match(folder, proj=proj, utmproj=utmproj, csv=csv, ext=ext, resize=resize, schnaps=cleanpoints) 
        
        
    if doBundle == True:
    
        # bundle adjust
        # if required here for calib
        bundle_adjust(folder,  ext=ext, proj=proj, utmproj=utmproj, calib=sub, gpsAcc=gpsAcc, 
                      gcp=gcp, gcpAcc=gcpAcc, sep=sep)
    
    
    
    # For the RGB dataset
    if doDense==True:
        
        if mode == 'Malt':    
            if ResolTerrain != None:
                malt(folder, proj=proj, utmproj=utmproj, ext=ext, mask=shpmask, sub=subset,
                     ResolTerrain=ResolTerrain)
            else:               
                malt(folder, proj=proj, utmproj=utmproj, ext=ext, mask=shpmask, sub=subset)
        if mode == 'PIMs':
            pims(folder, mode=submode, ext=ext, mask=pointmask)
            pims2mnt(folder, proj=proj, utmproj=utmproj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
        if mode == 'C3DC':
            c3dc(folder, mode=submode, ext=ext)                    
            pims2mnt(folder, proj=proj, utmproj=utmproj, mode=submode,  DoOrtho='1',
                 DoMnt='1')
        
        tawny(folder, proj=proj, utmproj=utmproj, mode=mode, Out="RGB.tif", RadiomEgal=egal)
    else:
        pass
    
def rel_model(folder, ext='JPG', method='All', submode='Statue', schnaps=False,
              resize=None, doFeat=True, doBundle=True,
              doDense=True, doMesh=True, lineMax='10'):
    
    """
    A function for producing a point cloud using C3DC without geo-reffing,
    will do exhaustive matching by default. 
            
    Notes
    -----------

    This assumes certain parameters, if want fine-grained control, 
    use the individual commands.

         
    Parameters
    -----------
    
    folder: string
           working directory
           
    ext: string
           image ext
           
    method: string
           feature detection & matching method
           
    submode: string
             the processing mode of C3DC
             
    doFeat: bool
            if repeating after debug/changes mis out early stages 
            
    doBundle: bool
            if repeating after debug/changes mis out early stages  
            
    doDense: bool
            if repeating after debug/changes mis out early stages  
            
    doMesh: bool
            if repeating after debug/changes mis out early stages  
               
    """
    
    
    
    extFin = '.*'+ext
    
    chdir(folder)
    
    if doFeat==True:
        featlog = open(path.join(folder, 'Featlog.txt'), "w")
        
        imList = glob(path.join(folder, "*"+ext))
        img = Image.open(imList[0])
        w, h = img.size
        wprm = str(w / 2)
        
        if resize != None:
            Parallel(n_jobs=-1, verbose=5)(delayed(_imresize)(i, resize) for i in imList)
        
        if method == 'All':
            tapi = ["mm3d", "Tapioca", "All", extFin, wprm.replace(".0", ""), "@SFS"]
        if method == "Line":
            tapi = ["mm3d", "Tapioca", "Line",  extFin, wprm.replace(".0", ""), lineMax, "@SFS"]
        
        _callit(tapi, featlog)
    
        if schnaps == True:
            schnapi = ["mm3d", "Schnaps", extFin, "MoveBadImgs=1"]
            _callit(schnapi, featlog)
            rename(path.join(folder, "Homol"), path.join(folder, "Homol_init"))
            rename(path.join(folder, "Homol_mini"), path.join(folder, "Homol"))
    
    if doBundle==True:
        rel_orient(folder, ext=ext)
    
    if doDense==True:
        c3dc(folder, mode=submode, ext=ext, orientation="Arbitrary")

    if doMesh==True:
        mesh(folder, "Dense.ply", mode=submode, ext=ext, ori="Arbitrary")
        
        mvList = glob(path.join(folder, "Dense*.ply"))
        ootDir = path.join(folder, 'OUTPUT')
        [move(i, ootDir) for i in mvList]
    


