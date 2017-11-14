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
# "@(#) $Id: ngamsMirroringControlThread.py,v 1.33 2012/03/03 21:24:33 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  27/03/2008  Created
#

"""
This module contains the code for the Mirroring Control Thread, which is used
to coordinate the mirroring of the local NGAS Cluster with other NGAS Clusters.

The NGAS Mirroring Service is running as a background service which does not
consume soo many resources for the general command handling.
"""

# TODO:
#   - Detailed reporting not yet implemented.


from ngams import *
import ngamsLib
import ngamsFileInfo
import ngamsStatus
import ngamsHighLevelLib
import ngamsDbm
import ngamsMirroringRequest
import os
import sys
import time
import thread
import threading
import socket
import random
import copy
import base64
import pcc
import PccUtTime
import urllib,httplib



# Various definitions used within this module.

# Definitions for internal DBM based queues used.
NGAMS_MIR_QUEUE_DBM          = "MIR_QUEUE"
NGAMS_MIR_ERR_QUEUE_DBM      = "MIR_ERROR_QUEUE"
NGAMS_MIR_COMPL_QUEUE_DBM    = "MIR_COMPLETED_QUEUE"
NGAMS_MIR_DBM_COUNTER        = "MIR_DBM_COUNTER"
NGAMS_MIR_DBM_POINTER        = "MIR_DBM_POINTER"
NGAMS_MIR_FILE_LIST_RAW      = "MIR_FILE_LIST_RAW"
NGAMS_MIR_CLUSTER_FILE_DBM   = "MIR_CLUSTER_FILE_INFO"
NGAMS_MIR_DBM_MAX_LIMIT      = (2**30)
NGAMS_MIR_MIR_THREAD_TIMEOUT = 10.0
NGAMS_MIR_SRC_ARCH_INF_DBM   = "MIR_SRC_ARCH_INFO"
NGAMS_MIR_ALL_LOCAL_SRVS     = "ALL"
 
# Used as exception message when the thread is stopping execution
# (deliberately).
NGAMS_MIR_CONTROL_THR_STOP = "_STOP_MIR_CONTROL_THREAD_"

def startMirControlThread(srvObj):
    """
    Start the Mirroring Control Thread.

    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()
    
    info(3, "Starting the Mirroring Control Thread ...")
    args = (srvObj, None)
    srvObj._mirControlThread = threading.Thread(None, mirControlThread,
                                                NGAMS_MIR_CONTROL_THR, args)
    srvObj._mirControlThread.setDaemon(0)
    srvObj._mirControlThread.start()
    srvObj.setMirControlThreadRunning(1)
    info(3, "Mirroring Control Thread started")


def stopMirControlThread(srvObj):
    """
    Stop the Mirroring Control Thread.

    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()
    
    if (not srvObj.getMirControlThreadRunning()): return
    info(3, "Stopping the Mirroring Service ...")
    srvObj._mirControlThread = None
    info(3, "Mirroring Control Thread stopped")


