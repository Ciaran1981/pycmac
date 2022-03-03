Pycmac
~~~~~~~~

Installation
~~~~~~~~~~~~~~~~~


A python lib for Micmac and associated geospatial functionality, for the conveneince of use with python.

As well a grey-scale and RGB processing pycmac also facilitates the processing of multi-spectral imagery.
 
Both MicaSense (including surface reflectance processing) and Slant view imagery are currently supported. 

Documentation is found here, including a quick start. 

https://ciaran1981.github.io/pycmac/build/html/index.html

Clone the repository and cd into folder then....

.. code-block:: bash

    conda env create -f pycmac_env.yml

This will install pycmac and dependencies into a conda environment. Remember to activate it when you use it by...

.. code-block:: bash
    
    conda activate pycmac

I have also now created a docker container, if you do not wish to use the above options or compile micmac seperately.

.. code-block:: bash

    docker build git://github.com/Ciaran1981/micmac-docker

If you are using a GNU/Linux OS, this shell script will do the whole install including micmac for you.

.. code-block:: bash

   chmod +x pycmac_setup.sh
   
   pycmac_setup.sh

Micamac & dependency installation
~~~~~~~~~~~~~~~~~

**MicMac**

https://micmac.ensg.eu/index.php/Accueil

See MicMac install instructions here:

https://micmac.ensg.eu/index.php/Install

This will usually work. If you don't want QT5 menus/GUIs omit this from the cmake line below. 

.. code-block:: bash

    sudo apt-get install make imagemagick libimage-exiftool-perl exiv2 proj-bin qt5-default
    
    git clone https://github.com/micmacIGN/micmac.git
    
    cd micmac
    
    cmake WITH_QT5=1 ..

    make install -j k

if compiling with QT (handy for GCPs, delineating things on photos) add the following to your bashrc if the GUI menus don't work

.. code-block:: bash

    export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms


Remember to add the micmac bin dir to your path (.bashrc or .bash_profile)

