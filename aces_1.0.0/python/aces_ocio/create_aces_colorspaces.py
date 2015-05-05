#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for *ACES* colorspaces conversions and transfer functions.
"""

from __future__ import division

import math
import numpy
import os
import pprint
import string
import shutil

import PyOpenColorIO as ocio

from aces_ocio.generate_lut import (
    generate_1d_LUT_from_CTL,
    generate_3d_LUT_from_CTL,
    write_SPI_1d)
from aces_ocio.utilities import (
    ColorSpace,
    mat44_from_mat33,
    sanitize,
    compact)


__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['ACES_AP1_TO_AP0',
           'ACES_AP0_TO_XYZ',
           'create_ACES',
           'create_ACEScc',
           'create_ACESproxy',
           'create_ACEScg',
           'create_ADX',
           'create_ACES_LMT',
           'create_ACES_RRT_plus_ODT',
           'create_generic_log',
           'create_LMTs',
           'create_ODTs',
           'get_transform_info',
           'get_ODTs_info',
           'get_LMTs_info',
           'create_colorspaces']

# Matrix converting *ACES AP1* primaries to *ACES AP0*.
ACES_AP1_TO_AP0 = [0.6954522414, 0.1406786965, 0.1638690622,
                   0.0447945634, 0.8596711185, 0.0955343182,
                   -0.0055258826, 0.0040252103, 1.0015006723]

# Matrix converting *ACES AP0* primaries to *ACES AP1*.
ACES_AP0_TO_AP1 = [1.4514393161, -0.2365107469, -0.2149285693,
                   -0.0765537734, 1.1762296998, -0.0996759264,
                   0.0083161484, -0.0060324498, 0.9977163014]

# Matrix converting *ACES AP0* primaries to *XYZ*.
ACES_AP0_TO_XYZ = [0.9525523959, 0.0000000000, 0.0000936786,
                   0.3439664498, 0.7281660966, -0.0721325464,
                   0.0000000000, 0.0000000000, 1.0088251844]

# Matrix converting *ACES AP0* primaries to *XYZ*.
ACES_XYZ_TO_AP0 = [1.0498110175, 0.0000000000, -0.0000974845,
                   -0.4959030231, 1.3733130458, 0.0982400361,
                   0.0000000000, 0.0000000000, 0.9912520182]


def create_ACES():
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

    # Defining the reference colorspace.
    aces2065_1 = ColorSpace('ACES2065-1')
    aces2065_1.description = (
        'The Academy Color Encoding System reference color space')
    aces2065_1.equality_group = ''
    aces2065_1.aliases = ["lin_ap0", "aces"]
    aces2065_1.family = 'ACES'
    aces2065_1.is_data = False
    aces2065_1.allocation_type = ocio.Constants.ALLOCATION_LG2
    aces2065_1.allocation_vars = [-8, 5, 0.00390625]

    return aces2065_1


def create_ACEScc(aces_ctl_directory,
                  lut_directory,
                  lut_resolution_1d,
                  cleanup,
                  name='ACEScc',
                  min_value=0,
                  max_value=1,
                  input_scale=1):
    """
    Creates the *ACEScc* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *ACEScc* colorspace.
    """

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = ["acescc_ap1"]
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False
    cs.allocation_type = ocio.Constants.ALLOCATION_UNIFORM
    cs.allocation_vars = [min_value, max_value]

    ctls = [os.path.join(aces_ctl_directory,
                         'ACEScc',
                         'ACEScsc.ACEScc_to_ACES.a1.0.0.ctl')]
    lut = '%s_to_linear.spi1d' % name

    lut = sanitize(lut)

    generate_1d_LUT_from_CTL(
        os.path.join(lut_directory, lut),
        ctls,
        lut_resolution_1d,
        'float',
        input_scale,
        1,
        {'transferFunctionOnly':1},
        cleanup,
        aces_ctl_directory,
        min_value,
        max_value,
        1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    # *AP1* primaries to *AP0* primaries.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs


def create_ACESproxy(aces_ctl_directory,
                     lut_directory,
                     lut_resolution_1d,
                     cleanup,
                     name='ACESproxy'):
    """
    Creates the *ACESproxy* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *ACESproxy* colorspace.
    """

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = ["acesproxy_ap1"]
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False

    ctls = [os.path.join(aces_ctl_directory,
                         'ACESproxy',
                         'ACEScsc.ACESproxy10i_to_ACES.a1.0.0.ctl'),
                          # This transform gets back to the *AP1* primaries.
                          # Useful as the 1d LUT is only covering the transfer function.
                          # The primaries switch is covered by the matrix below:
                          os.path.join(aces_ctl_directory,
                                       'ACEScg',
                                       'ACEScsc.ACES_to_ACEScg.a1.0.0.ctl')]
    lut = '%s_to_linear.spi1d' % name

    lut = sanitize(lut)

    generate_1d_LUT_from_CTL(
        os.path.join(lut_directory, lut),
        ctls,
        lut_resolution_1d,
        'uint16',
        64,
        1,
        {},
        cleanup,
        aces_ctl_directory,
        0,
        1,
        1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    # *AP1* primaries to *AP0* primaries.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# *ACEScg*
# -------------------------------------------------------------------------
def create_ACEScg(aces_ctl_directory,
                  lut_directory,
                  lut_resolution_1d,
                  cleanup,
                  name='ACEScg'):
    """
    Creates the *ACEScg* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *ACEScg* colorspace.
    """

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = ["lin_ap1"]
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False
    cs.allocation_type = ocio.Constants.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]

    cs.to_reference_transforms = []

    # *AP1* primaries to *AP0* primaries.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# *ADX*
# -------------------------------------------------------------------------
def create_ADX(lut_directory,
               lut_resolution_1d,
               bit_depth=10,
               name='ADX'):
    """
    Creates the *ADX* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *ADX* colorspace.
    """

    name = '%s%s' % (name, bit_depth)
    cs = ColorSpace(name)
    cs.description = '%s color space - used for film scans' % name
    cs.aliases = ["adx%s" % str(bit_depth)]
    cs.equality_group = ''
    cs.family = 'ADX'
    cs.is_data = False

    if bit_depth == 10:
        cs.bit_depth = ocio.Constants.BIT_DEPTH_UINT10
        ADX_to_CDD = [1023 / 500, 0, 0, 0,
                      0, 1023 / 500, 0, 0,
                      0, 0, 1023 / 500, 0,
                      0, 0, 0, 1]
        offset = [-95 / 500, -95 / 500, -95 / 500, 0]
    elif bit_depth == 16:
        cs.bit_depth = ocio.Constants.BIT_DEPTH_UINT16
        ADX_to_CDD = [65535 / 8000, 0, 0, 0,
                      0, 65535 / 8000, 0, 0,
                      0, 0, 65535 / 8000, 0,
                      0, 0, 0, 1]
        offset = [-1520 / 8000, -1520 / 8000, -1520 / 8000, 0]

    cs.to_reference_transforms = []

    # Converting from *ADX* to *Channel-Dependent Density*.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': ADX_to_CDD,
        'offset': offset,
        'direction': 'forward'})

    # Convert from Channel-Dependent Density to Channel-Independent Density
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': [0.75573, 0.22197, 0.02230, 0,
                   0.05901, 0.96928, -0.02829, 0,
                   0.16134, 0.07406, 0.76460, 0,
                   0, 0, 0, 1],
        'direction': 'forward'})

    # Copied from *Alex Fry*'s *adx_cid_to_rle.py*
    def create_CID_to_RLE_LUT():

        def interpolate_1D(x, xp, fp):
            return numpy.interp(x, xp, fp)

        LUT_1D_xp = [-0.190000000000000,
                     0.010000000000000,
                     0.028000000000000,
                     0.054000000000000,
                     0.095000000000000,
                     0.145000000000000,
                     0.220000000000000,
                     0.300000000000000,
                     0.400000000000000,
                     0.500000000000000,
                     0.600000000000000]

        LUT_1D_fp = [-6.000000000000000,
                     -2.721718645000000,
                     -2.521718645000000,
                     -2.321718645000000,
                     -2.121718645000000,
                     -1.921718645000000,
                     -1.721718645000000,
                     -1.521718645000000,
                     -1.321718645000000,
                     -1.121718645000000,
                     -0.926545676714876]

        REF_PT = ((7120 - 1520) / 8000 * (100 / 55) -
                  math.log(0.18, 10))

        def cid_to_rle(x):
            if x <= 0.6:
                return interpolate_1D(x, LUT_1D_xp, LUT_1D_fp)
            return (100 / 55) * x - REF_PT

        def fit(value, from_min, from_max, to_min, to_max):
            if from_min == from_max:
                raise ValueError('from_min == from_max')
            return (value - from_min) / (from_max - from_min) * (
                to_max - to_min) + to_min

        num_samples = 2 ** 12
        domain = (-0.19, 3)
        data = []
        for i in xrange(num_samples):
            x = i / (num_samples - 1)
            x = fit(x, 0, 1, domain[0], domain[1])
            data.append(cid_to_rle(x))

        lut = 'ADX_CID_to_RLE.spi1d'
        write_SPI_1d(os.path.join(lut_directory, lut),
                     domain[0],
                     domain[1],
                     data,
                     num_samples, 1)

        return lut

    # Converting *Channel Independent Density* values to
    # *Relative Log Exposure* values.
    lut = create_CID_to_RLE_LUT()
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    # Converting *Relative Log Exposure* values to
    # *Relative Exposure* values.
    cs.to_reference_transforms.append({
        'type': 'log',
        'base': 10,
        'direction': 'inverse'})

    # Convert *Relative Exposure* values to *ACES* values.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': [0.72286, 0.12630, 0.15084, 0,
                   0.11923, 0.76418, 0.11659, 0,
                   0.01427, 0.08213, 0.90359, 0,
                   0, 0, 0, 1],
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs

# -------------------------------------------------------------------------
# *Generic Log Transform*
# -------------------------------------------------------------------------
def create_generic_log(aces_ctl_directory,
                       lut_directory,
                       lut_resolution_1d,
                       cleanup,
                       name='log',
                       aliases=[],
                       min_value=0,
                       max_value=1,
                       input_scale=1,
                       middle_grey=0.18,
                       min_exposure=-6,
                       max_exposure=6.5):
    """
    Creates the *Generic Log* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *Generic Log* colorspace.
    """

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [os.path.join(
        aces_ctl_directory,
        'utilities',
        'ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl')]
    lut = '%s_to_linear.spi1d' % name

    lut = sanitize(lut)

    generate_1d_LUT_from_CTL(
        os.path.join(lut_directory, lut),
        ctls,
        lut_resolution_1d,
        'float',
        input_scale,
        1,
        {'middleGrey': middle_grey,
         'minExposure': min_exposure,
         'maxExposure': max_exposure},
        cleanup,
        aces_ctl_directory,
        min_value,
        max_value,
        1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs

# -------------------------------------------------------------------------
# *base Dolby PQ Transform*
# -------------------------------------------------------------------------
def create_dolbypq(aces_CTL_directory,
                    lut_directory,
                    lut_resolution_1d,
                    cleanup,
                    name='pq',
                    aliases=[],
                    min_value=0.0,
                    max_value=1.0,
                    input_scale=1.0):
    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [os.path.join(
                         aces_CTL_directory,
                         'utilities',
                         'ACESlib.OCIO_shaper_dolbypq_to_lin.a1.0.0.ctl')]
    lut = '%s_to_linear.spi1d' % name

    lut = sanitize(lut)

    generate_1d_LUT_from_CTL(
        os.path.join(lut_directory, lut),
        ctls,
        lut_resolution_1d,
        'float',
        input_scale,
        1.0,
        {},
        cleanup,
        aces_CTL_directory,
        min_value,
        max_value)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs

# -------------------------------------------------------------------------
# *Dolby PQ Transform that considers a fixed linear range*
# -------------------------------------------------------------------------
def create_dolbypq_scaled(aces_CTL_directory,
                           lut_directory,
                           lut_resolution_1d,
                           cleanup,
                           name='pq',
                           aliases=[],
                           min_value=0.0,
                           max_value=1.0,
                           input_scale=1.0,
                           middle_grey=0.18,
                           min_exposure=-6.0,
                           max_exposure=6.5):
    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [os.path.join(
                         aces_CTL_directory,
                         'utilities',
                         'ACESlib.OCIO_shaper_dolbypq_to_lin_param.a1.0.0.ctl')]
    lut = '%s_to_linear.spi1d' % name

    lut = sanitize(lut)

    generate_1d_LUT_from_CTL(
        os.path.join(lut_directory, lut),
        ctls,
        lut_resolution_1d,
        'float',
        input_scale,
        1.0,
        {'middleGrey': middle_grey,
         'minExposure': min_exposure,
         'maxExposure': max_exposure},
        cleanup,
        aces_CTL_directory,
        min_value,
        max_value)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    cs.from_reference_transforms = []
    return cs

# -------------------------------------------------------------------------
# *Individual LMT*
# -------------------------------------------------------------------------
def create_ACES_LMT(lmt_name,
                    lmt_values,
                    shaper_info,
                    aces_ctl_directory,
                    lut_directory,
                    lut_resolution_1d=1024,
                    lut_resolution_3d=64,
                    cleanup=True,
                    aliases=None):
    """
    Creates the *ACES LMT* colorspace.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    Colorspace
         *ACES LMT* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace('%s' % lmt_name)
    cs.description = 'The ACES Look Transform: %s' % lmt_name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Look'
    cs.is_data = False
    cs.allocation_type = ocio.Constants.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]

    pprint.pprint(lmt_values)

    # Generating the *shaper* transform.
    (shaper_name,
     shaper_to_ACES_CTL,
     shaper_from_ACES_CTL,
     shaper_input_scale,
     shaper_params) = shaper_info

    # Add the shaper transform
    shaper_lut = '%s_to_linear.spi1d' % shaper_name
    shaper_lut = sanitize(shaper_lut)

    shaper_OCIO_transform = {
        'type': 'lutFile',
        'path': shaper_lut,
        'interpolation': 'linear',
        'direction': 'inverse'}

    # Generating the forward transform.
    cs.from_reference_transforms = []

    if 'transformCTL' in lmt_values:
        ctls = [shaper_to_ACES_CTL % aces_ctl_directory,
                os.path.join(aces_ctl_directory,
                             lmt_values['transformCTL'])]
        lut = '%s.%s.spi3d' % (shaper_name, lmt_name)

        lut = sanitize(lut)

        generate_3d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            ctls,
            lut_resolution_3d,
            'float',
            1 / shaper_input_scale,
            1,
            shaper_params,
            cleanup,
            aces_ctl_directory)

        cs.from_reference_transforms.append(shaper_OCIO_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})

    # Generating the inverse transform.
    cs.to_reference_transforms = []

    if 'transformCTLInverse' in lmt_values:
        ctls = [os.path.join(aces_ctl_directory,
                             lmt_values['transformCTLInverse']),
                shaper_from_ACES_CTL % aces_ctl_directory]
        lut = 'Inverse.%s.%s.spi3d' % (odt_name, shaper_name)

        lut = sanitize(lut)

        generate_3d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            ctls,
            lut_resolution_3d,
            'half',
            1,
            shaper_input_scale,
            shaper_params,
            cleanup,
            aces_ctl_directory,
            0,
            1,
            1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})

        shaper_inverse = shaper_OCIO_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)

    return cs

