#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on %(date)s
@author: %(username)s

This module includes a class able to implement a basic interface to 
Princeton Instrument's PICam library.

it is based on the original version writtes by  Daniel R. Dietze <daniel.dietze@berkeley.edu>

"""
# %%
__author__ = "ROMEO Michelangelo"
__copyright__ = "Copyright 2020, The HYRBID Python formation Project"
__credits__ = ""
__license__ = "GPL"
__version__ = "1.2.0"
__maintainer__ = "M. ROMEO"
__email__ = "michelangelo.romeo@ipcms.unistra.fr"
__status__ = "Production"
# %%
# TODO: Comment and Doc objects


import os
import ctypes
if os.name == 'nt':
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    def check_bool(result, func, args):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return args

    kernel32.LoadLibraryExW.errcheck = check_bool
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.LoadLibraryExW.argtypes = (wintypes.LPCWSTR,
                                        wintypes.HANDLE,
                                        wintypes.DWORD)

class CDLLEx(ctypes.WinDLL):
    def __init__(self, name, mode=0, handle=None, 
                 use_errno=True, use_last_error=False):
        if os.name == 'nt' and handle is None:
            handle = kernel32.LoadLibraryExW(name, None, mode)
        super(CDLLEx, self).__init__(name, mode, handle,
                                     use_errno, use_last_error)


import numpy as np
if __name__ == '__main__':
    from picam_types import *
else:
    from modules.picam_types import *

# EOL = '\n' or '<br>'
EOL = '\n'

# ##########################################################################################################
# helper functions
def ptr(x):
    """Shortcut to return a ctypes.pointer to object x.
    """
    return ctypes.pointer(x)


# ##########################################################################################################
# Camera Class
class picam():
    """Main class that handles all connectivity with library and cameras.
    """
    # +++++++++++ CONSTRUCTION / DESTRUCTION ++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self):
        # empty handle
        self.cam = None
        self.camIDs = None
        self.roisPtr = []
        self.pulsePtr = []
        self.modPtr = []
        self.acqThread = None
        self.totalFrameSize = 0
        self.paraType = ''
        self.framecount = pi64s(0)
        self.errors = []
        self.messages = []
        self.ROISAll = []

    # load picam.dll
    def loadLibrary(self, pathToLib=""):
        """Loads the picam library ('Picam.dll').

        :param str pathToLib: Path to the dynamic link library (optional). If empty, the library is loaded using the path given by the environment variabel *PicamRoot*, which is normally created by the PICam SDK installer.
        :returns: 
        """
        if pathToLib == "":
            # print(os.environ["PATH"])
            pathToLib = os.path.join(os.environ["PATH"], "Runtime", "Picam.dll")
        # pathToLib = os.path.join(pathToLib, "Picam.dll")
        # pathToLib = "C:\Program Files\Princeton Instruments\PICam\Runtime\Picam.dll"
        # print(pathToLib)
        try:
            self.lib = CDLLEx(pathToLib, 0x00000008)
            # self.lib = ctypes.cdll.LoadLibrary(pathToLib)
        except OSError:
            self.errors.append('Library not loaded' + EOL)
            return
        self.errors.append('Library loaded' + EOL)
        return

    # initialize library
    def initLibrary(self):
        """Initializes the picam library ('Picam.dll').

        :No params
        :returns: Prints the library version to stdout.
        """
        isconnected = pibln()
        try:
            self.status(self.lib.Picam_IsLibraryInitialized(ptr(isconnected)))
        except AttributeError:
            self.errors.append('Library not loaded' + EOL)
            return None
        if not isconnected.value:
            self.status(self.lib.Picam_InitializeLibrary())
        self.errors.append(self.getLibraryVersion())
        return None


    # call this function to release any resources and free the library
    def uninitLibrary(self):
        """Call this function to release any resources and free the library.
        """
        # clean up all reserved memory that may be around
        for i in range(len(self.roisPtr)):
            self.status(self.lib.Picam_DestroyRois(self.roisPtr[i]))
        self.roisPtr = []
        for i in range(len(self.pulsePtr)):
            self.status(self.lib.Picam_DestroyPulses(self.pulsePtr[i]))
        self.pulsePtr = []
        for i in range(len(self.modPtr)):
            self.status(self.lib.Picam_DestroyModulations(self.modPtr[i]))
        self.modPtr = []

        # disconnect from camera
        self.disconnect()

        if isinstance(self.camIDs, list):
            for c in self.camIDs:
                self.status(self.lib.Picam_DisconnectDemoCamera(ptr(c)))

        # free camID resources
        if self.camIDs is not None and not isinstance(self.camIDs, list):
            self.status(self.lib.Picam_DestroyCameraIDs(self.camIDs))
            self.camIDs = None

        # unload the library
        self.status(self.lib.Picam_UninitializeLibrary())
        
        self.errors.append("Unloaded PICamSDK" + EOL)
        return None

    # +++++++++++ CLASS FUNCTIONS ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # get version information
    def getLibraryVersion(self):
        """Returns the PICam library version string.
        """
        major = piint()
        minor = piint()
        distr = piint()
        released = piint()
        self.status(self.lib.Picam_GetVersion(ptr(major), ptr(minor), ptr(distr), ptr(released)))
        ret = f"PICam Library Version {major.value}.{minor.value}.{distr.value}.{released.value}" + EOL
        return ret
        
    # returns a list of camera IDs that are connected to the computer
    # if no physical camera is found, a demo camera is initialized - for debug only
    def getAvailableCameras(self):
        """Queries a list of IDs of cameras that are connected to the computer and prints some sensor information for each camera to stdout.

        If no physical camera is found, a demo camera is initialized - *for debug only*.
        """
        if self.camIDs is not None and not isinstance(self.camIDs, list):
            self.status(self.lib.Picam_DestroyCameraIDs(self.camIDs))
            self.camIDs = None

        # get connected cameras
        self.camIDs = ptr(PicamCameraID())
        id_count = piint()
        self.status(self.lib.Picam_GetAvailableCameraIDs(ptr(self.camIDs), ptr(id_count)))

        # if none are found, create a demo camera
        ret = "Available Cameras:" + EOL
        if id_count.value < 1:
            self.status(self.lib.Picam_DestroyCameraIDs(self.camIDs))

            model_array = ptr(piint())
            model_count = piint()
            self.status(self.lib.Picam_GetAvailableDemoCameraModels(ptr(model_array), ptr(model_count)))

            model_ID = PicamCameraID()
            # serial = ctypes.c_char_p("Demo Cam 1")
            serial = ctypes.c_char_p(0)
            self.status(self.lib.Picam_ConnectDemoCamera(model_array[85], serial, ptr(model_ID)))
            self.camIDs = [model_ID]

            self.status(self.lib.Picam_DestroyModels(model_array))

            ret += f'  Model is {PicamModelLookup[model_ID.model]}' + EOL
            ret += f'  Computer interface is {PicamComputerInterfaceLookup[model_ID.computer_interface]}' + EOL
            ret += f'  Sensor_name is {model_ID.sensor_name}' + EOL
            ret += f'  Serial number is {model_ID.serial_number}' + EOL
            ret += EOL
        else:
            for i in range(id_count.value):
                ret += f'  Model is {PicamModelLookup[self.camIDs[i].model]}' + EOL
                ret += f'  Computer interface is {PicamComputerInterfaceLookup[self.camIDs[i].computer_interface]}' + EOL
                ret += f'  Sensor_name is {self.camIDs[i].sensor_name}' + EOL
                ret += f'  Serial number is {self.camIDs[i].serial_number}' + EOL
                ret += EOL
        return ret

    # returns string associated with last error
    def getLastError(self):
        """Returns the identifier associated with the last error (*str*).
        """
        return PicamErrorLookup[self.err]

    def status(self, err):
        """Checks the return value of a picam function for any error code. If an error occurred, it prints the error message to stdout.

        :param int err: Error code returned by any picam function call.
        :returns: Error code (int) and if an error occurred, prints error message.
        """
        errstr = PicamErrorLookup.get(err, 'UnknownError')
        self.err = err
        if errstr != "None":
            self.errors.append(f"ERROR: {errstr}" + EOL)
            raise RuntimeError(f"PICam error {err}: {errstr}")
        self.err = err
        return err

    # connect / disconnect camera
    # if no camera ID is given, connect to the first available camera
    # otherwise camID is an integer index into a list of valid camera IDs that
    # has been retrieved by getAvailableCameras()
    def connect(self, camID=None):
        """ Connect to camera.

        :param int camID: Number / index of camera to connect to (optional). It is an integer index into a list of valid camera IDs that has been retrieved by :py:func:`getAvailableCameras`. If camID is None, this functions connects to the first available camera (default).
        """ 
        if self.cam is not None:
            self.disconnect()
        if camID is None:
            self.cam = pivoid()
            self.status(self.lib.Picam_OpenFirstCamera(ptr(self.cam)))
            print(self.cam)
        else:
            self.cam = pivoid()
            self.status(self.lib.Picam_OpenCamera(ptr(self.camIDs[camID]), ctypes.addressof(self.cam)))
        # invoke commit parameters to validate all parameters for acquisition
        self.errors.append(self.sendConfiguration())
        return None

    def disconnect(self):
        """Disconnect current camera.
        """
        if self.cam is not None:
            self.status(self.lib.Picam_CloseCamera(self.cam))
        self.cam = None
        self.errors.append("disconnected" + EOL)
        return None


    def getCurrentCameraID(self):
        """Returns the current camera ID (:py:class:`PicamCameraID`).
        """
        id = PicamCameraID()
        self.status(self.lib.Picam_GetCameraID(self.cam, ptr(id)))
        return id

    def getConstraintForParameter(self, name):
        ''' gets constraints for parameter "name" '''
        name = self.stripParameter(name)
        try:
            param = PicamParameter[name]
        except KeyError:
            return None
        
        # read / write access
        access = piint()
        self.status(self.lib.Picam_GetParameterValueAccess(self.cam, param, ptr(access)))
        readable = PicamValueAccessLookup[access.value]

        # constraints
        contype = piint()
        self.status(self.lib.Picam_GetParameterConstraintType(self.cam, param, ptr(contype)))
        t = None
        if PicamConstraintTypeLookup[contype.value] == "NA":
            constraint = None

        elif PicamConstraintTypeLookup[contype.value] == "None":
            constraint = "ALL"

        elif PicamConstraintTypeLookup[contype.value] == "Range":
            t = "Range"
            c = ptr(PicamRangeConstraint())
            self.status(self.lib.Picam_GetParameterRangeConstraint(self.cam, 
                        param, PicamConstraintCategory['Capable'], ptr(c)))

            constraint = (c[0].minimum, c[0].maximum, c[0].increment)

            self.lib.Picam_DestroyRangeConstraints(c)

        elif PicamConstraintTypeLookup[contype.value] == "Collection":
            t = "Collection"
            c = ptr(PicamCollectionConstraint())
            self.status(self.lib.Picam_GetParameterCollectionConstraint(self.cam, param, 
                                        PicamConstraintCategory['Capable'], ptr(c)))

            constraint = []
            for j in range(c[0].values_count):
                if constraint != "":
                    constraint.append(c[0].values_array[j])

            self.lib.Picam_DestroyCollectionConstraints(c)

        elif PicamConstraintTypeLookup[contype.value] == "Rois":
            constraint = None
        elif PicamConstraintTypeLookup[contype.value] == "Pulse":
            constraint = None
        elif PicamConstraintTypeLookup[contype.value] == "Modulations":
            constraint = None
        return (readable, constraint, self.getParameterType())

    # prints a list of parameters that are available
    def printAvailableParameters(self):
        """Prints an overview over the parameters to stdout that are available for the current camera and their limits.
        """
        parameter_array = ptr(piint())
        parameter_count = piint()
        self.lib.Picam_GetParameters(self.cam, ptr(parameter_array), ptr(parameter_count))

        ret = ''
        for i in range(parameter_count.value):

            # read / write access
            access = piint()
            self.lib.Picam_GetParameterValueAccess(self.cam, parameter_array[i], ptr(access))
            readable = PicamValueAccessLookup[access.value]

            # constraints
            contype = piint()
            self.lib.Picam_GetParameterConstraintType(self.cam, parameter_array[i], ptr(contype))

            if PicamConstraintTypeLookup[contype.value] == "None":
                constraint = "ALL"

            elif PicamConstraintTypeLookup[contype.value] == "Range":

                c = ptr(PicamRangeConstraint())
                self.lib.Picam_GetParameterRangeConstraint(self.cam, parameter_array[i], PicamConstraintCategory['Capable'], ptr(c))

                constraint = "from %f to %f in steps of %f" % (c[0].minimum, c[0].maximum, c[0].increment)

                self.lib.Picam_DestroyRangeConstraints(c)

            elif PicamConstraintTypeLookup[contype.value] == "Collection":

                c = ptr(PicamCollectionConstraint())
                self.lib.Picam_GetParameterCollectionConstraint(self.cam, parameter_array[i], PicamConstraintCategory['Capable'], ptr(c))

                constraint = ""
                for j in range(c[0].values_count):
                    if constraint != "":
                        constraint += ", "
                    constraint += str(c[0].values_array[j])

                self.lib.Picam_DestroyCollectionConstraints(c)

            elif PicamConstraintTypeLookup[contype.value] == "Rois":
                constraint = "N.A."
            elif PicamConstraintTypeLookup[contype.value] == "Pulse":
                constraint = "N.A."
            elif PicamConstraintTypeLookup[contype.value] == "Modulations":
                constraint = "N.A."

            # print infos
            try:
                ret += f"{PicamParameterLookup[parameter_array[i]]}" + EOL
                ret += f" value access:{readable}" + EOL
                ret += f" allowed values:{constraint}" + EOL
                ret += EOL
            except KeyError:
                self.errors.append(f"ERROR: key {parameter_array[i]} does not exists in lookup table" + EOL)
                self.errors.append(f" value access:{readable}" + EOL)
                self.errors.append(f" allowed values:{constraint}" + EOL)
                self.errors.append(EOL)

        self.lib.Picam_DestroyParameters(parameter_array)
        return ret
    
    def stripParameter(self, param):
        if param[3] == '_':
            param = param[4:]
        return param
        
    def parameterExists(self, parameter):
        parameter = self.stripParameter(parameter)
        return parameter in PicamParameter.keys()

    # get / set parameters
    # name is a string specifying the parameter
    def getParameter(self, name, giveType=False):
        """Reads and returns the value of the parameter with given name. If there is no parameter of this name, the function returns None and prints a warning.

        :param str name: Name of the parameter exactly as stated in the PICam SDK manual.
        :returns: Value of this parameter with data type corresponding to the type of parameter.
        """
        name = self.stripParameter(name)
        prm = PicamParameter[name]
        self.paraType = ''
        exists = pibln()
        self.status(self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists)))
        ret = ''
        if not exists.value:
            ret += f"Ignoring parameter{name}" + EOL
            ret += f"  Parameter does not exist for current camera!" + EOL
            self.errors.append(ret)
            return False

        # get type of parameter
        type = piint()
        self.status(self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type)))

        if type.value not in PicamValueTypeLookup:
            ret += f"Not a valid parameter type enumeration:{type.value}" + EOL
            ret += f"Ignoring parameter {name}" + EOL
            self.errors.append(ret)
            return False

        if PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = piint()

            self.paraType = 'c_long'
            if PicamValueTypeLookup[type.value] in ["Boolean"]:
                self.paraType = 'c_bool'
            # test whether we can read the value directly from hardware
            cr = pibln()
            self.status(self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr)))
            if cr.value:
                if self.lib.Picam_ReadParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    if giveType:
                        return val
                    return val.value
            else:
                if self.lib.Picam_GetParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    if giveType:
                        return val
                    return val.value

        if PicamValueTypeLookup[type.value] == "LargeInteger":
            val = pi64s()
            self.paraType = 'c_longlong'
            if self.lib.Picam_GetParameterLargeIntegerValue(self.cam, prm, ptr(val)) == 0:
                if giveType:
                        return val
                return val.value

        if PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = piflt()

            # NEW
            # test whether we can read the value directly from hardware
            cr = pibln()
            self.status(self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr)))
            self.paraType = 'c_float'
            if cr.value:
                if self.lib.Picam_ReadParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    if giveType:
                        return val
                    return val.value
            else:
                if self.lib.Picam_GetParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    if giveType:
                        return val
                    return val.value

        if PicamValueTypeLookup[type.value] == "Rois":
            val = ptr(PicamRois())
            self.paraType = 'rois'
            if self.lib.Picam_GetParameterRoisValue(self.cam, prm, ptr(val)) == 0:
                self.roisPtr.append(val)
                return val.contents

        if PicamValueTypeLookup[type.value] == "Pulse":
            val = ptr(PicamPulse())
            self.paraType = 'pulse'
            if self.lib.Picam_GetParameterPulseValue(self.cam, prm, ptr(val)) == 0:
                self.pulsePtr.append(val)
                return val.contents

        if PicamValueTypeLookup[type.value] == "Modulations":
            val = ptr(PicamModulations())
            self.paraType = 'modulations'
            if self.lib.Picam_GetParameterModulationsValue(self.cam, prm, ptr(val)) == 0:
                self.modPtr.append(val)
                return val.contents

        return True

    def getParameterType(self):
        return self.paraType
    
    def setParameter(self, name, value):
        """Set parameter. The value is automatically typecast to the correct data type corresponding to the type of parameter.

        .. note:: Setting a parameter with this function does not automatically change the configuration in the camera. In order to apply all changes, :py:func:`sendConfiguration` has to be called.

        :param str name: Name of the parameter exactly as stated in the PICam SDK manual.
        :param mixed value: New parameter value. If the parameter value cannot be changed, a warning is printed to stdout.
        """
        name = self.stripParameter(name)
        prm = PicamParameter[name]
        exists = pibln()
        self.status(self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists)))
        ret = ''
        if not exists:
            ret += f"Ignoring parameter{name}" + EOL
            ret += f"  Parameter does not exist for current camera!" + EOL
            self.errors.append(ret)
            return None

        access = piint()
        self.status(self.lib.Picam_GetParameterValueAccess(self.cam, prm, ptr(access)))
        if PicamValueAccessLookup[access.value] not in ["ReadWrite", "ReadWriteTrivial"]:
            ret += f"Ignoring parameter{name}" + EOL
            ret += f"  Not allowed to overwrite parameter!" + EOL
            self.errors.append(ret)
            return None
        if PicamValueAccessLookup[access.value] == "ReadWriteTrivial":
            ret += f"WARNING: Parameter {name} allows only one value!" + EOL

        # get type of parameter
        type = piint()
        self.status(self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type)))
        if type.value not in PicamValueTypeLookup:
            ret += f"Ignoring parameter{name}" + EOL
            ret += f"  Not a valid parameter type:{type.value}" + EOL
            self.errors.append(ret)
            return None

        if PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = piint(int(value))
            self.status(self.lib.Picam_SetParameterIntegerValue(self.cam, prm, val))

        if PicamValueTypeLookup[type.value] == "LargeInteger":
            # val = pi64s(long(value))
            val = pi64s(int(value)) # long does not exist on python 3.x (automatically long if overflow)
            self.status(self.lib.Picam_SetParameterLargeIntegerValue(self.cam, prm, val))

        if PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = piflt(float(value))
            self.status(self.lib.Picam_SetParameterFloatingPointValue(self.cam, prm, val))
            
        if PicamValueTypeLookup[type.value] == "Rois":
            self.status(self.lib.Picam_SetParameterRoisValue(self.cam, prm, ptr(value)))

        if PicamValueTypeLookup[type.value] == "Pulse":
            self.status(self.lib.Picam_SetParameterPulseValue(self.cam, prm, ptr(value)))

        if PicamValueTypeLookup[type.value] == "Modulations":
            self.status(self.lib.Picam_SetParameterModulationsValue(self.cam, prm, ptr(value)))

        if self.err != PicamError["None"]:
            ret += f"Ignoring parameter{name}" + EOL
            ret += f"  Could not change parameter. Keeping previous value:{self.getParameter(name)}" + EOL
            self.errors.append(ret)
            return None
        return None
    
    # this function has to be called once all configurations
    # are done to apply settings to the camera
    def sendConfiguration(self):
        """This function has to be called once all configurations are done to apply settings to the camera.
        """
        failed = ptr(piint())
        failedCount = piint()

        self.status(self.lib.Picam_CommitParameters(self.cam, ptr(failed), ptr(failedCount)))

        rejected = [PicamParameterLookup.get(failed[i], str(failed[i]))
                    for i in range(failedCount.value)]
        self.status(self.lib.Picam_DestroyParameters(failed))
        if rejected:
            raise RuntimeError("Camera rejected parameters: " + ", ".join(rejected))
        
        self.updateROIS()
        self.framecount.value = 0
        self.messages.append("Configuration sent." + EOL)
        return None

    # this function has to be called to commit single parameters durin acquisition.
    # i.e. ExposureTime
    def commitSimple(self):
        """This function has to be called to commit single parameters durin acquisition.
        """
        failed = ptr(piint())
        failedCount = piint()

        self.status(self.lib.Picam_CommitParameters(self.cam, ptr(failed), ptr(failedCount)))

        if failedCount.value > 0:
            for i in range(failedCount.value):
                self.errors.append("Could not set parameter {PicamParameterLookup[failed[i]]}" + EOL)
        self.status(self.lib.Picam_DestroyParameters(failed))

        self.messages.append("Parameter sent." + EOL)
        return None

    # utility function that extracts the number of pixel sizes of all ROIs
    def updateROIS(self):
        """Internally used utility function to extract a list of pixel sizes of ROIs.
        """
        self.ROIS = []
        self.ROISAll = []
        rois = self.getParameter("Rois")
        self.totalFrameSize = 0
        offs = 0
        for i in range(rois.roi_count):
            xo = rois.roi_array[i].x
            yo = rois.roi_array[i].y
            wo = rois.roi_array[i].width
            ho = rois.roi_array[i].height
            xbo = rois.roi_array[i].x_binning
            ybo = rois.roi_array[i].y_binning
            w = int(np.ceil(float(rois.roi_array[i].width) / float(rois.roi_array[i].x_binning)))
            h = int(np.ceil(float(rois.roi_array[i].height) / float(rois.roi_array[i].y_binning)))
            self.ROIS.append((w, h, offs))
            self.ROISAll.append((xo, wo, xbo, yo, ho, ybo, w, h, offs))
            offs = offs + w * h
        self.totalFrameSize = offs
        self.messages.append(f'total frame size: {offs} pixels' + EOL)
        return None

    # set a single ROI
    def setROI(self, x0, w, xbin, y0, h, ybin):
        """Create a single region of interest (ROI).

        :param int x0: X-coordinate of upper left corner of ROI.
        :param int w: Width of ROI.
        :param int xbin: X-Binning, i.e. number of columns that are combined into one larger column (1 to w).
        :param int y0: Y-coordinate of upper left corner of ROI.
        :param int h: Height of ROI.
        :param int ybin: Y-Binning, i.e. number of rows that are combined into one larger row (1 to h).
        """
        r = PicamRoi(x0, w, xbin, y0, h, ybin)
        R = PicamRois(ptr(r), 1)
        ret = self.setParameter("Rois", R)
        self.updateROIS()
        self.errors.append(ret)
        return ret

    # add a ROI
    def addROI(self, x0, w, xbin, y0, h, ybin):
        """Add a region-of-interest to the existing list of ROIs.

        .. important:: The ROIs should not overlap! However, this function does not check for overlapping ROIs!

        :param int x0: X-coordinate of upper left corner of ROI.
        :param int w: Width of ROI.
        :param int xbin: X-Binning, i.e. number of columns that are combined into one larger column (1 to w).
        :param int y0: Y-coordinate of upper left corner of ROI.
        :param int h: Height of ROI.
        :param int ybin: Y-Binning, i.e. number of rows that are combined into one larger row (1 to h).
        """
        # read existing rois
        R = self.getParameter("Rois")
        r0 = (PicamRoi * (R.roi_count + 1))()
        for i in range(R.roi_count):
            r0[i] = R.roi_array[i]

        # add new roi
        r0[-1] = PicamRoi(x0, w, xbin, y0, h, ybin)
        # write back to camera
        R1 = PicamRois(ptr(r0[0]), len(r0))
        ret = self.setParameter("Rois", R1)
        self.errors.append(ret)
        self.updateROIS()
        return ret

    # get rois
    def getRois(self):
        R = self.getParameter("Rois")
        return R
        
    # acquisition functions
    # readNFrames waits till all frames have been collected (using Picam_Acquire)
    # N = number of frames
    # timeout = max wait time between frames in ms
    def readNFrames(self, N=1, timeout=5000000, framed=0):
        """This function acquires N frames using Picam_Acquire. It waits till all frames have been collected before it returns.

        :param int N: Number of frames to collect (>= 1, default=1). This number is essentially limited by the available memory.
        :param float timeout: Maximum wait time between frames in milliseconds (default=100). This parameter is important when using external triggering.
        :returns: List of acquired frames.
        """
        # global cam
        
        available = PicamAvailableData()
        errors = piint()

        running = pibln()
        self.status(self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running)))
        if running.value:
            raise RuntimeError("PICam acquisition is already running")

        # start acquisition
        ret = "start acquisition" + EOL
        self.status(self.lib.Picam_Acquire(self.cam, pi64s(N), piint(timeout), ptr(available), ptr(errors)))
        ret += f"Acquisition error mask: {errors.value}" + EOL
        ret += "end acquisition" + EOL
        self.errors.append(ret)
        if errors.value:
            raise RuntimeError(f"PICam acquisition error mask: {errors.value}")
        # return data as numpy array
        if available.readout_count >= N:
            if framed == 0:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)
            if len(self.ROIS) == 1:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)[0:N]
            else:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)[:][0:N]
        raise RuntimeError("PICam returned fewer readouts than requested")

    # this is a helper function that converts a readout buffer into a sequence of numpy arrays
    # it reads all available data at once into a numpy buffer and reformats data to fit to the output mask
    # size is number of readouts to read
    # returns data as floating point

    # acquisition functions
    # starts acquisition and returns immediately (using Picam_StartAcquisition)
    # N = number of frames
    # 
    def startAcquisition(self, N=1):
        """This function acquires N frames using Picam_StartAcquisition.
        It does not wait for frames to be collected before it returns.

        :param int N: Number of frames to collect (>= 1, default=1). This number is essentially limited by the available memory.
        :returns: True --> Ok, False --> something went wrong.
        """
        # global cam

        running = pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        if running.value:
            self.errors.append("ERROR: acquisition still running" + EOL)
            return pibln(0)

        self.setParameter("ReadoutCount", N)
        # commit
        self.sendConfiguration()
        # start acquisition
        self.status(self.lib.Picam_StartAcquisition(self.cam))
        if self.err != PicamError["None"]:
           self.errors.append(f"ERROR: {self.err}" + EOL)
           return pibln(0)
        return pibln(1)


    # acquisition functions
    # starts acquisition and returns immediately (using Picam_StartAcquisition)
    # N = number of frames
    # 
    def startAsyncAcquisition(self, frames, mode='ModeNormal'):
        """This function acquires ReadoutCount frames using Picam_StartAcquisition.
        It does not wait for frames to be collected before it returns.

        :param string mode: !='ModeFocus' --> PiCam_ReadoutCount is used ; 'ModeFocus' --> infinite Nb (actually 10000 not exagerating)
        :returns: True --> Ok, False --> something went wrong.
        """
        running = pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        if running.value:
            self.errors.append("ERROR: acquisition still running" + EOL)
            return pibln(0)

        if mode == 'ModeFocus':
            self.setParameter("ReadoutCount", 10000)
        else:
            self.setParameter("ReadoutCount", frames)
        # commit
        self.sendConfiguration()
        # start acquisition
        self.status(self.lib.Picam_StartAcquisition(self.cam))
        if self.err != PicamError["None"]:
           self.errors.append(f"ERROR: {self.err}" + EOL)
           return pibln(0)
        return pibln(1)


    # acquisition functions
    # stops on the fly acquisition (using Picam_StopAcquisition) and waits until finished
    def stopAcquisition(self):
        running = pibln()
        self.status(self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running)))
        if running.value:
           self.status(self.lib.Picam_StopAcquisition( self.cam ))
        if self.err != PicamError["None"]:
           self.errors.append(f"ERROR: {self.err}" + EOL)
           return pibln(0)
        while running.value:
            self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        return pibln(1)

    # acquisition functions
    # readXFrames on the fly (using Picam_WaitForAcquisitionUpdate)
    # timeout = max wait time between frames in ms
    def readXFrames(self, timeout=100, framed=0):
        """This function acquires X frames using Picam_WaitForAcquisitionUpdate.

        :param float timeout: Maximum wait time between frames in milliseconds (default=100). This parameter is important when using external triggering.
        :returns: List of acquired frames.
        """
        # global cam
        
        available = PicamAvailableData()
        errors = piint()

        status = PicamAcquisitionStatus()
        
        self.status(self.lib.Picam_WaitForAcquisitionUpdate( self.cam, piint(timeout), ptr(available), ptr(status) ))

        if self.err != PicamError["None"]:
            self.errors.append("ERROR: Terminating prematurely!  Try increasing time out" + EOL)
            self.lib.Picam_StopAcquisition( self.cam );
            return []

        self.framecount.value += available.readout_count
        if available.readout_count > 0:
           # return data as numpy array
           if framed == 0:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)
           if len(self.ROIS) == 1:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)[0:available.readout_count]
           else:
                return self.getBuffer(available.initial_readout, available.readout_count, framed)[:][0:available.readout_count]
        return []


    # this is a helper function that converts a readout buffer into a sequence of numpy arrays
    # it reads all available data at once into a numpy buffer and reformats data to fit to the output mask
    # size is number of readouts to read
    # returns data as floating point

    def getBuffer(self, address, size, framed):
        """This is an internally used function to convert the readout buffer into a sequence of numpy arrays.
        It reads all available data at once into a numpy buffer and reformats data to a usable format.

        :param long address: Memory address where the readout buffer is stored.
        :param int size: Number of readouts available in the readout buffer.
        :returns: List of ROIS; for each ROI, array of readouts; each readout is a NxM array.
        """
        # get number of pixels contained in a single readout and a single frame
        # parameters are bytes, a pixel in resulting array is 2 bytes
        readoutstride = int(self.getParameter("ReadoutStride") / 2)
        framestride = int(self.getParameter("FrameStride") / 2)
        frames = int(self.getParameter("FramesPerReadout"))

        # create a pointer to data
        dataArrayType = pi16u * readoutstride * size
        dataArrayPointerType = ctypes.POINTER(dataArrayType)
        dataPointer = ctypes.cast(address, dataArrayPointerType)

        # create a numpy array from the buffer
        ret = "creating buffer" + EOL
        data = np.frombuffer(dataPointer.contents, dtype='uint16')

        if framed == 0:
            ret += "returning data" + EOL
            self.messages.append(ret)
            return (data, readoutstride, size)

        # cast it into a usable format - [frames][data]
        ret += "reshape data" + EOL
        data = ((data.reshape(size, readoutstride)[:, :frames * framestride]).reshape(size, frames, framestride)[:, :, :self.totalFrameSize]).reshape(size * frames, self.totalFrameSize).astype(float)

        # if there is just a single ROI, we are done
        if len(self.ROIS) == 1:
            ret += "returning data" + EOL
            self.messages.append(ret)
            return [data.reshape(size * frames, self.ROIS[0][0], self.ROIS[0][1])]

        # otherwise, iterate through rois and add to output list (has to be list due to possibly different sizes)
        out = []
        for i, r in enumerate(self.ROIS):
            out.append(data[:, r[2]:r[0] * r[1] + r[2]])
            ret += f"returning data[{i}]" + EOL
        self.messages.append(ret)
        return out

    def nicePrintText(self, newmessage=None):
        errors = [x for x in self.errors if x is not None]
        error = "".join(errors)
        self.errors = []
        message = "".join(self.messages)
        self.messages = []
        if error is None:
            error = ''
        if message is None:
            message = ''
        error += message
        if newmessage is None:
            newmessage = ''
        if isinstance(newmessage, str):
            error += newmessage
        elif isinstance(newmessage, pibln):
            pass
        else:
            print(newmessage)
            print(error)
        return error
    
    def nicePrintHTML(self, newmessage=None):
        errors = [x for x in self.errors if x is not None]
        error = "".join(errors)
        self.errors = []
        message = "".join(self.messages)
        self.messages = []
        if error != "" and error is not None:
            error = '<span style=\"color: red; font-size:12px; font-family:Times; font-style: italic; bold; \">{}</span>'.format(error)
        else:
            error = ""
        if message != "" and message is not None:
            error += '<span style=\"color: green; font-size:12px; font-family:Times; font-style: italic; bold; \">{}</span>'.format(message)

        if isinstance(newmessage, str):
            if newmessage != "" and newmessage is not None:
                error = '<span style=\"color: blue; font-size:12px; font-family:Times; \">{}</span>'.format(newmessage) + error
        elif isinstance(newmessage, pibln):
            pass
        else:
            pass
            # print(newmessage)
            # print(error)
        return error

    def nicePrint(self, newmessage):
        if EOL == '\n':
            ret = self.nicePrintText(newmessage)
        else:
            ret = self.nicePrintHTML(newmessage)
        if ret is not None and ret != '':
            return ret
        

if __name__ == '__main__':

    cam = picam()
    #cam.nicePrint(cam.loadLibrary('.\DLLs\Picam.dll'))
    cam.nicePrint(cam.loadLibrary())
    cam.nicePrint(cam.initLibrary())
    cam.nicePrint(cam.getAvailableCameras())
    cam.nicePrint(cam.connect())
    # à enlever
    cam.nicePrint(cam.uninitLibrary())
    exit(0)
    # cool down CCD
    cam.nicePrint(cam.setParameter("SensorTemperatureSetPoint", -75))

    # shortest expoure
    cam.nicePrint(cam.setParameter("ExposureTime", 0))

    # readout mode
    cam.nicePrint(cam.setParameter("ReadoutControlMode", PicamReadoutControlMode["FullFrame"]))

    # custom chip settings
    cam.nicePrint(cam.setROI(0, 1340, 1, 0, 1, 1))
    cam.nicePrint(cam.setParameter("ActiveWidth", 1340))
    cam.nicePrint(cam.setParameter("ActiveHeight", 100))
    cam.nicePrint(cam.setParameter("ActiveLeftMargin", 0))
    cam.nicePrint(cam.setParameter("ActiveRightMargin", 0))
    cam.nicePrint(cam.setParameter("ActiveTopMargin", 8))
    cam.nicePrint(cam.setParameter("ActiveBottomMargin", 8))
    cam.nicePrint(cam.setParameter("VerticalShiftRate", 3.2))    # select fastest

    # set logic out to not ready
    cam.nicePrint(cam.setParameter("OutputSignal", PicamOutputSignal["Busy"]))

    # shutter delays; open before trigger corresponds to shutter opening pre delay
    cam.nicePrint(cam.setParameter("ShutterTimingMode", PicamShutterTimingMode["Normal"]))
    cam.nicePrint(cam.setParameter("ShutterClosingDelay", 0))

    # sensor cleaning
    cam.nicePrint(cam.setParameter("CleanSectionFinalHeightCount", 1))
    cam.nicePrint(cam.setParameter("CleanSectionFinalHeight", 100))
    cam.nicePrint(cam.setParameter("ExposureTime", 100))
    cam.nicePrint(cam.setParameter("CleanSerialRegister", False))
    cam.nicePrint(cam.setParameter("CleanCycleCount", 1))
    cam.nicePrint(cam.setParameter("CleanCycleHeight", 100))
    cam.nicePrint(cam.setParameter("CleanUntilTrigger", True))

    # sensor gain settings
    # according to manual, Pixis supports 100kHz and 2MHz; select fastest
    cam.nicePrint(cam.setParameter("AdcSpeed", 2.0))
    cam.nicePrint(cam.setParameter("AdcAnalogGain", PicamAdcAnalogGain["Low"]))
    cam.nicePrint(cam.setParameter("AdcQuality", PicamAdcQuality["HighCapacity"]))

    # trigger and timing settings
    cam.nicePrint(cam.setParameter("TriggerDetermination", PicamTriggerDetermination["PositivePolarity"]))
    cam.nicePrint(cam.setParameter("TriggerResponse", PicamTriggerResponse["ReadoutPerTrigger"]))

    # send configuration
    cam.nicePrint(cam.sendConfiguration())

    # get readout speed
    print("Estimated readout time = %f ms" % cam.getParameter("ReadoutTimeCalculation"))
    cam.nicePrint(cam.readNFrames(N=3, timeout=10000, framed=1))
    
    print('parameters')
    print(cam.parameterExists('blabla'))
    print(cam.parameterExists('ExposureTime'))
    print('parameters')
    # cam.nicePrint(cam.printAvailableParameters())
    # cam.nicePrint(cam.disconnect())
    cam.nicePrint(cam.uninitLibrary())

'''
Here is some example code showing the necessary parameters to get 1 kHz readout rates on a PIXIS100::

    from picam import *

    # initialize camera class and connect to library, look for available camera and connect to first one
    cam = picam()
    cam.loadLibrary()
    cam.getAvailableCameras()
    cam.connect()

    # this will cool down CCD
    cam.setParameter("SensorTemperatureSetPoint", -75)

    # shortest expoure
    cam.setParameter("ExposureTime", 0)

    # readout mode
    cam.setParameter("ReadoutControlMode", PicamReadoutControlMode["FullFrame"])

    # custom chip settings
    cam.setROI(0, 1340, 1, 0, 100, 100)
    cam.setParameter("ActiveWidth", 1340)
    cam.setParameter("ActiveHeight", 100)
    cam.setParameter("ActiveLeftMargin", 0)
    cam.setParameter("ActiveRightMargin", 0)
    cam.setParameter("ActiveTopMargin", 8)
    cam.setParameter("ActiveBottomMargin", 8)
    cam.setParameter("VerticalShiftRate", 3.2)    # select fastest

    # set logic out to not ready
    cam.setParameter("OutputSignal", PicamOutputSignal["Busy"])

    # shutter delays; open before trigger corresponds to shutter opening pre delay
    cam.setParameter("ShutterTimingMode", PicamShutterTimingMode["Normal"])
    cam.setParameter("ShutterClosingDelay", 0)

    # sensor cleaning
    cam.setParameter("CleanSectionFinalHeightCount", 1)
    cam.setParameter("CleanSectionFinalHeight", 100)
    cam.setParameter("CleanSerialRegister", False)
    cam.setParameter("CleanCycleCount", 1)
    cam.setParameter("CleanCycleHeight", 100)
    cam.setParameter("CleanUntilTrigger", True)

    # sensor gain settings
    # according to manual, Pixis supports 100kHz and 2MHz; select fastest
    cam.setParameter("AdcSpeed", 2.0)
    cam.setParameter("AdcAnalogGain", PicamAdcAnalogGain["Low"])
    cam.setParameter("AdcQuality", PicamAdcQuality["HighCapacity"])

    # trigger and timing settings
    cam.setParameter("TriggerDetermination", PicamTriggerDetermination["PositivePolarity"])
    cam.setParameter("TriggerResponse", PicamTriggerResponse["ReadoutPerTrigger"])

    # send configuration
    cam.sendConfiguration()

    # get readout speed
    print "Estimated readout time = %f ms" % cam.getParameter("ReadoutTimeCalculation")

    cam.disconnect()
    cam.unloadLibrary()

'''
