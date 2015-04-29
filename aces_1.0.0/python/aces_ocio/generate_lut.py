#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines objects to generate various kind of 1d, 2d and 3d LUTs in various file
formats.
"""

from __future__ import division

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

__all__ = ['generate_1d_LUT_image',
           'write_SPI_1d',
           'generate_1d_LUT_from_image',
           'generate_3d_LUT_image',
           'generate_3d_LUT_from_image',
           'apply_CTL_to_image',
           'convert_bit_depth',
           'generate_1d_LUT_from_CTL',
           'correct_LUT_image',
           'generate_3d_LUT_from_CTL',
           'main']


def generate_1d_LUT_image(ramp_1d_path,
                          resolution=1024,
                          min_value=0,
                          max_value=1):
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

    ramp = oiio.ImageOutput.create(ramp_1d_path)

    spec = oiio.ImageSpec()
    spec.set_format(oiio.FLOAT)
    # spec.format.basetype = oiio.FLOAT
    spec.width = resolution
    spec.height = 1
    spec.nchannels = 3

    ramp.open(ramp_1d_path, spec, oiio.Create)

    data = array.array('f',
                       '\0' * spec.width * spec.height * spec.nchannels * 4)
    for i in range(resolution):
        value = float(i) / (resolution - 1) * (
            max_value - min_value) + min_value
        data[i * spec.nchannels + 0] = value
        data[i * spec.nchannels + 1] = value
        data[i * spec.nchannels + 2] = value

    ramp.write_image(spec.format, data)
    ramp.close()


def write_SPI_1d(filename, 
                 from_min, 
                 from_max, 
                 data, 
                 entries, 
                 channels, 
                 components=3):
    """
    Object description.

    Credit to *Alex Fry* for the original single channel version of the spi1d
    writer.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('Version 1\n')
        fp.write('From %f %f\n' % (from_min, from_max))
        fp.write('Length %d\n' % entries)
        fp.write('Components %d\n' % components)
        fp.write('{\n')
        for i in range(0, entries):
            entry = ''
            for j in range(0, components):
                entry = '%s %s' % (entry, data[i * channels + j])
            fp.write('        %s\n' % entry)
        fp.write('}\n')


def write_CSP_1d(filename, 
                 from_min, 
                 from_max, 
                 data, 
                 entries, 
                 channels, 
                 components=3):
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

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('CSPLUTV100\n')
        fp.write('1D\n')
        fp.write('\n')
        fp.write('BEGIN METADATA\n')
        fp.write('END METADATA\n')

        fp.write('\n')

        fp.write('2\n')
        fp.write('%f %f\n' % (from_min, from_max))
        fp.write('0.0 1.0\n')
        fp.write('2\n')
        fp.write('%f %f\n' % (from_min, from_max))
        fp.write('0.0 1.0\n')
        fp.write('2\n')
        fp.write('%f %f\n' % (from_min, from_max))
        fp.write('0.0 1.0\n')

        fp.write('\n')

        fp.write('%d\n' % entries)
        if components == 1:
          for i in range(0, entries):
              entry = ''
              for j in range(3):
                  entry = '%s %s' % (entry, data[i * channels])
              fp.write('%s\n' % entry)
        else:
          for i in range(entries):
              entry = ''
              for j in range(components):
                  entry = '%s %s' % (entry, data[i * channels + j])
              fp.write('%s\n' % entry)
        fp.write('\n')