# -------------------------------------------------------------------------
# *LMTs*
# -------------------------------------------------------------------------
def create_LMTs(aces_ctl_directory,
                lut_directory,
                lut_resolution_1d,
                lut_resolution_3d,
                lmt_info,
                shaper_name,
                cleanup):
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

    colorspaces = []

    # -------------------------------------------------------------------------
    # *LMT Shaper*
    # -------------------------------------------------------------------------
    lmt_lut_resolution_1d = max(4096, lut_resolution_1d)
    lmt_lut_resolution_3d = max(65, lut_resolution_3d)

    # Defining the *Log 2* shaper.
    lmt_shaper_name = 'LMT Shaper'
    lmt_shaper_name_aliases = ['crv_lmtshaper']
    lmt_params = {
        'middleGrey': 0.18,
        'minExposure': -10,
        'maxExposure': 6.5}

    lmt_shaper = create_generic_log(aces_ctl_directory,
                                    lut_directory,
                                    lmt_lut_resolution_1d,
                                    cleanup,
                                    name=lmt_shaper_name,
                                    middle_grey=lmt_params['middleGrey'],
                                    min_exposure=lmt_params['minExposure'],
                                    max_exposure=lmt_params['maxExposure'],
                                    aliases=lmt_shaper_name_aliases)
    colorspaces.append(lmt_shaper)

    shaper_input_scale_generic_log2 = 1

    # *Log 2* shaper name and *CTL* transforms bundled up.
    lmt_shaper_data = [
        lmt_shaper_name,
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl'),
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl'),
        shaper_input_scale_generic_log2,
        lmt_params]

    sorted_LMTs = sorted(lmt_info.iteritems(), key=lambda x: x[1])
    print(sorted_LMTs)
    for lmt in sorted_LMTs:
        lmt_name, lmt_values = lmt
        lmt_aliases = ["look_%s" % compact(lmt_values['transformUserName'])]
        cs = create_ACES_LMT(
            lmt_values['transformUserName'],
            lmt_values,
            lmt_shaper_data,
            aces_ctl_directory,
            lut_directory,
            lmt_lut_resolution_1d,
            lmt_lut_resolution_3d,
            cleanup,
            lmt_aliases)
        colorspaces.append(cs)

    return colorspaces

