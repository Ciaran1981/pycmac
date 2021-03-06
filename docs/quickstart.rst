.. _quickstart:

Quickstart
==========


Notes
---------

Be sure to assign paths with paths to your own data for the folder (where your images are) and csv variables where appropriate. 


A workflow using the Malt algorithm
-----------------------------------

The following simple example uses the pycmac modules, culminating in the use of the Malt dense matching algorithm to produce a DSM. Micmac has two dense matching implementations (Malt and PIMs), each with various modes and parameters. 

.. code-block:: python

    from pycmac import orientation, dense_match

Perform the relative orientation of images (poses).

.. code-block:: python
	
    folder = path/to/my/folder

    orientation. feature_match(folder, proj="30 +north",  ext="JPG", schnaps=True)

Perform the bundle adjustment with GPS information.

.. code-block:: python

    orientation.bundle_adjust(folder, algo="Fraser", proj="30 +north",
                      ext="JPG", calib="pathtocsv.csv", gpsAcc='1')
                      
Perform the dense matching using the malt algorithm. The args for the dense matching algorithms are largely identical to the MicMac commands (Malt & PIMs), but additional masking, georeferencing and subsetting is carried out.

The final DSM will be copied to a folder named OUTPUT in your working directory for ease of access. This is also the case for the other dense_match functions that produce either DSMs or Orthomosaics. 

.. code-block:: python
                      
    dense_match.malt(folder, proj="30 +north", mode='Ortho', ext="JPG", orientation="Ground_UTM",
             DoOrtho='1',  DefCor='0')
             
Mosaicing can be performed using Tawny or seamline-feathering (enhanced to process multi-band) algorithms native to MicMac or ossim.

The examples below are Tawny and seamline-feathering. 

Please note that seamline-feathering for multi-band imagery (including RGB) the "ms" variable must be specified below. If not, it will return a greyscale mosaic. 


.. code-block:: python

    dense_match.tawny(folder, proj="30 +north", mode='Malt')


    dense_match.feather(folder, proj="ESPG:32360", mode='Malt', ms=['r', 'g', 'b'])
