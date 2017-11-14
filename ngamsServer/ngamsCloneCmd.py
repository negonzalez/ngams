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
# "@(#) $Id: ngamsCloneCmd.py,v 1.10 2012/11/22 21:48:52 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  21/03/2002  Created
#

"""
Contains utilities used in connection with the cloning of files.
"""

import urllib, thread, getpass, cPickle

import pcc, PccUtTime

from   ngams import *
import ngamsLib, ngamsDbm, ngamsFileList, ngamsStatus
import ngamsArchiveUtils, ngamsDiskUtils
import ngamsFileInfo, ngamsDiskInfo
import ngamsReqProps, ngamsHighLevelLib, ngamsDapiStatus
import ngamsNotification, ngamsSrvUtils, ngamsFileUtils
import ngamsCacheControlThread


def handleCmdClone(srvObj,
                   reqPropsObj,
                   httpRef):
    """
    Handle CLONE command.
        
    srvObj:         Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).
        
    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).
        
    Returns:        Void.
    """
    T = TRACE()

    # Is this NG/AMS permitted to handle Archive Requests?
    if (not srvObj.getCfg().getAllowArchiveReq()):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["Clone"])
        error(errMsg)
        raise Exception, errMsg

    # Check if State/Sub-State correct for perfoming the cloning.
    srvObj.checkSetState("Command CLONE", [NGAMS_ONLINE_STATE],
                         [NGAMS_IDLE_SUBSTATE, NGAMS_BUSY_SUBSTATE])

    # Get the parameters from the query.
    if (reqPropsObj.hasHttpPar("file_id")):
        fileId = reqPropsObj.getHttpPar("file_id")
    else:
        fileId =""
    if (reqPropsObj.hasHttpPar("disk_id")):
        diskId = reqPropsObj.getHttpPar("disk_id")
    else:
        diskId = ""
    if (reqPropsObj.hasHttpPar("file_version")):
        fileVersion = int(reqPropsObj.getHttpPar("file_version"))
    else:
        fileVersion = -1
    if (reqPropsObj.hasHttpPar("target_disk_id")):
        targetDiskId = reqPropsObj.getHttpPar("target_disk_id")
    else:
        targetDiskId = ""

    # Carry out the cloning.
    clone(srvObj, diskId, fileId, fileVersion,targetDiskId,reqPropsObj,httpRef)