def write_CTL_1d(filename, 
                 from_min, 
                 from_max, 
                 data, 
                 entries, 
                 channels, 
                 components=3):
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

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('// %d x %d LUT generated by "generate_lut"\n' % (
          entries, components))
        fp.write('\n')
        fp.write('const float min1d = %3.9f;\n' % from_min)
        fp.write('const float max1d = %3.9f;\n' % from_max)
        fp.write('\n')

        # Write LUT
        if components == 1:
          fp.write('const float lut[] = {\n')
          for i in range(0, entries):
              fp.write('%s' % data[i * channels])
              if i != (entries-1):
                fp.write(',')
              fp.write('\n')
          fp.write('};\n')
          fp.write('\n')
        else:
          for j in range(components):
            fp.write('const float lut%d[] = {\n' % j)
            for i in range(0, entries):
                fp.write('%s' % data[i * channels])
                if i != (entries-1):
                  fp.write(',')
                fp.write('\n')
            fp.write('};\n')
            fp.write('\n')

        fp.write('void main\n')
        fp.write('(\n')
        fp.write('  input varying float rIn,\n')
        fp.write('  input varying float gIn,\n')
        fp.write('  input varying float bIn,\n')
        fp.write('  input varying float aIn,\n')
        fp.write('  output varying float rOut,\n')
        fp.write('  output varying float gOut,\n')
        fp.write('  output varying float bOut,\n')
        fp.write('  output varying float aOut\n')
        fp.write(')\n')
        fp.write('{\n')
        fp.write('  float r = rIn;\n')
        fp.write('  float g = gIn;\n')
        fp.write('  float b = bIn;\n')
        fp.write('\n')
        fp.write('  // Apply LUT\n')
        if components == 1:
          fp.write('  r = lookup1D(lut, min1d, max1d, r);\n')
          fp.write('  g = lookup1D(lut, min1d, max1d, g);\n')
          fp.write('  b = lookup1D(lut, min1d, max1d, b);\n')
        elif components == 3:
          fp.write('  r = lookup1D(lut0, min1d, max1d, r);\n')
          fp.write('  g = lookup1D(lut1, min1d, max1d, g);\n')
          fp.write('  b = lookup1D(lut2, min1d, max1d, b);\n')          
        fp.write('\n')
        fp.write('  rOut = r;\n')
        fp.write('  gOut = g;\n')
        fp.write('  bOut = b;\n')
        fp.write('  aOut = aIn;\n')
        fp.write('}\n')

def write_1d(filename, 
             from_min, 
             from_max, 
             data, 
             data_entries, 
             data_channels, 
             lut_components=3,
             format='spi1d'):
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

    ocioFormatsToExtensions = {'cinespace' : 'csp',
                               'flame'     : '3dl',
                               'icc'       : 'icc',
                               'houdini'   : 'lut',
                               'lustre'    : '3dl',
                               'ctl'       : 'ctl'}

    if format in ocioFormatsToExtensions:
      if ocioFormatsToExtensions[format] == 'csp':
        write_CSP_1d(filename,
                     from_min,
                     from_max,
                     data,
                     data_entries,
                     data_channels,
                     lut_components)
      elif ocioFormatsToExtensions[format] == 'ctl':
        write_CTL_1d(filename,
                     from_min,
                     from_max,
                     data,
                     data_entries,
                     data_channels,
                     lut_components)
    else:
      write_SPI_1d(filename,
                   from_min,
                   from_max,
                   data,
                   data_entries,
                   data_channels,
                   lut_components)

def generate_1d_LUT_from_image(ramp_1d_path,
                               output_path=None,
                               min_value=0,
                               max_value=1,
                               channels=3,
                               format='spi1d'):
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

    if output_path is None:
        output_path = '%s.%s' % (ramp_1d_path, 'spi1d')

    ramp = oiio.ImageInput.open(ramp_1d_path)

    ramp_spec = ramp.spec()
    ramp_width = ramp_spec.width
    ramp_channels = ramp_spec.nchannels

    # Forcibly read data as float, the Python API doesn't handle half-float
    # well yet.
    type = oiio.FLOAT
    ramp_data = ramp.read_image(type)

    write_1d(output_path, min_value, max_value, 
      ramp_data, ramp_width, ramp_channels, channels, format)


def generate_3d_LUT_image(ramp_3d_path, resolution=32):
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

    args = ['--generate',
            '--cubesize',
            str(resolution),
            '--maxwidth',
            str(resolution * resolution),
            '--output',
            ramp_3d_path]
    lut_extract = Process(description='generate a 3d LUT image',
                          cmd='ociolutimage',
                          args=args)
    lut_extract.execute()


