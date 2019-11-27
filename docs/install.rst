Pycmac
~~~~~~~~

Installation
~~~~~~~~~~~~~~~~~

cd into the pycmac folder and type 

.. code-block:: bash

    conda env create -f pycmac_env.yml

This will install pycmac and dependencies into a conda environment. Remember to activate it when you use it via:

.. code-block:: bash

    conda activate pycmac



Dependency installation
~~~~~~~~~~~~~~~~~~~~~~~~

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

Remember to add the micmac bin dir to your path (.bashrc or .bash_profile)

**OSSIM**

Install OSSIM via tha ubuntu GIS or equivalent repo 

- Ensure the OSSIM preferences file is on you path, otherwise it will not recognise different projections

- see here https://trac.osgeo.org/ossim/wiki/ossimPreferenceFile
