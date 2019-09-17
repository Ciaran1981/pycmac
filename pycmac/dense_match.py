#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciaran Robb, 2019

A module which calls Micmac dense matching commands and mosaicking operations, 
whilst a providing dditional file parsing, sorting, image masking and multi-band 
functionallity.

https://github.com/Ciaran1981/Sfm/pycmac/


"""


from subprocess import call, Popen
from os import path, chdir, mkdir
import gdal
import re
import sys
from glob2 import glob
import osr
from pycmac.utilities import mask_raster_multi
from pycmac.gdal_edit import gdal_edit
from pycmac.gdal_merge import _merge
from shutil import rmtree, copytree
from joblib import Parallel, delayed
import pandas as pd
from pycmac.tile import  run
from shutil import rmtree, move, copy#, copytree
from tqdm import tqdm
from PIL import Image

def malt(folder, proj="30 +north", mode='Ortho', ext="JPG", orientation="Ground_UTM",
         DoOrtho='1',  DefCor='0', sub=None, **kwargs):
    
    """
    
    A function calling the Malt command for use in python 
            
    Notes
    -----------
    
    see MicMac tools link for further possible kwargs - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
    e.g = UseGpu='1'
    
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
        
    alIm : string
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext : string
                 image extention e.g JPG, tif
    
    orientation : string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
       
    """
    
    if sub != None:
        extFin = _subset(folder, sub, ext=ext)
    else:
        extFin = '.*'+ext

    
    mlog = open(path.join(folder, 'Maltlog.txt'), "w")    
    
    cmd = ['mm3d', 'Malt', mode, extFin, orientation, 'DoOrtho='+DoOrtho,
           'DefCor='+DefCor, 'EZA=1']  
    
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
        
    
    
    
    dsmF = path.join(folder, 'MEC-Malt', '*Z_Num*_DeZoom*_STD-MALT.tif*')
    
    zedS = glob(dsmF)
   
    
    
    projF = "+proj=utm +zone="+proj+"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    
    # georef the DEMs - by georeffing them all we eliminate having to decide which one
    [_set_dataset_config(z, projF, FMT = 'Gtiff') for z in zedS]
    
    # Now to mask the last zoom -level raster
    img = zedS[-1]
    
    # want the lower number
    digit = re.findall('\d+', img)
    digit.sort()

    maskstr = "Masq_STD-MALT_DeZoom"+digit[0]+".tif"
    mask_ras = path.join(folder, 'MEC-Malt', maskstr)
    mask_raster_multi(img, mask=mask_ras) 
    
    
#    
def pims(folder, mode='BigMac', ext="JPG", orientation="Ground_UTM",  
         DefCor='0', sub=None, **kwargs):
    """
    
    A function calling the PIMs command for use in python 
            
    Notes
    -----------
       
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
            
    Parameters
    -----------
    
    folder : string
           working directory
           
    proj : string
           a proj4/gdal like projection information e.g ESPG:32360
        
    mode : string
             Correlation mode - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        
    ext : string
                 image extention e.g JPG, tif
    
    orientation : string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
    e.g = UseGpu='1'  
    """
    
    if sub != None:
        extFin = _subset(folder, sub, ext=ext)
    else:
        extFin = '.*'+ext
    
    mlog = open(path.join(folder, 'Maltlog.txt'), "w")    
    
    cmd = ['mm3d', 'PIMs', mode, extFin, orientation, 'DefCor='+DefCor]  
    
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
    
    if mode == 'Forest':
        pishList = [path.join(folder, 'PIMs-TmpBasc'),
                    path.join(folder, 'PIMs-ORTHO'),
                    path.join(folder, 'PIMs-TmpMnt'),
                    path.join(folder, 'PIMs-TmpMntOrtho')]
        
        Parallel(n_jobs=-1, verbose=5)(delayed(rmtree)(pish) for pish in pishList)
#    
#    
def pims2mnt(folder, proj="30 +north", mode='BigMac',  DoOrtho='1',  **kwargs):
    """
    
    A function calling the PIMs2MNT command for use in python 
            
    Notes
    -----------
    
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
            
    Parameters
    -----------
    
    folder : string
           working directory
           
    proj : string
           a proj4/gdal like projection information e.g "ESPG:32360"
        
    mode : string
             Correlation folder to grid/rectify - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        

    
       
    """
    
    
    mlog = open(path.join(folder, 'PIMslog.txt'), "w")    
    
    cmd = ['mm3d', 'PIMs2MNT', mode, 'DoOrtho='+DoOrtho]  
    
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
    
    dsmF = (folder, 'PIMs-Tmp-Basc', 'PIMs-Merged-Prof.tif')
    
    # georef the DEM
    _set_dataset_config(dsmF, proj, FMT = 'Gtiff')

def tawny(folder, proj="30 +north", mode='PIMs', **kwargs):

    """
    
    A function calling the PIMs2MNT command for use in python 
            
    Notes
    -----------
    
    see MicMac tools link for further possible args - just put the module cmd as a kwarg
    The kwargs must be exactly the same case as the mm3d cmd options
    
    
        
    Parameters
    -----------
    
    folder : string
           working directory
           
    proj : string
           a proj4/gdal like projection information e.g "ESPG:32360"
        
    mode : string
             Correlation folder to grid/rectify - MicMac, BigMac, QuickMac, Forest, Statue
             Default is BigMac
        

    
       
    """
    
    if mode == 'PIMs':
        ootFolder = 'PIMs-ORTHO'
    elif mode == 'Malt':
        ootFolder = 'Ortho-MEC-Malt'
    
    mlog = open(path.join(folder, 'Tawnylog.txt'), "w")    
    

    
    cmd = ['mm3d', 'Tawny', mode]  
    
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
    
    
    orthF = path.join(folder, ootFolder, "Orthophotomosaic.tif") 
    
    _set_dataset_config(orthF, proj, FMT = 'Gtiff')

def feather(folder, proj="ESPG:32360", mode='PIMs', ApplyRE="1", ComputeRE="1",
            ms=['r', 'g', 'b'], mp=True, subset=None, SzBox='5000'):
    

    """
    
    A function calling the TestLib SeamlineFeathering command for use in python 
            
    Notes
    -----------
    
    The native micmac function only processes single band - this function provides 
    a multi band capability (3 at present)
        
        
    Parameters
    -----------
    
    folder : string
           working directory
           
    proj : string
           a proj4/gdal like projection information e.g "ESPG:32360"
        
    mode : string
             Ortho folder use either PIMs or Malt here
    ms : list
        if a multi band image the band names in a list
        
    mp : bool
        if true, process bands in parallel - with large datasets in sequence
        is recommended as there appears to be little merit to parallel.
    subset : string
        the absolute path to a csv defining a subset list of images to process
        if left as None, all the images will be mosiacked. 

    
       
    """
    if mode == 'PIMs':
        ootFolder = path.join(folder,'PIMs-ORTHO')
    elif mode == 'Malt':
        ootFolder =  path.join(folder,'Ortho-MEC-Malt')
    
    chdir(folder)
    
    if ms !=None:
        
        for i in ms:
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
    
    szbx = "SzBox=["+SzBox+","+SzBox+"]" 
    
    for oot in ootDirs:
        
        
        if subset != None:
            sub2 = _subset(folder, subset, ext="tif")
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
        
        cmd = ["mm3d", "TestLib", "SeamlineFeathering", '"'+sub2+'"',
               "ApplyRE="+ApplyRE, "ComputeRE="+ComputeRE, szbx,
               "Out=SeamMosaic.tif"]
        print("mosaiking "+oot)
        cmdList.append(cmd)
    
    if mp ==True:    
        Parallel(n_jobs=3,
                 verbose=5)(delayed(call)(c) for c in cmdList)
    else:
        [call(c) for c in cmdList]
        
        #p = Popen(cmd)
        
#        if mp == True:
#            p = Popen(cmd)
#            cmdList.append(p)
        #else:
        #cmdList.append(cmd)
        
#        ret = call(cmd, stdout=mlog)
#    
#        if ret !=0:
#            print('A micmac error has occured - check the log file')
#            sys.exit()
        
#        orthF = path.join(folder, ootFolder, "SeamMosaic.tif")
#        _set_dataset_config(path.abspath(orthF), proj, FMT = 'Gtiff')
#    if mp == True:
#        [c.wait() for c in cmdList]
#        
#    else:

        
    #[call(c) for c in cmdList]
    
    _merge(names = outList, out_file = path.join(folder, "OUTPUT", "FeatherMosaic.tif"))
    

    #chdir(folder)

def ossimmosaic(folder, proj="30 +north", mode="ossimFeatherMosaic", nt=-1):
    
    """
    
    A function mosaicing using the ossim library 
            
    Notes
    -----------  
        
    Parameters
    -----------
    
    folder : string
           working directory - likely a malt-ortho or pims equiv
           
    proj : string
           a proj4/gdal like projection information 
        
    mode : string
            ossim mosaic type of the options below:
            ossimBlendMosaic ossimMaxMosaic ossimImageMosaic 
            ossimClosestToCenterCombiner ossimBandMergeSource
            ossimFeatherMosaic
        

    
       
    """    
    

    projstr = ("+proj=utm +zone="+proj+" +ellps=WGS84 +datum=WGS84"
              "+units=m +no_defs")
    
    orthList = glob(path.join(folder, "*Ort_*tif"))
    
    Parallel(n_jobs=16,
             verbose=5)(delayed(gdal_edit)(datasetname=i,
                       srs=projstr) for i in orthList) 
#    [gdal_edit(datasetname=i, srs=projstr) for i in tqdm(orthList)]
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
    
    
    ossimproc= ["ossim-orthoigen", "--combiner-type", mode, path.join(folder, "*Ort_*tif"),
     path.join(folder, mode+".tif")]
    call(ossimproc)
#    echo "generating image histograms"
#    find $FOLDER/*Ort_*tif | parallel "ossim-create-histo -i {}" 
     
    # Max seems best
#    echo "creating final mosaic using $MTYPE"
#    ossim-orthoigen --combiner-type "${PBATCH}"  $FOLDER/*Ort_*tif $FOLDER/$OUT
    
#    if kwargs != None:
#        for k in kwargs.items():
#            oot = re.findall(r'\w+',str(k))
#            anArg = oot[0]+'='+oot[1]
#            cmd.append(anArg)

        
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

def _subset(folder, csv, ext="JPG"):
    
    """
    
    A function for passing a subset to Malt or PIMS
            
    Notes
    -----------
     
    
    see MicMac tools link for further possible kwargs - just put the module cmd as a kwarg
    
    
    
        
    Parameters
    -----------
    
    folder : string
           working directory
    proj : string
           a UTM zone eg "30 +north" 
        
    mode : string
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext : string
                 image extention e.g JPG, tif
    
    orientation : string
                 orientation folder to use (generated by previous tools/cmds)
                 default is "Ground_UTM"
    
       
    """

    
    
    dF = pd.read_table(csv, sep=",")
    
    imList = list(dF['#F=N'])
    imList.sort()
    
    
    #subList = [path.split(item)[1] for item in imList]
    
    subStr = str(imList)
    
    sub2 = subStr.replace("[", "")
    sub2 = sub2.replace("]", "")
    sub2 = sub2.replace("'", "") 
    sub2 = sub2.replace(", ", "|")                 
    
    return sub2

def _proc_malt(subList, subName, bFolder, gOri, algo='Ortho', gP='0', window='2',
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
            
    Notes
    -----------
        
        
    Parameters
    -----------
    
    folder : string
           working directory
    gp : string (optional)
           path to gpu suppoted micmac bin folder 
        
    mp : string
             Correlation mode - Ortho, UrbanMNE, GeomImage
        
    ext : string
                 image extention e.g JPG, tif
    
    orientation : string
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

