#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for *Sony* colorspaces conversions and transfer functions.
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

__all__ = ['create_s_log',
           'create_colorspaces']


def create_s_log(gamut,
                 transfer_function,
                 lut_directory,
                 lut_resolution_1d,
                 aliases):
    """
    Creates colorspace covering the conversion from Sony spaces to ACES, with
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

    name = '%s - %s' % (transfer_function, gamut)
    if transfer_function == '':
        name = 'Linear - %s' % gamut
    if gamut == '':
        name = 'Curve - %s' % transfer_function

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/Sony'
    cs.is_data = False

    if gamut and transfer_function:
        cs.aces_transform_id = 'IDT.Sony.%s_%s_10i.a1.v1' % (
            transfer_function.replace('-', ''),
            gamut.replace('-', '').replace(' ', '_'))

    # A linear space needs allocation variables.
    if transfer_function == '':
        cs.allocation_type = ocio.Constants.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    def s_log1_to_linear(s_log):
        b = 64.
        ab = 90.
        w = 940.

        if s_log >= ab:
            linear = ((pow(10.,
                           (((s_log - b) /
                             (w - b) - 0.616596 - 0.03) / 0.432699)) -
                       0.037584) * 0.9)
        else:
            linear = (((s_log - b) / (
                w - b) - 0.030001222851889303) / 5.) * 0.9
        return linear

    def s_log2_to_linear(s_log):
        b = 64.
        ab = 90.
        w = 940.

        if s_log >= ab:
            linear = ((219. * (pow(10.,
                                   (((s_log - b) /
                                     (w - b) - 0.616596 - 0.03) / 0.432699)) -
                               0.037584) / 155.) * 0.9)
        else:
            linear = (((s_log - b) / (
                w - b) - 0.030001222851889303) / 3.53881278538813) * 0.9
        return linear

    def s_log3_to_linear(code_value):
        if code_value >= 171.2102946929:
            linear = (pow(10, ((code_value - 420) / 261.5)) *
                      (0.18 + 0.01) - 0.01)
        else:
            linear = (code_value - 95) * 0.01125000 / (171.2102946929 - 95)

        return linear

    cs.to_reference_transforms = []

    if transfer_function == 'S-Log1':
        data = array.array('f', '\0' * lut_resolution_1d * 4)
        for c in range(lut_resolution_1d):
            data[c] = s_log1_to_linear(1023 * c / (lut_resolution_1d - 1))

        lut = '%s_to_linear.spi1d' % transfer_function
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
    elif transfer_function == 'S-Log2':
        data = array.array('f', '\0' * lut_resolution_1d * 4)
        for c in range(lut_resolution_1d):
            data[c] = s_log2_to_linear(1023 * c / (lut_resolution_1d - 1))

        lut = '%s_to_linear.spi1d' % transfer_function
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
    elif transfer_function == 'S-Log3':
        data = array.array('f', '\0' * lut_resolution_1d * 4)
        for c in range(lut_resolution_1d):
            data[c] = s_log3_to_linear(1023 * c / (lut_resolution_1d - 1))

        lut = '%s_to_linear.spi1d' % transfer_function
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

    if gamut == 'S-Gamut':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(
                [0.754338638, 0.133697046, 0.111968437,
                 0.021198141, 1.005410934, -0.026610548,
                 -0.009756991, 0.004508563, 1.005253201]),
            'direction': 'forward'})
    elif gamut == 'S-Gamut Daylight':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(
                [0.8764457030, 0.0145411681, 0.1090131290,
                 0.0774075345, 0.9529571767, -0.0303647111,
                 0.0573564351, -0.1151066335, 1.0577501984]),
            'direction': 'forward'})
    elif gamut == 'S-Gamut Tungsten':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(
                [1.0110238740, -0.1362526051, 0.1252287310,
                 0.1011994504, 0.9562196265, -0.0574190769,
                 0.0600766530, -0.1010185315, 1.0409418785]),
            'direction': 'forward'})
    elif gamut == 'S-Gamut3.Cine':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(
                [0.6387886672, 0.2723514337, 0.0888598992,
                 -0.0039159061, 1.0880732308, -0.0841573249,
                 -0.0299072021, -0.0264325799, 1.0563397820]),
            'direction': 'forward'})
    elif gamut == 'S-Gamut3':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(
                [0.7529825954, 0.1433702162, 0.1036471884,
                 0.0217076974, 1.0153188355, -0.0370265329,
                 -0.0094160528, 0.0033704179, 1.0060456349]),
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
         A list of colorspaces for Sony cameras and encodings.
    """

    colorspaces = []

    # *S-Log1*
    s_log1_s_gamut = create_s_log(
        'S-Gamut',
        'S-Log1',
        lut_directory,
        lut_resolution_1d,
        ['slog1_sgamut'])
    colorspaces.append(s_log1_s_gamut)

    # *S-Log2*
    s_log2_s_gamut = create_s_log(
        'S-Gamut',
        'S-Log2',
        lut_directory,
        lut_resolution_1d,
        ['slog2_sgamut'])
    colorspaces.append(s_log2_s_gamut)

    s_log2_s_gamut_daylight = create_s_log(
        'S-Gamut Daylight',
        'S-Log2',
        lut_directory,
        lut_resolution_1d,
        ['slog2_sgamutday'])
    colorspaces.append(s_log2_s_gamut_daylight)

    s_log2_s_gamut_tungsten = create_s_log(
        'S-Gamut Tungsten',
        'S-Log2',
        lut_directory,
        lut_resolution_1d,
        ['slog2_sgamuttung'])
    colorspaces.append(s_log2_s_gamut_tungsten)

    # *S-Log3*
    s_log3_s_gamut3Cine = create_s_log(
        'S-Gamut3.Cine',
        'S-Log3',
        lut_directory,
        lut_resolution_1d,
        ['slog3_sgamutcine'])
    colorspaces.append(s_log3_s_gamut3Cine)

    s_log3_s_gamut3 = create_s_log(
        'S-Gamut3',
        'S-Log3',
        lut_directory,
        lut_resolution_1d,
        ['slog3_sgamut3'])
    colorspaces.append(s_log3_s_gamut3)

    # Linearization Only
    s_log1 = create_s_log(
        '',
        'S-Log1',
        lut_directory,
        lut_resolution_1d,
        ['crv_slog1'])
    colorspaces.append(s_log1)

    s_log2 = create_s_log(
        '',
        'S-Log2',
        lut_directory,
        lut_resolution_1d,
        ['crv_slog2'])
    colorspaces.append(s_log2)

    s_log3 = create_s_log(
        '',
        'S-Log3',
        lut_directory,
        lut_resolution_1d,
        ['crv_slog3'])
    colorspaces.append(s_log3)

    # Primaries Only
    s_gamut = create_s_log(
        'S-Gamut',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_sgamut'])
    colorspaces.append(s_gamut)

    s_gamut_daylight = create_s_log(
        'S-Gamut Daylight',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_sgamutday'])
    colorspaces.append(s_gamut_daylight)

    s_gamut_tungsten = create_s_log(
        'S-Gamut Tungsten',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_sgamuttung'])
    colorspaces.append(s_gamut_tungsten)

    s_gamut3Cine = create_s_log(
        'S-Gamut3.Cine',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_sgamut3cine'])
    colorspaces.append(s_gamut3Cine)

    s_gamut3 = create_s_log(
        'S-Gamut3',
        '',
        lut_directory,
        lut_resolution_1d,
        ['lin_sgamut3'])
    colorspaces.append(s_gamut3)

    return colorspaces
