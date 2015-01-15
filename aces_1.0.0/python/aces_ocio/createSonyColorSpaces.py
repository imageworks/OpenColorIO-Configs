import array

import aces_ocio.generateLUT as genlut
from aces_ocio.util import ColorSpace, mat44FromMat33

#
# SLog to ACES
#
def createSlog(gamut, transferFunction, name, lutDir, lutResolution1d):
    name = "%s - %s" % (transferFunction, gamut)
    if transferFunction == "":
        name = "Linear - %s" % gamut
    if gamut == "":
        name = "%s" % transferFunction

    cs = ColorSpace(name)
    cs.description = name
    cs.equalityGroup = ''
    cs.family = 'Sony'
    cs.isData=False

    def sLog1ToLinear(SLog):
        b = 64.
        ab = 90.
        w = 940.

        if (SLog >= ab):
            lin = ( pow(10., ( ( ( SLog - b) / ( w - b) - 0.616596 - 0.03) / 0.432699)) - 0.037584) * 0.9
        else:
            lin = ( ( ( SLog - b) / ( w - b) - 0.030001222851889303) / 5.) * 0.9 
        return lin

    def sLog2ToLinear(SLog):
        b = 64.
        ab = 90.
        w = 940.

        if (SLog >= ab):
            lin = ( 219. * ( pow(10., ( ( ( SLog - b) / ( w - b) - 0.616596 - 0.03) / 0.432699)) - 0.037584) / 155.) * 0.9
        else:
            lin = ( ( ( SLog - b) / ( w - b) - 0.030001222851889303) / 3.53881278538813) * 0.9
        return lin

    def sLog3ToLinear(codeValue):
        if codeValue >= (171.2102946929):
            linear = pow(10.0, ((codeValue - 420.0) / 261.5)) * (0.18 + 0.01) - 0.01
        else:
            linear = (codeValue - 95.0)*0.01125000/(171.2102946929 - 95.0)
        #print( codeValue, linear )
        return linear

    cs.toReferenceTransforms = []

    if transferFunction == "S-Log1":
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = sLog1ToLinear(1023.0*c/(lutResolution1d-1))

        lut = "%s_to_linear.spi1d" % transferFunction
        genlut.writeSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

        #print( "Writing %s" % lut)

        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )
    elif transferFunction == "S-Log2":
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = sLog2ToLinear(1023.0*c/(lutResolution1d-1))

        lut = "%s_to_linear.spi1d" % transferFunction
        genlut.writeSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

        #print( "Writing %s" % lut)

        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )
    elif transferFunction == "S-Log3":
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = sLog3ToLinear(1023.0*c/(lutResolution1d-1))

        lut = "%s_to_linear.spi1d" % transferFunction
        genlut.writeSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

        #print( "Writing %s" % lut)

        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

    if gamut == 'S-Gamut':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([0.754338638, 0.133697046, 0.111968437,
                                    0.021198141, 1.005410934, -0.026610548, 
                                    -0.009756991, 0.004508563, 1.005253201]),
            'direction':'forward'
        })
    elif gamut == 'S-Gamut Daylight':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([0.8764457030, 0.0145411681, 0.1090131290,
                                    0.0774075345, 0.9529571767, -0.0303647111, 
                                    0.0573564351, -0.1151066335, 1.0577501984]),
            'direction':'forward'
        })
    elif gamut == 'S-Gamut Tungsten':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([1.0110238740, -0.1362526051, 0.1252287310, 
                        0.1011994504, 0.9562196265, -0.0574190769,
                        0.0600766530, -0.1010185315, 1.0409418785]),
            'direction':'forward'
        })
    elif gamut == 'S-Gamut3.Cine':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([0.6387886672, 0.2723514337, 0.0888598992, 
                                    -0.0039159061, 1.0880732308, -0.0841573249, 
                                    -0.0299072021, -0.0264325799, 1.0563397820]),
            'direction':'forward'
        })
    elif gamut == 'S-Gamut3':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33([0.7529825954, 0.1433702162, 0.1036471884, 
                        0.0217076974, 1.0153188355, -0.0370265329, 
                        -0.0094160528, 0.0033704179, 1.0060456349]),
            'direction':'forward'
        })

    cs.fromReferenceTransforms = []
    return cs

def createColorSpaces(lutDir, lutResolution1d):
    colorspaces = []

    # SLog1
    SLog1SGamut = createSlog("S-Gamut", "S-Log1", "S-Log", lutDir, lutResolution1d)
    colorspaces.append(SLog1SGamut)

    # SLog2
    SLog2SGamut = createSlog("S-Gamut", "S-Log2", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SLog2SGamut)

    SLog2SGamutDaylight = createSlog("S-Gamut Daylight", "S-Log2", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SLog2SGamutDaylight)

    SLog2SGamutTungsten = createSlog("S-Gamut Tungsten", "S-Log2", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SLog2SGamutTungsten)

    # SLog3
    SLog3SGamut3Cine = createSlog("S-Gamut3.Cine", "S-Log3", "S-Log3", lutDir, lutResolution1d)
    colorspaces.append(SLog3SGamut3Cine)

    SLog3SGamut3 = createSlog("S-Gamut3", "S-Log3", "S-Log3", lutDir, lutResolution1d)
    colorspaces.append(SLog3SGamut3)

    # Linearization only
    SLog1 = createSlog("", "S-Log1", "S-Log", lutDir, lutResolution1d)
    colorspaces.append(SLog1)

    SLog2 = createSlog("", "S-Log2", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SLog2)

    SLog3 = createSlog("", "S-Log3", "S-Log3", lutDir, lutResolution1d)
    colorspaces.append(SLog3)

    # Primaries only
    SGamut = createSlog("S-Gamut", "", "S-Log", lutDir, lutResolution1d)
    colorspaces.append(SGamut)

    SGamutDaylight = createSlog("S-Gamut Daylight", "", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SGamutDaylight)

    SGamutTungsten = createSlog("S-Gamut Tungsten", "", "S-Log2", lutDir, lutResolution1d)
    colorspaces.append(SGamutTungsten)

    SGamut3Cine = createSlog("S-Gamut3.Cine", "", "S-Log3", lutDir, lutResolution1d)
    colorspaces.append(SGamut3Cine)

    SGamut3 = createSlog("S-Gamut3", "", "S-Log3", lutDir, lutResolution1d)
    colorspaces.append(SGamut3)

    return colorspaces

