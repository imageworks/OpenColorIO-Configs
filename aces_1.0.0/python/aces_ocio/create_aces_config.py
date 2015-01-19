#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines objects creating the *ACES* configuration.
"""

import math
import numpy
import os
import pprint
import shutil
import string
import sys

# TODO: This restores the capability of running the script without having
# added the package to PYTHONPATH, this is ugly and should ideally replaced by
# dedicated executable in a /bin directory.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import PyOpenColorIO as ocio

import aces_ocio.create_arri_colorspaces as arri
import aces_ocio.create_canon_colorspaces as canon
import aces_ocio.create_red_colorspaces as red
import aces_ocio.create_sony_colorspaces as sony
from aces_ocio.generate_lut import (
    generate_1d_LUT_from_CTL,
    generate_3d_LUT_from_CTL,
    write_SPI_1d)
from aces_ocio.process import Process
from aces_ocio.utilities import ColorSpace, mat44_from_mat33

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['ACES_OCIO_CTL_DIRECTORY_ENVIRON',
           'ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON',
           'set_config_default_roles',
           'write_config',
           'generate_OCIO_transform',
           'create_config',
           'generate_LUTs',
           'generate_baked_LUTs',
           'create_config_dir',
           'get_transform_info',
           'get_ODT_info',
           'get_LMT_info',
           'create_ACES_config',
           'main']

ACES_OCIO_CTL_DIRECTORY_ENVIRON = 'ACES_OCIO_CTL_DIRECTORY'
ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON = 'ACES_OCIO_CONFIGURATION_DIRECTORY'


def set_config_default_roles(config,
                             color_picking='',
                             color_timing='',
                             compositing_log='',
                             data='',
                             default='',
                             matte_paint='',
                             reference='',
                             scene_linear='',
                             texture_paint=''):
    """
    Sets given *OCIO* configuration default roles.

    Parameters
    ----------
    config : config
        *OCIO* configuration.
    color_picking : str or unicode
        Color picking role title.
    color_timing : str or unicode
        Color timing role title.
    compositing_log : str or unicode
        Compositing log role title.
    data : str or unicode
        Data role title.
    default : str or unicode
        Default role title.
    matte_paint : str or unicode
        Matte painting role title.
    reference : str or unicode
        Reference role title.
    scene_linear : str or unicode
        Scene linear role title.
    texture_paint : str or unicode
        Texture painting role title.

    Returns
    -------
    bool
         Definition success.
    """

    if color_picking:
        config.setRole(ocio.Constants.ROLE_COLOR_PICKING, color_picking)
    if color_timing:
        config.setRole(ocio.Constants.ROLE_COLOR_TIMING, color_timing)
    if compositing_log:
        config.setRole(ocio.Constants.ROLE_COMPOSITING_LOG, compositing_log)
    if data:
        config.setRole(ocio.Constants.ROLE_DATA, data)
    if default:
        config.setRole(ocio.Constants.ROLE_DEFAULT, default)
    if matte_paint:
        config.setRole(ocio.Constants.ROLE_MATTE_PAINT, matte_paint)
    if reference:
        config.setRole(ocio.Constants.ROLE_REFERENCE, reference)
    if scene_linear:
        config.setRole(ocio.Constants.ROLE_SCENE_LINEAR, scene_linear)
    if texture_paint:
        config.setRole(ocio.Constants.ROLE_TEXTURE_PAINT, texture_paint)

    return True


def write_config(config, config_path, sanity_check=True):
    """
    Writes the configuration to given path.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    if sanity_check:
        try:
            config.sanityCheck()
        except Exception, e:
            print e
            print 'Configuration was not written due to a failed Sanity Check'
            return
            # sys.exit()

    file_handle = open(config_path, mode='w')
    file_handle.write(config.serialize())
    file_handle.close()


