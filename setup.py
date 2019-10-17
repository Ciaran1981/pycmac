# -*- coding: utf-8 -*-
"""
Created on Wed May 15 12:16:49 2019

@author: ciaran
"""

# -*- coding: utf-8 -*-
"""Alternations to setup.py based on Brandon Rhodes' conda setup.py:
https://github.com/brandon-rhodes/conda-install"""
from setuptools import setup, find_packages
from setuptools.command.install import install 
from io import open
import subprocess


with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


descript = ('A python lib for Micmac and associated geospatial functionality with enhancements and adaptations. \nThe lib also facilitates the processing of Micasense multi-spectral imagery to surface reflectance ready for use with MicMac (or indeed others)')

#class CondaInstall(install):
#    def run(self):
#        try:
#
##            subprocess.check_call(['conda', 'env', 'create', '-n', 'pycmac'])
##            subprocess.check_call(['conda', 'activate', 'pycmac'])
##            packages = open('conda_modules.txt').read().splitlines()
##            command = ['conda', 'install', '-y']
##            command.extend(packages)
#            command = ['conda', 'env', 'create', '-f', 'pycmac_env.yml']
#
#            subprocess.check_call(command)
#            #install.do_egg_install(self)
#        except subprocess.CalledProcessError:
#            print("Conda install failed: do you have Anaconda/miniconda installed and on your PATH?")
#


setup(
    name="pycmac",
    version="0.1",
    packages=find_packages(),
#    install_requires=['pyzbar', 'pysolar', 'mapboxgl', 'pyexiftool',
#
                      #'git+https://github.com/smarnach/pyexiftool.git#egg=pyexiftoolpy',
#                      'imageio-ffmpeg', 'open3d'],
    
    #open('requirements.txt').read().splitlines(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
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


