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
import os, sys
import matplotlib.pyplot as plt

import pycmac.micasense.imageutils as imageutils
import pycmac.micasense.capture as capture
from pycmac.utilities import _copy_dataset_config

import numpy as np
import pycmac.micasense.imageset as imageset
from glob2 import glob
import imageio
import cv2
from pycmac.micasense.panel import Panel
from pycmac.micasense.image import Image
from skimage import exposure, util
from subprocess import call#, check_call
from joblib import Parallel, delayed
from tqdm import tqdm
import gdal, ogr#, gdal_array
#from PIL import Image
import warnings


exiftoolPath=None


#nt = args.noT

def slant_view_proc(folder, nt=-1):


    dirList =  os.listdir(folder)
    
    dirList.sort()
    
    fileList = glob(os.path.join(folder, dirList[0], "*.tif"))
    
    ref = cv2.imread(fileList[0], cv2.IMREAD_LOAD_GDAL)
    
    fileList = [os.path.split(i)[1] for i in fileList] 
    
    fileList.sort()
    
    rgbdir = os.path.join(folder, "RGB")
    os.mkdir(rgbdir)
    
    msdir = os.path.join(folder, "RRENir")
    os.mkdir(msdir)
    
   
    def _proc_my_pics(f):
        
        inList = [os.path.join(folder, d, f) for d in dirList]
        
        rgb = np.zeros((ref.shape[0], ref.shape[1], 3), dtype=np.uint8)
        mspec = np.zeros((ref.shape[0], ref.shape[1], 3), dtype=np.uint8)
        
        
        for im in range(0,3):
            rgb[:,:,im] = cv2.imread(inList[im], cv2.IMREAD_LOAD_GDAL)
        
        for im in range(3,6):
            mspec[:,:,im-3] = cv2.imread(inList[im], cv2.IMREAD_LOAD_GDAL)    
            
        outRgb = os.path.join(rgbdir, f)
        imageio.imwrite(outRgb, rgb)    
        
        cmd1 = ["exiftool", "-tagsFromFile", inList[0],  "-file:all", "-iptc:all",
           "-exif:all",  "-xmp", "-Composite:all", outRgb, 
           "-overwrite_original"]
        call(cmd1)
        
        
        outMs = os.path.join(msdir, f)
        imageio.imwrite(outMs, mspec)  
        
        cmd2 = ["exiftool", "-tagsFromFile", inList[0],  "-file:all", "-iptc:all",
           "-exif:all",  "-xmp", "-Composite:all", outMs, 
           "-overwrite_original"]
        call(cmd2)
    
    Parallel(n_jobs=nt, verbose=2)(delayed(_proc_my_pics)(file) for file in fileList)
    