# -------------------------------------------------------------------------
# *ACES RRT* with supplied *ODT*.
# -------------------------------------------------------------------------
def create_ACES_RRT_plus_ODT(odt_name,
                             odt_values,
                             shaper_info,
                             aces_ctl_directory,
                             lut_directory,
                             lut_resolution_1d=1024,
                             lut_resolution_3d=64,
                             cleanup=True,
                             aliases=None):
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

    if aliases is None:
        aliases = []

    cs = ColorSpace('%s' % odt_name)
    cs.description = '%s - %s Output Transform' % (
        odt_values['transformUserNamePrefix'], odt_name)
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Output'
    cs.is_data = False

    pprint.pprint(odt_values)

    # Generating the *shaper* transform.
    (shaper_name,
     shaper_to_ACES_CTL,
     shaper_from_ACES_CTL,
     shaper_input_scale,
     shaper_params) = shaper_info

    if 'legalRange' in odt_values:
        shaper_params['legalRange'] = odt_values['legalRange']
    else:
        shaper_params['legalRange'] = 0

    # Add the shaper transform
    shaper_lut = '%s_to_linear.spi1d' % shaper_name
    shaper_lut = sanitize(shaper_lut)

    shaper_OCIO_transform = {
        'type': 'lutFile',
        'path': shaper_lut,
        'interpolation': 'linear',
        'direction': 'inverse'}

    # Generating the *forward* transform.
    cs.from_reference_transforms = []

    if 'transformLUT' in odt_values:
        transform_LUT_file_name = os.path.basename(
            odt_values['transformLUT'])
        lut = os.path.join(lut_directory, transform_LUT_file_name)
        shutil.copy(odt_values['transformLUT'], lut)

        cs.from_reference_transforms.append(shaper_OCIO_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': transform_LUT_file_name,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})
    elif 'transformCTL' in odt_values:
        ctls = [
            shaper_to_ACES_CTL % aces_ctl_directory,
            os.path.join(aces_ctl_directory,
                         'rrt',
                         'RRT.a1.0.0.ctl'),
            os.path.join(aces_ctl_directory,
                         'odt',
                         odt_values['transformCTL'])]
        lut = '%s.RRT.a1.0.0.%s.spi3d' % (shaper_name, odt_name)

        lut = sanitize(lut)

        generate_3d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            # shaperLUT,
            ctls,
            lut_resolution_3d,
            'float',
            1 / shaper_input_scale,
            1,
            shaper_params,
            cleanup,
            aces_ctl_directory)

        cs.from_reference_transforms.append(shaper_OCIO_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})

    # Generating the *inverse* transform.
    cs.to_reference_transforms = []

    if 'transformLUTInverse' in odt_values:
        transform_LUT_inverse_file_name = os.path.basename(
            odt_values['transformLUTInverse'])
        lut = os.path.join(lut_directory, transform_LUT_inverse_file_name)
        shutil.copy(odt_values['transformLUTInverse'], lut)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': transform_LUT_inverse_file_name,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})

        shaper_inverse = shaper_OCIO_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)
    elif 'transformCTLInverse' in odt_values:
        ctls = [os.path.join(aces_ctl_directory,
                             'odt',
                             odt_values['transformCTLInverse']),
                os.path.join(aces_ctl_directory,
                             'rrt',
                             'InvRRT.a1.0.0.ctl'),
                shaper_from_ACES_CTL % aces_ctl_directory]
        lut = 'InvRRT.a1.0.0.%s.%s.spi3d' % (odt_name, shaper_name)

        lut = sanitize(lut)

        generate_3d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            # None,
            ctls,
            lut_resolution_3d,
            'half',
            1,
            shaper_input_scale,
            shaper_params,
            cleanup,
            aces_ctl_directory)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'})

        shaper_inverse = shaper_OCIO_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)

    return cs