def cloneCheckDiskSpace(srvObj,
                        cloneListDbmName,
                        tmpFilePat,
                        targetDiskId = ""):
    """
    Check if there is enough disk space available on this NGAS host for
    carrying out the Clone Request. 

    srvObj:           Reference to instance of Server Object (ngamsServer).

    cloneListDbmName: Name of DBM containing the information about
                      the files to be cloned. This DB has an index number
                      as key pointing to pickled information about each file.
                      This pickled information is

                        [<File Info Object>, <Host ID>, <Mount Point>]
                       
                      (string)
                     
    tmpFilePat:       File pattern to be used for generating temporary
                      files (string).

    targetDiskId:     ID of disk to where the files cloned should be
                      written (string).
   
    Returns:          Void.
    """
    T = TRACE()
    
    # Make a dictionary with the available amount of space per disk.
    info(4,"Generating dictionary with available space per disk")
    availDiskSpaceDic = {}
    mtRootDir = srvObj.getCfg().getRootDirectory()
    if (targetDiskId):
        tmpDiskInfoObjList = [ngamsDiskInfo.ngamsDiskInfo().\
                              read(srvObj.getDb(), targetDiskId)]        
    else:
        tmpDiskInfoObjList = ngamsDiskUtils.\
                             getDiskInfoForMountedDisks(srvObj.getDb(),
                                                        getHostId(),
                                                        mtRootDir)
    for diskInfoObj in tmpDiskInfoObjList:
        mtPt = diskInfoObj.getMountPoint()
        diskId = diskInfoObj.getDiskId()
        availDiskSpaceDic[diskId] = getDiskSpaceAvail(mtPt, format="B",
                                                      float=1)

    # Now simulate the execution of the clone job by going sequentially
    # through the files selected for cloning and subtract the required
    # disk space from the available amount for each disk.
    #
    # When a disk reaches the threshold for considering the disk as
    # completed, it is removed from the list of available disks.

    cloneListDbm = ngamsDbm.ngamsDbm(cloneListDbmName)

    # This dictionary contains a list of files that have been simulated
    # successfully cloned. Since they are not updated in the DB, we keep
    # track of this locally.
    cloneSucDbmName = tmpFilePat + "_CLONE_SUCCESS_DB"
    rmFile(cloneSucDbmName + "*")
    cloneSucDbm = ngamsDbm.ngamsDbm(cloneSucDbmName, cleanUpOnDestr=1,
                                    writePerm=1)

    # This is used to keep track of the files that could not be cloned
    # due to lack of space.
    cloneFailDbmName = tmpFilePat + "_CLONE_FAILED_DB"
    rmFile(cloneFailDbmName + "*")
    cloneFailDbm = ngamsDbm.ngamsDbm(cloneFailDbmName, cleanUpOnDestr=1,
                                     writePerm=1)

    # This is used to simulate disk completion. If a specific target
    # disk is defined, all other disks should be ignored (=we set them to
    # completed).
    cloneSimDiskCompl = []
    if (targetDiskId):
        tmpDiskList = ngamsDiskUtils.\
                      getDiskInfoForMountedDisks(srvObj.getDb(), getHostId(),
                                                 mtRootDir)
        for idx in range(len(tmpDiskList)):
            if (tmpDiskList[idx].getDiskId() != targetDiskId):
                cloneSimDiskCompl.append(tmpDiskList[idx].getDiskId())

    # Carry out the simulated clone process.
    ngamsDiskUtils.findTargetDiskResetCache()
    key = 0
    while (1):
        if (not cloneListDbm.hasKey(str(key))): break
        fileInfo = cloneListDbm.get(str(key))
        key += 1
        fio = fileInfo[0]
        hostName = fileInfo[1]

        text = "Simulating cloning of file - File ID: %s/%d, on disk " +\
               "with ID: %s on host: %s"
        info(3,text % (fio.getFileId(), fio.getFileVersion(),
                       fio.getDiskId(), hostName))

        diskExemptList = cloneSimDiskCompl + [fio.getDiskId()]
        trgDiskInfo = None
        while (1):
            try:
                trgDiskInfo = ngamsDiskUtils.\
                              findTargetDisk(srvObj.getDb(), srvObj.getCfg(),
                                             fio.getFormat(), 0,
                                             diskExemptList, 1)
                info(3, 'target disk info: ' + str(trgDiskInfo))
            except Exception, e:
                warning('No candidate disk available for mime-type %s - please check the config file and make sure there is a Stream for this mime type' % fio.getFormat())
                if (str(e).find("NGAMS_AL_NO_STO_SETS") != -1):
                    # No more candidate Target Disks for this type
                    # of data - this file cannot be cloned.
                    cloneFailDbm.addIncKey(fio)
                break

            # Check if a file with that ID + version is already
            # stored on the selected Target Disk.
            fileInDb = srvObj.getDb().fileInDb(trgDiskInfo.getDiskId(),
                                               fio.getFileId(),
                                               fio.getFileVersion())
            fileKey = ngamsLib.genFileKey(trgDiskInfo.getDiskId(),
                                          fio.getFileId(),
                                          fio.getFileVersion())
            fileSimCloned = cloneSucDbm.hasKey(fileKey)
            if (fileInDb or fileSimCloned):
                # This file is already stored on the given disk.
                # Add to the exempt list.
                diskExemptList.append(trgDiskInfo.getDiskId())
            else:
                # OK, this disk should be OK, stop looking for a
                # suitable Target Disk.
                info(3,"Found suitable disk with ID: %s/Slot ID: %s" %\
                     (trgDiskInfo.getDiskId(), trgDiskInfo.getSlotId()))
                cloneSucDbm.add(fileKey, "")
                break
            
        # We now subtract the size of the file from the available amount of
        # disk space for the selected Target Disk. When the amount of available
        # space goes below the threshold defined for this NG/AMS system that
        # disk is considered to be completed.
        if (trgDiskInfo):
            diskId = trgDiskInfo.getDiskId()
            availDiskSpaceDic[diskId] -= float(fio.getFileSize())
            if ((availDiskSpaceDic[diskId] / 1048576.0) < \
                srvObj.getCfg().getFreeSpaceDiskChangeMb()):
                cloneSimDiskCompl.append(diskId)

    # Now, if there are files that could not be cloned we raise an exception
    # indicating this, and in particular indicating for which mime-types there
    # is not enough disk space.
    if (cloneFailDbm.getCount()):
        spaceLackMimeTypeDic = {}
        cloneFailDbm.initKeyPtr()
        while (1):
            key, fio = cloneFailDbm.getNext()
            if (not key): break
            format = fio.getFormat()
            if (not spaceLackMimeTypeDic.has_key(fio.getFormat())):
                spaceLackMimeTypeDic[format] = 0.0
            spaceLackMimeTypeDic[format] += float(fio.getFileSize())
        errMsg = "Insufficient space to carry out the CLONE Command. " +\
                 "Approximate amount of disk space missing (mime-type: MB):"
        for mt in spaceLackMimeTypeDic.keys():
            errMsg += " %s: %.3f MB" %\
                      (mt, (spaceLackMimeTypeDic[mt] / 1048576.0))
        errMsg = genLog("NGAMS_ER_CLONE_REJECTED", [errMsg])
        raise Exception, errMsg


def _checkFile(srvObj,
               fileInfoObj,
               stagFile,
               httpHeaders,
               checkChecksum):
    """
    Make a consistency check of the Staging File.

    srvObj:           Reference to instance of Server Object (ngamsServer).

    fileInfoObj:      File info object with info about the file
                      (ngamsFileInfo).
    
    stagFile:         Staging filename (string).
    
    httpHeaders:      HTTP headers (mimetools.Message)

    checkChecksum:    Carry out checksum check (0|1/integer).

    Returns:          Void.
    """
    # First ensure to flush file caches.
    ngamsFileUtils.syncCachesCheckFiles(srvObj, [stagFile])
    
    # Check file size.
    fileSize = getFileSize(stagFile)
    if (fileSize != fileInfoObj.getFileSize()):
        # If the mime-type is 'text/xml' we check if the returned
        # document is an NG/AMS XML Status reporting a problem.
        tmpStat = None
        if (httpHeaders.type == NGAMS_XML_MT):
            try:
                tmpStat = ngamsStatus.ngamsStatus().load(stagFile,getStatus=1)
                if (tmpStat.getStatus() != NGAMS_FAILURE):
                    del tmpStat
                    tmpStat = None
            except Exception, e:
                # Was apparently not an NG/AMS Status Document.
                pass
        if (tmpStat):
            # An error response was received from the source node.
            raise Exception, tmpStat.getMessage()
        else:
            # The file seems not to have been transferred completely.
            errMsg = "Size of cloned file wrong (expected: %d/actual: %d)"
            raise Exception, errMsg % (fileInfoObj.getFileSize(), fileSize)
    info(4,"Size of cloned Staging File OK: " + stagFile)

    # The file size was correct.
    if (checkChecksum):
        dcpi = fileInfoObj.getChecksumPlugIn()
        if (dcpi):
            try:
                exec "import " + dcpi
                checksum = eval(dcpi + "." + dcpi + "(srvObj, stagFile, 0)")
            except Exception, e:
                errMsg = "Error checking checksum of file: " + str(e)
                raise Exception, errMsg
            if (checksum != fileInfoObj.getChecksum()):
                errMsg = "Wrong checksum of cloned file"
                raise Exception, errMsg
            info(4,"Checksum of cloned Staging File OK: " + stagFile)
        else:
            info(4,"No Checksum Plug-In specified for file")


