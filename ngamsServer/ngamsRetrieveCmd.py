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
# "@(#) $Id: ngamsRetrieveCmd.py,v 1.17 2012/11/22 21:50:58 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  11/01/2002  Created
#

"""
Function + code to handle the RETRIEVE Command.
"""

import socket, re, glob, commands
import pcc, PccUtTime
from   ngams import *
import ngamsDb, ngamsLib, ngamsHighLevelLib
import ngamsDb, ngamsPlugInApi, ngamsFileInfo, ngamsDiskInfo, ngamsFileList
import ngamsDppiStatus, ngamsStatus, ngamsDiskUtils
import ngamsSrvUtils, ngamsFileUtils, ngamsReqProps


def performProcessing(srvObj,
                      reqPropsObj,
                      filename,
                      mimeType):
    """
    Carry out the processing requested.

    srvObj:       Reference to NG/AMS server class object (ngamsServer).   
    
    reqPropsObj:  Request Property object to keep track of actions done
                  during the request handling (ngamsReqProps).
        
    filename:     File to be processed (string).

    mimeType:     Mime-type of file (string).

    Returns:      List with ngamsDppiStatus object
                  (list/ngamsDppiStatus objects).
    """
    T = TRACE()
    
    statusObjList = []

    # Carry out the processing specified. If no processing is
    # specified, we simply set the source file as the file to be send.
    if (reqPropsObj.hasHttpPar("processing")):
        dppi = reqPropsObj.getHttpPar("processing")
        # Before starting to process, check if the specified DPPI
        # is supported by this NG/AMS.
        if (not srvObj.getCfg().hasDppiDef(dppi)):
            errMsg = genLog("NGAMS_ER_ILL_DPPI", [dppi])
            raise Exception, errMsg        
        # Invoke the DPPI.
        exec "import " + dppi
        info(2,"Invoking DPPI: " + dppi + " to process file: " + filename)
        statusObj = eval(dppi + "." + dppi + "(srvObj, reqPropsObj, filename)")
    else:
        info(2,"No processing requested - sending back file as is")
        resultObj = ngamsDppiStatus.ngamsDppiResult(NGAMS_PROC_FILE, mimeType,
                                                    filename, filename)
        statusObj = ngamsDppiStatus.ngamsDppiStatus().addResult(resultObj)
    statusObjList.append(statusObj)

    return statusObjList


def cleanUpAfterProc(statusObjList):
    """
    Clean up after processing. I.e., remove the directories created for
    holding the files being processed.

    statusObjList:   List of status objects as returned by
                     ngamsCmdHandling.performProcessing()
                     (list/ngamsDppiStatus objects).

    Returns:         Void.
    """
    T = TRACE()

    for statObj in statusObjList:
        for resObj in statObj.getResultList():
            if (resObj.getProcDir() != ""):
                info(3,"Cleaning up processing directory: " +\
                     resObj.getProcDir() + " after completed processing")
                ngamsPlugInApi.execCmd("rm -rf " + resObj.getProcDir())
    

