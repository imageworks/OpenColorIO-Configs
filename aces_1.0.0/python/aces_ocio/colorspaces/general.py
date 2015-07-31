#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for general colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.colorspaces import aces
from aces_ocio.utilities import ColorSpace, mat44_from_mat33

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['create_matrix_colorspace',
           'create_transfer_colorspace',
           'create_matrix_plus_transfer_colorspace',
           'transfer_function_sRGB_to_linear',
           'transfer_function_Rec709_to_linear',
           'transfer_function_Rec2020_10bit_to_linear',
           'transfer_function_Rec2020_12bit_to_linear',
           'transfer_function_Rec1886_to_linear',
           'create_colorspaces',
           'create_raw']


# -------------------------------------------------------------------------
# *Matrix Transform*
# -------------------------------------------------------------------------
def create_matrix_colorspace(name='matrix',
                             from_reference_values=None,
                             to_reference_values=None,
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

    if from_reference_values is None:
        from_reference_values = []

    if to_reference_values is None:
        to_reference_values = []

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.Constants.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    cs.to_reference_transforms = []
    if to_reference_values:
        for matrix in to_reference_values:
            cs.to_reference_transforms.append({
                'type': 'matrix',
                'matrix': mat44_from_mat33(matrix),
                'direction': 'forward'})

    cs.from_reference_transforms = []
    if from_reference_values:
        for matrix in from_reference_values:
            cs.from_reference_transforms.append({
                'type': 'matrix',
                'matrix': mat44_from_mat33(matrix),
                'direction': 'forward'})

    return cs


# -------------------------------------------------------------------------
# *Transfer Function Transform*
# -------------------------------------------------------------------------
def create_transfer_colorspace(name='transfer',
                               transfer_function_name='transfer_function',
                               transfer_function=lambda x: x,
                               lut_directory='/tmp',
                               lut_resolution_1d=1024,
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

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.Constants.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Sampling the transfer function.
    data = array.array('f', '\0' * lut_resolution_1d * 4)
    for c in range(lut_resolution_1d):
        data[c] = transfer_function(c / (lut_resolution_1d - 1))

    # Writing the sampled data to a *LUT*.
    lut = '%s_to_linear.spi1d' % transfer_function_name
    genlut.write_SPI_1d(
        os.path.join(lut_directory, lut),
        0,
        1,
        data,
        lut_resolution_1d,
        1)

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'})

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []

    return cs


# -------------------------------------------------------------------------
# *Transfer Function + Matrix Transform*
# -------------------------------------------------------------------------
def create_matrix_plus_transfer_colorspace(
        name='matrix_plus_transfer',
        transfer_function_name='transfer_function',
        transfer_function=lambda x: x,
        lut_directory='/tmp',
        lut_resolution_1d=1024,
        from_reference_values=None,
        to_reference_values=None,
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

    if from_reference_values is None:
        from_reference_values = []

    if to_reference_values is None:
        to_reference_values = []

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.Constants.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Sampling the transfer function.
    data = array.array('f', '\0' * lut_resolution_1d * 4)
    for c in range(lut_resolution_1d):
        data[c] = transfer_function(c / (lut_resolution_1d - 1))

    # Writing the sampled data to a *LUT*.
    lut = '%s_to_linear.spi1d' % transfer_function_name
    genlut.write_SPI_1d(
        os.path.join(lut_directory, lut),
        0,
        1,
        data,
        lut_resolution_1d,
        1)

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    if to_reference_values:
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'})

        for matrix in to_reference_values:
            cs.to_reference_transforms.append({
                'type': 'matrix',
                'matrix': mat44_from_mat33(matrix),
                'direction': 'forward'})

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []
    if from_reference_values:
        for matrix in from_reference_values:
            cs.from_reference_transforms.append({
                'type': 'matrix',
                'matrix': mat44_from_mat33(matrix),
                'direction': 'forward'})

        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'inverse'})

    return cs


# Transfer functions for standard colorspaces.
def transfer_function_sRGB_to_linear(v):
    a = 1.055
    b = 0.04045
    d = 12.92
    g = 2.4

    if v < b:
        return v / d
    return pow(((v + (a - 1)) / a), g)


def transfer_function_Rec709_to_linear(v):
    a = 1.099
    b = 0.018
    d = 4.5
    g = (1.0 / 0.45)

    if v < b * d:
        return v / d

    return pow(((v + (a - 1)) / a), g)


def transfer_function_Rec2020_10bit_to_linear(v):
    a = 1.099
    b = 0.018
    d = 4.5
    g = (1.0 / 0.45)

    if v < b * d:
        return v / d

    return pow(((v + (a - 1)) / a), g)


def transfer_function_Rec2020_12bit_to_linear(v):
    a = 1.0993
    b = 0.0181
    d = 4.5
    g = (1.0 / 0.45)

    if v < b * d:
        return v / d

    return pow(((v + (a - 1)) / a), g)


def transfer_function_Rec1886_to_linear(v):
    g = 2.4
    Lw = 1
    Lb = 0

    # Ignoring legal to full scaling for now.
    # v = (1023.0*v - 64.0)/876.0

    t = pow(Lw, 1.0 / g) - pow(Lb, 1.0 / g)
    a = pow(t, g)
    b = pow(Lb, 1.0 / g) / t

    return a * pow(max((v + b), 0.0), g)


def create_colorspaces(lut_directory,
                       lut_resolution_1d):
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

    # -------------------------------------------------------------------------
    # XYZ
    # -------------------------------------------------------------------------
    cs = create_matrix_colorspace('XYZ-D60',
                                  to_reference_values=[aces.ACES_XYZ_TO_AP0],
                                  from_reference_values=[aces.ACES_AP0_TO_XYZ],
                                  aliases=['lin_xyz_d60'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # P3-D60
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *P3D60* primaries
    XYZ_to_P3D60 = [2.4027414142, -0.8974841639, -0.3880533700,
                    -0.8325796487, 1.7692317536, 0.0237127115,
                    0.0388233815, -0.0824996856, 1.0363685997]

    cs = create_matrix_colorspace(
        'Linear - P3-D60',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3D60],
        aliases=['lin_p3d60'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # P3-DCI
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *P3DCI* primaries
    XYZ_to_P3DCI = [2.7253940305, -1.0180030062, -0.4401631952,
                    -0.7951680258, 1.6897320548, 0.0226471906,
                    0.0412418914, -0.0876390192, 1.1009293786]

    cs = create_matrix_colorspace(
        'Linear - P3-DCI',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3DCI],
        aliases=['lin_p3dci'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # sRGB
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Rec. 709* primaries.
    # *sRGB* and *Rec 709* use the same gamut.
    XYZ_to_Rec709 = [3.2409699419, -1.5373831776, -0.4986107603,
                     -0.9692436363, 1.8759675015, 0.0415550574,
                     0.0556300797, -0.2039769589, 1.0569715142]

    cs = create_matrix_colorspace(
        'Linear - sRGB',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['lin_srgb'])
    colorspaces.append(cs)

    # *Linear* to *sRGB* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - sRGB',
        'sRGB',
        transfer_function_sRGB_to_linear,
        lut_directory,
        lut_resolution_1d,
        aliases=['crv_srgb'])
    colorspaces.append(cs)

    # *ACES* to *sRGB* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'sRGB',
        'sRGB',
        transfer_function_sRGB_to_linear,
        lut_directory,
        lut_resolution_1d,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['srgb'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Rec 709
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Rec. 709* primaries
    XYZ_to_Rec709 = [3.2409699419, -1.5373831776, -0.4986107603,
                     -0.9692436363, 1.8759675015, 0.0415550574,
                     0.0556300797, -0.2039769589, 1.0569715142]

    cs = create_matrix_colorspace(
        'Linear - Rec.709',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['lin_rec709'])
    colorspaces.append(cs)

    # *Linear* to *Rec. 709* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.709',
        'rec709',
        transfer_function_Rec709_to_linear,
        lut_directory,
        lut_resolution_1d,
        aliases=['crv_rec709'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 709* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.709 - Camera',
        'rec709',
        transfer_function_Rec709_to_linear,
        lut_directory,
        lut_resolution_1d,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['rec709_camera'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Rec 2020
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Rec. 2020* primaries
    XYZ_to_Rec2020 = [1.7166511880, -0.3556707838, -0.2533662814,
                      -0.6666843518, 1.6164812366, 0.0157685458,
                      0.0176398574, -0.0427706133, 0.9421031212]

    cs = create_matrix_colorspace(
        'Linear - Rec.2020',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['lin_rec2020'])
    colorspaces.append(cs)

    # *Linear* to *Rec. 2020 10 bit* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.2020',
        'rec2020',
        transfer_function_Rec2020_10bit_to_linear,
        lut_directory,
        lut_resolution_1d,
        aliases=['crv_rec2020'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 2020 10 bit* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.2020 - Camera',
        'rec2020',
        transfer_function_Rec2020_10bit_to_linear,
        lut_directory,
        lut_resolution_1d,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['rec2020_camera'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Rec 1886
    # -------------------------------------------------------------------------
    # *Linear* to *Rec.1886* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.1886',
        'rec1886',
        transfer_function_Rec1886_to_linear,
        lut_directory,
        lut_resolution_1d,
        aliases=['crv_rec1886'])
    colorspaces.append(cs)

    # *ACES* to *sRGB* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.709 - Display',
        'rec1886',
        transfer_function_Rec1886_to_linear,
        lut_directory,
        lut_resolution_1d,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['rec709_display'])
    colorspaces.append(cs)

    # *ACES* to *sRGB* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.2020 - Display',
        'rec1886',
        transfer_function_Rec1886_to_linear,
        lut_directory,
        lut_resolution_1d,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['rec2020_display'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # ProPhoto
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Pro Photo* primaries
    AP0_to_RIMM = [1.2412367771, -0.1685692287, -0.0726675484,
                   0.0061203066, 1.083151174, -0.0892714806,
                   -0.0032853314, 0.0099796402, 0.9933056912]

    cs = create_matrix_colorspace(
        'Linear - RIMM ROMM (ProPhoto)',
        from_reference_values=[AP0_to_RIMM],
        aliases=['lin_prophoto', 'lin_rimm'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Adobe RGB
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Adobe RGB* primaries
    AP0_to_ADOBERGB = [1.7245603168, -0.4199935942, -0.3045667227,
                       -0.2764799142, 1.3727190877, -0.0962391734,
                       -0.0261255258, -0.0901747807, 1.1163003065]

    cs = create_matrix_colorspace(
        'Linear - Adobe RGB',
        from_reference_values=[AP0_to_ADOBERGB],
        aliases=['lin_adobergb'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Adobe Wide Gamut RGB
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Adobe Wide Gamut RGB* primaries
    AP0_to_ADOBERGB = [1.3809814778, -0.1158594573, -0.2651220205,
                       0.0057015535, 1.0402949043, -0.0459964578,
                       -0.0038908746, -0.0597091815, 1.0636000561]

    cs = create_matrix_colorspace(
        'Linear - Adobe Wide Gamut RGB',
        from_reference_values=[AP0_to_ADOBERGB],
        aliases=['lin_adobewidegamutrgb'])
    colorspaces.append(cs)

    return colorspaces


def create_raw():
    # *Raw* utility space
    name = 'Raw'
    raw = ColorSpace(name)
    raw.description = 'The %s color space' % name
    raw.aliases = ['raw']
    raw.equality_group = name
    raw.family = 'Utility'
    raw.is_data = True

    return raw
