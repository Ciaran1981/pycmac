#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciaran Robb, 2019

A module which calls Micmac image orientation commands  
whilst providing additional file parsing and sorting operations. 

https://github.com/Ciaran1981/Sfm/pycmac/

"""

from subprocess import call
from os import path, chdir, rename
#import gdal
#import imageio
import sys
from glob2 import glob
#import osr
from PIL import Image
from pycmac.utilities import calib_subset, make_sys_utm, make_xml
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

def feature_match(folder, csv=None, proj="30 +north", method='File', resize=None, ext="JPG",
                  delim=" ", schnaps=True,  dist="100"):
    
    """
    
    A function running the feature detection and matching with micmac 
    
    
            
    Notes
    -----------
    
    Underlying cmds include
    
    (Tapioca and Schnapps) 
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
        
    resize : string
             The long axis in pixels to optionally resize the imagery
        
    ext : string
                 image extention e.g JPG, tif

    
       
    """
    
    extFin = '.*'+ext   
    
    chdir(folder)
    
    projF = "+proj=utm +zone="+proj+" +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    make_sys_utm(folder, projF)
    
    
    
    featlog = open(path.join(folder, 'Featlog.txt'), "w")
    
    if csv is None:
                     
        xif = ['mm3d', 'XifGps2Txt', extFin]
        
        _callit(xif, featlog)                            
        
        gpxml = ["mm3d", "XifGps2Xml", extFin, "RAWGNSS"]
        
        _callit(gpxml, featlog)
        
        oriCon= ["mm3d", "OriConvert", "#F=N X Y Z", "GpsCoordinatesFromExif.txt",
                 "RAWGNSS_N","ChSys=DegreeWGS84@RTLFromExif.xml", "MTD1=1",
                 "DN="+dist, "NameCple=FileImagesNeighbour.xml", "CalcV=1"]
            
        
        _callit(oriCon, featlog)
        

    else:
        hd, tl = path.split(csv)
        
        make_xml(csv, folder, sep=delim)
        oriCon= ["mm3d", "OriConvert", "OriTxtInFile", tl, "RAWGNSS_N", "ChSys=DegreeWGS84@SysUTM.xml", "MTD1=1",
                 "NameCple=FileImagesNeighbour.xml", "CalcV=1"]
        _callit(oriCon, featlog)
    
    imList = glob(path.join(folder, "*"+ext))
    

    if resize != None:
        Parallel(n_jobs=-1, verbose=5)(delayed(_imresize)(i, resize) for i in imList)
        wprm = "-1"
    else:
        # Always at least half even for Tapioca if user does not provide resize 
        # as little/no gain from full res        
        img = Image.open(imList[0])
        w, h = img.size
        wprm = str(w / 2)
        del img
    if method == 'All':
        tapi = ["mm3d", "Tapioca", "All", extFin, wprm.replace(".0", ""), "@SFS"]
    if method == "Line":
        tapi = ["mm3d", "Tapioca", "Line", extFin, wprm.replace(".0", ""), "@SFS"]
    if method == 'File':        
        tapi = ["mm3d", "Tapioca", "File", "FileImagesNeighbour.xml", wprm.replace(".0", ""), "@SFS"]

    _callit(tapi)
    
    if schnaps is True:
        schnapi = ["mm3d", "Schnaps", extFin, "MoveBadImgs=1"]
        _callit(schnapi, featlog)
        rename(path.join(folder, "Homol"), path.join(folder, "Homol_init"))
        rename(path.join(folder, "Homol_mini"), path.join(folder, "Homol"))
        
    
     
       

def bundle_adjust(folder, algo="Fraser", proj="30 +north",
                  ext="JPG", calib=None,  gpsAcc='1', sep=",", exif=False,
                  meshlab=False):
    """
    
    A function running the relative orientation/bundle adjustment with micmac 
    
    A calibration subset is optional
            
    Notes
    -----------
    
    Underlying cmds include
    
    (Tapas, centrebascule, Campari, ChgSysCo, OriExport)
    
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
    calib : string
            a calibration subset (optional - otherwise the martini initialisation will be used)
    ext : string
                 image extention e.g JPG, tif
    SH : string
        a reduced set of tie points (output of schnaps command)
                 
    gpsAcc : string
        an estimate in metres of the onboard GPS accuracy
                 
    exif : bool
        if the GPS info is embedded in the image exif check this as True to 
        convert back to geographic coordinates, 
        If previous steps always used a csv for img coords ignore this     
    exif : bool
        if true open the pointcloud with meshlab for visualisation     
    """
#    if SH is None:
#        shFin=""
#    else:
#        shFin = "SH="+SH
#    
    extFin = '.*'+ext  
    
    
    chdir(folder)
    
    if calib != None:
        calib_subset(folder, calib, ext=extFin,  algo="Fraser", delim=sep)
    else:
        marti = ["mm3d", "Martini", extFin]
        _callit(marti)
        
        #['mm3d', 'Tapas', 'Fraser', '.*tif', 'Out=Arbitrary', 'SH=_mini']
        tlog = open(path.join(folder, algo+'log.txt'), "w")
        tapas = ["mm3d",  "Tapas", "Fraser", extFin, "Out=Arbitrary", 
                 "InOri=Martini"]
        _callit(tapas, tlog)
    
        
    basc = ["mm3d", "CenterBascule", extFin, "Arbitrary",  "RAWGNSS_N",
            "Ground_Init_RTL"]
    
    _callit(basc)
    
    glog = open(path.join(folder, algo+'GPSlog.txt'), "w")
    

    
    if exif is True:
        
        campari =["mm3d", "Campari", extFin, "Ground_Init_RTL",
                  "Ground_RTL", "EmGPS=[RAWGNSS_N,"+gpsAcc+"]", "AllFree=1"]
        
        _callit(campari, glog)
    
        sysco = ["mm3d", "ChgSysCo",  extFin, "Ground_RTL",
                 "RTLFromExif.xml@SysUTM.xml", "Ground_UTM"]
        _callit(sysco)
        
        oriex = ["mm3d", "OriExport", "Ori-Ground_UTM/.*xml",
                 "CameraPositionsUTM.txt", "AddF=1"]
        _callit(oriex)
    else:
        campari =["mm3d", "Campari", extFin, "Ground_Init_RTL", "Ground_UTM",
              "EmGPS=[RAWGNSS_N,"+gpsAcc+"]", "AllFree=1"]
        _callit(campari, glog)
    
    aperi = ["mm3d", "AperiCloud", extFin,  "Ground_UTM"]
    
    aplog = open(path.join(folder, 'aperilog.txt'), "w")
    _callit(aperi, aplog)
    
    pntPth = path.join(folder, "AperiCloud_Ground_UTM.ply")
#    pcd = o3d.io.read_point_cloud(pntPth)
#    
#    o3d.visualization.draw_geometries([pcd])
    if meshlab == True:
        call(["meshlab", pntPth])
    

    