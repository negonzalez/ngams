#*******************************************************************************
# ALMA - Atacama Large Millimeter Array
# Copyright (c) ESO - European Southern Observatory, 2011
# (in the framework of the ALMA collaboration).
# All rights reserved.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#*******************************************************************************
#******************************************************************************
# ESO/DMD
#
# "@(#) $Id: ngamsFitsPlugIn.py,v 1.2 2011/11/24 13:06:42 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/05/2001  Created
#

"""
This Data Archiving Plug-In is used to handle reception and processing
of FITS files.

Note, that the plug-in is implemented for the usage at ESO. If used in other
contexts, a dedicated plug-in matching the individual context should be
implemented and NG/AMS configured to use it.
"""

import os, string
import PccUtTime
from   ngams import *
import ngamsPlugInApi, ngamsDiskUtils, ngamsDiskInfo


def getComprExt(comprMethod):
    """
    Determine the extension for the given type of compression specified.

    comprMethod:   Compression method e.g. 'compress' or 'gzip' (string).

    Returns:       Extension used by the given compression method (string).
    """
    if (comprMethod.find("compress") != -1):
        return "Z"
    elif (comprMethod.find("gzip") != -1):
        return "gz"
    else:
        errMsg = "Unknown compression method specified: " + comprMethod
        errMsg = genLog("NGAMS_ER_DAPI", [errMsg])
        raise Exception, errMsg


def getDpIdInfo(filename):
    """
    Generate the File ID (here DP ID) for the file.

    filename:   Name of FITS file (string).

    Returns:    Tuple containing the value of ARCFILE, the DP ID
                of the file, and the JD date. The two latter deducted from
                the ARCFILE keyword (tuple).
    """
    try:
        keyDic  = ngamsPlugInApi.getFitsKeys(filename, ["ARCFILE"])
        arcFile = keyDic["ARCFILE"][0]
        els     = string.split(arcFile, ".")
        dpId    = els[0] + "." + els[1] + "." + els[2]
        date    = string.split(els[1], "T")[0]
        # Make sure that the files are stored according to JD
        # (one night is 12am -> 12am).
        isoTime = els[1]
        ts1 = PccUtTime.TimeStamp(isoTime)
        ts2 = PccUtTime.TimeStamp(ts1.getMjd() - 0.5)
        dateDirName = string.split(ts2.getTimeStamp(), "T")[0]

        return [arcFile, dpId, dateDirName]
    except:
        err = "Did not find keyword ARCFILE in FITS file or ARCFILE illegal"
        errMsg = genLog("NGAMS_ER_DAPI_BAD_FILE", [os.path.basename(filename),
                                                   "ngamsFitsPlugIn", err])
        raise Exception, errMsg


def checkFitsFileSize(filename):
    """
    Check if the size of the FITS file is a multiple of 2880. If this
    is not the case, we through an exception.

    filename:   FITS file to check (string).

    Returns:    Void.
    """
    if (string.split(filename, ".")[-1] == "fits"):
        size = ngamsPlugInApi.getFileSize(filename)
        testVal = (size / 2880.0)
        if (testVal != int(testVal)):
            errMsg = "The size of the FITS file issued " +\
                     "is not a multiple of 2880! Rejecting file!"
            errMsg = genLog("NGAMS_ER_DAPI_BAD_FILE",
                            [os.path.basename(filename),
                             "ngamsFitsPlugIn", errMsg])
            raise Exception, errMsg


def checkChecksum(parDic,
                  filename):
    """
    Check that the checksum of the file is correct.

    parDic:    Dictionary with disk information (ngamsPhysDiskInfo objects)
               (dictionary).
    
    filename:  Name of FITS file (string).

    Returns:   Void.
    """
    # Only do check if the checksum_util parameter is set.
    if (not parDic.has_key("checksum_util")): return

    # Execute the checksum routine and evaluate result.
    info(2,"Invoking checksum test utility: " + parDic["checksum_util"] +\
         " on file: " + filename)
    res = ngamsPlugInApi.execCmd(parDic["checksum_util"] + " " + filename)
    if (int(res[0]) != 0):
        errMsg = "Problem occurred invoking checksum check utility: " +\
                 parDic["checksum_util"]
        errMsg = genLog("NGAMS_ER_DAPI", [errMsg])
        error(errMsg)
        raise Exception, errMsg
    if (res[1] != parDic["checksum_result"]):
        errMsg = "Executing checksum utility: " + parDic["checksum_util"] +\
                 " gave unexpected result. Result: [" + res[1] + "]. " +\
                 "Expected Result: [" + parDic["checksum_result"] + "]."
        errMsg = genLog("NGAMS_ER_DAPI_BAD_FILE", [filename, "ngamsFitsPlugIn",
                                                   errMsg])
        error(errMsg)
        raise Exception, errMsg
    