def _cloneExec(srvObj,
               cloneListDbmName,
               tmpFilePat,
               targetDiskId,
               reqPropsObj):
    """
    See documentation of ngamsCloneCmd._cloneThread(). This function is
    merely implemented in order to encapsulate the whole process to be able
    to clean up properly when the processing is terminated.
    """
    T = TRACE(1)
    
    cloneListDbm = cloneStatusDbm = None

    emailNotif = 0
    checkChecksum = 1
    if (reqPropsObj):
        if (reqPropsObj.hasHttpPar("notif_email")): emailNotif = 1
        if (reqPropsObj.hasHttpPar("check")):
            checkChecksum = int(reqPropsObj.getHttpPar("check"))

    # Open clone list DB.
    cloneListDbm = ngamsDbm.ngamsDbm(cloneListDbmName)
    
    # We have to get the port numbers of the hosts where the files to be
    # cloned are stored.
    hostInfoDic = {}
    cloneListDbm.initKeyPtr()
    while (1):
        key, fileInfo = cloneListDbm.getNext()
        if (not key): break
        hostInfoDic[fileInfo[1]] = -1
    hostInfoDic = ngamsHighLevelLib.resolveHostAddress(srvObj.getDb(),
                                                       srvObj.getCfg(),
                                                       hostInfoDic.keys())

    # The cloning loop. Loop over the list of files to clone and generate
    # a report with the result.
    if (emailNotif):
        cloneStatusDbmName = tmpFilePat + "_CLONE_STATUS_DB"
        cloneStatusDbm = ngamsDbm.ngamsDbm(cloneStatusDbmName,
                                           cleanUpOnDestr = 0, writePerm = 1)
        
    successCloneCount = 0
    failedCloneCount  = 0
    abortCloneLoop    = 0
    cloneTimer        = PccUtTime.Timer()
    timeAccu          = 0.0
    key = 0
    while (1):
        cloneTimer.start()
        if (not cloneListDbm.hasKey(str(key))): break
        fileInfo = cloneListDbm.get(str(key))
        key += 1

        # Check if we have permission to run. Otherwise, stop.
        if (not srvObj.getThreadRunPermission()): break

        fio = fileInfo[0]
        mtPt = fileInfo[2]
        if (emailNotif):
            tmpFileList = ngamsFileList.\
                          ngamsFileList("FILE_CLONE_STATUS",
                                        "File: " + fio.getFileId() + "/" +\
                                        fio.getDiskId() + "/" +\
                                        str(fio.getFileVersion()))
        hostId = fileInfo[1]
        text = "Cloning file - File ID: %s/%d, on disk " +\
               "with ID: %s on host: %s"
        info(3,text % (fio.getFileId(), fio.getFileVersion(),
                       fio.getDiskId(), hostId))

        # We generate a local Staging File and archive this.
        stagingFilename = ""
        try:
            # Check if file is marked as bad.
            if (fio.getFileStatus()[0] == "1"):
                errMsg = "File marked as bad - skipping!"
                raise Exception, errMsg

            if (targetDiskId == ""):
                # Try to find a disk not hosting already a file with that
                # ID + version.
                diskExemptList = [fio.getDiskId()]
                while (1):
                    trgDiskInfo = ngamsDiskUtils.\
                                  findTargetDisk(srvObj.getDb(),
                                                 srvObj.getCfg(),
                                                 fio.getFormat(),
                                                 1, diskExemptList)
                    # Check if a file with that ID + version is already
                    # stored on the selected Target Disk.
                    if (srvObj.getDb().fileInDb(trgDiskInfo.getDiskId(),
                                                fio.getFileId(),
                                                fio.getFileVersion())):
                        # This file is already stored on the given disk.
                        # Add to the exempt list.
                        diskExemptList.append(trgDiskInfo.getDiskId())
                    else:
                        # OK, this disk should be OK, stop looking for a
                        # suitable Target Disk.
                        break
            else:
                try:
                    trgDiskInfo = ngamsDiskInfo.ngamsDiskInfo().\
                                  read(srvObj.getDb(), targetDiskId)
                    slotId = trgDiskInfo.getSlotId()
                    storageSetId = srvObj.getCfg().\
                                   getStorageSetFromSlotId(slotId).\
                                   getStorageSetId()
                    trgDiskInfo.setStorageSetId(storageSetId)
                except Exception, e:
                    abortCloneLoop = 1
                    raise e

            # We don't accept to clone onto the same disk (this would mean
            # overwriting).
            if (trgDiskInfo.getDiskId() == fio.getDiskId()):
                err = "Source and target files are identical"
                msg = "Failed in cloning file with ID: " + fio.getFileId() +\
                      "/Version: " + str(fio.getFileVersion()) +\
                      " on disk with ID: " + fio.getDiskId() +\
                      " on host: " + hostId + ". Reason: " + err
                warning(msg)
                if (emailNotif):
                    tmpFileList.setStatus(NGAMS_FAILURE + ": " + err)
                    tmpFileList.addFileInfoObj(fio.setTag("SOURCE_FILE"))
                    cloneStatusDbm.addIncKey(tmpFileList)
                failedCloneCount += 1
                continue

            storageSetId = trgDiskInfo.getStorageSetId()
            tmpReqPropsObj = ngamsReqProps.ngamsReqProps()
            tmpReqPropsObj.setMimeType(fio.getFormat())
            stagingFilename = ngamsHighLevelLib.\
                              genStagingFilename(srvObj.getCfg(),
                                                 tmpReqPropsObj,
                                                 srvObj.getDiskDic(),
                                                 storageSetId, fio.getFileId())
            # Receive the data into the Staging File using the urllib.
            if (getHostId() != hostId):
                # Example: http://host:7777/RETRIEVE?file_id=id&file_version=1
                ipAddress = hostInfoDic[hostId].getIpAddress()
                portNo = hostInfoDic[hostId].getSrvPort()
                fileUrl = "http://" + ipAddress + ":" + str(portNo) +\
                          "/RETRIEVE?" + "file_id=" + fio.getFileId() +\
                          "&file_version=" + str(fio.getFileVersion())
                # If a specific Disk ID for the source file is given, append
                # this.
                if (fio.getDiskId()):
                    fileUrl += "&disk_id=%s" % fio.getDiskId()

                # Check if host is suspended, if yes, wake it up.
                if (srvObj.getDb().getSrvSuspended(hostId)):
                    info(3,"Clone Request - Waking up suspended " +\
                         "NGAS Host: " + hostId)
                    ngamsSrvUtils.wakeUpHost(srvObj, hostId)
            else:
                fileUrl = "file:" + mtPt + "/" + fio.getFilename()
            info(3,"Receiving file via URI: " + fileUrl + " into " +\
                 "staging filename: " + stagingFilename)
            # We try up to 5 times to retrieve the file in case a problem is
            # encountered during cloning.
            for attempt in range(5):
                try:
                    filename, headers = urllib.urlretrieve(fileUrl,
                                                           stagingFilename)
                    _checkFile(srvObj, fio, stagingFilename, headers,
                               checkChecksum)
                    # If we get to this point the transfer was (probably) OK.
                    break
                except Exception, e:
                    rmFile(stagingFilename)
                    errMsg = "Problem occurred while cloning file "+\
                             "via URL: " + fileUrl + " - Error: " + str(e)
                    if (attempt < 4):
                        errMsg += " - Retrying in 5s ..."
                        error(errMsg)
                        time.sleep(5)
                    else:
                        raise Exception, errMsg

            # We simply copy the file into the same destination as the
            # source file (but on another disk).
            targPathName  = os.path.dirname(fio.getFilename())
            targFilename  = os.path.basename(fio.getFilename())
            complTargPath = os.path.normpath(trgDiskInfo.getMountPoint() +\
                                             "/" + targPathName)
            checkCreatePath(complTargPath)
            complFilename = os.path.normpath(complTargPath + "/"+targFilename)
            info(1, 'FINAL FILENAME: ' + str(complFilename));
            mvTime = mvFile(stagingFilename, complFilename)
            ngamsLib.makeFileReadOnly(complFilename)
          
            # Update status for new file in the DB.
            newFileInfo = fio.clone().setDiskId(trgDiskInfo.getDiskId()).\
                          setCreationDate(getFileCreationTime(complFilename))
            fileExists = srvObj.getDb().fileInDb(trgDiskInfo.getDiskId(),
                                                 fio.getFileId(),
                                                 fio.getFileVersion())
            newFileInfo.write(srvObj.getDb())

            # Update status for the Target Disk in DB + check if the disk is
            # completed.
            if (fileExists): mvTime = 0
            dummyDapiStatObj = ngamsDapiStatus.ngamsDapiStatus().\
                               setDiskId(trgDiskInfo.getDiskId()).\
                               setFileExists(fileExists).\
                               setFileSize(fio.getFileSize()).setIoTime(mvTime)
            ngamsDiskUtils.updateDiskStatusDb(srvObj.getDb(), dummyDapiStatObj)
            ngamsArchiveUtils.checkDiskSpace(srvObj, trgDiskInfo.getDiskId())
     
            # Update the clone file status list.
            if (emailNotif):
                tmpFileList.setStatus(NGAMS_SUCCESS)
                tmpFileList.addFileInfoObj(fio.setTag("SOURCE_FILE"))
                tmpFileList.addFileInfoObj(newFileInfo.setTag("TARGET_FILE"))
                cloneStatusDbm.addIncKey(tmpFileList)
            successCloneCount += 1

            # If running as a cache archive, update the Cache New Files DBM
            # with the information about the new file.
            if (srvObj.getCachingActive()):
                diskId   = trgDiskInfo.getDiskId()
                fileId   = fio.getFileId()
                fileVer  = fio.getFileVersion()
                filename = fio.getFilename()
                ngamsCacheControlThread.addEntryNewFilesDbm(srvObj, diskId,
                                                            fileId, fileVer,
                                                            filename)

            # Generate a confirmation log entry.
            msg = genLog("NGAMS_INFO_FILE_CLONED",
                         [fio.getFileId(), fio.getFileVersion(),
                          fio.getDiskId(), hostId])
            sysLogInfo(1,msg)
            cloneTime = cloneTimer.stop()
            timeAccu += cloneTime
            msg = msg + ". Time: %.3fs. Total time: %.3fs." %\
                  (cloneTime, timeAccu)
            info(1,msg)
        except Exception, e:
            cloneTime = cloneTimer.stop()
            timeAccu += cloneTime
            errMsg = genLog("NGAMS_ER_FILE_CLONE_FAILED",
                            [fio.getFileId(), fio.getFileVersion(),
                             fio.getDiskId(), hostId, str(e)])
            if (abortCloneLoop):
                sysLogInfo(1,errMsg)
                error(errMsg)
                thread.exit()
            else:
                warning(errMsg)
                if (emailNotif):
                    tmpFileList.setStatus(NGAMS_FAILURE + ": Error: " + errMsg)
                    tmpFileList.addFileInfoObj(fio.setTag("SOURCE_FILE"))
                    cloneStatusDbm.addIncKey(tmpFileList)
                failedCloneCount += 1
 
            # Delete Staging File if already created.
            if ((stagingFilename != "") and (os.path.exists(stagingFilename))):
                rmFile(stagingFilename)

        # Calculate time statistics.
        if (reqPropsObj):
            ngamsHighLevelLib.stdReqTimeStatUpdate(srvObj, reqPropsObj.\
                                                   incActualCount(1), timeAccu)
        
    # Final update of the Request Status.
    if (reqPropsObj):
        complPercent = (100.0 * (float(reqPropsObj.getActualCount()) /
                                 float(reqPropsObj.getExpectedCount())))
        reqPropsObj.setCompletionPercent(complPercent, 1)
        reqPropsObj.setCompletionTime(1)
        srvObj.updateRequestDb(reqPropsObj)
    
    # Send Clone Report with list of files cloned to a possible 
    # requestor(select) of this.
    totFiles = (successCloneCount + failedCloneCount)
    if (emailNotif):
        xmlStat = 0
        # TODO: Generation of XML status report is disabled since we cannot
        #       handle for the moment XML documents with 1000s of elements.
        if (xmlStat):        
            cloneStatusFileList = ngamsFileList.\
                                  ngamsFileList("FILE_CLONING_STATUS_REPORT",
                                                "File Cloning Status Report")
            fileCount = 0
            while (fileCount < cloneStatusDbm.getCount()):
                tmpFileList = cloneStatusDbm.get(str(fileCount))
                cloneStatusFileList.addFileListObj(tmpFileList)
                
            # Make overall status.
            cloneStatusFileList.setStatus("SUCCESS: " +\
                                          str(successCloneCount) +\
                                          ", FAILURE: " +\
                                          str(failedCloneCount) +\
                                          ", NOT DONE: " +\
                                          str(len(cloneList) -\
                                              successCloneCount -\
                                              failedCloneCount))
            status = srvObj.genStatus(NGAMS_SUCCESS,
                                      "CLONE command status report").\
                                      addFileList(cloneStatusFileList)
            statRep = status.genXmlDoc(0, 0, 0, 1, 0)
            statRep = ngamsHighLevelLib.\
                      addDocTypeXmlDoc(srvObj, statRep,
                                       NGAMS_XML_STATUS_ROOT_EL,
                                       NGAMS_XML_STATUS_DTD)
            mimeType = NGAMS_XML_MT
        else:
            # Generate a 'simple' ASCII report.
            statRep = tmpFilePat + "_NOTIF_EMAIL.txt"
            fo = open(statRep, "w")
            timeStamp = PccUtTime.TimeStamp().getTimeStamp()
            if (reqPropsObj.hasHttpPar("disk_id")):
                diskId = reqPropsObj.getHttpPar("disk_id")
            else:
                diskId = "-----"
            if (reqPropsObj.hasHttpPar("file_id")):
                fileId = reqPropsObj.getHttpPar("file_id")
            else:
                fileId = "-----"
            if (reqPropsObj.hasHttpPar("file_version")):
                fileVersion = reqPropsObj.getHttpPar("file_version")
            else:
                fileVersion = "-----"
            tmpFormat = "CLONE STATUS REPORT:\n\n" +\
                        "==Summary:\n\n" +\
                        "Date:                       %s\n" +\
                        "NGAS Host:                  %s\n" +\
                        "Disk ID:                    %s\n" +\
                        "File ID:                    %s\n" +\
                        "File Version:               %s\n" +\
                        "Total Number of Files:      %d\n" +\
                        "Number of Cloned Files:     %d\n" +\
                        "Number of Failed Files:     %d\n" +\
                        "Total processing time (s):  %.3f\n" +\
                        "Handling time per file (s): %.3f\n\n" +\
                        "==File List:\n\n"
            fo.write(tmpFormat % (timeStamp, getHostId(), diskId, fileId,
                                  str(fileVersion), totFiles,
                                  successCloneCount, failedCloneCount,
                                  timeAccu, (timeAccu / totFiles)))
            tmpFormat = "%-70s %-70s %-7s\n"
            fo.write(tmpFormat % ("Source File", "Target File", "Status"))
            fo.write(tmpFormat % (70 * "-", 70 * "-", 7 * "-"))
            key = 1
            while (1):
                if (not cloneStatusDbm.hasKey(str(key))): break
                tmpFileList = cloneStatusDbm.get(str(key))
                key += 1
                srcFileObj = tmpFileList.getFileInfoObjList()[0]
                srcFile = "%s/%s/%d" % (srcFileObj.getDiskId(),
                                        srcFileObj.getFileId(),
                                        srcFileObj.getFileVersion())
                if (tmpFileList.getStatus() == NGAMS_SUCCESS):
                    trgFileObj = tmpFileList.getFileInfoObjList()[1]
                    trgFile = "%s/%s/%d" % (trgFileObj.getDiskId(),
                                            trgFileObj.getFileId(),
                                            trgFileObj.getFileVersion())
                else:
                    trgFile = "-----"
                fo.write(tmpFormat % (srcFile,trgFile,tmpFileList.getStatus()))
            fo.write(149 * "-")
            fo.write("\n\n==END\n")
            fo.close()
            mimeType = NGAMS_TEXT_MT

        # Send out the status report.
        emailAdrList = reqPropsObj.getHttpPar("notif_email").split(",")
        attachmentName = "CloneStatusReport"
        if (reqPropsObj.hasHttpPar("disk_id")):
            attachmentName += "-" + reqPropsObj.getHttpPar("disk_id")
        if (reqPropsObj.hasHttpPar("file_id")):
            attachmentName += "-" + reqPropsObj.getHttpPar("file_id")
        if (reqPropsObj.hasHttpPar("file_version")):
            attachmentName += "-" + reqPropsObj.getHttpPar("file_version")
        ngamsNotification.notify(srvObj.getCfg(), NGAMS_NOTIF_INFO,
                                 "CLONE STATUS REPORT", statRep, emailAdrList,
                                 1, mimeType, attachmentName, 1)
        del cloneStatusDbm
        rmFile(cloneStatusDbmName + "*")
        rmFile(statRep)

    if (cloneListDbm): del cloneListDbm
    rmFile(cloneListDbmName + "*")
    info(1, "_cloneExec(). Total time: %.3fs. Average time per file: %.3fs." %\
         (timeAccu, (timeAccu / totFiles)))