def generate_3d_LUT_from_image(ramp_3d_path, 
                               output_path=None, 
                               resolution=32,
                               format='spi3d'):
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

    if output_path is None:
        output_path = '%s.%s' % (ramp_3d_path, 'spi3d')

    ocioFormatsToExtensions = {'cinespace' : 'csp',
                               'flame'     : '3dl',
                               'icc'       : 'icc',
                               'houdini'   : 'lut',
                               'lustre'    : '3dl'}

    if format == 'spi3d' or not (format in ocioFormatsToExtensions):
      # Extract a spi3d LUT
      args = ['--extract',
              '--cubesize',
              str(resolution),
              '--maxwidth',
              str(resolution * resolution),
              '--input',
              ramp_3d_path,
              '--output',
              output_path]
      lut_extract = Process(description='extract a 3d LUT',
                            cmd='ociolutimage',
                            args=args)
      lut_extract.execute()

    else:
      output_path_spi3d = '%s.%s' % (output_path, 'spi3d')

      # Extract a spi3d LUT
      args = ['--extract',
              '--cubesize',
              str(resolution),
              '--maxwidth',
              str(resolution * resolution),
              '--input',
              ramp_3d_path,
              '--output',
              output_path_spi3d]
      lut_extract = Process(description='extract a 3d LUT',
                            cmd='ociolutimage',
                            args=args)
      lut_extract.execute()

      # Convert to a different format
      args = ['--lut',
              output_path_spi3d,
              '--format',
              format,
              output_path]
      lut_convert = Process(description='convert a 3d LUT',
                            cmd='ociobakelut',
                            args=args)
      lut_convert.execute()


def apply_CTL_to_image(input_image,
                       output_image,
                       ctl_paths=None,
                       input_scale=1,
                       output_scale=1,
                       global_params=None,
                       aces_ctl_directory=None):
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

    if ctl_paths is None:
        ctl_paths = []
    if global_params is None:
        global_params = {}

    if len(ctl_paths) > 0:
        ctlenv = os.environ
        if aces_ctl_directory is not None:
            if os.path.split(aces_ctl_directory)[1] != 'utilities':
                ctl_module_path = os.path.join(aces_ctl_directory, 'utilities')
            else:
                ctl_module_path = aces_ctl_directory
            ctlenv['CTL_MODULE_PATH'] = ctl_module_path

        args = []
        for ctl in ctl_paths:
            args += ['-ctl', ctl]
        args += ['-force']
        args += ['-input_scale', str(input_scale)]
        args += ['-output_scale', str(output_scale)]
        args += ['-global_param1', 'aIn', '1.0']
        for key, value in global_params.iteritems():
            args += ['-global_param1', key, str(value)]
        args += [input_image]
        args += [output_image]

        ctlp = Process(description='a ctlrender process',
                       cmd='ctlrender',
                       args=args, env=ctlenv)

        ctlp.execute()


def convert_bit_depth(input_image, output_image, depth):
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

    args = [input_image,
            '-d',
            depth,
            '-o',
            output_image]
    convert = Process(description='convert image bit depth',
                      cmd='oiiotool',
                      args=args)
    convert.execute()


def generate_1d_LUT_from_CTL(lut_path,
                             ctl_paths,
                             lut_resolution=1024,
                             identity_LUT_bit_depth='half',
                             input_scale=1,
                             output_scale=1,
                             global_params=None,
                             cleanup=True,
                             aces_ctl_directory=None,
                             min_value=0,
                             max_value=1,
                             channels=3,
                             format='spi1d'):
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

    if global_params is None:
        global_params = {}

    lut_path_base = os.path.splitext(lut_path)[0]

    identity_LUT_image_float = '%s.%s.%s' % (lut_path_base, 'float', 'tiff')
    generate_1d_LUT_image(identity_LUT_image_float,
                          lut_resolution,
                          min_value,
                          max_value)

    if identity_LUT_bit_depth not in ['half', 'float']:
        identity_LUT_image = '%s.%s.%s' % (lut_path_base, 'uint16', 'tiff')
        convert_bit_depth(identity_LUT_image_float,
                          identity_LUT_image,
                          identity_LUT_bit_depth)
    else:
        identity_LUT_image = identity_LUT_image_float

    transformed_LUT_image = '%s.%s.%s' % (lut_path_base, 'transformed', 'exr')
    apply_CTL_to_image(identity_LUT_image,
                       transformed_LUT_image,
                       ctl_paths,
                       input_scale,
                       output_scale,
                       global_params,
                       aces_ctl_directory)

    generate_1d_LUT_from_image(transformed_LUT_image,
                               lut_path,
                               min_value,
                               max_value,
                               channels,
                               format)

    if cleanup:
        os.remove(identity_LUT_image)
        if identity_LUT_image != identity_LUT_image_float:
            os.remove(identity_LUT_image_float)
        os.remove(transformed_LUT_image)


