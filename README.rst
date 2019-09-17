Pycmac
~~~~~~~~

Installation
~~~~~~~~~~~~~~~~~


A python lib for Micmac and associated geospatial functionality with enhancements and adaptations. 

The lib also facilitates the processing of Micasense multi-spectral imagery to surface reflectance ready for use with MicMac (or indeed others)

All the functionallity of the material in the scripts site (https://github.com/Ciaran1981/Sfm/) is covered here in a more 

compact form via python.


Documentation is found here, including a quick start. 

https://ciaran1981.github.io/pycmac/build/html/index.html

cd into the pycmac folder and type 

.. code-block:: python

    python setup.py install

This will install pycmac and dependencies into a conda environment. Remember to activate it when you use it. 



Dependency installation
~~~~~~~~~~~~~~~~~


**MicMac**

https://micmac.ensg.eu/index.php/Accueil

See MicMac install instructions here:

https://micmac.ensg.eu/index.php/Install

This will usually work. 

.. code-block:: bash

    sudo apt-get install make imagemagick libimage-exiftool-perl exiv2 proj-bin qt5-default
    
    git clone https://github.com/micmacIGN/micmac.git
    
    cd micmac
    
    cmake ..

    make install -j k

**OSSIM**

Install OSSIM via tha ubuntu GIS or equivalent repo 

- Ensure the OSSIM preferences file is on you path, otherwise it will not recognise different projections

- see here https://trac.osgeo.org/ossim/wiki/ossimPreferenceFile