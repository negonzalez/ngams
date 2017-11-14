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
# "@(#) $Id: ngamsCmd_RSYNC.py,v 1.1 2012/11/22 21:48:21 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  11/01/2002  Created
#

"""
Function + code to handle the RETRIEVE Command.
"""

from   ngams import *
import ngamsFileUtils
import subprocess

# does NOT currently support proxying / redirecting. Is not as flecible as the RETRIEVE command.
# the file must exist on the host to which this command was sent.
# for more flexibility it should be derived from ngamsRetrieveCmd - I don't need this right now
# for the ALMA mirroring

def genReplyRetrieve(srvObj,
                     reqPropsObj,
                     httpRef,
                     fileId,
                     fileLocation,
                     mimeType,
                     targetHost,
                     targetLocation):
    """
    Function to send back a reply with the result queried with the
    RETRIEVE command. After having send back the result, the
    processing areas may be cleaned up.

    srvObj:          Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:     Request Property object to keep track of
                     actions done during the request handling
                     (ngamsReqProps).
        
    httpRef:         Reference to the HTTP request handler
                     object (ngamsHttpRequestHandler).

    statusObjList:   List of status objects as returned by
                     ngamsCmdHandling.performProcessing()
                     (list/ngamsDppiStatus objects).

    Returns:         Void.
    """
    TRACE()

    # Send back reply with the result queried.
    try:
        transferFile(srvObj, fileLocation, targetHost, targetLocation)        
        info(3,"Sending data back to requestor. Reference filename: " +\
             fileId + ", Location: " + fileLocation)
    except Exception, e:
        raise e

def transferFile(srvObj, fileLocation, targetHost, targetLocation):
    options = '-P --append --inplace -e "ssh -o StrictHostKeyChecking=no"'
    if srvObj.getCfg().getVal("Mirroring[1].rsync_options"):
        options = srvObj.getCfg().getVal("Mirroring[1].rsync_options")
    fetchCommand = "rsync " + options + " " + fileLocation + " ngas@" + targetHost + ":" + targetLocation
    info(2, "sync command: " + fetchCommand)
    process = subprocess.Popen(fetchCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.communicate()
    if output[0] != '': info(2, 'RSYNC stdout: ' + output[0])
    if output[1] != '': error("RSYNC: " + output[1])
    result = process.wait()
    info(1, "finished command with status: " + str(result))
    
def _handleCmd(srvObj,
                       reqPropsObj,
                       httpRef):
    """
    Carry out the action of a RETRIEVE command.
    
    srvObj:         Reference to NG/AMS server class object (ngamsServer).
     
    reqPropsObj:    Request Property object to keep track of
                    actions done during the request handling
                    (ngamsReqProps).
        
    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).
        
    Returns:        Void.
    """
    TRACE()
    
    # For data files, retrieval must be enabled otherwise the request is
    # rejected.
    if (not srvObj.getCfg().getAllowRetrieveReq()):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["RSYNC"])
        error(errMsg)
        raise Exception, errMsg
   
    # At least file_id must be specified if not an internal file has been
    # requested.
    if (not reqPropsObj.hasHttpPar("file_id") or reqPropsObj.getHttpPar("file_id").strip() == ""):
        errMsg = "rquired parameter file_id is missing"
        error(errMsg)
        raise Exception, errMsg
    fileId = reqPropsObj.getHttpPar("file_id")
    if (not reqPropsObj.hasHttpPar("targetHost") or reqPropsObj.getHttpPar("targetHost").strip() == ""):
        errMsg = "rquired parameter targetHost is missing"
        error(errMsg)
        raise Exception, errMsg
    targetHost = reqPropsObj.getHttpPar("targetHost")
    if (not reqPropsObj.hasHttpPar("targetLocation") or reqPropsObj.getHttpPar("targetLocation").strip() == ""):
        errMsg = "rquired parameter targetLocation is missing"
        error(errMsg)
        raise Exception, errMsg
    targetLocation = reqPropsObj.getHttpPar("targetLocation")
    info(3,"Handling request for file with ID: " + fileId)
    fileVersion = -1
    if (reqPropsObj.hasHttpPar("file_version")):
        fileVersion = int(reqPropsObj.getHttpPar("file_version"))
    diskId = ""
    hostId = ""
    domain = ""

    # First try the quick retrieve attempt, just try to get the first
    # (and best?) suitable file which is online and located on a node in the
    # same domain as the contacted node.
    info(3, 'trying a quick location of the file')
    location, host, ipAddress, port, mountPoint, filename,\
                  fileVersion, mimeType =\
                  ngamsFileUtils.quickFileLocate(srvObj, reqPropsObj, fileId,
                                                 hostId, domain, diskId,
                                                 fileVersion)

    # Get the file and send back the contents from this NGAS host.
    fileLocation = os.path.normpath(mountPoint + "/" + filename)

    info(1, 'req props: ' + str(reqPropsObj))

    # Send back reply with the result(s) queried and possibly processed.
    genReplyRetrieve(srvObj, reqPropsObj, httpRef, fileId, fileLocation, mimeType, targetHost, targetLocation)
    

def handleCmd(srvObj,
                      reqPropsObj,
                      httpRef):
    """
    Handle a RETRIEVE command.
        
    srvObj:         Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:    Request Property object to keep track of
                    actions done during the request handling
                    (ngamsReqProps).
        
    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).
        
    Returns:        Void.
    """
    TRACE()
    
    # If an internal file is retrieved we allow to handle the request also
    # when the system is Offline (for trouble-shooting purposes).
    info(1, 'rsync')
    try:
        _handleCmd(srvObj, reqPropsObj, httpRef)
    except Exception, e:
        error(str(e))
        raise Exception, e
    finally:
        srvObj.setSubState(NGAMS_IDLE_SUBSTATE)  

# EOF
