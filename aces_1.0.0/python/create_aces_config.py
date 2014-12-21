'''
usage from python

import sys
sys.path.append( "/path/to/script" )
import create_aces_config as cac
acesReleaseCTLDir = "/path/to/github/checkout/releases/v0.7.1/transforms/ctl"
configDir = "/path/to/config/dir"
cac.createACESConfig(acesReleaseCTLDir, configDir, 1024, 33, True)

usage from command line, from the directory with 'create_aces_config.py'
python create_aces_config.py -a "/path/to/github/checkout/releases/v0.7.1/transforms/ctl" -c "/path/to/config/dir" --lutResolution1d 1024 --lutResolution3d 33 --keepTempImages



build instructions for osx for needed packages.

#opencolorio
brew install -vd opencolorio --with-python

#openimageio
brew tap homebrew/science

# optional installs
brew install -vd libRaw
brew install -vd OpenCV

brew install -vd openimageio --with-python

#ctl
brew install -vd CTL

#opencolorio - again.
# this time, 'ociolutimage' will build because openimageio is installed
brew uninstall -vd opencolorio
brew install -vd opencolorio --with-python
'''

import sys
import os
import array
import shutil
import string
import pprint
import math
import numpy

import OpenImageIO as oiio
import PyOpenColorIO as OCIO

import process

#
# Utility functions
#
def setConfigDefaultRoles( config, 
    color_picking="",
    color_timing="",
    compositing_log="",
    data="",
    default="",
    matte_paint="",
    reference="",
    scene_linear="",
    texture_paint=""):
    
    # Add Roles
    if color_picking: config.setRole( OCIO.Constants.ROLE_COLOR_PICKING, color_picking )
    if color_timing: config.setRole( OCIO.Constants.ROLE_COLOR_TIMING, color_timing )
    if compositing_log: config.setRole( OCIO.Constants.ROLE_COMPOSITING_LOG, compositing_log )
    if data: config.setRole( OCIO.Constants.ROLE_DATA, data )
    if default: config.setRole( OCIO.Constants.ROLE_DEFAULT, default )
    if matte_paint: config.setRole( OCIO.Constants.ROLE_MATTE_PAINT, matte_paint )
    if reference: config.setRole( OCIO.Constants.ROLE_REFERENCE, reference )
    if scene_linear: config.setRole( OCIO.Constants.ROLE_SCENE_LINEAR, scene_linear )
    if texture_paint: config.setRole( OCIO.Constants.ROLE_TEXTURE_PAINT, texture_paint )
    
    

# Write config to disk
def writeConfig( config, configPath, sanityCheck=True ):
    if sanityCheck:
        try:
            config.sanityCheck()
        except Exception,e:
            print e
            print "Configuration was not written due to a failed Sanity Check"
            return
            #sys.exit()

    fileHandle = open( configPath, mode='w' )
    fileHandle.write( config.serialize() )
    fileHandle.close()

#
# Functions used to generate LUTs using CTL transforms
#
def generate1dLUTImage(ramp1dPath, resolution=1024, minValue=0.0, maxValue=1.0):
    #print( "Generate 1d LUT image - %s" % ramp1dPath)

    # open image
    format = os.path.splitext(ramp1dPath)[1]
    ramp = oiio.ImageOutput.create(ramp1dPath)

    # set image specs
    spec = oiio.ImageSpec()
    spec.set_format( oiio.FLOAT )
    #spec.format.basetype = oiio.FLOAT
    spec.width = resolution
    spec.height = 1
    spec.nchannels = 3

    ramp.open (ramp1dPath, spec, oiio.Create)

    data = array.array("f", "\0" * spec.width * spec.height * spec.nchannels * 4)
    for i in range(resolution):
        value = float(i)/(resolution-1) * (maxValue - minValue) + minValue
        data[i*spec.nchannels +0] = value
        data[i*spec.nchannels +1] = value
        data[i*spec.nchannels +2] = value

    ramp.write_image(spec.format, data)
    ramp.close()

# Credit to Alex Fry for the original single channel version of the spi1d writer
def WriteSPI1D(filename, fromMin, fromMax, data, entries, channels):
    f = file(filename,'w')
    f.write("Version 1\n")
    f.write("From %f %f\n" % (fromMin, fromMax))
    f.write("Length %d\n" % entries)
    f.write("Components %d\n" % (min(3, channels)) )
    f.write("{\n")
    for i in range(0, entries):
        entry = ""
        for j in range(0, min(3, channels)):
            entry = "%s %s" % (entry, data[i*channels + j])
        f.write("        %s\n" % entry)
    f.write("}\n")
    f.close()

def generate1dLUTFromImage(ramp1dPath, outputPath=None, minValue=0.0, maxValue=1.0):
    if outputPath == None:
        outputPath = ramp1dPath + ".spi1d"

    # open image
    ramp = oiio.ImageInput.open( ramp1dPath )

    # get image specs
    spec = ramp.spec()
    type = spec.format.basetype
    width = spec.width
    height = spec.height
    channels = spec.nchannels

    # get data
    # Force data to be read as float. The Python API doesn't handle half-floats well yet.
    type = oiio.FLOAT
    data = ramp.read_image(type)

    WriteSPI1D(outputPath, minValue, maxValue, data, width, channels)

def generate3dLUTImage(ramp3dPath, resolution=32):
    args = ["--generate", "--cubesize", str(resolution), "--maxwidth", str(resolution*resolution), "--output", ramp3dPath]
    lutExtract = process.Process(description="generate a 3d LUT image", cmd="ociolutimage", args=args)
    lutExtract.execute()    

def generate3dLUTFromImage(ramp3dPath, outputPath=None, resolution=32):
    if outputPath == None:
        outputPath = ramp3dPath + ".spi3d"

    args = ["--extract", "--cubesize", str(resolution), "--maxwidth", str(resolution*resolution), "--input", ramp3dPath, "--output", outputPath]
    lutExtract = process.Process(description="extract a 3d LUT", cmd="ociolutimage", args=args)
    lutExtract.execute()    

def applyCTLToImage(inputImage, 
    outputImage, 
    ctlPaths=[], 
    inputScale=1.0, 
    outputScale=1.0, 
    globalParams={},
    acesCTLReleaseDir=None):
    if len(ctlPaths) > 0:
        ctlenv = os.environ
        if acesCTLReleaseDir != None:
            ctlModulePath = "%s/utilities" % acesCTLReleaseDir
            ctlenv['CTL_MODULE_PATH'] = ctlModulePath

        args = []
        for ctl in ctlPaths:
            args += ['-ctl', ctl]
        args += ["-force"]
        #args += ["-verbose"]
        args += ["-input_scale", str(inputScale)]
        args += ["-output_scale", str(outputScale)]
        args += ["-global_param1", "aIn", "1.0"]
        for key, value in globalParams.iteritems():
            args += ["-global_param1", key, str(value)]
        args += [inputImage]
        args += [outputImage]

        #print( "args : %s" % args )

        ctlp = process.Process(description="a ctlrender process", cmd="ctlrender", args=args, env=ctlenv )

        ctlp.execute()

def convertBitDepth(inputImage, outputImage, depth):
    args = [inputImage, "-d", depth, "-o", outputImage]
    convert = process.Process(description="convert image bit depth", cmd="oiiotool", args=args)
    convert.execute()    

def generate1dLUTFromCTL(lutPath, 
    ctlPaths, 
    lutResolution=1024, 
    identityLutBitDepth='half', 
    inputScale=1.0, 
    outputScale=1.0,
    globalParams={},
    cleanup=True,
    acesCTLReleaseDir=None,
    minValue=0.0,
    maxValue=1.0):
    #print( lutPath )
    #print( ctlPaths )

    lutPathBase = os.path.splitext(lutPath)[0]

    identityLUTImageFloat = lutPathBase + ".float.tiff"
    generate1dLUTImage(identityLUTImageFloat, lutResolution, minValue, maxValue)

    if identityLutBitDepth != 'half':
        identityLUTImage = lutPathBase + ".uint16.tiff"
        convertBitDepth(identityLUTImageFloat, identityLUTImage, identityLutBitDepth)
    else:
        identityLUTImage = identityLUTImageFloat

    transformedLUTImage = lutPathBase + ".transformed.exr"
    applyCTLToImage(identityLUTImage, transformedLUTImage, ctlPaths, inputScale, outputScale, globalParams, acesCTLReleaseDir)

    generate1dLUTFromImage(transformedLUTImage, lutPath, minValue, maxValue)

    if cleanup:
        os.remove(identityLUTImage)
        if identityLUTImage != identityLUTImageFloat:
            os.remove(identityLUTImageFloat)
        os.remove(transformedLUTImage)

