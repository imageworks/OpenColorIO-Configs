import PyOpenColorIO as OCIO

#
# Utility classes and functions
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