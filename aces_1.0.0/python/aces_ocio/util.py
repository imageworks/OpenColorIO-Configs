#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines various package utilities objects.
"""

import os
import re

import PyOpenColorIO as OCIO

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['ColorSpace',
           'mat44FromMat33',
           'filter_words',
           'files_walker']

#
# Utility classes and functions
#

class ColorSpace:
    """
    A container for data needed to define an OCIO 'Color Space'
    """

    def __init__(self,
                 name,
                 description=None,
                 bitDepth=OCIO.Constants.BIT_DEPTH_F32,
                 equalityGroup=None,
                 family=None,
                 isData=False,
                 toReferenceTransforms=[],
                 fromReferenceTransforms=[],
                 allocationType=OCIO.Constants.ALLOCATION_UNIFORM,
                 allocationVars=[0.0, 1.0]):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        self.name = name
        self.bitDepth = bitDepth
        self.description = description
        self.equalityGroup = equalityGroup
        self.family = family
        self.isData = isData
        self.toReferenceTransforms = toReferenceTransforms
        self.fromReferenceTransforms = fromReferenceTransforms
        self.allocationType = allocationType
        self.allocationVars = allocationVars


def mat44FromMat33(mat33):
    """
    Creates a 4x4 matrix from given 3x3 matrix.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    return [mat33[0], mat33[1], mat33[2], 0.0,
            mat33[3], mat33[4], mat33[5], 0.0,
            mat33[6], mat33[7], mat33[8], 0.0,
            0, 0, 0, 1.0]


def filter_words(words, filters_in=None, filters_out=None, flags=0):
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    filtered_words = []
    for word in words:
        if filters_in:
            filter_matched = False
            for filter in filters_in:
                if re.search(filter, word, flags):
                    filter_matched = True
                    break
            if not filter_matched:
                continue

        if filters_out:
            filter_matched = False
            for filter in filters_out:
                if re.search(filter, word, flags):
                    filter_matched = True
                    break
            if filter_matched:
                continue
        filtered_words.append(word)
    return filtered_words


def files_walker(directory, filters_in=None, filters_out=None, flags=0):
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    for parent_directory, directories, files in os.walk(directory,
                                                        topdown=False,
                                                        followlinks=True):
        for file in files:
            path = os.path.join(parent_directory, file)
            if os.path.isfile(path):
                if not filter_words((path,), filters_in, filters_out, flags):
                    continue

                yield path