def genReplyRetrieve(srvObj,
                     reqPropsObj,
                     httpRef,
                     statusObjList):
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
    T = TRACE()

    # Send back reply with the result queried.
    try:
        # TODO: Make possible to send back several results - use multipart
        # mime-type message -- for now only one result is sent back.
        resObj = statusObjList[0].getResultObject(0)

        mimeType = resObj.getMimeType()
        dataSize = resObj.getDataSize()
        refFilename = resObj.getRefFilename()
        startByte = reqPropsObj.getRange()
        info(3,"Sending data back to requestor. Reference filename: " +\
             refFilename + ". Start byte: " + str(startByte) + ", Size: " + str(dataSize - startByte))
        srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, None, 0,
                            mimeType, dataSize - startByte)
        contDisp = "attachment; filename=\"" + refFilename + "\""
        info(4,"Sending header: Content-disposition: " + contDisp)
        httpRef.send_header('Content-disposition', contDisp)
        # let the client know that the range header was accepted. We are not properly adhering to the HTTP spec.
        # we should really send back a HTTP/1.1 206 Partial content message
        httpRef.send_header("Accept-Ranges", "bytes")
        httpRef.wfile.write("\n")
        
        # Send back data from the memory buffer, from the result file, or
        # from HTTP socket connection.
        if (resObj.getObjDataType() == NGAMS_PROC_DATA):
            info(3,"Sending data in buffer to requestor ...")
            #httpRef.wfile.write(resObj.getDataRef())
            httpRef.wfile._sock.sendall(resObj.getDataRef())
        elif (resObj.getObjDataType() == NGAMS_PROC_FILE):
            info(3,"Reading data block-wise from file and sending " +\
                 "to requestor ...")
            fd = open(resObj.getDataRef())
            fd.seek(startByte)
            dataSent = startByte
            dataToSent = getFileSize(resObj.getDataRef())
            while (dataSent < dataToSent):
                tmpData = fd.read(srvObj.getCfg().getBlockSize())
                #os.write(httpRef.wfile.fileno(), tmpData)
                httpRef.wfile._sock.sendall(tmpData)
                dataSent += len(tmpData)
            info(3, 'Sent bytes: ' + str(dataSent))
        else:
            # NGAMS_PROC_STREAM - read the data from the File Object in
            # blocks and send it directly to the requestor.
            info(3,"Routing data from foreign location to requestor ...")
            dataSent = 0
            dataToSent = dataSize
            while (dataSent < dataToSent):
                tmpData = resObj.getDataRef().\
                          read(srvObj.getCfg().getBlockSize())
                #os.write(httpRef.wfile.fileno(), tmpData)
                httpRef.wfile._sock.sendall(tmpData)
                dataSent += len(tmpData)

        info(3,"HTTP reply sent to: " + str(httpRef.client_address))
        reqPropsObj.setSentReply(1)
    
        cleanUpAfterProc(statusObjList)
    except Exception, e:
        cleanUpAfterProc(statusObjList)
        raise e


def _handleRemoteIntFile(srvObj,
                         reqPropsObj,
                         httpRef):
    """
    Retrieve the remote, internal file and send it back to the requestor.

    srvObj:        Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:   Request Property object to keep track of actions done
                   during the request handling (ngamsReqProps).
    
    httpRef:       Reference to the HTTP request handler object
                   (ngamsHttpRequestHandler).

    Returns:       Void.
    """
    T = TRACE()
    
    forwardHost = reqPropsObj.getHttpPar("host_id")
    forwardPort = srvObj.getDb().getPortNoFromHostId(forwardHost)
    httpStatCode, httpStatMsg, httpHdrs, data =\
                  srvObj.forwardRequest(reqPropsObj, httpRef, forwardHost,
                                        forwardPort, autoReply = 1)

    
