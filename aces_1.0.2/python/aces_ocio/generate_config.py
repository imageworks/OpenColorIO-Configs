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
           'set_config_roles',
           'create_ocio_transform',
           'add_colorspace_aliases',
           'add_look',
           'add_looks_to_views',
           'create_config',
           'create_config_data',
           'write_config',
           'generate_baked_LUTs',
           'generate_config_directory',
           'generate_config',
           'main']

ACES_OCIO_CTL_DIRECTORY_ENVIRON = 'ACES_OCIO_CTL_DIRECTORY'
ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON = 'ACES_OCIO_CONFIGURATION_DIRECTORY'


def set_config_roles(config,
                     color_picking=None,
                     color_timing=None,
                     compositing_log=None,
                     data=None,
                     default=None,
                     matte_paint=None,
                     reference=None,
                     scene_linear=None,
                     texture_paint=None,
                     rendering=None,
                     compositing_linear=None):
    """
    Sets given *OCIO* configuration roles to the config.
    Parameters
    ----------
    config : Config
        *OCIO* configuration.
    color_picking : str or unicode, optional
        Color Picking role title.
    color_timing : str or unicode, optional
        Color Timing role title.
    compositing_log : str or unicode, optional
        Compositing Log role title.
    data : str or unicode, optional
        Data role title.
    default : str or unicode, optional
        Default role title.
    matte_paint : str or unicode, optional
        Matte Painting role title.
    reference : str or unicode, optional
        Reference role title.
    scene_linear : str or unicode, optional
        Scene Linear role title.
    texture_paint : str or unicode, optional
        Texture Painting role title.
    rendering : str or unicode, optional
        Rendering role title.
    compositing_linear : str or unicode, optional
        Compositing Linear role title.
    Returns
    -------
    bool
         Definition success.
    """

    if color_picking is not None:
        config.setRole(ocio.Constants.ROLE_COLOR_PICKING, color_picking)
    if color_timing is not None:
        config.setRole(ocio.Constants.ROLE_COLOR_TIMING, color_timing)
    if compositing_log is not None:
        config.setRole(ocio.Constants.ROLE_COMPOSITING_LOG, compositing_log)
    if data is not None:
        config.setRole(ocio.Constants.ROLE_DATA, data)
    if default is not None:
        config.setRole(ocio.Constants.ROLE_DEFAULT, default)
    if matte_paint is not None:
        config.setRole(ocio.Constants.ROLE_MATTE_PAINT, matte_paint)
    if reference is not None:
        config.setRole(ocio.Constants.ROLE_REFERENCE, reference)
    if texture_paint is not None:
        config.setRole(ocio.Constants.ROLE_TEXTURE_PAINT, texture_paint)

    # *rendering* and *compositing_linear* roles default to the *scene_linear*
    # value if not set explicitly.
    if rendering is not None:
        config.setRole('rendering', rendering)
    if compositing_linear is not None:
        config.setRole('compositing_linear', compositing_linear)
    if scene_linear is not None:
        config.setRole(ocio.Constants.ROLE_SCENE_LINEAR, scene_linear)
        if rendering is None:
            config.setRole('rendering', scene_linear)
        if compositing_linear is None:
            config.setRole('compositing_linear', scene_linear)

    return True


