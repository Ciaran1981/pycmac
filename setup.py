# -*- coding: utf-8 -*-
"""
Created on Wed May 15 12:16:49 2019

@author: ciaran
"""

# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from setuptools.command.install import install 
from io import open


with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


descript = ('A python lib for Micmac and associated geospatial functionality with enhancements and adaptations. \nThe lib also facilitates the processing of Micasense multi-spectral imagery to surface reflectance ready for use with MicMac (or indeed others)')



setup(
    name="pycmac",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,# {
        # If any package contains *.txt or *.rst files, include them:
        # And include any *.msg files found in the 'hello' package, too:
    #},
    classifiers=[
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
#          'Programming Language :: Python :: 3.4',
#          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: GIS',
          'Topic :: Utilities'],
    # metadata for upload to PyPI
    # zip_safe = True,
    author="Ciaran Robb",
    description=descript,
    long_description=long_description,
    license='GPLv3+',
    url="https://github.com/Ciaran1981/Sfm/pycmac",   # project home page, if any
    download_url="https://github.com/Ciaran1981/Sfm/pycmac"
    # could also include long_description, download_url, classifiers, etc.
)


