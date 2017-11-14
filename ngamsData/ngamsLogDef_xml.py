"""
<?xml version="1.0" encoding="UTF-8"?>
<?xml:stylesheet type="text/xsl" 
                 href="http://www.eso.org/~jknudstr/LogDef.xsl"?>
<!-- http://www.eso.org/projects/esoxml/LogDef.xsl -->
<!DOCTYPE LogDef SYSTEM "http://www.eso.org/~jknudstr/LogDef.dtd">
<!-- Use: http://www.eso.org/projects/esoxml/LogDef.dtd -->

<!--
     ALMA - Atacama Large Millimiter Array
     (c) European Southern Observatory, 2002
     Copyright by ESO (in the framework of the ALMA collaboration),
     All rights reserved
  
     This library is free software; you can redistribute it and/or
     modify it under the terms of the GNU Lesser General Public
     License as published by the Free Software Foundation; either
     version 2.1 of the License, or (at your option) any later version.
  
     This library is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
     Lesser General Public License for more details.
  
     You should have received a copy of the GNU Lesser General Public
     License along with this library; if not, write to the Free Software
     Foundation, Inc., 59 Temple Place, Suite 330, Boston,
     MA 02111-1307  USA
  
 -->

<!-- 
  Who        When        What
  ********   **********  ***************************************************
  jknudstr   11.10.2001  Created
  **************************************************************************
  This file contains the definition of the logs used by the NG/AMS project.

  Consult the DTD LogDef.dtd for further information about the contents.

  The logs have been divided in the following categories determined
  by the log number:

  Range           Category
  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
  0000-0999       Not used.
  1000-1999       Logs related to the NG/AMS Configuration.
  2000-2999       Logs related to DB access/contents.
  3000-3999       Logs related to operation/system.
  4000-4999       Logs related to request handling.
  -->

<LogDef>
  <Header Name="ngamsErrDef.xml"
          Type="NGAMS-ERROR-DEF"
          Context="NGAMS"
          Release="1.0"
          Source="jknudstr@eso.org"
          Revision="@(#) $Id: ngamsLogDef.xml,v 1.5 2011/05/04 19:37:18 jagonzal Exp $">
    <Description>
      This XML document contains the definition of the error logs used
      within the NG/AMS project.
    </Description>
  </Header>

  <LogDefEl LogId="NGAMS_ER_NO_STORAGE_SET"
            LogNumber="1000"
	    LogType="ERROR">
    <LogText>
    No Storage Set matching the Slot ID: %s. Check NG/AMS Configuration: %s.
    </LogText>  
    <Description>
    NG/AMS could not find a Storage Set which matches the given Slot ID.
    There seems to be a problem in the NG/AMS Configuration.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_NO_MIME_TYPES"
            LogNumber="1001"
	    LogType="ERROR">
    <LogText>
    No mime-type/extension mappings defined in configuration file: %s 
    (Element: MimeTypes)!
    </LogText>  
    <Description>
    There are no mime-types/Data Handling Plug-In mappings defined in
    the NG/AMS Configuration. These are necessary in order to have
    each type of data file properly handled by NG/AMS.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MISSING_ELEMENT"
            LogNumber="1002"
	    LogType="ERROR">
    <LogText>
    Could not find element: %s in NG/AMS Configuration: %s. Must be specified!
    </LogText>  
    <Description>
    The element referred to in the log text, was not found in the
    configuration file as expected. Must be specified in order to
    run the NG/AMS Server.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CRE_GLOB_BAD_FILE_DIR"
            LogNumber="1004"
	    LogType="ERROR">
    <LogText>
    Problem creating Global Bad Files Directory: %s specified in
    configuration file: %s. Parameter: FileHandling.GlobalBadDirLoc.
    </LogText>  
    <Description>
    The Global Bad Files Directory could not be created. Make the
    parent directory writable for the NG/AMS Server host account and
    try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CONF_PROP"
            LogNumber="1005"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    The value defined for the property referred is not properly
    defined. Must define a proper value. Check configuration 
    file and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CONF_FILE"
            LogNumber="1006"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    An error occurred while parsing the configuration file at the
    position in the document as indicated by the error 
    message. Check/correct configuration file and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_ROOT_DIR"
            LogNumber="1007"
	    LogType="ERROR">
    <LogText>
    Illegal path specified for Root Directory in
    configuration file: %s (Parameter: Server.RootDirectory). 
    Path given: %s.
    </LogText>  
    <Description>
    The directory specified as Root Directory is not writable or
    not existing. Create this and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_LOAD_CFG"
            LogNumber="1008"
	    LogType="ERROR">
    <LogText>
    Problem encountered attempting to load the 
    NG/AMS Configuration: %s. Error message: %s
    </LogText>  
    <Description>
    The specified configuration file could not be loaded. This could
    e.g. be due to that the file is not readable (has not read
    permissions) for the user running NG/AMS, or that the file is not
    available.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_PROC_DIR"
            LogNumber="1009"
	    LogType="ERROR">
    <LogText>
    Illegal path specified for Processing Directory in
    configuration file: %s (Parameter: FileHandling.ProcessingDirectory). 
    Path given: %s.
    </LogText>  
    <Description>
    The directory specified as Processing Directory is not writable or
    not existing. Create this and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_PLUGIN_PAR"
            LogNumber="1010"
	    LogType="ERROR">
    <LogText>
    Plug-In Parameters are improperly formatted: %s. Correct format
    is: (par)=(value),(par)=(value)...
    </LogText>  
    <Description>
    The Plug-IN Parameters defined in connection with a plug-in are
    not formatted as expected. 
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MISSING_DISK_ID"
            LogNumber="2000"
	    LogType="ERROR">
    <LogText>
    Error - Disk ID: %s, not found in DB!
    </LogText>  
    <Description>
    Could not find the Disk ID referred, in the DB. 
    </Description>
  </LogDefEl>
 
  <LogDefEl LogId="NGAMS_WA_DB_CON"
            LogNumber="2001"
	    LogType="WARNING">
    <LogText>
    DB Connection not open - trying to reconnect ...
    </LogText>  
    <Description>
    A problem occurred interacting with the DB. It will be attempted
    to connect again, to see if problem may be rectified.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DB_COM"
            LogNumber="2002"
	    LogType="ERROR">
    <LogText>
    Problems communicating with the DB: %s
    </LogText>  
    <Description>
    A problem occurred interacting with the DB. It may be temporarily 
    impossible to communicate with the DB server. When this situation
    occurs, the system can buffer frames (if configured to do this).
    It will be attempted to archive these buffered frames at a later stage.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_NOTICE_NGAS_HOSTS"
            LogNumber="2003"
	    LogType="NOTICE">
    <LogText>
    Table ngas_hosts in the NGAS DB could not be accessed.
    </LogText>  
    <Description>
    A problem occurred while trying to access the ngas_hosts table
    in the NGAS DB. This in some cases is accepted as it is possible
    to operate NG/AMS without the availability of ngas_hosts. 
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_MIS_HOST"
            LogNumber="2004"
	    LogType="ALERT">
    <LogText>
    Did not find entry for NGAS Host: %s in DB table ngas_hosts.
    </LogText>  
    <Description>
    An entry is missing in the ngas_hosts table for an NGAS Host
    referred to e.g. in a request. This information is needed for
    instance in connection with the CLONE or RETRIEVE command to be
    able to locate files in an NGAS System.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DB_UNIQUE"
    LogNumber="2005"
    LogType="ERROR">
    <LogText>
      Unique constraint violated in DB when executing a query (%s)
    </LogText>  
    <Description>
      An SQL statement violated an unique constraint in the DB.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DB_GENERIC"
    LogNumber="2006"
    LogType="ERROR">
    <LogText>
      An exception (%s) ocurred when executing a query (%s) in the data base.
    </LogText>
    <Description>
      An error ocurred executing a query in the data base.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MAIN_DISK_WRONGLY_USED"
            LogNumber="3000"
	    LogType="ERROR">
    <LogText>
    Disk in slot: %s, with Logical Name: %s, is previously registered
    as a Main Disk but is now installed in a Replication Disk slot.
    </LogText>  
    <Description>
    When a disk has been registered by the system as being a Main Disk,
    it should not be attempted to use it later as a Replication Disk.
    The way to recover from this problem is to install the disk in a
    Main Disk Slot, together with the Replication Disk with which it
    was originally registered.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_REP_DISK_WRONGLY_USED"
            LogNumber="3001"
	    LogType="ERROR">
    <LogText>
    Disk in slot: %s, with Logical Name: %s, has previously been registered
    as a Replication Disk but is now installed in a Main Disk slot.
    </LogText>  
    <Description>
    When a disk has been registered by the system as being a Replication 
    Disk, it should not be attempted to use it later as a Main Disk.
    The way to recover from this problem is to install the disk in a
    Replication Disk Slot, together with the Main Disk with which it
    was originally registered.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DISK_INACCESSIBLE"
            LogNumber="3004"
	    LogType="ERROR">
    <LogText>
    Disk with ID: %s is not accessible (writable).
    </LogText>  
    <Description>
    NG/AMS probes for each disk installed and configured for an
    archiving system if it is possible to write on the disk. If not
    an error is returned.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_NO_TARG_DISKS"
            LogNumber="3005"
	    LogType="WARNING">
    <LogText>
    No target disks found for the Stream(s) with mime-type(s): %s.
    </LogText>  
    <Description>
    For each Data Stream Defined in the configuration file, a target
    disk must be available in order for the system to be able to 
    handle Archive Requests.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DISK_STATUS"
            LogNumber="3006"
	    LogType="ERROR">
    <LogText>
    Error querying information for disk with ID: %s - cannot generate
    disk status on disk!
    </LogText>  
    <Description>
    An error occurred while trying to query information about a disk
    from the NGAS DB. This means that it is not possible to generate
    the NGAS Disk Info Status File on the disk. This file is normally
    generated when the system goes Online/Offline. The status file for 
    the disk in question, may not be up to date. 

    Note, maybe the problem is caused by incorrect information in
    connection with the disk. Could also be caused by a general
    problem with the communication with the DB server.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_OFFLINE_PLUGIN"
            LogNumber="3007"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    A problem occurred while executing the Offline Plug-In. The system
    could not be brought properly to Offline State, or some actions
    may have been skipped.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ONLINE_PLUGIN"
            LogNumber="3008"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    A problem occurred while executing the Online Plug-In. The system
    could not be brought properly to Offline State, or some actions
    may have been skipped.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_INIT_SERVER"
            LogNumber="3009"
	    LogType="ERROR">
    <LogText>
    Problems occurred initializing NG/AMS Server. Error message: %s
    </LogText>  
    <Description>
    An error occurred while initializing the NG/AMS Server. The server
    could not be prepared for execution, and was terminated. Consult
    the NG/AMS Logs for further information.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MULT_INST"
            LogNumber="3010"
	    LogType="ERROR">
    <LogText>
    Apparently an instance of the NG/AMS Server is running or the server was
    not shut down properly previously! If it is desirable to force the
    server to start, use the -force command line parameter.
    </LogText>  
    <Description>
    Another instance of the NG/AMS Server may be running already as it
    was intended to start a session. Having several NG/AMS Servers
    running in parallel, may cause conflicts. If it is the intention
    to star a new session the previous server should be
    terminated. Otherwise, if it is the intention to run two servers,
    another communication port number could be specified. 

    A new session can be forced started using the -force command line option.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_INIT_LOG"
            LogNumber="3011"
	    LogType="ERROR">
    <LogText>
    Problem setting up logging properties! Check if log file: %s 
    can be created! Error: %s
    </LogText>  
    <Description>
    A problem occurred setting up the properties for the
    logging. Check the configuration file and/or the command line
    input parameters and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_OP_HTTP_SERV"
            LogNumber="3012"
	    LogType="ERROR">
    <LogText>
    Problems operating NG/AMS Server: %s
    </LogText>  
    <Description>
    The NG/AMS Server could not be started. This could because by
    conflicting port numbers, or other problems in connection with the
    network set-up.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_NOTICE_NO_DISKS_AVAIL"
            LogNumber="3013"
	    LogType="NOTICE">
    <LogText>
    Warning -- No Disks available in this NGAS System.
    NGAS ID: %s. Host ID: %s.
    </LogText>  
    <Description>
    No disks are available in this NGAS System. This may be OK if the 
    server is only acting as a proxy for other NGAS Nodes.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_NO_STO_SETS"
            LogNumber="3014"
	    LogType="ALERT">
    <LogText>
    No Storage Sets found for mime-type: %s
    </LogText>  
    <Description>
    No available Storage Set (disk set) was found for storing the data 
    with the Mime-type as referred above in the error message. Check 
    the disk configuration and the NG/AMS Configuration.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_NO_TARGET_DISK"
            LogNumber="3015"
	    LogType="ALERT">
    <LogText>
    NO SUITABLE TARGET DISK FOUND FOR DATA WITH MIME-TYPE: %s.
    - PROBABLY NEED TO CHANGE DISKS!
    </LogText>  
    <Description>
    No suitable Storage Set (disks) was found for storing the data with the 
    Mime-type as referred above in the error message. Check the disk
    configuration and the NG/AMS Configuration.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_STARTING_SRV"
            LogNumber="3016"
	    LogType="INFO">
    <LogText>
    Starting/initializing NG/AMS Server - Version: %s - Host: %s - Port %d
    </LogText>  
    <Description>
    The NG/AMS Server is initializing and preparing for execution.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_TERM_SRV"
            LogNumber="3017"
	    LogType="INFO">
    <LogText>
    NG/AMS Server terminating - Version: %s - Host: %s - Port %d
    </LogText>  
    <Description>
    The NG/AMS Server is cleaning and preparing to terminate execution.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_EMAIL_NOTIF"
            LogNumber="3019"
	    LogType="ERROR">
    <LogText>
    Problem sending email notification message to: %s sender: %s,
    using SMTP host: %s. Error: %s.
    </LogText>  
    <Description>
    The system could not send an Email Notification Message to the
    destination specified using the SMTP host specified. Check if the
    parameters are correct, in particular if the SMTP host is
    correctly specified and accessible.    
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_DATA_CHK_STAT"
            LogNumber="3020"
	    LogType="INFO">
    <LogText>
    Number of files checked: %d. Number of unregistered files found: %d.
    Number of bad files found: %d. Amount of data checked: %.3f MB.
    Checking rate: %.5f MB/s. Total time for checking: %.3fs.
    </LogText>  
    <Description>
    After one Data Checking cycle has been executed, it is possible to 
    configure NG/AMS to generate a log entry in the log outputs 
    (CFG: NgamsCfg.FileHandling:DataCheckLogSummary).
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ARCH_BACK_LOG_BUF"
            LogNumber="3021"
	    LogType="ERROR">
    <LogText>
    An error occurred while archiving data found in NG/AMS Back-Log 
    Buffer. Error: %s.
    </LogText>  
    <Description>
    An error was encountered when the NG/AMS Janitor Thread tried to
    archive a file found in the NG/AMS Back-Log Buffer. The
    symptom/type of the error is indicated in the error message.    
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_NO_DISK_SPACE"
            LogNumber="3022"
	    LogType="ERROR">
    <LogText>
    Not enough disk space for creating file: %s, of size: %d bytes.
    </LogText>  
    <Description>
    NG/AMS could not create a file with the given name of the given size.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_MV_FILE"
            LogNumber="3023"
	    LogType="ALERT">
    <LogText>
    Could not move file from location: %s to new location: %s. Error: %s.
    </LogText>  
    <Description>
    Problems occurred while trying to move/rename a file. If this
    happens while handling an Archive Request, the file cannot be
    archived and will be buffered in the Back-Log Buffer and handled
    at a later point in time.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_DISK_SPACE_SAT"
            LogNumber="3024"
	    LogType="ALERT">
    <LogText>
    The minimum amount of free system disk space (%d MB) is exceeded.
    Directories/parameters concerned: %s
    </LogText>  
    <Description>
    The system monitors the minimum free amount of disk space that should
    be available for the the directories used by NG/AMS for the operation.
    If the amount of free disk space for one of these directories (defined 
    in the configuration file), goes below a certain limit, the system will
    go automatically in Offline State and will not perform any further
    requests or operations.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_AL_CP_FILE"
            LogNumber="3025"
	    LogType="ALERT">
    <LogText>
    Could not copy file from location: %s to new location: %s. Error: %s
    </LogText>  
    <Description>
    Problems occurred while trying to copying a file.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_RETRIEVE_KEYS"
            LogNumber="4000"
	    LogType="ERROR">
    <LogText>
    Problem occurred retrieving key(s): %s, from data file: %s.
    </LogText>  
    <Description>
    The keyword cards listed above, could not be found in the file
    referred. This means that the handling of the file could not be
    carried out as expected.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DAPI"
            LogNumber="4001"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    An error occurred in the Data Handling Plug-In - the file has not
    been handled successfully, and has not been archived.

    The data in the file will be back-log buffered and attempted
    handled at a later stage.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DAPI_RM"
            LogNumber="4002"
	    LogType="ERROR">
    <LogText>
    %s
    </LogText>  
    <Description>
    An error occurred in the Data Handling Plug-In - the file has not
    been handled successfully, and has not been archived.

    The data in the file will be discarded by NG/AMS.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DAPI_BAD_FILE"
            LogNumber="4003"
	    LogType="ERROR">
    <LogText>
    Error occurred handling file: %s in DAPI: %s, Error: %s
    </LogText>  
    <Description>
    A DAPI detected a problem/inconsistency in the file being handled.
    The file is considered as bad and cannot be archived properly.
    
    The file will be discarded.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_REQ_HANDLING"
            LogNumber="4010"
	    LogType="ERROR">
    <LogText>
    Error occurred handling request! Error/exception: %s
    </LogText>  
    <Description>
    A problem occurred while handling a request issued to NG/AMS. The
    request could not be carried out successfully.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ARCHIVE_PUSH_REQ"
            LogNumber="4011"
	    LogType="ERROR">
    <LogText>
    Problem occurred handling Archive Push Request! URI: %s. Error: %s.
    </LogText>  
    <Description>
    A problem occurred while handling an Archive Push Request. The
    archive request has not been carried out successfully. It should
    be investigated what caused the problem, and the file should
    possibly be archived again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ARCHIVE_PULL_REQ"
            LogNumber="4012"
	    LogType="ERROR">
    <LogText>
    Problems occurred handling Archive Pull Request! URI: %s. Error: %s
    </LogText>  
    <Description>
    A problem occurred while handling an Archive Pull Request. The
    archive request has not been carried out successfully. It should
    be investigated what caused the problem, and the file should
    possibly be archived again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MISSING_URI"
            LogNumber="4013"
	    LogType="ERROR">
    <LogText>
    Must specify a URI for the data file to archive!
    </LogText>  
    <Description>
    When issuing an archive request, a URI must always be
    specified. This is used as reference to the file, and in the case
    of an Archive Pull Request, the URI is used to actually pick up
    the file.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_UNKNOWN_MIME_TYPE1"
            LogNumber="4014"
	    LogType="ERROR">
    <LogText>
    Could not determine mime-type for data file with URI: %s. Check 
    NG/AMS Configuration.
    </LogText>  
    <Description>
    From the extension of the file URI given, the mime-type could not
    be determined, i.e., is not among the mime-types defined in the
    configuration file. Check the configuration file to see if support
    for this type of data file should be added.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_IMPROPER_STATE"
            LogNumber="4015"
	    LogType="ERROR">
    <LogText>
    %s not allowed when in State/Sub-State: %s/%s. Allowed
    State(s)/Sub-State(s) are: %s/%s.
    </LogText>  
    <Description>
    The request issued cannot be handled by NG/AMS when in the
    State/Sub-State as indicated in the error message. Bring the
    system to one of the allowed States/Sub-States listed in the error
    message and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_CMD"
            LogNumber="4016"
	    LogType="ERROR">
    <LogText>
    Illegal command: %s received. Rejecting request!
    </LogText>  
    <Description>
    The command issued is not known/accepted by the NG/AMS
    Server. Check context and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_REQ"
            LogNumber="4017"
	    LogType="ERROR">
    <LogText>
    This NG/AMS is not configured for accepting %s Requests. Rejecting 
    request!
    </LogText>  
    <Description>
    This installation of NG/AMS, is not configured for accepting the
    request type as specified in the error message. Re-consider the
    request issued, or to configure the server to handle the given
    type of request.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_RETRIEVE_CMD"
            LogNumber="4018"
	    LogType="ERROR">
    <LogText>
    Incorrect parameter given for RETRIEVE command.
    </LogText>  
    <Description>
    The syntax specified for the RETRIEVE command is illegal.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_UNAVAIL_FILE"
            LogNumber="4019"
	    LogType="ERROR">
    <LogText>
    File with ID: %s appears not to be available.
    </LogText>  
    <Description>
    It was requested by a client to retrieve information about a
    certain file, or to return the file. This file however, appears
    not to be available. Check the File ID and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_UNKNOWN_DISK"
            LogNumber="4020"
	    LogType="ERROR">
    <LogText>
    Could not retrieve information about disk with Disk ID: %s. 
    Disk is probably unknown to this NG/AMS! Rejecting request!
    </LogText>  
    <Description>
    NG/AMS was requested by a client to return information about a
    specific disk. This disk however, is not known to NG/AMS. Check
    the Disk ID (or other information given with the query) and try again.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_RETRIEVE_REQ"
            LogNumber="4021"
	    LogType="ERROR">
    <LogText>
    Illegal retrieve request. Reason: %s
    </LogText>  
    <Description>
    The Retrieve Request could not be carried out due to the
    reason/problem described in the error message.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_BUF_DATA"
            LogNumber="4022"
	    LogType="WARNING">
    <LogText>
    Problems occurred while handling file with URI: %s. Data will be 
    Back-Log Buffered, and attempted archived at a later stage. Previous error 
    message: %s.
    </LogText>  
    <Description>
    A problem occurred while handling an Archive Request. The kind of 
    error that occurred, may be recovered later. The data has
    therefore been buffered by NG/AMS, and will be attempted archived
    (by an internal procedure) at a later stage.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_PROB_STAGING_AREA"
            LogNumber="4023"
	    LogType="ERROR">
    <LogText>
    Problem encountered, while storing data in Staging Area File: %s.
    Error: %s
    </LogText>  
    <Description>
    A problem occurred while storing the data on the HTTP connection
    into the Staging Area on the target disk. This might be caused by
    that the Staging Area directory is inaccessible, or the target
    disk as such, or that that there is no more space in the Staging Area.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_PROB_BACK_LOG_BUF"
            LogNumber="4024"
	    LogType="ERROR">
    <LogText>
    Problem encountered, while storing data of file with URI: %s, 
    in Back-Log Buffer: %s. Error: %s
    </LogText>  
    <Description>
    A problem occurred while storing data in the Back-Log Buffer Area.
    This might be caused by that the Back-Log Buffer directory is 
    inaccessible, or the target disk as such, or that that there is no 
    more space in the Staging Area.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_NOTICE_FILE_REINGESTED"
            LogNumber="4025"
	    LogType="NOTICE">
    <LogText>
    Note: File issued with URI: %s was already archived and has 
    been re-ingested!
    </LogText>  
    <Description>
    The file issued was already archived and has been re-ingested 
    into NGAS. This means in practice that an additional copy of the
    file is available in the NGAS data repository.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_ARCHIVING_FILE"
            LogNumber="4026"
	    LogType="INFO">
    <LogText>
    Archiving file with URI: %s
    </LogText>  
    <Description>
    NG/AMS is about to handle/archive the file referenced in the 
    log message. An additional message (additional messages) will 
    follow this one indicating if the archiving was successful or not.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_ARCHIVED"
            LogNumber="4027"
	    LogType="INFO">
    <LogText>
    Successfully archived file with URI: %s
    </LogText>  
    <Description>
    The file referenced by its URI in the log message was successfully
    handled/archived by NG/AMS
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MIS_PAR"
            LogNumber="4028"
	    LogType="ERROR">
    <LogText>
    Missing parameter: %s in connection with command: %s.
    </LogText>  
    <Description>
    Together with the command issued, the parameter listed above
    should have been issued. Since this is not the case, the
    request cannot be handled.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_AVAIL"
            LogNumber="4029"
	    LogType="INFO">
    <LogText>
    File with File ID: %s, is available on NGAS Host with Host ID: %s.
    </LogText>  
    <Description>
    The file with the given File ID, is available and accessible on the NGAS 
    system contacted.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_NOT_AVAIL"
            LogNumber="4030"
	    LogType="INFO">
    <LogText>
    File with File ID: %s, is not available on NGAS
    Host with Host ID: %s.
    </LogText>  
    <Description>
    The file with the given File ID, is not available/accessible
    on the NGAS Node contacted.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_REDIRECT"
            LogNumber="4031"
	    LogType="INFO">
    <LogText>
    Redirection URL: %s
    </LogText>  
    <Description>
    The resource requested is not available on the NGAS Node contacted,
    and the NG/AMS Server on this system cannot act as proxy to 
    handle the request. The request should be re-send by the client, using 
    the re-direction URL given.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_SERVICE_UNAVAIL"
            LogNumber="4032"
	    LogType="INFO">
    <LogText>
    The service: %s is not available on this system.
    </LogText>  
    <Description>
    The service needed for fulfilling the request is not available
    on this NG/AMS System. Could e.g. be File Retrieval.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_DPPI"
            LogNumber="4034"
	    LogType="ERROR">
    <LogText>
    Illegal DPPI: %s specified in connection with Retrieve
    Request. Given DPPI is not defined in the NG/AMS Configuration.
    </LogText>  
    <Description>
    An NG/AMS installation only accepts to execute DPPIs, which are
    explicitly defined in the NG/AMS Configuration. If a DPPI is
    specified, which is not defined in the configuration this will be
    rejected even if this DPPI might be available as such on the NGAS
    host handling the request. The problem can be solved by adding the
    name of the DPPI in the configuration file provided that this DPPI
    in fact is available on the system and that it is desirable to
    make this DPPI available for external users.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CMD_SYNTAX"
            LogNumber="4035"
	    LogType="ERROR">
    <LogText>
    The combination of parameters given together with the command: %s
    is illegal. Parameter(s): %s.
    </LogText>  
    <Description>
    The combinations of parameters given together with the command
    referred to in the error message is illegal (syntactic or
    semantically) wrong. Check the NG/AMS User's Manual or the online
    NG/AMS help for further information about the command.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CMD_EXEC"
            LogNumber="4036"
	    LogType="ERROR">
    <LogText>
    Problem(s) encountered executing command: %s. Error: %s
    </LogText>  
    <Description>
    A problem or problems was/were encountered while executing the
    command indicated in the error message. This may be due to an
    illegal combination of parameters, or due to that prerequisites
    for executing the command are not fulfilled.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DEL_FILE_DISK"
            LogNumber="4037"
	    LogType="ERROR">
    <LogText>
    Problem(s) encountered deleting file from disk. Disk ID: %s, File
    ID: %s, File Version: %d. Error: %s.
    </LogText>  
    <Description>
    A problem or problems was/were encountered while trying to delete 
    the referenced file from an NGAS disk. Could be due to e.g. that the
    disk is read-only mounted or that the file itself is read-only.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DEL_FILE_DB"
            LogNumber="4038"
	    LogType="ERROR">
    <LogText>
    Problem(s) encountered deleting file info from DB. Disk ID: %s, File
    ID: %s, File Version: %d. Error: %s.
    </LogText>  
    <Description>
    A problem or problems was/were encountered while trying to delete 
    the information for the referenced file from an NGAS DB. Could be
    due to that the DB user has not permission to carry out DELETE SQL
    statements.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_DEL_FILE"
            LogNumber="4039"
	    LogType="INFO">
    <LogText>
    Successfully deleted info for file. Disk ID: %s, File
    ID: %s, File Version: %d.
    </LogText>  
    <Description>
    The information for a file was successfully removed from the NGAS
    DB and from the NGAS disk hosting the file.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_DEL_STAT"
            LogNumber="4040"
	    LogType="INFO">
    <LogText>
    File deletion status. Files Selected: %d, Files Deleted: %d,
    Failed File Deletions: %d.
    </LogText>  
    <Description>
    Status over a REMFILE command indicating 1) How many files were
    selected for deletion, 2) How many files were deleted, 3) How many
    attempts to delete file that failed.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DEL_DISK"
            LogNumber="4041"
	    LogType="ERROR">
    <LogText>
    Problem encountered deleting files on disk. Disk ID: %s. Error: %s
    </LogText>  
    <Description>
    A problem was encountered while trying to delete files on the disk
    with the Disk ID given in the error message. Maybe the disk is
    mounted read-only.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DEL_DISK_DB"
            LogNumber="4042"
	    LogType="ERROR">
    <LogText>
    Problem encountered deleting disk info from DB. Disk ID: %s. Error: %s
    </LogText>  
    <Description>
    A problem was encountered while trying to delete the information
    for a disk from the NGAS DB. Maybe the DB user used, does not have
    permission to execute DELETE SQL statements.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_DEL_DISK"
            LogNumber="4043"
	    LogType="INFO">
    <LogText>
    Successfully deleted info for disk. Disk ID: %s.
    </LogText>  
    <Description>
    The information for a disk was successfully removed from the NGAS
    DB and the files on the disk successfully deleted.
    </Description>
  </LogDefEl>
 
  <LogDefEl LogId="NGAMS_INFO_DEL_DISK_SEL"
            LogNumber="4044"
	    LogType="INFO">
    <LogText>
    Info for disk selected for deletion. Disk ID: %s.
    </LogText>  
    <Description>
    The REMDISK command given, would delete the disk referenced to in
    the log message if execute=1 would be specified.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_DEL_DISK2"
            LogNumber="4045"
	    LogType="WARNING">
    <LogText>
    No disk found on NGAS Host: %s with Disk ID: %s. No disk selected.
    </LogText>  
    <Description>
    The REMDISK command given, did not match any disk installed in the
    contacted NGAS Host.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_FILE_COPIES"
            LogNumber="4046"
	    LogType="WARNING">
    <LogText>
    One or more files requested to be deleted are not available in at
    least 3 independent copies within this NGAS system.
    </LogText>  
    <Description>
    For security reasons it is enforced by NG/AMS to have at least two
    independent copies of each file (defined by a File ID + File Version). 
    
    In case of a REMDISK or REMFILE command, it will be checked for
    each file that would be deleted by the request, if it is available
    within the NGAS system in at least 3 independent copies.

    Independent copies is defined as instances of one file stored
    on different storage media.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_UNKNOWN_MIME_TYPE2"
            LogNumber="4047"
	    LogType="ERROR">
    <LogText>
    Illegal mime-type: %s issued in Archive Request for file with URI: %s.
    Rejecting request.
    </LogText>  
    <Description>
    The mime-type specified in the Archive Request for the file with
    the given URI is unknown to this NG/AMS installation. Check the
    configuration.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_TARG_DISK"
            LogNumber="4048"
	    LogType="ERROR">
    <LogText>
    The target disk specified with Disk ID: %s cannot store more
    files (is completed). Remarks: %s
    </LogText>  
    <Description>
    A disk specified as Target Disk for storing files, is marked as
    completed and cannot store more files. This error can occurr for
    instance during an CLONE command when a Target Disk is explicitly
    specified, which cannot be used as storage disk.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_PATH"
            LogNumber="4049"
	    LogType="ERROR">
    <LogText>
    Illegal path or filename specified: %s. Context: %s
    </LogText>  
    <Description>
    A filename or path specified, does not exists or is not
    readable/accessible.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_FILES_NOT_REG"
            LogNumber="4050"
	    LogType="WARNING">
    <LogText>
    One or more files stored on a disk, which contents is about to be
    deleted are not registered in the NGAS DB.
    </LogText>  
    <Description>
    For security reasons NG/AMS do not allow to remove files not
    registered in the NGAS DB, as these could be valuable files, which
    should not be deleted.

    It is necessary to remove these files (manually) or to archive
    them onto another media, before the disk can be removed.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_CLONED"
            LogNumber="4051"
	    LogType="INFO">
    <LogText>
    Cloned file - File ID: %s, File Version: %s, 
    located on disk with ID: %s and host with ID %s
    </LogText>  
    <Description>
    The file with the given ID and version, which is located on the
    host referenced, was successfully cloned.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_FILE_CLONE_FAILED"
            LogNumber="4052"
	    LogType="ERROR">
    <LogText>
    Failed in cloning file - File ID: %s, File Version: %s, 
    located on disk with ID: %s and host with ID %s. Error: %s
    </LogText>  
    <Description>
    The file with the given ID and version, which is located on the
    host referenced, could not be cloned.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_CLONE_REJECTED"
            LogNumber="4053"
	    LogType="ERROR">
    <LogText>
    The clone command was rejected. Reason: %s
    </LogText>  
    <Description>
    The CLONE command could not be exeucted due to the reason given in
    the error message.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_REGISTERED"
            LogNumber="4054"
	    LogType="INFO">
    <LogText>
    Registered file: %s - File ID: %s, File Version: %s, Format: %s
    </LogText>  
    <Description>
    The file with the path specified, was registered successfully in
    the NGAS DB.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_FILE_REG_FAILED"
            LogNumber="4055"
	    LogType="ERROR">
    <LogText>
    Failed in registering file: %s. Error: %s
    </LogText>  
    <Description>
    The file with the path specified, could not be registered in the NGAS DB.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_FILE_OK"
            LogNumber="4056"
	    LogType="INFO">
    <LogText>
    Checked file with File ID: %s/File Version: %d/Disk ID: %s/Slot ID: %s/
    Host ID: %s - file found to be consistent.
    </LogText>  
    <Description>
    A consistency check was carried out on the referenced file. The file
    was found to be OK.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_FILE_NOK"
            LogNumber="4057"
	    LogType="ERROR">
    <LogText>
    Checked file with File ID: %s/File Version: %d/Disk ID: %s/Slot ID: %s/
    Host ID: %s - file found to be inconsistent%s
    </LogText>  
    <Description>
    A consistency check was carried out on the referenced file,  one or
    more discrepancies were detected.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_COM"
            LogNumber="4058"
	    LogType="ERROR">
    <LogText>
    An error occurred while trying to communicate with NG/AMS Server on
    host/port: %s/%d. Error: %s
    </LogText>  
    <Description>
    An error was encountered while trying to communicate the the NG/AMS
    Server referenced. The type of problem is indicated if possible.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_REQ_ID"
            LogNumber="4059"
	    LogType="ERROR">
    <LogText>
    The specified Request ID: %s is not (or no-longer) registered.
    </LogText>  
    <Description>
    The specified Request ID is not registered in the list of Request IDs.
    It may also be that the request was finished, and the entry removed
    from the internal list.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ILL_URI"
            LogNumber="4060"
	    LogType="ERROR">
    <LogText>
    The URI specified: %s is illegal. Context: %s
    </LogText>  
    <Description>
    A URI given e.g. with an Archive Command is illegal and the
    resource referred to cannot be accessed.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_WA_FILE_NON_REM"
            LogNumber="4061"
	    LogType="WARNING">
    <LogText>
    File requested to be deleted cannot be removed. The file(s) might
    be read-only or be marked to be ignored or as bad in the DB.
    </LogText>  
    <Description>
    A REMFILE or REMDISK command could not be execute because one or
    more files scheduled for deletion could not be removed.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_MAX_REQ_EXCEEDED"
            LogNumber="4062"
	    LogType="ERROR">
    <LogText>
    The maximum number of simultaneous requests (%d) has been exceeded.
    The request cannot be handled now. Rejecting request.
    </LogText>  
    <Description>
    The Maximum Number of Simultaneous Requests (defined by the
    configuration parameter Ngams:MaxSimReqs) has been exhausted.
    The request cannot be handled. It should be retried later to issue
    the reuqest.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DISCARD_NOT_FOUND"
            LogNumber="4063"
	    LogType="ERROR">
    <LogText>
    File scheduled to be discarded not found: %s. NGAS Node: %s.
    </LogText>  
    <Description>
    A file referenced with by its Disk ID, File ID and File Version,
    or by its path, could not be located on the contacted system.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DISCARD_NOT_REM"
            LogNumber="4064"
	    LogType="ERROR">
    <LogText>
    File scheduled to be discarded not removable: %s. NGAS Node: %s.
    </LogText>  
    <Description>
    A file referenced with by its Disk ID, File ID and File Version,
    or by its path, cannot be removed.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_DISCARD_GRANTED"
            LogNumber="4065"
	    LogType="INFO">
    <LogText>
    File discard request granted. File: %s. NGAS Node %s.
    </LogText>  
    <Description>
    A file referenced with by its Disk ID, File ID and File Version,
    or its path can be discarded.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_DISCARD_OK"
            LogNumber="4066"
	    LogType="INFO">
    <LogText>
    File discarded: %s. NGAS Node: %s.
    </LogText>  
    <Description>
    A file referenced with by its Disk ID, File ID and File Version,
    or its path was successfully discarded.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_DISCARD_FAILED"
            LogNumber="4067"
	    LogType="ERROR">
    <LogText>
    File discard request failed: %s. NGAS Node: %s. Error: %s.
    </LogText>  
    <Description>
    A file referenced with by its Disk ID, File ID and File Version,
    or its path could not be discarded.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_INFO_ARCH_REQ_OK"
            LogNumber="4068"
	    LogType="INFO">
    <LogText>
    Handling of Archive Request for mime-type: %s is possible on node: %s
    </LogText>  
    <Description>
    Data files with the given mime-type can be handled on the referenced node
    at this point in time.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ARCH_REQ_NOK"
            LogNumber="4069"
	    LogType="ERROR">
    <LogText>
    Handling of Archive Request for mime-type: %s is not possible on node: %s
    </LogText>  
    <Description>
    Data files with the given mime-type cannot be handled on the
    referenced node at this point in time or in general.
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_ARCH_RECV"
            LogNumber="4070"
	    LogType="ERROR">
    <LogText>
    Error occurred while receiving data for file with URI:
    %s. Expected size: %d bytes. Actual size: %d bytes.
    </LogText>  
    <Description>
    An error ocurred while receiving the data in connection with an Archive
    Request. Less bytes were received than expected. This could be
    caused by a communication issue on the network connection between
    the client and the server.	    
    </Description>
  </LogDefEl>

  <LogDefEl LogId="NGAMS_ER_UNAUTH_REQ"
            LogNumber="4100"
	    LogType="ERROR">
    <LogText>
    Unauthorized request received. 
    </LogText>  
    <Description>
    A request was issued to a server, which has HTTP Authentication enabled. 
    The client did not provide a valid authentication code.
    </Description>
  </LogDefEl>




</LogDef>


<!-- EOF -->

"""

# EOF