def _cloneExplicit(srvObj,
                   reqPropsObj,
                   diskId,
                   fileId,
                   fileVersion,
                   targetDiskId):
    """
    Execute CLONE Command, where the source Disk ID, File ID and File Version
    are specified. Is much faster than a normal CLONE Command when an explicit
    file is specified.

    srvObj:           Reference to instance of Server Object (ngamsServer).

    fileInfoObj:      File info object with info about the file
    
    diskId:           ID of disk hosting the file to be cloned (string).

    fileId:           ID of file to clone (string).

    fileVersion:      Version of file to clone (integer).

    targetDiskId:     ID of target disk (string).

    Returns:          Void.
    """
    T = TRACE(1)

    # Resolve the location of the file to clone.
    location, hostId, ipAddress, portNo, mountPoint, filename,\
              fileVersion, mimeType =\
              ngamsFileUtils.quickFileLocate(srvObj, reqPropsObj, fileId,
                                             diskId=diskId,
                                             fileVersion=fileVersion)
    # Read also the entire file info (unfortunately).
    srcFileInfo = ngamsFileInfo.ngamsFileInfo().read(srvObj.getDb(), fileId,
                                                     fileVersion, diskId)

    # Determine target disk.
    if (targetDiskId == ""):
        # Try to find a disk not hosting already a file with that
        # ID + version.
        diskExemptList = [diskId]
        while (1):
            trgDiskInfo = ngamsDiskUtils.\
                          findTargetDisk(srvObj.getDb(), srvObj.getCfg(),
                                         mimeType, 1, diskExemptList)
            # Check if a file with that ID + version is already
            # stored on the selected Target Disk.
            if (srvObj.getDb().fileInDb(trgDiskInfo.getDiskId(), fileId,
                                        fileVersion)):
                # This file is already stored on the given disk.
                # Add to the exempt list.
                diskExemptList.append(trgDiskInfo.getDiskId())
            else:
                # OK, this disk should be OK, stop looking for a
                # suitable Target Disk.
                break
    else:
        trgDiskInfo = ngamsDiskInfo.ngamsDiskInfo().\
                      read(srvObj.getDb(), targetDiskId)
        slotId = trgDiskInfo.getSlotId()
        storageSetId = srvObj.getCfg().getStorageSetFromSlotId(slotId).\
                       getStorageSetId()
        trgDiskInfo.setStorageSetId(storageSetId)
    
    # Don't accept to clone onto the same disk (this would meann overwriting).
    if (trgDiskInfo.getDiskId() == diskId):
        err = "Source and target files are identical"
        msg = "Failed in cloning file with ID: " + fileId +\
              "/Version: " + str(fileVersion) +\
              " on disk with ID: " + diskId +\
              " on host: " + hostId + ". Reason: " + err
        raise Exception, msg

    # Receive the file into the staging filename.
    storageSetId = trgDiskInfo.getStorageSetId()
    tmpReqPropsObj = ngamsReqProps.ngamsReqProps()
    tmpReqPropsObj.setMimeType(mimeType)
    stagingFilename = ngamsHighLevelLib.genStagingFilename(srvObj.getCfg(),
                                                           tmpReqPropsObj,
                                                           srvObj.getDiskDic(),
                                                           storageSetId,
                                                           fileId)
    try:
        quickLocation = False
        if (reqPropsObj.hasHttpPar("quick")):
            quickLocation = int(reqPropsObj.getHttpPar("quick"))

        # Receive the data into the Staging File using the urllib.
        if (getHostId() != hostId):
            # Example: http://host:7777/RETRIEVE?disk_id=%s&"
            #          file_id=id&file_version=1
            fileUrl = "http://%s:%s/RETRIEVE?disk_id=%s&file_id=%s&" +\
                      "file_version=%s"
            fileUrl = fileUrl % (ipAddress, str(portNo), diskId, fileId,
                                 str(fileVersion))

            # If CLONE?quick specified, we try to retrieve the file via the
            # RETRIEVE?quick_location method.
            quickFileUrl = fileUrl
            if (reqPropsObj.hasHttpPar("quick")):
                if (int(reqPropsObj.getHttpPar("quick"))):
                    quickFileUrl = fileUrl + "&quick_location=1"

            # Check if host is suspended, if yes, wake it up.
            if (srvObj.getDb().getSrvSuspended(hostId)):
                info(3,"Clone Request - Waking up suspended " +\
                     "NGAS Host: " + hostId)
                ngamsSrvUtils.wakeUpHost(srvObj, hostId)
        else:
            fileUrl = "file:" + mtPt + "/" + filename
        info(3,"Receiving file via URI: " + fileUrl + " into " +\
             "staging filename: " + stagingFilename)
        # We try up to 5 times to retrieve the file in case a problem is
        # encountered during cloning.
        for attempt in range(5):
            try:
                if (attempt == 0):
                    filename, headers = urllib.urlretrieve(quickFileUrl,
                                                           stagingFilename)
                else:
                    filename, headers = urllib.urlretrieve(fileUrl,
                                                           stagingFilename)
                _checkFile(srvObj, srcFileInfo, stagingFilename, headers, True)
                # If we get to this point the transfer was (probably) OK.
                break
            except Exception, e:
                rmFile(stagingFilename)
                errMsg = "Problem occurred while cloning file "+\
                         "via URL: " + fileUrl + " - Error: " + str(e)
                if (attempt < 4):
                    errMsg += " - Retrying in 5s ..."
                    error(errMsg)
                    time.sleep(0.5)
                else:
                    raise Exception, errMsg

        # We simply copy the file into the same destination as the
        # source file (but on another disk).
        targPathName  = os.path.dirname(srcFileInfo.getFilename())
        targFilename  = os.path.basename(srcFileInfo.getFilename())
        complTargPath = os.path.normpath(trgDiskInfo.getMountPoint() +\
                                         "/" + targPathName)
        checkCreatePath(complTargPath)
        complFilename = os.path.normpath(complTargPath + "/" + targFilename)
        mvTime = mvFile(stagingFilename, complFilename)
        ngamsLib.makeFileReadOnly(complFilename)

        # Update status for new file in the DB.
        newFileInfo = srcFileInfo.clone().setDiskId(trgDiskInfo.getDiskId()).\
                      setCreationDate(getFileCreationTime(complFilename))
        fileExists = srvObj.getDb().fileInDb(trgDiskInfo.getDiskId(),
                                             fileId, fileVersion)
        newFileInfo.write(srvObj.getDb())

        # Update status for the Target Disk in DB + check if the disk is
        # completed.
        if (fileExists): mvTime = 0
        dummyDapiStatObj = ngamsDapiStatus.ngamsDapiStatus().\
                           setDiskId(trgDiskInfo.getDiskId()).\
                           setFileExists(fileExists).\
                           setFileSize(srcFileInfo.getFileSize()).\
                           setIoTime(mvTime)
        ngamsDiskUtils.updateDiskStatusDb(srvObj.getDb(), dummyDapiStatObj)
        ngamsArchiveUtils.checkDiskSpace(srvObj, trgDiskInfo.getDiskId())

        # If running as a cache archive, update the Cache New Files DBM
        # with the information about the new file.
        if (srvObj.getCachingActive()):
            ngamsCacheControlThread.addEntryNewFilesDbm(srvObj, diskId, fileId,
                                                        fileVersion, filename)

        # Generate a confirmation log entry.
        msg = genLog("NGAMS_INFO_FILE_CLONED",
                     [fileId, fileVersion, diskId, hostId])
        sysLogInfo(1, msg)
        info(1, msg)
    except Exception, e:
        # Delete Staging File if already created.
        if (os.path.exists(stagingFilename)): rmFile(stagingFilename)
        raise Exception, e





def _cloneThread(srvObj,
                 cloneListDbmName,
                 tmpFilePat,
                 targetDiskId = "",
                 reqPropsObj = None,
                 dummyPar = None):
    """
    Function that carried out the actual cloning process of the files
    referenced to in the 'cloneList' 

    srvObj:           Reference to instance of Server Object (ngamsServer).

    cloneListDbmName: Name of DBM containing the information about
                      the files to be cloned. This DB has an index number
                      as key pointing to pickled information about each file.
                      This pickled information is

                        [<File Info Object>, <Host ID>, <Mount Point>]
                       
                      (string)
                     
    tmpFilePat:       File pattern to be used for generating temporary
                      files (string). 

    targetDiskId:     ID of disk to where the files cloned should be written
                      (string).

    reqPropsObj:      If an NG/AMS Request Properties Object is given, the
                      Request Status will be updated as the request is carried
                      out (ngamsReqProps).

    Returns:          Void.
    """
    info(1,"Cloning Thread carrying out Clone Request ...")
    try:
        _cloneExec(srvObj, cloneListDbmName, tmpFilePat, targetDiskId,
                   reqPropsObj)
        rmFile(tmpFilePat + "*")
        info(1,"Processing of Clone Request completed")
        thread.exit()
    except Exception, e:
        rmFile(tmpFilePat + "*")
        raise e


