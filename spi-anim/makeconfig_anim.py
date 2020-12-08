#!/usr/bin/env python3

import math,os,sys
import PyOpenColorIO as OCIO


outputfilename = "config.ocio"

config = OCIO.Config() 

LUT_SEARCH_PATH = ['luts']
config.setSearchPath(':'.join(LUT_SEARCH_PATH))

# Set roles
config.setRole(OCIO.ROLE_SCENE_LINEAR, "lnf")
config.setRole(OCIO.ROLE_REFERENCE, "lnf")
config.setRole(OCIO.ROLE_COLOR_TIMING, "lm10")
config.setRole(OCIO.ROLE_COMPOSITING_LOG, "lmf")
config.setRole(OCIO.ROLE_COLOR_PICKING,"cpf")
config.setRole(OCIO.ROLE_DATA,"ncf")
config.setRole(OCIO.ROLE_DEFAULT,"ncf")
config.setRole(OCIO.ROLE_MATTE_PAINT,"mp16")
config.setRole(OCIO.ROLE_TEXTURE_PAINT,"dt16")

## Scene OCIO.Constants.INTERP_LINEAR ###############################################################

cs = OCIO.ColorSpace(family='ln', name='lnf')
cs.setDescription("lnf :linear show space JJS")
cs.setBitDepth(OCIO.BIT_DEPTH_F32)
cs.setAllocationVars([-13.0,4.0])
cs.setAllocation(OCIO.ALLOCATION_LG2)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='ln', name='lnh')
cs.setDescription("lnh :linear show space")
cs.setBitDepth(OCIO.BIT_DEPTH_F16)
cs.setAllocationVars([-13.0,4.0])
cs.setAllocation(OCIO.ALLOCATION_LG2)
config.addColorSpace(cs)

## Log Monitor ########################################################################

cs = OCIO.ColorSpace(family='lm',name='lm16')
cs.setDescription("lm16 : Log Monitor this space has a log like response and srgb primaries, it is used for color grading ")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
t=OCIO.FileTransform('lm16.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR)
cs.setTransform(t, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='lm',name='lm10')
cs.setDescription("lm10 : Log Monitor this space has a log like response and srgb primaries, it is used for color grading ")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT10)
t=OCIO.FileTransform('lm10.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR)
cs.setTransform(t, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='lm',name='lmf')
cs.setDescription("lmf : Log Monitor this space has a log like response and srgb primaries, it is used as a compositing log")
cs.setBitDepth(OCIO.BIT_DEPTH_F32)
cs.setAllocationVars([-0.2,2.484])
t=OCIO.FileTransform('lmf.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR)
cs.setTransform(t, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)

## VD ########################################################################

cs = OCIO.ColorSpace(family='vd',name='vd16')
cs.setDescription("vd16 : The simple video conversion from a gamma 2.2 srgb space")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('vd16.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)


cs = OCIO.ColorSpace(family='vd',name='vd10')
cs.setDescription("vd10 : The simple video conversion from a gamma 2.2 srgb space")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT10)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('vd10.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='vd',name='vd8')
cs.setDescription("vd8 : The simple video conversion from a gamma 2.2 srgb space")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT8)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('vd8.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)


## REC709 CONVERSIONS ########################################################################
cs = OCIO.ColorSpace(family='hd',name='hd10')
cs.setDescription("hd10 : The simple conversion for REC709")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT10)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('hdOffset.spimtx',direction=OCIO.TRANSFORM_DIR_INVERSE,interpolation=OCIO.INTERP_NEAREST))
groupTransform.prependTransform(OCIO.ColorSpaceTransform(src='vd16', dst='lnf'))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)


## TEXTURE PUBLISHING ########################################################################

cs = OCIO.ColorSpace(family='dt',name='dt16')
cs.setDescription("dt16 :diffuse texture conversion")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('dt.spimtx',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST))
groupTransform.prependTransform(OCIO.ColorSpaceTransform(src='vd16', dst='lnf'))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)


## MATTE PUBLISHING ########################################################################
cs = OCIO.ColorSpace(family='mp',name='mp16')
cs.setDescription("mp16 : conversion for matte painting")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.FileTransform('mp.spimtx',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST))
groupTransform.prependTransform(OCIO.ColorSpaceTransform(src='vd16', dst='lnf'))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)


## COLOR PICKER ########################################################################

