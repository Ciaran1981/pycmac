#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciaran Robb, 2019

https://github.com/Ciaran1981/Sfm

This module processes data from the micasense red-edge camera for use in MicMac
or indeed other SfM software

This correction is based on the material on the micasense lib git site, 
though this uses as fork of the micasense lib with some alterations. 

"""
import os#, sys
import matplotlib.pyplot as plt

import pycmac.micasense.imageutils as imageutils
import pycmac.micasense.capture as capture
from pycmac.utilities import _copy_dataset_config

import numpy as np
import pycmac.micasense.imageset as imageset
from glob2 import glob
import imageio
import cv2

from skimage import exposure, util
from subprocess import call#, check_call
from joblib import Parallel, delayed
from tqdm import tqdm
import gdal, ogr#, gdal_array
#from PIL import Image
import warnings


exiftoolPath=None


#nt = args.noT
def mspec_proc(precal, imgFolder, alIm, srFolder, postcal=None, refBnd=1, 
               nt=-1, mx=100, stk=1, plots=False, panel_ref=None, 
               warp_type='MH'):
    
    """
    
    A function processing the micasense data to surface reflectance with a 
    choice of output types dependent on preference.
    
   
            
    Notes
    -----------
    
    A set of RGB & RReNir images is recommended for processing with MicMac
    
    Either 5 band stack or single band outputs can also be produced.
    
    
        
    Parameters
    -----------
    
    precal : string
           directory containing pre-flight calibration panels pics
           
    imgFolder : string
           a directory containing the  
        
    alIm : string
             4 digit code of the image to align band images
             e.g. "0023"
        
    srFolder : string
                 path to directory for surface reflectance imagery
    
    postcal : string
                 directory containing pre-flight calibration panels pics
                 
    refBnd : int
                The band to which all others are aligned
            
    nt : int
                No of threads to use   
    
    mx : int
                Max iterations for alignment (uses opencv motion homography)

    stk : int
                The various multi-band stacking options
                1 = A set of RGB & RReNir images (best for MicMac)
                None = Single band images in separate folders are returned
    plots : bool
    
            Whether to display plots of the alignment images for visual inspection
    
    panel_ref : list
    
            The panel ref values unique to your panel/camera
            If left as None, it will load the authors camera values!
 
    warp_type : string
            
            The type of warping used to align the bands from the following choice of cv2 modes
    
            Either:
                MH for MOTION_HOMOGRAPHY
                Affine for MOTION_AFFINE
            
    """
    
    if warp_type == 'MH':
        warp_md = cv2.MOTION_HOMOGRAPHY
    elif warp_type =='Affine':
        warp_md= cv2.MOTION_AFFINE
        
    
    calibPre = os.path.abspath(precal)
    
    if postcal != None:
        calibPost = os.path.abspath(postcal)
    
    imagesFolder = os.path.abspath(imgFolder)
    
    reflFolder = os.path.abspath(srFolder)

    print("Aligning images, may take a while...")
    # Increase max_iterations to 1000+ for better results, but much longer runtimes
    '''
    Right so each capture means each set of bands 1-5
    This requires the image list to be sorted in a way that can be aligned
    It appears as though micasense have done this with their lib


    '''

    


    # RP03-1731303-SC
    #panel_ref = [0.56, 0.56, 0.56, 0.51, 0.55]
    
    # RP03-1731271-SC
    if panel_ref == None:
        panel_ref = [0.55, 0.56, 0.55, 0.50, 0.54]
    
    if os.path.isdir(srFolder) != True:
        os.mkdir(srFolder)
    
    
    imgset = imageset.ImageSet.from_directory(imagesFolder)
    
    
    preCapList = glob(os.path.join(calibPre, "*.tif"))
    preCapList.sort()
    pCapPre = capture.Capture.from_filelist(preCapList) 
    pPreIr = pCapPre.panel_irradiance(panel_ref)
    
    if postcal != None:
        pCapPost = capture.Capture.from_filelist(glob(calibPost, "*.tif")) 
    
        pPostIr = pCapPost.panel_irradiance(panel_ref)
    
        panel_irradiance = (pPreIr + pPostIr) / 2
    else:
        panel_irradiance = pPreIr
     #RedEdge band_index order
    
    # First we must find an image with decent features from which a band alignment 
    # can be applied to the whole dataset
     
    wildCrd = "IMG_"+alIm+"*.tif"
    algList = glob(os.path.join(imagesFolder, wildCrd))
    #algList.sort()
    imAl = capture.Capture.from_filelist(algList) 
    imAl.compute_reflectance(panel_irradiance)
    #imAl.plot_undistorted_reflectance(panel_irradiance)
    
    
    rf = refBnd
    
    imAl, mx, reflFolder, rf, plots, warp_md
    
    warp_matrices, alignment_pairs = align_template(imAl, mx, reflFolder,
                                                    rf, plots, warp_md)

    
    if stk != None:
        
        

        print("Producing pairs of 3-band composites muti core")
        #prep the dir
        bndNames = ['RGB', 'RRENir', 'GRNir', 'GRRe']
        bndFolders = [os.path.join(reflFolder, b) for b in bndNames]
        [os.mkdir(bf) for bf in bndFolders]
        
        Parallel(n_jobs=nt,
                 verbose=2)(delayed(_proc_imgs_comp)(imCap, warp_matrices,
                           bndFolders,
                           panel_irradiance, warp_md, rf) for imCap in imgset.captures)

        

    else:
        print("Producing single band images")
        
        bndNames = ['Blue', 'Green', 'Red', 'NIR', 'Red edge']
        bndFolders = [os.path.join(reflFolder, b) for b in bndNames]
        [os.mkdir(bf) for bf in bndFolders]
        Parallel(n_jobs=nt,
                 verbose=2)(delayed(_proc_imgs)(imCap,
                 warp_matrices,
                 bndFolders,
                 panel_irradiance, rf) for imCap in imgset.captures)

# func to align and display the result. 
def align_template(imAl, mx, reflFolder, rf, plots, warp_md):

    
    warp_matrices, alignment_pairs = imageutils.align_capture(imAl,
                                                              ref_index=rf, 
                                                              warp_mode=warp_md,
                                                              max_iterations=mx)
    for x,mat in enumerate(warp_matrices):
        print("Band {}:\n{}".format(x,mat))

    # cropped_dimensions is of the form:
    # (first column with overlapping pixels present in all images, 
    #  first row with overlapping pixels present in all images, 
    #  number of columns with overlapping pixels in all images, 
    #  number of rows with overlapping pixels in all images   )
    dist_coeffs = []
    cam_mats = []
# create lists of the distortion coefficients and camera matricies
    for i,img in enumerate(imAl.images):
        dist_coeffs.append(img.cv2_distortion_coeff())
        cam_mats.append(img.cv2_camera_matrix())
        
    #warp_mode = cv2.MOTION_HOMOGRAPHY #alignment_pairs[0]['warp_mode']
    match_index = rf#alignment_pairs[0]['ref_index']
    
    cropped_dimensions, edges = imageutils.find_crop_bounds(imAl, 
                                                            warp_matrices,
                                                            warp_mode=warp_md)
   # capture, warp_matrices, cv2.MOTION_HOMOGRAPHY, cropped_dimensions, None, img_type="reflectance",
    im_aligned = imageutils.aligned_capture(imAl, warp_matrices, warp_md,
                                            cropped_dimensions, match_index,
                                            img_type="reflectance")
    im_display = np.zeros((im_aligned.shape[0],im_aligned.shape[1],5), dtype=np.float32 )
    
    for iM in range(0,im_aligned.shape[2]):
        im_display[:,:,iM] =  imageutils.normalize(im_aligned[:,:,iM])
        
    rgb = im_display[:,:,[2,1,0]] 
    cir = im_display[:,:,[3,2,1]] 
    grRE = im_display[:,:,[4,2,1]] 
    
    
    if plots == True:
        
        fig, axes = plt.subplots(1, 3, figsize=(16,16)) 
        plt.title("Red-Green-Blue Composite") 
        axes[0].imshow(rgb) 
        plt.title("Color Infrared (CIR) Composite") 
        axes[1].imshow(cir) 
        plt.title("Red edge-Green-Red (ReGR) Composite") 
        axes[2].imshow(grRE) 
        plt.show()
    
    prevList = [rgb, cir, grRE]
    nmList = ['rgb.jpg', 'cir.jpg', 'grRE.jpg']
    names = [os.path.join(reflFolder, pv) for pv in nmList]
    
    for ind, p in enumerate(prevList):
        #img8 = bytescale(p)
        imgre = exposure.rescale_intensity(p)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            img8 = util.img_as_ubyte(imgre)
        imageio.imwrite(names[ind], img8)
    
    return warp_matrices, alignment_pairs#, dist_coeffs, cam_mats, cropped_dimensions
   
# prep work dir


# Main func to  write bands to their respective directory

def _proc_imgs(i, warp_matrices, bndFolders, panel_irradiance, warp_md, normalize=None):
    
    
#    for i in imgset.captures: 
    
    i.compute_reflectance(panel_irradiance) 
    #i.plot_undistorted_reflectance(panel_irradiance)  


    cropped_dimensions, edges = imageutils.find_crop_bounds(i, warp_matrices, warp_mode=warp_md)
    
    im_aligned = imageutils.aligned_capture(i, warp_matrices,
                                            warp_md,
                                            cropped_dimensions,
                                            None, img_type="reflectance")
    
    im_display = np.zeros((im_aligned.shape[0],im_aligned.shape[1],5), dtype=np.float32 )
    
    for iM in range(0,im_aligned.shape[2]):
        im_display[:,:,iM] =  imageutils.normalize(im_aligned[:,:,iM])*65535
    
    for k in range(0,im_display.shape[2]):
         im = i.images[k]
         hd, nm = os.path.split(im.path)
         outdata = im_aligned[:,:,i]
         outdata[outdata<0] = 0
         outdata[outdata>1] = 1
         
         outfile = os.path.join(bndFolders[k], nm)
         imageio.imwrite(outfile, outdata)
        
         cmd = ["exiftool", "-tagsFromFile", im.path,  "-file:all", "-iptc:all",
               "-exif:all",  "-xmp", "-Composite:all", outfile, 
               "-overwrite_original"]
         call(cmd)

def _proc_imgs_comp(i, warp_matrices, bndFolders, panel_irradiance, warp_md, rf):
    
    
    
    i.compute_reflectance(panel_irradiance) 
    #i.plot_undistorted_reflectance(panel_irradiance)  


    cropped_dimensions, edges = imageutils.find_crop_bounds(i, warp_matrices)
    
    im_aligned = imageutils.aligned_capture(i, warp_matrices,
                                            warp_md,
                                            cropped_dimensions,
                                            match_index=rf, img_type="reflectance")
    
    
    
    im_display = np.zeros((im_aligned.shape[0], im_aligned.shape[1], 5), dtype=np.float32)
    
    for iM in range(0,im_aligned.shape[2]):
        im_display[:,:,iM] =  imageutils.normalize(im_aligned[:,:,iM])*32768
    

    
    rgb = im_display[:,:,[2,1,0]] 
    #cir = im_display[:,:,[3,2,1]] 
    RRENir = im_display[:,:,[4,3,2]] 
    
#    cir = im_display[:,:,[3,2,1]]
#    
#    grRE = im_display[:,:,[4,2,1]] 
#    
#    imoot = [rgb, RRENir]
    
    del im_display
    
    imtags = ["RGB.tif", "RRENir.tif"]#, "GRNir.tif", "GRRE.tif"]
    im = i.images[1]
    hd, nm = os.path.split(im.path[:-5])
    
    

    #cmdList = []
    
    def _writeim(image, folder, nametag, im):
    
    #for ind, k in enumerate(bndFolders):      
         #img8 = bytescale(imoot[ind])
        #imgre = exposure.rescale_intensity(image,  out_range='uint16')
     
        #with warnings.catch_warnings():
        #warnings.simplefilter("ignore")
        img16 = np.uint16(np.round(image, decimals=0))
        del image
        outFile = os.path.join(folder, nm+nametag)
        #imageio.imwrite(outfile, img8)
        
        #imOut = Image.fromarray(img16)
    
        #imOut.save(outFile)
        imageio.imwrite(outFile, img16)
        
        del img16
        cmd = ["exiftool", "-tagsFromFile", im.path,  "-file:all", "-iptc:all",
               "-exif:all",  "-xmp", "-Composite:all", outFile, 
               "-overwrite_original"]
        call(cmd)
        
        
    
    _writeim(rgb, bndFolders[0], imtags[0], im)
    del rgb    
    _writeim(RRENir, bndFolders[1], imtags[1], im)
    del RRENir#, 
    # for ref
#[_proc_imgs(imCap, warp_matrices, reflFolder) for imCap in imgset]
def _proc_stack(i, warp_matrices, bndFolders, panel_irradiance, reflFolder, warp_md, rf):
    
    i.compute_reflectance(panel_irradiance) 
        #i.plot_undistorted_reflectance(panel_irradiance)  
    
    
    cropped_dimensions, edges = imageutils.find_crop_bounds(i, warp_matrices, warp_mode=warp_md)
    
    im_aligned = imageutils.aligned_capture(i, warp_matrices,
                                            cropped_dimensions,
                                            warp_md,
                                            match_index=rf, img_type="reflectance")
    
    im_display = np.zeros((im_aligned.shape[0],im_aligned.shape[1],5), 
                          dtype=np.float32)
    
    rows, cols, bands = im_display.shape
#    driver = gdal.GetDriverByName('GTiff')
    
    im = i.images[1].path
    hd, nm = os.path.split(im[:-6])

    filename = os.path.join(reflFolder, nm+'.tif') #blue,green,red,nir,redEdge
    #
    
#    outRaster = driver.Create(filename, cols, rows, 5, gdal.GDT_Byte)
#    normalize = False
    
    # Output a 'stack' in the same band order as RedEdge/Alutm
    # Blue,Green,Red,NIR,RedEdge[,Thermal]
    
    # NOTE: NIR and RedEdge are not in wavelength order!
    
    i.compute_reflectance(panel_irradiance+[0])
    
    i.save_capture_as_reflectance_stack(filename, normalize = True)
    
#    for i in range(0,5):
#        outband = outRaster.GetRasterBand(i+1)
#        if normalize:
#            outband.WriteArray(imageutils.normalize(im_aligned[:,:,i])*65535)
#        else:
#            outdata = im_aligned[:,:,i]
#            outdata[outdata<0] = 0
#            outdata[outdata>1] = 1
#            
#            outband.WriteArray(outdata*65535)
#        outband.FlushCache()
#    
#    if im_aligned.shape[2] == 6:
#        outband = outRaster.GetRasterBand(6)
#        outdata = im_aligned[:,:,5] * 100 # scale to centi-C to fit into uint16
#        outdata[outdata<0] = 0
#        outdata[outdata>65535] = 65535
#        outband.WriteArray(outdata)
#        outband.FlushCache()
#    outRaster = None
    
    cmd = ["exiftool", "-tagsFromFile", im,  "-file:all", "-iptc:all",
               "-exif:all",  "-xmp", "-Composite:all", filename, 
               "-overwrite_original"]
    call(cmd)


         

def stack_rasters(inRas1, inRas2, outRas, blocksize=256):
    rasterList1 = [1,2,3]
    rasterList2 = [2, 3]
    
    inDataset1 = gdal.Open(inRas1)
    inDataset2 = gdal.Open(inRas2)
    
    outDataset = _copy_dataset_config(inDataset1, FMT = 'Gtiff', outMap = outRas,
                         dtype = gdal.GDT_Int32, bands = 5)
    
    bnnd = inDataset1.GetRasterBand(1)
    cols = outDataset.RasterXSize
    rows = outDataset.RasterYSize

    # So with most datasets blocksize is a row scanline
    if blocksize == None:
        blocksize = bnnd.GetBlockSize()
        blocksizeX = blocksize[0]
        blocksizeY = blocksize[1]
    else:
        blocksizeX = blocksize
        blocksizeY = blocksize
    del bnnd
    
    
    
    for band in rasterList1:
        bnd1 = inDataset1.GetRasterBand(band)
        ootBnd = outDataset.GetRasterBand(band)
        
        for i in tqdm(range(0, rows, blocksizeY)):
                if i + blocksizeY < rows:
                    numRows = blocksizeY
                else:
                    numRows = rows -i
            
                for j in range(0, cols, blocksizeX):
                    if j + blocksizeX < cols:
                        numCols = blocksizeX
                    else:
                        numCols = cols - j
#                    for band in range(1, bands+1):
                    
                    array = bnd1.ReadAsArray(j, i, numCols, numRows)
    
                    if array is None:
                        continue
                    else:
    
                        ootBnd.WriteArray(array, j, i)
                    
    for k,band in enumerate(rasterList2):
        
        bnd2 = inDataset2.GetRasterBand(band)
        ootBnd = outDataset.GetRasterBand(k+4)
        
        for i in tqdm(range(0, rows, blocksizeY)):
                if i + blocksizeY < rows:
                    numRows = blocksizeY
                else:
                    numRows = rows -i
            
                for j in range(0, cols, blocksizeX):
                    if j + blocksizeX < cols:
                        numCols = blocksizeX
                    else:
                        numCols = cols - j
    #                for band in range(1, bands+1):
                    
                    array = bnd2.ReadAsArray(j, i, numCols, numRows)
                    
                    if array is None:
                        continue
                    else:
    
                        ootBnd.WriteArray(array, j, i)
                        
    outDataset.FlushCache()
    outDataset = None

    

def mica_csv(folder, time_date=False):
    
    
    if time_date != False:
        header = "#F=N X Y Z GPSTimeStamp"
    else:
        header = "#F=N X Y Z"
    lines = [header]
    
    imgset = imageset.ImageSet.from_directory(folder)

    for cap in imgset.captures:
    
        lat,lon,alt = cap.location()
        #resolution = capture.images[0].focal_plane_resolution_px_per_mm
        impath = cap.images[0].path[:-6]
        hd, tl  = os.path.split(impath)
        linestr = tl+","
        linestr += str(lon)+","
        linestr += str(lat)+","
        linestr += str(alt)+","    
        linestr += capture.utc_time().strftime("%Y:%m:%d,%H:%M:%S,")
        linestr += '\n' # when writing in text mode, the write command will convert to os.linesep
        lines.append(linestr)
    
    fullCsvPath = os.path.join(folder,'log.csv')
    with open(fullCsvPath, 'w') as csvfile: #create CSV
        csvfile.writelines(lines)



def clip_raster(inRas, inShape, outRas):

    """
    Clip a raster using the extent of a shapefile
    
    Parameters
    ----------
        
    inRas : string
            the input image 
            
    inShape : string
              the input polygon file path 
        
    outRas : string (optional)
             the clipped raster
        
    nodata_value : numerical (optional)
                   self explanatory
        
   
    """
    

    vds = ogr.Open(inShape)
           
    rds = gdal.Open(inRas, gdal.GA_ReadOnly)
    
    lyr = vds.GetLayer()

    
    extent = lyr.GetExtent()
    
    extent = [extent[0], extent[2], extent[1], extent[3]]
            

    print('cropping')
    ds = gdal.Warp(outRas,
              rds,
              format = 'GTiff', outputBounds = extent)
              


    ds.FlushCache()

    ds = None












    