def generate_OCIO_transform(transforms):
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

    # print('Generating transforms')

    interpolation_options = {
        'linear': ocio.Constants.INTERP_LINEAR,
        'nearest': ocio.Constants.INTERP_NEAREST,
        'tetrahedral': ocio.Constants.INTERP_TETRAHEDRAL
    }
    direction_options = {
        'forward': ocio.Constants.TRANSFORM_DIR_FORWARD,
        'inverse': ocio.Constants.TRANSFORM_DIR_INVERSE
    }

    ocio_transforms = []

    for transform in transforms:
        if transform['type'] == 'lutFile':
            ocio_transform = ocio.FileTransform(
                src=transform['path'],
                interpolation=interpolation_options[
                    transform['interpolation']],
                direction=direction_options[transform['direction']])
            ocio_transforms.append(ocio_transform)
        elif transform['type'] == 'matrix':
            ocio_transform = ocio.MatrixTransform()
            # MatrixTransform member variables can't be initialized directly.
            # Each must be set individually.
            ocio_transform.setMatrix(transform['matrix'])

            if 'offset' in transform:
                ocio_transform.setOffset(transform['offset'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)
        elif transform['type'] == 'exponent':
            ocio_transform = ocio.ExponentTransform()
            ocio_transform.setValue(transform['value'])
            ocio_transforms.append(ocio_transform)
        elif transform['type'] == 'log':
            ocio_transform = ocio.LogTransform(
                base=transform['base'],
                direction=direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)
        else:
            print('Ignoring unknown transform type : %s' % transform['type'])

    # Build a group transform if necessary
    if len(ocio_transforms) > 1:
        transform_G = ocio.GroupTransform()
        for transform in ocio_transforms:
            transform_G.push_back(transform)
        transform = transform_G

    # Or take the first transform from the list
    else:
        transform = ocio_transforms[0]

    return transform


def create_config(config_data, nuke=False):
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

    # Create the config
    config = ocio.Config()

    #
    # Set config wide values
    #
    config.setDescription('An ACES config generated from python')
    config.setSearchPath('luts')

    #
    # Define the reference color space
    #
    reference_data = config_data['referenceColorSpace']
    print('Adding the reference color space : %s' % reference_data.name)

    # Create a color space
    reference = ocio.ColorSpace(
        name=reference_data.name,
        bitDepth=reference_data.bit_depth,
        description=reference_data.description,
        equalityGroup=reference_data.equality_group,
        family=reference_data.family,
        isData=reference_data.is_data,
        allocation=reference_data.allocation_type,
        allocationVars=reference_data.allocation_vars)

    # Add to config
    config.addColorSpace(reference)

    #
    # Create the rest of the color spaces
    #
    for colorspace in sorted(config_data['colorSpaces']):
        print('Creating new color space : %s' % colorspace.name)

        ocio_colorspace = ocio.ColorSpace(
            name=colorspace.name,
            bitDepth=colorspace.bit_depth,
            description=colorspace.description,
            equalityGroup=colorspace.equality_group,
            family=colorspace.family,
            isData=colorspace.is_data,
            allocation=colorspace.allocation_type,
            allocationVars=colorspace.allocation_vars)

        if colorspace.to_reference_transforms != []:
            print('Generating To-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                colorspace.to_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_TO_REFERENCE)

        if colorspace.from_reference_transforms != []:
            print('Generating From-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                colorspace.from_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_FROM_REFERENCE)

        config.addColorSpace(ocio_colorspace)

        print('')

    #
    # Define the views and displays
    #
    displays = []
    views = []

    # Generic display and view setup
    if not nuke:
        for display, view_list in config_data['displays'].iteritems():
            for view_name, colorspace in view_list.iteritems():
                config.addDisplay(display, view_name, colorspace.name)
                if not (view_name in views):
                    views.append(view_name)
            displays.append(display)
    # A Nuke specific set of views and displays
    #
    # XXX
    # A few names: Output Transform, ACES, ACEScc, are hard-coded here.
    # Would be better to automate.
    #
    else:
        for display, view_list in config_data['displays'].iteritems():
            for view_name, colorspace in view_list.iteritems():
                if (view_name == 'Output Transform'):
                    view_name = 'View'
                    config.addDisplay(display, view_name, colorspace.name)
                    if not (view_name in views):
                        views.append(view_name)
            displays.append(display)

        config.addDisplay('linear', 'View', 'ACES2065-1')
        displays.append('linear')
        config.addDisplay('log', 'View', 'ACEScc')
        displays.append('log')

    # Set active displays and views
    config.setActiveDisplays(','.join(sorted(displays)))
    config.setActiveViews(','.join(views))

    #
    # Need to generalize this at some point
    #

    # Add Default Roles
    set_config_default_roles(
        config,
        color_picking=reference.getName(),
        color_timing=reference.getName(),
        compositing_log=reference.getName(),
        data=reference.getName(),
        default=reference.getName(),
        matte_paint=reference.getName(),
        reference=reference.getName(),
        scene_linear=reference.getName(),
        texture_paint=reference.getName())

    # Check to make sure we didn't screw something up
    config.sanityCheck()

    return config


def generate_LUTs(odt_info,
                  lmt_info,
                  shaper_name,
                  aces_CTL_directory,
                  lut_directory,
                  lut_resolution_1d=4096,
                  lut_resolution_3d=64,
                  cleanup=True):
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    dict
         Colorspaces and transforms converting between those colorspaces and
         the reference colorspace, *ACES*.
    """

    print('generateLUTs - begin')
    config_data = {}

    #
    # Define the reference color space
    #
    ACES = ColorSpace('ACES2065-1')
    ACES.description = (
        'The Academy Color Encoding System reference color space')
    ACES.equality_group = ''
    ACES.family = 'ACES'
    ACES.is_data = False
    ACES.allocation_type = ocio.Constants.ALLOCATION_LG2
    ACES.allocation_vars = [-15, 6]

    config_data['referenceColorSpace'] = ACES

    #
    # Define the displays
    #
    config_data['displays'] = {}

    #
    # Define the other color spaces
    #
    config_data['colorSpaces'] = []

    # Matrix converting ACES AP1 primaries to AP0
    ACES_AP1_to_AP0 = [0.6954522414, 0.1406786965, 0.1638690622,
                       0.0447945634, 0.8596711185, 0.0955343182,
                       -0.0055258826, 0.0040252103, 1.0015006723]

    # Matrix converting ACES AP0 primaries to XYZ
    ACES_AP0_to_XYZ = [0.9525523959, 0.0000000000, 0.0000936786,
                       0.3439664498, 0.7281660966, -0.0721325464,
                       0.0000000000, 0.0000000000, 1.0088251844]

    #
    # ACEScc
    #
    def create_ACEScc(name='ACEScc',
                      min_value=0.0,
                      max_value=1.0,
                      input_scale=1.0):
        cs = ColorSpace(name)
        cs.description = 'The %s color space' % name
        cs.equality_group = ''
        cs.family = 'ACES'
        cs.is_data = False

        ctls = [
            '%s/ACEScc/ACEScsc.ACEScc_to_ACES.a1.0.0.ctl' % aces_CTL_directory,
            # This transform gets back to the AP1 primaries
            # Useful as the 1d LUT is only covering the transfer function
            # The primaries switch is covered by the matrix below
            '%s/ACEScg/ACEScsc.ACES_to_ACEScg.a1.0.0.ctl' % aces_CTL_directory
        ]
        lut = '%s_to_ACES.spi1d' % name

        # Remove spaces and parentheses
        lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

        generate_1d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            ctls,
            lut_resolution_1d,
            'float',
            input_scale,
            1.0,
            {},
            cleanup,
            aces_CTL_directory,
            min_value,
            max_value)

        cs.to_reference_transforms = []
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

        # AP1 primaries to AP0 primaries
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(ACES_AP1_to_AP0),
            'direction': 'forward'
        })

        cs.from_reference_transforms = []
        return cs

    ACEScc = create_ACEScc()
    config_data['colorSpaces'].append(ACEScc)

    #
    # ACESproxy
    #
    def create_ACESproxy(name='ACESproxy'):
        cs = ColorSpace(name)
        cs.description = 'The %s color space' % name
        cs.equality_group = ''
        cs.family = 'ACES'
        cs.is_data = False

        ctls = [
            '%s/ACESproxy/ACEScsc.ACESproxy10i_to_ACES.a1.0.0.ctl' % (
                aces_CTL_directory),
            # This transform gets back to the AP1 primaries
            # Useful as the 1d LUT is only covering the transfer function
            # The primaries switch is covered by the matrix below
            '%s/ACEScg/ACEScsc.ACES_to_ACEScg.a1.0.0.ctl' % aces_CTL_directory
        ]
        lut = '%s_to_aces.spi1d' % name

        # Remove spaces and parentheses
        lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

        generate_1d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            ctls,
            lut_resolution_1d,
            'uint16',
            64.0,
            1.0,
            {},
            cleanup,
            aces_CTL_directory)

        cs.to_reference_transforms = []
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

        # AP1 primaries to AP0 primaries
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(ACES_AP1_to_AP0),
            'direction': 'forward'
        })

        cs.from_reference_transforms = []
        return cs

    ACESproxy = create_ACESproxy()
    config_data['colorSpaces'].append(ACESproxy)

    #
    # ACEScg
    #
    def create_ACEScg(name='ACEScg'):
        cs = ColorSpace(name)
        cs.description = 'The %s color space' % name
        cs.equality_group = ''
        cs.family = 'ACES'
        cs.is_data = False

        cs.to_reference_transforms = []

        # AP1 primaries to AP0 primaries
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': mat44_from_mat33(ACES_AP1_to_AP0),
            'direction': 'forward'
        })

        cs.from_reference_transforms = []
        return cs

    ACEScg = create_ACEScg()
    config_data['colorSpaces'].append(ACEScg)

    #
    # ADX
    #
    def create_ADX(bit_depth=10, name='ADX'):
        name = '%s%s' % (name, bit_depth)
        cs = ColorSpace(name)
        cs.description = '%s color space - used for film scans' % name
        cs.equality_group = ''
        cs.family = 'ADX'
        cs.is_data = False

        if bit_depth == 10:
            cs.bit_depth = bit_depth = ocio.Constants.BIT_DEPTH_UINT10
            adx_to_cdd = [1023.0 / 500.0, 0.0, 0.0, 0.0,
                          0.0, 1023.0 / 500.0, 0.0, 0.0,
                          0.0, 0.0, 1023.0 / 500.0, 0.0,
                          0.0, 0.0, 0.0, 1.0]
            offset = [-95.0 / 500.0, -95.0 / 500.0, -95.0 / 500.0, 0.0]
        elif bit_depth == 16:
            cs.bit_depth = bit_depth = ocio.Constants.BIT_DEPTH_UINT16
            adx_to_cdd = [65535.0 / 8000.0, 0.0, 0.0, 0.0,
                          0.0, 65535.0 / 8000.0, 0.0, 0.0,
                          0.0, 0.0, 65535.0 / 8000.0, 0.0,
                          0.0, 0.0, 0.0, 1.0]
            offset = [-1520.0 / 8000.0, -1520.0 / 8000.0, -1520.0 / 8000.0,
                      0.0]

        cs.to_reference_transforms = []

        # Convert from ADX to Channel-Dependent Density
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': adx_to_cdd,
            'offset': offset,
            'direction': 'forward'
        })

        # Convert from Channel-Dependent Density to Channel-Independent Density
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': [0.75573, 0.22197, 0.02230, 0,
                       0.05901, 0.96928, -0.02829, 0,
                       0.16134, 0.07406, 0.76460, 0,
                       0.0, 0.0, 0.0, 1.0],
            'direction': 'forward'
        })

        # Copied from Alex Fry's adx_cid_to_rle.py
        def create_CID_to_RLE_LUT():
            def interpolate_1D(x, xp, fp):
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

            REF_PT = ((7120.0 - 1520.0) / 8000.0 * (100.0 / 55.0) -
                      math.log(0.18, 10.0))

            def cid_to_rle(x):
                if x <= 0.6:
                    return interpolate_1D(x, LUT_1D_xp, LUT_1D_fp)
                return (100.0 / 55.0) * x - REF_PT

            def fit(value, from_min, from_max, to_min, to_max):
                if from_min == from_max:
                    raise ValueError('from_min == from_max')
                return (value - from_min) / (from_max - from_min) * (
                    to_max - to_min) + to_min

            NUM_SAMPLES = 2 ** 12
            RANGE = (-0.19, 3.0)
            data = []
            for i in xrange(NUM_SAMPLES):
                x = i / (NUM_SAMPLES - 1.0)
                x = fit(x, 0.0, 1.0, RANGE[0], RANGE[1])
                data.append(cid_to_rle(x))

            lut = 'ADX_CID_to_RLE.spi1d'
            write_SPI_1d(os.path.join(lut_directory, lut),
                         RANGE[0],
                         RANGE[1],
                         data,
                         NUM_SAMPLES, 1)

            return lut

        # Convert Channel Independent Density values to Relative Log Exposure
        # values.
        lut = create_CID_to_RLE_LUT()
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

        # Convert Relative Log Exposure values to Relative Exposure values
        cs.to_reference_transforms.append({
            'type': 'log',
            'base': 10,
            'direction': 'inverse'
        })

        # Convert Relative Exposure values to ACES values
        cs.to_reference_transforms.append({
            'type': 'matrix',
            'matrix': [0.72286, 0.12630, 0.15084, 0,
                       0.11923, 0.76418, 0.11659, 0,
                       0.01427, 0.08213, 0.90359, 0,
                       0.0, 0.0, 0.0, 1.0],
            'direction': 'forward'
        })

        cs.from_reference_transforms = []
        return cs

    ADX10 = create_ADX(bit_depth=10)
    config_data['colorSpaces'].append(ADX10)

    ADX16 = create_ADX(bit_depth=16)
    config_data['colorSpaces'].append(ADX16)

    #
    # Camera Input Transforms
    #

    # RED color spaces to ACES
    red_colorspaces = red.create_colorspaces(lut_directory, lut_resolution_1d)
    for cs in red_colorspaces:
        config_data['colorSpaces'].append(cs)

    # Canon-Log to ACES
    canon_colorspaces = canon.create_colorspaces(lut_directory,
                                                 lut_resolution_1d)
    for cs in canon_colorspaces:
        config_data['colorSpaces'].append(cs)

    # S-Log to ACES
    sony_colorSpaces = sony.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in sony_colorSpaces:
        config_data['colorSpaces'].append(cs)

    # Log-C to ACES
    arri_colorSpaces = arri.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in arri_colorSpaces:
        config_data['colorSpaces'].append(cs)

    #
    # Generic log transform
    #
    def create_generic_log(name='log',
                           min_value=0.0,
                           max_value=1.0,
                           input_scale=1.0,
                           middle_grey=0.18,
                           min_exposure=-6.0,
                           max_exposure=6.5,
                           lut_resolution_1d=lut_resolution_1d):
        cs = ColorSpace(name)
        cs.description = 'The %s color space' % name
        cs.equality_group = name
        cs.family = 'Utility'
        cs.is_data = False

        ctls = [
            '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl' % (
                aces_CTL_directory)]
        lut = '%s_to_aces.spi1d' % name

        # Remove spaces and parentheses
        lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

        generate_1d_LUT_from_CTL(
            os.path.join(lut_directory, lut),
            ctls,
            lut_resolution_1d,
            'float',
            input_scale,
            1.0,
            {
                'middleGrey': middle_grey,
                'minExposure': min_exposure,
                'maxExposure': max_exposure
            },
            cleanup,
            aces_CTL_directory,
            min_value,
            max_value)

        cs.to_reference_transforms = []
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

        cs.from_reference_transforms = []
        return cs

    #
    # ACES LMTs
    #
    def create_ACES_LMT(lmt_name,
                        lmt_values,
                        shaper_info,
                        lut_resolution_1d=1024,
                        lut_resolution_3d=64,
                        cleanup=True):
        cs = ColorSpace('%s' % lmt_name)
        cs.description = 'The ACES Look Transform: %s' % lmt_name
        cs.equality_group = ''
        cs.family = 'Look'
        cs.is_data = False

        pprint.pprint(lmt_values)

        #
        # Generate the shaper transform
        #
        (shaper_name,
         shaper_to_ACES_CTL,
         shaper_from_ACES_CTL,
         shaper_input_scale,
         shaper_params) = shaper_info

        shaper_lut = '%s_to_aces.spi1d' % shaper_name
        if (not os.path.exists(os.path.join(lut_directory, shaper_lut))):
            ctls = [shaper_to_ACES_CTL % aces_CTL_directory]

            # Remove spaces and parentheses
            shaper_lut = shaper_lut.replace(
                ' ', '_').replace(')', '_').replace('(', '_')

            generate_1d_LUT_from_CTL(
                os.path.join(lut_directory, shaper_lut),
                ctls,
                lut_resolution_1d,
                'float',
                1.0 / shaper_input_scale,
                1.0,
                shaper_params,
                cleanup,
                aces_CTL_directory)

        shaper_OCIO_transform = {
            'type': 'lutFile',
            'path': shaper_lut,
            'interpolation': 'linear',
            'direction': 'inverse'
        }

        #
        # Generate the forward transform
        #
        cs.from_reference_transforms = []

        if 'transformCTL' in lmt_values:
            ctls = [
                shaper_to_ACES_CTL % aces_CTL_directory,
                '%s/%s' % (aces_CTL_directory, lmt_values['transformCTL'])
            ]
            lut = '%s.%s.spi3d' % (shaper_name, lmt_name)

            # Remove spaces and parentheses
            lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

            generate_3d_LUT_from_CTL(
                os.path.join(lut_directory, lut),
                ctls,
                lut_resolution_3d,
                'float',
                1.0 / shaper_input_scale,
                1.0,
                shaper_params,
                cleanup,
                aces_CTL_directory)

            cs.from_reference_transforms.append(shaper_OCIO_transform)
            cs.from_reference_transforms.append({
                'type': 'lutFile',
                'path': lut,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })

        #
        # Generate the inverse transform
        #
        cs.to_reference_transforms = []

        if 'transformCTLInverse' in lmt_values:
            ctls = [
                '%s/%s' % (
                    aces_CTL_directory, odt_values['transformCTLInverse']),
                shaper_from_ACES_CTL % aces_CTL_directory
            ]
            lut = 'Inverse.%s.%s.spi3d' % (odt_name, shaper_name)

            # Remove spaces and parentheses
            lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

            generate_3d_LUT_from_CTL(
                os.path.join(lut_directory, lut),
                ctls,
                lut_resolution_3d,
                'half',
                1.0,
                shaper_input_scale,
                shaper_params,
                cleanup,
                aces_CTL_directory)

            cs.to_reference_transforms.append({
                'type': 'lutFile',
                'path': lut,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })

            shaper_inverse = shaper_OCIO_transform.copy()
            shaper_inverse['direction'] = 'forward'
            cs.to_reference_transforms.append(shaper_inverse)

        return cs

    #
    # LMT Shaper
    #

    lmt_lut_resolution_1d = max(4096, lut_resolution_1d)
    lmt_lut_resolution_3d = max(65, lut_resolution_3d)

    # Log 2 shaper
    lmt_shaper_name = 'LMT Shaper'
    lmt_params = {
        'middleGrey': 0.18,
        'minExposure': -10.0,
        'maxExposure': 6.5
    }
    lmt_shaper = create_generic_log(name=lmt_shaper_name,
                                    middle_grey=lmt_params['middleGrey'],
                                    min_exposure=lmt_params['minExposure'],
                                    max_exposure=lmt_params['maxExposure'],
                                    lut_resolution_1d=lmt_lut_resolution_1d)
    config_data['colorSpaces'].append(lmt_shaper)

    shaper_input_scale_generic_log2 = 1.0

    # Log 2 shaper name and CTL transforms bundled up
    lmt_shaper_data = [
        lmt_shaper_name,
        '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl',
        '%s/utilities/ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl',
        shaper_input_scale_generic_log2,
        lmt_params
    ]

    sorted_LMTs = sorted(lmt_info.iteritems(), key=lambda x: x[1])
    print(sorted_LMTs)
    for lmt in sorted_LMTs:
        (lmt_name, lmt_values) = lmt
        cs = create_ACES_LMT(
            lmt_values['transformUserName'],
            lmt_values,
            lmt_shaper_data,
            lmt_lut_resolution_1d,
            lmt_lut_resolution_3d,
            cleanup)
        config_data['colorSpaces'].append(cs)

    #
    # ACES RRT with the supplied ODT
    #
    def create_ACES_RRT_plus_ODT(odt_name,
                                 odt_values,
                                 shaper_info,
                                 lut_resolution_1d=1024,
                                 lut_resolution_3d=64,
                                 cleanup=True):
        cs = ColorSpace('%s' % odt_name)
        cs.description = '%s - %s Output Transform' % (
            odt_values['transformUserNamePrefix'], odt_name)
        cs.equality_group = ''
        cs.family = 'Output'
        cs.is_data = False

        pprint.pprint(odt_values)

        #
        # Generate the shaper transform
        #
        # if 'shaperCTL' in odtValues:
        (shaper_name,
         shaper_to_ACES_CTL,
         shaper_from_ACES_CTL,
         shaper_input_scale,
         shaper_params) = shaper_info

        if 'legalRange' in odt_values:
            shaper_params['legalRange'] = odt_values['legalRange']
        else:
            shaper_params['legalRange'] = 0

        shaper_lut = '%s_to_aces.spi1d' % shaper_name
        if (not os.path.exists(os.path.join(lut_directory, shaper_lut))):
            ctls = [shaper_to_ACES_CTL % aces_CTL_directory]

            # Remove spaces and parentheses
            shaper_lut = shaper_lut.replace(
                ' ', '_').replace(')', '_').replace('(', '_')

            generate_1d_LUT_from_CTL(
                os.path.join(lut_directory, shaper_lut),
                ctls,
                lut_resolution_1d,
                'float',
                1.0 / shaper_input_scale,
                1.0,
                shaper_params,
                cleanup,
                aces_CTL_directory)

        shaper_OCIO_transform = {
            'type': 'lutFile',
            'path': shaper_lut,
            'interpolation': 'linear',
            'direction': 'inverse'
        }

        #
        # Generate the forward transform
        #
        cs.from_reference_transforms = []

        if 'transformLUT' in odt_values:
            # Copy into the lut dir
            transform_LUT_file_name = os.path.basename(
                odt_values['transformLUT'])
            lut = os.path.join(lut_directory, transform_LUT_file_name)
            shutil.copy(odt_values['transformLUT'], lut)

            cs.from_reference_transforms.append(shaper_OCIO_transform)
            cs.from_reference_transforms.append({
                'type': 'lutFile',
                'path': transform_LUT_file_name,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })
        elif 'transformCTL' in odt_values:
            # shaperLut

            ctls = [
                shaper_to_ACES_CTL % aces_CTL_directory,
                '%s/rrt/RRT.a1.0.0.ctl' % aces_CTL_directory,
                '%s/odt/%s' % (aces_CTL_directory, odt_values['transformCTL'])
            ]
            lut = '%s.RRT.a1.0.0.%s.spi3d' % (shaper_name, odt_name)

            # Remove spaces and parentheses
            lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

            generate_3d_LUT_from_CTL(
                os.path.join(lut_directory, lut),
                # shaperLUT,
                ctls,
                lut_resolution_3d,
                'float',
                1.0 / shaper_input_scale,
                1.0,
                shaper_params,
                cleanup,
                aces_CTL_directory)

            cs.from_reference_transforms.append(shaper_OCIO_transform)
            cs.from_reference_transforms.append({
                'type': 'lutFile',
                'path': lut,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })

        #
        # Generate the inverse transform
        #
        cs.to_reference_transforms = []

        if 'transformLUTInverse' in odt_values:
            # Copy into the lut dir
            transform_LUT_inverse_file_name = os.path.basename(
                odt_values['transformLUTInverse'])
            lut = os.path.join(lut_directory, transform_LUT_inverse_file_name)
            shutil.copy(odt_values['transformLUTInverse'], lut)

            cs.to_reference_transforms.append({
                'type': 'lutFile',
                'path': transform_LUT_inverse_file_name,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })

            shaper_inverse = shaper_OCIO_transform.copy()
            shaper_inverse['direction'] = 'forward'
            cs.to_reference_transforms.append(shaper_inverse)
        elif 'transformCTLInverse' in odt_values:
            ctls = [
                '%s/odt/%s' % (
                    aces_CTL_directory, odt_values['transformCTLInverse']),
                '%s/rrt/InvRRT.a1.0.0.ctl' % aces_CTL_directory,
                shaper_from_ACES_CTL % aces_CTL_directory
            ]
            lut = 'InvRRT.a1.0.0.%s.%s.spi3d' % (odt_name, shaper_name)

            # Remove spaces and parentheses
            lut = lut.replace(' ', '_').replace(')', '_').replace('(', '_')

            generate_3d_LUT_from_CTL(
                os.path.join(lut_directory, lut),
                # None,
                ctls,
                lut_resolution_3d,
                'half',
                1.0,
                shaper_input_scale,
                shaper_params,
                cleanup,
                aces_CTL_directory)

            cs.to_reference_transforms.append({
                'type': 'lutFile',
                'path': lut,
                'interpolation': 'tetrahedral',
                'direction': 'forward'
            })

            shaper_inverse = shaper_OCIO_transform.copy()
            shaper_inverse['direction'] = 'forward'
            cs.to_reference_transforms.append(shaper_inverse)

        return cs

    #
    # RRT/ODT shaper options
    #
    shaper_data = {}

    # Log 2 shaper
    log2_shaper_name = shaper_name
    log2_params = {
        'middleGrey': 0.18,
        'minExposure': -6.0,
        'maxExposure': 6.5
    }
    log2_shaper = create_generic_log(
        name=log2_shaper_name,
        middle_grey=log2_params['middleGrey'],
        min_exposure=log2_params['minExposure'],
        max_exposure=log2_params['maxExposure'])
    config_data['colorSpaces'].append(log2_shaper)

    shaper_input_scale_generic_log2 = 1.0

    # Log 2 shaper name and CTL transforms bundled up
    log2_shaper_data = [
        log2_shaper_name,
        '%s/utilities/ACESlib.OCIO_shaper_log2_to_lin_param.a1.0.0.ctl',
        '%s/utilities/ACESlib.OCIO_shaper_lin_to_log2_param.a1.0.0.ctl',
        shaper_input_scale_generic_log2,
        log2_params
    ]

    shaper_data[log2_shaper_name] = log2_shaper_data

    #
    # Shaper that also includes the AP1 primaries
    # - Needed for some LUT baking steps
    #
    log2_shaper_AP1 = create_generic_log(
        name=log2_shaper_name,
        middle_grey=log2_params['middleGrey'],
        min_exposure=log2_params['minExposure'],
        max_exposure=log2_params['maxExposure'])
    log2_shaper_AP1.name = '%s - AP1' % log2_shaper_AP1.name
    # AP1 primaries to AP0 primaries
    log2_shaper_AP1.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(ACES_AP1_to_AP0),
        'direction': 'forward'
    })
    config_data['colorSpaces'].append(log2_shaper_AP1)

    #
    # Choose your shaper
    #
    rrt_shaper_name = log2_shaper_name
    rrt_shaper = log2_shaper_data

    #
    # RRT + ODT Combinations
    #
    sorted_odts = sorted(odt_info.iteritems(), key=lambda x: x[1])
    print(sorted_odts)
    for odt in sorted_odts:
        (odt_name, odt_values) = odt

        # Have to handle ODTs that can generate either legal or full output
        if odt_name in ['Academy.Rec2020_100nits_dim.a1.0.0',
                        'Academy.Rec709_100nits_dim.a1.0.0',
                        'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:
            odt_name_legal = '%s - Legal' % odt_values['transformUserName']
        else:
            odt_name_legal = odt_values['transformUserName']

        odt_legal = odt_values.copy()
        odt_legal['legalRange'] = 1

        cs = create_ACES_RRT_plus_ODT(
            odt_name_legal,
            odt_legal,
            rrt_shaper,
            lut_resolution_1d,
            lut_resolution_3d,
            cleanup)
        config_data['colorSpaces'].append(cs)

        # Create a display entry using this color space
        config_data['displays'][odt_name_legal] = {
            'Linear': ACES,
            'Log': ACEScc,
            'Output Transform': cs}

        if odt_name in ['Academy.Rec2020_100nits_dim.a1.0.0',
                        'Academy.Rec709_100nits_dim.a1.0.0',
                        'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:
            print('Generating full range ODT for %s' % odt_name)

            odt_name_full = '%s - Full' % odt_values['transformUserName']
            odt_full = odt_values.copy()
            odt_full['legalRange'] = 0

            cs_full = create_ACES_RRT_plus_ODT(
                odt_name_full,
                odt_full,
                rrt_shaper,
                lut_resolution_1d,
                lut_resolution_3d,
                cleanup)
            config_data['colorSpaces'].append(cs_full)

            # Create a display entry using this color space
            config_data['displays'][odt_name_full] = {
                'Linear': ACES,
                'Log': ACEScc,
                'Output Transform': cs_full}

    #
    # Generic Matrix transform
    #
    def create_generic_matrix(name='matrix',
                              from_reference_values=[],
                              to_reference_values=[]):
        cs = ColorSpace(name)
        cs.description = 'The %s color space' % name
        cs.equality_group = name
        cs.family = 'Utility'
        cs.is_data = False

        cs.to_reference_transforms = []
        if to_reference_values != []:
            for matrix in to_reference_values:
                cs.to_reference_transforms.append({
                    'type': 'matrix',
                    'matrix': mat44_from_mat33(matrix),
                    'direction': 'forward'
                })

        cs.from_reference_transforms = []
        if from_reference_values != []:
            for matrix in from_reference_values:
                cs.from_reference_transforms.append({
                    'type': 'matrix',
                    'matrix': mat44_from_mat33(matrix),
                    'direction': 'forward'
                })

        return cs

    cs = create_generic_matrix('XYZ', from_reference_values=[ACES_AP0_to_XYZ])
    config_data['colorSpaces'].append(cs)

    cs = create_generic_matrix(
        'Linear - AP1', to_reference_values=[ACES_AP1_to_AP0])
    config_data['colorSpaces'].append(cs)

    # ACES to Linear, P3D60 primaries
    XYZ_to_P3D60 = [2.4027414142, -0.8974841639, -0.3880533700,
                    -0.8325796487, 1.7692317536, 0.0237127115,
                    0.0388233815, -0.0824996856, 1.0363685997]

    cs = create_generic_matrix(
        'Linear - P3-D60',
        from_reference_values=[ACES_AP0_to_XYZ, XYZ_to_P3D60])
    config_data['colorSpaces'].append(cs)

    # ACES to Linear, P3D60 primaries
    XYZ_to_P3DCI = [2.7253940305, -1.0180030062, -0.4401631952,
                    -0.7951680258, 1.6897320548, 0.0226471906,
                    0.0412418914, -0.0876390192, 1.1009293786]

    cs = create_generic_matrix(
        'Linear - P3-DCI',
        from_reference_values=[ACES_AP0_to_XYZ, XYZ_to_P3DCI])
    config_data['colorSpaces'].append(cs)

    # ACES to Linear, Rec 709 primaries
    XYZ_to_Rec709 = [3.2409699419, -1.5373831776, -0.4986107603,
                     -0.9692436363, 1.8759675015, 0.0415550574,
                     0.0556300797, -0.2039769589, 1.0569715142]

    cs = create_generic_matrix(
        'Linear - Rec.709',
        from_reference_values=[ACES_AP0_to_XYZ, XYZ_to_Rec709])
    config_data['colorSpaces'].append(cs)

    # ACES to Linear, Rec 2020 primaries
    XYZ_to_Rec2020 = [1.7166511880, -0.3556707838, -0.2533662814,
                      -0.6666843518, 1.6164812366, 0.0157685458,
                      0.0176398574, -0.0427706133, 0.9421031212]

    cs = create_generic_matrix(
        'Linear - Rec.2020',
        from_reference_values=[ACES_AP0_to_XYZ, XYZ_to_Rec2020])
    config_data['colorSpaces'].append(cs)

    print('generateLUTs - end')
    return config_data


def generate_baked_LUTs(odt_info,
                        shaper_name,
                        baked_directory,
                        config_path,
                        lut_resolution_1d,
                        lut_resolution_3d,
                        lut_resolution_shaper=1024):
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

    # Add the legal and full variations into this list
    odt_info_C = dict(odt_info)
    for odt_CTL_name, odt_values in odt_info.iteritems():
        if odt_CTL_name in ['Academy.Rec2020_100nits_dim.a1.0.0',
                            'Academy.Rec709_100nits_dim.a1.0.0',
                            'Academy.Rec709_D60sim_100nits_dim.a1.0.0']:
            odt_name = odt_values['transformUserName']

            odt_values_legal = dict(odt_values)
            odt_values_legal['transformUserName'] = '%s - Legal' % odt_name
            odt_info_C['%s - Legal' % odt_CTL_name] = odt_values_legal

            odt_values_full = dict(odt_values)
            odt_values_full['transformUserName'] = '%s - Full' % odt_name
            odt_info_C['%s - Full' % odt_CTL_name] = odt_values_full

            del (odt_info_C[odt_CTL_name])

    for odt_CTL_name, odt_values in odt_info_C.iteritems():
        odt_prefix = odt_values['transformUserNamePrefix']
        odt_name = odt_values['transformUserName']

        # For Photoshop
        for input_space in ['ACEScc', 'ACESproxy']:
            args = ['--iconfig', config_path,
                    '-v',
                    '--inputspace', input_space]
            args += ['--outputspace', '%s' % odt_name]
            args += ['--description',
                     '%s - %s for %s data' % (odt_prefix,
                                              odt_name,
                                              input_space)]
            args += ['--shaperspace', shaper_name,
                     '--shapersize', str(lut_resolution_shaper)]
            args += ['--cubesize', str(lut_resolution_3d)]
            args += ['--format',
                     'icc',
                     '%s/photoshop/%s for %s.icc' % (baked_directory,
                                                     odt_name,
                                                     input_space)]

            bake_LUT = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=args)
            bake_LUT.execute()

        # For Flame, Lustre
        for input_space in ['ACEScc', 'ACESproxy']:
            args = ['--iconfig', config_path,
                    '-v',
                    '--inputspace', input_space]
            args += ['--outputspace', '%s' % odt_name]
            args += ['--description',
                     '%s - %s for %s data' % (
                         odt_prefix, odt_name, input_space)]
            args += ['--shaperspace', shaper_name,
                     '--shapersize', str(lut_resolution_shaper)]
            args += ['--cubesize', str(lut_resolution_3d)]

            fargs = ['--format', 'flame', '%s/flame/%s for %s Flame.3dl' % (
                baked_directory, odt_name, input_space)]
            bake_LUT = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + fargs))
            bake_LUT.execute()

            largs = ['--format', 'lustre', '%s/lustre/%s for %s Lustre.3dl' % (
                baked_directory, odt_name, input_space)]
            bake_LUT = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + largs))
            bake_LUT.execute()

        # For Maya, Houdini
        for input_space in ['ACEScg', 'ACES2065-1']:
            args = ['--iconfig', config_path,
                    '-v',
                    '--inputspace', input_space]
            args += ['--outputspace', '%s' % odt_name]
            args += ['--description',
                     '%s - %s for %s data' % (
                         odt_prefix, odt_name, input_space)]
            if input_space == 'ACEScg':
                lin_shaper_name = '%s - AP1' % shaper_name
            else:
                lin_shaper_name = shaper_name
            args += ['--shaperspace', lin_shaper_name,
                     '--shapersize', str(lut_resolution_shaper)]

            args += ['--cubesize', str(lut_resolution_3d)]

            margs = ['--format', 'cinespace', '%s/maya/%s for %s Maya.csp' % (
                baked_directory, odt_name, input_space)]
            bake_LUT = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + margs))
            bake_LUT.execute()

            hargs = ['--format', 'houdini',
                     '%s/houdini/%s for %s Houdini.lut' % (
                         baked_directory, odt_name, input_space)]
            bake_LUT = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + hargs))
            bake_LUT.execute()


def create_config_dir(config_directory, bake_secondary_LUTs):
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

    dirs = [config_directory, '%s/luts' % config_directory]
    if bake_secondary_LUTs:
        dirs.extend(['%s/baked' % config_directory,
                     '%s/baked/flame' % config_directory,
                     '%s/baked/photoshop' % config_directory,
                     '%s/baked/houdini' % config_directory,
                     '%s/baked/lustre' % config_directory,
                     '%s/baked/maya' % config_directory])

    for d in dirs:
        not os.path.exists(d) and os.mkdir(d)


def get_transform_info(ctl_transform):
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

    # TODO: Use *with* statement.
    fp = open(ctl_transform, 'rb')

    # Read lines
    lines = fp.readlines()

    # Grab transform ID and User Name
    transform_ID = lines[1][3:].split('<')[1].split('>')[1].strip()
    # print(transformID)
    transform_user_name = '-'.join(
        lines[2][3:].split('<')[1].split('>')[1].split('-')[1:]).strip()
    transform_user_name_prefix = (
        lines[2][3:].split('<')[1].split('>')[1].split('-')[0].strip())
    # print(transformUserName)
    fp.close()

    return transform_ID, transform_user_name, transform_user_name_prefix


def get_ODT_info(aces_CTL_directory):
    """
    Object description.

    For versions after WGR9.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate usage of *files_walker* definition here.
    # Credit to Alex Fry for the original approach here
    odt_dir = os.path.join(aces_CTL_directory, 'odt')
    all_odt = []
    for dir_name, subdir_list, file_list in os.walk(odt_dir):
        for fname in file_list:
            all_odt.append((os.path.join(dir_name, fname)))

    odt_CTLs = [x for x in all_odt if
                ('InvODT' not in x) and (os.path.split(x)[-1][0] != '.')]

    # print odtCTLs

    odts = {}

    for odt_CTL in odt_CTLs:
        odt_tokens = os.path.split(odt_CTL)
        # print(odtTokens)

        # Handle nested directories
        odt_path_tokens = os.path.split(odt_tokens[-2])
        odt_dir = odt_path_tokens[-1]
        while odt_path_tokens[-2][-3:] != 'odt':
            odt_path_tokens = os.path.split(odt_path_tokens[-2])
            odt_dir = os.path.join(odt_path_tokens[-1], odt_dir)

        # Build full name
        # print('odtDir : %s' % odtDir)
        transform_CTL = odt_tokens[-1]
        # print(transformCTL)
        odt_name = string.join(transform_CTL.split('.')[1:-1], '.')
        # print(odtName)

        # Find id, user name and user name prefix
        (transform_ID,
         transform_user_name,
         transform_user_name_prefix) = get_transform_info(
            '%s/odt/%s/%s' % (aces_CTL_directory, odt_dir, transform_CTL))

        # Find inverse
        transform_CTL_inverse = 'InvODT.%s.ctl' % odt_name
        if not os.path.exists(
                os.path.join(odt_tokens[-2], transform_CTL_inverse)):
            transform_CTL_inverse = None
        # print(transformCTLInverse)

        # Add to list of ODTs
        odts[odt_name] = {}
        odts[odt_name]['transformCTL'] = os.path.join(odt_dir, transform_CTL)
        if transform_CTL_inverse != None:
            odts[odt_name]['transformCTLInverse'] = os.path.join(
                odt_dir, transform_CTL_inverse)

        odts[odt_name]['transformID'] = transform_ID
        odts[odt_name]['transformUserNamePrefix'] = transform_user_name_prefix
        odts[odt_name]['transformUserName'] = transform_user_name

        print('ODT : %s' % odt_name)
        print('\tTransform ID               : %s' % transform_ID)
        print('\tTransform User Name Prefix : %s' % transform_user_name_prefix)
        print('\tTransform User Name        : %s' % transform_user_name)
        print('\tForward ctl                : %s' % (
            odts[odt_name]['transformCTL']))
        if 'transformCTLInverse' in odts[odt_name]:
            print('\tInverse ctl                : %s' % (
                odts[odt_name]['transformCTLInverse']))
        else:
            print('\tInverse ctl                : %s' % 'None')

    print('\n')

    return odts


def get_LMT_info(aces_CTL_directory):
    """
    Object description.

    For versions after WGR9.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate refactoring with previous definition.

    # Credit to Alex Fry for the original approach here
    lmt_dir = os.path.join(aces_CTL_directory, 'lmt')
    all_lmt = []
    for dir_name, subdir_list, file_list in os.walk(lmt_dir):
        for fname in file_list:
            all_lmt.append((os.path.join(dir_name, fname)))

    lmt_CTLs = [x for x in all_lmt if
                ('InvLMT' not in x) and ('README' not in x) and (
                    os.path.split(x)[-1][0] != '.')]

    # print lmtCTLs

    lmts = {}

    for lmt_CTL in lmt_CTLs:
        lmt_tokens = os.path.split(lmt_CTL)
        # print(lmtTokens)

        # Handle nested directories
        lmt_path_tokens = os.path.split(lmt_tokens[-2])
        lmt_dir = lmt_path_tokens[-1]
        while lmt_path_tokens[-2][-3:] != 'ctl':
            lmt_path_tokens = os.path.split(lmt_path_tokens[-2])
            lmt_dir = os.path.join(lmt_path_tokens[-1], lmt_dir)

        # Build full name
        # print('lmtDir : %s' % lmtDir)
        transform_CTL = lmt_tokens[-1]
        # print(transformCTL)
        lmt_name = string.join(transform_CTL.split('.')[1:-1], '.')
        # print(lmtName)

        # Find id, user name and user name prefix
        (transform_ID,
         transform_user_name,
         transform_user_name_prefix) = get_transform_info(
            '%s/%s/%s' % (aces_CTL_directory, lmt_dir, transform_CTL))

        # Find inverse
        transform_CTL_inverse = 'InvLMT.%s.ctl' % lmt_name
        if not os.path.exists(
                os.path.join(lmt_tokens[-2], transform_CTL_inverse)):
            transform_CTL_inverse = None
        # print(transformCTLInverse)

        # Add to list of LMTs
        lmts[lmt_name] = {}
        lmts[lmt_name]['transformCTL'] = os.path.join(lmt_dir, transform_CTL)
        if transform_CTL_inverse != None:
            # TODO: Check unresolved *odt_name* referemce.
            lmts[odt_name]['transformCTLInverse'] = os.path.join(
                lmt_dir, transform_CTL_inverse)

        lmts[lmt_name]['transformID'] = transform_ID
        lmts[lmt_name]['transformUserNamePrefix'] = transform_user_name_prefix
        lmts[lmt_name]['transformUserName'] = transform_user_name

        print('LMT : %s' % lmt_name)
        print('\tTransform ID               : %s' % transform_ID)
        print('\tTransform User Name Prefix : %s' % transform_user_name_prefix)
        print('\tTransform User Name        : %s' % transform_user_name)
        print('\t Forward ctl : %s' % lmts[lmt_name]['transformCTL'])
        if 'transformCTLInverse' in lmts[lmt_name]:
            print('\t Inverse ctl : %s' % (
                lmts[lmt_name]['transformCTLInverse']))
        else:
            print('\t Inverse ctl : %s' % 'None')

    print('\n')

    return lmts


def create_ACES_config(aces_CTL_directory,
                       config_directory,
                       lut_resolution_1d=4096,
                       lut_resolution_3d=64,
                       bake_secondary_LUTs=True,
                       cleanup=True):
    """
    Creates the ACES configuration.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # Get ODT names and CTL paths
    odt_info = get_ODT_info(aces_CTL_directory)

    # Get ODT names and CTL paths
    lmt_info = get_LMT_info(aces_CTL_directory)

    # Create config dir
    create_config_dir(config_directory, bake_secondary_LUTs)

    # Generate config data and LUTs for different transforms
    lut_directory = '%s/luts' % config_directory
    shaper_name = 'Output Shaper'
    config_data = generate_LUTs(odt_info,
                                lmt_info,
                                shaper_name,
                                aces_CTL_directory,
                                lut_directory,
                                lut_resolution_1d,
                                lut_resolution_3d,
                                cleanup)

    # Create the config using the generated LUTs
    print('Creating generic config')
    config = create_config(config_data)
    print('\n\n\n')

    # Write the config to disk
    write_config(config, '%s/config.ocio' % config_directory)

    # Create a config that will work well with Nuke using the previously
    # generated LUTs.
    print('Creating Nuke-specific config')
    nuke_config = create_config(config_data, nuke=True)
    print('\n\n\n')

    # Write the config to disk
    write_config(nuke_config, '%s/nuke_config.ocio' % config_directory)

    # Bake secondary LUTs using the config
    if bake_secondary_LUTs:
        generate_baked_LUTs(odt_info,
                            shaper_name,
                            '%s/baked' % config_directory,
                            '%s/config.ocio' % config_directory,
                            lut_resolution_1d,
                            lut_resolution_3d,
                            lut_resolution_1d)

    return True


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

    p = optparse.OptionParser(description='An OCIO config generation script',
                              prog='createACESConfig',
                              version='createACESConfig 0.1',
                              usage='%prog [options]')
    p.add_option('--acesCTLDir', '-a', default=os.environ.get(
        'ACES_OCIO_CTL_DIRECTORY', None))
    p.add_option('--configDir', '-c', default=os.environ.get(
        'ACES_OCIO_CONFIGURATION_DIRECTORY', None))
    p.add_option('--lutResolution1d', default=4096)
    p.add_option('--lutResolution3d', default=64)
    p.add_option('--dontBakeSecondaryLUTs', action='store_true')
    p.add_option('--keepTempImages', action='store_true')

    options, arguments = p.parse_args()

    #
    # Get options
    #
    aces_CTL_directory = options.acesCTLDir
    config_directory = options.configDir
    lut_resolution_1d = int(options.lutResolution1d)
    lut_resolution_3d = int(options.lutResolution3d)
    bake_secondary_LUTs = not (options.dontBakeSecondaryLUTs)
    cleanup_temp_images = not (options.keepTempImages)

    try:
        args_start = sys.argv.index('--') + 1
        args = sys.argv[args_start:]
    except:
        args_start = len(sys.argv) + 1
        args = []

    print('command line : \n%s\n' % ' '.join(sys.argv))

    # TODO: Use assertion and mention environment variables.
    if not aces_CTL_directory:
        print('process: No ACES CTL directory specified')
        return
    if not config_directory:
        print('process: No configuration directory specified')
        return
    #
    # Generate the configuration
    #
    return create_ACES_config(aces_CTL_directory,
                              config_directory,
                              lut_resolution_1d,
                              lut_resolution_3d,
                              bake_secondary_LUTs,
                              cleanup_temp_images)


if __name__ == '__main__':
    main()
