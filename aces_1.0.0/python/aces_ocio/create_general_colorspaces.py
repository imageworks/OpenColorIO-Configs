#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for general colorspaces conversions and transfer functions.
"""

from __future__ import division

import PyOpenColorIO as ocio

import aces_ocio.create_aces_colorspaces as aces
from aces_ocio.utilities import ColorSpace, mat44_from_mat33


__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['create_generic_matrix',
           'create_colorspaces']

# -------------------------------------------------------------------------
# *Simple Matrix Transform*
# -------------------------------------------------------------------------
def create_generic_matrix(name='matrix',
                          from_reference_values=None,
                          to_reference_values=None,
                          aliases=[]):
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

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables
    cs.allocation_type = ocio.Constants.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]

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

def create_colorspaces(lut_directory,
                       lut_resolution_1d,
                       lut_resolution_3d):
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

    cs = create_generic_matrix('XYZ',
                               to_reference_values=[aces.ACES_XYZ_TO_AP0],
                               from_reference_values=[aces.ACES_AP0_TO_XYZ],
                               aliases=["lin_xyz"])
    colorspaces.append(cs)

    cs = create_generic_matrix(
        'Linear - AP1',
        to_reference_values=[aces.ACES_AP1_TO_AP0],
        from_reference_values=[aces.ACES_AP0_TO_AP1],
        aliases=["lin_ap1"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *P3D60* primaries.
    XYZ_to_P3D60 = [2.4027414142, -0.8974841639, -0.3880533700,
                    -0.8325796487, 1.7692317536, 0.0237127115,
                    0.0388233815, -0.0824996856, 1.0363685997]

    cs = create_generic_matrix(
        'Linear - P3-D60',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3D60],
        aliases=["lin_p3d60"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *P3DCI* primaries.
    XYZ_to_P3DCI = [2.7253940305, -1.0180030062, -0.4401631952,
                    -0.7951680258, 1.6897320548, 0.0226471906,
                    0.0412418914, -0.0876390192, 1.1009293786]

    cs = create_generic_matrix(
        'Linear - P3-DCI',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3DCI],
        aliases=["lin_p3dci"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Rec. 709* primaries.
    XYZ_to_Rec709 = [3.2409699419, -1.5373831776, -0.4986107603,
                     -0.9692436363, 1.8759675015, 0.0415550574,
                     0.0556300797, -0.2039769589, 1.0569715142]

    cs = create_generic_matrix(
        'Linear - Rec.709',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=["lin_rec709"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Rec. 2020* primaries.
    XYZ_to_Rec2020 = [1.7166511880, -0.3556707838, -0.2533662814,
                      -0.6666843518, 1.6164812366, 0.0157685458,
                      0.0176398574, -0.0427706133, 0.9421031212]

    cs = create_generic_matrix(
        'Linear - Rec.2020',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=["lin_rec2020"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Pro Photo* primaries.
    AP0_to_RIMM = [1.2412367771, -0.1685692287, -0.0726675484,
                   0.0061203066, 1.083151174, -0.0892714806,
                   -0.0032853314, 0.0099796402, 0.9933056912]

    cs = create_generic_matrix(
        'Linear - RIMM ROMM (ProPhoto)',
        from_reference_values=[AP0_to_RIMM],
        aliases=["lin_prophoto", "lin_rimm"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Adobe RGB* primaries.
    AP0_to_ADOBERGB = [1.7245603168, -0.4199935942, -0.3045667227,
                       -0.2764799142, 1.3727190877, -0.0962391734,
                       -0.0261255258, -0.0901747807, 1.1163003065]

    cs = create_generic_matrix(
        'Linear - Adobe RGB',
        from_reference_values=[AP0_to_ADOBERGB],
        aliases=["lin_adobergb"])
    colorspaces.append(cs)


    # *ACES* to *Linear*, *Adobe Wide Gamut RGB* primaries.
    AP0_to_ADOBERGB = [1.3809814778, -0.1158594573, -0.2651220205,
                       0.0057015535, 1.0402949043, -0.0459964578,
                       -0.0038908746, -0.0597091815, 1.0636000561]

    cs = create_generic_matrix(
        'Linear - Adobe Wide Gamut RGB',
        from_reference_values=[AP0_to_ADOBERGB],
        aliases=["lin_adobewidegamutrgb"])
    colorspaces.append(cs)

    return colorspaces

def create_raw():
    # *Raw* utility space
    name = "Raw"
    raw = ColorSpace(name)
    raw.description = 'The %s color space' % name
    raw.aliases = []
    raw.equality_group = name
    raw.family = 'Utility'
    raw.is_data = True

    return raw


