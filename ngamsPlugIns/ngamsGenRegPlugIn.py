#
#    ALMA - Atacama Large Millimiter Array
#    (c) European Southern Observatory, 2002
#    Copyright by ESO (in the framework of the ALMA collaboration),
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#

#******************************************************************************
#
# "@(#) $Id: ngamsGenRegPlugIn.py,v 1.2 2012/03/03 21:18:17 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jagonzal  199/01/2011  Created
#

"""
This Data Register Plug-In is used to generically handle the registration of files
already stored on an 'NGAS disk', which just need to be registered in the DB.

Note, that the plug-in is implemented for the usage at ESO. If used in other
contexts, a dedicated plug-in matching the individual context should be
implemented and NG/AMS configured to use it.
"""

import os, string
from   ngams import *
import ngamsPlugInApi, ngamsDiskUtils, ngamsDiskInfo, ngamsLib

# Data Registration Function.
def ngamsGenRegPlugIn(srvObj,
                      reqPropsObj):
    """
    Data Registration Plug-In to handle registration of FITS files.

    srvObj:       Reference to NG/AMS Server Object (ngamsServer).
    
    reqPropsObj:  NG/AMS request properties object (ngamsReqProps).

    Returns:      Standard NG/AMS Data Archiving Plug-In Status as generated
                  by: ngamsPlugInApi.genDapiSuccessStat() (ngamsDapiStatus).
    """
    info(1,"Plug-In registering file with URI: " + reqPropsObj.getFileUri())
    diskInfo = reqPropsObj.getTargDiskInfo()
    parDic = ngamsPlugInApi.parseRegPlugInPars(srvObj.getCfg(),
                                               reqPropsObj.getMimeType())
    stageFile = reqPropsObj.getStagingFilename()
    
    # Get file_id
    file_id = os.path.basename(reqPropsObj.getFileUri())
    file_id = file_id.split('.')
    file_id = file_id[0].replace(':','/')

    # Get mime type
    mimeTypeMappings = srvObj.getCfg().getMimeTypeMappings()
    format = ngamsLib.detMimeType(mimeTypeMappings,reqPropsObj.getFileUri(),1)
    if (format == NGAMS_UNKNOWN_MT): format = "multipart/related"

    # Get file_size
    file_size = ngamsPlugInApi.getFileSize(reqPropsObj.getFileUri())

    # Compression and uncompress file size
    compresion = "no"
    uncomprSize = file_size

    # Get various information about the file being handled
    fileVersion, relPath, relFilename,\
                 complFilename, fileExists =\
                 ngamsPlugInApi.genFileInfoReg(srvObj.getDb(), srvObj.getCfg(),
                                               reqPropsObj, diskInfo,
                                               stageFile, file_id)

    info(3,"Register Plug-In finished processing of file with URI %s: file_id=%s, file_version=%s, format=%s file_size=%s" \
            %(reqPropsObj.getFileUri(),file_id,fileVersion,format,file_size))

    return ngamsPlugInApi.genRegPiSuccessStat(diskInfo.getDiskId(),relFilename,
                                              file_id, fileVersion, format,
                                              file_size, uncomprSize,compresion,
                                              relPath, diskInfo.getSlotId(),
                                              fileExists, complFilename)


# EOF
