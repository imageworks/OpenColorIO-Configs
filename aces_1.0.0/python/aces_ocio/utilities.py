#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines various package utilities objects.
"""

from __future__ import division

import os
import re
from collections import OrderedDict

import PyOpenColorIO as OCIO

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['ColorSpace',
           'mat44_from_mat33',
           'filter_words',
           'files_walker',
           'replace',
           'sanitize',
           'compact']


class ColorSpace(object):
    """
    A container for data needed to define an *OCIO* *ColorSpace*.
    """

    def __init__(self,
                 name,
                 aliases=[],
                 description=None,
                 bit_depth=OCIO.Constants.BIT_DEPTH_F32,
                 equality_group=None,
                 family=None,
                 is_data=False,
                 to_reference_transforms=[],
                 from_reference_transforms=[],
                 allocation_type=OCIO.Constants.ALLOCATION_UNIFORM,
                 allocation_vars=[0, 1]):
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
        self.aliases = []
        self.bit_depth = bit_depth
        self.description = description
        self.equality_group = equality_group
        self.family = family
        self.is_data = is_data
        self.to_reference_transforms = to_reference_transforms
        self.from_reference_transforms = from_reference_transforms
        self.allocation_type = allocation_type
        self.allocation_vars = allocation_vars


def mat44_from_mat33(mat33):
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

    return [mat33[0], mat33[1], mat33[2], 0,
            mat33[3], mat33[4], mat33[5], 0,
            mat33[6], mat33[7], mat33[8], 0,
            0, 0, 0, 1]


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


def replace(string, data):
    """
    Replaces the data occurrences in the string.

    Parameters
    ----------
    string : str or unicode
        String to manipulate.
    data : dict
        Replacement occurrences.

    Returns
    -------
    unicode
        Manipulated string.

    Examples
    --------
    >>> patterns = {"John" : "Luke",
    ...             "Jane" : "Anakin",
    ...             "Doe" : "Skywalker",
    ...             "Z6PO" : "R2D2"}
    >>> data = "Users are: John Doe, Jane Doe, Z6PO."
    >>> replace(data,patterns )
    u'Users are: Luke Skywalker, Anakin Skywalker, R2D2.'
    """

    for old, new in data.iteritems():
        string = string.replace(old, new)
    return string


def sanitize(path):
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

    return replace(path, {' ': '_', ')': '_', '(': '_'})


def compact(string):
    """
    Removes blanks, underscores, dashes and parentheses.

    Parameters
    ----------
    string : str or unicode
        String to compact.

    Returns
    -------
    str or unicode
         A compact version of that string.
    """

    return replace(string.lower(),
                   OrderedDict(((' ', '_'),
                                ('(', '_'),
                                (')', '_'),
                                ('.', '_'),
                                ('-', '_'),
                                ('___', '_'),
                                ('__', '_'),
                                ('_', ''))))