def prepFile(reqPropsObj,
             parDic):
    """
    Prepare the file. If it is compressed, decompress it into a temporary
    filename.

    reqPropsObj:  NG/AMS request properties object (ngamsReqProps).

    parDic:       Dictionary with parameters for the DAPI. This is generated
                  with ngamsPlugInApi.parseDapiPlugInPars() (Dictionary).

    Returns:      Tuple containing:

                    (<DP ID>, <Date Obs. Night>, <Compr. Ext.>)   (tuple).   
    """
    info(4,"ngamsFitsPlugIn: Entering prepFile() ...")
    
    # If the file is already compressed, we have to decompress it.
    tmpFn = reqPropsObj.getStagingFilename()
    if ((tmpFn.find(".Z") != -1) or (tmpFn.find(".gz") != -1)):
        ngamsPlugInApi.execCmd("gunzip " + tmpFn)
        reqPropsObj.setStagingFilename(os.path.splitext(tmpFn)[0])
    checkFitsFileSize(reqPropsObj.getStagingFilename())
    checkChecksum(parDic, reqPropsObj.getStagingFilename())
    if (parDic.has_key("compression")):
        comprExt = getComprExt(parDic["compression"])
    else:
        comprExt = ""
    dpIdInfo = getDpIdInfo(reqPropsObj.getStagingFilename())

    info(4,"ngamsFitsPlugIn: Leaving prepFile()")
    return dpIdInfo[1], dpIdInfo[2], comprExt


def compress(reqPropsObj,
             parDic):
    """
    Compress the file if required.

    reqPropsObj:  NG/AMS request properties object (ngamsReqProps).

    parDic:       Dictionary with parameters for the DAPI. This is generated
                  with ngamsPlugInApi.parseDapiPlugInPars() (Dictionary).

    Returns:      Tupe containing uncompressed filesize, archived filesize
                  and the format (mime-type) of the resulting data file
                  (tuple).   
    """
    stFn = reqPropsObj.getStagingFilename()

    # If a compression application is specified, apply this.
    uncomprSize = ngamsPlugInApi.getFileSize(stFn)
    if (parDic["compression"] != ""):
        info(2,"Compressing file using: " + parDic["compression"] + " ...")
        exitCode, stdOut =\
                  ngamsPlugInApi.execCmd(parDic["compression"] + " " + stFn)
        if (exitCode != 0):
            errMsg = "ngamsFitsPlugIn: Problems during archiving! " +\
                     "Compressing the file failed"
            raise Exception, errMsg
        
        stFn = stFn + "." + getComprExt(parDic["compression"])
        # Remember to update Staging Filename in the Request Properties Object.
        reqPropsObj.setStagingFilename(stFn)
        if (parDic["compression"].find("compress") != -1):
            format = "application/x-cfits"
        else:
            format = "application/x-gfits"
        info(2,"File compressed")
    else:
        format = reqPropsObj.getMimeType()
        
    archFileSize = ngamsPlugInApi.getFileSize(reqPropsObj.getStagingFilename())
    return uncomprSize, archFileSize, format


# DAPI function.
def ngamsFitsPlugIn(srvObj,
                    reqPropsObj):
    """
    Data Archiving Plug-In to handle archiving of FITS files.

    srvObj:       Reference to NG/AMS Server Object (ngamsServer).
    
    reqPropsObj:  NG/AMS request properties object (ngamsReqProps).

    Returns:      Standard NG/AMS Data Archiving Plug-In Status as generated
                  by: ngamsPlugInApi.genDapiSuccessStat() (ngamsDapiStatus).
    """
    info(1,"Plug-In handling data for file with URI: " +
         os.path.basename(reqPropsObj.getFileUri()))
    diskInfo = reqPropsObj.getTargDiskInfo()
    parDic = ngamsPlugInApi.parseDapiPlugInPars(srvObj.getCfg(),
                                                reqPropsObj.getMimeType())
    
    # Check file (size + checksum) + extract information.
    dpId, dateDirName, comprExt = prepFile(reqPropsObj, parDic)

    # Get various information about the file being handled.
    dpIdInfo = getDpIdInfo(reqPropsObj.getStagingFilename())
    dpId = dpIdInfo[1]
    dateDirName = dpIdInfo[2]
    fileVersion, relPath, relFilename,\
                 complFilename, fileExists =\
                 ngamsPlugInApi.genFileInfo(srvObj.getDb(), srvObj.getCfg(),
                                            reqPropsObj, diskInfo,
                                            reqPropsObj.getStagingFilename(),
                                            dpId, dpId, [dateDirName],
                                            [comprExt])

    # If a compression application is specified, apply this.
    uncomprSize, archFileSize, format = compress(reqPropsObj, parDic)

    # Generate status + return.
    info(3,"DAPI finished processing of file - returning to main application")
    return ngamsPlugInApi.genDapiSuccessStat(diskInfo.getDiskId(), relFilename,
                                             dpId, fileVersion, format,
                                             archFileSize, uncomprSize,
                                             parDic["compression"], relPath,
                                             diskInfo.getSlotId(), fileExists,
                                             complFilename)


# EOF
