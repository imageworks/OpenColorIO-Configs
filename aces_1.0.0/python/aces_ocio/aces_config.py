#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines objects creating the *ACES* configuration.
"""

from __future__ import division

import copy
import os
import shutil
import sys

import PyOpenColorIO as ocio
from aces_ocio.colorspaces import aces
from aces_ocio.colorspaces import arri
from aces_ocio.colorspaces import canon
from aces_ocio.colorspaces import general
from aces_ocio.colorspaces import gopro
from aces_ocio.colorspaces import panasonic
from aces_ocio.colorspaces import red
from aces_ocio.colorspaces import sony
from aces_ocio.process import Process

from aces_ocio.utilities import (
    ColorSpace,
    colorspace_prefixed_name,
    compact,
    replace,
    unpack_default)

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
           'add_colorspace_alias',
           'create_config',
           'generate_LUTs',
           'generate_baked_LUTs',
           'create_config_dir',
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
                             texture_paint='',
                             rendering='',
                             compositing_linear=''):
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
    if texture_paint:
        config.setRole(ocio.Constants.ROLE_TEXTURE_PAINT, texture_paint)

    # 'rendering' and 'compositing_linear' roles default to the 'scene_linear'
    # value if not set explicitly
    if rendering:
        config.setRole('rendering', rendering)
    if compositing_linear:
        config.setRole('compositing_linear', compositing_linear)
    if scene_linear:
        config.setRole(ocio.Constants.ROLE_SCENE_LINEAR, scene_linear)
        if not rendering:
            config.setRole('rendering', scene_linear)
        if not compositing_linear:
            config.setRole('compositing_linear', scene_linear)

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

    with open(config_path, mode='w') as fp:
        fp.write(config.serialize())


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

    interpolation_options = {
        'linear': ocio.Constants.INTERP_LINEAR,
        'nearest': ocio.Constants.INTERP_NEAREST,
        'tetrahedral': ocio.Constants.INTERP_TETRAHEDRAL}

    direction_options = {
        'forward': ocio.Constants.TRANSFORM_DIR_FORWARD,
        'inverse': ocio.Constants.TRANSFORM_DIR_INVERSE}

    ocio_transforms = []

    for transform in transforms:

        # lutFile transform
        if transform['type'] == 'lutFile':
            # Create transforms
            ocio_transform = ocio.FileTransform()

            if 'path' in transform:
                ocio_transform.setSrc(transform['path'])

            if 'cccid' in transform:
                ocio_transform.setCCCId(transform['cccid'])

            if 'interpolation' in transform:
                ocio_transform.setInterpolation(transform['interpolation'])
            else:
                ocio_transform.setInterpolation(ocio.Constants.INTERP_BEST)

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # matrix transform
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

        # exponent transform
        elif transform['type'] == 'exponent':
            ocio_transform = ocio.ExponentTransform()

            if 'value' in transform:
                ocio_transform.setValue(transform['value'])

            ocio_transforms.append(ocio_transform)

        # log transform
        elif transform['type'] == 'log':
            ocio_transform = ocio.LogTransform()

            if 'base' in transform:
                ocio_transform.setBase(transform['base'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # color space transform
        elif transform['type'] == 'colorspace':
            ocio_transform = ocio.ColorSpaceTransform()

            if 'src' in transform:
                ocio_transform.setSrc(transform['src'])

            if 'dst' in transform:
                ocio_transform.setDst(transform['dst'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # look transform
        elif transform['type'] == 'look':
            ocio_transform = ocio.LookTransform()
            if 'look' in transform:
                ocio_transform.setLooks(transform['look'])

            if 'src' in transform:
                ocio_transform.setSrc(transform['src'])

            if 'dst' in transform:
                ocio_transform.setDst(transform['dst'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # unknown type
        else:
            print('Ignoring unknown transform type : %s' % transform['type'])

    if len(ocio_transforms) > 1:
        group_transform = ocio.GroupTransform()
        for transform in ocio_transforms:
            group_transform.push_back(transform)
        transform = group_transform
    else:
        transform = ocio_transforms[0]

    return transform


def add_colorspace_aliases(config,
                           reference_colorspace,
                           colorspace,
                           colorspace_alias_names,
                           family='Aliases'):
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

    for alias_name in colorspace_alias_names:
        if alias_name.lower() == colorspace.name.lower():
            print(
            'Skipping alias creation for %s, alias %s, because lower cased names match' % (
                colorspace.name, alias_name))
            continue

        print('Adding alias colorspace space %s, alias to %s' % (
            alias_name, colorspace.name))

        compact_family_name = family

        description = colorspace.description
        if colorspace.aces_transform_id:
            description += '\n\nACES Transform ID : %s' % colorspace.aces_transform_id

        ocio_colorspace_alias = ocio.ColorSpace(
            name=alias_name,
            bitDepth=colorspace.bit_depth,
            description=description,
            equalityGroup=colorspace.equality_group,
            family=compact_family_name,
            isData=colorspace.is_data,
            allocation=colorspace.allocation_type,
            allocationVars=colorspace.allocation_vars)

        if colorspace.to_reference_transforms:
            print('\tGenerating To-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                [{'type': 'colorspace',
                  'src': colorspace.name,
                  'dst': reference_colorspace.name,
                  'direction': 'forward'}])
            ocio_colorspace_alias.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_TO_REFERENCE)

        if colorspace.from_reference_transforms:
            print('\tGenerating From-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                [{'type': 'colorspace',
                  'src': reference_colorspace.name,
                  'dst': colorspace.name,
                  'direction': 'forward'}])
            ocio_colorspace_alias.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_FROM_REFERENCE)

        config.addColorSpace(ocio_colorspace_alias)


def add_look(config,
             look,
             prefix,
             custom_lut_dir,
             reference_name,
             config_data,
             multiple_displays=False):
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

    look_name, look_colorspace, look_lut, look_cccid = unpack_default(look, 4)

    print('Adding look %s - %s' % (look_name, ', '.join(look)))

    #
    # Copy look lut
    #
    if custom_lut_dir:
        if not '$' in look_lut:
            print('Getting ready to copy look lut : %s' % look_lut)
            shutil.copy2(look_lut, custom_lut_dir)
            look_lut = os.path.split(look_lut)[1]
        else:
            print('Skipping LUT copy because path contains a context variable')

    #
    # Create OCIO Look
    #
    # Look 1
    print('Adding look to config')
    lk1 = ocio.Look()
    lk1.setName(look_name)
    lk1.setProcessSpace(look_colorspace)

    keys = {'type': 'lutFile',
            'path': look_lut,
            'direction': 'forward'}
    if look_cccid:
        keys['cccid'] = look_cccid

    ocio_transform = generate_OCIO_transform([keys])
    lk1.setTransform(ocio_transform)

    # add to config
    config.addLook(lk1)

    print('Creating aliased colorspace')

    #
    # Create OCIO colorspace that references that look
    # - Needed for some implementations that don't process looks well
    # - Also needed for some implementations that don't expose looks well
    #
    look_aliases = ['look_%s' % compact(look_name)]
    colorspace = ColorSpace(look_name,
                            aliases=look_aliases,
                            description='The %s Look colorspace' % look_name,
                            family='Look')

    colorspace.from_reference_transforms = [{'type': 'look',
                                             'look': look_name,
                                             'src': reference_name,
                                             'dst': reference_name,
                                             'direction': 'forward'}]

    print('Adding colorspace %s, alias to look %s to config data' % (
        look_name, look_name))

    # Add this colorspace into the main list of colorspaces
    config_data['colorSpaces'].append(colorspace)

    print()


def integrate_looks_into_views(config,
                               looks,
                               reference_name,
                               config_data,
                               multiple_displays=False):
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
    look_names = [look[0] for look in looks]

    # Option 1 - Add a 'look' to each Display
    # - Assumes there is a Display for each ACES Output Transform
    if multiple_displays:
        for look_name in look_names:
            config_data['looks'].append(look_name)

    # Option 2
    # - Copy each Output Transform colorspace
    # - For each copy, add a LookTransform at the head of the from_reference
    #     transform list
    # - Add these new copied colorspaces for the Displays / Views 
    else:
        for display, view_list in config_data['displays'].iteritems():
            output_colorspace_copy = None
            look_names_string = ''
            for view_name, output_colorspace in view_list.iteritems():
                if view_name == 'Output Transform':

                    print('Adding new View that incorporates looks')

                    # Make a copy of the output colorspace
                    output_colorspace_copy = copy.deepcopy(output_colorspace)

                    # for look_name in look_names:
                    for i in range(len(look_names)):
                        look_name = look_names[i]

                        # Add the LookTransform to the head of the from_reference transform list
                        if output_colorspace_copy.from_reference_transforms:
                            output_colorspace_copy.from_reference_transforms.insert(
                                i, {'type': 'look',
                                    'look': look_name,
                                    'src': reference_name,
                                    'dst': reference_name,
                                    'direction': 'forward'})

                        # Add the LookTransform to the end of the to_reference transform list
                        if output_colorspace_copy.to_reference_transforms:
                            inverse_look_name = look_names[
                                len(look_names) - 1 - i]

                            output_colorspace_copy.to_reference_transforms.append(
                                {'type': 'look',
                                 'look': inverse_look_name,
                                 'src': reference_name,
                                 'dst': reference_name,
                                 'direction': 'inverse'})

                        if not look_name in config_data['looks']:
                            config_data['looks'].append(look_name)

                    look_names_string = ', '.join(look_names)
                    output_colorspace_copy.name = '%s with %s' % (
                    output_colorspace.name, look_names_string)
                    output_colorspace_copy.aliases = [
                        'out_%s' % compact(output_colorspace_copy.name)]

                    print(
                    'Colorspace that incorporates looks created : %s' % output_colorspace_copy.name)

                    config_data['colorSpaces'].append(output_colorspace_copy)

            if output_colorspace_copy:
                print(
                'Adding colorspace that incorporates looks into view list')

                # Change the name of the View
                view_list[
                    'Output Transform with %s' % look_names_string] = output_colorspace_copy
                config_data['displays'][display] = view_list

                # print( 'Display : %s, View List : %s' % (display, ', '.join(view_list)) )


def create_config(config_data,
                  aliases=False,
                  prefix=False,
                  multiple_displays=False,
                  look_info=None,
                  custom_lut_dir=None):
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

    if look_info is None:
        look_info = []

    prefixed_names = {}
    alias_colorspaces = []

    # Creating the *OCIO* configuration.
    config = ocio.Config()

    # Setting configuration description.
    config.setDescription('An ACES config generated from python')

    # Setting configuration search path.
    searchPath = ['luts']
    if custom_lut_dir:
        searchPath.append('custom')
    config.setSearchPath(':'.join(searchPath))

    # Defining the reference colorspace.
    reference_data = config_data['referenceColorSpace']

    # Adding the color space Family into the name
    # Helps with applications that present colorspaces as one long list
    if prefix:
        prefixed_name = colorspace_prefixed_name(reference_data)
        prefixed_names[reference_data.name] = prefixed_name
        reference_data.name = prefixed_name

    print('Adding the reference color space : %s' % reference_data.name)

    reference = ocio.ColorSpace(
        name=reference_data.name,
        bitDepth=reference_data.bit_depth,
        description=reference_data.description,
        equalityGroup=reference_data.equality_group,
        family=reference_data.family,
        isData=reference_data.is_data,
        allocation=reference_data.allocation_type,
        allocationVars=reference_data.allocation_vars)

    config.addColorSpace(reference)

    # Add alias
    if aliases:
        if reference_data.aliases:
            # add_colorspace_alias(config, reference_data,
            #                     reference_data, reference_data.aliases)
            # defer adding alias colorspaces until end. Helps with some applications
            alias_colorspaces.append(
                [reference_data, reference_data, reference_data.aliases])

    print()

    # print( 'color spaces : %s' % [x.name for x in sorted(config_data['colorSpaces'])])

    #
    # Add Looks and Look colorspaces
    #
    if look_info:
        print('Adding looks')

        config_data['looks'] = []

        # Add looks and colorspaces
        for look in look_info:
            add_look(config,
                     look,
                     prefix,
                     custom_lut_dir,
                     reference_data.name,
                     config_data)

        # Integrate looks with displays, views
        integrate_looks_into_views(config,
                                   look_info,
                                   reference_data.name,
                                   config_data,
                                   multiple_displays)

        print()

    print('Adding the regular color spaces')

    # Creating the remaining colorspaces.
    for colorspace in sorted(config_data['colorSpaces']):
        # Adding the color space Family into the name
        # Helps with applications that present colorspaces as one long list
        if prefix:
            prefixed_name = colorspace_prefixed_name(colorspace)
            prefixed_names[colorspace.name] = prefixed_name
            colorspace.name = prefixed_name

        print('Creating new color space : %s' % colorspace.name)

        description = colorspace.description
        if colorspace.aces_transform_id:
            description += '\n\nACES Transform ID : %s' % colorspace.aces_transform_id

        ocio_colorspace = ocio.ColorSpace(
            name=colorspace.name,
            bitDepth=colorspace.bit_depth,
            description=description,
            equalityGroup=colorspace.equality_group,
            family=colorspace.family,
            isData=colorspace.is_data,
            allocation=colorspace.allocation_type,
            allocationVars=colorspace.allocation_vars)

        if colorspace.to_reference_transforms:
            print('\tGenerating To-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                colorspace.to_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_TO_REFERENCE)

        if colorspace.from_reference_transforms:
            print('\tGenerating From-Reference transforms')
            ocio_transform = generate_OCIO_transform(
                colorspace.from_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_FROM_REFERENCE)

        config.addColorSpace(ocio_colorspace)

        #
        # Add alias to normal colorspace, using compact name
        #
        if aliases:
            if colorspace.aliases:
                # add_colorspace_alias(config, reference_data,
                #                     colorspace, colorspace.aliases)
                # defer adding alias colorspaces until end. Helps with some applications
                alias_colorspaces.append(
                    [reference_data, colorspace, colorspace.aliases])

        print()

    print()

    #
    # We add roles early so we can create alias colorspaces with the names of the roles
    # before the rest of the colorspace aliases are added to the config.
    #
    print('Setting the roles')

    if prefix:
        set_config_default_roles(
            config,
            color_picking=prefixed_names[
                config_data['roles']['color_picking']],
            color_timing=prefixed_names[config_data['roles']['color_timing']],
            compositing_log=prefixed_names[
                config_data['roles']['compositing_log']],
            data=prefixed_names[config_data['roles']['data']],
            default=prefixed_names[config_data['roles']['default']],
            matte_paint=prefixed_names[config_data['roles']['matte_paint']],
            reference=prefixed_names[config_data['roles']['reference']],
            scene_linear=prefixed_names[config_data['roles']['scene_linear']],
            texture_paint=prefixed_names[
                config_data['roles']['texture_paint']])

        # Not allowed for the moment. role names can not overlap with colorspace names.
        """
        # Add the aliased colorspaces for each role
        for role_name, role_colorspace_name in config_data['roles'].iteritems():
            role_colorspace_prefixed_name = prefixed_names[role_colorspace_name]

            print( 'Finding colorspace : %s' % role_colorspace_prefixed_name )
            # Find the colorspace pointed to by the role
            role_colorspaces = [colorspace for colorspace in config_data['colorSpaces'] if colorspace.name == role_colorspace_prefixed_name]
            role_colorspace = None
            if len(role_colorspaces) > 0:
                role_colorspace = role_colorspaces[0]
            else:
                if reference_data.name == role_colorspace_prefixed_name:
                    role_colorspace = reference_data

            if role_colorspace:
                print( 'Adding an alias colorspace named %s, pointing to %s' % (
                    role_name, role_colorspace.name))

                add_colorspace_aliases(config, reference_data, role_colorspace, [role_name], 'Roles')
        """

    else:
        set_config_default_roles(
            config,
            color_picking=config_data['roles']['color_picking'],
            color_timing=config_data['roles']['color_timing'],
            compositing_log=config_data['roles']['compositing_log'],
            data=config_data['roles']['data'],
            default=config_data['roles']['default'],
            matte_paint=config_data['roles']['matte_paint'],
            reference=config_data['roles']['reference'],
            scene_linear=config_data['roles']['scene_linear'],
            texture_paint=config_data['roles']['texture_paint'])

        # Not allowed for the moment. role names can not overlap with colorspace names.
        """
        # Add the aliased colorspaces for each role
        for role_name, role_colorspace_name in config_data['roles'].iteritems():
            # Find the colorspace pointed to by the role
            role_colorspaces = [colorspace for colorspace in config_data['colorSpaces'] if colorspace.name == role_colorspace_name]
            role_colorspace = None
            if len(role_colorspaces) > 0:
                role_colorspace = role_colorspaces[0]
            else:
                if reference_data.name == role_colorspace_name:
                    role_colorspace = reference_data

            if role_colorspace:
                print( 'Adding an alias colorspace named %s, pointing to %s' % (
                    role_name, role_colorspace.name))

                add_colorspace_aliases(config, reference_data, role_colorspace, [role_name], 'Roles')
        """

    print()

    # We add these at the end as some applications use the order of the colorspaces
    # definitions in the config to order the colorspaces in their selection lists.
    # Other go alphabetically. This should keep the alias colorspaces out of the way
    # for the apps that use the order of definition in the config.
    print('Adding the alias colorspaces')
    for reference, colorspace, aliases in alias_colorspaces:
        add_colorspace_aliases(config, reference, colorspace, aliases)

    print()

    print('Adding the diplays and views')

    # Set the color_picking role to be the first Display's Output Transform View
    default_display_name = config_data['defaultDisplay']
    default_display_views = config_data['displays'][default_display_name]
    default_display_colorspace = default_display_views['Output Transform']

    set_config_default_roles(
        config,
        color_picking=default_display_colorspace.name)

    # Defining the *views* and *displays*.
    displays = []
    views = []

    # Defining a *generic* *display* and *view* setup.
    if multiple_displays:
        # Built list of looks to add to Displays
        looks = config_data['looks'] if ('looks' in config_data) else []
        looks = ', '.join(looks)
        print('Creating multiple displays, with looks : %s' % looks)

        # Note: We don't reorder the Displays to put the 'defaultDisplay' first
        # because OCIO will order them alphabetically when the config is written to disk.

        # Create Displays, Views
        for display, view_list in config_data['displays'].iteritems():
            for view_name, colorspace in view_list.iteritems():
                config.addDisplay(display, view_name, colorspace.name, looks)
                if 'Output Transform' in view_name and looks != '':
                    # Add normal View, without looks
                    config.addDisplay(display, view_name, colorspace.name)

                    # Add View with looks
                    view_name_with_looks = '%s with %s' % (view_name, looks)
                    config.addDisplay(display, view_name_with_looks,
                                      colorspace.name, looks)
                else:
                    config.addDisplay(display, view_name, colorspace.name)
                if not (view_name in views):
                    views.append(view_name)
            displays.append(display)

    # Defining the set of *views* and *displays* useful in a *GUI* context.
    else:
        single_display_name = 'ACES'
        # single_display_name = config_data['roles']['scene_linear']
        displays.append(single_display_name)

        # Make sure the default display is first
        display_names = sorted(config_data['displays'])
        display_names.insert(0, display_names.pop(
            display_names.index(default_display_name)))

        # Built list of looks to add to Displays
        looks = config_data['looks'] if ('looks' in config_data) else []
        look_names = ', '.join(looks)

        displays_views_colorspaces = []

        # Create Displays, Views
        for display in display_names:
            view_list = config_data['displays'][display]
            for view_name, colorspace in view_list.iteritems():
                if 'Output Transform' in view_name:
                    # print( 'Adding view for %s' % colorspace.name )

                    # We use the Display names as the View names in this case
                    # as there is a single Display that contains all views.
                    # This works for more applications than not, as of the time of this implementation.

                    # Maya 2016 doesn't like parentheses in View names
                    display_cleaned = replace(display, {')': '', '(': ''})

                    # If View includes looks
                    if 'with' in view_name:
                        # Integrate looks into view name
                        display_cleaned = '%s with %s' % (
                        display_cleaned, look_names)

                        viewsWithLooksAtEnd = False
                        # Storing combo of display, view and colorspace name in a list so we can
                        # add them to the end of the list
                        if viewsWithLooksAtEnd:
                            displays_views_colorspaces.append(
                                [single_display_name, display_cleaned,
                                 colorspace.name])

                        # Or add as normal
                        else:
                            config.addDisplay(single_display_name,
                                              display_cleaned, colorspace.name)

                            # Add to views list
                            if not (display_cleaned in views):
                                views.append(display_cleaned)

                    # A normal View
                    else:
                        config.addDisplay(single_display_name, display_cleaned,
                                          colorspace.name)

                        # Add to views list
                        if not (display_cleaned in views):
                            views.append(display_cleaned)

        # Add to config any display, view combinations that were saved for later
        # This list will be empty unless viewsWithLooksAtEnd is set to True above 
        for display_view_colorspace in displays_views_colorspaces:
            single_display_name, display_cleaned, colorspace_name = display_view_colorspace

            # Add to config
            config.addDisplay(single_display_name, display_cleaned,
                              colorspace_name)

            # Add to views list
            if not (display_cleaned in views):
                views.append(display_cleaned)


        # Works with Nuke Studio and Mari, but not Nuke
        # single_display_name = 'Utility'
        # displays.append(single_display_name)

        raw_display_space_name = config_data['roles']['data']
        log_display_space_name = config_data['roles']['compositing_log']

        # Find the newly-prefixed colorspace names
        if prefix:
            # print( prefixed_names )
            raw_display_space_name = prefixed_names[raw_display_space_name]
            log_display_space_name = prefixed_names[log_display_space_name]

        config.addDisplay(single_display_name, 'Raw', raw_display_space_name)
        views.append('Raw')
        config.addDisplay(single_display_name, 'Log', log_display_space_name)
        views.append('Log')

    # Setting the active *displays* and *views*.
    config.setActiveDisplays(','.join(sorted(displays)))
    config.setActiveViews(','.join(views))

    print()

    # Make sure we didn't create a bad config
    config.sanityCheck()

    # Reset the colorspace names back to their non-prefixed versions
    if prefix:
        # Build the reverse lookup
        prefixed_names_inverse = {}
        for original, prefixed in prefixed_names.iteritems():
            prefixed_names_inverse[prefixed] = original

        # Reset the reference colorspace name
        reference_data.name = prefixed_names_inverse[reference_data.name]

        # Reset the rest of the colorspace names
        try:
            for colorspace in config_data['colorSpaces']:
                colorspace.name = prefixed_names_inverse[colorspace.name]
        except:
            print('Prefixed names')
            for original, prefixed in prefixed_names.iteritems():
                print('%s, %s' % (original, prefixed))

            print('\n')

            print('Inverse Lookup of Prefixed names')
            for prefixed, original in prefixed_names_inverse.iteritems():
                print('%s, %s' % (prefixed, original))
            raise

    return config


def generate_LUTs(odt_info,
                  lmt_info,
                  shaper_name,
                  aces_ctl_directory,
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

    # Initialize a few variables
    config_data['displays'] = {}
    config_data['colorSpaces'] = []

    # -------------------------------------------------------------------------
    # *ACES Color Spaces*
    # -------------------------------------------------------------------------

    # *ACES* colorspaces
    (aces_reference,
     aces_colorspaces,
     aces_displays,
     aces_log_display_space,
     aces_roles,
     aces_default_display) = aces.create_colorspaces(aces_ctl_directory,
                                                     lut_directory,
                                                     lut_resolution_1d,
                                                     lut_resolution_3d,
                                                     lmt_info,
                                                     odt_info,
                                                     shaper_name,
                                                     cleanup)

    config_data['referenceColorSpace'] = aces_reference
    config_data['roles'] = aces_roles

    for cs in aces_colorspaces:
        config_data['colorSpaces'].append(cs)

    for name, data in aces_displays.iteritems():
        config_data['displays'][name] = data

    config_data['defaultDisplay'] = aces_default_display
    config_data['linearDisplaySpace'] = aces_reference
    config_data['logDisplaySpace'] = aces_log_display_space

    # -------------------------------------------------------------------------
    # *Camera Input Transforms*
    # -------------------------------------------------------------------------

    # *ARRI Log-C* to *ACES*.
    arri_colorSpaces = arri.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in arri_colorSpaces:
        config_data['colorSpaces'].append(cs)

    # *Canon-Log* to *ACES*.
    canon_colorspaces = canon.create_colorspaces(lut_directory,
                                                 lut_resolution_1d)
    for cs in canon_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *GoPro Protune* to *ACES*.
    gopro_colorspaces = gopro.create_colorspaces(lut_directory,
                                                 lut_resolution_1d)
    for cs in gopro_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *Panasonic V-Log* to *ACES*.
    panasonic_colorSpaces = panasonic.create_colorspaces(lut_directory,
                                                         lut_resolution_1d)
    for cs in panasonic_colorSpaces:
        config_data['colorSpaces'].append(cs)

    # *RED* colorspaces to *ACES*.
    red_colorspaces = red.create_colorspaces(lut_directory,
                                             lut_resolution_1d)
    for cs in red_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *S-Log* to *ACES*.
    sony_colorSpaces = sony.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in sony_colorSpaces:
        config_data['colorSpaces'].append(cs)

    # -------------------------------------------------------------------------
    # General Color Spaces
    # -------------------------------------------------------------------------
    general_colorSpaces = general.create_colorspaces(lut_directory,
                                                     lut_resolution_1d,
                                                     lut_resolution_3d)
    for cs in general_colorSpaces:
        config_data['colorSpaces'].append(cs)

    # The *Raw* color space
    raw = general.create_raw()
    config_data['colorSpaces'].append(raw)

    # Override certain roles, for now
    config_data['roles']['data'] = raw.name
    config_data['roles']['reference'] = raw.name
    config_data['roles']['texture_paint'] = raw.name

    print('generateLUTs - end')
    return config_data


def generate_baked_LUTs(odt_info,
                        shaper_name,
                        baked_directory,
                        config_path,
                        lut_resolution_1d,
                        lut_resolution_3d,
                        lut_resolution_shaper=1024,
                        prefix=False):
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

    odt_info_C = dict(odt_info)

    # Uncomment if you would like to support the older behavior where ODTs
    # that have support for full and legal range output generate a LUT for each.
    """
    # Create two entries for ODTs that have full and legal range support
    for odt_ctl_name, odt_values in odt_info.iteritems():
        if odt_values['transformHasFullLegalSwitch']:
            odt_name = odt_values['transformUserName']

            odt_values_legal = dict(odt_values)
            odt_values_legal['transformUserName'] = '%s - Legal' % odt_name
            odt_info_C['%s - Legal' % odt_ctl_name] = odt_values_legal

            odt_values_full = dict(odt_values)
            odt_values_full['transformUserName'] = '%s - Full' % odt_name
            odt_info_C['%s - Full' % odt_ctl_name] = odt_values_full

            del (odt_info_C[odt_ctl_name])
    """

    # Generate appropriate LUTs for each ODT
    for odt_ctl_name, odt_values in odt_info_C.iteritems():
        odt_prefix = odt_values['transformUserNamePrefix']
        odt_name = odt_values['transformUserName']

        # *Photoshop*
        for input_space in ['ACEScc', 'ACESproxy']:
            args = ['--iconfig', config_path,
                    '-v']
            if prefix:
                args += ['--inputspace', 'ACES - %s' % input_space]
                args += ['--outputspace', 'Output - %s' % odt_name]
            else:
                args += ['--inputspace', input_space]
                args += ['--outputspace', odt_name]

            args += ['--description',
                     '%s - %s for %s data' % (odt_prefix,
                                              odt_name,
                                              input_space)]
            if prefix:
                args += ['--shaperspace', 'Utility - %s' % shaper_name,
                         '--shapersize', str(lut_resolution_shaper)]
            else:
                args += ['--shaperspace', shaper_name,
                         '--shapersize', str(lut_resolution_shaper)]
            args += ['--cubesize', str(lut_resolution_3d)]
            args += ['--format',
                     'icc',
                     os.path.join(baked_directory,
                                  'photoshop',
                                  '%s for %s.icc' % (odt_name, input_space))]

            bake_lut = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=args)
            bake_lut.execute()

        # *Flame*, *Lustre*
        for input_space in ['ACEScc', 'ACESproxy']:
            args = ['--iconfig', config_path,
                    '-v']
            if prefix:
                args += ['--inputspace', 'ACES - %s' % input_space]
                args += ['--outputspace', 'Output - %s' % odt_name]
            else:
                args += ['--inputspace', input_space]
                args += ['--outputspace', odt_name]
            args += ['--description',
                     '%s - %s for %s data' % (
                         odt_prefix, odt_name, input_space)]
            if prefix:
                args += ['--shaperspace', 'Utility - %s' % shaper_name,
                         '--shapersize', str(lut_resolution_shaper)]
            else:
                args += ['--shaperspace', shaper_name,
                         '--shapersize', str(lut_resolution_shaper)]
            args += ['--cubesize', str(lut_resolution_3d)]

            fargs = ['--format',
                     'flame',
                     os.path.join(
                         baked_directory,
                         'flame',
                         '%s for %s Flame.3dl' % (odt_name, input_space))]
            bake_lut = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + fargs))
            bake_lut.execute()

            largs = ['--format',
                     'lustre',
                     os.path.join(
                         baked_directory,
                         'lustre',
                         '%s for %s Lustre.3dl' % (odt_name, input_space))]
            bake_lut = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + largs))
            bake_lut.execute()

        # *Maya*, *Houdini*
        for input_space in ['ACEScg', 'ACES2065-1']:
            args = ['--iconfig', config_path,
                    '-v']
            if prefix:
                args += ['--inputspace', 'ACES - %s' % input_space]
                args += ['--outputspace', 'Output - %s' % odt_name]
            else:
                args += ['--inputspace', input_space]
                args += ['--outputspace', odt_name]
            args += ['--description',
                     '%s - %s for %s data' % (
                         odt_prefix, odt_name, input_space)]
            if input_space == 'ACEScg':
                lin_shaper_name = '%s - AP1' % shaper_name
            else:
                lin_shaper_name = shaper_name
            if prefix:
                lin_shaper_name = 'Utility - %s' % lin_shaper_name
            args += ['--shaperspace', lin_shaper_name,
                     '--shapersize', str(lut_resolution_shaper)]

            args += ['--cubesize', str(lut_resolution_3d)]

            margs = ['--format',
                     'cinespace',
                     os.path.join(
                         baked_directory,
                         'maya',
                         '%s for %s Maya.csp' % (odt_name, input_space))]
            bake_lut = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + margs))
            bake_lut.execute()

            hargs = ['--format',
                     'houdini',
                     os.path.join(
                         baked_directory,
                         'houdini',
                         '%s for %s Houdini.lut' % (odt_name, input_space))]
            bake_lut = Process(description='bake a LUT',
                               cmd='ociobakelut',
                               args=(args + hargs))
            bake_lut.execute()


def create_config_dir(config_directory,
                      bake_secondary_LUTs=False,
                      custom_lut_dir=None):
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

    lut_directory = os.path.join(config_directory, 'luts')
    dirs = [config_directory, lut_directory]

    if bake_secondary_LUTs:
        dirs.extend([os.path.join(config_directory, 'baked'),
                     os.path.join(config_directory, 'baked', 'flame'),
                     os.path.join(config_directory, 'baked', 'photoshop'),
                     os.path.join(config_directory, 'baked', 'houdini'),
                     os.path.join(config_directory, 'baked', 'lustre'),
                     os.path.join(config_directory, 'baked', 'maya')])

    if custom_lut_dir:
        dirs.append(os.path.join(config_directory, 'custom'))

    for d in dirs:
        not os.path.exists(d) and os.mkdir(d)

    return lut_directory


def create_ACES_config(aces_ctl_directory,
                       config_directory,
                       lut_resolution_1d=4096,
                       lut_resolution_3d=64,
                       bake_secondary_LUTs=True,
                       multiple_displays=False,
                       look_info=None,
                       copy_custom_luts=True,
                       cleanup=True,
                       prefix_colorspaces_with_family_names=True):
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

    if look_info is None:
        look_info = []

    # Directory for custom LUTs
    custom_lut_dir = None
    if copy_custom_luts:
        custom_lut_dir = os.path.join(config_directory, 'custom')

    lut_directory = create_config_dir(config_directory,
                                      bake_secondary_LUTs,
                                      custom_lut_dir)

    odt_info = aces.get_ODTs_info(aces_ctl_directory)
    lmt_info = aces.get_LMTs_info(aces_ctl_directory)

    shaper_name = 'Output Shaper'
    config_data = generate_LUTs(odt_info,
                                lmt_info,
                                shaper_name,
                                aces_ctl_directory,
                                lut_directory,
                                lut_resolution_1d,
                                lut_resolution_3d,
                                cleanup)

    print('Creating config - with prefixes, with aliases')
    config = create_config(config_data,
                           prefix=prefix_colorspaces_with_family_names,
                           aliases=True,
                           multiple_displays=multiple_displays,
                           look_info=look_info,
                           custom_lut_dir=custom_lut_dir)
    print('\n\n\n')

    write_config(config,
                 os.path.join(config_directory, 'config.ocio'))

    if bake_secondary_LUTs:
        generate_baked_LUTs(odt_info,
                            shaper_name,
                            os.path.join(config_directory, 'baked'),
                            os.path.join(config_directory, 'config.ocio'),
                            lut_resolution_1d,
                            lut_resolution_3d,
                            lut_resolution_1d,
                            prefix=prefix_colorspaces_with_family_names)

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

    usage = '%prog [options]\n'
    usage += '\n'
    usage += 'An OCIO config generation script for ACES 1.0\n'
    usage += '\n'
    usage += 'Command line examples'
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0 config with no secondary, baked LUTs : \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 --dontBakeSecondaryLUTs'
    usage += '\n'
    usage += 'Create a more OCIO-compliant ACES 1.0 config : \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 --createMultipleDisplays'
    usage += '\n'
    usage += '\n'
    usage += 'Adding custom looks'
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0 config with an ACES-style CDL (will be applied in the ACEScc colorspace): \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 \n\t\t--addACESLookCDL ACESCDLName /path/to/SampleCDL.ccc cc03345'
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0 config with an general CDL: \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 \n\t\t--addCustomLookCDL CustomCDLName "ACES - ACEScc" /path/to/SampleCDL.ccc cc03345'
    usage += '\n'
    usage += '\tIn this example, the CDL will be applied in the ACEScc colorspace, but the user could choose other spaces by changing the argument after the name of the look. \n'
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0 config with an ACES-style LUT (will be applied in the ACEScc colorspace): \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 \n\t\t--addACESLookLUT ACESLUTName /path/to/SampleCDL.ccc cc03345'
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0 config with an general LUT: \n'
    usage += '\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl --lutResolution1d 1024 --lutResolution3d 33 -c aces_1.0.0 \n\t\t--addCustomLookLUT CustomLUTName "ACES - ACEScc" /path/to/SampleCDL.ccc cc03345'
    usage += '\n'
    usage += '\tIn this example, the LUT will be applied in the ACEScc colorspace, but the user could choose other spaces by changing the argument after the name of the look. \n'
    usage += '\n'

    look_info = []

    def look_info_callback(option, opt_str, value, parser):
        print('look_info_callback')
        print(option, opt_str, value, parser)
        if opt_str == '--addCustomLookCDL':
            look_info.append(value)
        elif opt_str == '--addCustomLookLUT':
            look_info.append(value)
        elif opt_str == '--addACESLookCDL':
            look_info.append([value[0], 'ACES - ACEScc', value[1], value[2]])
        elif opt_str == '--addACESLookLUT':
            look_info.append([value[0], 'ACES - ACEScc', value[1]])

    p = optparse.OptionParser(description='',
                              prog='create_aces_config',
                              version='create_aces_config 1.0',
                              usage=usage)
    p.add_option('--acesCTLDir', '-a', default=os.environ.get(
        ACES_OCIO_CTL_DIRECTORY_ENVIRON, None))
    p.add_option('--configDir', '-c', default=os.environ.get(
        ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON, None))
    p.add_option('--lutResolution1d', default=4096)
    p.add_option('--lutResolution3d', default=64)
    p.add_option('--dontBakeSecondaryLUTs', action='store_true', default=False)
    p.add_option('--keepTempImages', action='store_true', default=False)

    p.add_option('--createMultipleDisplays', action='store_true',
                 default=False)

    p.add_option('--addCustomLookLUT', '', type='string', nargs=3,
                 action='callback', callback=look_info_callback)
    p.add_option('--addCustomLookCDL', '', type='string', nargs=4,
                 action='callback', callback=look_info_callback)
    p.add_option('--addACESLookLUT', '', type='string', nargs=2,
                 action='callback', callback=look_info_callback)
    p.add_option('--addACESLookCDL', '', type='string', nargs=3,
                 action='callback', callback=look_info_callback)
    p.add_option('--copyCustomLUTs', action='store_true', default=False)

    options, arguments = p.parse_args()

    aces_ctl_directory = options.acesCTLDir
    config_directory = options.configDir
    lut_resolution_1d = int(options.lutResolution1d)
    lut_resolution_3d = int(options.lutResolution3d)
    bake_secondary_luts = not options.dontBakeSecondaryLUTs
    cleanup_temp_images = not options.keepTempImages
    multiple_displays = options.createMultipleDisplays
    copy_custom_luts = options.copyCustomLUTs

    print(look_info)

    print('command line : \n%s\n' % ' '.join(sys.argv))

    assert aces_ctl_directory is not None, (
        'process: No "{0}" environment variable defined or no "ACES CTL" '
        'directory specified'.format(
            ACES_OCIO_CTL_DIRECTORY_ENVIRON))

    assert config_directory is not None, (
        'process: No "{0}" environment variable defined or no configuration '
        'directory specified'.format(
            ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON))

    return create_ACES_config(aces_ctl_directory,
                              config_directory,
                              lut_resolution_1d,
                              lut_resolution_3d,
                              bake_secondary_luts,
                              multiple_displays,
                              look_info,
                              copy_custom_luts,
                              cleanup_temp_images)


if __name__ == '__main__':
    main()
