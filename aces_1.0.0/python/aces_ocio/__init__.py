#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ACES OCIO
=========

Usage
-----

Python
******

>>> import sys
>>> sys.path.append("/path/to/script")
>>> import create_aces_config as cac
>>> acesReleaseCTLDir = "/path/to/github/checkout/releases/v0.7.1/transforms/ctl"
>>> configDir = "/path/to/config/dir"
>>> cac.createACESConfig(acesReleaseCTLDir, configDir, 1024, 33, True)

Command Line
************

From the directory with 'create_aces_config.py':

$ python create_aces_config.py -a "/path/to/github/checkout/releases/v0.7.1/transforms/ctl" -c "/path/to/config/dir" --lut_resolution_1d 1024 --lut_resolution_3d 33 --keepTempImages

Build
-----

Mac OS X - Required packages
****************************

OpenColorIO
___________

$ brew install -vd opencolorio --with-python

OpenImageIO
___________

$ brew tap homebrew/science

Optional Dependencies
_____________________

$ brew install -vd libRaw
$ brew install -vd OpenCV
$ brew install -vd openimageio --with-python

CTL
___

$ brew install -vd CTL

OpenColorIO
___________

*ociolutimage* will build with *openimageio* installed.

$ brew uninstall -vd opencolorio
$ brew install -vd opencolorio --with-python
"""

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__major_version__ = '1'
__minor_version__ = '0'
__change_version__ = '0'
__version__ = '.'.join((__major_version__,
                        __minor_version__,
                        __change_version__))