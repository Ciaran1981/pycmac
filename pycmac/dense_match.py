#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciaran Robb

A module which calls Micmac dense matching commands and mosaicking operations, 
whilst a providing dditional file parsing, sorting, image masking and multi-band 
functionallity.



"""


from subprocess import call, Popen
from os import path, chdir, mkdir, remove, system
import gdal
import re
import sys
import ogr
from glob2 import glob
import osr
from pycmac.utilities import mask_raster_multi, pims_mask
from pycmac.gdal_edit import gdal_edit
from pycmac.gdal_merge import _merge
from shutil import rmtree, copytree, copy2, copy, move
from joblib import Parallel, delayed
#import pandas as pd
from pycmac.tile import  run
from tqdm import tqdm
from PIL import Image

def malt(folder, proj="30 +north", mode='Ortho', ext="JPG", orientation="Ground_UTM",
         DoOrtho='1', DoMEC='1', DefCor='0', sub=None, delim=",", 
         ResolTerrain=None,
         BoxTerrain=None, mask=None, **kwargs):
    
    """
    
    A function calling the Malt command for use in python.
    
    Upon successful completion, this will return the directory OUTPUT with DSM, ortho (if desried)
    and correlation image
            
    Notes
    -----------
    
    see MicMac tools link for further possible kwargs - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
    e.g = UseGpu='1'
    
        
    Parameters
    -----------
    
    folder: string
           working directory
    proj: string
           a UTM zone eg "30 +north" 
        
    mode: string
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext: string
                 image extention e.g JPG, tif
    
    orientation: string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    sub: string
            path to csv containing an image subset
    
    BoxTerrain: list
            The bottom left and top right coordinates of a bounding box to constrain processing
            e.g. [480644.0,5752033.4,481029.4,5752251.6]
    
    mask: string
            path to a polygon file (eg shape, geojson) that will yield a bounding box to constrain processing
       
    """
    
    if sub != None:
        extFin = _subset(folder, sub, ext=ext)
    else:
        extFin = '.*'+ext

    
    mlog = open(path.join(folder, 'Maltlog.txt'), "w")    
    
    cmd = ['mm3d', 'Malt', mode, extFin, orientation, "DoMEC="+DoMEC,
           'DoOrtho='+DoOrtho,
           'DefCor='+DefCor, 'EZA=1']  
    
    if kwargs != None:
        for k in kwargs.items():
            oot = re.findall(r'\w+',str(k))
            anArg = oot[0]+'='+oot[1]
            cmd.append(anArg)
            
    if ResolTerrain != None:
        cmd.append("ResolTerrain="+ResolTerrain)               
    
    if mask != None:
        inShp = ogr.Open(mask)
        lyr = inShp.GetLayer()
        extent = list(lyr.GetExtent())
        extent = [extent[0], extent[2], extent[1], extent[3]]
        extStr = str(extent)
        finalExt = extStr.replace(" ", "")
        maskParam = 'BoxTerrain='+finalExt
        
        cmd.append(maskParam)
        
     
    if BoxTerrain != None:
        bt = 'BoxTerrain='+str(BoxTerrain)
        bt2 = bt.replace(" ", "")
        cmd.append(bt2)
        
        
    chdir(folder)
    
      
    ret = call(cmd, stdout=mlog)
    
    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
        
    
    
    
    dsmF = path.join(folder, 'MEC-Malt', '*Z_Num*_DeZoom*_STD-MALT.tif*')
    
    zedS = glob(dsmF)
    
    projF = "+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    
    # It could be we are simply producing the ortho's in which case this is all
    # not required
    if DoMEC == "1":
    # georef the DEMs - by georeffing them all we eliminate having to decide which one
        [_set_dataset_config(z, projF, FMT = 'Gtiff') for z in zedS]
        
        finalZs = path.join(folder, 'MEC-Malt', '*Z_Num*_DeZoom2*_STD-MALT.tif*')
        # Now to mask the last zoom -level raster
        
        zedFS = glob(finalZs)
        
        zedFS.sort()
        
        img = zedFS[-1]
        
        h,t = path.split(img)
        # want the lower number
        digit = re.findall('\d+', t)
        digit.sort()
        
        n1 = int(digit[1])-1
    
        maskstr = "Masq_STD-MALT_DeZoom"+digit[0]+".tif"
        mask_ras = path.join(folder, 'MEC-Malt', maskstr)
        
        
        finDir = path.join(folder, 'OUTPUT')
        if path.isdir(finDir) == False:
            mkdir(finDir)
        
        correl = path.join(folder, "MEC-Malt", "Correl_STD-MALT_Num_"+str(n1)+".tif")
        
        copy2(img, finDir)
        imgMeta = img[:-3]+"tfw"
        copy2(imgMeta, finDir)
        # here so we retain the unmasked one in MEC
        mask_raster_multi(path.join(finDir, img), mask=mask_ras) 
        
        copy2(correl, finDir)
        copy2(imgMeta, path.join(finDir,"Correl_STD-MALT_Num_"+str(n1)+".tfw"))
        
        outCor = path.join(finDir,"Correl_STD-MALT_Num_"+str(n1)+".tif")
        
        _set_dataset_config(outCor, projF, FMT = 'Gtiff')
#    
def pims(folder, mode='BigMac', ext="JPG", orientation="Ground_UTM",  
         DefCor='0', sub=None, delim=",", mask=False, **kwargs):
    """
    
    A function calling the PIMs command for use in python 
            
    Notes
    -----------
       
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
            
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a proj4/gdal like projection information e.g ESPG:32360
        
    mode: string
             Correlation mode - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        
    ext: string
                 image extention e.g JPG, tif
    
    orientation: string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
    mask: bool
                 image extention e.g JPG, tif
    """
    
    chdir(folder)
    
    if sub != None:
        extFin = _subset(folder, sub, delim=delim, ext=ext)
    else:
        extFin = '.*'+ext
    
    mlog = open(path.join(folder, 'PIMslog.txt'), "w")

    cmd = ['mm3d', 'PIMs', mode, extFin, orientation, 'DefCor='+DefCor]  
    
    if mask == True:
        sais = ["mm3d", "SaisieMasqQT", "AperiCloud_Ground_UTM.ply"]
        call(sais)
        cmd.append("Masq3D=AperiCloud_Ground_UTM_polyg3d.xml")
    
    if kwargs != None:
        for k in kwargs.items():
            oot = re.findall(r'\w+',str(k))
            anArg = oot[0]+'='+oot[1]
            cmd.append(anArg)
    
      
    ret = call(cmd, stdout=mlog)
    
    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit() 
        
def c3dc(folder, mode='Statue', ext="JPG", orientation="Ground_UTM", 
         sub=None, DefCor='0', delim=",", **kwargs):
    """
    
    A function calling the Culture 3D-cloud function 
            
    Notes
    -----------
       
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
            
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a proj4/gdal like projection information e.g ESPG:32360
        
    mode: string
             Correlation mode - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        
    ext: string
                 image extention e.g JPG, tif
    
    orientation: string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
    """
    
    chdir(folder)
    
    if sub != None:
        extFin = _subset(folder, sub, delim=delim, ext=ext)
    else:
        extFin = '.*'+ext
    
    
    mlog = open(path.join(folder, 'PIMslog.txt'), "w")
    
    oot = path.join("OUTPUT", "pointcloud.ply")
    
    if path.isdir(path.join(folder, 'OUTPUT')) == False:
        mkdir(path.join(folder, 'OUTPUT'))
    

    maskCloud = "AperiCloud_"+orientation+".ply"
    maskXml = "AperiCloud_"+orientation+"_polyg3d.xml"

    cmd = ['mm3d', 'C3DC', mode, extFin, orientation, 
           "Masq3D="+maskXml,'DefCor='+DefCor,
           "Out=Dense.ply"]  
    
    # A mask is mandatory here

    sais = ["mm3d", "SaisieMasqQT", maskCloud]
    call(sais)
    
    if kwargs != None:
        for k in kwargs.items():
            oot = re.findall(r'\w+',str(k))
            anArg = oot[0]+'='+oot[1]
            cmd.append(anArg)
    
      
    ret = call(cmd, stdout=mlog)
    
    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit() 
        
    copy2(path.join(folder, "Dense.ply"),
          path.join(folder, 'OUTPUT'))
    

def pims2mnt(folder, proj="30 +north", mode='BigMac',  DoOrtho='1',
             DoMnt='1',  **kwargs):
    """
    
    A function calling the PIMs2MNT command for use in python 
            
    Notes
    -----------
    
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
            
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a proj4/gdal like projection information e.g "ESPG:32360"
        
    mode: string
             Correlation folder to grid/rectify - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        

    
       
    """
    
    
    mlog = open(path.join(folder, 'PIMslog.txt'), "w")    
    
    cmd = ['mm3d', 'PIMs2MNT', mode, 'DoOrtho='+DoOrtho, "DoMnt="+DoMnt]  
    
    if kwargs != None:
        for k in kwargs.items():
            oot = re.findall(r'\w+',str(k))
            anArg = oot[0]+'='+oot[1]
            cmd.append(anArg)
            
            
        
        
    chdir(folder)
    
      
    ret = call(cmd, stdout=mlog)
    
    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
    
    dsmF = path.join(folder, 'PIMs-TmpBasc', 'PIMs-Merged_Prof.tif')
    dsmMeta = path.join(folder, 'PIMs-TmpBasc', 'PIMs-Merged_Prof.tfw')
    mask  = path.join(folder, 'PIMs-TmpBasc', 'PIMs-Merged_Masq.tif')
    correl = path.join(folder, 'PIMs-TmpBasc', 'PIMs-Merged_Correl.tif')
    
    # georef the DEM
    
    projF = "+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    
#    gdal_edit(datasetname=dsmF, srs=projF)
    _set_dataset_config(dsmF, projF, FMT = 'Gtiff')
    
    _set_dataset_config(correl, projF, FMT = 'Gtiff')
    
    mask_raster_multi(dsmF, mask=mask)
    
    finDir = path.join(folder, 'OUTPUT')
    if path.isdir(finDir) == False:
        mkdir(finDir)
    
    if DoMnt == '1':
        copy(dsmF, finDir)
        copy(dsmMeta, finDir)
        copy(correl, finDir)
    

#    if mode == 'Forest':
#        pishList = [path.join(folder, 'PIMs-TmpBasc'),
#                    path.join(folder, 'PIMs-ORTHO'),
#                    path.join(folder, 'PIMs-TmpMnt'),
#                    path.join(folder, 'PIMs-TmpMntOrtho')]
        
#        Parallel(n_jobs=-1, verbose=5)(delayed(rmtree)(pish) for pish in pishList)


def _remove_ortho_tiles(folder):
    '''
    Remove every other orthomosaic tile. Optimizes color balance and radiometric routine,
    speeds up ortho generation using Porto/Tawny module.
    
    Adapted from ODM node micmac
    '''
    ort_files = path.join(folder,'Ortho-MEC-Malt', 'Ort_*.tif')
    fileList = glob(ort_files)
    fileList.sort()
    # this doesn't work - so I have replaced it though I wonder what dif is...
    # tiles = glob(ort_files)
    # tiles.sort(key=lambda f: int(filter(str.isdigit, f)))
    
    rej = path.join(folder, 'Orthorejects')
    mkdir(rej)
    
    [move(tile, rej) for tile in fileList[::2]]
            

def tawny(folder, proj="30 +north", mode='PIMs', Out=None, rmtile=False,
          **kwargs):

    """
    
    A function calling the Tawny command for use in python 
            
    Notes
    -----------
    
    see MicMac tools link for further possible args - just put the module arg as a keyword arg
    The kwargs must be exactly the same case as the mm3d cmd options
    
    If struggling with even illumination, try:
    
    tawny(folder, proj="30 +north", mode='PIMs', Out=None, rmtile=False, 
          DEq="1", DegRapXY="[4,4]" SzV="75" NbPerIm="5e4")
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a proj4/gdal like projection information e.g "ESPG:32360"
        
    mode: string
             Either Malt or PIMs depending on the previous process
    rmtile: bool
             Remove every second tile - can speed up and sometimes improve 
             even illumination across mosaic

       
    """
    
    if mode == 'PIMs':
        ootFolder = 'PIMs-ORTHO'
    elif mode == 'Malt':
        ootFolder = 'Ortho-MEC-Malt'
    
    
    if rmtile==True:
        _remove_ortho_tiles(folder)
    
    mlog = open(path.join(folder, 'Tawnylog.txt'), "w")    
    
    chdir(folder)
    
    cmd = ['mm3d', 'Tawny', ootFolder]  
    
    if kwargs != None:
        for k in kwargs.items():
            oot = re.findall(r'\w+',str(k))
            anArg = oot[0]+'='+oot[1]
            cmd.append(anArg)
    
      
    ret = call(cmd, stdout=mlog)

    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
    orthF = path.join(folder, ootFolder, "Orthophotomosaic_Out.tif") 
    if path.exists(orthF) == False:
        orthF = path.join(folder, ootFolder, "Orthophotomosaic.tif")
        
    
    orthMeta = path.join(folder, ootFolder, "Orthophotomosaic.tfw") 
    
    cnvIm = ["mm3d", "ConvertIm", path.join(ootFolder, 'Orthophotomosaic.tif')] 
    
    ret = call(cnvIm, stdout=mlog)

    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
        
    projF = "+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    #gdal_edit(datasetname=orthF, srs=projF)
    _set_dataset_config(orthF, projF, FMT = 'Gtiff')
    
    finDir = path.join(folder, 'OUTPUT')
    
    if path.isdir(finDir) == False:
        mkdir(finDir)
        
    if Out == None:
        copy(orthF, path.join(finDir, "MosaicOut.tif"))
        copy(orthMeta, path.join(finDir, "MosaicOut.tfw"))
    else:
        copy(orthF, path.join(finDir, Out))
        copy(orthMeta, path.join(finDir, Out[:-2]+"fw"))
         

    

def feather(folder, proj="30 +north", mode='PIMs',
            ms=['r', 'g', 'b'], Dist="100", ApplyRE="1", ComputeRE="1", 
            subset=None,  outMosaic=None, rmtile=False, 
            mp=False, Label=False, redo=False, delim=",", **kwargs):
    
    """
    
    A function calling the TestLib SeamlineFeathering command for use in python 
            
    Notes
    -----------
    
    The native micmac function only processes single band - this function provides 
    a multi band capability
    
    
    An example usage:
        
    feather(folder, mode='Malt',outMosaic="Feathermp.tif", Dist="100", ApplyRE="1", ComputeRE="1", mp=True)
            
        
    Parameters
    -----------
    
    folder: string
           working directory
           
    proj: string
           a proj4/gdal like projection information e.g "ESPG:32360"

    mode: string
             Ortho folder use either PIMs or Malt here
             
    ms: list
        if a multi band image the band names in a list 
          
    mp: int
        Whether to employ multiprocessing 

    Dist: string
            The chamfer distance to feather, def None
            
    Lambda: string
             lambda value for gaussian distance weighting, def 0.4
             
    ApplyRE: string
                whether to apply radiometric equalisation, def 1
                
    ComputeRE: string
                whether to compute radiometric equalisation
        
    subset: string
        the absolute path to a csv defining a subset list of images to process
        if left as None, all the images will be mosiacked. 
        
    SzBox: string
            size of processing block, def [25000,25000]

    SzTile: string
            size of processing block, def [25000,25000] 
            
    Buffer: string
            Buffer [pix] to apply for each tile in order to avoid edge effect, def=300
            
    
    Label: bool
        Whether to use a tawny generated label map (Label.tif)
        This requires a run of Tawny on the Ortho folder first!
        
    redo: bool
        To rerun without having to copy the band folders on big datasets
        Useful as this step is time consuming during processing otherwise
    
    delim: string 
        If using a csv-based subset list, the delimeter can be specified- it is comma by default                                     
    """  
    
    if mode == 'PIMs':
        ootFolder = path.join(folder,'PIMs-ORTHO')
    elif mode == 'Malt':
        ootFolder =  path.join(folder,'Ortho-MEC-Malt')
    
    chdir(folder)
    
    mlog = open(path.join(folder, 'FeatherLog.txt'), "w") 
    
    if rmtile==True:
        _remove_ortho_tiles(folder)
#        
    projstr = ("+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    
    if ms !=None:
                
            if redo == True:
                for i in ms:
                    if path.exists(path.join(ootFolder+i,"RadiomEgalModels.xml")):
                        remove(path.join(ootFolder+i,"RadiomEgalModels.xml"))
                ootDirs =  [ootFolder+i for i in ms]
                
            else:
                for i in ms:
                    if path.isdir(ootFolder+i):
                        rmtree(ootFolder+i)
                    copytree(ootFolder, ootFolder+i)
                print(ootFolder+i+' done')
                
            #[copytree(ootFolder, ootFolder+i) for i in ms]
            
                ootDirs =  [ootFolder+i for i in ms]
        
                imList = glob(path.join(folder, ootDirs[0], "*Ort_*.tif"))
                imList.sort()
                for im in imList:
                    
                    img = Image.open(im)
                    hd, tail = path.split(im)
                    r,g,b = img.split()
                    r.save(path.join(ootDirs[0], tail))
                    g.save(path.join(ootDirs[1], tail))
                    b.save(path.join(ootDirs[2], tail))
        #[Popen(['mm3d', 'Tawny', d, "RadioEgal=1"]) for d in ootDirs]
        
    cmdList = []  
    outList = []
    

    
    for oot in ootDirs:
        
        
        if subset != None:
            sub2 = _subset(folder, subset, delim=delim, ext="tif")
            # Ort_IMG_0552_RGB.tif
            sub2 = sub2.replace("IMG", "Ort_IMG")

        else:
            imList = glob(path.join(folder, oot, "*Ort_*.tif"))
            imList.sort()
        #mlog = open(path.join(folder, 'SeamLog.txt'), "w")  
       
            subList = [path.split(item)[1] for item in imList]
        
            subStr = str(subList)
            
            sub2 = subStr.replace("[", "")
            sub2 = sub2.replace("]", "")
            sub2 = sub2.replace("'", "") 
            sub2 = sub2.replace(", ", "|")      
        
        chdir(path.join(folder, oot))
        
        outList.append(path.join(folder, oot, "SeamMosaic.tif")) 
        
        if Label == True:
            label = "Label="+path.join(folder, oot, "Label.tif") 
            cmd = ["mm3d", "TestLib", "SeamlineFeathering", '"'+sub2+'"', label,
               "Out=SeamMosaic.tif"]
        else:
            
            cmd = ["mm3d", "TestLib", "SeamlineFeathering", '"'+sub2+'"',
                   "Out=SeamMosaic.tif"]
        
        if kwargs != None:
            
            for k in kwargs.items():
                out = re.findall(r'\w+',str(k))
                anArg = out[0]+'='+out[1]
                cmd.append(anArg)
            
        print("mosaiking "+oot)
        
        if mp == True:
            p = Popen(cmd)
            cmdList.append(p)
        else:
            ret = call(cmd, stdout=mlog)
            if ret !=0:
                print('A micmac error has occured - check the log file')
                sys.exit()
            
    if mp == True:
       [c.wait() for c in cmdList]
        
    
    finDir = path.join(folder, 'OUTPUT')
    if path.isdir(finDir) == False:
        mkdir(finDir)
        
    if outMosaic != None:
        ootFeath = path.join(finDir, outMosaic)
    else:
        ootFeath = path.join(finDir, "FeatherMosaic.tif")
    _merge(names = outList, out_file = ootFeath)
    
    # TODO!
    _set_dataset_config(ootFeath, projstr, FMT = 'Gtiff')

    #chdir(folder)

# TODO - consider canning this as ossim is pain to get working on machines
# and for some weird reason will not subprocess so uses os.system
def ossimmosaic(folder, proj="30 +north", mode="ossimFeatherMosaic", nt=-1,
                rmtile=False):
    
    """
    
    A function mosaicing using the ossim library 
            
    Notes
    -----------  
        
    Parameters
    -----------
    
    folder: string
           working directory - likely a malt-ortho or pims equiv
           
    proj: string
           a proj4/gdal like projection information 
        
    mode: string
            ossim mosaic type of the options below:
            ossimBlendMosaic ossimMaxMosaic ossimImageMosaic 
            ossimClosestToCenterCombiner ossimBandMergeSource
            ossimFeatherMosaic
    rmtile: bool
           remove every other tile to perhaps improve things       

    
       
    """    
    

    projstr = ("+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    
    if rmtile==True:
        _remove_ortho_tiles(folder)
    
    orthList = glob(path.join(folder, "*Ort_*tif"))
    
    # Using this for now as for some bizarre reason I can't get it to work
    # internally for ossim
    
#    for f in $FOLDER/*Ort_*tif; do
#        gdal_edit.py -a_srs 
#        "+proj=utm +zone=$UTM  +ellps=WGS84 +datum=WGS84 +units=m +no_defs" "$f"; done
    Parallel(n_jobs=nt,
             verbose=5)(delayed(gdal_edit)(datasetname=i,
                       srs=projstr) for i in orthList) 
#    [call(["gdal_edit.py", i, "-a_srs", projstr]) for i in tqdm(orthList)]

#    Parallel(n_jobs=nt,
#             verbose=5)(delayed(gdal_edit)(call(["gdal_edit.py", i, "-a_srs", projstr])) 
#             for i in orthList) 
    # this works
    #procList=[]
    
    # messy
#    for item in orthList:
#        his_cmd = ["ossim-create-histo", "-i", item]
#        p = Popen(his_cmd)# runs parallel
#        procList.append(p)
#    [p.wait() for p in procList]
    # or gnu para
#    parCmd = ["ossim-orthoigen", "--combiner-type", mode, path.join(folder, "*Ort_*tif"),
#     path.join(folder, mode+".tif")]
    Parallel(n_jobs=-1,
             verbose=5)(delayed(call)(["ossim-create-histo",
                       "-i", i]) for i in orthList) 
    
    
#    inPth = path.join(folder, "*Ort_*tif")
                
    ootPth = mode+".tif"
    
    #TODO - this is the only thing that will work for some reason all the other comm'd out
    # stuff doesn't Ahhhhrrrgh!!!
    chdir(folder)
    print("Mosaicing orthos....")
    system("ossim-orthoigen --combiner-type ossimFeatherMosaic *Ort_*tif "+ootPth)
    print("done!")


        
def _set_dataset_config(inRas, projection, FMT = 'Gtiff'):
                         #dtype = gdal.GDT_CFloat64, bands = 1):
    """sets projection in dataset.

    """
    
    inDataset = gdal.Open(inRas, gdal.GA_Update)

    sr = osr.SpatialReference() 
    
    sr.ImportFromProj4(projection)
    # must be this for a geotiff
    wkt = sr.ExportToWkt()
    inDataset.SetProjection(wkt)
    
    inDataset.FlushCache()

def _subset(folder, csv, delim=",", ext="JPG"):
    
    """
    
    A function for passing a subset to Malt or PIMS
            
    Notes
    -----------
     
    
    see MicMac tools link for further possible kwargs - just put the module cmd as a kwarg
    
    
    
        
    Parameters
    -----------
    
    folder: string
           working directory
    proj: string
           a UTM zone eg "30 +north" 
        
    mode: string
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext: string
                 image extention e.g JPG, tif
    
    orientation: string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
       
    """

    with open(csv, 'r') as f:
        header = f.readline().strip('\n').split(delim)
        nm = header.index("#F=N")
        x_col = header.index('X') 
        y_col = header.index('Y')
        z_col = header.index('Z')
        imList = []
        x = []
        y = []
        z = []
        
        for line in f:
                l = line.strip('\n').split(delim)
                imList.append(l[nm])
                x.append(l[x_col])
                y.append(l[y_col])
                z.append(l[z_col])

    imList.sort()
    
    
    
    #subList = [path.split(item)[1] for item in imList]
    
    subStr = str(imList)
    
    sub2 = subStr.replace("[", "")
    sub2 = sub2.replace("]", "")
    sub2 = sub2.replace("'", "") 
    sub2 = sub2.replace(", ", "|")                 
    
    return sub2

def _proc_malt(subList, subName, bFolder, gOri, algo='Ortho', gP='0', window='5',
               proc=1, mmgpu=None, bbox=True):
    # Yes all this string mucking about is not great but it is better than 
    # dealing with horrific xml, when the info is so simple
    
    if gP ==None:
        gP = '0'
        mmgpu=='mm3d'


        
    
    tLog = path.join(bFolder, "TawnyLogs")
#    mkdir(tLog)
    mLog = path.join(bFolder, "MaltLogs")
#    mkdir(mLog)
    flStr = open(subList).read()
    # first we need the box terrain line
    box = flStr.split('\n', 1)[0]
    # then the images
    imgs = flStr.split("\n", 1)[1]
    # If on a repeat run this should avoid problems
#    imgSeq = imgs.split()
    imgs.replace("\n", "|")
    sub = imgs.replace("\n", "|")
    print('the img subset is \n'+sub+'\n\n, the bounding box is '+box) 
    
    # Outputting mm3d output to txt as it is better to keep track of multi process log
    if bbox ==True:
        mm3d = [mmgpu, "Malt", algo,'"'+sub+'"', gOri, "DefCor=0", "DoOrtho=1",
                "SzW="+window, "DirMEC="+subName[:-5], 
                "UseGpu="+gP, "NbProc="+str(proc), "EZA=1", box]
    else:
        mm3d = [mmgpu, "Malt", algo,'"'+sub+'"', gOri, "DefCor=0", "DoOrtho=1",
                "SzW="+window, "DirMEC="+subName[:-5], 
                "UseGpu="+gP, "NbProc="+str(proc), "EZA=1"]
    mf = open(path.join(mLog, subName[:-5]+'Mlog.txt'), "w")            
    ret = call(mm3d, stdout=mf)
    if ret != 0:        
        print(subName+" missed, will pick it up later")
        pass
    else:       
        tawny = [mmgpu, 'Tawny', "Ortho-"+subName+'/', 'RadiomEgal=1', 
                 'Out=Orthophotomosaic.tif']
        tf = open(path.join(tLog, subName[:-5]+'Tlog.txt'), "w")  
        call(tawny, stdout=tf)
        mDir = path.join(bFolder, subName)
        oDir = path.join(bFolder, "Ortho-"+subName) 
#        pDir= path.join(fld, subName+"pyram")
        hd, tl = path.split(subList)
        subDir = path.join(bFolder, tl)
        mkdir(subDir)
        if path.exists(mDir):
            move(mDir, subDir)
            print('subName done')
        else:
            pass            
        if path.exists(oDir):
            move(oDir, subDir)
            print('subName mosaic done')
        else:
            pass
#        if path.exists(pDir):
#            move(pDir, subDir)
#        else:
#            pass
        #return rejectList

def malt_batch(folder,  mode='Ortho',  mp=-1, gp=0, window=2, mx=None, ext="JPG",
               tiles="3,3", overlap=10, bb=False):
    """
    
    A function for passing a subset to Malt or PIMS
        
    Parameters
    -----------
    
    folder: string
           working directory
    mode: string
            The micmac processing mode eg 'Ortho' (default)
    
    gp: int (optional)
           path to gpu suppoted micmac bin folder 
        
    mp: int
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext: string
                 image extention e.g JPG, tif
    
    orientation: string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
    
       
    """    
    
    DMatch = path.join(folder, 'DMatch')
    bFolder = path.join(folder, 'MaltBatch')
    ori = path.join(folder,'Ori-Ground_UTM')
    homol = path.join(folder,'Homol')
    extFin = '.*'+ext
    
    
    if path.exists(DMatch):
        rmtree(DMatch)
    if path.exists(bFolder):
        rmtree(bFolder)
    
    mkdir(bFolder)

    tLog = path.join(bFolder, "TawnyLogs")
    mkdir(tLog)
    mLog = path.join(bFolder, "MaltLogs")
    mkdir(mLog)
    
    #binList = [DMatch, bFolder]
    
    gpp = str(gp)

    run(ori, homol, extFin,6, DMatch, tiles, overlap)
    
    txtList = glob(path.join(DMatch,'*.list'))
    nameList = [path.split(i)[1] for i in txtList]
    txtList.sort()
    nameList .sort()
    #list mania - I am crap at writing code
    finalList = list(zip(txtList, nameList))
    
#    def makelists(bFolder, subList):
##        tLog = path.join(bFolder, "TawnyLogs")
##    #    mkdir(tLog)
##        mLog = path.join(bFolder, "MaltLogs")
#    #    mkdir(mLog)
#        flStr = open(subList).read()
#        # first we need the box terrain line
#        box = flStr.split('\n', 1)[0]
#        # then the images
#        imgs = flStr.split("\n", 1)[1]
#        # If on a repeat run this should avoid problems
#    #    imgSeq = imgs.split()
#        imgs.replace("\n", "|")
#        sub = imgs.replace("\n", "|")
#        print('the img subset is \n'+sub+'\n\n, the bounding box is '+box) 
    
#
#        malt(folder, proj="30 +north", mode=mode, ext=ext, orientation=path.join(folder,"Ground_UTM"),
#             DoOrtho='1',  DefCor='0', sub=None, DirMEC=subName[:-5], NbProc=1, UseGpu=gp)
    chdir(folder)
    if mx == None:
        print('processing whole dataset')
        todoList = Parallel(n_jobs=mp,verbose=5)(delayed(_proc_malt)(i[0], 
             i[1], bFolder, "Ground_UTM", algo=mode, gP=gpp,  bbox=bb) for i in finalList) 
    else:
        subFinal = finalList[0:mx]
        todoList = Parallel(n_jobs=mp,verbose=5)(delayed(_proc_malt)(i[0], 
                 i[1], bFolder, "Ground_UTM", algo=mode, gP=gpp,  bbox=bb) for i in subFinal) 

    
    # get a list of what has worked
    doneList = glob(path.join(bFolder, "*.list"))
    doneFinal = [path.split(d)[1] for d in doneList]
    
    # get the difference between completed and listed tiles
    # set is a nice command for this purpose :D
    
    if mx is None:
        rejSet = set(nameList) - set(doneFinal)
        rejList = list(rejSet)
    else:
        nameList = [s[1] for s in subFinal] 
        rejSet = set(nameList) - set(doneFinal)
        rejList = list(rejSet)
    
    if len(rejList) ==0:
        print('No tiles missed, all done!')
        pass
    else:
        print('The following tiles have been missed\n')    
        [print(t) for t in rejList]
        print("\nRectifying this now...")

def dense_pcl(folder, mode="PIMs", out="psm.ply"):
    
    """
    A function for generating a dense cloud

    Parameters
    -----------
    
    folder: string
           working directory
    mode: string
            The micmac processing mode Malt or PIMs
    out: string
          The output point cloud in .ply format
    """
    
    if mode == 'PIMs':
        ootply = path.join(folder,'PIMs-TmpBasc', 'PIMs-Merged.xml')
        ootorth = path.join(folder,'PIMs-ORTHO', 'Orthophotomosaic.tif')
        
    elif mode == 'Malt':
        
        ootply = path.join(folder,'MEC-Malt', 'NuageImProf_STD-MALT_Etape_8.xml')
        ootorth = path.join(folder,'Ortho-MEC-Malt', 'Orthophotomosaic.tif')
        
    chdir(folder)
    

    
    nuage = ["mm3d", "Nuage2Ply",  ootply, "Attr="+ootorth, "Out="+out, "64B=1"]
    
    ret = call(nuage)

    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
    
    outcloud = path.join("OUTPUT", out)
    
    move(path.join(folder,out), outcloud)
    

def mesh(folder, inply, mode="Statue", ext='tif', ori="Ground_UTM"):
    
    """
    A function for passing a subset to Malt or PIMS

    Parameters
    -----------
    
    folder: string
           working directory
    inply: string
          the input dense cloud ply
    mode: string
            The micmac processing mode Malt or PIMs
    ext: string
         imagery extension
    ori: string
          orientation used
    """
    
    chdir(folder)
    
    extFin='.*'+ext
    
    cmd1 = ["mm3d", "TiPunch", inply, "Mode="+mode, "Pattern="+extFin]
    
    ret = call(cmd1)

    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()
    
    cmd2 = ["mm3d", "Tequila", extFin, ori, "Dense_poisson_depth8.ply", "Filter=1"]

    ret = call(cmd2)

    if ret !=0:
        print('A micmac error has occured - check the log file')
        sys.exit()

    
    
    