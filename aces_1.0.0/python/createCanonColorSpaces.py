import array

from util import *
import generateLUT as genlut

#
# Canon-Log to ACES
#
def createCanonLog(gamut, transferFunction, name, lutDir, lutResolution1d):
    name = "%s - %s" % (transferFunction, gamut)
    if transferFunction == "":
        name = "Linear - %s" % gamut
    if gamut == "":
        name = "%s" % transferFunction

    cs = ColorSpace(name)
    cs.description = name
    cs.equalityGroup = ''
    cs.family = 'Canon'
    cs.isData=False

    def legalToFull(codeValue):
        return (codeValue - 64.0)/(940.0 - 64.0)

    def canonLogToLinear(codeValue):
        # log = fullToLegal(c1 * log10(c2*linear + 1) + c3)
        # linear = (pow(10, (legalToFul(log) - c3)/c1) - 1)/c2
        c1 = 0.529136
        c2 = 10.1596
        c3 = 0.0730597

        linear = (pow(10.0, (legalToFull(codeValue) - c3)/c1) -1.0)/c2
        linear = 0.9 * linear
        #print( codeValue, linear )
        return linear

    cs.toReferenceTransforms = []

    if transferFunction == "Canon-Log":
        data = array.array('f', "\0" * lutResolution1d * 4)
        for c in range(lutResolution1d):
            data[c] = canonLogToLinear(1023.0*c/(lutResolution1d-1))

        lut = "%s_to_linear.spi1d" % transferFunction
        genlut.writeSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

    if gamut == 'Rec. 709 Daylight':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.561538969, 0.402060105, 0.036400926, 0.0, 
                        0.092739623, 0.924121198, -0.016860821, 0.0, 
                        0.084812961, 0.006373835, 0.908813204, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })
    elif gamut == 'Rec. 709 Tungsten':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.566996399, 0.365079418, 0.067924183, 0.0, 
                        0.070901044, 0.880331008, 0.048767948, 0.0, 
                        0.073013542, -0.066540862, 0.99352732, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })
    elif gamut == 'DCI-P3 Daylight':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.607160575, 0.299507286, 0.093332140, 0.0, 
                        0.004968120, 1.050982224, -0.055950343, 0.0, 
                        -0.007839939, 0.000809127, 1.007030813, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })
    elif gamut == 'DCI-P3 Tungsten':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.650279125, 0.253880169, 0.095840706, 0.0, 
                        -0.026137986, 1.017900530, 0.008237456, 0.0, 
                        0.007757558, -0.063081669, 1.055324110, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })
    elif gamut == 'Cinema Gamut Daylight':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.763064455, 0.149021161, 0.087914384, 0.0, 
                        0.003657457, 1.10696038, -0.110617837, 0.0, 
                        -0.009407794,-0.218383305, 1.227791099, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })
    elif gamut == 'Cinema Gamut Tungsten':
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.817416293, 0.090755698, 0.091828009, 0.0, 
                        -0.035361374, 1.065690585, -0.030329211, 0.0, 
                        0.010390366, -0.299271107, 1.288880741, 0.0, 
                        0,0,0,1.0],
            'direction':'forward'
        })

    cs.fromReferenceTransforms = []
    return cs

# Generate all color spaces conversion
def createColorSpaces(lutDir, lutResolution1d):
    colorspaces = []

    # Full conversion
    CanonLog1 = createCanonLog("Rec. 709 Daylight", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog1)

    CanonLog2 = createCanonLog("Rec. 709 Tungsten", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog2)

    CanonLog3 = createCanonLog("DCI-P3 Daylight", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog3)

    CanonLog4 = createCanonLog("DCI-P3 Tungsten", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog4)

    CanonLog5 = createCanonLog("Cinema Gamut Daylight", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog5)

    CanonLog6 = createCanonLog("Cinema Gamut Tungsten", "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog6)

    # Linearization only
    CanonLog7 = createCanonLog('', "Canon-Log", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog7)

    # Primaries only
    CanonLog8 = createCanonLog("Rec. 709 Daylight", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog8)

    CanonLog9 = createCanonLog("Rec. 709 Tungsten", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog9)

    CanonLog10 = createCanonLog("DCI-P3 Daylight", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog10)

    CanonLog11 = createCanonLog("DCI-P3 Tungsten", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog11)

    CanonLog12 = createCanonLog("Cinema Gamut Daylight", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog12)

    CanonLog13 = createCanonLog("Cinema Gamut Tungsten", "", "Canon-Log", lutDir, lutResolution1d)
    colorspaces.append(CanonLog13)

    return colorspaces