def correct_LUT_image(transformed_LUT_image,
                      corrected_LUT_image,
                      lut_resolution):
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

    transformed = oiio.ImageInput.open(transformed_LUT_image)

    transformed_spec = transformed.spec()
    width = transformed_spec.width
    height = transformed_spec.height
    channels = transformed_spec.nchannels

    if width != lut_resolution * lut_resolution or height != lut_resolution:
        print(('Correcting image as resolution is off. '
               'Found %d x %d. Expected %d x %d') % (
                  width,
                  height,
                  lut_resolution * lut_resolution,
                  lut_resolution))
        print('Generating %s' % corrected_LUT_image)

        # Forcibly read data as float, the Python API doesn't handle half-float
        # well yet.
        type = oiio.FLOAT
        source_data = transformed.read_image(type)

        correct = oiio.ImageOutput.create(corrected_LUT_image)

        correct_spec = oiio.ImageSpec()
        correct_spec.set_format(oiio.FLOAT)
        correct_spec.width = height
        correct_spec.height = width
        correct_spec.nchannels = channels

        correct.open(corrected_LUT_image, correct_spec, oiio.Create)

        dest_data = array.array('f',
                                ('\0' * correct_spec.width *
                                 correct_spec.height *
                                 correct_spec.nchannels * 4))
        for j in range(0, correct_spec.height):
            for i in range(0, correct_spec.width):
                for c in range(0, correct_spec.nchannels):
                    dest_data[(correct_spec.nchannels *
                               correct_spec.width * j +
                               correct_spec.nchannels * i + c)] = (
                        source_data[correct_spec.nchannels *
                                    correct_spec.width * j +
                                    correct_spec.nchannels * i + c])

        correct.write_image(correct_spec.format, dest_data)
        correct.close()
    else:
        # shutil.copy(transformedLUTImage, correctedLUTImage)
        corrected_LUT_image = transformed_LUT_image

    transformed.close()

    return corrected_LUT_image


def generate_3d_LUT_from_CTL(lut_path,
                             ctl_paths,
                             lut_resolution=64,
                             identity_LUT_bit_depth='half',
                             input_scale=1,
                             output_scale=1,
                             global_params=None,
                             cleanup=True,
                             aces_ctl_directory=None,
                             format='spi3d'):
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

    if global_params is None:
        global_params = {}

    lut_path_base = os.path.splitext(lut_path)[0]

    identity_LUT_image_float = '%s.%s.%s' % (lut_path_base, 'float', 'tiff')
    generate_3d_LUT_image(identity_LUT_image_float, lut_resolution)

    if identity_LUT_bit_depth not in ['half', 'float']:
        identity_LUT_image = '%s.%s.%s' % (lut_path_base,
                                           identity_LUT_bit_depth,
                                           'tiff')
        convert_bit_depth(identity_LUT_image_float,
                          identity_LUT_image,
                          identity_LUT_bit_depth)
    else:
        identity_LUT_image = identity_LUT_image_float

    transformed_LUT_image = '%s.%s.%s' % (lut_path_base, 'transformed', 'exr')
    apply_CTL_to_image(identity_LUT_image,
                       transformed_LUT_image,
                       ctl_paths,
                       input_scale,
                       output_scale,
                       global_params,
                       aces_ctl_directory)

    corrected_LUT_image = '%s.%s.%s' % (lut_path_base, 'correct', 'exr')
    corrected_LUT_image = correct_LUT_image(transformed_LUT_image,
                                            corrected_LUT_image,
                                            lut_resolution)

    generate_3d_LUT_from_image(corrected_LUT_image, 
                               lut_path, 
                               lut_resolution, 
                               format)

    if cleanup:
        os.remove(identity_LUT_image)
        if identity_LUT_image != identity_LUT_image_float:
            os.remove(identity_LUT_image_float)
        os.remove(transformed_LUT_image)
        if corrected_LUT_image != transformed_LUT_image:
            os.remove(corrected_LUT_image)
        if format != 'spi3d':
            lut_path_spi3d = '%s.%s' % (lut_path, 'spi3d')
            os.remove(lut_path_spi3d)