def mspec_proc(imgFolder, alIm, srFolder, precal=None, postcal=None, refBnd=4, 
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
                The band to which all others are aligned def 4 works best
            
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
        
    if precal != None:
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
           
        #panel_ref = [0.55, 0.56, 0.55, 0.50, 0.54]
    if precal !=None:
        preCapList = glob(os.path.join(calibPre, "*.tif"))
        preCapList.sort()
        pCapPre = capture.Capture.from_filelist(preCapList) 
        pPreIr = pCapPre.panel_irradiance(panel_ref)
    else:
        pPreIr = None
    if panel_ref == None:
        
        pList = [Panel(Image(i)) for i in preCapList]
        
        panel_ref = [p.reflectance_from_panel_serial() for p in pList]

    
    if os.path.isdir(srFolder) != True:
        os.mkdir(srFolder)
    
    
    imgset = imageset.ImageSet.from_directory(imagesFolder)
    

    
    if postcal != None:
        
        pstList = glob(os.path.join(calibPost, "*.tif"))
        pstList.sort()
        pCapPost = capture.Capture.from_filelist(pstList) 
        pPostIr = pCapPost.panel_irradiance(panel_ref)
        
        panel_irr = (np.array(pPreIr) + np.array(pPostIr)) / 2
        panel_irradiance = list(panel_irr)
    else:
        panel_irradiance = pPreIr
     #RedEdge band_index order
    
    # First we must find an image with decent features from which a band alignment 
    # can be applied to the whole dataset
     
    wildCrd = "IMG_"+alIm+"*.tif"
    algList = glob(os.path.join(imagesFolder, wildCrd))
    #algList.sort()
    imAl = capture.Capture.from_filelist(algList) 
    imAl.compute_reflectance(irradiance_list=panel_irradiance)
    #imAl.plot_undistorted_reflectance(panel_irradiance)
    
    
    rf = refBnd-1
    
    #imAl, mx, reflFolder, rf, plots, warp_md
    
    warp_matrices, alignment_pairs, rgb, cir, grRE = align_template(imAl, mx, reflFolder,
                                                    rf, plots, warp_md)
    
    if plots == True:
        
        fig, axes = plt.subplots(1, 3, figsize=(16,16)) 
        plt.title("Red-Green-Blue Composite") 
        axes[0].imshow(rgb) 
        plt.title("Color Infrared (CIR) Composite") 
        axes[1].imshow(cir) 
        plt.title("Red edge-Green-Red (ReGR) Composite") 
        axes[2].imshow(grRE) 
        plt.show()
    
    if not input("Please check the SR folder - Is the imagery correctly aligned for all bands ? (y/n): ").lower().strip()[:1] == "y": 
        print("Run again with a different alignment image candidate")
        sys.exit(1)
        
    del rgb, cir, grRE
    
    if stk != None:
        
        

        print("Producing pairs of 3-band composites muti core")
        #prep the dir
        bndNames = ['RGB', 'RRENir']
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
    
    

    
    prevList = [rgb, cir, grRE]
    nmList = ['rgb.jpg', 'cir.jpg', 'grRE.jpg']
    ootF, _ = os.path.split(reflFolder)
    names = [os.path.join(ootF, pv) for pv in nmList]
    
    for ind, p in enumerate(prevList):
        #img8 = bytescale(p)
        imgre = exposure.rescale_intensity(p)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            img8 = util.img_as_ubyte(imgre)
        imageio.imwrite(names[ind], img8)
    
    return warp_matrices, alignment_pairs, rgb, cir, grRE#, dist_coeffs, cam_mats, cropped_dimensions
   
# prep work dir


# Main func to  write bands to their respective directory

def _proc_imgs(i, warp_matrices, bndFolders, panel_irradiance, warp_md, normalize=None):
    
    
#    for i in imgset.captures: 
    
    i.compute_reflectance(irradiance_list=panel_irradiance) 
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
    
    
    
    i.compute_reflectance(irradiance_list=panel_irradiance) 
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
    hd, nm = os.path.split(im.path[:-6])
    
    

    #cmdList = []
    
    def _writeim(image, folder, nametag, im):
    
    #for ind, k in enumerate(bndFolders):      
         #img8 = bytescale(imoot[ind])
        #imgre = exposure.rescale_intensity(image,  out_range='uint16')
     
        #with warnings.catch_warnings():
        #warnings.simplefilter("ignore")
        img16 = np.uint16(np.round(image, decimals=0))
        del image
        outFile = os.path.join(folder, nm+'.tif')
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
    
    i.compute_reflectance(irradiance_list=panel_irradiance) 
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


         

def _raster_copy( s_fh, s_xoff, s_yoff, s_xsize, s_ysize, s_band_n,
                 t_fh, t_xoff, t_yoff, t_xsize, t_ysize, t_band_n):
    
    """
    Lifted from gdal_merge - internal use
    
    """

#    if verbose != 0:
    print('Copy %d,%d,%d,%d to %d,%d,%d,%d.'
          % (s_xoff, s_yoff, s_xsize, s_ysize,
         t_xoff, t_yoff, t_xsize, t_ysize ))



    s_band = s_fh.GetRasterBand( s_band_n )
    m_band = None
    # Works only in binary mode and doesn't take into account
    # intermediate transparency values for compositing.
    if s_band.GetMaskFlags() != gdal.GMF_ALL_VALID: 
        m_band = s_band.GetMaskBand()
    elif s_band.GetColorInterpretation() == gdal.GCI_AlphaBand:
        m_band = s_band
#    if m_band is not None:
#        return raster_copy_with_mask(
#            s_fh, s_xoff, s_yoff, s_xsize, s_ysize, s_band_n,
#            t_fh, t_xoff, t_yoff, t_xsize, t_ysize, t_band_n,
#            m_band )

    s_band = s_fh.GetRasterBand( s_band_n )
    t_band = t_fh.GetRasterBand( t_band_n )

    data = s_band.ReadRaster( s_xoff, s_yoff, s_xsize, s_ysize,
                  t_xsize, t_ysize, t_band.DataType )
    t_band.WriteRaster( t_xoff, t_yoff, t_xsize, t_ysize,
                        data, t_xsize, t_ysize, t_band.DataType )

    return 0

def _copy_into(inRas, t_fh, s_band = 1, t_band = 1):
    """
    
    Adapted from gdal_merge and now shorne of object-based rubbish.
    
    For internal use in this module
    
    Copy this files image into target file.

    This method will compute the overlap area of the file_info objects
    file, and the target gdal.Dataset object, and copy the image data
    for the common window area.  It is assumed that the files are in
    a compatible projection ... no checking or warping is done.  However,
    if the destination file is a different resolution, or different
    image pixel type, the appropriate resampling and conversions will
    be done (using normal GDAL promotion/demotion rules).
    
    Parameters
    ----------
        
    inRas : byte
            a gdal.Dataset object (already opened)
            
    t_fh : byte
              gdal.Dataset object for the file into which some or all
    of this file may be copied.
    
    
    """


    inxsize = inRas.RasterXSize
    inysize = inRas.RasterYSize
    ingeotransform = inRas.GetGeoTransform()
    inulx = ingeotransform[0]
    inuly = ingeotransform[3]
    inlrx = inulx + ingeotransform[1] * inxsize
    inlry = inuly + ingeotransform[5] * inysize

    ct = inRas.GetRasterBand(1).GetRasterColorTable()
    if ct is not None:
        inct = ct.Clone()
    else:
        inct = None

    
    t_geotransform = t_fh.GetGeoTransform()
    t_ulx = t_geotransform[0]
    t_uly = t_geotransform[3]
    t_lrx = t_geotransform[0] + t_fh.RasterXSize * t_geotransform[1]
    t_lry = t_geotransform[3] + t_fh.RasterYSize * t_geotransform[5]

    # figure out intersection region
    tgw_ulx = max(t_ulx,inulx)
    tgw_lrx = min(t_lrx,inlrx)
    if t_geotransform[5] < 0:
        tgw_uly = min(t_uly,inuly)
        tgw_lry = max(t_lry,inlry)
    else:
        tgw_uly = max(t_uly,inuly)
        tgw_lry = min(t_lry,inlry)

    # do they even intersect?
    if tgw_ulx >= tgw_lrx:
        return 1
    if t_geotransform[5] < 0 and tgw_uly <= tgw_lry:
        return 1
    if t_geotransform[5] > 0 and tgw_uly >= tgw_lry:
        return 1

    # compute target window in pixel coordinates.
    tw_xoff = int((tgw_ulx - t_geotransform[0]) / t_geotransform[1] + 0.1)
    tw_yoff = int((tgw_uly - t_geotransform[3]) / t_geotransform[5] + 0.1)
    tw_xsize = int((tgw_lrx - t_geotransform[0])/t_geotransform[1] + 0.5) \
               - tw_xoff
    tw_ysize = int((tgw_lry - t_geotransform[3])/t_geotransform[5] + 0.5) \
               - tw_yoff

    if tw_xsize < 1 or tw_ysize < 1:
        return 1

    # Compute source window in pixel coordinates.
    sw_xoff = int((tgw_ulx - ingeotransform[0]) / ingeotransform[1])
    sw_yoff = int((tgw_uly - ingeotransform[3]) / ingeotransform[5])
    sw_xsize = int((tgw_lrx - ingeotransform[0]) \
                   / ingeotransform[1] + 0.5) - sw_xoff
    sw_ysize = int((tgw_lry - ingeotransform[3]) \
                   / ingeotransform[5] + 0.5) - sw_yoff

    if sw_xsize < 1 or sw_ysize < 1:
        return 1

    # Copy the selected region.

    return _raster_copy(inRas, sw_xoff, sw_yoff, sw_xsize, sw_ysize, s_band,
                        t_fh, tw_xoff, tw_yoff, tw_xsize, tw_ysize, t_band)


         

def stack_rasters(inRas1, inRas2, outRas, dtype=gdal.GDT_Int32, slantr=False):
    
    
    """
    Stack the intersected extent of £-band composites from MicMac which contain 
    
    RGB and RReNir respectively. Obviously the red band will not be written twice!
    
    Parameters
    ----------
        
    inRas1 : string
            path to RGB image
            
    inRas2 : string
             path to RReNir image
    outRas3 : string
             path to outputted stack
             
    dtype : int 
            gdal datatype e.g. gdal.GDT_Int32 (default)
   """
    
    
    
    rasterList1 = [1,2,3]
    if slantr==True:
        rasterList2 = [1, 2, 3]
        bnds=6
    else:
        
        rasterList2 = [2, 3]
        bnds=5
    
    inDataset1 = gdal.Open(inRas1)
    inDataset2 = gdal.Open(inRas2)
    
    outDataset = _copy_dataset_config(inDataset1, FMT = 'Gtiff', outMap = outRas,
                         dtype = dtype, bands = bnds)
    
    
    
    for band in rasterList1:

        _copy_into( inDataset1, outDataset, s_band = band, t_band = band)        
                    
    for k,band in enumerate(rasterList2):
        _copy_into( inDataset2, outDataset, s_band = band, t_band = k+4)
        
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












    