# -------------------------------------------------------------------------
# *ODTs*
# -------------------------------------------------------------------------
def create_ODTs(aces_ctl_directory,
                lut_directory,
                lut_resolution_1d,
                lut_resolution_3d,
                odt_info,
                shaper_name,
                cleanup,
                linear_display_space,
                log_display_space):
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

    colorspaces = []
    displays = {}

    # -------------------------------------------------------------------------
    # *RRT / ODT* Shaper Options
    # -------------------------------------------------------------------------
    shaper_data = {}

    # Defining the *Log 2* shaper.
    log2_shaper_name = shaper_name
    log2_shaper_name_aliases = ["crv_%s" % compact(log2_shaper_name)]
    log2_params = {
        'middleGrey': 0.18,
        'minExposure': -6,
        'maxExposure': 6.5}

    log2_shaper_colorspace = create_generic_log(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1d,
        cleanup,
        name=log2_shaper_name,
        middle_grey=log2_params['middleGrey'],
        min_exposure=log2_params['minExposure'],
        max_exposure=log2_params['maxExposure'],
        aliases=log2_shaper_name_aliases)
    colorspaces.append(log2_shaper_colorspace)

    shaper_input_scale_generic_log2 = 1

    # *Log 2* shaper name and *CTL* transforms bundled up.
    log2_shaper_data = [
        log2_shaper_name,
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl'),
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl'),
        shaper_input_scale_generic_log2,
        log2_params]

    shaper_data[log2_shaper_name] = log2_shaper_data

    # Space with a more user-friendly name. Direct copy otherwise.
    log2_shaper_copy_name = "Log2 Shaper"
    log2_shaper_copy_colorspace = ColorSpace(log2_shaper_copy_name)
    log2_shaper_copy_colorspace.description = 'The %s color space' % log2_shaper_copy_name
    log2_shaper_copy_colorspace.aliases = [compact(log2_shaper_copy_name)]
    log2_shaper_copy_colorspace.equality_group = log2_shaper_copy_name
    log2_shaper_copy_colorspace.family = log2_shaper_colorspace.family
    log2_shaper_copy_colorspace.is_data = log2_shaper_colorspace.is_data
    log2_shaper_copy_colorspace.to_reference_transforms = list(log2_shaper_colorspace.to_reference_transforms)
    log2_shaper_copy_colorspace.from_reference_transforms = list(log2_shaper_colorspace.from_reference_transforms)
    colorspaces.append(log2_shaper_copy_colorspace)

    # Defining the *Log2 shaper that includes the AP1* primaries.
    log2_shaper_api1_name = "%s - AP1" % "Log2 Shaper"
    log2_shaper_api1_colorspace = ColorSpace(log2_shaper_api1_name)
    log2_shaper_api1_colorspace.description = 'The %s color space' % log2_shaper_api1_name
    log2_shaper_api1_colorspace.aliases = ["%s_ap1" % compact(log2_shaper_copy_name)]
    log2_shaper_api1_colorspace.equality_group = log2_shaper_api1_name
    log2_shaper_api1_colorspace.family = log2_shaper_colorspace.family
    log2_shaper_api1_colorspace.is_data = log2_shaper_colorspace.is_data
    log2_shaper_api1_colorspace.to_reference_transforms = list(log2_shaper_colorspace.to_reference_transforms)
    log2_shaper_api1_colorspace.from_reference_transforms = list(log2_shaper_colorspace.from_reference_transforms)

    # *AP1* primaries to *AP0* primaries.
    log2_shaper_api1_colorspace.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction': 'forward'
    })
    colorspaces.append(log2_shaper_api1_colorspace)

    # Defining the *Log2 shaper that includes the AP1* primaries.
    # Named with 'shaper_name' variable. Needed for some LUT baking steps.
    shaper_api1_name = "%s - AP1" % shaper_name
    shaper_api1_colorspace = ColorSpace(shaper_api1_name)
    shaper_api1_colorspace.description = 'The %s color space' % shaper_api1_name
    shaper_api1_colorspace.aliases = ["%s_ap1" % compact(shaper_api1_name)]
    shaper_api1_colorspace.equality_group = shaper_api1_name
    shaper_api1_colorspace.family = log2_shaper_colorspace.family
    shaper_api1_colorspace.is_data = log2_shaper_colorspace.is_data
    shaper_api1_colorspace.to_reference_transforms = list(log2_shaper_api1_colorspace.to_reference_transforms)
    shaper_api1_colorspace.from_reference_transforms = list(log2_shaper_api1_colorspace.from_reference_transforms)
    colorspaces.append(shaper_api1_colorspace)

    # Define the base *Dolby PQ Shaper*
    #
    dolbypq_shaper_name = "Dolby PQ 10000"
    dolbypq_shaper_name_aliases = ["crv_%s" % "dolbypq_10000"]

    dolbypq_shaper_colorspace = create_dolbypq(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1d,
        cleanup,
        name=dolbypq_shaper_name,
        aliases=dolbypq_shaper_name_aliases)
    colorspaces.append(dolbypq_shaper_colorspace)

    # *Dolby PQ* shaper name and *CTL* transforms bundled up.
    dolbypq_shaper_data = [
        dolbypq_shaper_name,
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_dolbypq_to_lin.a1.0.0.ctl'),
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_lin_to_dolbypq.a1.0.0.ctl'),
        1.0,
        {}]

    shaper_data[dolbypq_shaper_name] = dolbypq_shaper_data

    # Define the *Dolby PQ Shaper that considers a fixed linear range*
    #
    dolbypq_scaled_shaper_name = "Dolby PQ Scaled"
    dolbypq_scaled_shaper_name_aliases = ["crv_%s" % "dolbypq_scaled"]

    dolbypq_scaled_shaper_colorspace = create_dolbypq_scaled(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1d,
        cleanup,
        name=dolbypq_scaled_shaper_name,
        aliases=dolbypq_scaled_shaper_name_aliases)
    colorspaces.append(dolbypq_scaled_shaper_colorspace)

    # *Dolby PQ* shaper name and *CTL* transforms bundled up.
    dolbypq_scaled_shaper_data = [
        dolbypq_scaled_shaper_name,
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_dolbypq_to_lin_param.a1.0.0.ctl'),
        os.path.join('%s',
                     'utilities',
                     'ACESlib.OCIO_shaper_lin_to_dolbypq_param.a1.0.0.ctl'),
        1.0,
        log2_params]

    shaper_data[dolbypq_scaled_shaper_name] = dolbypq_scaled_shaper_data

    #
    # Pick a specific shaper
    #
    rrt_shaper = log2_shaper_data
    #rrt_shaper = dolbypq_scaled_shaper_data

    # *RRT + ODT* combinations.
    sorted_odts = sorted(odt_info.iteritems(), key=lambda x: x[1])
    print(sorted_odts)
    for odt in sorted_odts:
        (odt_name, odt_values) = odt

        # Generating legal range transform for *ODTs* that can generate 
        # either *legal* or *full* output.
        if odt_values['transformHasFullLegalSwitch']:
            odt_name_legal = '%s - Legal' % odt_values['transformUserName']
        else:
            odt_name_legal = odt_values['transformUserName']

        odt_legal = odt_values.copy()
        odt_legal['legalRange'] = 1

        odt_aliases = ["out_%s" % compact(odt_name_legal)]

        cs = create_ACES_RRT_plus_ODT(
            odt_name_legal,
            odt_legal,
            rrt_shaper,
            aces_ctl_directory,
            lut_directory,
            lut_resolution_1d,
            lut_resolution_3d,
            cleanup,
            odt_aliases)
        colorspaces.append(cs)

        displays[odt_name_legal] = {
            'Linear': linear_display_space,
            'Log': log_display_space,
            'Output Transform': cs}


        # Generating full range transform for *ODTs* that can generate 
        # either *legal* or *full* output.
        if odt_values['transformHasFullLegalSwitch']:
            print('Generating full range ODT for %s' % odt_name)

            odt_name_full = '%s - Full' % odt_values['transformUserName']
            odt_full = odt_values.copy()
            odt_full['legalRange'] = 0

            odt_full_aliases = ["out_%s" % compact(odt_name_full)]

            cs_full = create_ACES_RRT_plus_ODT(
                odt_name_full,
                odt_full,
                rrt_shaper,
                aces_ctl_directory,
                lut_directory,
                lut_resolution_1d,
                lut_resolution_3d,
                cleanup,
                odt_full_aliases)
            colorspaces.append(cs_full)

            displays[odt_name_full] = {
                'Linear': linear_display_space,
                'Log': log_display_space,
                'Output Transform': cs_full}

    return (colorspaces, displays)


