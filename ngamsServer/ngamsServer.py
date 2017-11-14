#!/opsw/util/python/bin/python

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
# "@(#) $Id: ngamsServer.py,v 1.35 2012/03/03 21:25:43 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  07/05/2001  Created
#

"""
This module contains the class ngamsServer that provides the
services for the NG/AMS Server.
"""

import os, sys, re, string, threading, time, glob, cPickle, base64, types
import thread, traceback
import SocketServer, BaseHTTPServer, socket, signal

import pcc, PccUtTime

from   ngams import *
import ngamsLib, ngamsHighLevelLib
import ngamsDbm, ngamsDb, ngamsConfig, ngamsReqProps
import ngamsDiskUtils, ngamsStatus
import ngamsDiskInfo, ngamsFileInfo, ngamsHostInfo, ngamsPlugInApi
import ngamsArchiveUtils, ngamsSrvUtils, ngamsCmdHandling
import ngamsNotification, ngamsAuthUtils

# jagonzal: Add queues for the mirroring insert and update statements
from Queue import *


# Pointing to the HTTP request callback.
_reqCallBack = None


# Refers to the instance of the NG/AMS Server. Used to access the
# server instance e.g. from the NG/AMS Exit Handler.
_ngamsServer = None

   
def ngamsExitHandler(signalNo,
                     frameObject = "",
                     killServer = 1,
                     exitCode = 0,
                     delPidFile = 1):
    """
    NG/AMS Exit Handler Function. Is invoked when the NG/AMS Server
    is killed/terminated.

    signalNo:     Number of signal received.

    frameObject:  Frame object (string).

    killServer:   1 = kill the server (integer).

    exitCode:     Exit code with which the server should exit (integer).

    delPidFile:   Flag indicating if NG/AMS PID file should be deleted or
                  not (integer/0|1).
                 
    Returns:      Void. 
    """
    global _ngamsServer
    ngamsSrvUtils.ngamsBaseExitHandler(_ngamsServer, signalNo, killServer,
                                       exitCode, delPidFile)


class ngamsSimpleRequest:
    """
    Small class to provide minimal HTTP Request Handler functionality.
    """

    def __init__(self,
                 request,
                 clientAddress):
        """
        Constructor method.
        """
        self.rbufsize = -1
        self.wbufsize = 0
        self.connection = request
        self.client_address = clientAddress
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.wfile = self.connection.makefile('wb', self.wbufsize)

    
    def send_header(self,
                    keyword,
                    value):
        """
        Send an HTTP header.
        
        keyword:    HTTP header keyword (string).

        value:      Value for the HTTP header keyword (string).
        """
        self.wfile.write("%s: %s\r\n" % (keyword, value))


# class ngamsHttpServer(SocketServer.ForkingMixIn,
#                      SocketServer.TCPServer,
#                      BaseHTTPServer.HTTPServer):
class ngamsHttpServer(SocketServer.ThreadingMixIn,
                      SocketServer.TCPServer,
                      BaseHTTPServer.HTTPServer):
    """  
    Class that provides the multithreaded HTTP server functionality.sim
    """
    allow_reuse_address = 1

    
    def process_request(self,
                        request,
                        client_address):
        """
        Start a new thread to process the request.
        """
        # Check the number of requests being handled. It is checked already
        # here to avoid starting another thread.
        noOfAliveThr = 0
        for thrObj in threading.enumerate():
            try:
                if (thrObj.isAlive()): noOfAliveThr += 1
                info(4, 'XTHREAD: ' + str(thrObj.isAlive()) + ': ' + str(thrObj))
            except Exception, e:
                pass
        if (_ngamsServer):
            if ((noOfAliveThr - 4) >= _ngamsServer.getCfg().getMaxSimReqs()):
                try:
                   errMsg = genLog("NGAMS_ER_MAX_REQ_EXCEEDED",
                                [_ngamsServer.getCfg().getMaxSimReqs()])
                   error(errMsg)
                   httpRef = ngamsSimpleRequest(request, client_address)
                   tmpReqPropsObj = ngamsReqProps.ngamsReqProps()
                   _ngamsServer.reply(tmpReqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                                   NGAMS_FAILURE, errMsg)
                except IOError:
                   errMsg = "Maximum number of requests exceeded and I/O ERROR encountered! Trying to continue...."
                   error(errMsg)
                return

        # Create a new thread to handle the request.
        t = threading.Thread(target = self.finish_request,
                             args = (request, client_address))
        t.start()


    def handle_request(self):
        """
        Handle a request.
        """
        T = TRACE(5)
        
        try:
            request, client_address = self.get_request()
        except socket.error:
            info(5,"handle_request() - socket.error")
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.close_request(request)


class ngamsHttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    Class used to handle an HTTP request.
    """

    def finish(self):
        """
        Finish the handling of the HTTP request.
        
        Returns:    Void.
        """
        try:
            self.rfile.close()
        except:
            pass
        try:
            self.wfile.flush()
            self.wfile.close()
        except:
            pass    
        try:
            logFlush()
        except:
            pass


    def log_request(self,
                    code = '-',
                    size = '-'):
        """
        The default log_request is not safe (it blocks) under heavy load.
        I suggest using a Queue and another thread to read from the queue
        and write it to disk as a possible solution here. A pass works for
        now, but you get no logging.

        Comment this method out to enable (unsafe) logging.

        Returns:    Void.
        """
        pass


    def do_GET(self):
        """
        Serve a GET method request.

        Returns:   Void.
        """
        self.reqHandle()

  
    def do_POST(self):
        """
        Serve a POST method request.

        Returns:    Void.
        """
        self.reqHandle()


    def reqHandle(self):
        """
        Basic, generic request handler to handle an incoming HTTP request.
        
        Returns:    Void.
        """
        global _reqCallBack
        if (_reqCallBack != None):
            path = trim(self.path, "?/ ")
            try:
                _reqCallBack(self, self.client_address, self.command, path,
                             self.request_version, self.headers,
                             self.wfile, self.rfile)
            except Exception, e:
                error(str(e))
                sysLogInfo(1,str(e))
                thread.exit()
        else:
            status = ngamsStatus.ngamsStatus()
            status.\
                     setDate(PccUtTime.TimeStamp().getTimeStamp()).\
                     setVersion(getNgamsVersion()).setHostId(getHostId()).\
                     setStatus(NGAMS_FAILURE).\
                     setMessage("NG/AMS Server not properly functioning! " +\
                                "No HTTP request callback!")
            self.send_error(NGAMS_HTTP_BAD_REQ, status.genXmlDoc())
            

class ngamsServer:
    """
    Class providing the functionality of the NG/AMS Server.
    """
    
    def __init__(self):
        """
        Constructor method.
        """
        self._serverName              = "ngamsServer"
        self.__ngamsCfg               = ""
        self.__ngamsCfgObj            = ngamsConfig.ngamsConfig()
        self.__dbCfgId                = ""
        self.__verboseLevel           = -1
        self.__locLogLevel            = -1
        self.__locLogFile             = None
        self.__sysLog                 = -1
        self.__sysLogPrefix           = NGAMS_DEF_LOG_PREFIX
        self.__force                  = 0
        self.__autoOnline             = 0
        self.__noAutoExit             = 0
        self.__multipleSrvs           = 0
        self.__ngasDb                 = None
        self.__diskDic                = None
        self.__dynCmdDic              = {}
        self.__mimeType2PlugIn        = {}
        self.__state                  = NGAMS_OFFLINE_STATE
        self.__subState               = NGAMS_IDLE_SUBSTATE
        self.__stateSem               = threading.Semaphore(1)
        self.__subStateSem            = threading.Semaphore(1)
        self.__busyCount              = 0
        self.__sysMtPtDic             = {}
        self.__partnerSites           = []

        # Server list handling.
        self.__srvListDic             = {}

        self.__httpDaemon             = None

        # General flag to control thread execution.
        self._threadRunPermission     = 0

        # Handling of the Janitor Thread.
        self._janitorThread           = None
        self._janitorThreadRunning    = 0
        self._janitorThreadRunSync    = threading.Event()
        self._janitorThreadRunCount   = 0

        # Handling of the Data Check Thread.
        self._dataCheckThread         = None
        self._dataCheckRunSync        = threading.Event()

        # Handling of the Data Subscription.
        self._subscriberDic           = {}
        self._subscriptionThread      = None
        self._subscriptionSem         = threading.Semaphore(1)
        self._backLogAreaSem          = threading.Semaphore(1)
        self._subscriptionRunSync     = threading.Event()
        self._subscriptionFileList    = []
        self._subscriptionSubscrList  = []
        self._subscriptionStopSync    = threading.Event()
        self._subscriptionStopSyncConf= threading.Event()
        self._deliveryStopSync        = threading.Event()
        self._subscrBackLogCount      = 0
        # List to keep track off to which Data Providers an NG/AMS
        # Server is subscribed.
        self._subscriptionStatusList  = []

        # Handling of the Mirroring Control Thread.
        self._mirControlThread        = None
        self._mirControlThreadRunning = 0
        self.__mirControlTrigger      = threading.Event()
        self._pauseMirThreads         = False
        self._mirThreadsPauseCount    = 0
        # - Mirroring Queue DBM.
        self._mirQueueDbm = None
        self._mirQueueDbmSem = threading.Semaphore(1)
        # - Error Queue DBM.
        self._errQueueDbm = None
        self._errQueueDbmSem = threading.Semaphore(1)
        # - Completed Queue DBM.
        self._complQueueDbm = None
        self._complQueueDbmSem = threading.Semaphore(1)
        # - Source Archive Info DBM.
        self._srcArchInfoDbm = None
        self._srcArchInfoDbmSem = threading.Semaphore(1)
       
        # Handling of User Service Plug-In.
        self._userServicePlugIn       = None
        self._userServiceRunSync      = threading.Event()

        # Handling of host info in ngas_hosts.
        self.__hostInfo               = ngamsHostInfo.ngamsHostInfo()

        # To indicate in the code where certain statments that could
        # influence the execution of the test should not be executed.
        ######self.__unitTest               = 0

        # Handling of Host Suspension.
        self.__lastReqStartTime         = 0.0
        self.__lastReqEndTime           = 0.0
        self.__nextDataCheckTime        = 0
        
        # Dictionary to keep track of the various requests being handled.
        self.__requestDbm               = None
        self.__requestDbmSem            = threading.Semaphore(1)
        self.__requestId                = 0

        # Handling of a Cache Archive.
        self._cacheArchive              = False
        self._cacheControlThread        = None
        self._cacheControlThreadRunning = False
        # - Cache Contents SQLite DBMS.
        self._cacheContDbms             = None
        self._cacheContDbmsCur          = None
        self._cacheContDbmsSem          = threading.Semaphore(1)
        self._cacheNewFilesDbm          = None
        self._cacheNewFilesDbmSem       = threading.Semaphore(1)
        self._cacheCtrlPiDbm            = None
        self._cacheCtrlPiDelDbm         = None 
        self._cacheCtrlPiFilesDbm       = None
        self._cacheCtrlPiThreadGr       = None

        # jagonzal: Create queries queue for the mirroring insert and update statements
        self.__ngas_files_queue = Queue(0)
        self.__ngas_disks_queue = Queue(0)
        self.__mirroring_bookkeeping_queue = Queue(0)
        self.__target_mirroring_disk = None
        self.__mirroring_running = 0

    def get_ngas_files_queue(self):
        return self.__ngas_files_queue
    
    def get_ngas_disks_queue(self):
        return self.__ngas_disks_queue

    def get_mirroring_bookkeeping_queue(self):
        return self.__mirroring_bookkeeping_queue

    def getMirroringRunning(self):
        #return self.__mirroring_running
        return self.__mirroring_running > 0

    def get_target_mirroring_disk(self):
        return self.__target_mirroring_disk

    def set_target_mirroring_disk(self,diskId):
        self.__target_mirroring_disk = diskId

    def setMirroringRunning(self, state):
        if state == 1:
            self.__mirroring_running += 1
        else:
            self.__mirroring_running -= 1
 
    def getLogFilename(self):
        """
        Return the filename of the Local Log File.

        Returns:   Name of the Local Log File (string).
        """
        return self.__locLogFile


    def setDb(self,
              dbObj):
        """
        Set reference to the DB connection object.

        dbObj:      Valid NG/AMS DB Connection object (ngamsDb).

        Returns:    Reference to object itself.
        """
        self.__ngasDb = dbObj
        return self


    def getDb(self):
        """
        Get reference to the DB connection object.

        Returns:    Reference to DB connection object (ngamsDb).
        """
        return self.__ngasDb


    def getCachingActive(self):
        """
        Return the value of the Caching Active Flag.

        Returns:  State of Caching Active Flag (boolean).
        """
        T = TRACE()

        return self._cacheArchive
    

    def getReqDbName(self):
        """
        Get the name of the Request Info DB (BSD DB).

        Returns:    Filename of Request Info DB (string).
        """
        ngasId = ngamsHighLevelLib.genNgasId(self.getCfg())
        cacheDir = ngamsHighLevelLib.genCacheDirName(self.getCfg())
        return os.path.normpath(cacheDir + "/" + ngasId + "_REQUEST_INFO_DB")


    def addRequest(self,
                   reqPropsObj):
        """
        Add a request handling object in the Request List (NG/AMS Request
        Properties Object).

        reqPropsObj:     Instance of the request properties object
                         (ngamsReqProps).

        Returns:         Request ID (integer).
        """
        T = TRACE()
        
        try:
            self.__requestDbmSem.acquire()
            self.__requestId += 1
            if (self.__requestId >= 1000000): self.__requestId = 1
            reqPropsObj.setRequestId(self.__requestId)
            reqObj = reqPropsObj.clone().setReadFd(None).setWriteFd(None)
            self.__requestDbm.add(str(self.__requestId), reqObj)
            self.__requestDbm.sync()
            self.__requestDbmSem.release()
            return self.__requestId
        except Exception, e:
            self.__requestDbmSem.release()
            raise e


    def updateRequestDb(self,
                        reqPropsObj):
        """
        Update an existing Request Properties Object in the Request DB.

        reqPropsObj: Instance of the request properties object (ngamsReqProps).

        Returns:     Reference to object itself.
        """
        T = TRACE()
        
        try:
            self.__requestDbmSem.acquire()
            reqId = reqPropsObj.getRequestId()
            reqObj = reqPropsObj.clone().setReadFd(None).setWriteFd(None)
            self.__requestDbm.add(str(reqId), reqObj)
            self.__requestDbm.sync()
            self.__requestDbmSem.release()
            return self
        except Exception, e:
            self.__requestDbmSem.release()
            raise e


    def getRequestIds(self):
        """
        Return a list with the Request IDs.

        Returns:    List with Request IDs (list).
        """
        return self.__requestDbm.keys() 


    def getRequest(self,
                   requestId):
        """
        Return the request handle object (ngamsReqProps) for a given
        request. If request not contained in the list, None is returned.

        requestId:     ID allocated to the request (string).

        Returns:       NG/AMS Request Properties Object or None
                       (ngamsReqProps|None).
        """
        try:
            self.__requestDbmSem.acquire()
            if (self.__requestDbm.hasKey(str(requestId))):
                retVal = self.__requestDbm.get(str(requestId))
            else:
                retVal = None
            self.__requestDbmSem.release()
            return retVal
        except Exception, e:
            self.__requestDbmSem.release()
            raise e
        

    def delRequest(self,
                   requestId):
        """
        Delete the Request Properties Object associated to the given
        Request ID.
        
        requestId:     ID allocated to the request (string).

        Returns:       Reference to object itself.
        """
        try:
            self.__requestDbmSem.acquire()
            if (self.__requestDbm.hasKey(str(requestId))):
                self.__requestDbm.rem(str(requestId))
                self.__requestDbm.sync()
            self.__requestDbmSem.release()
            return self
        except Exception, e:
            self.__requestDbmSem.release()
            raise e


    def takeStateSem(self):
        """
        Acquire the State Semaphore to request for permission to change it.
        
        Returns:    Void.
        """
        self.__stateSem.acquire()


    def relStateSem(self):
        """
        Release the State Semaphore acquired with takeStateSem().
        
        Returns:    Void.
        """
        self.__stateSem.release()


    def takeSubStateSem(self):
        """
        Acquire the Sub-State Semaphore to request for permission to change it.
        
        Returns:    Void.
        """
        self.__subStateSem.acquire()


    def relSubStateSem(self):
        """
        Release the Sub-State Semaphore acquired with takeStateSem().
        
        Returns:    Void.
        """
        self.__subStateSem.release()


    def setState(self,
                 state,
                 updateDb = True):
        """
        Set the State of NG/AMS.

        state:      State of NG/AMS (see ngams) (string).

        updateDb:   Update the state in the DB (boolean).
        
        Returns:    Reference to object itself.
        """
        self.__state = state
        self.updateHostInfo(None, None, None, None, None, None, None,
                            state, updateDb)
        return self


    def getState(self):
        """
        Get the NG/AMS State.
        
        Returns:    State of NG/AMS (string).
        """
        return self.__state


    def setSubState(self,
                    subState):
        """
        Set the Sub-State of NG/AMS.

        subState:   Sub-State of NG/AMS (see ngams) (string).
        
        Returns:    Reference to object itself.
        """
        # TODO: Change the handling of the Sub-State: Use
        #       ngamsServer.getHandlingCmd() and set the Sub-State
        #       to busy if 1 other idle. Remove ngamsServer.__busyCount.
        self.takeSubStateSem()
        if (subState == NGAMS_BUSY_SUBSTATE):
            self.__busyCount = self.__busyCount + 1
        if ((subState == NGAMS_IDLE_SUBSTATE) and (self.__busyCount > 0)):
            self.__busyCount = self.__busyCount - 1
        if ((subState == NGAMS_IDLE_SUBSTATE) and (self.__busyCount == 0)):
            self.__subState = NGAMS_IDLE_SUBSTATE
        else:
            self.__subState = NGAMS_BUSY_SUBSTATE
        self.relSubStateSem()
        return self


    def getSubState(self):
        """
        Get the Sub-State of NG/AMS.
        
        Returns:    Sub-State of NG/AMS (string).
        """
        return self.__subState


    def checkSetState(self,
                      action,
                      allowedStates,
                      allowedSubStates,
                      newState = "",
                      newSubState = "",
                      updateDb = True):
        """
        Check and set the State and Sub-State if allowed. The method checks
        if it is allowed to set the State/Sub-State, by checking the list of
        the allowed States/Sub-States against the present State/Sub-State. If
        not, an exception is raised. Otherwise if a new State/Sub-State are
        defined this/these will become the new State/Sub-State of the system.

        action:            Action for which the state change is
                           needed (string).
        
        allowedStates:     Tuple containing allowed States for
                           executing the action (tuple).
        
        allowedSubStates:  Tuple containing allowed Sub-States for
                           executing the action (tuple).
        
        newState:          If specified this will become the new State
                           of NG/AMS if state conditions allows this (string).
        
        newSubState:       If specified this will become the new Sub-State
                           of NG/AMS if state conditions allows this (string).

        updateDb:          Update the state in the DB (boolean).
        
        Returns:           Void.
        """
        T = TRACE()
        
        self.takeStateSem()
        if ((ngamsLib.searchList(allowedStates, self.getState()) == -1) or
            (ngamsLib.searchList(allowedSubStates, self.getSubState()) == -1)):
            errMsg = [action, self.getState(), self.getSubState(),
                      str(allowedStates), str(allowedSubStates)]
            errMsg = genLog("NGAMS_ER_IMPROPER_STATE", errMsg)
            self.relStateSem()
            error(errMsg)
            raise Exception, errMsg  

        if (newState != ""): self.setState(newState, updateDb)
        if (newSubState != ""): self.setSubState(newSubState)
        self.relStateSem()


    def setThreadRunPermission(self,
                               permission):
        """
        Set the Thread Run Permission Flag. A value of 1 means that
        the threads are allowed to run.

        permission:    Thread Run Permission flag (integer/0|1).

        Returns:       Reference to object itself.
        """
        self._threadRunPermission = permission
        return self


    def getThreadRunPermission(self):
        """
        Return the Thread Run Permission Flag.

        Returns:       Thread Run Permission flag (integer/0|1).
        """
        return self._threadRunPermission


    def setJanitorThreadRunning(self,
                                running):
        """
        Set the Janitor Thread Running Flag to indicate if the Janitor
        Thread is running or not.

        running:     Janitor Thread Running Flag (integer/0|1).

        Returns:     Reference to object itself.
        """
        self._janitorThreadRunning = running
        return self


    def getJanitorThreadRunning(self):
        """
        Get the Janitor Thread Running Flag to indicate if the Janitor
        Thread is running or not.

        Returns:    Janitor Thread Running Flag (integer/0|1).
        """
        return self._janitorThreadRunning


    def incJanitorThreadRunCount(self):
        """
        Increase the Janitor Thread run count.

        Returns:     Reference to object itself.
        """
        self._janitorThreadRunCount += 1
        return self


    def resetJanitorThreadRunCount(self):
        """
        Reset the Janitor Thread run count.

        Returns:     Reference to object itself.
        """
        self._janitorThreadRunCount = 0
        return self


    def getJanitorThreadRunCount(self):
        """
        Return the Janitor Thread run count.

        Returns:     Janitor Thread Run Count (integer).
        """
        return self._janitorThreadRunCount


    def triggerSubscriptionThread(self):
        """
        Trigger the Data Subscription Thread so that it carries out a
        check to see if there are file to be delivered to Subscribers.

        Returns:   Reference to object itself.
        """
        T = TRACE()
        
        self._subscriptionRunSync.set()
        return self
    

    def addSubscriptionInfo(self,
                            fileRefs = [],
                            subscrObjs = []):
        """
        It is possible to indicate that specific files should be checked
        to see if it should be delivered to Subscribers. This is used when
        a new file has been archived.

        It is also possible to specify that it should be checked for a
        specific Subscriber if there is data to be delivered to this
        specific Subscriber.

        If no file references are given nor Subscriber references, the
        Subscription Thread will make a general check if there are files
        to be delivered.

        fileRefs:     List of tuples of File IDs + File Versions to be checked
                      if they should be delivered to the Subscribers
                      (list/tuple/string).

        subscrObjs:   List of Subscriber Objects indicating that data
                      delivery should be investigated for each Subscriber
                      (list/ngamsSubscriber).

        Returns:      Reference to object itself.
        """
        T = TRACE()
        
        try:
            startTime = time.time()
            self._subscriptionSem.acquire()
            if (fileRefs != []): self._subscriptionFileList += fileRefs
            if (subscrObjs != []): self._subscriptionSubscrList += subscrObjs
            self._subscriptionSem.release()
        except Exception, e:
            self._subscriptionSem.release()
            errMsg = "Error occurred in ngamsServer." +\
                     "addSubscriptionInfo(). Exception: " + str(e)
            alert(errMsg)
            raise Exception, errMsg
        return self

    
    def incSubcrBackLogCount(self):
        """
        Increase the Subscription Back-Log Counter.

        Returns:  Current value of the Subscription Back-Log Counter (integer).
        """
        self._subscrBackLogCount += 1
        return self._subscrBackLogCount
    

    def resetSubcrBackLogCount(self):
        """
        Increase the Subscription Back-Log Counter.

        Returns:    Reference to object itself.
        """
        self._subscrBackLogCount = 0
        return self


    def getSubcrBackLogCount(self):
        """
        Get the value of the Subscription Back-Log Counter.
        
        Returns:  Current value of the Subscription Back-Log Counter (integer).
        """
        return self._subscrBackLogCount


    def getSubscrStatusList(self):
        """
        Return reference to the Subscription Status List. This list contains
        the reference to the various Data Providers to which a server has
        subscribed.
    
        Returns:     Reference to Subscription Status List (list).
        """
        return self._subscriptionStatusList


    def resetSubscrStatusList(self):
        """
        Reset the Subscription Status List. This list contains the reference
        to the various Data Providers to which a server has subscribed.
    
        Returns:     Reference to object itself.
        """
        self._subscriptionStatusList = []
        return self


    def setMirControlThreadRunning(self,
                                   running):
        """
        Set the Mirroring Control Thread Running Flag to indicate if the
        thread.

        running:     Mirroring Control Running Flag (integer/0|1).

        Returns:     Reference to object itself.
        """
        self._mirControlThreadRunning = running
        return self


    def getMirControlThreadRunning(self):
        """
        Get the Mirroring Control Thread Running Flag to indicate if the
        Mirroring Control Thread is running or not.

        Returns:    Mirroring Control Thread Running Flag (integer/0|1).
        """
        return self._mirControlThreadRunning


    def triggerMirThreads(self):
        """
        Set (trigger) the mirroring event to signal to the Mirroring
        Threads, that there is data in the queue to be handled.

        Returns:    Reference to object itself.
        """
        self.__mirControlTrigger.set()
        return self


    def waitMirTrigger(self,
                       timeout = None):
        """
        Wait for the availability of Mirroring Requests in the queue.

        timeout:    Timeout in seconds to max wait for the event (float|None).

        Returns:    Reference to object itself.
        """
        if (timeout):
            self.__mirControlTrigger.wait(timeout)
        else:
            self.__mirControlTrigger.wait()
        self.__mirControlTrigger.clear()
        return self
    

    def setCacheControlThreadRunning(self,
                                     running):
        """
        Set the Cache Control Thread Running Flag to indicate if the thread.

        running:     Cache Control Running Flag (integer/0|1).

        Returns:     Reference to object itself.
        """
        self._cacheControlThreadRunning = running
        return self


    def getCacheControlThreadRunning(self):
        """
        Get the Cache Control Thread Running Flag to indicate if the
        Cache Control Thread is running or not.

        Returns:    Cache Control Thread Running Flag (integer/0|1).
        """
        return self._cacheControlThreadRunning


    def setForce(self,
                 force):
        """
        Set the Force Execution Flag, indicating whether to force
        the server to start even if the PID file is found.

        force:    Force Flag (force = 1) (int)

        Returns:  Reference to object itself.
        """
        self.__force = int(force)
        return self


    def getForce(self):
        """
        Return the Force Execution Flag, indicating whether to force
        the server to start even if the PID file is found.

        Returns:   Force Flag (force = 1) (int)
        """
        return self.__force


    def setLastReqStartTime(self):
        """
        Register start time for handling of last request.

        Returns:      Reference to object itself.
        """
        self.__lastReqStartTime = time.time()
        return self


    def getLastReqStartTime(self):
        """
        Return the start time for last request handling initiated.

        Returns:       Absolute time for starting last request handling
                       (seconds since epoch) (float).
        """
        return self.__lastReqStartTime

    
    def setLastReqEndTime(self):
        """
        Register end time for handling of last request.

        Returns:      Reference to object itself.
        """
        self.__lastReqEndTime = time.time()
        return self


    def getLastReqEndTime(self):
        """
        Return the end time for last request handling initiated.

        Returns:       Absolute time for end last request handling
                       (seconds since epoch) (float).
        """
        return self.__lastReqEndTime


    def getHandlingCmd(self):
        """
        Identify if the NG/AMS Server is handling a request. In case yes
        1 is returned, otherwise 0 is returned.

        Returns:   1 = handling request, 0 = not handling a request
                   (integer/0|1).
        """
        # If the time for initiating the last request handling is later than
        # the time for finishing the previous request a request is being
        # handled.
        if (self.getLastReqStartTime() > self.getLastReqEndTime()):
            return 1
        else:
            return 0


    def setNextDataCheckTime(self,
                             nextTime):
        """
        Set the absolute time for when the next data check is due (seconds
        since epoch).

        nextTime:    Absolute time in seconds for scheduling the next
                     data check (integer).

        Returns:     Reference to object itself.
        """
        self.__nextDataCheckTime = int(nextTime)
        return self


    def getNextDataCheckTime(self):
        """
        Return the absolute time for when the next data check is due (seconds
        since epoch).

        Returns:  Absolute time in seconds for scheduling the next
                  data check (integer).
        """
        return self.__nextDataCheckTime


    def setAutoOnline(self,
                      autoOnline):
        """
        Set the Auto Online Flag, indicating whether to bring the
        server Online automatically, immediately after initializing.

        autoOnline:    Auto Online Flag (Auto Online = 1) (int)

        Returns:       Reference to object itself.
        """
        self.__autoOnline = int(autoOnline)
        return self


    def getAutoOnline(self):
        """
        Return the Auto Online Flag, indicating whether to bring the
        server Online automatically, immediately after initializing.

        Returns:    Auto Online Flag (Auto Online = 1) (int)
        """
        return self.__autoOnline


    def setNoAutoExit(self,
                      noAutoExit):
        """
        Set the No Auto Exit Flag, indicating whether the server is
        allowed to exit automatically for instance in case of problems
        in connection with going Online automatically (-autoOnline).

        autoOnline:    Auto Online Flag (Auto Online = 1) (int)

        Returns:       Reference to object itself.
        """
        self.__noAutoExit = int(noAutoExit)
        return self


    def getNoAutoExit(self):
        """
        Return the No Auto Exit Flag.

        Returns:    No Auto Exit Flag (No Auto Exit = 1) (int)
        """
        return self.__noAutoExit


    def setMultipleSrvs(self,
                        multipleSrvs):
        """
        Set the Multiple Servers Flag to indicating that several servers
        can be executed on the same node and that the Host ID should be
        composed of hostname and port number.

        multipleSrvs:    Multiple Servers Flag (integer/0|1).

        Returns:         Reference to object itself.
        """
        self.__multipleSrvs = int(multipleSrvs)
        return self


    def getMultipleSrvs(self):
        """
        Get the Multiple Servers Flag to indicating that several servers
        can be executed on the same node and that the Host ID should be
        composed of hostname and port number.

        Returns:    Multiple Servers Flag (integer/0|1).
        """
        return self.__multipleSrvs


    def setCfg(self,
               ngamsCfgObj):
        """
        Set the reference to the configuration object.

        ngamsCfgObj:  Instance of the configuration object (ngamsConfig)
        
        Returns:      Reference to object itself.
        """
        self.__ngamsCfgObj = ngamsCfgObj
        return self


    def getCfg(self):
        """
        Return reference to object containing the NG/AMS Configuration.
        
        Returns:    Reference to NG/AMS Configuration (ngamsConfig).
        """
        return self.__ngamsCfgObj

    
    def getSrvListDic(self):
        """
        Return reference to the Server List Dictionary.

        Returns:    Reference to Server List Dictionary (dictionary).
        """
        return self.__srvListDic

    
    def getPartnerSites(self):
        """
        Return reference to the Partner Site vector.

        Returns:  Reference to Partner Site vector (vector).
        """
        return self.__partnerSites


    def setDiskDic(self,
                   diskDic):
        """
        Set the Disk Dictionary of the server object.

        diskDic:    Dick Dictionary (dictionary):

        Returns:    Reference to object itself.
        """
        self.__diskDic = diskDic
        return self


    def getDiskDic(self):
        """
        Get reference to Disk Dictionary.

        Returns:   Disk Dictionary (dictionary)
        """
        return self.__diskDic


    def getDynCmdDic(self):
        """
        Get reference to Dynamic Command Module Dictionary.

        Returns:   Dynamic Command Dictionary (dictionary)
        """
        return self.__dynCmdDic


    def setCfgFilename(self,
                       filename):
        """
        Set the name of the NG/AMS Configuration File.

        filename:     Name of configuration file (string).

        Returns:      Reference to object itself.
        """
        self.__ngamsCfg = filename
        return self


    def getCfgFilename(self):
        """
        Return name of NG/AMS Configuration file.

        Returns:   Name of NG/AMS Configuration file (string).
        """
        return self.__ngamsCfg


    def getMimeTypeDic(self):
        """
        Return reference to the Mime-Type Dictionary.

        Returns:  Reference to Mime-Type Dictionary (dictionary).
        """
        return self.__mimeType2PlugIn


    def getHostInfoObj(self):
        """
        Return reference to internal host info object.

        Returns:   Reference to host info object (ngamsHostInfo).
        """
        return  self.__hostInfo


    def updateHostInfo(self,
                       version,
                       portNo,
                       allowArchiveReq,
                       allowRetrieveReq,
                       allowProcessingReq,
                       allowRemoveReq,
                       dataChecking,
                       state,
                       updateDb = True):
        """
        Update the information about this NG/AMS Server in the NGAS DB
        (ngas_hosts). If a field should not be updated it should be given
        in as None.

        If a connection to the DB is not yet created, the method returns
        without doing anything.

        version:             NG/AMS version (string).
        
        portNo:              Port number (integer).
        
        allowArchiveReq:     Allow Archive Requests Flag (integer/0|1).
        
        allowRetrieveReq:    Allow Retrieve Requests Flag (integer/0|1).
        
        allowProcessingReq:  Allow Processing Requests Flag (integer/0|1).

        allowRemoveReq:      Allow Remove Requests Flag (integer/0|1).
        
        dataChecking:        Data Checking Active Flag (integer/0|1).
        
        state:               State of NG/AMS Server (string).

        updateDb:            Update the state in the DB if True (boolean).

        Returns:             Reference to object itself.
        """
        T = TRACE(5)
        
        if (self.getDb() == None): return self

        if (version != None): self.getHostInfoObj().setSrvVersion(version)
        if (portNo != None): self.getHostInfoObj().setSrvPort(portNo)
        self.getHostInfoObj().\
                                setSrvArchive(allowArchiveReq).\
                                setSrvRetrieve(allowRetrieveReq).\
                                setSrvProcess(allowProcessingReq).\
                                setSrvRemove(allowRemoveReq).\
                                setSrvDataChecking(dataChecking).\
                                setSrvState(state)
        if (updateDb):
            ngamsHighLevelLib.updateSrvHostInfo(self.getDb(),
                                                self.getHostInfoObj(), 1)
        return self


    def getSubscriberDic(self):
        """
        Returns reference to dictionary with Subscriber Objects.

        Returns:   Reference to dictionary with Subscriber info
                   (dictionary/ngamsSubscriber).
        """
        return self._subscriberDic
    

    def reqCallBack(self,
                    httpRef,
                    clientAddress,
                    method,
                    path,
                    requestVersion,
                    headers,
                    writeFd,
                    readFd):
        """
        Call-back to handle the HTTP request.

        httpRef:         Reference to the HTTP request handler
                         object (ngamsHttpRequestHandler).
         
        clientAddress:   Address of client (string).
         
        method:          HTTP method (string).
        
        path:            Path of HTTP request (URL) (string).
        
        requestVersion:  HTTP version (string).
        
        headers:         HTTP headers (dictionary).
        
        writeFd:         File object used to write data back to
                         client (file object).
        
        readFd:          File object used to read data from
                         client (file object).

        Returns:         Void.
        """
        T = TRACE()

        # Create new request handle + add this entry in the Request DB.
        reqPropsObj = ngamsReqProps.ngamsReqProps()
        self.addRequest(reqPropsObj)

        # Handle read/write FD.
        reqPropsObj.setReadFd(readFd).setWriteFd(writeFd)

        # Handle the request.
        try:
            self.handleHttpRequest(reqPropsObj, httpRef, clientAddress,
                                   method, path, requestVersion, headers)
            if (not reqPropsObj.getSentReply()):
                msg = "Successfully handled request"
                self.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                           NGAMS_SUCCESS, msg)
            self.setLastReqEndTime()
            reqPropsObj.getReadFd().close()
            reqPropsObj.setCompletionTime(1)
            self.updateRequestDb(reqPropsObj)
        except Exception, e:
            reqPropsObj.setCompletionTime(1)
            self.updateRequestDb(reqPropsObj)
            self.setLastReqEndTime()
            
            # Flush read socket if needed.
            if (reqPropsObj.getBytesReceived() < reqPropsObj.getSize()):
                #info(4,"Closing HTTP read socket ...")
                #reqPropsObj.getReadFd().close()
                #info(4,"Closed HTTP read socket")
                ngamsLib.flushHttpCh(reqPropsObj.getReadFd(), 32768,
                                     (reqPropsObj.getSize() -
                                      reqPropsObj.getBytesReceived()))
                reqPropsObj.setBytesReceived(reqPropsObj.getSize())
            reqPropsObj.getReadFd().close()
            if (getDebug()): traceback.print_exc(file = sys.stdout)
            errMsg = str(e)
            error(errMsg)
            self.setSubState(NGAMS_IDLE_SUBSTATE)
            if (not reqPropsObj.getSentReply()):
                self.reply(reqPropsObj, httpRef, NGAMS_HTTP_BAD_REQ,
                           NGAMS_FAILURE, errMsg)


    def handleHttpRequest(self,
                          reqPropsObj,
                          httpRef,
                          clientAddress,
                          method,
                          path,
                          requestVersion,
                          headers):
        """
        Handle the HTTP request.
        
        reqPropsObj:     Request Property object to keep track of actions done
                         during the request handling (ngamsReqProps).

        httpRef:         Reference to the HTTP request handler
                         object (ngamsHttpRequestHandler).
         
        clientAddress:   Address of client (string).
         
        method:          HTTP method (string).
        
        path:            Path of HTTP request (URL) (string).
        
        requestVersion:  HTTP version (string).
        
        headers:         HTTP headers (dictionary).

        Returns:         Void.
        """
        T = TRACE()

        # If running in Unit Test Mode, check if the server is suspended.
        # In case yes, raise an exception indicating this.
        if (getTestMode()):
            if (self.getDb().getSrvSuspended(getHostId())):
                raise Exception, "UNIT-TEST: This server is suspended"

        # Handle the command.
        self.setLastReqStartTime()
        reqTimer = PccUtTime.Timer()
        safePath = ngamsLib.hidePassword(path)
        msg = "Handling HTTP request: client_address=" + str(clientAddress) +\
              " - method=" + method + " - path=|" + safePath + "|"
        for key in headers.keys():
            msg = msg + " - " + key + "=" + str(headers[key])
        info(1,msg)
        reqPropsObj.unpackHttpInfo(self.getCfg(), method, path, headers)

        # Handle authorization.
        ngamsAuthUtils.authorize(self, reqPropsObj, httpRef)

        # Request authorized - handle the command
        ngamsCmdHandling.cmdHandler(self, reqPropsObj, httpRef)
        info(2,"Total time for handling request: (" +\
             reqPropsObj.getHttpMethod() + "," + reqPropsObj.getCmd() + "," +\
             reqPropsObj.getMimeType() + "," +\
             reqPropsObj.getFileUri() + "): " +\
             str(int(1000.0 * reqTimer.stop()) / 1000.0) + "s")
        logFlush()


    def httpReplyGen(self,
                     reqPropsObj,
                     httpRef,
                     code,
                     dataRef = None,
                     dataInFile = 0,
                     contentType = None,
                     contentLength = 0,
                     addHttpHdrs = [],
                     closeWrFo = 0):
        """
        Generate a standard HTTP reply.
        
        reqPropsObj:   Request Property object to keep track of actions done
                       during the request handling (ngamsReqProps).
        
        httpRef:       Reference to the HTTP request handler
                       object (ngamsHttpRequestHandler).       
        
        code:          HTTP status code (integer)
        
        dataRef:       Data to send with the HTTP reply (string).

        dataInFile:    Data stored in a file (integer).
        
        contentType:   Content type (mime-type) of the data (string).

        contentLength: Length of the message. The actually message should
                       be send from the calling method (integer).

        addHttpHdrs:   List containing sub-lists with additional
                       HTTP headers to send. Format is:

                         [[<HTTP hdr>, <val>, ...]         (list)

        closeWrFo:     If set to 1, the HTTP write file object will be closed
                       by the function (integer/0|1).
        
        Returns:       Void.
        """
        T = TRACE()

        info(4, "httpReplyGen(). Generating HTTP reply " +\
             "to: " + str(httpRef.client_address) + " ...")
        if (reqPropsObj.getSentReply()):
            info(3,"Reply already sent for this request")
            return
        try:
            if (BaseHTTPServer.BaseHTTPRequestHandler.responses.has_key(code)):
                message = BaseHTTPServer.BaseHTTPRequestHandler.\
                          responses[code][0]
            else:
                message = ""
                
            protocol = BaseHTTPServer.BaseHTTPRequestHandler.protocol_version
            httpRef.wfile.write("%s %s %s\r\n" % (protocol, str(code),message))
            srvInfo = "NGAMS/" + getNgamsVersion()
            info(4,"Sending header: Server: " + srvInfo)
            httpRef.send_header("Server", srvInfo)
            httpTimeStamp = ngamsLib.httpTimeStamp()
            info(4,"Sending header: Date: " + httpTimeStamp)
            httpRef.send_header("Date", httpTimeStamp)        
            # Expires HTTP reponse header field, e.g.:
            # Expires: Mon, 17 Sep 2001 09:21:38 GMT
            info(4,"Sending header: Expires: " + httpTimeStamp)
            httpRef.send_header("Expires", httpTimeStamp)

            if (dataRef == None):
                dataSize = 0
            elif ((dataRef != None) and (dataInFile)):
                dataSize = getFileSize(dataRef)
            elif (dataRef != None):
                if (len(dataRef) and (not contentLength)):
                    dataSize = len(dataRef)
                else:
                    dataSize = contentLength

            # Send additional headers if any.
            sentContDisp = 0
            for hdrInfo in addHttpHdrs:
                if (hdrInfo[0] == "Content-disposition"): sentContDisp = 1
                info(4,"Sending header: " + hdrInfo[0] + ": " + hdrInfo[1])
                httpRef.send_header(hdrInfo[0], hdrInfo[1])
            if (contentType != None):
                info(4,"Sending header: Content-type: " + contentType)
                httpRef.send_header("Content-type", contentType)
            if (dataRef != None):
                info(4,"Sending header: Content-length/1: " + str(dataSize))
                httpRef.send_header("Content-length", dataSize)
                if (dataInFile):
                    if (not sentContDisp):
                        contDisp = "attachment; filename=" +\
                                   os.path.basename(dataRef)
                        info(4,"Sending header: Content-disposition: " +\
                             contDisp)
                        httpRef.send_header("Content-disposition", contDisp)
                    httpRef.wfile.write("\n")
                    fo = None
                    try:
                        fo = open(dataRef, "r")
                        dataSent = 0
                        while (dataSent < dataSize):
                            tmpData = fo.read(65536)
                            httpRef.wfile.write(tmpData)
                            dataSent += len(tmpData)
                        fo.close()
                    except Exception, e:
                        if (fo != None): fo.close()
                        raise e
                else:
                    httpRef.wfile.write("\n" + dataRef)
                    info(5,"Message sent with HTTP reply=|%s|" %\
                         str(dataRef).replace("\n", ""))
            elif (contentLength != 0):
                info(4,"Sending header: Content-length/2: "+str(contentLength))
                httpRef.send_header("Content-length", contentLength)
            
            httpRef.wfile.flush()

            #################################################################
            # Due to synchronization problems/socket communication problems
            # when running several servers on the same node (data lost, e.g.
            # test ngasDiscardCmd.py) a small pause is build in when the sender
            # of the command is running on the same node. This is acceptable,
            # since only in case of the Unit Tests it is used to run several
            # servers on a node to simulate the operation in a cluster
            # configuration.
            #
            # This patch is not a guarantee that the lost data in connection
            # with the socket may occur. However, it reduces the probability
            # that it happens.
            #
            # TODO: Check if this piece of code can be removed using a newer
            #       version of Python (socket module).
            #################################################################
            if (reqPropsObj.hasHttpHdr("remote_host")):
                reqHost = reqPropsObj.getHttpHdr("remote_host").split(":")[0]
                if (reqHost == getHostName()):
                    info(4,"Sender and receiver running on the same host: Sleeping 0.1 s")
                    time.sleep(0.100)
            #################################################################
                
            if (closeWrFo): httpRef.wfile.close()
            reqPropsObj.setSentReply(1)
        except Exception, e:
            reqPropsObj.setSentReply(1)
            errMsg = "Error occurred while sending reply to: " +\
                     str(httpRef.client_address) + ". Error: " + str(e)
            error(errMsg)
        info(4,"Generated HTTP reply to: " + str(httpRef.client_address))

  
    def httpReply(self,
                  reqPropsObj,
                  httpRef,
                  code,
                  msg = None,
                  contentType = NGAMS_TEXT_MT,
                  addHttpHdrs = []):
        """
        Generate standard HTTP reply.
        
        reqPropsObj:   Request Property object to keep track of
                       actions done during the request handling
                       (ngamsReqProps).
        
        httpRef:       Reference to the HTTP request handler
                       object (ngamsHttpRequestHandler).       
        
        code:          HTTP status code (integer)
        
        msg:           Message to send as data with the HTTP reply (string).
        
        contentType:   Content type (mime-type) of the msg (string).

        addHttpHdrs:   List containing sub-lists with additional
                       HTTP headers to send. Format is:

                         [[<HTTP hdr>, <val>, ...]         (list)
        
        Returns:       Void.
        """
        T = TRACE()
        
        if (reqPropsObj.getSentReply()):
            info(3,"Reply already sent for this request")
            return
        self.httpReplyGen(reqPropsObj, httpRef, code, msg, 0, contentType,
                          len(msg), addHttpHdrs)
        httpRef.wfile.write("\r\n")
        info(3,"HTTP reply sent to: " + str(httpRef.client_address))


    def httpRedirReply(self,
                       reqPropsObj,
                       httpRef,
                       redirHost,
                       redirPort):
        """
        Generate an HTTP Redirection Reply and send this back to the
        requestor.
        
        reqPropsObj:   Request Property object to keep track of actions done
                       during the request handling (ngamsReqProps).

        httpRef:       Reference to the HTTP request handler
                       object (ngamsHttpRequestHandler).  

        redirHost:     NGAS host to which to redirect the request (string).

        redirPort:     Port number of the NG/AMS Server to which to redirect
                       the request (integer).

        Returns:       Void.
        """
        T = TRACE()
        
        pars = ""
        for par in reqPropsObj.getHttpParNames():
            if (par != "initiator"):
                pars += par + "=" + reqPropsObj.getHttpPar(par) + "&"
        pars = pars[0:-1]
        redirectUrl = "http://" + redirHost + ":" + str(redirPort) + "/" +\
                      reqPropsObj.getCmd() + "?" + pars
        msg = genLog("NGAMS_INFO_REDIRECT", [redirectUrl])
        info(1,msg)
        addHttpHdrs = [["Location", redirectUrl]]
        self.reply(reqPropsObj, httpRef, NGAMS_HTTP_REDIRECT, NGAMS_SUCCESS,
                   msg, addHttpHdrs)


    def forwardRequest(self,
                       reqPropsObj,
                       httpRefOrg,
                       forwardHost,
                       forwardPort,
                       autoReply = 1,
                       mimeType = ""):
        """
        Forward an HTTP request to the given host + port and handle the reply
        from the remotely, contacted NGAS node. If the host to contact for
        handling the request is different that the actual target host, the
        proper contact host (e.g. cluster main node) is resolved internally.
 
        reqPropsObj:    Request Property object to keep track of actions done
                        during the request handling (ngamsReqProps).

        httpRefOrg:     Reference to the HTTP request handler object for
                        the request received from the originator
                        (ngamsHttpRequestHandler).
                    
        forwardHost:    Host ID to where the request should be forwarded
                        (string).
        
        forwardPort:    Port number of the NG/AMS Server on the remote
                        host (integer).

        autoReply:      Send back reply to originator of the request
                        automatically (integer/0|1).

        mimeType:       Mime-type of possible data to forward (string).

        Returns:        Tuple with the following information:

                          (<HTTP Status>, <HTTP Status Msg>, <HTTP Hdrs>,
                           <Data>)  (tuple).
        """
        T = TRACE()

        # Resolve the proper contact host/port if needed/possible.
        hostDic = ngamsHighLevelLib.\
                  resolveHostAddress(self.getDb(),self.getCfg(),[forwardHost])
        if (hostDic[forwardHost] != None):
            contactHost = hostDic[forwardHost].getHostId()
            contactAddr = hostDic[forwardHost].getIpAddress()
            contactPort = hostDic[forwardHost].getSrvPort()
        else:
            contactHost = forwardHost
            contactAddr = forwardHost
            contactPort = forwardPort 
        pars = []
        for par in reqPropsObj.getHttpParNames():
            if (par != "initiator"):
                val = reqPropsObj.getHttpPar(par)
                pars.append([par, val])
        cmdInfo = reqPropsObj.getCmd() + "/Parameters: " +\
                  str(pars)[1:-1] + " to server defined " +\
                  "by host/port: %s/%s." % (forwardHost, str(forwardPort))
        cmdInfo += " Contact address: %s/%s." % (contactAddr, str(contactPort))
        info(2,"Forwarding command: %s" % cmdInfo)
        try:
            # If target host is suspended, wake it up.
            if (self.getDb().getSrvSuspended(contactHost)):
                ngamsSrvUtils.wakeUpHost(self, contactHost)

            # If the NGAS Internal Authorization User is defined generate
            # an internal Authorization Code.
            if (self.getCfg().hasAuthUser(NGAMS_HTTP_INT_AUTH_USER)):
                authHttpHdrVal = self.getCfg().\
                                 getAuthHttpHdrVal(NGAMS_HTTP_INT_AUTH_USER)
            else:
                authHttpHdrVal = ""

            # Forward GET or POST request.
            reqTimeOut = reqPropsObj.getHttpPar("time_out")
            if (reqPropsObj.getHttpMethod() == NGAMS_HTTP_GET):
                httpStatCode, httpStatMsg, httpHdrs, data =\
                              ngamsLib.httpGet(contactAddr, contactPort,
                                               reqPropsObj.getCmd(), 1, pars,
                                               "",self.getCfg().getBlockSize(),
                                               timeOut=reqTimeOut,
                                               returnFileObj=0,
                                               authHdrVal=authHttpHdrVal)
            else:
                # It's a POST request, forward request + possible data.
                fn = reqPropsObj.getFileUri()
                contLen = reqPropsObj.getSize()
                if ((reqPropsObj.getCmd() == NGAMS_ARCHIVE_CMD) and
                    (contLen <= 0)):
                    raise Exception, "Must specify a content-length when " +\
                          "forwarding Archive Requests (Archive Proxy Mode)"
                httpStatCode, httpStatMsg, httpHdrs, data =\
                                  ngamsLib.httpPost(contactAddr, contactPort,
                                                    reqPropsObj.getCmd(),
                                                    mimeType,
                                                    reqPropsObj.getReadFd(),
                                                    "FD", pars,
                                                    authHdrVal=authHttpHdrVal,
                                                    fileName=fn,
                                                    dataSize=contLen,
                                                    timeOut=reqTimeOut)
            
            # If auto-reply is selected, the reply from the remote server
            # is send back to the originator of the request.
            if (autoReply):
                tmpReqObj = ngamsReqProps.ngamsReqProps().\
                            unpackHttpInfo(self.getCfg(),
                                           reqPropsObj.getHttpMethod(), "",
                                           httpHdrs.dict)
                mimeType = tmpReqObj.getMimeType()
                if (tmpReqObj.getFileUri()):
                    attachmentName = os.path.basename(tmpReqObj.getFileUri())
                    httpHdrs = [["Content-disposition",
                                 "attachment; filename=" + attachmentName]]
                else:
                    httpHdrs = []
                self.httpReply(reqPropsObj, httpRefOrg, httpStatCode, data,
                               mimeType, httpHdrs)

            return httpStatCode, httpStatMsg, httpHdrs, data
        except Exception, e:
            errMsg = "Problem occurred forwarding command: " + cmdInfo +\
                     ". Error: " + str(e)
            raise Exception, errMsg


    def genStatus(self,
                  status,
                  msg):
        """
        Generate an NG/AMS status object with the basic fields set.

        status:   Status: OK/FAILURE (string).
        
        msg:      Message for status (string).
        
        Returns:  Status object (ngamsStatus).
        """
        return ngamsStatus.ngamsStatus().\
               setDate(PccUtTime.TimeStamp().getTimeStamp()).\
               setVersion(getNgamsVersion()).setHostId(getHostId()).\
               setStatus(status).setMessage(msg).setState(self.getState()).\
               setSubState(self.getSubState())


    def reply(self,
              reqPropsObj,
              httpRef,
              code,
              status,
              msg,
              addHttpHdrs = []):
        """
        Standard reply to HTTP request.

        reqPropsObj:   Request Property object to keep track of
                       actions done during the request handling
                       (ngamsReqProps).
        
        httpRef:       Reference to the HTTP request handler
                       object (ngamsHttpRequestHandler).       
        
        code:          HTTP status code (integer)

        status:        Status: OK/FAILURE (string).
        
        msg:           Message for status (string).

        addHttpHdrs:   List containing sub-lists with additional
                       HTTP headers to send. Format is:

                         [[<HTTP hdr>, <val>, ...]         (list)
        
        Returns:       Void.
        """
        T = TRACE()
        
        if (reqPropsObj.getSentReply()):
            info(3,"Reply already sent for this request")
            return
        status = self.genStatus(status, msg).\
                 setReqStatFromReqPropsObj(reqPropsObj).\
                 setCompletionTime(reqPropsObj.getCompletionTime())
        xmlStat = status.genXmlDoc()
        xmlStat = ngamsHighLevelLib.\
                  addDocTypeXmlDoc(self, xmlStat, NGAMS_XML_STATUS_ROOT_EL,
                                   NGAMS_XML_STATUS_DTD)
        self.httpReply(reqPropsObj, httpRef, code, xmlStat, NGAMS_XML_MT,
                       addHttpHdrs)


    def ingestReply(self,
                    reqPropsObj,
                    httpRef,
                    code,
                    status,
                    msg,
                    diskInfoObj):
        """
        Standard HTTP reply to archive ingestion action.

        reqPropsObj:   Request Property object to keep track of actions done
                       during the request handling (ngamsReqProps).
        
        httpRef:       Reference to the HTTP request handler
                       object (ngamsHttpRequestHandler).       
        
        code:          HTTP status code (integer)

        status:        Status: OK/FAILURE (string).

        msg:           Message to send as data with the HTTP reply (string).

        diskInfoObj:   Disk info object containing status for disk
                       where file were stored (Main Disk) (ngamsDiskInfo).
        """
        T = TRACE()
        
        statusObj = self.genStatus(status, msg).addDiskStatus(diskInfoObj).\
                    setReqStatFromReqPropsObj(reqPropsObj)
        xmlStat = statusObj.genXmlDoc(0, 1, 1)
        xmlStat = ngamsHighLevelLib.\
                  addDocTypeXmlDoc(self, xmlStat, NGAMS_XML_STATUS_ROOT_EL,
                                   NGAMS_XML_STATUS_DTD)
        self.httpReply(reqPropsObj, httpRef, code, xmlStat, NGAMS_XML_MT)

                
    def checkDiskSpaceSat(self,
                          minDiskSpaceMb = None):
        """
        This method checks the important mount points used by NG/AMS for
        the operation. If the amount of free disk space goes below 10 GB
        this is signalled by raising an exception.

        minDiskSpaceDb:   The amount of minimum free disk space (integer).

        Returns:          Void.
        """
        T = TRACE()

        if (not minDiskSpaceMb):
            minDiskSpaceMb = self.getCfg().getMinSpaceSysDirMb()
        for mtPt in self.__sysMtPtDic.keys():
            diskSpace = getDiskSpaceAvail(mtPt)
            if (diskSpace < minDiskSpaceMb):
                dirErrMsg = "("
                for dirInfo in self.__sysMtPtDic[mtPt]:
                    dirErrMsg += "Directory: %s - Info: %s, " %\
                                 (dirInfo[0], dirInfo[1])
                dirErrMsg = dirErrMsg[0:-2] + ")"
                errMsg = genLog("NGAMS_AL_DISK_SPACE_SAT",
                                [minDiskSpaceMb, dirErrMsg])
                raise Exception, errMsg
        

    def init(self,
             argv,
             serve = 1):
        """
        Initialize the NG/AMS Server.

        argv:       Tuple containing the command line parameters to
                    the server (tuple). 

        serve:      If set to 1, the server will start serving on the
                    given HTTP port (integer/0|1).
                    
        Returns:    Reference to object itself.
        """
        # Parse input parameters, set up signal handlers, connect to DB,
        # load NGAMS configuration, start NG/AMS HTTP server.
        self.parseInputPars(argv)
        info(1,"NG/AMS Server version: " + getNgamsVersion())
        info(1,"Python version: " + re.sub("\n", "", sys.version))

        # Make global reference to this instance of the NG/AMS Server.
        global _ngamsServer
        _ngamsServer = self

        # Set up signal handlers.
        info(4,"Setting up signal handler for SIGTERM ...")
        signal.signal(signal.SIGTERM, ngamsExitHandler)
        info(4,"Setting up signal handler for SIGINT ...")
        signal.signal(signal.SIGINT, ngamsExitHandler)
        
        if (getDebug()):
            self.handleStartUp(serve)
        else:
            try:
                self.handleStartUp(serve)
            except Exception, e:
                errMsg = genLog("NGAMS_ER_INIT_SERVER", [str(e)])
                error(errMsg)
                ngamsNotification.notify(self.getCfg(), NGAMS_NOTIF_ERROR,
                                         "PROBLEMS INITIALIZING NG/AMS SERVER",
                                         errMsg, [], 1)
                self.killServer()

        return self


    def pidFile(self):
        """
        Return the name of the PID file in which NG/AMS stores its PID.

        Returns:   Name of PID file (string).
        """
        # Generate a PID file with the  name: <mt root dir>/.<NGAS ID>
        if ((not self.getCfg().getRootDirectory()) or \
            (self.getCfg().getPortNo() < 1)): return ""
        try:
            pidFile = os.path.join(self.getCfg().getRootDirectory(), "." +
                                   ngamsHighLevelLib.genNgasId(self.getCfg()))
        except Exception, e:
            errMsg = "Error occurred generating PID file name. Check " +\
                     "Mount Root Directory + Port Number in configuration. "+\
                     "Error: " + str(e)
            raise Exception, errMsg
        return pidFile


    def loadCfg(self):
        """
        Load the NG/AMS Configuration.

        Returns:   Reference to object itself.
        """
        info(1,"Loading NG/AMS Configuration: " + self.getCfgFilename()+" ...")
        self.getCfg().load(self.getCfgFilename())

        # Connect to the DB.
        if (not self.__ngasDb):
            msg = "Connecting to DB (Server: %s - DB: %s - User: %s) ..."
            info(1, msg % (str(self.getCfg().getDbServer()),
                           str(self.getCfg().getDbName()),
                           str(self.getCfg().getDbUser())))
            creSnap  = self.getCfg().getDbSnapshot()
            driver   = self.getCfg().getDbInterface()
            multCon  = self.getCfg().getDbMultipleCons()
            drvPars  = self.getCfg().getDbParameters()
            msg = "-- additional DB parameters: Create Snapshot: %d, " +\
                  "Driver: %s, Multiple Connections: %d, " +\
                  "Driver Parameters: %s"
            info(2, msg % (creSnap, str(driver), multCon, str(drvPars)))
            self.__ngasDb = ngamsDb.ngamsDb(self.getCfg().getDbServer(),
                                            self.getCfg().getDbName(),
                                            self.getCfg().getDbUser(),
                                            self.getCfg().getDbPassword(),
                                            createSnapshot = creSnap,
                                            interface = driver,
                                            multipleConnections = multCon,
                                            parameters = drvPars)
        else:
            msg = "Already established connection to DB %s"
            info(1, msg % (self.__ngasDb.getDbName()))

            msg = "-- additional DB parameters: Create Snapshot: %d, " +\
                  "Driver: %s, Multiple Connections: %d, " +\
                  "Driver Parameters: %s"
            info(2, msg % (self.getCfg().getDbSnapshot(), \
                  self.getCfg().getDbInterface(), \
                  self.getCfg().getDbMultipleCons(), \
                  self.getCfg().getDbParameters()))


        # Check if we should load a configuration from the DB.
        if (self.__dbCfgId): self.getCfg().loadFromDb(self.__dbCfgId,
                                                      self.getDb())
        ngasTmpDir = ngamsHighLevelLib.getNgasTmpDir(self.getCfg())
        self.__ngasDb.setDbTmpDir(ngasTmpDir)
    
        # Check the configuration.
        self.getCfg()._check()

        info(1,"Successfully loaded NG/AMS Configuration")
        return self
        

    def handleStartUp(self,
                      serve = 1):
        """
        Initialize the NG/AMS Server. This implies loading the NG/AMS
        Configuration, setting up DB connection, checking disk configuration,
        and starting the HTTP server.

        serve:      If set to 1, the server will start serving on the
                    given HTTP port (integer/0|1).
        
        Returns:    Void.
        """       
        # Remember to set the time for the last request initially to the
        # start-up time to avoid that the host is suspended immediately.
        self.setLastReqEndTime()

        # Load NG/AMS Configuration (from XML Document/DB).
        self.loadCfg()

        # Check if there is an entry for this node in the ngas_hosts
        # table, if not create it.
        if (self.getMultipleSrvs()): setSrvPort(self.getCfg().getPortNo())
        hostInfo = self.getDb().getHostInfoFromHostIds([getHostId()])
        if (hostInfo == []):
            tmpHostInfoObj = ngamsHostInfo.ngamsHostInfo()
            ipAddress = socket.gethostbyname(getHostName())
            domain = ngamsLib.getDomain()
            if (not domain): domain = NGAMS_NOT_SET
            tmpHostInfoObj.\
                             setHostId(getHostId()).\
                             setDomain(domain).\
                             setIpAddress(ipAddress).\
                             setMacAddress(NGAMS_NOT_SET).\
                             setNSlots(-1).\
                             setClusterName(getHostId()).\
                             setInstallationDateFromSecs(time.time())
            info(1,"Creating entry in NGAS Hosts Table for this node: %s" %\
                 getHostId())
            self.getDb().writeHostInfo(tmpHostInfoObj)

        # Should be possible to execute several servers on one node.
        self.__hostInfo.setHostId(getHostId())
        
        # Log some essential information.
        allowArchiveReq    = self.getCfg().getAllowArchiveReq()
        allowRetrieveReq   = self.getCfg().getAllowRetrieveReq()
        allowProcessingReq = self.getCfg().getAllowProcessingReq()
        allowRemoveReq     = self.getCfg().getAllowRemoveReq()
        info(1,"Allow Archiving Requests: %d"  % allowArchiveReq)
        info(1,"Allow Retrieving Requests: %d" % allowRetrieveReq)
        info(1,"Allow Processing Requests: %d" % allowProcessingReq)
        info(1,"Allow Remove Requests: %d"     % allowRemoveReq)
        self.getHostInfoObj().\
                                setSrvArchive(allowArchiveReq).\
                                setSrvRetrieve(allowRetrieveReq).\
                                setSrvProcess(allowProcessingReq).\
                                setSrvRemove(allowRemoveReq).\
                                setSrvDataChecking(0)

        # Extract information about partner sites.
        partnerSiteKeyPat = "PartnerSites[1].PartnerSite[%d].Address"
        idx = 1
        while (True):
            partnerSiteKey = partnerSiteKeyPat % idx
            partnerSiteAddress = self.getCfg().getVal(partnerSiteKey)
            if (partnerSiteAddress):
                info(1,"Registering partner site: %s" % partnerSiteAddress)
                self.__partnerSites.append(partnerSiteAddress)
                idx += 1
            else:
                break
 
        # Check if there is already a PID file.
        info(5,"Check if NG/AMS PID file is existing ...")
        if (not self.getForce() and os.path.exists(self.pidFile())):
            errMsg = genLog("NGAMS_ER_MULT_INST")
            error(errMsg)
            ngamsNotification.notify(self.getCfg(), NGAMS_NOTIF_ERROR,
                                     "CONFLICT STARTING NG/AMS SERVER", errMsg)
            ngamsExitHandler(0, "", 0, 1, 0)

        # Store the PID of this process in a PID file.
        info(4,"Creating PID file for this session ...")
        checkCreatePath(os.path.dirname(self.pidFile()))
        fo = open(self.pidFile(), "w")
        fo.write(str(os.getpid()))
        fo.close()
        info(4,"PID file for this session created")

        # Check/create the NG/AMS Temporary and Cache Directories.
        checkCreatePath(ngamsHighLevelLib.getTmpDir(self.getCfg()))
        checkCreatePath(ngamsHighLevelLib.genCacheDirName(self.getCfg()))

        # Remove Request DB (DBM file).
        rmFile(self.getReqDbName() + "*")

        # Find the directories (mount directoties) to monitor for a minimum
        # amount of disk space. This is resolved from the various
        # directories defined in the configuration.
        info(4,"Find NG/AMS System Directories to monitor for disk space ...")
        dirList = [(self.getCfg().getRootDirectory(),
                    "Mount Root Directory (Ngams:RootDirectory"),
                   (self.getCfg().getBackLogBufferDirectory(),
                    "Back-Log Buffer Directory " +\
                    "(Ngams:BackLogBufferDirectory)"),
                   (self.getCfg().getProcessingDirectory(),
                    "Processing Directory (FileHandling:ProcessingDirectory"),
                   (self.getCfg().getLocalLogFile(),
                    "Local Log File (Log:LocalLogFile)")]
        for dirInfo in dirList:
            dirName = os.path.dirname(dirInfo[1])
            stat, out = commands.getstatusoutput("df " + dirInfo[0])
            if (stat == 0):
                mtPt = out.split("\n")[1].split("%")[-1].strip()
                if (not self.__sysMtPtDic.has_key(mtPt)):
                    self.__sysMtPtDic[mtPt] = []
                self.__sysMtPtDic[mtPt].append(dirInfo)
        info(4,"Found NG/AMS System Directories to monitor for disk space")

        info(4,"Check/create NG/AMS Request Info DB ...")
        reqDbmName = self.getReqDbName()
        self.__requestDbm = ngamsDbm.ngamsDbm(reqDbmName, cleanUpOnDestr = 0,
                                              writePerm = 1)
        info(4,"Checked/created NG/AMS Request Info DB")

        # Set up final logging conditions.
        if (self.__locLogLevel == -1):
            self.__locLogLevel = self.getCfg().getLocalLogLevel()
        if ((self.__locLogFile != "") and (self.getCfg().getLocalLogFile())):
            self.__locLogFile = self.getCfg().getLocalLogFile()
        if (self.__sysLog == -1):
            self.__sysLog = self.getCfg().getSysLog() 
        if (self.__sysLogPrefix == NGAMS_DEF_LOG_PREFIX):
            self.__sysLogPrefix = self.getCfg().getSysLogPrefix()
        try:
            setLogCond(self.__sysLog, self.__sysLogPrefix, self.__locLogLevel,
                       self.__locLogFile, self.__verboseLevel)
            msg = "Logging properties for NGAS Node: %s " +\
                  "defined as: Sys Log: %s " +\
                  "- Sys Log Prefix: %s  - Local Log File: %s " +\
                  "- Local Log Level: %s - Verbose Level: %s"
            info(1, msg % (getHostId(), str(self.__sysLog),
                           self.__sysLogPrefix, self.__locLogFile,
                           str(self.__locLogLevel), str(self.__verboseLevel)))
        except Exception, e:
            errMsg = genLog("NGAMS_ER_INIT_LOG", [self.__locLogFile, str(e)])
            error(errMsg)
            ngamsNotification.notify(self.getCfg(), NGAMS_NOTIF_ERROR,
                                     "PROBLEM SETTING UP LOGGING", errMsg)
            raise Exception, errMsg
        if (self.getCfg().getLogBufferSize() != -1):
            setLogCache(self.getCfg().getLogBufferSize())

        sysLogInfo(1, genLog("NGAMS_INFO_STARTING_SRV",
                             [getNgamsVersion(), getHostId(),
                              self.getCfg().getPortNo()]))

        # Reset the parameters for the suspension.
        self.getDb().resetWakeUpCall(None, 1)

        # Create a mime-type to DAPI dictionary
        for stream in self.getCfg().getStreamList():
            self.getMimeTypeDic()[stream.getMimeType()] = stream.getPlugIn()
 
        # If Auto Online is selected, bring the Server Online
        if (self.getAutoOnline()):
            info(2,"Auto Online requested - server going to Online State ...")
            try:
                ngamsSrvUtils.handleOnline(self)
            except Exception, e:
                if (not self.getNoAutoExit()): raise e
        else:
            info(2,"Auto Online not requested - " +\
                 "server remaining in Offline State")

        # Update the internal ngamsHostInfo object + ngas_hosts table.
        clusterName = self.getDb().getClusterNameFromHostId(getHostId())
        self.getHostInfoObj().setClusterName(clusterName)
        self.updateHostInfo(getNgamsVersion(), self.getCfg().getPortNo(),
                            self.getCfg().getAllowArchiveReq(),
                            self.getCfg().getAllowRetrieveReq(),
                            self.getCfg().getAllowProcessingReq(),
                            self.getCfg().getAllowRemoveReq(),
                            0, None)

        # Start HTTP server.
        if (serve):
            info(1,"Initializing HTTP server ...")
            try:
                self.serve()
            except Exception, e:
                errMsg = genLog("NGAMS_ER_OP_HTTP_SERV", [str(e)])
                error(errMsg)
                ngamsNotification.notify(self.getCfg(), NGAMS_NOTIF_ERROR,
                                         "PROBLEM ENCOUNTERED STARTING " +\
                                         "SERVER", errMsg)
                ngamsExitHandler(0, "")


    def reqWakeUpCall(self,
                      wakeUpHostId,
                      wakeUpTime):
        """
        Request a Wake-Up Call via the DB.
        
        wakeUpHostId:  Name of host where the NG/AMS Server requested for
                       the Wake-Up Call is running (string).
        
        wakeUpTime:    Absolute time for being woken up (seconds since
                       epoch) (integer).

        Returns:       Reference to object itself.
        """
        self.getDb().reqWakeUpCall(wakeUpHostId, wakeUpTime)
        self.getHostInfoObj().\
                                setSrvSuspended(1).\
                                setSrvReqWakeUpSrv(wakeUpHostId).\
                                setSrvReqWakeUpTime(wakeUpTime)
        return self


    def serve(self):
        """
        Start to serve.

        Returns:  Void.
        """
        global _reqCallBack
        _reqCallBack = self.reqCallBack

        tmpHostName = os.uname()[1]
        info(3,"System host name: %s" % str(tmpHostName))
        if (tmpHostName.split(".")[-1] == "local"):
            hostName = "localhost"
        else:
            hostName = getHostName()
        portNo = self.getCfg().getPortNo()
        info(1,"Setting up NG/AMS HTTP Server (Host: " + getHostName() +\
             " - Port: " + str(portNo) + ") ...")
        self.__httpDaemon = ngamsHttpServer((hostName, portNo), 
                                            ngamsHttpRequestHandler)
        info(1,"NG/AMS HTTP Server ready (Host: " + getHostName() +\
             " - Port: " + str(portNo) + ")")
        self.__httpDaemon.serve_forever()


    def killServer(self,
                   delPidFile = 1):
        """
        Kills the server itself and deletes the PID file.

        delPidFile:  Flag indicating if NG/AMS PID file should be deleted or
                     not (integer/0|1).
                     
        Returns:     Void.
        """
        msg = genLog("NGAMS_INFO_TERM_SRV", [getNgamsVersion(), getHostName(),
                                             self.getCfg().getPortNo()])
        sysLogInfo(1, msg)
        info(1,msg)
        pid = None
        if (self.pidFile()):
            pidFile = self.pidFile()
            if (os.path.exists(pidFile)):
                fo = open(pidFile, "r")
                pid = fo.read()
                fo.close()
                if (delPidFile): os.remove(pidFile)
        if (not pid): pid = os.getpid()
        try:
            notice("Killing NG/AMS Main Thread. PID: %d" % int(pid))
            logFlush()
            os.kill(int(pid), signal.SIGKILL)
        except Exception, e:
            error("Server encountered problem terminating: " + str(e))
        info(1,"Terminated NG/AMS Server")


    def _incCheckIdx(self,
                     idx,
                     argv):
        """
        Increment and check index for command line parameters.

        idx:       Present index to increment (integer).
        
        argv:      Tuple containing command line arguments (tuple).
        
        Returns:   Increment index.
        """
        idx = idx + 1
        if (idx == len(argv)): self.correctUsage()
        return idx


    def correctUsage(self):
        """
        Print out correct usage message.
        
        Returns:    Void.
        """
        fo = open(ngamsGetSrcDir() + "/ngamsServer/ngamsServer.doc")
        manPage = fo.read()
        fo.close()
        manPage = manPage.replace("ngamsServer", self._serverName)
        print manPage
        print ngamsCopyrightString()


    def parseInputPars(self,
                       argv):
        """
        Parse input parameters.

        argv:       Tuple containing command line parameters (tuple)

        Returns:
        """
        setLogCache(10)
        exitValue = 1
        silentExit = 0
        idx = 1
        while idx < len(argv):
            par = argv[idx].upper()
            try:
                if (par == "-CFG"):
                    idx = self._incCheckIdx(idx, argv)
                    info(1,"Configuration specified: %s" % argv[idx])
                    self.setCfgFilename(argv[idx])
                elif (par == "-DBCFGID"):
                    idx = self._incCheckIdx(idx, argv)
                    info(1,"Configuration DB ID specified: %s" % argv[idx])
                    self.__dbCfgId = argv[idx]
                elif (par == "-V"):
                    idx = self._incCheckIdx(idx, argv)
                    self.__verboseLevel = int(argv[idx])
                    setLogCond(self.__sysLog, self.__sysLogPrefix,
                               self.__locLogLevel, self.__locLogFile,
                               self.__verboseLevel)
                elif (par == "-LOCLOGFILE"):
                    idx = self._incCheckIdx(idx, argv)
                    self.__locLogFile = argv[idx]
                    setLogCond(self.__sysLog, self.__sysLogPrefix,
                               self.__locLogLevel, self.__locLogFile,
                               self.__verboseLevel)
                elif (par == "-LOCLOGLEVEL"):
                    idx = self._incCheckIdx(idx, argv)
                    self.__locLogLevel = int(argv[idx])
                    setLogCond(self.__sysLog, self.__sysLogPrefix,
                               self.__locLogLevel, self.__locLogFile,
                               self.__verboseLevel)
                elif (par == "-SYSLOG"):
                    idx = self._incCheckIdx(idx, argv)
                    self.__sysLogLevel = argv[idx]
                    setLogCond(self.__sysLog, self.__sysLogPrefix,
                               self.__locLogLevel, self.__locLogFile,
                               self.__verboseLevel)
                elif (par == "-SYSLOGPREFIX"):
                    idx = self._incCheckIdx(idx, argv)
                    self.__sysLogPrefix = argv[idx]
                    setLogCond(self.__sysLog, self.__sysLogPrefix,
                               self.__locLogLevel, self.__locLogFile,
                               self.__verboseLevel)
                elif (par == "-VERSION"):
                    print getNgamsVersion()
                    exitValue = 0
                    silentExit = 1
                    sys.exit(0)
                elif (par == "-LICENSE"):
                    print getNgamsLicense()
                    exitValue = 0
                    silentExit = 1
                    sys.exit(0)
                elif (par == "-D"):
                    info(1,"Debug Mode enabled")
                    setDebug(1)
                elif (par == "-FORCE"):
                    info(1,"Forced Mode requested")
                    self.setForce(1)
                elif (par == "-AUTOONLINE"):
                    info(1,"Auto Online requested")
                    self.setAutoOnline(1)
                elif (par == "-NOAUTOEXIT"):
                    info(1,"Auto Exit is off")
                    self.setNoAutoExit(1)
                elif (par == "-MULTIPLESRVS"):
                    info(1,"Running in Multiple Servers Mode")
                    self.setMultipleSrvs(1)
                elif (par == "-TEST"):
                    info(1,"Running server in Test Mode")
                    setTestMode()
                else:
                    self.correctUsage()
                    silentExit = 1
                    sys.exit(1)
                idx = idx + 1
            except Exception, e:
                if (str(e) == "0"): sys.exit(0)
                if (str(1) != "1"):
                    print "Problem encountered parsing command line " +\
                          "parameters: "+ str(e)
                if (not silentExit): self.correctUsage()
                sys.exit(exitValue)

        # Check correctness of the command line parameters.
        if (self.getCfgFilename() == ""):
            self.correctUsage()
            sys.exit(1)

    ########################################################################
    # The following methods are used for the NG/AMS Unit Tests.
    # The method do not contain any code, but in the Unit Test code it is
    # possible to override these methods to give the server a specific,
    # usually abnormal, behavior, e.g. to simulate that the server crashes.
    ########################################################################
    def test_AfterSaveInStagingFile(self):
        """
        Method invoked in NG/AMS Server immediately after saving data in a
        Staging File while handling an Archive Request.

        Returns:   Void.
        """
        pass

    def test_AfterCreateTmpPropFile(self):
        """
        Method invoked in NG/AMS Server immediately after having created
        the Temp. Req. Prop. File while handling an Archive Request.

        Returns:   Void.
        """
        pass

    def test_BeforeDapiInvocation(self):
        """
        Test method invoked in NG/AMS Server immediately before invoking
        the DAPI during the handling of the Archive Request.

        Returns:   Void.
        """
        pass
    
    def test_AfterDapiInvocation(self):
        """
        Test method invoked in NG/AMS Server immediately after having invoked
        the DAPI during the handling of the Archive Request.

        Returns:   Void.
        """
        pass

    def test_AfterMovingStagingFile(self):
        """
        Test method invoked in NG/AMS Server immediately moving the
        Processing Staging File to its final destination (Main File).

        Returns:   Void.
        """
        pass

    def test_BeforeRepFile(self):
        """
        Test method invoked in NG/AMS Server after handling the Main File
        (before handling the Replication File).

        Returns:   Void.
        """
        pass

    def test_BeforeDbUpdateRepFile(self):
        """
        Test method invoked in NG/AMS Server during handling of the Replication
        File, after creating the Replication Copy, before updating its info in
        the DB.

        Returns:   Void.
        """
        pass

    def test_BeforeArchCleanUp(self):
        """
        Test method invoked in NG/AMS Server during the Archive handling,
        before deleting the Original Staging File and the Request Propeties
        File.
        """
        pass
    ########################################################################


if __name__ == '__main__':
    """
    Main function instatiating the NG/AMS Server Class and starting the server.
    """
    T = TRACE()

    ngams = ngamsServer()
    ngams.init(sys.argv)


# EOF