def main():
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

    import optparse

    p = optparse.OptionParser(
        description='A utility to generate LUTs from CTL',
        prog='generateLUT',
        version='0.01',
        usage='%prog [options]')

    p.add_option('--lut', '-l', type='string', default='')
    p.add_option('--format', '-f', type='string', default='')
    p.add_option('--ctl', '-c', type='string', action='append')
    p.add_option('--lutResolution1d', '', type='int', default=1024)
    p.add_option('--lutResolution3d', '', type='int', default=33)
    p.add_option('--ctlReleasePath', '-r', type='string', default='')
    p.add_option('--bitDepth', '-b', type='string', default='float')
    p.add_option('--keepTempImages', '', action='store_true')
    p.add_option('--minValue', '', type='float', default=0)
    p.add_option('--maxValue', '', type='float', default=1)
    p.add_option('--inputScale', '', type='float', default=1)
    p.add_option('--outputScale', '', type='float', default=1)
    p.add_option('--ctlRenderParam', '-p', type='string', nargs=2,
                 action='append')

    p.add_option('--generate1d', '', action='store_true')
    p.add_option('--generate3d', '', action='store_true')

    options, arguments = p.parse_args()

    lut = options.lut
    format = options.format
    ctls = options.ctl
    lut_resolution_1d = options.lutResolution1d
    lut_resolution_3d = options.lutResolution3d
    min_value = options.minValue
    max_value = options.maxValue
    input_scale = options.inputScale
    output_scale = options.outputScale
    ctl_release_path = options.ctlReleasePath
    generate_1d = options.generate1d is True
    generate_3d = options.generate3d is True
    bit_depth = options.bitDepth
    cleanup = not options.keepTempImages

    params = {}
    if options.ctlRenderParam is not None:
        for param in options.ctlRenderParam:
            params[param[0]] = float(param[1])

    try:
        args_start = sys.argv.index('--') + 1
        args = sys.argv[args_start:]
    except:
        args_start = len(sys.argv) + 1
        args = []

    if generate_1d:
        print('1D LUT generation options')
    else:
        print('3D LUT generation options')

    print('lut                 : %s' % lut)
    print('format              : %s' % format)
    print('ctls                : %s' % ctls)
    print('lut res 1d          : %s' % lut_resolution_1d)
    print('lut res 3d          : %s' % lut_resolution_3d)
    print('min value           : %s' % min_value)
    print('max value           : %s' % max_value)
    print('input scale         : %s' % input_scale)
    print('output scale        : %s' % output_scale)
    print('ctl render params   : %s' % params)
    print('ctl release path    : %s' % ctl_release_path)
    print('bit depth of input  : %s' % bit_depth)
    print('cleanup temp images : %s' % cleanup)

    if generate_1d:
        generate_1d_LUT_from_CTL(lut,
                                 ctls,
                                 lut_resolution_1d,
                                 bit_depth,
                                 input_scale,
                                 output_scale,
                                 params,
                                 cleanup,
                                 ctl_release_path,
                                 min_value,
                                 max_value,
                                 format=format)

    elif generate_3d:
        generate_3d_LUT_from_CTL(lut,
                                 ctls,
                                 lut_resolution_3d,
                                 bit_depth,
                                 input_scale,
                                 output_scale,
                                 params,
                                 cleanup,
                                 ctl_release_path,
                                 format=format)
    else:
        print(('\n\nNo LUT generated. '
               'You must choose either 1D or 3D LUT generation\n\n'))


if __name__ == '__main__':
    main()

