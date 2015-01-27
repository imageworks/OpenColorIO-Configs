#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for general colorspaces conversions and transfer functions.
"""

import array
import math
import os

import aces_ocio.generate_lut as genlut
import aces_ocio.create_aces_colorspaces as aces
from aces_ocio.utilities import ColorSpace, mat44_from_mat33, sanitize_path, compact


__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['create_generic_matrix',
           'create_colorspaces']

# -------------------------------------------------------------------------
# Generic Matrix transform
# -------------------------------------------------------------------------
def create_generic_matrix(name='matrix',
                          from_reference_values=None,
                          to_reference_values=None,
                          aliases=[]):

    if from_reference_values is None:
         from_reference_values = []
    if to_reference_values is None:
         to_reference_values = []

    cs = ColorSpace(name)
    cs.description = 'The %s color space' % name
    cs.aliases = []
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

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
        from_reference_values=[aces.ACES_AP0_to_XYZ], 
        aliases=["lin_xyz"])
    colorspaces.append(cs)

    cs = create_generic_matrix(
        'Linear - AP1', 
        to_reference_values=[aces.ACES_AP1_to_AP0],
        aliases=["lin_ap1"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *P3D60* primaries.
    XYZ_to_P3D60 = [2.4027414142, -0.8974841639, -0.3880533700,
                    -0.8325796487, 1.7692317536, 0.0237127115,
                    0.0388233815, -0.0824996856, 1.0363685997]

    cs = create_generic_matrix(
        'Linear - P3-D60',
        from_reference_values=[aces.ACES_AP0_to_XYZ, XYZ_to_P3D60],
        aliases=["lin_p3d60"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *P3DCI* primaries.
    XYZ_to_P3DCI = [2.7253940305, -1.0180030062, -0.4401631952,
                    -0.7951680258, 1.6897320548, 0.0226471906,
                    0.0412418914, -0.0876390192, 1.1009293786]

    cs = create_generic_matrix(
        'Linear - P3-DCI',
        from_reference_values=[aces.ACES_AP0_to_XYZ, XYZ_to_P3DCI],
        aliases=["lin_p3dci"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Rec. 709* primaries.
    XYZ_to_Rec709 = [3.2409699419, -1.5373831776, -0.4986107603,
                     -0.9692436363, 1.8759675015, 0.0415550574,
                     0.0556300797, -0.2039769589, 1.0569715142]

    cs = create_generic_matrix(
        'Linear - Rec.709',
        from_reference_values=[aces.ACES_AP0_to_XYZ, XYZ_to_Rec709],
        aliases=["lin_rec709"])
    colorspaces.append(cs)

    # *ACES* to *Linear*, *Rec. 2020* primaries.
    XYZ_to_Rec2020 = [1.7166511880, -0.3556707838, -0.2533662814,
                      -0.6666843518, 1.6164812366, 0.0157685458,
                      0.0176398574, -0.0427706133, 0.9421031212]

    cs = create_generic_matrix(
        'Linear - Rec.2020',
        from_reference_values=[aces.ACES_AP0_to_XYZ, XYZ_to_Rec2020],
        aliases=["lin_rec2020"])
    colorspaces.append(cs)

    return colorspaces
