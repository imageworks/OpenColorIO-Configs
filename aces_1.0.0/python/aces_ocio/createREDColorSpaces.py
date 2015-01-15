#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implements support for *RED* colorspaces conversions and transfer functions.
"""

import array

import aces_ocio.generateLUT as genlut
from aces_ocio.util import ColorSpace, mat44FromMat33

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['createREDlogFilm',
           'createColorSpaces']


def createREDlogFilm(gamut, transferFunction, name, lutDir, lutResolution1d):
    """
    Object description.

    RED colorspaces to ACES.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    name = "%s - %s" % (transferFunction, gamut)
    if transferFunction == "":
        name = "Linear - %s" % gamut
    if gamut == "":
        name = "%s" % transferFunction

    cs = ColorSpace(name)
    cs.description = name
    cs.equalityGroup = ''
    cs.family = 'RED'
    cs.isData = False

    def cineonToLinear(codeValue):
        nGamma = 0.6
        blackPoint = 95.0
        whitePoint = 685.0
        codeValueToDensity = 0.002

        blackLinear = pow(10.0, (blackPoint - whitePoint) * (
            codeValueToDensity / nGamma))
        codeLinear = pow(10.0, (codeValue - whitePoint) * (
            codeValueToDensity / nGamma))

        return (codeLinear - blackLinear) / (1.0 - blackLinear)

    cs.toReferenceTransforms = []

    if transferFunction == 'REDlogFilm':
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = cineonToLinear(1023.0 * c / (lutResolution1d - 1))

        lut = "CineonLog_to_linear.spi1d"
        genlut.writeSPI1D(lutDir + "/" + lut,
                          0.0,
                          1.0,
                          data,
                          lutResolution1d,
                          1)

        cs.toReferenceTransforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    if gamut == 'DRAGONcolor':
        cs.toReferenceTransforms.append({
            'type': 'matrix',
            'matrix': mat44FromMat33([0.532279, 0.376648, 0.091073,
                                      0.046344, 0.974513, -0.020860,
                                      -0.053976, -0.000320, 1.054267]),
            'direction': 'forward'
        })
    elif gamut == 'DRAGONcolor2':
        cs.toReferenceTransforms.append({
            'type': 'matrix',
            'matrix': mat44FromMat33([0.468452, 0.331484, 0.200064,
                                      0.040787, 0.857658, 0.101553,
                                      -0.047504, -0.000282, 1.047756]),
            'direction': 'forward'
        })
    elif gamut == 'REDcolor2':
        cs.toReferenceTransforms.append({
            'type': 'matrix',
            'matrix': mat44FromMat33([0.480997, 0.402289, 0.116714,
                                      -0.004938, 1.000154, 0.004781,
                                      -0.105257, 0.025320, 1.079907]),
            'direction': 'forward'
        })
    elif gamut == 'REDcolor3':
        cs.toReferenceTransforms.append({
            'type': 'matrix',
            'matrix': mat44FromMat33([0.512136, 0.360370, 0.127494,
                                      0.070377, 0.903884, 0.025737,
                                      -0.020824, 0.017671, 1.003123]),
            'direction': 'forward'
        })
    elif gamut == 'REDcolor4':
        cs.toReferenceTransforms.append({
            'type': 'matrix',
            'matrix': mat44FromMat33([0.474202, 0.333677, 0.192121,
                                      0.065164, 0.836932, 0.097901,
                                      -0.019281, 0.016362, 1.002889]),
            'direction': 'forward'
        })

    cs.fromReferenceTransforms = []
    return cs


def createColorSpaces(lutDir, lutResolution1d):
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

    # Full conversion
    REDlogFilmDRAGON = createREDlogFilm(
        "DRAGONcolor", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmDRAGON)

    REDlogFilmDRAGON2 = createREDlogFilm(
        "DRAGONcolor2", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmDRAGON2)

    REDlogFilmREDcolor2 = createREDlogFilm(
        "REDcolor2", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor2)

    REDlogFilmREDcolor3 = createREDlogFilm(
        "REDcolor3", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor3)

    REDlogFilmREDcolor4 = createREDlogFilm(
        "REDcolor4", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor4)

    # Linearization only
    REDlogFilmDRAGON = createREDlogFilm(
        "", "REDlogFilm", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmDRAGON)

    # Primaries only
    REDlogFilmDRAGON = createREDlogFilm(
        "DRAGONcolor", "", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmDRAGON)

    REDlogFilmDRAGON2 = createREDlogFilm(
        "DRAGONcolor2", "", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmDRAGON2)

    REDlogFilmREDcolor2 = createREDlogFilm(
        "REDcolor2", "", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor2)

    REDlogFilmREDcolor3 = createREDlogFilm(
        "REDcolor3", "", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor3)

    REDlogFilmREDcolor4 = createREDlogFilm(
        "REDcolor4", "", "REDlogFilm", lutDir, lutResolution1d)
    colorspaces.append(REDlogFilmREDcolor4)

    return colorspaces
