#!/usr/bin/env python
# -*- coding: utf-8 -*-

import array
import math

import aces_ocio.generateLUT as genlut
from aces_ocio.util import ColorSpace, mat44FromMat33


#
# LogC to ACES
#
def createLogC(gamut, transferFunction, exposureIndex, name, lutDir, lutResolution1d):
    name = "%s (EI%s) - %s" % (transferFunction, exposureIndex, gamut)
    if transferFunction == "":
        name = "Linear - %s" % gamut
    if gamut == "":
        name = "%s (EI%s)" % (transferFunction, exposureIndex)

    cs = ColorSpace(name)
    cs.description = name
    cs.equalityGroup = ''
    cs.family = 'ARRI'
    cs.isData=False

    # Globals
    IDT_maker_version = "0.08"

    nominalEI = 400.0
    blackSignal = 0.003907
    midGraySignal = 0.01
    encodingGain = 0.256598
    encodingOffset = 0.391007

    def gainForEI(EI) :
        return (math.log(EI/nominalEI)/math.log(2) * (0.89 - 1) / 3 + 1) * encodingGain

    def LogCInverseParametersForEI(EI) :
        cut = 1.0 / 9.0
        slope = 1.0 / (cut * math.log(10))
        offset = math.log10(cut) - slope * cut
        gain = EI / nominalEI
        gray = midGraySignal / gain
        # The higher the EI, the lower the gamma
        encGain = gainForEI(EI)
        encOffset = encodingOffset
        for i in range(0,3) :
            nz = ((95.0 / 1023.0 - encOffset) / encGain - offset) / slope
            encOffset = encodingOffset - math.log10(1 + nz) * encGain
        # Calculate some intermediate values
        a = 1.0 / gray
        b = nz - blackSignal / gray
        e = slope * a * encGain
        f = encGain * (slope * b + offset) + encOffset
        # Manipulations so we can return relative exposure
        s = 4 / (0.18 * EI)
        t = blackSignal
        b = b + a * t
        a = a * s
        f = f + e * t
        e = e * s
        return { 'a' : a,
                 'b' : b,
                 'cut' : (cut - b) / a,
                 'c' : encGain,
                 'd' : encOffset,
                 'e' : e,
                 'f' : f }

    def logCtoLinear(codeValue, exposureIndex):
        p = LogCInverseParametersForEI(exposureIndex)
        breakpoint = p['e'] * p['cut'] + p['f']
        if (codeValue > breakpoint):
            linear = (pow(10,(codeValue/1023.0 - p['d']) / p['c']) - p['b']) / p['a']
        else:
            linear = (codeValue/1023.0 - p['f']) / p['e']

        #print( codeValue, linear )
        return linear


    cs.toReferenceTransforms = []

    if transferFunction == "V3 LogC":
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = logCtoLinear(1023.0*c/(lutResolution1d-1), int(exposureIndex))

        lut = "%s_to_linear.spi1d" % ("%s_%s" % (transferFunction, exposureIndex))

        # Remove spaces and parentheses
        lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

        genlut.writeSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

        #print( "Writing %s" % lut)
        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

    if gamut == 'Wide Gamut':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([0.680206, 0.236137, 0.083658, 
                        0.085415, 1.017471, -0.102886, 
                        0.002057, -0.062563, 1.060506]),
            'direction':'forward'
        })

    cs.fromReferenceTransforms = []
    return cs

def createColorSpaces(lutDir, lutResolution1d):
    colorspaces = []

    transferFunction = "V3 LogC"
    gamut = "Wide Gamut"
    #EIs = [160.0, 200.0, 250.0, 320.0, 400.0, 500.0, 640.0, 800.0, 1000.0, 1280.0, 1600.0, 2000.0, 2560.0, 3200.0]
    EIs = [160, 200, 250, 320, 400, 500, 640, 800, 1000, 1280, 1600, 2000, 2560, 3200]
    defaultEI = 800

    # Full conversion
    for EI in EIs:
        LogCEIfull = createLogC(gamut, transferFunction, EI, "LogC", lutDir, lutResolution1d)
        colorspaces.append(LogCEIfull)

    # Linearization only
    for EI in [800]:
        LogCEIlinearization = createLogC("", transferFunction, EI, "LogC", lutDir, lutResolution1d)
        colorspaces.append(LogCEIlinearization)

    # Primaries
    LogCEIprimaries = createLogC(gamut, "", defaultEI, "LogC", lutDir, lutResolution1d)
    colorspaces.append(LogCEIprimaries)

    return colorspaces