def get_transform_info(ctl_transform):
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

    with open(ctl_transform, 'rb') as fp:
        lines = fp.readlines()

    # Retrieving the *transform ID* and *User Name*.
    transform_id = lines[1][3:].split('<')[1].split('>')[1].strip()
    transform_user_name = '-'.join(
        lines[2][3:].split('<')[1].split('>')[1].split('-')[1:]).strip()
    transform_user_name_prefix = (
        lines[2][3:].split('<')[1].split('>')[1].split('-')[0].strip())

    # Figuring out if this transform has options for processing full and legal range
    transform_full_legal_switch = False
    for line in lines:
        if line.strip() == "input varying int legalRange = 0":
            # print( "%s has legal range flag" % transform_user_name)
            transform_full_legal_switch = True
            break

    return (transform_id, transform_user_name, transform_user_name_prefix,
            transform_full_legal_switch)


def get_ODTs_info(aces_ctl_directory):
    """
    Object description.

    For versions after WGR9.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate usage of *files_walker* definition here.
    # Credit to *Alex Fry* for the original approach here.
    odt_dir = os.path.join(aces_ctl_directory, 'odt')
    all_odt = []
    for dir_name, subdir_list, file_list in os.walk(odt_dir):
        for fname in file_list:
            all_odt.append((os.path.join(dir_name, fname)))

    odt_CTLs = [x for x in all_odt if
                ('InvODT' not in x) and (os.path.split(x)[-1][0] != '.')]

    odts = {}

    for odt_CTL in odt_CTLs:
        odt_tokens = os.path.split(odt_CTL)

        # Handling nested directories.
        odt_path_tokens = os.path.split(odt_tokens[-2])
        odt_dir = odt_path_tokens[-1]
        while odt_path_tokens[-2][-3:] != 'odt':
            odt_path_tokens = os.path.split(odt_path_tokens[-2])
            odt_dir = os.path.join(odt_path_tokens[-1], odt_dir)

        # Building full name,
        transform_CTL = odt_tokens[-1]
        odt_name = string.join(transform_CTL.split('.')[1:-1], '.')

        # Finding id, user name and user name prefix.
        (transform_ID,
         transform_user_name,
         transform_user_name_prefix,
         transform_full_legal_switch) = get_transform_info(
            os.path.join(aces_ctl_directory, 'odt', odt_dir, transform_CTL))

        # Finding inverse.
        transform_CTL_inverse = 'InvODT.%s.ctl' % odt_name
        if not os.path.exists(
                os.path.join(odt_tokens[-2], transform_CTL_inverse)):
            transform_CTL_inverse = None

        # Add to list of ODTs
        odts[odt_name] = {}
        odts[odt_name]['transformCTL'] = os.path.join(odt_dir, transform_CTL)
        if transform_CTL_inverse is not None:
            odts[odt_name]['transformCTLInverse'] = os.path.join(
                odt_dir, transform_CTL_inverse)

        odts[odt_name]['transformID'] = transform_ID
        odts[odt_name]['transformUserNamePrefix'] = transform_user_name_prefix
        odts[odt_name]['transformUserName'] = transform_user_name
        odts[odt_name][
            'transformHasFullLegalSwitch'] = transform_full_legal_switch

        forward_CTL = odts[odt_name]['transformCTL']

        print('ODT : %s' % odt_name)
        print('\tTransform ID               : %s' % transform_ID)
        print('\tTransform User Name Prefix : %s' % transform_user_name_prefix)
        print('\tTransform User Name        : %s' % transform_user_name)
        print(
            '\tHas Full / Legal Switch    : %s' % transform_full_legal_switch)
        print('\tForward ctl                : %s' % forward_CTL)
        if 'transformCTLInverse' in odts[odt_name]:
            inverse_CTL = odts[odt_name]['transformCTLInverse']
            print('\tInverse ctl                : %s' % inverse_CTL)
        else:
            print('\tInverse ctl                : %s' % 'None')

    print('\n')

    return odts


def get_LMTs_info(aces_ctl_directory):
    """
    Object description.

    For versions after WGR9.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate refactoring with previous definition.

    # Credit to Alex Fry for the original approach here
    lmt_dir = os.path.join(aces_ctl_directory, 'lmt')
    all_lmt = []
    for dir_name, subdir_list, file_list in os.walk(lmt_dir):
        for fname in file_list:
            all_lmt.append((os.path.join(dir_name, fname)))

    lmt_CTLs = [x for x in all_lmt if
                ('InvLMT' not in x) and ('README' not in x) and (
                    os.path.split(x)[-1][0] != '.')]

    lmts = {}

    for lmt_CTL in lmt_CTLs:
        lmt_tokens = os.path.split(lmt_CTL)

        # Handlimg nested directories.
        lmt_path_tokens = os.path.split(lmt_tokens[-2])
        lmt_dir = lmt_path_tokens[-1]
        while lmt_path_tokens[-2][-3:] != 'ctl':
            lmt_path_tokens = os.path.split(lmt_path_tokens[-2])
            lmt_dir = os.path.join(lmt_path_tokens[-1], lmt_dir)

        # Building full name.
        transform_CTL = lmt_tokens[-1]
        lmt_name = string.join(transform_CTL.split('.')[1:-1], '.')

        # Finding id, user name and user name prefix.
        (transform_ID,
         transform_user_name,
         transform_user_name_prefix,
         transform_full_legal_switch) = get_transform_info(
            os.path.join(aces_ctl_directory, lmt_dir, transform_CTL))

        # Finding inverse.
        transform_CTL_inverse = 'InvLMT.%s.ctl' % lmt_name
        if not os.path.exists(
                os.path.join(lmt_tokens[-2], transform_CTL_inverse)):
            transform_CTL_inverse = None

        lmts[lmt_name] = {}
        lmts[lmt_name]['transformCTL'] = os.path.join(lmt_dir, transform_CTL)
        if transform_CTL_inverse is not None:
            lmts[lmt_name]['transformCTLInverse'] = os.path.join(
                lmt_dir, transform_CTL_inverse)

        lmts[lmt_name]['transformID'] = transform_ID
        lmts[lmt_name]['transformUserNamePrefix'] = transform_user_name_prefix
        lmts[lmt_name]['transformUserName'] = transform_user_name

        forward_CTL = lmts[lmt_name]['transformCTL']

        print('LMT : %s' % lmt_name)
        print('\tTransform ID               : %s' % transform_ID)
        print('\tTransform User Name Prefix : %s' % transform_user_name_prefix)
        print('\tTransform User Name        : %s' % transform_user_name)
        print('\t Forward ctl               : %s' % forward_CTL)
        if 'transformCTLInverse' in lmts[lmt_name]:
            inverse_CTL = lmts[lmt_name]['transformCTLInverse']
            print('\t Inverse ctl                : %s' % inverse_CTL)
        else:
            print('\t Inverse ctl                : %s' % 'None')

    print('\n')

    return lmts