def checkStopMirControlThread(srvObj):
    """
    Used to check if the Mirroring Control Thread should be stopped and in case
    yes, to stop it.

    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE(5)
    
    if (not srvObj.getThreadRunPermission()):
        srvObj.setMirControlThreadRunning(0)
        info(2, "Stopping the Mirroring Service")
        raise Exception, NGAMS_MIR_CONTROL_THR_STOP


def addEntryMirQueue(srvObj,
                     mirReqObj,
                     updateDb = True):
    """
    Add (schedule) a new Mirroring Request in the internal DBM Mirroring Queue.

    srvObj:     Reference to server object (ngamsServer).

    mirReqObj:  Instance of Mirroring Request Object to schedule
                (ngamsMirroringRequest).

    updateDb:   If true, the status is updated in the DB (boolean).

    Returns:    Void.
    """
    T = TRACE()
    
    try:
        srvObj._mirQueueDbmSem.acquire()
        info(4, "Adding entry in Mirroring Queue: %s/%d" %\
             (mirReqObj.getFileId(), mirReqObj.getFileVersion()))
        newKey = ((srvObj._mirQueueDbm.get(NGAMS_MIR_DBM_COUNTER) + 1) %\
                  NGAMS_MIR_DBM_MAX_LIMIT)
        srvObj._mirQueueDbm.\
                              add(str(newKey), mirReqObj).\
                              add(NGAMS_MIR_DBM_COUNTER, newKey).sync()
        if (updateDb): srvObj.getDb().updateMirReq(mirReqObj)
        srvObj._mirQueueDbmSem.release()
    except Exception, e:
        srvObj._mirQueueDbmSem.release()
        msg = "Error adding new element to DBM Mirroring Queue. Error: %s" %\
              str(e)
        raise Exception, msg


def addEntryErrQueue(srvObj,
                     mirReqObj,
                     updateDb = True):
    """
    Add a Mirroring Request in the internal DBM Mirroring Error Queue.

    srvObj:     Reference to server object (ngamsServer).

    mirReqObj:  Instance of Mirroring Request Object to schedule
                (ngamsMirroringRequest).

    updateDb:   If true, the status is updated in the DB (boolean).

    Returns:    Void.
    """
    T = TRACE()
    
    try:
        srvObj._errQueueDbmSem.acquire()
        info(4, "Adding entry in Mirroring Error Queue: %s/%d" %\
             (mirReqObj.getFileId(), mirReqObj.getFileVersion()))
        srvObj._errQueueDbm.add(mirReqObj.genFileKey(), mirReqObj).sync()
        if (updateDb): srvObj.getDb().updateMirReq(mirReqObj)
        srvObj._errQueueDbmSem.release()
    except Exception, e:
        srvObj._errQueueDbmSem.release()
        msg = "Error adding new element to DBM Mirroring Error Queue. " +\
              "Error: %s"
        raise Exception, msg % str(e)


def popEntryQueue(srvObj,
                  mirReqObj,
                  dbm,
                  dbmSem):
    """
    Get (pop) a Mirroring Request Object from the given DBM queue. The entry is
    removed from the queue. The entry to get is referenced by its Mirroring
    Request Object.

    srvObj:     Reference to server object (ngamsServer).

    mirReqObj:  Instance of Mirroring Request Object to schedule
                (ngamsMirroringRequest).

    dbm:        DBM handle to that DBM queue (ngamsDbm).

    dbmSem:     Semaphore controlling access to that queue
                (threading.Semaphore).

    Return:     Reference to the Mirroring Request Object removed from the
                Error Queue DBM (ngamsMirroringRequest).
    """
    T = TRACE()

    try:
        dbmSem.acquire()
        
        if (not dbm.hasKey(mirReqObj.genFileKey())):
            msg = "Mirroring Request: %s not found in DBM Queue: %s"
            raise Exception, msg % (mirReqObj.genSummary(), dbm.getDbmName())

        mirReqObj = dbm.get(mirReqObj.genFileKey())
        dbm.rem(mirReqObj.genFileKey())
        
        dbmSem.release()
        return mirReqObj
    
    except Exception, e:
        dbmSem.release()
        msg = "Error retrieving element from DBM queue: %s. Error: %s"
        raise Exception, msg % (dbm.getDbmName(), str(e))


def dumpKeysQueue(srvObj,
                  dbm,
                  dbmSem,
                  targetDbmName):
    """
    Make a snapshot of all keys in the referenced DBM.

    srvObj:    Reference to server object (ngamsServer).

    dbm:       DBM from which to dump the keys (ngamsDbm).
    
    dbmSem:    Semaphore used to access that DBM (threading.Semaphore).

    dbmName:   Name of the DBM in which to dump the keys (string).

    Returns:   The final name of the resulting DBM (string).
    """
    T = TRACE()

    rmFile("%s*" % targetDbmName)
    keyDbm = ngamsDbm.ngamsDbm(targetDbmName, cleanUpOnDestr = False,
                               writePerm = True)    
    try:
        dbmSem.acquire()
        dbm.initKeyPtr()
        while (True):
            key, data = dbm.getNext()
            if (not key): break
            keyDbm.add(key, data)
        dbmSem.release()
    except Exception, e:
        dbmSem.release()
        msg = "Error dumping keys from DBM: %s. Error: %s"
        raise Exception, msg % (dbm.getDbmName(), str(e))
    
    dbmName = keyDbm.sync().getDbmName()
    return dbmName


def addEntryComplQueue(srvObj,
                       mirReqObj,
                       updateDb = True):
    """
    Add a Mirroring Request in the DBM Mirroring Completed Queue.

    srvObj:     Reference to server object (ngamsServer).

    mirReqObj:  Instance of Mirroring Request Object to put in the queue
                (ngamsMirroringRequest).

    updateDb:   If true, the status is updated in the DB (boolean).

    Returns:    Void.
    """
    T = TRACE()
    
    try:
        srvObj._complQueueDbmSem.acquire()
        info(4, "Adding entry in Mirroring Completed Queue: %s/%d" %\
             (mirReqObj.getFileId(), mirReqObj.getFileVersion()))
        srvObj._complQueueDbm.add(mirReqObj.genFileKey(), mirReqObj).sync()
        if (updateDb): srvObj.getDb().updateMirReq(mirReqObj)
        srvObj._complQueueDbmSem.release()
    except Exception, e:
        srvObj._complQueueDbmSem.release()
        msg = "Error adding new element to DBM Mirroring Completed Queue. " +\
              "Error: %s"
        raise Exception, msg % str(e)


def scheduleMirReq(srvObj,
                   instanceId,
                   fileId,
                   fileVersion,
                   ingestionDate,
                   srvListId,
                   xmlFileInfo):
    """
    Schedule a new Mirroring Request in the DB Mirroring Queue and the
    Mirroring Queue DBM.
    
    srvObj:         Reference to server object (ngamsServer).

    instanceId:     ID for instance controlling the mirroring (string).
    
    fileId:         NGAS ID of file (string).
    
    fileVersion:    NGAS version of file (integer).

    ingestionDate:  NGAS ingestion date reference for file (string/ISO 8601).

    srvListId:      Server list ID for this request indicating the nodes to
                    contact to obtain this file (string).

    xmlFileInfo:    The XML file information for the file (string/XML).
    
    Returns:        Void.    
    """
    T = TRACE()

    mirReqObj = ngamsMirroringRequest.ngamsMirroringRequest().\
                setInstanceId(instanceId).\
                setFileId(fileId).\
                setFileVersion(fileVersion).\
                setIngestionDate(ingestionDate).\
                setSrvListId(srvListId).\
                setStatus(ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_SCHED).\
                setXmlFileInfo(xmlFileInfo)
    info(3, "Scheduling data object for mirroring: %s" %\
         mirReqObj.genSummary())
    srvObj.getDb().writeMirReq(mirReqObj)
    addEntryMirQueue(srvObj, mirReqObj, updateDb = False)


def getMirRequestFromQueue(srvObj):
    """
    Get the next Mirroring Request from the Mirroring Request Queue.
    If there are no requests in the queue, None is returned.

    The entries are removed (popped) from the queue.

    srvObj:     Reference to server object (ngamsServer).

    Returns:    Next Mirroring Request Object or None
                (ngamsMirroringRequest | None).
    """
    T = TRACE()
    
    try:
        srvObj._mirQueueDbmSem.acquire()
        nextKey = ((srvObj._mirQueueDbm.get(NGAMS_MIR_DBM_POINTER) + 1) %\
                   NGAMS_MIR_DBM_MAX_LIMIT)
        if (srvObj._mirQueueDbm.hasKey(str(nextKey))):
            mirReqObj = srvObj._mirQueueDbm.get(str(nextKey))
            srvObj._mirQueueDbm.\
                                  add(NGAMS_MIR_DBM_POINTER, nextKey).\
                                  rem(str(nextKey)).sync()
        else:
            mirReqObj = None
        srvObj._mirQueueDbmSem.release()
        return mirReqObj
    
    except Exception, e:
        srvObj._mirQueueDbmSem.release()
        msg = "Error adding new element to DBM Mirroring Queue. Error: %s" %\
              str(e)
        raise Exception, msg
    

def startMirroringThreads(srvObj):
    """
    Start the Mirroring Threads according to the configuration.
    
    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()

    for thrNo in range(1, (srvObj.getCfg().getMirroringThreads() + 1)):
        threadId = NGAMS_MIR_THR + "-" + str(thrNo)
        args = (srvObj, None)
        info(4,"Starting Mirroring Thread: %s" % threadId)
        thrHandle = threading.Thread(None, mirroringThread, threadId, args)
        thrHandle.setDaemon(0)
        thrHandle.start()


def pauseMirThreads(srvObj):
    """
    Called by the Mirroring Control Thread to request the Mirroring Threads
    to pause themselves until asked to resume.
    
    srvObj:     Reference to server object (ngamsServer).

    Returns:    Void.
    """
    T = TRACE()

    srvObj._pauseMirThreads = True
    # Wait for all threads to enter pause mode.
    noOfMirThreads = srvObj.getCfg().getMirroringThreads() 
    while (True):
        checkStopMirControlThread(srvObj)
        if (srvObj._mirThreadsPauseCount == noOfMirThreads):
            info(3, "All Mirroring Threads entered paused mode")
            return
        else:
            time.sleep(1.0)


def resumeMirThreads(srvObj):
    """
    Called by the Mirroring Control Thread to request the Mirroring Threads
    to resume service after they have been paused.

    srvObj:     Reference to server object (ngamsServer).

    Returns:    Void.
    """
    T = TRACE()

    srvObj._pauseMirThreads = False
    # Wait for all threads to resume service.
    noOfMirThreads = srvObj.getCfg().getMirroringThreads() 
    while (srvObj._mirThreadsPauseCount > 0):
        checkStopMirControlThread(srvObj)
        time.sleep(1.0)
    info(3, "All Mirroring Threads resumed service")
   

