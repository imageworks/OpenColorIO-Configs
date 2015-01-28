#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ACES OCIO
=========

Usage
-----

Python
******

>>> from aces_ocio.create_aces_config import create_ACES_config
>>> aces_ctl_directory = '/path/to/github/checkout/releases/v1.0.0/transforms/ctl'
>>> config_directory = '/path/to/configuration/dir'
>>> create_ACES_config(aces_ctl_directory, config_directory, 1024, 33, True)

Command Line
************

Using the *create_aces_config* binary:

$ create_aces_config -a '/path/to/github/checkout/releases/v0.7.1/transforms/ctl' -c '/path/to/config/dir' --lutResolution1d 1024 --lutResolution3d 33 --keepTempImages

It is possible to set the following environment variables to avoid passing
the paths to the binary:

- *ACES_OCIO_CTL_DIRECTORY*
- *ACES_OCIO_CONFIGURATION_DIRECTORY*

The above command line call would be done as follows:

$ create_aces_config --lutResolution1d 1024 --lutResolution3d 33 --keepTempImages

Testing the generated configuration is needs the
*ACES_OCIO_CTL_DIRECTORY* environment variable to be set and is done as
follows:

$ tests_aces_config

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