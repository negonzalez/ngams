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
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# cmoins    25/03/2013  Created
#

"""
Function to perform a direct copy from ngas to a nfs mounted directory. 
Created for the needs of ticket COMP-7755:
RH: support direct to disk writing for pipeline access
"""

from ngams import *
import ngamsPlugInApi, ngamsDppiStatus
import os
import shutil


def ngamsBulkCopyDppi(srvObj,
                     reqPropsObj,
                     filename):

    """
    This plug-in performs the processing neccessary for the files
    requested from the Alma Archive through the Request Handler.

    srvObj:        Reference to instance of the NG/AMS Server
                   class (ngamsServer).
    
    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).
    
    filename:      Name of file to be stored on a disk (string).

    Returns:       DPPI return status object (ngamsDppiStatus).
    """
    statusObj = ngamsDppiStatus.ngamsDppiStatus()


    #the plug-in parameter is the destination file complete path
    if (reqPropsObj.hasHttpPar("processing_pars")):
       sub_dir = os.path.dirname(reqPropsObj.getHttpPar("processing_pars"))
       dest_file_name = os.path.basename(reqPropsObj.getHttpPar("processing_pars"))
    else:
       raise Exception, "No sub directory was provided"
    
    parDicOnline = ngamsPlugInApi.\
                   parseRawPlugInPars(srvObj.getCfg().getDppiPars("ngamsBulkCopyDppi"))

    if (not parDicOnline.has_key("root_download_dir")):
        raise Exception, "Missing Online Plug-In Parameter: root_download_dir=destination " +  str(ngamsPlugInApi.getDppiPars(srvObj.getCfg().getDppiPars("ngamsBulkCopyDppi")))
    else:
        root_download_dir = parDicOnline["root_download_dir"]

    # mounted directory is removed from the sub directory if present
    while ((os.path.exists(root_download_dir + "/" + sub_dir) == False) & (sub_dir != '')):
       sub_dir = sub_dir.partition("/")[2]

    dest_dir = root_download_dir + "/" + sub_dir 

    if (os.path.exists(dest_dir) == False):
       raise Exception, dest_dir + " is not a valid directory "

    if (os.path.exists(dest_dir) == False):
       raise Exception, "Missing directory " + dest_dir

    #performs the copy    
    try:
       shutil.copy(filename,dest_dir + "/" + dest_file_name)
    except IOError, (errno, strerror):
       raise Exception, "IOError: Could not copy " + filename + " to " + dest_dir + ": " + str(errno) + " " + strerror
          
    # the copy was sucessful. As a stream must be returned, an empty file will be returned
    notification_file =  os.path.basename(filename) + ".txt"                    
    procFilename, procDir = ngamsPlugInApi.prepProcFile(srvObj.getCfg(), notification_file)    
   
    mimeType = "text/plain"
    resObj = ngamsDppiStatus.ngamsDppiResult(NGAMS_PROC_FILE, mimeType,
                                             procFilename, procFilename, procDir)
    statusObj.addResult(resObj)

    return statusObj

# EOF