def pauseMirThread(srvObj):
    """
    Called by the Mirroring Threads to check if they should pause on request
    from the Mirroring Control Thread. If yes, they pause themselves until
    requested to resume or to exit the service.

    srvObj:     Reference to server object (ngamsServer).

    Returns:    Void.
    """
    T = TRACE(5)

    if (srvObj._pauseMirThreads):
        info(3, "Mirroring Thread suspending itself ...")
        srvObj._mirThreadsPauseCount += 1
        while (srvObj._pauseMirThreads):
            checkStopMirControlThread(srvObj)
            time.sleep(1.0)
        info(3, "Mirroring Thread resuming service ...")
        srvObj._mirThreadsPauseCount -= 1


def getMirRequest(srvObj,
                  timeout):
    """
    Check if there is a Mirroring Request in the queue.

    srvObj:     Reference to server object (ngamsServer).

    timeout:    Max. timeout to wait for a new request (float).

    Returns:    Return Mirroring Request Object or None if no became available
                in the specified period of time (ngamsMirroringRequest|None).
    """
    T = TRACE()
    
    srvObj.waitMirTrigger(timeout)
    mirReqObj = getMirRequestFromQueue(srvObj)
    return mirReqObj


# An internal list of local serves is kept, to avoid reading this information
# continuesly from the DB.
_localSrvList = []
_lastUpdateLocalSrvList = 0
def getLocalNauList(srvObj,
                    localSrvListCfg):
    """
    Render the list of local servers that can be contacted for handling
    the re-archiving of the files from the source archive.

    If 'localSrvListCfg' is 'ALL', all the local servers with archiving
    capability are considered. If 'localSrvListCfg' is specified, only
    these are considered. In both cases the resulting list is shuffled
    randomly to obtain some load balancing.

    srvObj:             Reference to server object (ngamsServer).

    localSrvListCfg:    List with '<Server>:<Port>,...' to be contacted for
                        re-archiving requests in the local cluster, or 'ALL'
                        (string). 

    Returns:            List of servers that can be contacted (list).
    """
    T = TRACE()

    if (localSrvListCfg == NGAMS_MIR_ALL_LOCAL_SRVS):
        # All local servers should be considered.
        # Read only the list of local servers ~every minute.
        global _localSrvList, _lastUpdateLocalSrvList
        if ((time.time() - _lastUpdateLocalSrvList) > 60):
            clusterName = srvObj.getHostInfoObj().getClusterName()
            _localSrvList = srvObj.getDb().\
                            getClusterReadyArchivingUnits(clusterName)
            _lastUpdateLocalSrvList = time.time()
        tmpSrvList = _localSrvList
    else:
        # A specific list is given.
        tmpSrvList = cleanList(localSrvListCfg.split(","))

    # Create copy of list and shuffle it.
    srvList = copy.deepcopy(tmpSrvList)
    random.shuffle(srvList)
        
    return srvList

 
def handleMirRequest(srvObj,
                     mirReqObj):
    """
    Handle a Mirroring Request: Attempt to mirror the data object associated
    to that Mirroring Request.

    srvObj:     Reference to server object (ngamsServer).

    mirReqObj:  Mirroring Request Object (ngamsMirroringRequest).
    
    Returns:    Void.
    """
    T = TRACE()

    mirReqObj.setStatus(ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ACTIVE)
    srvObj.getDb().updateStatusMirReq(mirReqObj.getFileId(),
                                      mirReqObj.getFileVersion(),
                                      ngamsMirroringRequest.\
                                      NGAMS_MIR_REQ_STAT_ACTIVE_NO)

    # Find a node to contact in the local cluster (try the whole list
    # if necessary).
    srvList = srvObj.getSrvListDic()[mirReqObj.getSrvListId()]
    mirSrcObj = srvObj.getCfg().getMirroringSrcObjFromSrvList(srvList)
    localNauList = getLocalNauList(srvObj, mirSrcObj.getTargetNodes())
    succeeded = False
    encFileInfo = base64.b64encode(mirReqObj.getXmlFileInfo())
    fileInfoObj = ngamsFileInfo.ngamsFileInfo().\
                  unpackXmlDoc(mirReqObj.getXmlFileInfo())
    errMsg = ""
    for nextNau in localNauList:
        nextLocalSrv, nextLocalPort = nextNau.split(":")
        nextLocalPort = int(nextLocalPort)

        # Cycle over the specified remote nodes in the source archive, until
        # one of them are successful.

        # Get shuffled list of nodes in the source archive to contact to
        # get a copy of the file in question.
        srcNodeList = copy.deepcopy(srvObj.getSrvListDic()[mirSrcObj.getId()])
        random.shuffle(srcNodeList)
        for srcNodeAddress in srcNodeList:
            srcHostName, srcPortNo = srcNodeAddress.split(":")
            srcPortNo = int(srcPortNo)
            
            # Send REARCHIVE Command to the next, local contact node, asking
            # it to try to collect the file from the next node in the
            # Mirroring Source Archive.
            fileUri = "http://%s:%d/RETRIEVE?file_id=%s&file_version=%d&quick_location=1"
            fileUri = fileUri % (srcHostName, srcPortNo, mirReqObj.getFileId(),
                                 mirReqObj.getFileVersion())
            cmdPars = [[NGAMS_HTTP_PAR_FILENAME, fileUri]]
            httpHdrs = [[NGAMS_HTTP_HDR_FILE_INFO, encFileInfo],
                        [NGAMS_HTTP_HDR_CONTENT_TYPE, fileInfoObj.getFormat()]]
            code, msg, hdrs, data = ngamsLib.httpGet(nextLocalSrv,
                                                     nextLocalPort,
                                                     NGAMS_REARCHIVE_CMD,
                                                     pars = cmdPars,
                                                     timeOut = 600,
                                                     additionalHdrs = httpHdrs)
            if (code == NGAMS_HTTP_SUCCESS):
                succeeded = True
                break
            else:
                # An error occurred, log error notice and go to next (if there
                # are more nodes).
                tmpStatObj = ngamsStatus.ngamsStatus().unpackXmlDoc(data)
                msg = "Error issuing REARCHIVE Command. " +\
                      "Local node: %s:%d, source contact node: %s:%d. " +\
                      "Error message: %s"
                msg = msg % (nextLocalSrv, nextLocalPort, srcHostName,
                             srcPortNo, tmpStatObj.getMessage())
                notice(msg)
                errMsg = "Last error encountered: %s" % msg
                continue

        if (succeeded): break
                
    if (not succeeded):
        mirReqObj.\
                    setStatus(ngamsMirroringRequest.\
                              NGAMS_MIR_REQ_STAT_ERR_RETRY_NO).\
                    setMessage(errMsg).\
                    setLastActivityTime(time.time())
        srvObj.getDb().updateStatusMirReq(mirReqObj.getFileId(),
                                          mirReqObj.getFileVersion(),
                                          ngamsMirroringRequest.\
                                          NGAMS_MIR_REQ_STAT_ERR_RETRY_NO)
        msg = "Error handling Mirroring Request: %s" % mirReqObj.genSummary()
        raise Exception, msg
    else:
        msg = "Successfully handled Mirroring Request: %s"
        info(3, msg % mirReqObj.genSummary())


