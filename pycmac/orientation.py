#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciaran Robb

A module which calls Micmac image orientation commands  
whilst providing additional file parsing and sorting operations. 


"""

from subprocess import call
from os import path, chdir, rename
#import gdal
#import imageio
import sys
from glob2 import glob
#import osr
from PIL import Image
from pycmac.utilities import calib_subset, make_sys_utm, make_xml, make_csv
from joblib import Parallel, delayed
#import open3d as o3d



def _imresize(image, width):
    
    img = Image.open(image)
    wpercent = (width / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    
    exif = img.info['exif']
    
    img2 = img.resize((width, hsize), Image.ANTIALIAS)
    
    img2.save(image, exif=exif)

def _callit(cmd, log=None):
    ret = call(cmd, stdout=log)
    
    if ret !=0:
            print('A micmac error has occured - check the log file')
            sys.exit()

def feature_match(folder, csv=None, proj="30 +north", utmproj=True,
                  method='File', resize=None, ext="JPG",
                  delim=" ", schnaps=True, dist=None, lineMax='10'):
    
    """
    
    A function running the feature detection and matching with micmac 
            
    Notes
    -----------
    
    Underlying cmds include
    
    (Tapioca and Schnapps) 
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a UTM zone eg "30 +north" 
           
    csv: string
           a path to the csv of GPS coords
        
    resize: int
             The long axis in pixels to optionally resize the imagery
        
    ext: string
                 image extention e.g JPG, tif
                 
    dist: string
        distance for nearest neighbour search
        
    lineMax:
        if method='Line', the max adjacent images in the line to search
       
    """
    
    extFin = '.*'+ext   
    
    chdir(folder)
    
    if utmproj == True:
        projF = "+proj=utm +zone="+proj+" +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    else:
        projF = proj
    make_sys_utm(folder, projF)
    
    
    
    featlog = open(path.join(folder, 'Featlog.txt'), "w")
    
    if csv == None:
        
        # Now using csv as continual reprojection problems with MM's native method
        
        make_csv(folder, ext)
        csv = path.join(folder, "log.csv")                  
    
    hd, tl = path.split(csv)
    
    make_xml(csv, folder, sep=delim)
    oriCon= ["mm3d", "OriConvert", "OriTxtInFile", tl, "RAWGNSS_N", 
             "ChSys=DegreeWGS84@SysUTM.xml", "MTD1=1",
             "NameCple=FileImagesNeighbour.xml", "CalcV=1"]
    if dist != None:
        oriCon.append("DN="+dist)
        
    _callit(oriCon, featlog)
    
    imList = glob(path.join(folder, "*"+ext))
    

    if resize != None:
        Parallel(n_jobs=-1, verbose=5)(delayed(_imresize)(i, resize) for i in imList)
#        wprm = "-1"
    #else:
        # Always at least half even for Tapioca if user does not provide resize 
        # as little/no gain from full res        
    img = Image.open(imList[0])
    w, h = img.size
    wprm = str(w / 2)
    del img
    if method == 'All':
        tapi = ["mm3d", "Tapioca", "All", extFin, wprm.replace(".0", ""), "@SFS"]
    if method == "Line":
        tapi = ["mm3d", "Tapioca", "Line",  extFin, wprm.replace(".0", ""), lineMax, "@SFS"]
    if method == 'File':        
        tapi = ["mm3d", "Tapioca", "File", "FileImagesNeighbour.xml", wprm.replace(".0", ""), "@SFS"]

    _callit(tapi)
    
    if schnaps == True:
        schnapi = ["mm3d", "Schnaps", extFin, "MoveBadImgs=1"]
        _callit(schnapi, featlog)
        rename(path.join(folder, "Homol"), path.join(folder, "Homol_init"))
        rename(path.join(folder, "Homol_mini"), path.join(folder, "Homol"))
        
    
     
       

def bundle_adjust(folder, algo="Fraser", proj="30 +north", utmproj=True,
                  ext="JPG", calib=None,  gpsAcc='1', sep=",", gcp=None,
                  gcpAcc=["0.03", "1"], useGps=True):
    """
    
    A function running the relative orientation/bundle adjustment with micmac 
    
    A calibration subset is optional

            
    Notes
    -----------
    
    Underlying cmds include
    
    (Tapas, centrebascule, Campari, ChgSysCo, OriExport)
    
    Pleae note, that if GCPs are used, then the on-board GPS will not be 
    included in the final bundle adjustment as the on-board will not have 
    positive effect on the overall result. This assumes your GCPs come from a 
    DGPS, otherwise don't use them!
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a UTM zone eg "30 +north" 
           
    calib: string
            a calibration subset (optional - otherwise the martini initialisation will be used)
            
    ext: string
                 image extention e.g JPG, tif
                 
    gpsAcc: string
        an estimate in metres of the onboard GPS accuracy
        
    gcp: string
        whether to process gcps - you MUST have a GCP file in the MM format of
        #F=N X Y Z Ix Iy Iz and MUST be in the working dir (where Ix is uncertainty)   
        
    gcpAcc: list (of strings)
        an estimate of the GCP measurment uncertainty
        [on the ground in metres, in pixels]   
        
    exif: bool
        if the GPS info is embedded in the image exif check this as True to 
        convert back to geographic coordinates, 
        If previous steps always used a csv for img coords ignore this   
        
    useGps : bool
        if the GPS info is untrustyworthy with a lot of the data (eg Dji Phantom - z)
        simply transform from rel to ref coordinate sys without GPS aided bundle adjust.
        
    relOnly : Bool
        use only the realtive orientation - no geo coordinate system at all
  
    """

    extFin = '.*'+ext  
    
    
    chdir(folder)
    
    if calib != None:
        calib_subset(folder, calib, ext=extFin,  algo="Fraser", delim=sep)
    else:
        marti = ["mm3d", "Martini", extFin]
        _callit(marti)
        

        tlog = open(path.join(folder, algo+'log.txt'), "w")
        tapas = ["mm3d",  "Tapas", "Fraser", extFin, "Out=Arbitrary", 
                 "InOri=Martini"]
        _callit(tapas, tlog)
    
        
    basc = ["mm3d", "CenterBascule", extFin, "Arbitrary",  "RAWGNSS_N",
            "Ground_Init_RTL"]
    
    _callit(basc)
    
    glog = open(path.join(folder, algo+'GPSlog.txt'), "w")
  
    if useGps is False:
        sysco = ["mm3d", "ChgSysCo",  extFin, "Arbitrary",
                 "SysCoRTL.xml@SysUTM.xml", "Ground_UTM"]
        _callit(sysco)
    else:
        if gcp != None:
            # My goodness this is bad.....
            gcpcnv = ["mm3d", "GCPConvert", "AppInFile", gcp]
            _callit(gcpcnv)
            
            gcpent = ["mm3d", "SaisieAppuisPredicQT", extFin, "Ground_Init_RTL",
              gcp[:-3]+'xml', "MeasureFinal.xml"]
            _callit(gcpent)
            
            gcpbsc = ["mm3d", "GCPBascule", extFin, "Ground_Init_RTL", "Ground_GCP",
             gcp[:-3]+'xml',  "MeasureFinal-S2D.xml"]
            _callit(gcpbsc)
            
            #yuck
            gcpDiag = "GCP=["+gcp[:-3]+'xml,'+gcpAcc[0]+",MeasureFinal-S2D.xml,"+gcpAcc[1]+"]"
            
            campari =["mm3d", "Campari", extFin, "Ground_GCP", "Ground_UTM",
              gcpDiag ,"AllFree=1"]
            _callit(campari, glog)
        else:
            campari =["mm3d", "Campari", extFin, "Ground_Init_RTL", "Ground_UTM",
              "EmGPS=[RAWGNSS_N,"+gpsAcc+"]", "AllFree=1"]
            _callit(campari, glog)
            
        
    
    aperi = ["mm3d", "AperiCloud", extFin,  "Ground_UTM", "ProfCam=1"]
    
    aplog = open(path.join(folder, 'aperilog.txt'), "w")
    _callit(aperi, aplog)
    
    pntPth = path.join(folder, "AperiCloud_Ground_UTM.ply")
#    pcd = o3d.io.read_point_cloud(pntPth)
#    
#    o3d.visualization.draw_geometries([pcd])
#    if meshlab == True:
#        call(["meshlab", pntPth])



def rel_orient(folder, algo="Fraser", proj="30 +north", martini=False, 
                  ext="JPG", calib=None, sep=",", 
                  meshlab=False, useGps=False):
    """
    
    A function running the relative orientation with micmac 
    
    A calibration subset is optional
            
    Notes
    -----------
    
    Underlying cmds include
    
    (Tapas, centrebascule)
    
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a UTM zone eg "30 +north" 
           
    calib: string
            a calibration subset (optional - otherwise the martini initialisation will be used)
            
    ext: string
                 image extention e.g JPG, tif
  
    """

    extFin = '.*'+ext  
    
    
    chdir(folder)
    
    tlog = open(path.join(folder, algo+'log.txt'), "w")
    
    if calib != None:
        calib_subset(folder, calib, ext=extFin,  algo="Fraser", delim=sep)
    else:
        if martini == True:
            marti = ["mm3d", "Martini", extFin]
            _callit(marti)
        
            
            tapas = ["mm3d",  "Tapas", "Fraser", extFin, "Out=Arbitrary", 
                     "InOri=Martini"]
        else:
            tapas = ["mm3d",  "Tapas", "Fraser", extFin, "Out=Arbitrary"]
        _callit(tapas, tlog)
    
    aperi = ["mm3d", "AperiCloud", extFin,  "Arbitrary", "ProfCam=1"]
    
    aplog = open(path.join(folder, 'aperilog.txt'), "w")
    _callit(aperi, aplog)
    
    
    if useGps !=False:     
        basc = ["mm3d", "CenterBascule", extFin, "Arbitrary",  "RAWGNSS_N",
                "Ground_UTM"]
        
        _callit(basc)
        
        aperi2 = ["mm3d", "AperiCloud", extFin,  "Ground_UTM", "ProfCam=1"]
        _callit(aperi2, aplog)

def gps_orient(folder, algo="Fraser", proj="30 +north", utmproj=True,
                  ext="JPG", gpsAcc='1',  gcp=None,
                  gcpAcc=["0.03", "1"]):
    """
    
    A function running the gps bundle adjustment with micmac with or without 
    GCPs 
    
            
    Notes
    -----------
    
    Underlying cmds include
    
    (CenterBascule, Campari, AperiCloud)
    
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a UTM zone eg "30 +north" 
           
    ext: string
                 image extention e.g JPG, tif
                 
    gpsAcc: string
        an estimate in metres of the onboard GPS uncertainty

    gcp: string
        whether to process gcps - you MUST have a GCP file in the MM format of
        #F=N X Y Z Ix Iy Iz (minimum #F=N X Y Z)
        and MUST be in the working dir (where Ix is uncertainty)   
        
    gcpAcc: list (of strings)
        an estimate of the GCP measurment accuarcy
        [on the ground in metres, in pixels]  
                 
    """

    extFin = '.*'+ext  
    
    glog = open(path.join(folder, algo+'GPSlog.txt'), "w")
    
    chdir(folder)
    
#    basc = ["mm3d", "CenterBascule", extFin, "Arbitrary",  "RAWGNSS_N",
#            "Ground_Init_RTL"]
#    
#    _callit(basc)
    
    if gcp != None:
            # My goodness this is bad.....
            gcpcnv = ["mm3d", "GCPConvert", "AppInFile", gcp]
            _callit(gcpcnv)
            
            gcpent = ["mm3d", "SaisieAppuisPredicQT", extFin, "Ground_Init_RTL",
              gcp[:-3]+'xml', "MeasureFinal.xml"]
            _callit(gcpent)
            
            gcpbsc = ["mm3d", "GCPBascule", extFin, "Ground_Init_RTL", "Ground_GCP",
             gcp[:-3]+'xml',  "MeasureFinal-S2D.xml"]
            _callit(gcpbsc)
            
            #yuck
            gcpDiag = "GCP=["+gcp[:-3]+'xml,'+gcpAcc[0]+",MeasureFinal-S2D.xml,"+gcpAcc[1]+"]"
            
            campari =["mm3d", "Campari", extFin, "Ground_GCP", "Ground_UTM",
              gcpDiag ,"AllFree=1"]
            _callit(campari, glog)
    else:
        
        campari =["mm3d", "Campari", extFin, "Ground_Init_RTL", "Ground_UTM",
              "EmGPS=[RAWGNSS_N,"+gpsAcc+"]", "AllFree=1"]
        _callit(campari, glog)

    aperi = ["mm3d", "AperiCloud", extFin,  "Ground_UTM"]
    
    aplog = open(path.join(folder, 'aperilog.txt'), "w")
    _callit(aperi, aplog)
    

#### Here in case ever reinstated##############################################
#        xif = ['mm3d', 'XifGps2Txt', extFin]
#        
#        _callit(xif, featlog)                            
#        
#        gpxml = ["mm3d", "XifGps2Xml", extFin, "RAWGNSS"]
#        
#        _callit(gpxml, featlog)
#        
#        oriCon= ["mm3d", "OriConvert", "#F=N X Y Z", "GpsCoordinatesFromExif.txt",
#                 "RAWGNSS_N","ChSys=DegreeWGS84@RTLFromExif.xml", "MTD1=1",
#                 "NameCple=FileImagesNeighbour.xml", "CalcV=1"]
#        _callit(oriCon, featlog)   
        
###############################################################################        
#    Canned for same reason as feat
#    if exif is True:
#        
#        #TODO - CONSIDER using utilities.make_csv to avoid continual problems
#        # with exif coord transforms
#        
#        if useGps is False:
#            sysco = ["mm3d", "ChgSysCo",  extFin, "Arbitrary",
#                     "RTLFromExif.xml@SysUTM.xml", "Ground_UTM"]
#            _callit(sysco)
#        else:
#        
#            campari =["mm3d", "Campari", extFin, "Ground_Init_RTL",
#                      "Ground_RTL", "EmGPS=[RAWGNSS_N,"+gpsAcc+"]", "AllFree=1"]
#            
#            _callit(campari, glog)
#        
#            sysco = ["mm3d", "ChgSysCo",  extFin, "Ground_RTL",
#                     "RTLFromExif.xml@SysUTM.xml", "Ground_UTM"]
#            _callit(sysco)
#            
#            oriex = ["mm3d", "OriExport", "Ori-Ground_UTM/.*xml",
#                     "CameraPositionsUTM.txt", "AddF=1"]
#            _callit(oriex)
#    else: