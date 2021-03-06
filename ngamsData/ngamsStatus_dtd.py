"""
<?xml version="1.0" encoding="UTF-8"?>
<!ENTITY % XmlStd SYSTEM "http://ngas01.sco.alma.cl:7777/RETRIEVE?internal=XmlStd.dtd">
%XmlStd;
<!ENTITY % NgamsInternal SYSTEM 
           "http://ngas01.sco.alma.cl:7777/RETRIEVE?internal=ngamsInternal.dtd">
%NgamsInternal;

<!-- 
  E.S.O.
 
  Who        When        What
  ********   **********  ***************************************************
  jknudstr   04.04.2001  Created
  **************************************************************************
  ngamsStatus.dtd defines the contents and lay-out of the
  NG/AMS Status Report.

  Consult the DTD ngamsInternal.dtd which contains the actual definition
  of the elements of the NGAMS Status.
  -->


<!-- 
  The NgamsStatus element is the root element of the NGAMS Status Document.
  -->
<!ELEMENT NgamsStatus (Header, Status, NgamsCfg?, DiskStatus*, FileList*)>


<!-- 
  The Status Element is used to generate a status report e.g. in
  connection with the execution of a command.

  Attributes:
    Date:                    Date this Status Element was generated.

    Version:                 Version of NG/AMS generating the status.

    HostId:                  Name of host where the NG/AMS Server is running.

    Status:                  Overall status of the status information. Can be 
                             used to signal if errors are contained in
                             the Status Elements.

    Message:                 Message generated by the NG/AMS Server.

    State:                   State of the NG/AMS Server.

    SubState:                Sub-State of the NG/AMS Server.

    RequestId:               Request ID allocated to a specific request.

    RequestTime:             Time the request was received. Given in the 
                             ISO-8601 format.

    CompletionPercent:       The degree of (estimated) completion of the
                             request (in percent).
  
    ExpectedCount:           The expected number of iterations to be done
                             (e.g. files to be handled).

    ActualCount:             The current number of iterations done (e.g. files
                             handled).

    EstTotalTime:            The complete (estimated) time for carrying out the
                             request. Given in the format: HH:MM:SS.
 
    RemainingTime:           The (estimated) remaining time for carrying out  
                             the request. Given in the format: HH:MM:SS.

    LastRequestStatUpdate:   Last time the request status was updated. 
                             Given in the ISO-8601 format.

    CompletionTime:          Time when the request was completed. 
                             Given in the ISO-8601 format.
  -->
<!ELEMENT Status  EMPTY>
<!ATTLIST Status  Date                   CDATA             #REQUIRED
                  Version                CDATA             #REQUIRED
                  HostId                 CDATA             #REQUIRED
                  Status                 (OK|FAILURE|-)    "-"
                  Message                CDATA             #IMPLIED
                  State                  (ONLINE|OFFLINE)  "OFFLINE"
                  SubState               (IDLE|BUSY)       "IDLE"
                  RequestId              CDATA             #IMPLIED
                  RequestTime            CDATA             #IMPLIED
                  CompletionPercent      CDATA             #IMPLIED
                  ExpectedCount          CDATA             #IMPLIED
                  ActualCount            CDATA             #IMPLIED
                  EstTotalTime           CDATA             #IMPLIED
                  RemainingTime          CDATA             #IMPLIED
                  LastRequestStatUpdate  CDATA             #IMPLIED
                  CompletionTime         CDATA             #IMPLIED>


<!-- 
  The NgamsCfg Element contains the configuration used by NG/AMS.
  -->
<!ELEMENT NgamsCfg (Ngams, Db?, StorageSet*, Stream*, FileHandling?, 
                    Monitor?, Log?, Notification?, HostSuspension)>


<!-- 
  The DiskStatus Element contains the status for each disk and the
  status for the files stored on an HDD.

  Attributes:
    DiskId:             Unique ID for the HDD.

    Archive:            ID of the archive to which this disk belongs

    InstallationDate:   Date (ISO-8601) the disk was prepared.

    Type:               Type of the HDD.

    LogicalName:        Logical (human readable/memorable) name of 
                        the HDD.

    MainDisk:           Indicates if the HDD is the Main Disk or the
                        Replication Disk (0|1).

    HostId:             Name of the host where the HDD is installed.

    SlotId:             Slot ID (number) in which the HDD is installed.

    Mounted:            Indicates if the HDD is mounted in this NGAS
                        System (0|1).

    MountPoint:         Indicates the mount point for the HDD (path).

    NumberOfFiles:      Number of files stored on the disk.

    AvailableMb:        Indicates the capacity of the HDD (MB).

    BytesStored:        Bytes stored on the HDD.

    Completed:          Indicates if the disk is full - no more data
                        should be stored on this disk.

    Checksum:           Checksum for the data on the disk.

    TotalDiskWriteTime: Total time in seconds used for writing the 
                        bytes stored on this disk (s).
		
    LastCheck:          Date for last check.
  -->
<!ELEMENT DiskStatus (FileStatus*)>
<!ATTLIST DiskStatus DiskId              CDATA  #REQUIRED
                     Archive             CDATA  #REQUIRED
                     InstallationDate    CDATA  #REQUIRED
                     Type                CDATA  #REQUIRED
                     LogicalName         CDATA  #REQUIRED
                     MainDisk            (0|1)  #REQUIRED
                     HostId              CDATA  #REQUIRED
                     SlotId              CDATA  #REQUIRED
                     Mounted             (0|1)  #REQUIRED
                     MountPoint          CDATA  #REQUIRED
                     NumberOfFiles       CDATA  #REQUIRED
                     AvailableMb         CDATA  #REQUIRED
                     BytesStored         CDATA  #REQUIRED
                     Completed           (0|1)  #REQUIRED
                     CompletionDate      CDATA  #REQUIRED
                     Checksum            CDATA  #REQUIRED
                     TotalDiskWriteTime  CDATA  #REQUIRED
                     LastCheck           CDATA  #IMPLIED>


<!-- 
  The FileStatus Element contains the status of each file stored on
  the individual HDD.

  Attributes:
    FileName:              Name of the file (relative to the disk
                           mount point).

    FileId:                ID of the file, e.g. DP ID for ESO FITS files.

    FileVersion:           File Version.

    Format:                Mime-type of file.

    FileSize:              Size of the file (bytes).

    UncompressedFileSize:  Size of file uncompressed (bytes). Same as 
                           FileSize if uncompressed.

    Compression:           Type of compression applied on the file.

    IngestionDate:         Date the file was ingested (ISO8601).

    Ignore:                Ignore flag as set in the DB.
 
    Checksum:              Checksum for the file.

    ChecksumPlugIn:        Plug-in used to calculate the checksum.

    FileStatus:            File status as set in the DB.

    Tag:                   Tag, which can be used to add information about the 
                           file, not necessarily coming from the DB. 

    Permissions:           Permissions for file (UNIX style).

    Owner:                 Owner of file (user name).

    Group:                 Group for file.

    ModificationDate:      Date for last modification (ISO8601).

    AccessDate:            Date for last access (ISO8601).
  -->
<!ELEMENT FileStatus EMPTY>
<!ATTLIST FileStatus FileName              CDATA         #IMPLIED
                     FileId                CDATA         #IMPLIED
                     FileVersion           CDATA         #IMPLIED
                     Format                CDATA         #IMPLIED
                     FileSize              CDATA         #IMPLIED
                     UncompressedFileSize  CDATA         #IMPLIED
                     Compression           CDATA         #IMPLIED
                     IngestionDate         CDATA         #IMPLIED
                     Ignore                (0|1)         #IMPLIED
                     Checksum              CDATA         #IMPLIED
                     ChecksumPlugIn        CDATA         #IMPLIED
                     FileStatus            CDATA         #IMPLIED
                     Tag                   CDATA         #IMPLIED
                     Permissions           CDATA         #IMPLIED       
                     Owner                 CDATA         #IMPLIED
                     Group                 CDATA         #IMPLIED
                     ModificationDate      CDATA         #IMPLIED
                     AccessDate            CDATA         #IMPLIED>

<!-- 
  The FileList Element is used to contain a list of files. This can be
  used for various purposes, is e.g. used for the CLONE command to 
  indicate which files were attempted to be cloned but which couldn't
  be properly cloned.

  The element contain 1 or more FileStatus Elements.

  Attributes:
    Name:       Name allocated to the list.

    Id:         A short ID allocated to the file list. Should normally
                be a one word string, e.g.: 'PROCESSED_FILES'.

    Comment:    A comment can be added to a File List to remark
                special conditions.

    Status:     A status allocated to the File List.
  -->		    
<!ELEMENT FileList (FileStatus+ | FileList+)>
<!ATTLIST FileList Id             CDATA         #REQUIRED
                   Comment        CDATA         #IMPLIED
                   Status         CDATA         #IMPLIED>


<!-- EOF -->
"""

# EOF