def mirroringThread(srvObj,
                    dummy):
    """
    A number of Mirroring Threads are executing when the NGAS Mirroring Service
    is enabled to handle the requesting of data and ingestion into the local
    clster.

    srvObj:      Reference to server object (ngamsServer).

    dummy:       Needed by the thread handling ... 
    
    Returns:     Void.
    """
    T = TRACE()

    # Main loop.
    while (True):
        # Incapsulate this whole block to avoid that the thread dies in
        # case a problem occurs, like e.g. a problem with the DB connection.
        try:
            checkStopMirControlThread(srvObj)
            pauseMirThread(srvObj)
            
            info(5, "Mirroring Thread starting next iteration ...")

            ###################################################################
            # Business logic of Mirroring Thread
            ###################################################################
            try:
                # Wait for the next Mirroring Request. A timeout is applied,
                # if no request becomes available within the given timeout
                # an exception is thrown.
                mirReqObj = getMirRequest(srvObj, NGAMS_MIR_MIR_THREAD_TIMEOUT)
                if (mirReqObj):
                    handleMirRequest(srvObj, mirReqObj)
                
                    # The handling of the Mirroring Request succeeded (no
                    # exception was thrown). Put the handle in the Completed
                    # Queue.
                    mirReqObj.setStatus(ngamsMirroringRequest.\
                                        NGAMS_MIR_REQ_STAT_MIR)
                    fileVer = mirReqObj.getFileVersion()
                    mirroringStat = ngamsMirroringRequest.\
                                    NGAMS_MIR_REQ_STAT_MIR_NO
                    srvObj.getDb().updateStatusMirReq(mirReqObj.getFileId(),
                                                      fileVer, mirroringStat)
                    addEntryComplQueue(srvObj, mirReqObj)
            except Exception, e:
                if (str(e).find(NGAMS_MIR_CONTROL_THR_STOP) != -1): raise e
                msg = "Error handling Mirroring Request. Putting in Error " +\
                      "Queue. Error: %s" % str(e)
                warning(msg)
                # Put the request in the Error Queue DBM.
                statNo = ngamsMirroringRequest.\
                         NGAMS_MIR_REQ_STAT_ERR_RETRY_NO
                mirReqObj.\
                            setStatus(statNo).\
                            setMessage(str(e))
                srvObj.getDb().updateStatusMirReq(mirReqObj.getFileId(),
                                                  mirReqObj.getFileVersion(),
                                                  statNo)
                addEntryErrQueue(srvObj, mirReqObj)
            ###################################################################

        except Exception, e:
            if (str(e).find(NGAMS_MIR_CONTROL_THR_STOP) != -1): thread.exit()
            errMsg = "Error occurred during execution of the Mirroring " +\
                     "Control Thread. Exception: " + str(e)
            alert(errMsg)
            # We make a small wait here to avoid that the process tries
            # too often to carry out the tasks that failed.
            time.sleep(5.0)


def initMirroring(srvObj):
    """
    Initialize the NGAS Mirroring Service. If there are requests in the
    Mirroring Request Queue in the DB, these are read out and inserted
    in the local Mirroring Request DBM.

    srvObj:     Reference to server object (ngamsServer).

    Returns:    Void.
    """
    T = TRACE()

    # Build up the server list in the DB and the local repository kept
    # in memory.
    # The ID allocated to each Mirroring Source, is used as ID in the Server
    # List.
    for mirSrcObj in srvObj.getCfg().getMirroringSrcList():
        srvListId = srvObj.getDb().\
                    getSrvListIdFromSrvList(mirSrcObj.getServerList())
        srvObj.getSrvListDic()[srvListId] = mirSrcObj.getServerList()
        srvObj.getSrvListDic()[mirSrcObj.getServerList()] = srvListId
        # Add compiled version of the list, which is easy to use when
        # accessing the contact nodes.
        srvObj.getSrvListDic()[mirSrcObj.getId()] = mirSrcObj.\
                                                    getServerList().split(",")

    # Create the Mirroring DBM Queue.
    mirQueueDbmName = "%s/%s_%s" %\
                      (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
                       NGAMS_MIR_QUEUE_DBM, getHostId())
    rmFile("%s*" % mirQueueDbmName)
    srvObj._mirQueueDbm = ngamsDbm.ngamsDbm(mirQueueDbmName,
                                            cleanUpOnDestr = 0,
                                            writePerm = 1)
    srvObj._mirQueueDbm.\
                          add(NGAMS_MIR_DBM_COUNTER, 0).\
                          add(NGAMS_MIR_DBM_POINTER, 0)

    # Create the Error DBM Queue.
    errQueueDbmName = "%s/%s_%s" %\
                      (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
                       NGAMS_MIR_ERR_QUEUE_DBM, getHostId())
    rmFile("%s*" % errQueueDbmName)
    srvObj._errQueueDbm = ngamsDbm.ngamsDbm(errQueueDbmName,
                                            cleanUpOnDestr = 0,
                                            writePerm = 1)

    # Create the Completed DBM Queue.
    complQueueDbmName = "%s/%s_%s" %\
                        (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
                         NGAMS_MIR_COMPL_QUEUE_DBM, getHostId())
    rmFile("%s*" % complQueueDbmName)
    srvObj._complQueueDbm = ngamsDbm.ngamsDbm(complQueueDbmName,
                                              cleanUpOnDestr = 0,
                                              writePerm = 1)

    # Create the DBM to keep track of when synchronization was last done with
    # the specified Source Archives. Note this DBM is kept between sessions
    # to avoid too frequent complete syncrhonization checks.
    srcArchInfoDbm = "%s/%s_%s" %\
                     (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
                      NGAMS_MIR_SRC_ARCH_INF_DBM, getHostId())
    srvObj._srcArchInfoDbm = ngamsDbm.ngamsDbm(srcArchInfoDbm,
                                               cleanUpOnDestr = 0,
                                               writePerm = 1)
    # Update the Mirroring Source Archive DBM.
    for mirSrcObj in srvObj.getCfg().getMirroringSrcList():
        if (not srvObj._srcArchInfoDbm.hasKey(mirSrcObj.getId())):
            srvObj._srcArchInfoDbm.add(mirSrcObj.getId(), mirSrcObj)
        else:
            dbmMirSrcObj = srvObj._srcArchInfoDbm.get(mirSrcObj.getId())
            mirSrcObj.setLastSyncTime(dbmMirSrcObj.getLastSyncTime())
            srvObj._srcArchInfoDbm.add(mirSrcObj.getId(), mirSrcObj)
    
    # Restore the previous state of the mirroring from the DB Mirroring Queue
    # (if the service was interrupted).
    mirQCursor = srvObj.getDb().dumpMirroringQueue()
    while (True):
        mirReqInfoList = mirQCursor.fetch(10000)
        if (not mirReqInfoList): break
        for mirReqInfo in mirReqInfoList:
            mirReqObj = srvObj.getDb().unpackMirReqSqlResult(mirReqInfo)
            info(4, "Restoring Mirroring Request: %s" % mirReqObj.genSummary())
            # Add entry in the Mirroring DBM Queue?
            if (mirReqObj.getStatusAsNo() in
                (ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_SCHED_NO,
                 ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ACTIVE_NO)):
                addEntryMirQueue(srvObj, mirReqObj)
            # Add entry in the Error DBM Queue?
            elif (mirReqObj.getStatusAsNo() ==
                  ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ERR_RETRY_NO):
                addEntryErrQueue(srvObj, mirReqObj)
            # Add entry in the Completed DBM Queue?
            elif (mirReqObj.getStatusAsNo() in
                  (ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_MIR_NO,
                   ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_REP_NO,
                   ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ERR_ABANDON_NO)):
                addEntryComplQueue(srvObj, mirReqObj, updateDb = False)

  
def retrieveFileList(srvObj,
                     mirSrcObj,
                     node,
                     port,
                     statusCmdPars,
                     clusterFilesDbmName):
    """
    Retrieve and handle the information in connection with the STATUS?file_list
    request.

    srvObj:               Reference to server object (ngamsServer).

    mirSrcObj:            Mirroring Source Object associated with the NGAS
                          Cluster contacted (ngamsMirroringSource).
    
    node:                 NGAS host to contact (string).
    
    port:                 Port used by NGAS instance to contact (integer).
    
    statusCmdPars:        HTTP parameters for the STATUS Command (list).

    clusterFilesDbmName:  Name of the DBM containing a snapshot of all files
                          stored in the name space of the local cluster
                          (string).

    Returns:              Void
    """
    T = TRACE()
    
    # Send the STATUS?file_list query. Receive the data into a temporary file.
    rawFileListCompr = "%s/%s_%s.gz" %\
                       (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
                        NGAMS_MIR_FILE_LIST_RAW, getHostId())
   

    fileListId = None
    try:
        clusterFilesDbm = ngamsDbm.ngamsDbm(clusterFilesDbmName,
                                            cleanUpOnDestr = 0, writePerm = 1)
        
        # Retrieve the file info from the specified contact nodes and
        # schedule the files relevant.
        remainingEls = None
        while (True):
            rmFile("%s*" % rawFileListCompr[:-3])
            httpCode, httpStatus, httpHeaders, data =\
                      ngamsLib.httpGet(node, port, NGAMS_STATUS_CMD,
                                       pars = statusCmdPars,
                                       dataTargFile = rawFileListCompr,
                                       timeOut = 1800)
            if (httpCode != NGAMS_HTTP_SUCCESS):
                rmFile("%s*" % rawFileListCompr[:-3])
                statObj = ngamsStatus.ngamsStatus().unpackXmlDoc(data)
                msg = "Error accessing NGAS Node: %s/%d. Error: %s"
                raise Exception, msg % (node, port, statObj.getMessage())

            # Decompress the file (it is always transferred compressed).
            fileListRaw = decompressFile(rawFileListCompr)

            # Get the File List ID in connection with this request if not
            # already extracted.
            # Get the number of remaining items to retrieve info about.
            # It is necessary to scan through the beginning of the file to
            # get the FileList Element, which contains this information.
            # The entry looks something like this:
            #
            # <FileList Id="a8f2cbdb705899588468f72986c813ab"
            #           Status="REMAINING_DATA_OBJECTS: 1453">
            fo = open(fileListRaw)
            count = 0
            while (count < 100):
                nextLine = fo.readline()
                if (nextLine.find("FileList Id=") != -1):
                    lineEls = cleanList(nextLine.strip().split(" "))
                    if (not fileListId):
                        fileListId = lineEls[1].split("=")[1].strip('"')
                        statusCmdPars.append([NGAMS_HTTP_PAR_FILE_LIST_ID,
                                              fileListId])
                    remainingEls = int(cleanList(lineEls)[-1].split('"')[0])
                    break
                count += 1
            msg = "Retrieving File List. File List ID: %s. " +\
                  "Remaining Elements: %d"
            info(4, msg % (fileListId, remainingEls))
            if (count == 100):
                msg = "Illegal file list received as response to " +\
                      "STATUS?file_list Request"
                raise Exception, msg
            fo.seek(0)

            # Read out the file info and figure out whether to schedule it
            # for mirroring or not (file referenced by File ID + Version),
            # if this file is:
            #
            # - being mirrored already (if it is queued): Skip.
            #
            # - available in the local cluster name space: Skip.
            #
            # - not already available in local cluster name space: Schedule it.
            while (True):
                nextLine = fo.readline()
                if (nextLine == ""): break
                if (nextLine.find("FileStatus AccessDate=") != -1):
                    tmpFileObj = ngamsFileInfo.ngamsFileInfo().\
                                 unpackXmlDoc(nextLine)
                    fileKey = ngamsLib.genFileKey(None, tmpFileObj.getFileId(),
                                                  tmpFileObj.getFileVersion())
                    # Entry found in the
                    # - Mirroring DBM Queue?
                    # - Error DBM Queue?
                    # - Completed DBM Queue?
                    # Are there enough local copies in the cluster name space?
                    msg = "Checking whether to schedule file: %s/%d for " +\
                          "mirroring ..."
                    info(4, msg % (tmpFileObj.getFileId(),
                                   tmpFileObj.getFileVersion()))
                    if (srvObj._mirQueueDbm.hasKey(fileKey)):
                        continue
                    elif (srvObj._errQueueDbm.hasKey(fileKey)):
                        continue
                    elif (srvObj._complQueueDbm.hasKey(fileKey)):
                        continue
                    else:
                        # Check if the file is available in the name space of
                        # this cluster. If not, schedule it.
                        if (not clusterFilesDbm.hasKey(fileKey)):
                            # The data object is not available, schedule it!
                            srvListIdDb = srvObj.getSrvListDic()\
                                          [mirSrcObj.getServerList()]
                            scheduleMirReq(srvObj, getHostId(),
                                           tmpFileObj.getFileId(),
                                           tmpFileObj.getFileVersion(),
                                           tmpFileObj.getIngestionDate(),
                                           srvListIdDb, nextLine)

            # Stop if there are no more elements to read out.
            if (remainingEls == 0): break

    except Exception, e:
        msg = "Error retrieving file list. Error: %s"
        raise Exception, msg % str(e)
    
    