def correctLUTImage(transformedLUTImage, correctedLUTImage, lutResolution):
    # open image
    transformed = oiio.ImageInput.open( transformedLUTImage )

    # get image specs
    transformedSpec = transformed.spec()
    type = transformedSpec.format.basetype
    width = transformedSpec.width
    height = transformedSpec.height
    channels = transformedSpec.nchannels

    # rotate or not
    if width != lutResolution * lutResolution or height != lutResolution:
        print( "Correcting image as resolution is off. Found %d x %d. Expected %d x %d" % (width, height, lutResolution * lutResolution, lutResolution) )
        print( "Generating %s" % correctedLUTImage)

        #
        # We're going to generate a new correct image
        #

        # Get the source data
        # Force data to be read as float. The Python API doesn't handle half-floats well yet.
        type = oiio.FLOAT
        sourceData = transformed.read_image(type)

        format = os.path.splitext(correctedLUTImage)[1]
        correct = oiio.ImageOutput.create(correctedLUTImage)

        # set image specs
        correctSpec = oiio.ImageSpec()
        correctSpec.set_format( oiio.FLOAT )
        correctSpec.width = height
        correctSpec.height = width
        correctSpec.nchannels = channels

        correct.open (correctedLUTImage, correctSpec, oiio.Create)

        destData = array.array("f", "\0" * correctSpec.width * correctSpec.height * correctSpec.nchannels * 4)
        for j in range(0, correctSpec.height):
            for i in range(0, correctSpec.width):
                for c in range(0, correctSpec.nchannels):
                    #print( i, j, c )
                    destData[correctSpec.nchannels*correctSpec.width*j + correctSpec.nchannels*i + c] = sourceData[correctSpec.nchannels*correctSpec.width*j + correctSpec.nchannels*i + c]

        correct.write_image(correctSpec.format, destData)
        correct.close()
    else:
        #shutil.copy(transformedLUTImage, correctedLUTImage)
        correctedLUTImage = transformedLUTImage

    transformed.close()

    return correctedLUTImage

def generate3dLUTFromCTL(lutPath, 
    ctlPaths, 
    lutResolution=64, 
    identityLutBitDepth='half', 
    inputScale=1.0,
    outputScale=1.0, 
    globalParams={},
    cleanup=True,
    acesCTLReleaseDir=None):
    #print( lutPath )
    #print( ctlPaths )

    lutPathBase = os.path.splitext(lutPath)[0]

    identityLUTImageFloat = lutPathBase + ".float.tiff"
    generate3dLUTImage(identityLUTImageFloat, lutResolution)


    if identityLutBitDepth != 'half':
        identityLUTImage = lutPathBase + "." + identityLutBitDepth + ".tiff"
        convertBitDepth(identityLUTImageFloat, identityLUTImage, identityLutBitDepth)
    else:
        identityLUTImage = identityLUTImageFloat

    transformedLUTImage = lutPathBase + ".transformed.exr"
    applyCTLToImage(identityLUTImage, transformedLUTImage, ctlPaths, inputScale, outputScale, globalParams, acesCTLReleaseDir)

    correctedLUTImage = lutPathBase + ".correct.exr"
    correctedLUTImage = correctLUTImage(transformedLUTImage, correctedLUTImage, lutResolution)    

    generate3dLUTFromImage(correctedLUTImage, lutPath, lutResolution)

    if cleanup:
        os.remove(identityLUTImage)
        if identityLUTImage != identityLUTImageFloat:
            os.remove(identityLUTImageFloat)
        os.remove(transformedLUTImage)
        if correctedLUTImage != transformedLUTImage:
            os.remove(correctedLUTImage)
        #os.remove(correctedLUTImage)

def generateOCIOTransform(transforms):
    #print( "Generating transforms")

    interpolationOptions = { 
        'linear':OCIO.Constants.INTERP_LINEAR,
        'nearest':OCIO.Constants.INTERP_NEAREST, 
        'tetrahedral':OCIO.Constants.INTERP_TETRAHEDRAL 
    }
    directionOptions = { 
        'forward':OCIO.Constants.TRANSFORM_DIR_FORWARD,
        'inverse':OCIO.Constants.TRANSFORM_DIR_INVERSE 
    }

    ocioTransforms = []

    for transform in transforms:
        if transform['type'] == 'lutFile':

            ocioTransform = OCIO.FileTransform( src=transform['path'],
                interpolation=interpolationOptions[transform['interpolation']],
                direction=directionOptions[transform['direction']] )

            ocioTransforms.append(ocioTransform)
        elif transform['type'] == 'matrix':
            ocioTransform = OCIO.MatrixTransform()
            # MatrixTransform member variables can't be initialized directly. Each must be set individually
            ocioTransform.setMatrix( transform['matrix'] )

            if 'offset' in transform:
                ocioTransform.setOffset( transform['offset'] )
            if 'direction' in transform:
                ocioTransform.setDirection( directionOptions[transform['direction']] )

            ocioTransforms.append(ocioTransform)
        elif transform['type'] == 'exponent':
            ocioTransform = OCIO.ExponentTransform()
            ocioTransform.setValue( transform['value'] )

            ocioTransforms.append(ocioTransform)
        elif transform['type'] == 'log':
            ocioTransform = OCIO.LogTransform(base=transform['base'],
                direction=directionOptions[transform['direction']])

            ocioTransforms.append(ocioTransform)
        else:
            print( "Ignoring unknown transform type : %s" % transform['type'] )

    # Build a group transform if necessary
    if len(ocioTransforms) > 1:
        transformG = OCIO.GroupTransform()
        for transform in ocioTransforms:
            transformG.push_back( transform )
        transform = transformG

    # Or take the first transform from the list
    else:
        transform = ocioTransforms[0]

    return transform

