#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for *RED* colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.utilities import ColorSpace, mat44_from_mat33

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2016 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['create_red_log_film',
           'create_colorspaces']


def create_red_log_film(gamut,
                        transfer_function,
                        lut_directory,
                        lut_resolution_1d,
                        aliases=None):
    """
    Creates colorspace covering the conversion from RED spaces to ACES, with
    various transfer functions and encoding gamuts covered.

    Parameters
    ----------
    gamut : str
        The name of the encoding gamut to use.
    transfer_function : str
        The name of the transfer function to use.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1d : int
        The resolution of generated 1D LUTs.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A ColorSpace container class referencing the LUTs, matrices and
         identifying information for the requested colorspace.
    """

    if aliases is None:
        aliases = []

    name = '%s - %s' % (transfer_function, gamut)
    if transfer_function == '':
        name = 'Linear - %s' % gamut
    if gamut == '':
        name = 'Curve - %s' % transfer_function

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/RED'
    cs.is_data = False

    # A linear space needs allocation variables
    if transfer_function == '':
        cs.allocation_type = ocio.Constants.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    def cineon_to_linear(code_value):
        n_gamma = 0.6
        black_point = 95
        white_point = 685
        code_value_to_density = 0.002

        black_linear = pow(10, (black_point - white_point) * (
            code_value_to_density / n_gamma))
        code_linear = pow(10, (code_value - white_point) * (
            code_value_to_density / n_gamma))

        return (code_linear - black_linear) / (1 - black_linear)

    def log3g10_to_linear(code_value):
        a = 0.224282
        b = 155.975327
        c = 0.01

        normalized_log = code_value / 1023.0

        mirror = 1.0
        if normalized_log < 0.0:
            mirror = -1.0
            normalized_log = -normalized_log

        linear = (pow(10.0, normalized_log / a) - 1) / b
        linear = linear * mirror - c

        return linear

    cs.to_reference_transforms = []

    if transfer_function:
        if transfer_function == 'REDlogFilm':
            lut_name = "CineonLog"
            data = array.array('f', '\0' * lut_resolution_1d * 4)
            for c in range(lut_resolution_1d):
                data[c] = cineon_to_linear(1023 * c / (lut_resolution_1d - 1))
        elif transfer_function == 'REDLog3G10':
            lut_name = "REDLog3G10"
            data = array.array('f', '\0' * lut_resolution_1d * 4)
            for c in range(lut_resolution_1d):
                data[c] = log3g10_to_linear(1023 * c / (lut_resolution_1d - 1))

        lut = '%s_to_linear.spi1d' % lut_name
        genlut.write_SPI_1d(
            os.path.join(lut_directory, lut),
            0,
            1,
            data,
            lut_resolution_1d,
            1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'})

    if gamut == 'DRAGONcolor':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.532279, 0.376648, 0.091073,
                                        0.046344, 0.974513, -0.020860,
                                        -0.053976, -0.000320, 1.054267]),
            'direction': 'forward'})
    elif gamut == 'DRAGONcolor2':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.468452, 0.331484, 0.200064,
                                        0.040787, 0.857658, 0.101553,
                                        -0.047504, -0.000282, 1.047756]),
            'direction': 'forward'})
    elif gamut == 'REDcolor':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.451464, 0.388498, 0.160038,
                                        0.062716, 0.866790, 0.070491,
                                        -0.017541, 0.086921, 0.930590]),
            'direction': 'forward'})
    elif gamut == 'REDcolor2':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.480997, 0.402289, 0.116714,
                                        -0.004938, 1.000154, 0.004781,
                                        -0.105257, 0.025320, 1.079907]),
            'direction': 'forward'})
    elif gamut == 'REDcolor3':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.512136, 0.360370, 0.127494,
                                        0.070377, 0.903884, 0.025737,
                                        -0.020824, 0.017671, 1.003123]),
            'direction': 'forward'})
    elif gamut == 'REDcolor4':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.474202, 0.333677, 0.192121,
                                        0.065164, 0.836932, 0.097901,
                                        -0.019281, 0.016362, 1.002889]),
            'direction': 'forward'})
    elif gamut == 'REDWideGamutRGB':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.785043, 0.083844, 0.131118,
                                        0.023172, 1.087892, -0.111055,
                                        -0.073769, -0.314639, 1.388537]),
            'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs


def create_colorspaces(lut_directory, lut_resolution_1d):
    """
    Generates the colorspace conversions.

    Parameters
    ----------
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1d : int
        The resolution of generated 1D LUTs.

    Returns
    -------
    list
         A list of colorspaces for RED cameras and encodings.
    """

    colorspaces = []

    # Full conversion
    red_log_film_dragon = create_red_log_film(
        'DRAGONcolor',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_dgn'])
    colorspaces.append(red_log_film_dragon)

    red_log_film_dragon2 = create_red_log_film(
        'DRAGONcolor2',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_dgn2'])
    colorspaces.append(red_log_film_dragon2)

    red_log_film_color = create_red_log_film(
        'REDcolor',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_rc'])
    colorspaces.append(red_log_film_color)

    red_log_film_color2 = create_red_log_film(
        'REDcolor2',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_rc2'])
    colorspaces.append(red_log_film_color2)

    red_log_film_color3 = create_red_log_film(
        'REDcolor3',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_rc3'])
    colorspaces.append(red_log_film_color3)

    red_log_film_color4 = create_red_log_film(
        'REDcolor4',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['rlf_rc4'])
    colorspaces.append(red_log_film_color4)

    red_log_film_color5 = create_red_log_film(
        'REDWideGamutRGB',
        'REDLog3G10',
        lut_directory,
        lut_resolution_1d,
        ['rl3g10_rwg'])
    colorspaces.append(red_log_film_color5)

    # Linearization only
    red_log_film = create_red_log_film(
        '',
        'REDlogFilm',
        lut_directory,
        lut_resolution_1d,
        ['crv_rlf'])
    colorspaces.append(red_log_film)

    red_log_film2 = create_red_log_film(
        '',
        'REDLog3G10',
        lut_directory,
        lut_resolution_1d,
        ['crv_rl3g10'])
    colorspaces.append(red_log_film2)

    # Primaries only
    red_dragon = create_red_log_film(
        'DRAGONcolor',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_dgn'])
    colorspaces.append(red_dragon)

    red_dragon2 = create_red_log_film(
        'DRAGONcolor2',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_dgn2'])
    colorspaces.append(red_dragon2)

    red_color = create_red_log_film(
        'REDcolor',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_rc'])
    colorspaces.append(red_color)

    red_color2 = create_red_log_film(
        'REDcolor2',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_rc2'])
    colorspaces.append(red_color2)

    red_color3 = create_red_log_film(
        'REDcolor3',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_rc3'])
    colorspaces.append(red_color3)

    red_color4 = create_red_log_film(
        'REDcolor4',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_rc4'])
    colorspaces.append(red_color4)

    red_color5 = create_red_log_film(
        'REDWideGamutRGB',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_rwg'])
    colorspaces.append(red_color5)

    return colorspaces