def checkSourceArchives(srvObj):
    """
    Check the source archives to see if data is available for mirroring.
    
    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()

    # Dump the information for all files managed by this cluster.
    clusterName = srvObj.getDb().getClusterNameFromHostId(getHostId())
    clusterFilesDbmName = "%s/%s_%s" %\
                          (ngamsHighLevelLib.\
                           getNgasChacheDir(srvObj.getCfg()),
                           NGAMS_MIR_CLUSTER_FILE_DBM, clusterName)
    clusterFilesDbmName = os.path.normpath(clusterFilesDbmName)
    # Dump information about files registered in this cluster.
    # Use the file key as key in the DBM, count occurrences of each file.
    clusterFilesDbmName = srvObj.getDb().\
                          dumpFileInfoCluster(clusterName,
                                              clusterFilesDbmName,
                                              useFileKey = True,
                                              count = True)

    # Loop over the various Mirroring Source Archives specified in the
    # configuration.
    for mirSrcObj in srvObj.getCfg().getMirroringSrcList():
        dbmMirSrcObj = srvObj._srcArchInfoDbm.get(mirSrcObj.getId())

        # Figure out if a partial or complete sync should be done for this
        # mirroring source.
        timeNow = time.time()
        doPartialSync = False
        doComplSync = False
        if (mirSrcObj.getCompleteSyncList()):
            # OK, it is specified to do complete sync's in the configuration.
            timeNowTag = "%s_TIME_NOW" % getAsciiTime(timeSinceEpoch = timeNow,
                                                      precision = 0)
            # Find the last time stamp compared to now.
            tmpComplSyncList = copy.deepcopy(mirSrcObj.getCompleteSyncList())
            tmpComplSyncList.append(timeNowTag)
            tmpComplSyncList.sort()
            timeNowIdx = tmpComplSyncList.index(timeNowTag)
            # Get the closest sync. time handle (from the configuration)
            # compared to the present time.
            relevantSyncTime = tmpComplSyncList[timeNowIdx - 1]
            lastComplSync =\
                          dbmMirSrcObj.\
                          getLastCompleteSyncDic()[relevantSyncTime]
            if (not lastComplSync):
                # The sync time for that cfg. sync entry is None -> no sync
                # yet done for that sync time, just do it.
                doComplSync = True
            else:
                # Check if a complete sync for the relevant time was done
                # within the last 24 hours.
                dateNow = timeNowTag.split("_")[0]
                dateLastSync = lastComplSync.split("T")[0]
                if (dateNow > dateLastSync): doComplSync = True

        # Figure out if a partial sync should be done if not a complete sync
        # should be carried out.
        if (not doComplSync):
            lastPartialSyncSecs = iso8601ToSecs(dbmMirSrcObj.getLastSyncTime())
            if ((timeNow - lastPartialSyncSecs) >= dbmMirSrcObj.getPeriod()):
                doPartialSync = True

        # If no synchronization to be done for this source, continue to the
        # next mirroring source.
        if ((not doPartialSync) and (not doComplSync)): continue

        # Complete sync: Don't specify a lower limit ingestion date.
        # Partial sync:  Specify lower limit ingestion date.
        # TODO: For now only ingestion date is supported as selection criteria.
        if (getTestMode()):
            maxEls = 10
        else:
            maxEls = 100000
        statusCmdPars = [[NGAMS_HTTP_PAR_FILE_LIST, 1],
                         [NGAMS_HTTP_PAR_UNIQUE, 1],
                         [NGAMS_HTTP_PAR_MAX_ELS, maxEls]]
        if (doPartialSync):
            statusCmdPars.append([NGAMS_HTTP_PAR_FROM_ING_DATE,
                                  dbmMirSrcObj.getLastSyncTime()])

        # Go through the list, we shuffle it to get some kind of load balancing
        srvListIndexes = range(len(srvObj.getSrvListDic()[mirSrcObj.getId()]))
        random.shuffle(srvListIndexes)
        for srvIdx in srvListIndexes:
            nextSrv, nextPort = srvObj.\
                                getSrvListDic()[mirSrcObj.getId()][srvIdx].\
                                split(":")
            nextPort = int(nextPort)
            msg = "Sending STATUS/file_list request to Source Archive: %s. " +\
                  "Node: %s/%d"
            if (doComplSync):
                msg += ". Complete synchronization"
            else:
                msg += ". Partial synchronization from date: %s" %\
                       dbmMirSrcObj.getLastSyncTime()
            info(4, msg % (mirSrcObj.getId(), nextSrv, nextPort)) 
            try:
                retrieveFileList(srvObj, mirSrcObj, nextSrv, nextPort,
                                 statusCmdPars, clusterFilesDbmName)
                # The retrieval of the file list was successful, we don't need
                # to contacting others of the specified contact nodes.
                break
            except Exception, e:
                # Create log entry in case it was not possible to communicate
                # to this Mirroring Source Archive. Continue to the next
                # Mirroring Source Archive in that case.
                msg = "Error sending STATUS/file_list to Mirroring Source " +\
                      "Archive with ID: %s (%s:%d). Error: %s"
                notice(msg % (mirSrcObj.getId(), nextSrv, nextPort, str(e)))
                # Try the next contact node specified in the cfg.
                continue
            
        # Register the times for the last partial or complete sync.
        if (doComplSync):
            dbmMirSrcObj.\
                           getLastCompleteSyncDic()[relevantSyncTime] =\
                           timeRef2Iso8601(timeNow)
            # Fair enough to consider that a partial sync been done when a
            # complete sync has been carried out.
            dbmMirSrcObj.setLastSyncTime(timeNow)
        elif (doPartialSync):
            dbmMirSrcObj.setLastSyncTime(timeNow)

        # Store the updated Source Archive Object back into the Source
        # Archive DBM.
        srvObj._srcArchInfoDbm.add(mirSrcObj.getId(), dbmMirSrcObj).sync()

    # Signal to the Mirroring Threads that there might be new Mirroring
    # Requests to handle.
    srvObj.triggerMirThreads()


def checkErrorQueue(srvObj):
    """
    Check the Error Queue for failing Mirroring Requests to reschedule into 
    the internal DB Mirroring Queue.
    
    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()

    # Go through the list of entries in the Error Queue. Handle as follows:
    #
    # - For entries marked as Error/Reschedule:
    #
    #   - If the time since last activity time is larger than the
    #     ErrorRetryPeriod specified in the configuration, put these back into
    #     the Mirroring Queue.
    #
    #   - If the ErrorRetryTimeOut has expired, leave the entry in the queue
    #     for the reporting.
    #
    # - For entries marked as Error/Abandon: Leave these in the queue to be
    #   handled later by the reporting.
    
    # We create a snapshot of the keys in the Error DBM, so that we can
    # pass through these without interferring with other activities, and
    # to avoid creating a maybe huge list in memory.
    dbmName = "%s/%s_%s" %\
              (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
               "NGAMS_MIR_ERR_QUEUE_KEYS_DBM",
               srvObj.getHostInfoObj().getClusterName())
    dbmName = dumpKeysQueue(srvObj, srvObj._errQueueDbm,
                            srvObj._errQueueDbmSem, dbmName)
    errQueueKeysDbm = ngamsDbm.ngamsDbm(dbmName, cleanUpOnDestr = True)
    errQueueKeysDbm.initKeyPtr()
    while (True):
        nextKey, data = errQueueKeysDbm.getNext()
        if (not nextKey): break
        try:
            mirReqObj = srvObj._errQueueDbm.get(nextKey)
        except:
            # Maybe this entry was removed by the reporting, ignore, continue
            # to the next entry.
            continue
        if (mirReqObj.getStatusAsNo() ==
            ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ERR_RETRY_NO):
            # If the time since last activity is longer than ErrorRetryPeriod
            # reschedule the request into the Mirroring Queue.
            timeNow = time.time()
            if ((timeNow - iso8601ToSecs(mirReqObj.getLastActivityTime())) >
                srvObj.getCfg().getMirroringErrorRetryPeriod()):
                try:
                    mirReqObj = popEntryQueue(srvObj, mirReqObj,
                                              srvObj._errQueueDbm,
                                              srvObj._errQueueDbmSem)
                    addEntryMirQueue(srvObj, mirReqObj)
                except Exception, e:
                    msg = "Error moving Mirroring Request from Error DBM " +\
                          "Queue to the Mirroring DBM Queue: %s"
                    notice(msg % str(e))
        else:
            # NGAMS_MIR_REQ_STAT_ERR_ABANDON_NO: Do nothing.
            pass

    srvObj.triggerMirThreads()