def _handleCmdRetrieve(srvObj,
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
    T = TRACE()
    
    # Get query information.
    if (reqPropsObj.hasHttpPar("ng_log")):
        if (reqPropsObj.hasHttpPar("host_id")):
            if (reqPropsObj.getHttpPar("host_id") != getHostId()):
                _handleRemoteIntFile(srvObj, reqPropsObj, httpRef)
                return 

        # If there is a Local Log File, send it back.
        locLogFile = srvObj.getCfg().getLocalLogFile()
        if (os.path.exists(locLogFile)):
            mimeType = NGAMS_TEXT_MT
            srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                                locLogFile, 1, mimeType)
            return
        else:
            errMsg = genLog("NGAMS_ER_UNAVAIL_FILE", ["ng_log: " + locLogFile])
            error(errMsg)
            raise Exception, errMsg
    elif (reqPropsObj.hasHttpPar("cfg")):
        if (reqPropsObj.hasHttpPar("host_id")):
            if (reqPropsObj.getHttpPar("host_id") != getHostId()):
                _handleRemoteIntFile(srvObj, reqPropsObj, httpRef)
                return 

        # Send back the file.
        srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                            srvObj.getCfg().getCfg(), 1, "text/xml")
        return
    elif (reqPropsObj.hasHttpPar("internal")):
        if (reqPropsObj.hasHttpPar("host_id")):
            if (reqPropsObj.getHttpPar("host_id") != getHostId()):
                _handleRemoteIntFile(srvObj, reqPropsObj, httpRef)
                return

        # Handle internal (local) non-archive file or send back directory
        # contents info.
        intPath = reqPropsObj.getHttpPar("internal")
        if (intPath.strip() == ""):
            raise Exception, "Illegal path specified for RETRIEVE?internal"

        # If specified path is a directory, return contents of the directory.
        if (os.path.isdir(intPath) or (intPath == "/")):
            info(2,"Querying info about directory: %s" % intPath)
            comment = "Info about folder: " + intPath
            fileListObj = ngamsFileList.ngamsFileList("DIR-INFO", comment,
                                                      NGAMS_SUCCESS)
            if (intPath[-1] != "/"): intPath += "/"
            globFileList = glob.glob(os.path.normpath(intPath + "*"))

            # To get the permissions, owner, group, access and modification
            # time we use 'ls -l' for now.
            # TODO: PORTABILITY ISSUE: Avoid usage of UNIX commands.
            lsCmd = "ls --full-time %s" % intPath
            stat, lsBuf = commands.getstatusoutput(lsCmd)
            dirInfoList = lsBuf.split("\n")
            dirDic = {}
            for dirInfo in dirInfoList[1:]:
                dirInfo = dirInfo.strip()
                dirEls = cleanList(dirInfo.split(" "))
                if (len(dirEls) != 9): continue
                # Example:
                # -rw-r----- 1 ngas ngas 102 2007-03-30 13:10:38.000 +0200 XX
                # -rw-rw-r-- 1 ngas ngas 488 Oct 26     14:50              YY
                entryName = os.path.normpath(intPath + dirEls[8])
                dirDic[entryName] = dirEls

            # Unpack the information about each entry.
            for filename in globFileList:
                if (filename[:-1] == intPath): continue
                statInfo = os.stat(filename)
                tmpFileObj = ngamsFileInfo.ngamsFileInfo().\
                             setFilename(os.path.normpath(filename)).\
                             setPermissions(dirDic[filename][0]).\
                             setOwner(dirDic[filename][2]).\
                             setGroup(dirDic[filename][3]).\
                             setAccDateFromSecs(statInfo[7]).\
                             setModDateFromSecs(statInfo[8]).\
                             setCreationDate(statInfo[9]).\
                             setFileSize(statInfo[6])
                fileListObj.addFileInfoObj(tmpFileObj)
            statObj = srvObj.genStatus(NGAMS_SUCCESS, "Successfully handled " +
                                       "RETRIEVE Command").\
                                       addFileList(fileListObj)
            xmlStat = ngamsHighLevelLib.\
                      addDocTypeXmlDoc(srvObj, statObj.genXmlDoc(0, 0, 1),
                                       NGAMS_XML_STATUS_ROOT_EL,
                                       NGAMS_XML_STATUS_DTD)
            srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                                xmlStat, 0, NGAMS_XML_MT, len(xmlStat), [], 1)
            return
    
        # Check that it is not tried to retrieve a data file in this way.
        # This is done by checking if the file is located in one of the
        # storage areas. Certain files like NgasDiskInfo, DB Snapshot Files,
        # ect., can be retrieved.
        complFilename = ngamsLib.locateInternalFile(intPath)
        diskIdsMtPts = srvObj.getDb().getDiskIdsMtPtsMountedDisks(getHostId())
        mountRtDir = srvObj.getCfg().getRootDirectory()
        for diskInfo in diskIdsMtPts:
            tmpDir   = os.path.normpath(diskInfo[1] + "/tmp/")
            cacheDir = os.path.normpath(diskInfo[1] + "/cache/")
            dbDir    = os.path.normpath(diskInfo[1] + "/.db/")
            if ((os.path.basename(complFilename) != NGAMS_DISK_INFO) and
                (os.path.basename(complFilename) != NGAMS_VOLUME_ID_FILE) and
                (os.path.basename(complFilename) != NGAMS_VOLUME_INFO_FILE) and
                (complFilename.find(tmpDir) == -1) and
                (complFilename.find(cacheDir) == -1) and
                (complFilename.find(dbDir) == -1) and
                (complFilename.find(diskInfo[1]) == 0)):
                errMsg = genLog("NGAMS_ER_ILL_RETRIEVE_REQ",
                                ["File requested appears to be an archived " +\
                                "data file. Retrieve these using the " +\
                                "RETRIEVE command + a combination of " +\
                                "File ID, File Version and Disk ID"])
                raise Exception, errMsg
        
        # OK, get the file and send it back.
        if ((complFilename.find(".xml") != -1) or
            (complFilename.find(".dtd") != -1) or
            (complFilename.find(NGAMS_DISK_INFO) != -1)):
            mimeType = "text/xml"
        elif (complFilename.find(".html") != -1):
            mimeType = "text/html"
        else:
            mimeType = ngamsHighLevelLib.\
                       determineMimeType(srvObj.getCfg(), complFilename, 1)
            if (mimeType == NGAMS_UNKNOWN_MT):
                # ".py", ...
                mimeType = NGAMS_TEXT_MT

        # Send back the file.
        srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                            complFilename, 1, mimeType)
        return

    # For data files, retrieval must be enabled otherwise the request is
    # rejected.
    if (not srvObj.getCfg().getAllowRetrieveReq()):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["Retrieve"])
        error(errMsg)
        raise Exception, errMsg
   
    # At least file_id must be specified if not an internal file has been
    # requested.
    issueRetCmdErr = 0
    if (not reqPropsObj.hasHttpPar("file_id")):
        issueRetCmdErr = 1
    else:
        if (reqPropsObj.getHttpPar("file_id").strip() == ""):
            issueRetCmdErr = 1
    if (issueRetCmdErr):
        errMsg = genLog("NGAMS_ER_RETRIEVE_CMD")
        error(errMsg)
        raise Exception, errMsg
    fileId = reqPropsObj.getHttpPar("file_id")
    info(3,"Handling request for file with ID: " + fileId)
    fileVer = -1
    if (reqPropsObj.hasHttpPar("file_version")):
        fileVer = int(reqPropsObj.getHttpPar("file_version"))
    diskId = ""
    if (reqPropsObj.hasHttpPar("disk_id")):
        diskId = reqPropsObj.getHttpPar("disk_id")
    hostId = ""
    if (reqPropsObj.hasHttpPar("host_id")):
        hostId = reqPropsObj.getHttpPar("host_id")    
    domain = ""
    if (reqPropsObj.hasHttpPar("domain")):
        domain = reqPropsObj.getHttpPar("domain")    
    quickLocation = False
    if (reqPropsObj.hasHttpPar("quick_location")):
        quickLocation = int(reqPropsObj.getHttpPar("quick_location"))

    # First try the quick retrieve attempt, just try to get the first
    # (and best?) suitable file which is online and located on a node in the
    # same domain as the contacted node.
    ipAddress = None
    if (quickLocation):
        info(3, 'trying a quick location of the file')
        location, host, ipAddress, port, mountPoint, filename,\
                  fileVersion, mimeType =\
                  ngamsFileUtils.quickFileLocate(srvObj, reqPropsObj, fileId,
                                                 hostId, domain, diskId,
                                                 fileVer)

    # If not located the quick way try the normal way.
    if (not ipAddress):
        info(3, 'trying a normal location of the file')
        # Locate the file best suiting the query and send it back if possible.
        location, host, ipAddress, port, mountPoint, filename, fileId,\
                  fileVersion, mimeType =\
                  ngamsFileUtils.locateArchiveFile(srvObj, fileId, fileVer,
                                                   diskId, hostId, reqPropsObj)

    # If still not located, try to contact associated NGAS sites to query
    # if the file is available there.
    # TODO:
    if (not ipAddress):
        pass

    if (location == NGAMS_HOST_LOCAL):
        # Get the file and send back the contents from this NGAS host.
        srcFilename = os.path.normpath(mountPoint + "/" + filename)
        # Perform the possible processing requested.
        procResult = performProcessing(srvObj,reqPropsObj,srcFilename,mimeType)
    elif (((location == NGAMS_HOST_CLUSTER) or \
           (location == NGAMS_HOST_REMOTE)) and \
           srvObj.getCfg().getProxyMode()):

        info(3,"NG/AMS Server acting as proxy - requesting file with ID: " +\
             fileId + " from NG/AMS Server on host/port: " + host + "/" +\
             str(port) + " ...")

        # Act as proxy - get the file from the NGAS host specified and
        # send back the contents. The file is temporarily stored in the
        # Processing Area.
        procDir = ngamsHighLevelLib.genProcDirName(srvObj.getCfg())
        checkCreatePath(procDir)
        pars = []
        for par in reqPropsObj.getHttpParNames():
            if (par != "initiator"):
                pars.append([par, reqPropsObj.getHttpPar(par)])
        authHdr = ngamsSrvUtils.genIntAuthHdr(srvObj)
        httpStatCode, httpStatMsg, httpHdrs, data =\
                      ngamsLib.httpGet(ipAddress, port, NGAMS_RETRIEVE_CMD, 1,
                                       pars,"",srvObj.getCfg().getBlockSize(),
                                       timeOut = None, returnFileObj = 1,
                                       authHdrVal = authHdr)
        httpHdrDic = ngamsLib.httpMsgObj2Dic(httpHdrs)
        dataSize = int(httpHdrDic["content-length"])
        
        # Check that the Retrieve Request was successful.
        try:
            tmpStatObj = ngamsStatus.ngamsStatus().\
                         unpackXmlDoc(data, getStatus=1)
        except Exception, e:
            # Data was not a NG/AMS XML Status Document.
            tmpStatObj = None
            pass
        if (tmpStatObj):
            if (tmpStatObj.getStatus() == NGAMS_FAILURE):
                raise Exception, tmpStatObj.getMessage()
        
        tmpPars = ngamsLib.parseHttpHdr(httpHdrDic["content-disposition"])
        dataFilename = tmpPars["filename"]
        
        # Generate fake ngamsDppiStatus object.
        resultObj = ngamsDppiStatus.ngamsDppiResult(NGAMS_PROC_STREAM,
                                                    mimeType, data,
                                                    dataFilename, procDir,
                                                    dataSize)
        procResult = [ngamsDppiStatus.ngamsDppiStatus().addResult(resultObj)]
    else:
        # No proxy mode: A redirection HTTP response is generated.
        srvObj.httpRedirReply(reqPropsObj, httpRef, ipAddress, port)
        return

    # Send back reply with the result(s) queried and possibly processed.
    genReplyRetrieve(srvObj, reqPropsObj, httpRef, procResult)
    

def handleCmdRetrieve(srvObj,
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
    T = TRACE()
    
    # If an internal file is retrieved we allow to handle the request also
    # when the system is Offline (for trouble-shooting purposes).
    if ((not reqPropsObj.hasHttpPar("internal")) and
        (not reqPropsObj.hasHttpPar("ng_log")) and
        (not reqPropsObj.hasHttpPar("cfg"))):
        srvObj.checkSetState("Command RETRIEVE", [NGAMS_ONLINE_STATE],
                             [NGAMS_IDLE_SUBSTATE, NGAMS_BUSY_SUBSTATE],
                             "", NGAMS_BUSY_SUBSTATE)

    # Check if processing is requested if this systems allows processing.
    if (reqPropsObj.hasHttpPar("processing") and \
        (not srvObj.getCfg().getAllowProcessingReq())):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["Retrieve+Processing"])
        error(errMsg)
        srvObj.setSubState(NGAMS_IDLE_SUBSTATE)
        raise Exception, errMsg
    try:
        _handleCmdRetrieve(srvObj, reqPropsObj, httpRef)
    except Exception, e:
        error(str(e))
        raise Exception, e
    finally:
        srvObj.setSubState(NGAMS_IDLE_SUBSTATE)  

# EOF