def _clone(srvObj,
           diskId,
           fileId,
           fileVersion,
           targetDiskId,
           reqPropsObj,
           httpRef,
           tmpFilePat):
    """
    Internal function used by ngamsCloneCmd.clone() to carry out the
    cloning. See documentation for ngamsCloneCmd.clone().
    """
    targetDiskId = targetDiskId.strip()
    info(4,"Handling file cloning with parameters - File ID: " + fileId +\
         " - Disk ID: " + diskId + " - File Version: " + str(fileVersion) +\
         " - Target Disk ID: |" + targetDiskId + "|")
    if (((fileId == "") and (diskId == "") and (fileVersion != -1)) or
        ((fileId == "") and (diskId == "") and (fileVersion == -1))):
        errMsg = genLog("NGAMS_ER_CMD_SYNTAX",
                        [NGAMS_CLONE_CMD, "File Id: " + fileId +\
                         ", Disk ID: " + diskId +\
                         ", File Version: " + str(fileVersion)])
        raise Exception, errMsg

    # If Disk ID, File ID and File Version are given, execute a quick cloning.
    try:
        fileVersion = int(fileVersion)
    except:
        pass
    if (False and diskId and fileId and (fileVersion > 0)):
        _cloneExplicit(srvObj, reqPropsObj, diskId, fileId, fileVersion,
                       targetDiskId)
        info(1, "Successfully handled command CLONE")
        return

    # Handling cloning of more files.
    cloneListDbm = fileInfoDbm = None
    cloneListDbmName = tmpFilePat + "_CLONE_INFO_DB"
    try:
        # Get information about candidate files for cloning.
        fileInfoDbmNm = tmpFilePat + "_FILE_INFO_DB"
        fileInfoDbmNm = srvObj.getDb().\
                        dumpFileInfo(fileId, fileVersion, diskId, ignore=0,
                                     fileInfoDbmName=fileInfoDbmNm, order=0)
        fileInfoDbm = ngamsDbm.ngamsDbm(fileInfoDbmNm)

        # Create a BSD DB with information about files to be cloned.       
        rmFile(cloneListDbmName + "*")
        cloneListDbm = ngamsDbm.ngamsDbm(cloneListDbmName, cleanUpOnDestr = 0,
                                         writePerm = 1)
        noOfFiles = fileInfoDbm.getCount()
        if ((noOfFiles > 0) and
            (((fileId != "") and (diskId == "") and (fileVersion == -1)) or
             ((fileId != "") and (diskId != "") and (fileVersion == -1)) or
             ((fileId != "") and (diskId != "") and (fileVersion != -1)))):
            # Take only one element (the first).
            cloneListDbm.add("0", fileInfoDbm.get("0"))
        elif (noOfFiles > 0):
            # Take all the files.
            fileInfoDbm.initKeyPtr()
            cloneDbCount = 0
            while (1):
                key, tmpFileInfo = fileInfoDbm.getNext()
                if (not key): break
                cloneListDbm.add(str(cloneDbCount), tmpFileInfo)
                cloneDbCount += 1

        # Raise exception if no files were found.
        noOfCloneFiles = cloneListDbm.getCount()
        if (noOfCloneFiles == 0):
            errMsg = genLog("NGAMS_ER_CMD_EXEC",
                            [NGAMS_CLONE_CMD, "No files for cloning found"])
            raise Exception, errMsg

        del fileInfoDbm
        rmFile(fileInfoDbmNm + "*")
    except Exception, e:
        if (cloneListDbm): del cloneListDbm
        if (fileInfoDbm): del fileInfoDbm
        rmFile(fileInfoDbmNm + "*")
        rmFile(cloneListDbmName + "*")
        raise Exception, e
    info(3,"Found: " + str(noOfCloneFiles) + " file(s) for cloning ...")
    del cloneListDbm

    # Check available amount of disk space.
    cloneCheckDiskSpace(srvObj, cloneListDbmName, tmpFilePat, targetDiskId)

    # Initialize Request Status parameters.
    if (reqPropsObj):
        reqPropsObj.\
                      setCompletionPercent(0, 1).\
                      setExpectedCount(noOfCloneFiles, 1).\
                      setActualCount(0, 1)
        srvObj.updateRequestDb(reqPropsObj)

    # Wait until CLONE Command has finished, or send a reply before cloning?
    if (not reqPropsObj.getWait()):
        # Send intermediate reply if the HTTP Reference object is given
        # whenever send an auto reply now.
        info(3,"CLONE command accepted - generating immediate " +
             "confimation reply to CLONE command")
        status = srvObj.genStatus(NGAMS_SUCCESS,
                                  "Accepted CLONE command for execution").\
                                  setReqStatFromReqPropsObj(reqPropsObj).\
                                  setActualCount(0)

        # Do the actual cloning in a thread
        args = (srvObj, cloneListDbmName, tmpFilePat, targetDiskId,
                reqPropsObj, None)
        thrName = NGAMS_CLONE_THR + getThreadName()
        cloneThread = threading.Thread(None, _cloneThread, thrName, args)
        cloneThread.setDaemon(0)
        cloneThread.start()
    else:
        # Carry out the cloning (directly in this thread) and send reply
        # when this is done.
        _cloneExec(srvObj, cloneListDbmName, tmpFilePat, targetDiskId,
                   reqPropsObj)
        msg = "Successfully handled command CLONE"
        info(3,msg)
        status = srvObj.genStatus(NGAMS_SUCCESS, msg).\
                 setReqStatFromReqPropsObj(reqPropsObj).setActualCount(0)
        rmFile(cloneListDbmName + "*")

    # Send reply if possible.
    if (httpRef):
        xmlStat = status.genXmlDoc(0, 0, 0, 1, 0)
        xmlStat = ngamsHighLevelLib.\
                  addDocTypeXmlDoc(srvObj,xmlStat,NGAMS_XML_STATUS_ROOT_EL,
                                   NGAMS_XML_STATUS_DTD)
        srvObj.httpReplyGen(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                            xmlStat, 0, NGAMS_XML_MT, len(xmlStat), [], 1)