def generateReport(srvObj):
    """
    Check the queues and report the Mirroring Requests in the

      - Mirroring Queue.
      - Completed Queue.
      - Error Queue.

    A summary report and a detailed report is generated.

    srvObj:     Reference to server object (ngamsServer).
    
    Returns:    Void.
    """
    T = TRACE()

    reportHdr = "Date:         %s\n" +\
                "Control Node: %s\n\n"
    reportHdr = reportHdr % (timeRef2Iso8601(time.time()), getHostId())
    summary   = "NGAS MIRRORING - SUMMARY REPORT\n\n" + reportHdr
    # TODO: Generate detailed report in file.
    report    = "NGAS MIRRORING - SUMMARY\n\n" + reportHdr

    # Go through the various queue DBMs.
    dbmName = "%s/%s_%s" %\
              (ngamsHighLevelLib.getNgasChacheDir(srvObj.getCfg()),
               "NGAMS_MIR_REPORINTG_QUEUE_KEYS_DBM",
               srvObj.getHostInfoObj().getClusterName())
    
    # Go through Completed Queue.
    dbmName = dumpKeysQueue(srvObj, srvObj._complQueueDbm,
                            srvObj._complQueueDbmSem, dbmName)
    complQueueKeysDbm = ngamsDbm.ngamsDbm(dbmName, cleanUpOnDestr = True)
    complQueueKeysDbm.initKeyPtr()
    completedCount = 0
    while (True):
        nextKey, mirReqObj = complQueueKeysDbm.getNext()
        if (not nextKey): break
        try:
            mirReqObj = popEntryQueue(srvObj, mirReqObj,
                                      srvObj._complQueueDbm,
                                      srvObj._complQueueDbmSem)
            completedCount += 1
        except Exception, e:
            msg = "Error popping Mirroring Request from the Completed " +\
                  "DBM Queue: %s"
            notice(msg % str(e))
    summary += "Completed Requests:    %d\n" % completedCount

    # Go through Error Queue.
    dbmName = dumpKeysQueue(srvObj, srvObj._errQueueDbm,
                            srvObj._errQueueDbmSem, dbmName)
    errRetryCount = 0
    errTimeoutCount = 0
    errAbandonCount = 0
    errQueueKeysDbm = ngamsDbm.ngamsDbm(dbmName, cleanUpOnDestr = True)
    errQueueKeysDbm.initKeyPtr()
    while (True):
        nextKey, mirReqObj = errQueueKeysDbm.getNext()
        if (not nextKey): break
        if (mirReqObj.getStatusAsNo() ==
            ngamsMirroringRequest.NGAMS_MIR_REQ_STAT_ERR_ABANDON):
            try:
                mirReqObj = popEntryQueue(srvObj, mirReqObj,
                                          srvObj._errQueueDbm,
                                          srvObj._errQueueDbmSem)
                errAbandonCount += 1
            except Exception, e:
                msg = "Error popping Mirroring Request from Error DBM " +\
                      "Queue: %s"
                notice(msg % str(e))
        elif ((time.time() - iso8601ToSecs(mirReqObj.getSchedulingTime())) >
              srvObj.getCfg().getMirroringErrorRetryPeriod()):
            try:
                mirReqObj = popEntryQueue(srvObj, mirReqObj,
                                          srvObj._errQueueDbm,
                                          srvObj._errQueueDbmSem)
                errTimeoutCount += 1
            except Exception, e:
                msg = "Error popping Mirroring Request from Error DBM " +\
                      "Queue: %s"
                notice(msg % str(e))
        else:
            errRetryCount += 1
    summary += "Error Request/Retry:   %d\n" % errRetryCount
    summary += "Error Request/Timeout: %d\n" % errTimeoutCount
    summary += "Error Request/Abandon: %d\n" % errAbandonCount

    # Go through Mirroring Queue.
    dbmName = dumpKeysQueue(srvObj, srvObj._mirQueueDbm,
                            srvObj._mirQueueDbmSem, dbmName)
    mirQueueKeysDbm = ngamsDbm.ngamsDbm(dbmName, cleanUpOnDestr = True)
    mirQueueKeysDbm.initKeyPtr()
    mirQueueCount = 0
    while (True):
        nextKey, mirReqObj = mirQueueKeysDbm.getNext()
        if (not nextKey): break
        mirQueueCount += 1
    summary += "Mirroring Queue:    %d\n" % mirQueueCount

    # Submit report to the specified recipients.
    if (srvObj.getCfg().getMirroringReportRecipients()):
        repRecipients = str(srvObj.getCfg().getMirroringReportRecipients()).\
                        strip()
        if (not repRecipients): return
        subject = "NGAS MIRRORING SERVICE STATUS REPORT"
        for recipient in repRecipients.split(","):
            ngamsHighLevelLib.sendEmail(srvObj.getCfg(),
                                        srvObj.getCfg().getNotifSmtpHost(),
                                        subject, [recipient],
                                        srvObj.getCfg().getSender(), summary,
                                        "text/plain")

