#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
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
"""

import array
import os
import sys

import OpenImageIO as oiio

from aces_ocio.process import Process

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['generate1dLUTImage',
           'writeSPI1D',
           'generate1dLUTFromImage',
           'generate3dLUTImage',
           'generate3dLUTFromImage',
           'applyCTLToImage',
           'convertBitDepth',
           'generate1dLUTFromCTL',
           'correctLUTImage',
           'generate3dLUTFromCTL',
           'main']

#
# Functions used to generate LUTs using CTL transforms
#
def generate1dLUTImage(ramp1dPath,
                       resolution=1024,
                       minValue=0.0,
                       maxValue=1.0):
    # print("Generate 1d LUT image - %s" % ramp1dPath)

    # open image
    format = os.path.splitext(ramp1dPath)[1]
    ramp = oiio.ImageOutput.create(ramp1dPath)

    # set image specs
    spec = oiio.ImageSpec()
    spec.set_format(oiio.FLOAT)
    # spec.format.basetype = oiio.FLOAT
    spec.width = resolution
    spec.height = 1
    spec.nchannels = 3

    ramp.open(ramp1dPath, spec, oiio.Create)

    data = array.array("f",
                       "\0" * spec.width * spec.height * spec.nchannels * 4)
    for i in range(resolution):
        value = float(i) / (resolution - 1) * (maxValue - minValue) + minValue
        data[i * spec.nchannels + 0] = value
        data[i * spec.nchannels + 1] = value
        data[i * spec.nchannels + 2] = value

    ramp.write_image(spec.format, data)
    ramp.close()


# Credit to Alex Fry for the original single channel version of the spi1d
# writer
def writeSPI1D(filename, fromMin, fromMax, data, entries, channels):
    f = file(filename, 'w')
    f.write("Version 1\n")
    f.write("From %f %f\n" % (fromMin, fromMax))
    f.write("Length %d\n" % entries)
    f.write("Components %d\n" % (min(3, channels)))
    f.write("{\n")
    for i in range(0, entries):
        entry = ""
        for j in range(0, min(3, channels)):
            entry = "%s %s" % (entry, data[i * channels + j])
        f.write("        %s\n" % entry)
    f.write("}\n")
    f.close()


def generate1dLUTFromImage(ramp1dPath,
                           outputPath=None,
                           minValue=0.0,
                           maxValue=1.0):
    if outputPath == None:
        outputPath = ramp1dPath + ".spi1d"

    # open image
    ramp = oiio.ImageInput.open(ramp1dPath)

    # get image specs
    spec = ramp.spec()
    type = spec.format.basetype
    width = spec.width
    height = spec.height
    channels = spec.nchannels

    # get data
    # Force data to be read as float. The Python API doesn't handle
    # half-floats well yet.
    type = oiio.FLOAT
    data = ramp.read_image(type)

    writeSPI1D(outputPath, minValue, maxValue, data, width, channels)


def generate3dLUTImage(ramp3dPath, resolution=32):
    args = ["--generate",
            "--cubesize",
            str(resolution),
            "--maxwidth",
            str(resolution * resolution),
            "--output",
            ramp3dPath]
    lutExtract = Process(description="generate a 3d LUT image",
                         cmd="ociolutimage",
                         args=args)
    lutExtract.execute()


def generate3dLUTFromImage(ramp3dPath, outputPath=None, resolution=32):
    if outputPath == None:
        outputPath = ramp3dPath + ".spi3d"

    args = ["--extract",
            "--cubesize",
            str(resolution),
            "--maxwidth",
            str(resolution * resolution),
            "--input",
            ramp3dPath,
            "--output",
            outputPath]
    lutExtract = Process(description="extract a 3d LUT",
                         cmd="ociolutimage",
                         args=args)
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
            if os.path.split(acesCTLReleaseDir)[1] != "utilities":
                ctlModulePath = "%s/utilities" % acesCTLReleaseDir
            else:
                ctlModulePath = acesCTLReleaseDir
            ctlenv['CTL_MODULE_PATH'] = ctlModulePath

        args = []
        for ctl in ctlPaths:
            args += ['-ctl', ctl]
        args += ["-force"]
        # args += ["-verbose"]
        args += ["-input_scale", str(inputScale)]
        args += ["-output_scale", str(outputScale)]
        args += ["-global_param1", "aIn", "1.0"]
        for key, value in globalParams.iteritems():
            args += ["-global_param1", key, str(value)]
        args += [inputImage]
        args += [outputImage]

        # print("args : %s" % args)

        ctlp = Process(description="a ctlrender process",
                       cmd="ctlrender",
                       args=args, env=ctlenv)

        ctlp.execute()


def convertBitDepth(inputImage, outputImage, depth):
    args = [inputImage,
            "-d",
            depth,
            "-o",
            outputImage]
    convert = Process(description="convert image bit depth",
                      cmd="oiiotool",
                      args=args)
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
    # print(lutPath)
    # print(ctlPaths)

    lutPathBase = os.path.splitext(lutPath)[0]

    identityLUTImageFloat = lutPathBase + ".float.tiff"
    generate1dLUTImage(identityLUTImageFloat,
                       lutResolution,
                       minValue,
                       maxValue)

    if identityLutBitDepth != 'half':
        identityLUTImage = lutPathBase + ".uint16.tiff"
        convertBitDepth(identityLUTImageFloat,
                        identityLUTImage,
                        identityLutBitDepth)
    else:
        identityLUTImage = identityLUTImageFloat

    transformedLUTImage = lutPathBase + ".transformed.exr"
    applyCTLToImage(identityLUTImage,
                    transformedLUTImage,
                    ctlPaths,
                    inputScale,
                    outputScale,
                    globalParams,
                    acesCTLReleaseDir)

    generate1dLUTFromImage(transformedLUTImage, lutPath, minValue, maxValue)

    if cleanup:
        os.remove(identityLUTImage)
        if identityLUTImage != identityLUTImageFloat:
            os.remove(identityLUTImageFloat)
        os.remove(transformedLUTImage)


def correctLUTImage(transformedLUTImage, correctedLUTImage, lutResolution):
    # open image
    transformed = oiio.ImageInput.open(transformedLUTImage)

    # get image specs
    transformedSpec = transformed.spec()
    type = transformedSpec.format.basetype
    width = transformedSpec.width
    height = transformedSpec.height
    channels = transformedSpec.nchannels

    # rotate or not
    if width != lutResolution * lutResolution or height != lutResolution:
        print(("Correcting image as resolution is off. "
               "Found %d x %d. Expected %d x %d") % (
                  width, height, lutResolution * lutResolution, lutResolution))
        print("Generating %s" % correctedLUTImage)

        #
        # We're going to generate a new correct image
        #

        # Get the source data
        # Force data to be read as float. The Python API doesn't handle
        # half-floats well yet.
        type = oiio.FLOAT
        sourceData = transformed.read_image(type)

        format = os.path.splitext(correctedLUTImage)[1]
        correct = oiio.ImageOutput.create(correctedLUTImage)

        # set image specs
        correctSpec = oiio.ImageSpec()
        correctSpec.set_format(oiio.FLOAT)
        correctSpec.width = height
        correctSpec.height = width
        correctSpec.nchannels = channels

        correct.open(correctedLUTImage, correctSpec, oiio.Create)

        destData = array.array("f",
                               ("\0" * correctSpec.width *
                                correctSpec.height *
                                correctSpec.nchannels * 4))
        for j in range(0, correctSpec.height):
            for i in range(0, correctSpec.width):
                for c in range(0, correctSpec.nchannels):
                    # print(i, j, c)
                    destData[(correctSpec.nchannels *
                              correctSpec.width * j +
                              correctSpec.nchannels * i + c)] = (
                        sourceData[correctSpec.nchannels *
                                   correctSpec.width * j +
                                   correctSpec.nchannels * i + c])

        correct.write_image(correctSpec.format, destData)
        correct.close()
    else:
        # shutil.copy(transformedLUTImage, correctedLUTImage)
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
    # print(lutPath)
    # print(ctlPaths)

    lutPathBase = os.path.splitext(lutPath)[0]

    identityLUTImageFloat = lutPathBase + ".float.tiff"
    generate3dLUTImage(identityLUTImageFloat, lutResolution)

    if identityLutBitDepth != 'half':
        identityLUTImage = lutPathBase + "." + identityLutBitDepth + ".tiff"
        convertBitDepth(identityLUTImageFloat,
                        identityLUTImage,
                        identityLutBitDepth)
    else:
        identityLUTImage = identityLUTImageFloat

    transformedLUTImage = lutPathBase + ".transformed.exr"
    applyCTLToImage(identityLUTImage,
                    transformedLUTImage,
                    ctlPaths,
                    inputScale,
                    outputScale,
                    globalParams,
                    acesCTLReleaseDir)

    correctedLUTImage = lutPathBase + ".correct.exr"
    correctedLUTImage = correctLUTImage(transformedLUTImage,
                                        correctedLUTImage,
                                        lutResolution)

    generate3dLUTFromImage(correctedLUTImage, lutPath, lutResolution)

    if cleanup:
        os.remove(identityLUTImage)
        if identityLUTImage != identityLUTImageFloat:
            os.remove(identityLUTImageFloat)
        os.remove(transformedLUTImage)
        if correctedLUTImage != transformedLUTImage:
            os.remove(correctedLUTImage)
            # os.remove(correctedLUTImage)


def main():
    import optparse

    p = optparse.OptionParser(
        description='A utility to generate LUTs from CTL',
        prog='generateLUT',
        version='0.01',
        usage='%prog [options]')

    p.add_option('--lut', '-l', type="string", default="")
    p.add_option('--ctl', '-c', type="string", action="append")
    p.add_option('--lutResolution1d', '', type="int", default=1024)
    p.add_option('--lutResolution3d', '', type="int", default=33)
    p.add_option('--ctlReleasePath', '-r', type="string", default="")
    p.add_option('--bitDepth', '-b', type="string", default="float")
    p.add_option('--keepTempImages', '', action="store_true")
    p.add_option('--minValue', '', type="float", default=0.0)
    p.add_option('--maxValue', '', type="float", default=1.0)
    p.add_option('--inputScale', '', type="float", default=1.0)
    p.add_option('--outputScale', '', type="float", default=1.0)
    p.add_option('--ctlRenderParam', '-p', type="string", nargs=2,
                 action="append")

    p.add_option('--generate1d', '', action="store_true")
    p.add_option('--generate3d', '', action="store_true")

    options, arguments = p.parse_args()

    #
    # Get options
    # 
    lut = options.lut
    ctls = options.ctl
    lutResolution1d = options.lutResolution1d
    lutResolution3d = options.lutResolution3d
    minValue = options.minValue
    maxValue = options.maxValue
    inputScale = options.inputScale
    outputScale = options.outputScale
    ctlReleasePath = options.ctlReleasePath
    generate1d = options.generate1d == True
    generate3d = options.generate3d == True
    bitDepth = options.bitDepth
    cleanup = not options.keepTempImages

    params = {}
    if options.ctlRenderParam != None:
        for param in options.ctlRenderParam:
            params[param[0]] = float(param[1])

    try:
        argsStart = sys.argv.index('--') + 1
        args = sys.argv[argsStart:]
    except:
        argsStart = len(sys.argv) + 1
        args = []

    # print("command line : \n%s\n" % " ".join(sys.argv))

    #
    # Generate LUTs
    #
    if generate1d:
        print("1D LUT generation options")
    else:
        print("3D LUT generation options")

    print("lut                 : %s" % lut)
    print("ctls                : %s" % ctls)
    print("lut res 1d          : %s" % lutResolution1d)
    print("lut res 3d          : %s" % lutResolution3d)
    print("min value           : %s" % minValue)
    print("max value           : %s" % maxValue)
    print("input scale         : %s" % inputScale)
    print("output scale        : %s" % outputScale)
    print("ctl render params   : %s" % params)
    print("ctl release path    : %s" % ctlReleasePath)
    print("bit depth of input  : %s" % bitDepth)
    print("cleanup temp images : %s" % cleanup)

    if generate1d:
        generate1dLUTFromCTL(lut,
                             ctls,
                             lutResolution1d,
                             bitDepth,
                             inputScale,
                             outputScale,
                             params,
                             cleanup,
                             ctlReleasePath,
                             minValue,
                             maxValue)

    elif generate3d:
        generate3dLUTFromCTL(lut,
                             ctls,
                             lutResolution3d,
                             bitDepth,
                             inputScale,
                             outputScale,
                             params,
                             cleanup,
                             ctlReleasePath)
    else:
        print(("\n\nNo LUT generated. "
               "You must choose either 1D or 3D LUT generation\n\n"))

# main

if __name__ == '__main__':
    main()

