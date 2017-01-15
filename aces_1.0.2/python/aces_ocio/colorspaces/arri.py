#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for *ARRI* colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import math
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.utilities import ColorSpace, mat44_from_mat33, sanitize

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['create_log_c',
           'create_colorspaces']


def create_log_c(gamut,
                 transfer_function,
                 exposure_index,
                 lut_directory,
                 lut_resolution_1d,
                 aliases):
    """
    Creates colorspace covering the conversion from LogC to ACES, with various transfer 
    functions and encoding gamuts covered

    Parameters
    ----------
    gamut : str
        The name of the encoding gamut to use.
    transfer_function : str
        The name of the transfer function to use
    exposure_index : str
        The exposure index to use
    lut_directory : str or unicode 
        The directory to use when generating LUTs
    lut_resolution_1d : int
        The resolution of generated 1D LUTs
    aliases : list of str
        Aliases for this colorspace

    Returns
    -------
    ColorSpace
         A ColorSpace container class referencing the LUTs, matrices and identifying
         information for the requested colorspace.
    """

    name = '%s (EI%s) - %s' % (transfer_function, exposure_index, gamut)
    if transfer_function == '':
        name = 'Linear - ARRI %s' % gamut
    if gamut == '':
        name = 'Curve - %s (EI%s)' % (transfer_function, exposure_index)

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/ARRI'
    cs.is_data = False

    if gamut and transfer_function:
        cs.aces_transform_id = (
            'IDT.ARRI.Alexa-v3-logC-EI%s.a1.v1' % exposure_index)

    # A linear space needs allocation variables.
    if transfer_function == '':
        cs.allocation_type = ocio.Constants.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    IDT_maker_version = '0.08'

    nominal_EI = 400
    black_signal = 0.003907
    mid_gray_signal = 0.01
    encoding_gain = 0.256598
    encoding_offset = 0.391007

    def gain_for_EI(EI):
        return (math.log(EI / nominal_EI) / math.log(2) * (
            0.89 - 1) / 3 + 1) * encoding_gain

    def log_c_inverse_parameters_for_EI(EI):
        cut = 1 / 9
        slope = 1 / (cut * math.log(10))
        offset = math.log10(cut) - slope * cut
        gain = EI / nominal_EI
        gray = mid_gray_signal / gain
        # The higher the EI, the lower the gamma.
        enc_gain = gain_for_EI(EI)
        enc_offset = encoding_offset
        for i in range(0, 3):
            nz = ((95 / 1023 - enc_offset) / enc_gain - offset) / slope
            enc_offset = encoding_offset - math.log10(1 + nz) * enc_gain

        a = 1 / gray
        b = nz - black_signal / gray
        e = slope * a * enc_gain
        f = enc_gain * (slope * b + offset) + enc_offset

        # Ensuring we can return relative exposure.
        s = 4 / (0.18 * EI)
        t = black_signal
        b += a * t
        a *= s
        f += e * t
        e *= s

        return {'a': a,
                'b': b,
                'cut': (cut - b) / a,
                'c': enc_gain,
                'd': enc_offset,
                'e': e,
                'f': f}

    def normalized_log_c_to_linear(code_value, exposure_index):
        p = log_c_inverse_parameters_for_EI(exposure_index)
        breakpoint = p['e'] * p['cut'] + p['f']
        if code_value > breakpoint:
            linear = ((pow(10, (code_value - p['d']) / p['c']) -
                       p['b']) / p['a'])
        else:
            linear = (code_value - p['f']) / p['e']
        return linear

    cs.to_reference_transforms = []

    if transfer_function == 'V3 LogC':
        data = array.array('f', '\0' * lut_resolution_1d * 4)
        for c in range(lut_resolution_1d):
            data[c] = normalized_log_c_to_linear(c / (lut_resolution_1d - 1),
                                                 int(exposure_index))

        lut = '%s_to_linear.spi1d' % (
            '%s_%s' % (transfer_function, exposure_index))

        lut = sanitize(lut)

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

    if gamut == 'Wide Gamut':
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33([0.680206, 0.236137, 0.083658,
                                        0.085415, 1.017471, -0.102886,
                                        0.002057, -0.062563, 1.060506]),
            'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs


def create_colorspaces(lut_directory, lut_resolution_1d):
    """
    Generates the colorspace conversions.

    Parameters
    ----------
    lut_directory : str or unicode 
        The directory to use when generating LUTs
    lut_resolution_1d : int
        The resolution of generated 1D LUTs

    Returns
    -------
    list
         A list of colorspaces for ARRI cameras and encodings 
    """

    colorspaces = []

    transfer_function = 'V3 LogC'
    gamut = 'Wide Gamut'

    # EIs = [160, 200, 250, 320, 400, 500, 640, 800,
    # 1000, 1280, 1600, 2000, 2560, 3200]
    EIs = [160, 200, 250, 320, 400, 500, 640, 800,
           1000, 1280, 1600, 2000, 2560, 3200]
    default_EI = 800

    # Full Conversion
    for EI in EIs:
        log_c_EI_full = create_log_c(
            gamut,
            transfer_function,
            EI,
            lut_directory,
            lut_resolution_1d,
            ['%sei%s_%s' % ('logc3', str(EI), 'arriwide')])
        colorspaces.append(log_c_EI_full)

    # Linearization Only
    for EI in [800]:
        log_c_EI_linearization = create_log_c(
            '',
            transfer_function,
            EI,
            lut_directory,
            lut_resolution_1d,
            ['crv_%sei%s' % ('logc3', str(EI))])
        colorspaces.append(log_c_EI_linearization)

    # Primaries Only
    log_c_EI_primaries = create_log_c(
        gamut,
        '',
        default_EI,
        lut_directory,
        lut_resolution_1d,
        ['%s_%s' % ('lin', 'arriwide')])
    colorspaces.append(log_c_EI_primaries)

    return colorspaces