def createConfig(configData, nuke=False):
    # Create the config
    config = OCIO.Config()
    
    #
    # Set config wide values
    #
    config.setDescription( "An ACES config generated from python" )
    config.setSearchPath( "luts" )
    
    #
    # Define the reference color space
    #
    referenceData = configData['referenceColorSpace']
    print( "Adding the reference color space : %s" % referenceData.name)

    # Create a color space
    reference = OCIO.ColorSpace( name=referenceData.name, 
        bitDepth=referenceData.bitDepth, 
        description=referenceData.description, 
        equalityGroup=referenceData.equalityGroup, 
        family=referenceData.family, 
        isData=referenceData.isData, 
        allocation=referenceData.allocationType, 
        allocationVars=referenceData.allocationVars ) 

    # Add to config
    config.addColorSpace( reference )

    #
    # Create the rest of the color spaces
    #
    #sortedColorspaces = sorted(configData['colorSpaces'], key=lambda x: x.name)
    #print( sortedColorspaces )
    #for colorspace in sortedColorspaces:
    for colorspace in sorted(configData['colorSpaces']):
        print( "Creating new color space : %s" % colorspace.name)

        ocioColorspace = OCIO.ColorSpace( name=colorspace.name, 
            bitDepth=colorspace.bitDepth, 
            description=colorspace.description, 
            equalityGroup=colorspace.equalityGroup, 
            family=colorspace.family, 
            isData=colorspace.isData,
            allocation=colorspace.allocationType, 
            allocationVars=colorspace.allocationVars ) 

        if colorspace.toReferenceTransforms != []:
            print( "Generating To-Reference transforms")
            ocioTransform = generateOCIOTransform(colorspace.toReferenceTransforms)
            ocioColorspace.setTransform( ocioTransform, OCIO.Constants.COLORSPACE_DIR_TO_REFERENCE )

        if colorspace.fromReferenceTransforms != []:
            print( "Generating From-Reference transforms")
            ocioTransform = generateOCIOTransform(colorspace.fromReferenceTransforms)
            ocioColorspace.setTransform( ocioTransform, OCIO.Constants.COLORSPACE_DIR_FROM_REFERENCE )

        config.addColorSpace(ocioColorspace)

        print( "" )

    #
    # Define the views and displays
    #
    displays = []
    views = []

    # Generic display and view setup
    if not nuke:
        for display, viewList in configData['displays'].iteritems():
            for viewName, colorspace in viewList.iteritems():
                config.addDisplay( display, viewName, colorspace.name )
                if not (viewName in views):
                    views.append(viewName)
            displays.append(display)
    # A Nuke specific set of views and displays
    #
    # XXX
    # A few names: Output Transform, ACES, ACEScc, are hard-coded here. Would be better to automate
    #
    else:
        for display, viewList in configData['displays'].iteritems():
            for viewName, colorspace in viewList.iteritems():
                if( viewName == 'Output Transform'):
                    viewName = 'View'
                    config.addDisplay( display, viewName, colorspace.name )
                    if not (viewName in views):
                        views.append(viewName)
            displays.append(display)

        config.addDisplay( 'linear', 'View', 'ACES2065-1' )
        displays.append('linear')
        config.addDisplay( 'log', 'View', 'ACEScc' )
        displays.append('log')

    # Set active displays and views
    config.setActiveDisplays( ','.join(sorted(displays)) )
    config.setActiveViews( ','.join(views) )

    #
    # Need to generalize this at some point
    #

    # Add Default Roles
    setConfigDefaultRoles( config, 
        color_picking=reference.getName(),
        color_timing=reference.getName(),
        compositing_log=reference.getName(),
        data=reference.getName(),
        default=reference.getName(),
        matte_paint=reference.getName(),
        reference=reference.getName(),
        scene_linear=reference.getName(),
        texture_paint=reference.getName() )

    # Check to make sure we didn't screw something up
    config.sanityCheck()

    return config

#
# Functions to generate color space definitions and LUTs for transforms for a specific ACES release
#
class ColorSpace:
    "A container for data needed to define an OCIO 'Color Space' "

    def __init__(self, 
        name, 
        description=None, 
        bitDepth=OCIO.Constants.BIT_DEPTH_F32,
        equalityGroup=None,
        family=None,
        isData=False,
        toReferenceTransforms=[],
        fromReferenceTransforms=[],
        allocationType=OCIO.Constants.ALLOCATION_UNIFORM,
        allocationVars=[0.0, 1.0]):
        "Initialize the standard class variables"
        self.name = name
        self.bitDepth=bitDepth
        self.description = description
        self.equalityGroup=equalityGroup
        self.family=family 
        self.isData=isData
        self.toReferenceTransforms=toReferenceTransforms
        self.fromReferenceTransforms=fromReferenceTransforms
        self.allocationType=allocationType
        self.allocationVars=allocationVars

# Create a 4x4 matrix (list) based on a 3x3 matrix (list) input
def mat44FromMat33(mat33):
    return [mat33[0], mat33[1], mat33[2], 0.0, 
            mat33[3], mat33[4], mat33[5], 0.0, 
            mat33[6], mat33[7], mat33[8], 0.0, 
            0,0,0,1.0]