def create_ocio_transform(transforms):
    """
    Returns an *OCIO* transform from given array of transform descriptions.

    Parameters
    ----------
    transforms : array_like
        Transform descriptions as an array_like of dicts:
        {'type', 'src', 'dst', 'direction'}

    Returns
    -------
    Transform
         *OCIO* transform.
    """

    direction_options = {
        'forward': ocio.Constants.TRANSFORM_DIR_FORWARD,
        'inverse': ocio.Constants.TRANSFORM_DIR_INVERSE}

    ocio_transforms = []

    for transform in transforms:

        # *lutFile* transform
        if transform['type'] == 'lutFile':
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

        # *matrix* transform
        elif transform['type'] == 'matrix':
            ocio_transform = ocio.MatrixTransform()
            # `MatrixTransform` member variables can't be initialized directly,
            # each must be set individually.
            ocio_transform.setMatrix(transform['matrix'])

            if 'offset' in transform:
                ocio_transform.setOffset(transform['offset'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # *exponent* transform
        elif transform['type'] == 'exponent':
            ocio_transform = ocio.ExponentTransform()

            if 'value' in transform:
                ocio_transform.setValue(transform['value'])

            ocio_transforms.append(ocio_transform)

        # *log* transform
        elif transform['type'] == 'log':
            ocio_transform = ocio.LogTransform()

            if 'base' in transform:
                ocio_transform.setBase(transform['base'])

            if 'direction' in transform:
                ocio_transform.setDirection(
                    direction_options[transform['direction']])

            ocio_transforms.append(ocio_transform)

        # *colorspace* transform
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

        # *look* transform
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

        # *unknown* type
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
    Adds given colorspace aliases to the *OCIO* config.

    Parameters
    ----------
    config : Config
        *OCIO* configuration.
    reference_colorspace : Colorspace
        Reference colorspace.
    colorspace : Colorspace
        Colorspace to set the aliases into the *OCIO* config.
    family : unicode
        Family.

    Returns
    -------
    bool
        Definition success.
    """

    for alias_name in colorspace_alias_names:
        if alias_name.lower() == colorspace.name.lower():
            print('Skipping alias creation for %s, alias %s, '
                  'because lower cased names match' % (
                      colorspace.name, alias_name))
            continue

        print('Adding alias colorspace space %s, alias to %s' % (
            alias_name, colorspace.name))

        compact_family_name = family

        description = colorspace.description
        if colorspace.aces_transform_id:
            description += (
                '\n\nACES Transform ID : %s' % colorspace.aces_transform_id)

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
            ocio_transform = create_ocio_transform(
                [{'type': 'colorspace',
                  'src': colorspace.name,
                  'dst': reference_colorspace.name,
                  'direction': 'forward'}])
            ocio_colorspace_alias.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_TO_REFERENCE)

        if colorspace.from_reference_transforms:
            print('\tGenerating From-Reference transforms')
            ocio_transform = create_ocio_transform(
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
             custom_lut_dir,
             reference_name,
             config_data):
    """
    Adds given look to the *OCIO* config.

    Parameters
    ----------
    config : Config
        *OCIO* configuration.
    look : array_like
        Look description: {'name', 'colorspace', 'lut', 'cccid'}
    custom_lut_dir : str or unicode
        Directory to copy the look lut into.
    reference_name : str or unicode
        Reference name.
    config_data : dict
        Colorspaces and transforms converting between those colorspaces and
        the reference colorspace, *ACES*.

    Returns
    -------
    bool
        Definition success.
    """

    look_name, look_colorspace, look_lut, look_cccid = unpack_default(look, 4)

    print('Adding look %s - %s' % (look_name, ', '.join(look)))

    # Copy *look LUT* if `custom_lut_dir` is provided.
    if custom_lut_dir:
        if '$' not in look_lut:
            print('Getting ready to copy look lut : %s' % look_lut)
            shutil.copy2(look_lut, custom_lut_dir)
            look_lut = os.path.split(look_lut)[1]
        else:
            print('Skipping LUT copy because path contains a context variable')

    print('Adding look to config')
    ocio_look = ocio.Look()
    ocio_look.setName(look_name)
    ocio_look.setProcessSpace(look_colorspace)

    keys = {'type': 'lutFile',
            'path': look_lut,
            'direction': 'forward'}
    if look_cccid:
        keys['cccid'] = look_cccid

    ocio_transform = create_ocio_transform([keys])
    ocio_look.setTransform(ocio_transform)

    config.addLook(ocio_look)

    print('Creating aliased colorspace')

    # Creating *OCIO* colorspace referencing the look:
    # - Needed for implementations that don't process looks properly.
    # - Needed for implementations that don't expose looks properly.
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

    config_data['colorSpaces'].append(colorspace)

    print('')


def add_looks_to_views(looks,
                       reference_name,
                       config_data,
                       multiple_displays=False):
    """
    Integrates a set of looks into the *OCIO* config's Displays and Views

    Parameters
    ----------
    looks : array of str or unicode
        Names of looks
    reference_name : str or unicode
        The name of the *OCIO* reference colorspace
    config_data : dict
        Colorspaces and transforms converting between those colorspaces and
        the reference colorspace, *ACES*.
    multiple_displays : bool
        If true, looks are added to the config_data looks list
        If false, looks are integrated directly into the list of displays and 
        views. This may be necessary due to limitations of some applications' 
        currently implementation of OCIO, ex. Maya 2016.

    Returns
    -------
    None
    """
    look_names = [look[0] for look in looks]

    # Option 1
    # - Adding a *look* per *Display*.
    # - Assuming there is a *Display* for each *ACES* *Output Transform*.
    if multiple_displays:
        for look_name in look_names:
            config_data['looks'].append(look_name)

    # Option 2
    # - Copy each *Output Transform* colorspace.
    # - For each copy, add a *LookTransform* to the head of the
    # `from_reference` transform list.
    # - Add these the copy colorspaces for the *Displays* / *Views*.
    else:
        for display, view_list in config_data['displays'].iteritems():
            colorspace_c = None
            look_names_string = ''
            for view_name, output_colorspace in view_list.iteritems():
                if view_name == 'Output Transform':

                    print('Adding new View that incorporates looks')

                    colorspace_c = copy.deepcopy(output_colorspace)

                    for i, look_name in enumerate(look_names):
                        look_name = look_names[i]

                        # Add the `LookTransform` to the head of the
                        # `from_reference` transform list.
                        if colorspace_c.from_reference_transforms:
                            colorspace_c.from_reference_transforms.insert(
                                i,
                                {'type': 'look',
                                 'look': look_name,
                                 'src': reference_name,
                                 'dst': reference_name,
                                 'direction': 'forward'})

                        # Add the `LookTransform` to the end of
                        # the `to_reference` transform list.
                        if colorspace_c.to_reference_transforms:
                            inverse_look_name = look_names[
                                len(look_names) - 1 - i]

                            colorspace_c.to_reference_transforms.append(
                                {'type': 'look',
                                 'look': inverse_look_name,
                                 'src': reference_name,
                                 'dst': reference_name,
                                 'direction': 'inverse'})

                        if look_name not in config_data['looks']:
                            config_data['looks'].append(look_name)

                    look_names_string = ', '.join(look_names)
                    colorspace_c.name = '%s with %s' % (
                        output_colorspace.name, look_names_string)
                    colorspace_c.aliases = [
                        'out_%s' % compact(colorspace_c.name)]

                    print('Colorspace that incorporates looks '
                          'created : %s' % colorspace_c.name)

                    config_data['colorSpaces'].append(colorspace_c)

            if colorspace_c:
                print('Adding colorspace that incorporates looks '
                      'into view list')

                # Updating the *View* name.
                view_list['Output Transform with %s' % look_names_string] = (
                    colorspace_c)
                config_data['displays'][display] = view_list


def create_config(config_data,
                  aliases=False,
                  prefix=False,
                  multiple_displays=False,
                  look_info=None,
                  custom_lut_dir=None):
    """
    Create the *OCIO* config based on the configuration data

    Parameters
    ----------
    config_data : dict
        Colorspaces and transforms converting between those colorspaces and
        the reference colorspace, *ACES*, along with other data needed to 
        generate a complete *OCIO* configuration
    aliases : bool, optional
        Whether or not to include Alias colorspaces 
    prefix : bool, optional
        Whether or not to prefix the colorspace names with their Family names
    multiple_displays : bool, optional
        Whether to create a single display named *ACES* with Views for each
        Output Transform or multiple displays, one for each Output Transform
    look_info : array of str or unicode, optional
        Paths and names for look data
    custom_lut_dir : str or unicode, optional
        Directory to use for storing custom look files

    Returns
    -------
    *OCIO* config
         The constructed OCIO configuration
    """

    if look_info is None:
        look_info = []

    prefixed_names = {}
    alias_colorspaces = []

    config = ocio.Config()

    config.setDescription('An ACES config generated from python')

    search_path = ['luts']
    if custom_lut_dir:
        search_path.append('custom')
    config.setSearchPath(':'.join(search_path))

    reference_data = config_data['referenceColorSpace']

    # Adding the colorspace *Family* into the name which helps with
    # applications that presenting colorspaces as one a flat list.
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

    if aliases:
        if reference_data.aliases:
            # Deferring adding alias colorspaces until end, which helps with
            # applications listing the colorspaces in the order that they were
            # defined in the configuration: alias colorspaces are usually named
            # lower case with spaces but normal colorspaces names are longer
            # and more verbose, thus it becomes harder for user to visually
            # parse the list of colorspaces when there are names such as
            # "crv_canonlog" interspersed with names like
            # "Input - Canon - Curve - Canon-Log".
            # Moving the alias colorspace definitions to the end of the
            # configuration avoids the above problem.
            alias_colorspaces.append(
                [reference_data, reference_data, reference_data.aliases])

    print('')

    if look_info:
        print('Adding looks')

        config_data['looks'] = []

        for look in look_info:
            add_look(config,
                     look,
                     custom_lut_dir,
                     reference_data.name,
                     config_data)

        add_looks_to_views(look_info,
                           reference_data.name,
                           config_data,
                           multiple_displays)

        print('')

    print('Adding regular colorspaces')

    for colorspace in sorted(config_data['colorSpaces'],
        cmp=lambda x,y: cmp(x.family.lower(), y.family.lower())):
        # Adding the colorspace *Family* into the name which helps with
        # applications that presenting colorspaces as one a flat list.
        if prefix:
            prefixed_name = colorspace_prefixed_name(colorspace)
            prefixed_names[colorspace.name] = prefixed_name
            colorspace.name = prefixed_name

        print('Creating new color space : %s' % colorspace.name)

        description = colorspace.description
        if colorspace.aces_transform_id:
            description += (
                '\n\nACES Transform ID : %s' % colorspace.aces_transform_id)

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
            ocio_transform = create_ocio_transform(
                colorspace.to_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_TO_REFERENCE)

        if colorspace.from_reference_transforms:
            print('\tGenerating From-Reference transforms')
            ocio_transform = create_ocio_transform(
                colorspace.from_reference_transforms)
            ocio_colorspace.setTransform(
                ocio_transform,
                ocio.Constants.COLORSPACE_DIR_FROM_REFERENCE)

        config.addColorSpace(ocio_colorspace)

        if aliases:
            if colorspace.aliases:
                # Deferring adding alias colorspaces until end, which helps
                # with applications listing the colorspaces in the order that
                # they were defined in the configuration.
                alias_colorspaces.append(
                    [reference_data, colorspace, colorspace.aliases])

        print('')

    print('')

    # Adding roles early so that alias colorspaces can be created
    # with roles names before remaining colorspace aliases are added
    # to the configuration.
    print('Setting the roles')

    if prefix:
        set_config_roles(
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
            compositing_linear=prefixed_names[config_data['roles']['scene_linear']],
            rendering=prefixed_names[config_data['roles']['scene_linear']],
            texture_paint=prefixed_names[
                config_data['roles']['texture_paint']])

        # Add the aliased colorspaces for each role
        for role_name, role_colorspace_name in config_data['roles'].iteritems():
            role_colorspace_prefixed_name = prefixed_names[role_colorspace_name]

            #print( 'Finding colorspace : %s' % role_colorspace_prefixed_name )
            # Find the colorspace pointed to by the role
            role_colorspaces = [colorspace
                for colorspace in config_data['colorSpaces']
                if colorspace.name == role_colorspace_prefixed_name]
            role_colorspace = None
            if len(role_colorspaces) > 0:
                role_colorspace = role_colorspaces[0]
            else:
                if reference_data.name == role_colorspace_prefixed_name:
                    role_colorspace = reference_data

            if role_colorspace:
                # The alias colorspace shouldn't match the role name exactly
                role_name_alias1 = "role_%s" % role_name
                role_name_alias2 = "Role - %s" % role_name

                print( 'Adding a role colorspace named %s, pointing to %s' % (
                    role_name_alias2, role_colorspace.name))

                alias_colorspaces.append(
                (reference_data, role_colorspace, [role_name_alias1]))

                add_colorspace_aliases(
                config, reference_data, role_colorspace, [role_name_alias2], 'Roles')

    else:
        set_config_roles(
            config,
            color_picking=config_data['roles']['color_picking'],
            color_timing=config_data['roles']['color_timing'],
            compositing_log=config_data['roles']['compositing_log'],
            data=config_data['roles']['data'],
            default=config_data['roles']['default'],
            matte_paint=config_data['roles']['matte_paint'],
            reference=config_data['roles']['reference'],
            scene_linear=config_data['roles']['scene_linear'],
            compositing_linear=config_data['roles']['scene_linear'],
            rendering=config_data['roles']['scene_linear'],
            texture_paint=config_data['roles']['texture_paint'])

        # Add the aliased colorspaces for each role
        for role_name, role_colorspace_name in config_data['roles'].iteritems():
            # Find the colorspace pointed to by the role
            role_colorspaces = [colorspace
            for colorspace in config_data['colorSpaces']
            if colorspace.name == role_colorspace_name]
            role_colorspace = None
            if len(role_colorspaces) > 0:
                role_colorspace = role_colorspaces[0]
            else:
                if reference_data.name == role_colorspace_name:
                    role_colorspace = reference_data

            if role_colorspace:
                # The alias colorspace shouldn't match the role name exactly
                role_name_alias1 = "role_%s" % role_name
                role_name_alias2 = "Role - %s" % role_name

                print('Adding a role colorspace named %s, pointing to %s' % (
                    role_name_alias2, role_colorspace.name))

                alias_colorspaces.append(
                (reference_data, role_colorspace, [role_name_alias1]))

                add_colorspace_aliases(
                config, reference_data, role_colorspace, [role_name_alias2], 'Roles')

    print('')

    # Adding alias colorspaces at the end as some applications use
    # colorspaces definitions order of the configuration to order
    # the colorspaces in their selection lists, some applications
    # use alphabetical ordering.
    # This should keep the alias colorspaces out of the way for applications
    # using the configuration order.
    print('Adding the alias colorspaces')
    for reference, colorspace, aliases in alias_colorspaces:
        add_colorspace_aliases(config, reference, colorspace, aliases)

    print('')

    print('Adding the diplays and views')

    # Setting the *color_picking* role to be the first *Display*'s
    # *Output Transform* *View*.
    default_display_name = config_data['defaultDisplay']
    default_display_views = config_data['displays'][default_display_name]
    default_display_colorspace = default_display_views['Output Transform']

    # Defining *Displays* and *Views*.
    displays, views = [], []

    # Defining a generic *Display* and *View* setup.
    if multiple_displays:
        looks = config_data['looks'] if ('looks' in config_data) else []
        looks = ', '.join(looks)
        print('Creating multiple displays, with looks : %s' % looks)

        # *Displays* are not reordered to put the *defaultDisplay* first
        # because *OCIO* will order them alphabetically when the configuration
        # is written to disk.
        for display, view_list in config_data['displays'].iteritems():
            for view_name, colorspace in view_list.iteritems():
                config.addDisplay(display, view_name, colorspace.name, looks)
                if 'Output Transform' in view_name and looks != '':
                    # *Views* without *Looks*.
                    config.addDisplay(display, view_name, colorspace.name)

                    # *Views* with *Looks*.
                    view_name_with_looks = '%s with %s' % (view_name, looks)
                    config.addDisplay(display, view_name_with_looks,
                                      colorspace.name, looks)
                else:
                    config.addDisplay(display, view_name, colorspace.name)
                if not (view_name in views):
                    views.append(view_name)
            displays.append(display)

    # *Displays* and *Views* useful in a *GUI* context.
    else:
        single_display_name = 'ACES'
        displays.append(single_display_name)

        # Ensuring the *defaultDisplay* is first.
        display_names = sorted(config_data['displays'])
        display_names.insert(0, display_names.pop(
            display_names.index(default_display_name)))

        looks = config_data['looks'] if ('looks' in config_data) else []
        look_names = ', '.join(looks)

        displays_views_colorspaces = []

        for display in display_names:
            view_list = config_data['displays'][display]
            for view_name, colorspace in view_list.iteritems():
                if 'Output Transform' in view_name:

                    # We use the *Display* names as the *View* names in this
                    # case as there is a single *Display* containing all the
                    # *Views*.
                    # This works for more applications than not,as of the time
                    # of this implementation.

                    # Autodesk Maya 2016 doesn't support parentheses in
                    # *View* names.
                    sanitised_display = replace(display, {')': '', '(': ''})

                    # *View* with *Looks*.
                    if 'with' in view_name:
                        sanitised_display = '%s with %s' % (
                            sanitised_display, look_names)

                        views_with_looks_at_end = False
                        # Storing combo of *Display*, *View* and *Colorspace*
                        # name so they can be added to the end of the list.
                        if views_with_looks_at_end:
                            displays_views_colorspaces.append(
                                [single_display_name, sanitised_display,
                                 colorspace.name])
                        else:
                            config.addDisplay(single_display_name,
                                              sanitised_display,
                                              colorspace.name)

                            if not (sanitised_display in views):
                                views.append(sanitised_display)

                    # *View* without *Looks*.
                    else:
                        config.addDisplay(single_display_name,
                                          sanitised_display,
                                          colorspace.name)

                        if not (sanitised_display in views):
                            views.append(sanitised_display)

        # Adding to the configuration any *Display*, *View* combinations that
        # were saved for later.
        # This list should be empty unless `views_with_looks_at_end` is
        # set `True` above.
        for display_view_colorspace in displays_views_colorspaces:
            single_display_name, sanitised_display, colorspace_name = (
                display_view_colorspace)

            config.addDisplay(single_display_name,
                              sanitised_display,
                              colorspace_name)

            if not (sanitised_display in views):
                views.append(sanitised_display)

        raw_display_space_name = config_data['roles']['data']
        log_display_space_name = config_data['roles']['compositing_log']

        if prefix:
            raw_display_space_name = prefixed_names[raw_display_space_name]
            log_display_space_name = prefixed_names[log_display_space_name]

        config.addDisplay(single_display_name, 'Raw', raw_display_space_name)
        views.append('Raw')
        config.addDisplay(single_display_name, 'Log', log_display_space_name)
        views.append('Log')

    config.setActiveDisplays(','.join(sorted(displays)))
    config.setActiveViews(','.join(views))

    print('')

    # Ensuring the configuration is valid.
    config.sanityCheck()

    # Resetting colorspace names to their non-prefixed versions.
    if prefix:
        prefixed_names_inverse = {}
        for original, prefixed in prefixed_names.iteritems():
            prefixed_names_inverse[prefixed] = original

        reference_data.name = prefixed_names_inverse[reference_data.name]

        try:
            for colorspace in config_data['colorSpaces']:
                colorspace.name = prefixed_names_inverse[colorspace.name]
        except:
            print('Error with Prefixed names')
            for original, prefixed in prefixed_names.iteritems():
                print('%s, %s' % (original, prefixed))

            print('\n')

            print('Inverse Lookup of Prefixed names')
            for prefixed, original in prefixed_names_inverse.iteritems():
                print('%s, %s' % (prefixed, original))
            raise

    return config


def create_config_data(odt_info,
                       lmt_info,
                       shaper_name,
                       aces_ctl_directory,
                       lut_directory,
                       lut_resolution_1d=4096,
                       lut_resolution_3d=64,
                       cleanup=True):
    """
    Create the *ACES* LUTs and data structures needed for later *OCIO* 
    configuration generation

    Parameters
    ----------
    odt_info : array of dicts of str or unicode
        Descriptions of the *ACES* Output Transforms
    lmt_info : array of dicts of str or unicode
        Descriptions of the *ACES* Look Transforms
    shaper_name : str or unicode
        The name of the Shaper function to use when generating LUTs. 
        Options: Log2, DolbyPQ
    aces_ctl_directory : str or unicode
        The path to the aces 'transforms/ctl/utilities'
    lut_directory : str or unicode
        The path to use when writing LUTs
    lut_resolution_1d : int, optional
        The resolution of generated 1D LUTs
    lut_resolution_3d : int, optional
        The resolution of generated 3D LUTs
    cleanup : bool
        Whether or not to clean up the intermediate images 

    Returns
    -------
    dict
         Colorspaces, LUT paths and transforms converting between those 
         colorspaces and the reference colorspace, *ACES*.
    """

    print('create_config_data - begin')
    config_data = {}

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

    # *ARRI Log-C* to *ACES*
    arri_colorspaces = arri.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in arri_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *Canon-Log* to *ACES*
    canon_colorspaces = canon.create_colorspaces(lut_directory,
                                                 lut_resolution_1d)
    for cs in canon_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *GoPro Protune* to *ACES*
    gopro_colorspaces = gopro.create_colorspaces(lut_directory,
                                                 lut_resolution_1d)
    for cs in gopro_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *Panasonic V-Log* to *ACES*
    panasonic_colorspaces = panasonic.create_colorspaces(lut_directory,
                                                         lut_resolution_1d)
    for cs in panasonic_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *RED* colorspaces to *ACES*
    red_colorspaces = red.create_colorspaces(lut_directory,
                                             lut_resolution_1d)
    for cs in red_colorspaces:
        config_data['colorSpaces'].append(cs)

    # *S-Log* to *ACES*
    sony_colorspaces = sony.create_colorspaces(lut_directory,
                                               lut_resolution_1d)
    for cs in sony_colorspaces:
        config_data['colorSpaces'].append(cs)

    # -------------------------------------------------------------------------
    # General Colorspaces
    # -------------------------------------------------------------------------
    general_colorspaces = general.create_colorspaces(lut_directory,
                                                     lut_resolution_1d)
    for cs in general_colorspaces:
        config_data['colorSpaces'].append(cs)

    # The *Raw* colorspace
    raw = general.create_raw()
    config_data['colorSpaces'].append(raw)

    # Overriding various roles
    config_data['roles']['data'] = raw.name
    config_data['roles']['reference'] = raw.name
    config_data['roles']['texture_paint'] = raw.name

    print('create_config_data - end')

    return config_data


def write_config(config, config_path, sanity_check=True):
    """
    Writes the configuration to given path.

    Parameters
    ----------
    config : Config
        *OCIO* configuration.
    config_path : str or unicode
        Path to write the configuration path.
    sanity_check : bool
        Performs configuration sanity checking prior to writing it on disk.

    Returns
    -------
    bool
         Definition success.
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


def generate_baked_LUTs(odt_info,
                        shaper_name,
                        baked_directory,
                        config_path,
                        lut_resolution_3d,
                        lut_resolution_shaper=1024,
                        prefix=False):
    """
    Generate baked representations of the transforms from the *ACES* *OCIO*
    configuration

    Parameters
    ----------
    odt_info : array of dicts of str or unicode
        Descriptions of the *ACES* Output Transforms
    shaper_name : str or unicode
        The name of the Shaper function to use when generating LUTs. 
        Options: Log2, DolbyPQ
    baked_directory : str or unicode
        The path to use when writing baked LUTs
    config_path : str or unicode
        The path to the *OCIO* configuration
    lut_resolution_3d : int, optional
        The resolution of generated 3D LUTs
    lut_resolution_shaper : int, optional
        The resolution of shaper used as part of some 3D LUTs
    prefix : bool, optional
        Whether or not colorspace names will use their Family names as prefixes
        in the *OCIO* config

    Returns
    -------
    None
    """

    odt_info_C = dict(odt_info)

    # Older behavior for *ODTs* that have support for full and legal ranges,
    # generating a LUT for both ranges.
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

    for odt_ctl_name, odt_values in odt_info_C.iteritems():
        odt_prefix = odt_values['transformUserNamePrefix']
        odt_name = odt_values['transformUserName']

        pq_shaper_name = ("%s %s" % ('Dolby PQ', ' '.join(shaper_name.split(' ')[-3:])) )

        if '1000 nits' in odt_name:
            odt_shaper = pq_shaper_name.replace("48 nits", "1000 nits")
        elif '2000 nits' in odt_name:
            odt_shaper = pq_shaper_name.replace("48 nits", "2000 nits")
        elif '4000 nits' in odt_name:
            odt_shaper = pq_shaper_name.replace("48 nits", "4000 nits")
        else:
            odt_shaper = shaper_name

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
                args += ['--shaperspace', 'Utility - %s' % odt_shaper,
                         '--shapersize', str(lut_resolution_shaper)]
            else:
                args += ['--shaperspace', odt_shaper,
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
                args += ['--shaperspace', 'Utility - %s' % odt_shaper,
                         '--shapersize', str(lut_resolution_shaper)]
            else:
                args += ['--shaperspace', odt_shaper,
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
                lin_shaper_name = '%s - AP1' % odt_shaper
            else:
                lin_shaper_name = odt_shaper
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


def generate_config_directory(config_directory,
                              bake_secondary_luts=False,
                              custom_lut_dir=None):
    """
    Create the directories needed for configuration generation

    Parameters
    ----------
    config_directory : str or unicode
        The base config directory
    bake_secondary_luts : bool, optional
        Whether or not to create directories for baked LUTs
    custom_lut_dir : bool, optional
        Whether or not to create directories for custom Look LUTs

    Returns
    -------
    None
    """

    lut_directory = os.path.join(config_directory, 'luts')
    dirs = [config_directory, lut_directory]

    if bake_secondary_luts:
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


def generate_config(aces_ctl_directory,
                    config_directory,
                    lut_resolution_1d=4096,
                    lut_resolution_3d=64,
                    bake_secondary_luts=True,
                    multiple_displays=False,
                    look_info=None,
                    copy_custom_luts=True,
                    cleanup=True,
                    prefix_colorspaces_with_family_names=True,
                    shaper_base_name='Log2'):
    """
    Generates LUTs, matrices and configuration data and then creates the 
    *ACES* configuration.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to the aces 'transforms/ctl/utilities'
    config_directory : str or unicode
        The directory that will hold the generated configuration and LUTs
    lut_resolution_1d : int, optional
        The resolution of generated 1D LUTs
    lut_resolution_3d : int, optional
        The resolution of generated 3D LUTs
    bake_secondary_luts : bool, optional
        Whether or not to create directories for baked LUTs
    multiple_displays : bool, optional
        Whether to create a single display named *ACES* with Views for each
        Output Transform or multiple displays, one for each Output Transform
    look_info : array of str or unicode, optional
        Paths and names for look data
    copy_custom_luts : bool, optional
        Whether to reference custom look LUTs directly or to copy them into a 
        directory within the generated configuration
    cleanup : bool, optional
        Whether or not to clean up the intermediate images 
    prefix_colorspaces_with_family_names : bool, optional
        Whether or not colorspace names will use their Family names as prefixes
        in the *OCIO* config
    shaper_base_name : str or unicode
        The name of the Shaper function to use when generating LUTs. 
        Options: Log2, DolbyPQ

    Returns
    -------
    bool
         Success or failure of configuration generation process
    """

    if look_info is None:
        look_info = []

    custom_lut_dir = None
    if copy_custom_luts:
        custom_lut_dir = os.path.join(config_directory, 'custom')

    lut_directory = generate_config_directory(config_directory,
                                              bake_secondary_luts,
                                              custom_lut_dir)
    odt_info = aces.get_ODTs_info(aces_ctl_directory)
    lmt_info = aces.get_LMTs_info(aces_ctl_directory)

    if shaper_base_name == 'DolbyPQ':
        shaper_name = 'Dolby PQ 48 nits Shaper'
    else:
        shaper_name = 'Log2 48 nits Shaper'

    config_data = create_config_data(odt_info,
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

    if bake_secondary_luts:
        generate_baked_LUTs(odt_info,
                            shaper_name,
                            os.path.join(config_directory, 'baked'),
                            os.path.join(config_directory, 'config.ocio'),
                            lut_resolution_3d,
                            lut_resolution_1d,
                            prefix=prefix_colorspaces_with_family_names)

    return True


def main():
    """
    A simple main that allows the user to exercise the various functions
    defined in this file

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    import optparse

    usage = '%prog [options]\n'
    usage += '\n'
    usage += 'An OCIO config generation script for ACES 1.0.1\n'
    usage += '\n'
    usage += 'Command-line examples'
    usage += '\n'
    usage += ('Create a GUI-friendly ACES 1.0.1 config with no secondary, '
              'baked LUTs: \n')
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '--dontBakeSecondaryLUTs')
    usage += '\n'
    usage += 'Create a more OCIO-compliant ACES 1.0.1 config: \n'
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '--createMultipleDisplays')
    usage += '\n'
    usage += '\n'
    usage += 'Adding custom looks'
    usage += '\n'
    usage += ('Create a GUI-friendly ACES 1.0.1 config with an ACES-style CDL '
              '(will be applied in the ACEScc colorspace): \n')
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '\n\t\t--addACESLookCDL ACESCDLName '
              '/path/to/SampleCDL.ccc cc03345')
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0.1 config with a general CDL: \n'
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '\n\t\t--addCustomLookCDL CustomCDLName "ACES - ACEScc" '
              '/path/to/SampleCDL.ccc cc03345')
    usage += '\n'
    usage += ('\tIn this example, the CDL will be applied in the '
              'ACEScc colorspace, but the user could choose other spaces '
              'by changing the argument after the name of the look. \n')
    usage += '\n'
    usage += ('Create a GUI-friendly ACES 1.0.1 config with an ACES-style LUT '
              '(will be applied in the ACEScc colorspace): \n')
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '\n\t\t--addACESLookLUT ACESLUTName '
              '/path/to/SampleCDL.ccc cc03345')
    usage += '\n'
    usage += 'Create a GUI-friendly ACES 1.0.1 config with a general LUT: \n'
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '\n\t\t--addCustomLookLUT CustomLUTName "ACES - ACEScc" '
              '/path/to/SampleCDL.ccc cc03345')
    usage += '\n'
    usage += ('\tIn this example, the LUT will be applied in the '
              'ACEScc colorspace, but the user could choose other spaces '
              'by changing the argument after the name of the look. \n')
    usage += '\n'
    usage += ('Create a GUI-friendly ACES 1.0.1 config using the Dolby PQ '
              'transfer function as the shaper: \n')
    usage += ('\tcreate_aces_config -a /path/to/aces-dev/transforms/ctl '
              '--lutResolution1d 4096 --lutResolution3d 65 -c aces_1.0.1 '
              '--shaper DolbyPQ')
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

    p.add_option('--shaper', '-s', default='Log2')

    options, arguments = p.parse_args()

    aces_ctl_directory = options.acesCTLDir
    config_directory = options.configDir
    lut_resolution_1d = int(options.lutResolution1d)
    lut_resolution_3d = int(options.lutResolution3d)
    bake_secondary_luts = not options.dontBakeSecondaryLUTs
    cleanup_temp_images = not options.keepTempImages
    multiple_displays = options.createMultipleDisplays
    copy_custom_luts = options.copyCustomLUTs
    shaper_base_name = options.shaper
    prefix = True

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

    return generate_config(aces_ctl_directory,
                           config_directory,
                           lut_resolution_1d,
                           lut_resolution_3d,
                           bake_secondary_luts,
                           multiple_displays,
                           look_info,
                           copy_custom_luts,
                           cleanup_temp_images,
                           prefix,
                           shaper_base_name)


if __name__ == '__main__':
    main()