def cleanUpMirroring(srvObj):
    host = get_full_qualified_name(srvObj)
    info(1, "cleaning up mirroring tasks for ngas node: " + host)
    sql = "update ngas_mirroring_bookkeeping set status = 'ABORTED', staging_file = null where status = 'READY' and target_host = '" + host + "'"
    srvObj.getDb().query(sql)
    sql = "update ngas_mirroring_bookkeeping set status = 'TORESUME' where status = 'FETCHING' and target_host = '" + host + "'"
    srvObj.getDb().query(sql)

def get_full_qualified_name(srvObj):
    """
    Get full qualified server name for the input NGAS server object
    
    INPUT:
        srvObj  ngamsServer, Reference to NG/AMS server class object 
    
    RETURNS:
        fqdn    string, full qualified host name (host name + domain + port)
    """

    # Get hots_id, domain and port using ngamsLib functions
    host_id = getHostId()
    domain = ngamsLib.getDomain()
    port = str(srvObj.getCfg().getPortNo())
    # Concatenate all elements to construct full qualified name
    # Notice that host_id may contain port number
    fqdn = (host_id.rsplit(":"))[0] + "." + domain + ":" + port

    # Return full qualified server name
    return fqdn


def mirControlThread(srvObj,
                     dummy):
    """
    The Mirroring Control Thread runs periodically when the NG/AMS Server is
    Online (if enabled) to synchronize the data holding of the local NGAS
    Cluster against a set of remote NGAS Clusters.

    srvObj:      Reference to server object (ngamsServer).

    dummy:       Needed by the thread handling ... 
    
    Returns:     Void.
    """
    T = TRACE()

    info(3, "ALMA Mirroring Control Thread cleaning up from previous state")
    cleanUpMirroring(srvObj)
    
    # Don't execute the thread if deactivated in the configuration.
    if (not srvObj.getCfg().getMirroringActive()):
        info(1, "NGAS Mirroring not active - Mirroring Control Thread " +\
             "terminating with no actions")
        thread.exit()

    # Alma Mirroring Service
    if (srvObj.getCfg().getVal("Mirroring[1].AlmaMirroring")):
        info(1, "ALMA Mirroring is enabled")
        info(2, "ALMA Mirroring Control Thread entering main server loop")
        sleepTime = getMirroringSleepTime(srvObj)
        info(2, "ALMA Mirroring Control Thread waiting for %ss before starting" % sleepTime)
        time.sleep(float(sleepTime))
        while (True):
            # Incapsulate this whole block to avoid that the thread dies in
            try:
                checkStopMirControlThread(srvObj)
                info(2, "ALMA Mirroring Control Thread starting next iteration ...")

                # Update mirroring book keeping table
                info(3, "ALMA Mirroring Control Thread updating book keeping table ...")
                local_server_full_qualified_name = get_full_qualified_name(srvObj)
                target_node_conn = httplib.HTTPConnection(local_server_full_qualified_name)
                target_node_conn.request("GET", "MIRRTABLE")
                response = target_node_conn.getresponse()

                # Sleep to let Janitor Thread and DCC do their tasks
                # always reload from DB to allow for updates without restarting the server
                sleepTime = getMirroringSleepTime(srvObj)

                info(2, "ALMA Mirroring Control Thread sleeping for %ss" % sleepTime)
                time.sleep(float(sleepTime))
            except Exception, e:
                if (str(e).find(NGAMS_MIR_CONTROL_THR_STOP) != -1): thread.exit()
                errMsg = "Error occurred during execution of the ALMA Mirroring " +\
                         "Control Thread. Exception: " + str(e)
                alert(errMsg)
                # We make a small wait here to avoid that the process tries
                # too often to carry out the tasks that failed.
                time.sleep(5.0)
            finally:
                target_node_conn.close()
    
    # Generic Mirroring service
    else:
        # Initialize the mirroring service.
        initMirroring(srvObj)


        # Start the Mirroring Threads.
        startMirroringThreads(srvObj)

        # Render the suspension time as the minimum time for checking a remote
        # archive.
        period = (24 * 3600)
        for mirSrcObj in srvObj.getCfg().getMirroringSrcList():
            tmpPeriod = float(mirSrcObj.getPeriod())
            if (tmpPeriod < period): period = tmpPeriod

        info(2, "Mirroring Control Thread entering main server loop")
        while (True):
            startTime = time.time()
        
            # Incapsulate this whole block to avoid that the thread dies in
            # case a problem occurs, like e.g. a problem with the DB connection.
            try:
                checkStopMirControlThread(srvObj)
                info(5, "Mirroring Control Thread starting next iteration ...")

                ###################################################################
                # Business logic of Mirroring Control Thread
                ###################################################################

                # Check if there are new data objects in the specified source
                # archives to mirror. While checking this the Mirroring Threads
                # should be paused, since otherwise, inconsistencies may occurr
                # (e.g. a file scheduled several times).
                try:
                    pauseMirThreads(srvObj)
                    checkSourceArchives(srvObj)
                except Exception, e:
                    if (str(e).find(NGAMS_MIR_CONTROL_THR_STOP) != -1): raise e
                resumeMirThreads(srvObj)

                # Check if there are entries in Error State, which should be
                # resumed.
                checkErrorQueue(srvObj)

                # Check if there entries to be reported in the queues and generate
                # the report(s).
                generateReport(srvObj)
                ###################################################################
 
                ###################################################################
                # Suspend the Mirroring Control Thread for a while.
                ###################################################################
                suspTime = (period - (time.time() - startTime))
                if (suspTime < 1): suspTime = 1
                info(3, "Mirroring Control Thread executed - suspending for " +\
                      str(suspTime) + "s ...")
                suspStartTime = time.time()
                while ((time.time() - suspStartTime) < suspTime):
                    checkStopMirControlThread(srvObj)
                    time.sleep(0.250)
                ###################################################################
                    
            except Exception, e:
                if (str(e).find(NGAMS_MIR_CONTROL_THR_STOP) != -1): thread.exit()
                errMsg = "Error occurred during execution of the Mirroring " +\
                         "Control Thread. Exception: " + str(e)
                alert(errMsg)
                # We make a small wait here to avoid that the process tries
                # too often to carry out the tasks that failed.
                time.sleep(5.0)

def getMirroringSleepTime(srvObj):
    query = "select cfg_val"
    query += " from ngas_cfg_pars"
    query += " where cfg_par = 'sleepTime'"

    # Execute query 
    info(3, "Executing SQL query to get mirroring sleep time: %s" % query)
    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    sleepTime = str(res[0][0][0])

    # Log info
    info(3, "result is " + sleepTime)

    # Return void
    return sleepTime

# EOF