cs = OCIO.ColorSpace(family='cp',name='cpf')
cs.setDescription("cpf :video like conversion used for color picking ") 
cs.setBitDepth(OCIO.BIT_DEPTH_F32)
cs.setTransform(OCIO.FileTransform('cpf.spi1d',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_NEAREST), OCIO.COLORSPACE_DIR_TO_REFERENCE)
config.addColorSpace(cs)

## DATA ########################################################################

cs = OCIO.ColorSpace(family='nc',name='nc8')
cs.setDescription("nc8 :nc,Non-color used to store non-color data such as depth or surface normals")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT8)
cs.setIsData(True)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='nc',name='nc10')
cs.setDescription("nc10 :nc,Non-color used to store non-color data such as depth or surface normals")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT10)
cs.setIsData(True)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='nc',name='nc16')
cs.setDescription("nc16 :nc,Non-color used to store non-color data such as depth or surface normals")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
cs.setIsData(True)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='nc',name='ncf')
cs.setDescription("ncf :nc,Non-color used to store non-color data such as depth or surface normals")
cs.setBitDepth(OCIO.BIT_DEPTH_F32)
cs.setIsData(True)
config.addColorSpace(cs)

## DISPLAY SPACES ##################################################################

#
# This is not as clean as would be desired.
# There is a conversion made from srgb to P3.
# Then there is a tone range correction that limits the dynamic range of the DLP to 
# be appropriate for material created on the DreamColor display.
#
cs = OCIO.ColorSpace(family='p3dci',name='p3dci8')
cs.setDescription("p3dci8 : 8 Bit int rgb display space for gamma 2.6 P3 projection.")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT8)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.ColorSpaceTransform(src='lnf', dst='vd16'))
groupTransform.prependTransform(OCIO.ExponentTransform(value=[2.2,2.2,2.2,1.0], direction=OCIO.TRANSFORM_DIR_FORWARD))
groupTransform.prependTransform(OCIO.FileTransform('srgb_to_p3d65.spimtx',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR))
groupTransform.prependTransform(OCIO.FileTransform('p3d65_to_pdci.spimtx',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR))
groupTransform.prependTransform(OCIO.FileTransform('htr_dlp_tweak.spimtx',direction=OCIO.TRANSFORM_DIR_FORWARD,interpolation=OCIO.INTERP_LINEAR))
groupTransform.prependTransform(OCIO.ExponentTransform(value=[2.6,2.6,2.6,1.0], direction=OCIO.TRANSFORM_DIR_INVERSE))
groupTransform.prependTransform(OCIO.FileTransform('correction.spi1d'))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_FROM_REFERENCE)
config.addColorSpace(cs)

cs = OCIO.ColorSpace(family='xyz',name='xyz16')
cs.setDescription("xyz16 : 16 Bit int space for DCP creation.")
cs.setBitDepth(OCIO.BIT_DEPTH_UINT16)
groupTransform = OCIO.GroupTransform()
groupTransform.prependTransform(OCIO.ColorSpaceTransform(src='lnf',dst='p3dci8'))
groupTransform.prependTransform(OCIO.ExponentTransform([2.6,2.6,2.6,1.0]))
groupTransform.prependTransform(OCIO.FileTransform('p3_to_xyz16_corrected_wp.spimtx'))
groupTransform.prependTransform(OCIO.ExponentTransform([2.6,2.6,2.6,1.0],direction=OCIO.TRANSFORM_DIR_INVERSE))
cs.setTransform(groupTransform, OCIO.COLORSPACE_DIR_FROM_REFERENCE)
config.addColorSpace(cs)



## DISPLAY SPACES ##################################################################

for name,colorspace in [ ['Film','vd16'], ['Log','lm10'],['Raw','nc10']]:
    config.addDisplayView('sRGB',name,colorspace)
for name,colorspace in [ ['Film','p3dci8'], ['Log','lm10'], ['Raw','nc10']]:
     config.addDisplayView('DCIP3',name,colorspace)

config.setActiveViews(','.join(['Film','Log','Raw']))
config.setActiveDisplays(','.join(['sRGB','DCIP3']))


try:
    config.validate()
except e:
    print(e)
    print ("Configuration was not written due to a failed Sanity Check")
    sys.exit()
else:
    f = open(outputfilename,"w")
    f.write(config.serialize())
    f.close()
    print ("Wrote %s"%outputfilename)