# Output is a list of colorspaces and transforms that convert between those
# colorspaces and reference color space, ACES
def generateLUTs(odtInfo, lmtInfo, shaperName, acesCTLReleaseDir, lutDir, lutResolution1d=4096, lutResolution3d=64, cleanup=True):
    print( "generateLUTs - begin" )
    configData = {}

    #
    # Define the reference color space
    #
    ACES = ColorSpace('ACES2065-1')
    ACES.description = "The Academy Color Encoding System reference color space"
    ACES.equalityGroup = ''
    ACES.family = 'ACES'
    ACES.isData=False
    ACES.allocationType=OCIO.Constants.ALLOCATION_LG2
    ACES.allocationVars=[-15, 6]

    configData['referenceColorSpace'] = ACES

    #
    # Define the displays
    #
    configData['displays'] = {}

    #
    # Define the other color spaces
    #
    configData['colorSpaces'] = []

    # Matrix converting ACES AP1 primaries to AP0
    acesAP1toAP0 = [0.6954522414, 0.1406786965, 0.1638690622,
                    0.0447945634, 0.8596711185, 0.0955343182,
                    -0.0055258826, 0.0040252103, 1.0015006723]

    #
    # ACEScc
    #
    def createACEScc(name='ACEScc', minValue=0.0, maxValue=1.0, inputScale=1.0):
        cs = ColorSpace(name)
        cs.description = "The %s color space" % name
        cs.equalityGroup = ''
        cs.family = 'ACES'
        cs.isData=False

        ctls = [
            '%s/ACEScc/ACEScsc.ACEScc_to_ACES.a1.0.0.ctl' % acesCTLReleaseDir,
            # This transform gets back to the AP1 primaries
            # Useful to the 1d LUT is only covering the transfer function
            # The primaries switch is covered by the matrix below
            '%s/ACEScg/ACEScsc.ACES_to_ACEScg.a1.0.0.ctl' % acesCTLReleaseDir
        ]
        lut = "%s_to_ACES.spi1d" % name
        generate1dLUTFromCTL( lutDir + "/" + lut, 
            ctls, 
            lutResolution1d, 
            'float', 
            inputScale,
            1.0, 
            {},
            cleanup, 
            acesCTLReleaseDir,
            minValue,
            maxValue)

        cs.toReferenceTransforms = []
        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

        # AP1 primaries to AP0 primaries
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33(acesAP1toAP0),
            'direction':'forward'
        })

        cs.fromReferenceTransforms = []
        return cs

    ACEScc = createACEScc()
    configData['colorSpaces'].append(ACEScc)

    #
    # ACESproxy
    #
    def createACESProxy(name='ACESproxy'):
        cs = ColorSpace(name)
        cs.description = "The %s color space" % name
        cs.equalityGroup = ''
        cs.family = 'ACES'
        cs.isData=False

        ctls = [
            '%s/ACESproxy/ACEScsc.ACESproxy10i_to_ACES.a1.0.0.ctl' % acesCTLReleaseDir,
            # This transform gets back to the AP1 primaries
            # Useful to the 1d LUT is only covering the transfer function
            # The primaries switch is covered by the matrix below
            '%s/ACEScg/ACEScsc.ACES_to_ACEScg.a1.0.0.ctl' % acesCTLReleaseDir
        ]
        lut = "%s_to_aces.spi1d" % name
        generate1dLUTFromCTL( lutDir + "/" + lut, 
            ctls, 
            lutResolution1d, 
            'uint16', 
            64.0,
            1.0, 
            {},
            cleanup, 
            acesCTLReleaseDir )

        cs.toReferenceTransforms = []
        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

        # AP1 primaries to AP0 primaries
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33(acesAP1toAP0),
            'direction':'forward'
        })


        cs.fromReferenceTransforms = []
        return cs

    ACESproxy = createACESProxy()
    configData['colorSpaces'].append(ACESproxy)

    #
    # ACEScg
    #
    def createACEScg(name='ACEScg'):
        cs = ColorSpace(name)
        cs.description = "The %s color space" % name
        cs.equalityGroup = ''
        cs.family = 'ACES'
        cs.isData=False

        cs.toReferenceTransforms = []

        # AP1 primaries to AP0 primaries
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':mat44FromMat33(acesAP1toAP0),
            'direction':'forward'
        })

        cs.fromReferenceTransforms = []
        return cs

    ACEScg = createACEScg()
    configData['colorSpaces'].append(ACEScg)

    #
    # ADX
    #
    def createADX(bitdepth=10, name='ADX'):
        name = "%s%s" % (name, bitdepth)
        cs = ColorSpace(name)
        cs.description = "%s color space - used for film scans" % name
        cs.equalityGroup = ''
        cs.family = 'ADX'
        cs.isData=False

        if bitdepth == 10:
            cs.bitDepth = bitDepth=OCIO.Constants.BIT_DEPTH_UINT10
            adx_to_cdd = [1023.0/500.0, 0.0, 0.0, 0.0,
                        0.0, 1023.0/500.0, 0.0, 0.0,
                        0.0, 0.0, 1023.0/500.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]
            offset = [-95.0/500.0, -95.0/500.0, -95.0/500.0, 0.0]
        elif bitdepth == 16:
            cs.bitDepth = bitDepth=OCIO.Constants.BIT_DEPTH_UINT16
            adx_to_cdd = [65535.0/8000.0, 0.0, 0.0, 0.0,
                        0.0, 65535.0/8000.0, 0.0, 0.0,
                        0.0, 0.0, 65535.0/8000.0, 0.0,
                        0.0, 0.0, 0.0, 1.0]
            offset = [-1520.0/8000.0, -1520.0/8000.0, -1520.0/8000.0, 0.0]

        cs.toReferenceTransforms = []

        # Convert from ADX to Channel-Dependent Density
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':adx_to_cdd,
            'offset':offset,
            'direction':'forward'
        })

        # Convert from Channel-Dependent Density to Channel-Independent Density
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.75573, 0.22197, 0.02230, 0,
                        0.05901, 0.96928, -0.02829, 0,
                        0.16134, 0.07406, 0.76460, 0,
                        0.0, 0.0, 0.0, 1.0],
            'direction':'forward'
        })

        # Copied from Alex Fry's adx_cid_to_rle.py
        def createCIDtoRLELUT():
            def interpolate1D(x, xp, fp):
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

            REF_PT = (7120.0 - 1520.0) / 8000.0 * (100.0 / 55.0) - math.log(0.18, 10.0)

            def cid_to_rle(x):
                if x <= 0.6:
                    return interpolate1D(x, LUT_1D_xp, LUT_1D_fp)
                return (100.0 / 55.0) * x - REF_PT

            def Fit(value, fromMin, fromMax, toMin, toMax):
                if fromMin == fromMax:
                    raise ValueError("fromMin == fromMax")
                return (value - fromMin) / (fromMax - fromMin) * (toMax - toMin) + toMin

            NUM_SAMPLES = 2**12
            RANGE = (-0.19, 3.0)
            data = []
            for i in xrange(NUM_SAMPLES):
                x = i/(NUM_SAMPLES-1.0)
                x = Fit(x, 0.0, 1.0, RANGE[0], RANGE[1])
                data.append(cid_to_rle(x))

            lut = 'ADX_CID_to_RLE.spi1d'
            WriteSPI1D(lutDir + "/" + lut, RANGE[0], RANGE[1], data, NUM_SAMPLES, 1)

            return lut

        # Convert Channel Independent Density values to Relative Log Exposure values
        lut = createCIDtoRLELUT()
        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        })

        # Convert Relative Log Exposure values to Relative Exposure values
        cs.toReferenceTransforms.append( {
            'type':'log', 
            'base':10, 
            'direction':'inverse'
        })

        # Convert Relative Exposure values to ACES values
        cs.toReferenceTransforms.append( {
            'type':'matrix',
            'matrix':[0.72286, 0.12630, 0.15084, 0,
                        0.11923, 0.76418, 0.11659, 0,
                        0.01427, 0.08213, 0.90359, 0,
                        0.0, 0.0, 0.0, 1.0],
            'direction':'forward'
        })

        cs.fromReferenceTransforms = []
        return cs

    ADX10 = createADX(bitdepth=10)
    configData['colorSpaces'].append(ADX10)

    ADX16 = createADX(bitdepth=16)
    configData['colorSpaces'].append(ADX16)


    #
    # REDlogFilm to ACES
    #
    def createREDlogFilm(gamut, transferFunction, name='REDlogFilm'):
        name = "%s - %s" % (transferFunction, gamut)
        if transferFunction == "":
            name = "Linear - %s" % gamut
        if gamut == "":
            name = "%s" % transferFunction

        cs = ColorSpace(name)
        cs.description = name
        cs.equalityGroup = ''
        cs.family = 'RED'
        cs.isData=False

        def cineonToLinear(codeValue):
            nGamma = 0.6
            blackPoint = 95.0
            whitePoint = 685.0
            codeValueToDensity = 0.002

            blackLinear = pow(10.0, (blackPoint - whitePoint) * (codeValueToDensity / nGamma))
            codeLinear = pow(10.0, (codeValue - whitePoint) * (codeValueToDensity / nGamma))

            return (codeLinear - blackLinear)/(1.0 - blackLinear)

        cs.toReferenceTransforms = []

        if transferFunction == 'REDlogFilm':
            data = array.array('f', "\0" * lutResolution1d * 4)
            for c in range(lutResolution1d):
                data[c] = cineonToLinear(1023.0*c/(lutResolution1d-1))

            lut = "CineonLog_to_linear.spi1d"
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

            cs.toReferenceTransforms.append( {
                'type':'lutFile', 
                'path':lut, 
                'interpolation':'linear', 
                'direction':'forward'
            } )

        if gamut == 'DRAGONcolor':
            cs.toReferenceTransforms.append( {
                'type':'matrix',
                'matrix':mat44FromMat33([0.532279, 0.376648, 0.091073, 
                                        0.046344, 0.974513, -0.020860, 
                                        -0.053976, -0.000320, 1.054267]),
                'direction':'forward'
            })
        elif gamut == 'REDcolor3':
            cs.toReferenceTransforms.append( {
                'type':'matrix',
                'matrix':mat44FromMat33([0.512136, 0.360370, 0.127494, 
                                        0.070377, 0.903884, 0.025737, 
                                        -0.020824, 0.017671, 1.003123]),
                'direction':'forward'
            })
        elif gamut == 'REDcolor2':
            cs.toReferenceTransforms.append( {
                'type':'matrix',
                'matrix':mat44FromMat33([0.480997, 0.402289, 0.116714, 
                                        -0.004938, 1.000154, 0.004781, 
                                        -0.105257, 0.025320, 1.079907]),
                'direction':'forward'
            })

        cs.fromReferenceTransforms = []
        return cs

    # Full conversion
    REDlogFilmDRAGON = createREDlogFilm("DRAGONcolor", "REDlogFilm", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmDRAGON)

    REDlogFilmREDcolor2 = createREDlogFilm("REDcolor2", "REDlogFilm", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmREDcolor2)

    REDlogFilmREDcolor3 = createREDlogFilm("REDcolor3", "REDlogFilm", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmREDcolor3)

    # Linearization only
    REDlogFilmDRAGON = createREDlogFilm("", "REDlogFilm", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmDRAGON)

    # Primaries only
    REDlogFilmDRAGON = createREDlogFilm("DRAGONcolor", "", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmDRAGON)

    REDlogFilmREDcolor2 = createREDlogFilm("REDcolor2", "", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmREDcolor2)

    REDlogFilmREDcolor3 = createREDlogFilm("REDcolor3", "", name="REDlogFilm")
    configData['colorSpaces'].append(REDlogFilmREDcolor3)

    #
    # Canon-Log to ACES
    #
    def createCanonLog(gamut, transferFunction, name='Canon-Log'):
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
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

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

    # Full conversion
    CanonLog1 = createCanonLog("Rec. 709 Daylight", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog1)

    CanonLog2 = createCanonLog("Rec. 709 Tungsten", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog2)

    CanonLog3 = createCanonLog("DCI-P3 Daylight", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog3)

    CanonLog4 = createCanonLog("DCI-P3 Tungsten", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog4)

    CanonLog5 = createCanonLog("Cinema Gamut Daylight", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog5)

    CanonLog6 = createCanonLog("Cinema Gamut Tungsten", "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog6)

    # Linearization only
    CanonLog7 = createCanonLog('', "Canon-Log", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog7)

    # Primaries only
    CanonLog8 = createCanonLog("Rec. 709 Daylight", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog8)

    CanonLog9 = createCanonLog("Rec. 709 Tungsten", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog9)

    CanonLog10 = createCanonLog("DCI-P3 Daylight", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog10)

    CanonLog11 = createCanonLog("DCI-P3 Tungsten", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog11)

    CanonLog12 = createCanonLog("Cinema Gamut Daylight", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog12)

    CanonLog13 = createCanonLog("Cinema Gamut Tungsten", "", name="Canon-Log")
    configData['colorSpaces'].append(CanonLog13)

    #
    # SLog to ACES
    #
    def createSlog(gamut, transferFunction, name='S-Log3'):
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
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

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
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

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
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

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

    # SLog1
    SLog1SGamut = createSlog("S-Gamut", "S-Log1", name="S-Log")
    configData['colorSpaces'].append(SLog1SGamut)

    # SLog2
    SLog2SGamut = createSlog("S-Gamut", "S-Log2", name="S-Log2")
    configData['colorSpaces'].append(SLog2SGamut)

    SLog2SGamutDaylight = createSlog("S-Gamut Daylight", "S-Log2", name="S-Log2")
    configData['colorSpaces'].append(SLog2SGamutDaylight)

    SLog2SGamutTungsten = createSlog("S-Gamut Tungsten", "S-Log2", name="S-Log2")
    configData['colorSpaces'].append(SLog2SGamutTungsten)

    # SLog3
    SLog3SGamut3Cine = createSlog("S-Gamut3.Cine", "S-Log3", name="S-Log3")
    configData['colorSpaces'].append(SLog3SGamut3Cine)

    SLog3SGamut3 = createSlog("S-Gamut3", "S-Log3", name="S-Log3")
    configData['colorSpaces'].append(SLog3SGamut3)

    # Linearization only
    SLog1 = createSlog("", "S-Log1", name="S-Log")
    configData['colorSpaces'].append(SLog1)

    SLog2 = createSlog("", "S-Log2", name="S-Log2")
    configData['colorSpaces'].append(SLog2)

    SLog3 = createSlog("", "S-Log3", name="S-Log3")
    configData['colorSpaces'].append(SLog3)

    # Primaries only
    SGamut = createSlog("S-Gamut", "", name="S-Log")
    configData['colorSpaces'].append(SGamut)

    SGamutDaylight = createSlog("S-Gamut Daylight", "", name="S-Log2")
    configData['colorSpaces'].append(SGamutDaylight)

    SGamutTungsten = createSlog("S-Gamut Tungsten", "", name="S-Log2")
    configData['colorSpaces'].append(SGamutTungsten)

    SGamut3Cine = createSlog("S-Gamut3.Cine", "", name="S-Log3")
    configData['colorSpaces'].append(SGamut3Cine)

    SGamut3 = createSlog("S-Gamut3", "", name="S-Log3")
    configData['colorSpaces'].append(SGamut3)

    #
    # LogC to ACES
    #
    def createLogC(gamut, transferFunction, exposureIndex, name='LogC'):
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
            WriteSPI1D(lutDir + "/" + lut, 0.0, 1.0, data, lutResolution1d, 1)

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

    transferFunction = "V3 LogC"
    gamut = "Wide Gamut"
    #EIs = [160.0, 200.0, 250.0, 320.0, 400.0, 500.0, 640.0, 800.0, 1000.0, 1280.0, 1600.0, 2000.0, 2560.0, 3200.0]
    EIs = [160, 200, 250, 320, 400, 500, 640, 800, 1000, 1280, 1600, 2000, 2560, 3200]
    defaultEI = 800

    # Full conversion
    for EI in EIs:
        LogCEIfull = createLogC(gamut, transferFunction, EI, name="LogC")
        configData['colorSpaces'].append(LogCEIfull)

    # Linearization only
    for EI in [800]:
        LogCEIlinearization = createLogC("", transferFunction, EI, name="LogC")
        configData['colorSpaces'].append(LogCEIlinearization)

    # Primaries
    LogCEIprimaries = createLogC(gamut, "", defaultEI, name="LogC")
    configData['colorSpaces'].append(LogCEIprimaries)

    #
    # Generic log transform
    #
    def createGenericLog(name='log', 
        minValue=0.0, 
        maxValue=1.0, 
        inputScale=1.0,
        middleGrey=0.18,
        minExposure=-6.0,
        maxExposure=6.5,
        lutResolution1d=lutResolution1d):
        cs = ColorSpace(name)
        cs.description = "The %s color space" % name
        cs.equalityGroup = name
        cs.family = 'Utility'
        cs.isData=False

        ctls = [
            #'%s/logShaper/logShaper16i_to_aces_param.ctl' % acesCTLReleaseDir
            '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl' % acesCTLReleaseDir
        ]
        lut = "%s_to_aces.spi1d" % name

        generate1dLUTFromCTL( lutDir + "/" + lut, 
            ctls, 
            lutResolution1d, 
            'float', 
            inputScale,
            1.0, 
            {
                'middleGrey'  : middleGrey,
                'minExposure' : minExposure,
                'maxExposure' : maxExposure
            },
            cleanup, 
            acesCTLReleaseDir,
            minValue,
            maxValue)

        cs.toReferenceTransforms = []
        cs.toReferenceTransforms.append( {
            'type':'lutFile', 
            'path':lut, 
            'interpolation':'linear', 
            'direction':'forward'
        } )

        cs.fromReferenceTransforms = []
        return cs

    #
    # ACES LMTs
    #
    def createACESLMT(lmtName, 
        lmtValues,
        shaperInfo,
        lutResolution1d=1024, 
        lutResolution3d=64, 
        cleanup=True):
        cs = ColorSpace("%s" % lmtName)
        cs.description = "The ACES Look Transform: %s" % lmtName
        cs.equalityGroup = ''
        cs.family = 'Look'
        cs.isData=False

        import pprint
        pprint.pprint( lmtValues )

        #
        # Generate the shaper transform
        #
        (shaperName, shaperToACESCTL, shaperFromACESCTL, shaperInputScale, shaperParams) = shaperInfo

        shaperLut = "%s_to_aces.spi1d" % shaperName
        if( not os.path.exists( lutDir + "/" + shaperLut ) ):
            ctls = [
                shaperToACESCTL % acesCTLReleaseDir
            ]
            generate1dLUTFromCTL( lutDir + "/" + shaperLut, 
                ctls, 
                lutResolution1d, 
                'float', 
                1.0/shaperInputScale,
                1.0, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir)

        shaperOCIOTransform = {
            'type':'lutFile', 
            'path':shaperLut, 
            'interpolation':'linear', 
            'direction':'inverse'
        }

        #
        # Generate the forward transform
        #
        cs.fromReferenceTransforms = []

        if 'transformCTL' in lmtValues:
            ctls = [
                shaperToACESCTL % acesCTLReleaseDir, 
                '%s/%s' % (acesCTLReleaseDir, lmtValues['transformCTL'])
            ]
            lut = "%s.%s.spi3d" % (shaperName, lmtName)

            generate3dLUTFromCTL( lutDir + "/" + lut, 
                ctls, 
                lutResolution3d, 
                'float', 
                1.0/shaperInputScale,
                1.0, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir )

            cs.fromReferenceTransforms.append( shaperOCIOTransform )
            cs.fromReferenceTransforms.append( {
                'type':'lutFile', 
                'path':lut, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )

        #
        # Generate the inverse transform
        #
        cs.toReferenceTransforms = []

        if 'transformCTLInverse' in lmtValues:
            ctls = [
                '%s/%s' % (acesCTLReleaseDir, odtValues['transformCTLInverse']),
                shaperFromACESCTL % acesCTLReleaseDir
            ]
            lut = "Inverse.%s.%s.spi3d" % (odtName, shaperName)

            generate3dLUTFromCTL( lutDir + "/" + lut, 
                ctls, 
                lutResolution3d, 
                'half', 
                1.0,
                shaperInputScale, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir )

            cs.toReferenceTransforms.append( {
                'type':'lutFile', 
                'path':lut, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )

            shaperInverse = shaperOCIOTransform.copy()
            shaperInverse['direction'] = 'forward'
            cs.toReferenceTransforms.append( shaperInverse )

        return cs

    #
    # LMT Shaper
    #

    lmtLutResolution1d = max(4096, lutResolution1d)
    lmtLutResolution3d = max(65, lutResolution3d)

    # Log 2 shaper
    lmtShaperName = 'lmtShaper'
    lmtParams = {
        'middleGrey'  : 0.18,
        'minExposure' : -10.0,
        'maxExposure' : 6.5
    }
    lmtShaper = createGenericLog(name=lmtShaperName, 
        middleGrey=lmtParams['middleGrey'], 
        minExposure=lmtParams['minExposure'], 
        maxExposure=lmtParams['maxExposure'],
        lutResolution1d=lmtLutResolution1d)
    configData['colorSpaces'].append(lmtShaper)

    shaperInputScale_genericLog2 = 1.0

    # Log 2 shaper name and CTL transforms bundled up
    lmtShaperData = [
        lmtShaperName, 
        '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl',
        '%s/utilities/ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl',
        #'%s/logShaper/logShaper16i_to_aces_param.ctl',
        #'%s/logShaper/aces_to_logShaper16i_param.ctl',
        shaperInputScale_genericLog2,
        lmtParams
    ]

    sortedLMTs = sorted(lmtInfo.iteritems(), key=lambda x: x[1])
    print( sortedLMTs )
    for lmt in sortedLMTs:
        (lmtName, lmtValues) = lmt
        cs = createACESLMT(
            lmtValues['transformUserName'], 
            lmtValues,
            lmtShaperData,
            lmtLutResolution1d,
            lmtLutResolution3d,
            cleanup)
        configData['colorSpaces'].append(cs)

    #
    # ACES RRT with the supplied ODT
    #
    def createACESRRTplusODT(odtName, 
        odtValues,
        shaperInfo,
        lutResolution1d=1024, 
        lutResolution3d=64, 
        cleanup=True):
        cs = ColorSpace("%s" % odtName)
        cs.description = "%s - %s Output Transform" % (odtValues['transformUserNamePrefix'], odtName)
        cs.equalityGroup = ''
        cs.family = 'Output'
        cs.isData=False

        import pprint
        pprint.pprint( odtValues )

        #
        # Generate the shaper transform
        #
        #if 'shaperCTL' in odtValues:
        (shaperName, shaperToACESCTL, shaperFromACESCTL, shaperInputScale, shaperParams) = shaperInfo

        if 'legalRange' in odtValues:
            shaperParams['legalRange'] = odtValues['legalRange']
        else:
            shaperParams['legalRange'] = 0

        shaperLut = "%s_to_aces.spi1d" % shaperName
        if( not os.path.exists( lutDir + "/" + shaperLut ) ):
            ctls = [
                shaperToACESCTL % acesCTLReleaseDir
            ]
            generate1dLUTFromCTL( lutDir + "/" + shaperLut, 
                ctls, 
                lutResolution1d, 
                'float', 
                1.0/shaperInputScale,
                1.0, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir)

        shaperOCIOTransform = {
            'type':'lutFile', 
            'path':shaperLut, 
            'interpolation':'linear', 
            'direction':'inverse'
        }

        #
        # Generate the forward transform
        #
        cs.fromReferenceTransforms = []

        if 'transformLUT' in odtValues:
            # Copy into the lut dir
            transformLUTFileName = os.path.basename(odtValues['transformLUT'])
            lut = lutDir + "/" + transformLUTFileName
            shutil.copy(odtValues['transformLUT'], lut)

            cs.fromReferenceTransforms.append( shaperOCIOTransform )
            cs.fromReferenceTransforms.append( {
                'type':'lutFile', 
                'path': transformLUTFileName, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )
        elif 'transformCTL' in odtValues:
            #shaperLut

            ctls = [
                shaperToACESCTL % acesCTLReleaseDir, 
                '%s/rrt/RRT.a1.0.0.ctl' % acesCTLReleaseDir, 
                '%s/odt/%s' % (acesCTLReleaseDir, odtValues['transformCTL'])
            ]
            lut = "%s.RRT.a1.0.0.%s.spi3d" % (shaperName, odtName)

            generate3dLUTFromCTL( lutDir + "/" + lut, 
                #shaperLUT,
                ctls, 
                lutResolution3d, 
                'float', 
                1.0/shaperInputScale,
                1.0, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir )

            cs.fromReferenceTransforms.append( shaperOCIOTransform )
            cs.fromReferenceTransforms.append( {
                'type':'lutFile', 
                'path':lut, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )

        #
        # Generate the inverse transform
        #
        cs.toReferenceTransforms = []

        if 'transformLUTInverse' in odtValues:
            # Copy into the lut dir
            transformLUTInverseFileName = os.path.basename(odtValues['transformLUTInverse'])
            lut = lutDir + "/" + transformLUTInverseFileName
            shutil.copy(odtValues['transformLUTInverse'], lut)

            cs.toReferenceTransforms.append( {
                'type':'lutFile', 
                'path': transformLUTInverseFileName, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )

            shaperInverse = shaperOCIOTransform.copy()
            shaperInverse['direction'] = 'forward'
            cs.toReferenceTransforms.append( shaperInverse )
        elif 'transformCTLInverse' in odtValues:
            ctls = [
                '%s/odt/%s' % (acesCTLReleaseDir, odtValues['transformCTLInverse']),
                '%s/rrt/InvRRT.a1.0.0.ctl' % acesCTLReleaseDir,
                shaperFromACESCTL % acesCTLReleaseDir
            ]
            lut = "InvRRT.a1.0.0.%s.%s.spi3d" % (odtName, shaperName)

            generate3dLUTFromCTL( lutDir + "/" + lut, 
                #None,
                ctls, 
                lutResolution3d, 
                'half', 
                1.0,
                shaperInputScale, 
                shaperParams,
                cleanup, 
                acesCTLReleaseDir )

            cs.toReferenceTransforms.append( {
                'type':'lutFile', 
                'path':lut, 
                'interpolation':'tetrahedral', 
                'direction':'forward'
            } )

            shaperInverse = shaperOCIOTransform.copy()
            shaperInverse['direction'] = 'forward'
            cs.toReferenceTransforms.append( shaperInverse )

        return cs

    #
    # RRT/ODT shaper options
    #
    shaperData = {}

    # Log 2 shaper
    log2ShaperName = shaperName
    log2Params = {
        'middleGrey'  : 0.18,
        'minExposure' : -6.0,
        'maxExposure' : 6.5
    }
    log2Shaper = createGenericLog(name=log2ShaperName, 
        middleGrey=log2Params['middleGrey'], 
        minExposure=log2Params['minExposure'], 
        maxExposure=log2Params['maxExposure'])
    configData['colorSpaces'].append(log2Shaper)

    shaperInputScale_genericLog2 = 1.0

    # Log 2 shaper name and CTL transforms bundled up
    log2ShaperData = [
        log2ShaperName, 
        '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl',
        '%s/utilities/ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl',
        #'%s/logShaper/logShaper16i_to_aces_param.ctl',
        #'%s/logShaper/aces_to_logShaper16i_param.ctl',
        shaperInputScale_genericLog2,
        log2Params
    ]

    shaperData[log2ShaperName] = log2ShaperData

    #
    # Shaper that also includes the AP1 primaries
    # - Needed for some LUT baking steps
    #
    log2ShaperAP1 = createGenericLog(name=log2ShaperName, 
        middleGrey=log2Params['middleGrey'], 
        minExposure=log2Params['minExposure'], 
        maxExposure=log2Params['maxExposure'])
    log2ShaperAP1.name = "%s AP1" % log2ShaperAP1.name
    # AP1 primaries to AP0 primaries
    log2ShaperAP1.toReferenceTransforms.append( {
        'type':'matrix',
        'matrix':mat44FromMat33(acesAP1toAP0),
        'direction':'forward'
    })
    configData['colorSpaces'].append(log2ShaperAP1)

    #
    # Choose your shaper
    #
    # XXX
    # Shaper name. Should really be automated or made a user choice
    #
    # Options: aceslogShaper, aceslogScaledShaper, log2Shaper
    #shaperName = 'log2Shaper'

    #if shaperName in shaperData:
    #    rrtShaperName = shaperName
    #    rrtShaper = shaperData[shaperName]
    #else:

    rrtShaperName = log2ShaperName
    rrtShaper = log2ShaperData

    #
    # RRT + ODT Combinations
    #
    #for odtName, odtValues in odtInfo.iteritems():
    sortedOdts = sorted(odtInfo.iteritems(), key=lambda x: x[1])
    print( sortedOdts )
    for odt in sortedOdts:
        (odtName, odtValues) = odt

        # Have to handle ODTs that can generate either legal or full output
        if odtName in ['Academy.Rec2020_100nits_dim.a1.0.0', 
                'Academy.Rec709_100nits_dim.a1.0.0',
                'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:
            odtNameLegal = '%s - Legal' % odtValues['transformUserName']
        else:
            odtNameLegal = odtValues['transformUserName']

        odtLegal = odtValues.copy()
        odtLegal['legalRange'] = 1

        cs = createACESRRTplusODT(
            odtNameLegal, 
            odtLegal,
            rrtShaper,
            lutResolution1d,
            lutResolution3d,
            cleanup)
        configData['colorSpaces'].append(cs)

        # Create a display entry using this color space
        configData['displays'][odtNameLegal] = { 
            'Linear':ACES, 
            'Log':ACEScc, 
            'Output Transform':cs }

        if odtName in ['Academy.Rec2020_100nits_dim.a1.0.0', 
                'Academy.Rec709_100nits_dim.a1.0.0', 
                'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:

            print( "Generating full range ODT for %s" % odtName)

            odtNameFull = "%s - Full" % odtValues['transformUserName']
            odtFull = odtValues.copy()
            odtFull['legalRange'] = 0

            csFull = createACESRRTplusODT(
                odtNameFull, 
                odtFull,
                rrtShaper,
                lutResolution1d,
                lutResolution3d,
                cleanup)
            configData['colorSpaces'].append(csFull)

            # Create a display entry using this color space
            configData['displays'][odtNameFull] = { 
                'Linear':ACES, 
                'Log':ACEScc, 
                'Output Transform':csFull }


    print( "generateLUTs - end" )
    return configData

def generateBakedLUTs(odtInfo, shaperName, bakedDir, configPath, lutResolution1d, lutResolution3d, lutResolutionShaper=1024):

    # Add the legal and full variations into this list
    odtInfoC = dict(odtInfo)
    for odtCTLName, odtValues in odtInfo.iteritems():
        if odtCTLName in ['Academy.Rec2020_100nits_dim.a1.0.0', 
            'Academy.Rec709_100nits_dim.a1.0.0',
            'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:
                odtName = odtValues["transformUserName"]

                odtValuesLegal = dict(odtValues)
                odtValuesLegal["transformUserName"] = "%s - Legal" % odtName
                odtInfoC["%s - Legal" % odtCTLName] = odtValuesLegal

                odtValuesFull = dict(odtValues)
                odtValuesFull["transformUserName"] = "%s - Full" % odtName
                odtInfoC["%s - Full" % odtCTLName] = odtValuesFull
                
                del( odtInfoC[odtCTLName] )

    for odtCTLName, odtValues in odtInfoC.iteritems():
        odtPrefix = odtValues["transformUserNamePrefix"]
        odtName = odtValues["transformUserName"]

        # For Photoshop
        for inputspace in ["ACEScc", "ACESproxy"]:
            args =  ["--iconfig", configPath, "-v", "--inputspace", inputspace ]
            args += ["--outputspace", "%s" % odtName ]
            args += ["--description", "%s - %s for %s data" % (odtPrefix, odtName, inputspace) ]
            args += ["--shaperspace", shaperName, "--shapersize", str(lutResolutionShaper) ] 
            args += ["--cubesize", str(lutResolution3d) ]
            args += ["--format", "icc", "%s/photoshop/%s for %s.icc" % (bakedDir, odtName, inputspace) ]

            bakeLUT = process.Process(description="bake a LUT", cmd="ociobakelut", args=args)
            bakeLUT.execute()    

        # For Flame, Lustre
        for inputspace in ["ACEScc", "ACESproxy"]:
            args =  ["--iconfig", configPath, "-v", "--inputspace", inputspace ]
            args += ["--outputspace", "%s" % odtName ]
            args += ["--description", "%s - %s for %s data" % (odtPrefix, odtName, inputspace) ]
            args += ["--shaperspace", shaperName, "--shapersize", str(lutResolutionShaper) ] 
            args += ["--cubesize", str(lutResolution3d) ]

            fargs = ["--format", "flame", "%s/flame/%s for %s Flame.3dl" % (bakedDir, odtName, inputspace) ]
            bakeLUT = process.Process(description="bake a LUT", cmd="ociobakelut", args=(args + fargs))
            bakeLUT.execute()    

            largs = ["--format", "lustre", "%s/lustre/%s for %s Lustre.3dl" % (bakedDir, odtName, inputspace) ]
            bakeLUT = process.Process(description="bake a LUT", cmd="ociobakelut", args=(args + largs))
            bakeLUT.execute()

        # For Maya, Houdini
        for inputspace in ["ACEScg", "ACES2065-1"]:
            args =  ["--iconfig", configPath, "-v", "--inputspace", inputspace ]
            args += ["--outputspace", "%s" % odtName ]
            args += ["--description", "%s - %s for %s data" % (odtPrefix, odtName, inputspace) ]
            if inputspace == 'ACEScg':
                linShaperName = "%s AP1" % shaperName 
            else:
                linShaperName = shaperName
            args += ["--shaperspace", linShaperName, "--shapersize", str(lutResolutionShaper) ] 
            
            args += ["--cubesize", str(lutResolution3d) ]

            margs = ["--format", "cinespace", "%s/maya/%s for %s Maya.csp" % (bakedDir, odtName, inputspace) ]
            bakeLUT = process.Process(description="bake a LUT", cmd="ociobakelut", args=(args + margs))
            bakeLUT.execute()    

            hargs = ["--format", "houdini", "%s/houdini/%s for %s Houdini.lut" % (bakedDir, odtName, inputspace) ]
            bakeLUT = process.Process(description="bake a LUT", cmd="ociobakelut", args=(args + hargs))
            bakeLUT.execute()    


def createConfigDir(configDir, bakeSecondaryLUTs):
    dirs = [configDir, "%s/luts" % configDir]
    if bakeSecondaryLUTs:
        dirs.extend(["%s/baked" % configDir, 
            "%s/baked/flame" % configDir, "%s/baked/photoshop" % configDir,
            "%s/baked/houdini" % configDir, "%s/baked/lustre" % configDir,
            "%s/baked/maya" % configDir])

    for d in dirs:
        if not os.path.exists(d):
            os.mkdir(d)

def getTransformInfo(ctlTransform):
    fp = open(ctlTransform, 'rb')

    # Read lines
    lines = fp.readlines()

    # Grab transform ID and User Name
    transformID = lines[1][3:].split('<')[1].split('>')[1].lstrip().rstrip()
    #print( transformID )
    transformUserName = '-'.join(lines[2][3:].split('<')[1].split('>')[1].split('-')[1:]).lstrip().rstrip()
    transformUserNamePrefix = lines[2][3:].split('<')[1].split('>')[1].split('-')[0].lstrip().rstrip()
    #print( transformUserName )
    fp.close()

    return (transformID, transformUserName, transformUserNamePrefix)

# For versions after WGR9
def getODTInfo(acesCTLReleaseDir):
    # Credit to Alex Fry for the original approach here
    odtDir = os.path.join(acesCTLReleaseDir, "odt")
    allodt = []
    for dirName, subdirList, fileList in os.walk(odtDir):
        for fname in fileList:
            allodt.append((os.path.join(dirName,fname)))

    odtCTLs = [x for x in allodt if ("InvODT" not in x) and (os.path.split(x)[-1][0] != '.')]

    #print odtCTLs

    odts = {}

    for odtCTL in odtCTLs:
        odtTokens = os.path.split(odtCTL)
        #print( odtTokens )

        # Handle nested directories
        odtPathTokens = os.path.split(odtTokens[-2])
        odtDir = odtPathTokens[-1]
        while odtPathTokens[-2][-3:] != 'odt':
            odtPathTokens = os.path.split(odtPathTokens[-2])
            odtDir = os.path.join(odtPathTokens[-1], odtDir)

        # Build full name
        #print( "odtDir : %s" % odtDir )
        transformCTL = odtTokens[-1]
        #print( transformCTL )
        odtName = string.join(transformCTL.split('.')[1:-1], '.')
        #print( odtName )

        # Find id, user name and user name prefix
        (transformID, transformUserName, transformUserNamePrefix) = getTransformInfo(
            "%s/odt/%s/%s" % (acesCTLReleaseDir, odtDir, transformCTL) )

        # Find inverse
        transformCTLInverse = "InvODT.%s.ctl" % odtName
        if not os.path.exists(os.path.join(odtTokens[-2], transformCTLInverse)):
            transformCTLInverse = None
        #print( transformCTLInverse )

        # Add to list of ODTs
        odts[odtName] = {}
        odts[odtName]['transformCTL'] = os.path.join(odtDir, transformCTL)
        if transformCTLInverse != None:
            odts[odtName]['transformCTLInverse'] = os.path.join(odtDir, transformCTLInverse)

        odts[odtName]['transformID'] = transformID
        odts[odtName]['transformUserNamePrefix'] = transformUserNamePrefix
        odts[odtName]['transformUserName'] = transformUserName

        print( "ODT : %s" % odtName )
        print( "\tTransform ID               : %s" % transformID )
        print( "\tTransform User Name Prefix : %s" % transformUserNamePrefix )
        print( "\tTransform User Name        : %s" % transformUserName )
        print( "\tForward ctl                : %s" % odts[odtName]['transformCTL'])
        if 'transformCTLInverse' in odts[odtName]:
            print( "\tInverse ctl                : %s" % odts[odtName]['transformCTLInverse'])
        else:
            print( "\tInverse ctl                : %s" % "None" )

    print( "\n" )

    return odts

# For versions after WGR9
def getLMTInfo(acesCTLReleaseDir):
    # Credit to Alex Fry for the original approach here
    lmtDir = os.path.join(acesCTLReleaseDir, "lmt")
    alllmt = []
    for dirName, subdirList, fileList in os.walk(lmtDir):
        for fname in fileList:
            alllmt.append((os.path.join(dirName,fname)))

    lmtCTLs = [x for x in alllmt if ("InvLMT" not in x) and ("README" not in x) and (os.path.split(x)[-1][0] != '.')]

    #print lmtCTLs

    lmts = {}

    for lmtCTL in lmtCTLs:
        lmtTokens = os.path.split(lmtCTL)
        #print( lmtTokens )

        # Handle nested directories
        lmtPathTokens = os.path.split(lmtTokens[-2])
        lmtDir = lmtPathTokens[-1]
        while lmtPathTokens[-2][-3:] != 'ctl':
            lmtPathTokens = os.path.split(lmtPathTokens[-2])
            lmtDir = os.path.join(lmtPathTokens[-1], lmtDir)

        # Build full name
        #print( "lmtDir : %s" % lmtDir )
        transformCTL = lmtTokens[-1]
        #print( transformCTL )
        lmtName = string.join(transformCTL.split('.')[1:-1], '.')
        #print( lmtName )

        # Find id, user name and user name prefix
        (transformID, transformUserName, transformUserNamePrefix) = getTransformInfo(
            "%s/%s/%s" % (acesCTLReleaseDir, lmtDir, transformCTL) )

        # Find inverse
        transformCTLInverse = "InvLMT.%s.ctl" % lmtName
        if not os.path.exists(os.path.join(lmtTokens[-2], transformCTLInverse)):
            transformCTLInverse = None
        #print( transformCTLInverse )

        # Add to list of LMTs
        lmts[lmtName] = {}
        lmts[lmtName]['transformCTL'] = os.path.join(lmtDir, transformCTL)
        if transformCTLInverse != None:
            lmts[odtName]['transformCTLInverse'] = os.path.join(lmtDir, transformCTLInverse)

        lmts[lmtName]['transformID'] = transformID
        lmts[lmtName]['transformUserNamePrefix'] = transformUserNamePrefix
        lmts[lmtName]['transformUserName'] = transformUserName

        print( "LMT : %s" % lmtName )
        print( "\tTransform ID               : %s" % transformID )
        print( "\tTransform User Name Prefix : %s" % transformUserNamePrefix )
        print( "\tTransform User Name        : %s" % transformUserName )
        print( "\t Forward ctl : %s" % lmts[lmtName]['transformCTL'])
        if 'transformCTLInverse' in lmts[lmtName]:
            print( "\t Inverse ctl : %s" % lmts[lmtName]['transformCTLInverse'])
        else:
            print( "\t Inverse ctl : %s" % "None" )

    print( "\n" )

    return lmts

#
# Create the ACES config
#
def createACESConfig(acesCTLReleaseDir, 
    configDir, 
    lutResolution1d=4096, 
    lutResolution3d=64, 
    bakeSecondaryLUTs=True,
    cleanup=True):

    # Get ODT names and CTL paths
    odtInfo = getODTInfo(acesCTLReleaseDir)

    # Get ODT names and CTL paths
    lmtInfo = getLMTInfo(acesCTLReleaseDir)

    # Create config dir
    createConfigDir(configDir, bakeSecondaryLUTs)

    # Generate config data and LUTs for different transforms
    lutDir = "%s/luts" % configDir
    shaperName = 'outputShaper'
    configData = generateLUTs(odtInfo, lmtInfo, shaperName, acesCTLReleaseDir, lutDir, lutResolution1d, lutResolution3d, cleanup)
    
    # Create the config using the generated LUTs
    print( "Creating generic config")
    config = createConfig(configData)
    print( "\n\n\n" )

    # Write the config to disk
    writeConfig(config, "%s/config.ocio" % configDir )

    # Create a config that will work well with Nuke using the previously generated LUTs
    print( "Creating Nuke-specific config")
    nuke_config = createConfig(configData, nuke=True)
    print( "\n\n\n" )

    # Write the config to disk
    writeConfig(nuke_config, "%s/nuke_config.ocio" % configDir )

    # Bake secondary LUTs using the config
    if bakeSecondaryLUTs:
        generateBakedLUTs(odtInfo, shaperName, "%s/baked" % configDir, "%s/config.ocio" % configDir, lutResolution1d, lutResolution3d, lutResolution1d)

#
# Main
#
def main():
    import optparse

    p = optparse.OptionParser(description='An OCIO config generation script',
                                prog='createACESConfig',
                                version='createACESConfig 0.1',
                                usage='%prog [options]')
    p.add_option('--acesCTLDir', '-a', default=None)
    p.add_option('--configDir', '-c', default=None)
    p.add_option('--lutResolution1d', default=4096)
    p.add_option('--lutResolution3d', default=64)
    p.add_option('--dontBakeSecondaryLUTs', action="store_true")
    p.add_option('--keepTempImages', action="store_true")

    options, arguments = p.parse_args()

    #
    # Get options
    # 
    acesCTLDir = options.acesCTLDir
    configDir  = options.configDir
    lutResolution1d  = int(options.lutResolution1d)
    lutResolution3d  = int(options.lutResolution3d)
    bakeSecondaryLUTs  = not(options.dontBakeSecondaryLUTs)
    cleanupTempImages  = not(options.keepTempImages)

    try:
        argsStart = sys.argv.index('--') + 1
        args = sys.argv[argsStart:]
    except:
        argsStart = len(sys.argv)+1
        args = []

    print( "command line : \n%s\n" % " ".join(sys.argv) )

    if configDir == None:
        print( "process: No ACES CTL directory specified" )
        return
 
    #
    # Generate the configuration
    #
    createACESConfig(acesCTLDir, configDir, lutResolution1d, lutResolution3d, bakeSecondaryLUTs, cleanupTempImages)
# main

if __name__ == '__main__':
    main()