def create_colorspaces(aces_ctl_directory,
                       lut_directory,
                       lut_resolution_1d,
                       lut_resolution_3d,
                       lmt_info,
                       odt_info,
                       shaper_name,
                       cleanup):
    """
    Generates the colorspace conversions.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    colorspaces = []

    ACES = create_ACES()

    ACEScc = create_ACEScc(aces_ctl_directory, lut_directory,
                           lut_resolution_1d, cleanup, 
                           min_value=-0.35840, max_value=1.468)
    colorspaces.append(ACEScc)

    ACESproxy = create_ACESproxy(aces_ctl_directory, lut_directory,
                                 lut_resolution_1d, cleanup)
    colorspaces.append(ACESproxy)

    ACEScg = create_ACEScg(aces_ctl_directory, lut_directory,
                           lut_resolution_1d, cleanup)
    colorspaces.append(ACEScg)

    ADX10 = create_ADX(lut_directory, lut_resolution_1d, bit_depth=10)
    colorspaces.append(ADX10)

    ADX16 = create_ADX(lut_directory, lut_resolution_1d, bit_depth=16)
    colorspaces.append(ADX16)

    lmts = create_LMTs(aces_ctl_directory,
                       lut_directory,
                       lut_resolution_1d,
                       lut_resolution_3d,
                       lmt_info,
                       shaper_name,
                       cleanup)
    colorspaces.extend(lmts)

    odts, displays = create_ODTs(aces_ctl_directory,
                                 lut_directory,
                                 lut_resolution_1d,
                                 lut_resolution_3d,
                                 odt_info,
                                 shaper_name,
                                 cleanup,
                                 ACES,
                                 ACEScc)
    colorspaces.extend(odts)

    roles = {'color_picking'   : ACEScg.name,
             'color_timing'    : ACEScc.name,
             'compositing_log' : ACEScc.name,
             'data'            : '',
             'default'         : ACES.name,
             'matte_paint'     : ACEScc.name,
             'reference'       : '',
             'scene_linear'    : ACES.name,
             'texture_paint'   : ''}


    return ACES, colorspaces, displays, ACEScc, roles