def clone(srvObj,
          diskId,
          fileId,
          fileVersion,
          targetDiskId = "",
          reqPropsObj = None,
          httpRef = None):
    """
    Carry out the cloning. The conditions for carrying out the cloning
    are as follows:

      o diskId="", fileId!="", fileVersion=-1:
      Clone one file with the given ID. Latest version of the file is taken.

      o diskId!="", fileId!="", fileVersion=-1:
      Clone one file stored on the given disk. Latest version on that
      disk is taken.

      o diskId="", fileId!="", fileVersion!=-1:
      Clone all files found with the given File Version. Storage location
      (Disk ID) is not taken into account.

      o diskId!="", fileId!="", fileVersion!=-1:
      Clone one file on the given disk with the given File Version.

      o diskId!="", fileId="", fileVersion=-1:
      Clone all files from the disk with the given ID.

      o diskId!="", fileId="", fileVersion!=-1:
      Clone all files with the given File Version from the disk with
      the ID given.
   
      o diskId="", fileId="", fileVersion!=-1:
      Illegal. Not accepted to clone arbitrarily files given by only the
      File Version.

      o diskId="", fileId="", fileVersion=-1:
      Illegal. No files specified.

    srvObj:        Reference to instance of Server Object (ngamsServer).

    diskId:        ID of disk hosting file(s) to clone (string).
    
    fileId:        ID of file to clone (string).
     
    fileVersion:   Version of file(s) to clone (integer).

    targetDiskId:  ID of disk to where the files cloned should be written
                   (string).

    reqPropsObj:   If an NG/AMS Request Properties Object is given, the
                   Request Status will be updated as the request is carried
                   out (ngamsReqProps).

    httpRef:       Reference to the HTTP request handler
                   object (ngamsHttpRequestHandler).

    Returns:       Void.
    """
    T = TRACE()
    
    tmpFilePat = ngamsHighLevelLib.genTmpFilename(srvObj.getCfg(), "CLONE_CMD")
    try:
        _clone(srvObj, diskId, fileId, fileVersion, targetDiskId,
               reqPropsObj, httpRef, tmpFilePat)
    except Exception, e:
        rmFile(tmpFilePat + "*")
        raise e


# EOF
