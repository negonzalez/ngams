"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE NgamsCfg SYSTEM "ngamsCfg.dtd">

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

<NgamsCfg Id="ngamsCfgSim">

  <Header Context="NGAMS" 
          Name="ngamsServer.xml" 
          Release="1.0" 
          Revision="@(#) $Id: ngamsCfgSim.xml,v 1.3 2008/08/19 20:51:50 jknudstr Exp $"
          Source="jknudstr@eso.org" 
          Type="NGAMS-TEST-CONFIGURATION">
    <Description/>
  </Header>

  <Server Id="Server-Sim"
          ArchiveName="ESO-ARCHIVE" 
          BlockSize="65536"
          MaxSimReqs="30" 
          MountRootDirectory="/NGAS" 
          PortNo="7777" 
          ProxyMode="1"
          Simulation="1"
          SwVersion="v2.3.3"/>

  <JanitorThread Id="JanitorThread-Std"
                 SuspensionTime="0T00:00:30" 
                 MinSpaceSysDirMb="5000"/>

  <ArchiveHandling Id="ArchiveHandling-Test"
                   ArchiveUnits="ngasdev1" 
                   BackLogBufferDirectory="/NGAS/ngams_staging"
                   BackLogBuffering="1"
                   FreeSpaceDiskChangeMb="200"
                   MinFreeSpaceWarningMb="5000"
                   PathPrefix="saf"
                   Replication="1"/>

  <Db Id="Db-TESTSRV-ngastst1"
      Interface="ngamsSybase" 
      Name="ngastst1" 
      Password="bmdhc19wdw==" 
      Server="TESTSRV" 
      Snapshot="1" 
      User="ngas"/>

  <SystemPlugIns Id="SystemPlugIns-Std"
                 LabelPrinterPlugIn="ngamsBrotherPT9200DxPlugIn" 
                 LabelPrinterPlugInPars="dev=/dev/ttyS0,font_file=/opsw/packages/ngams/ngamsData/ngamsBrotherPT9200DxFonts.fnt" 
                 OfflinePlugIn="ngamsLinuxOfflinePlugIn" 
                 OfflinePlugInPars="unmount=0" 
                 OnlinePlugIn="ngamsLinuxOnlinePlugIn" 
                 OnlinePlugInPars="uri=http://localhost:1080/technical.html,
                                   module=3w-xxxx,old_format=1"
                 DiskSyncPlugIn="ngams3wareDiskSyncPlugIn"
                 DiskSyncPlugInPars="controllers=1/2"/>
 
  <Permissions Id="Permissions-Test"
               AllowArchiveReq="1" 
               AllowProcessingReq="1" 
               AllowRemoveReq="1" 
               AllowRetrieveReq="1"/>

  <MimeTypes Id="MimeTypes-Std">
    <MimeTypeMap Extension="fits" MimeType="image/x-fits"/>
    <MimeTypeMap Extension="nglog" MimeType="ngas/nglog"/>
    <MimeTypeMap Extension="nglog.Z" MimeType="application/x-nglog"/>
    <MimeTypeMap Extension="log" MimeType="text/log-file"/>
    <MimeTypeMap Extension="log.Z" MimeType="application/x-clog"/>
    <MimeTypeMap Extension="paf" MimeType="ngas/paf"/>
    <MimeTypeMap Extension="fits.gz" MimeType="application/x-gfits"/>
    <MimeTypeMap Extension="fits.Z" MimeType="application/x-cfits"/>
    <MimeTypeMap Extension="hfits" MimeType="application/x-hfits"/>
    <MimeTypeMap Extension="hdr" MimeType="image/x-fitshdr"/>
    <MimeTypeMap Extension="tar" MimeType="application/x-tar"/>
  </MimeTypes>

  <StorageSets Id="StorageSets-PATA-8-Dbl">
    <StorageSet DiskLabel="FITS"
                MainDiskSlotId="1"
                Mutex="0" 
                RepDiskSlotId="2" 
                StorageSetId="StorageSet1" 
                Synchronize="1"/>
    <StorageSet MainDiskSlotId="3" 
                Mutex="0" 
                RepDiskSlotId="4"
                StorageSetId="StorageSet2" 
                Synchronize="1"/>
    <StorageSet DiskLabel="FITS" 
                MainDiskSlotId="5" 
                Mutex="0" 
                RepDiskSlotId="6" 
                StorageSetId="StorageSet3" 
                Synchronize="1"/>
    <StorageSet MainDiskSlotId="7" 
                Mutex="0" 
                RepDiskSlotId="8" 
                StorageSetId="StorageSet4" 
                Synchronize="1"/>
  </StorageSets>

  <Streams Id="Streams-4-Dbl">
    <Stream MimeType="image/x-fits" 
            PlugIn="ngasGarArchFitsDapi" 
            PlugInPars="compression=compress -f,
                        checksum_util=utilFitsChecksum,
                        checksum_result=0/0000000000000000,
                        frame_ingest_db_id=TEST_SRV">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="cal/x-fits" PlugIn="ngamsCalibDapi" PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="cal/x-tfits" PlugIn="ngamsCalibDapi" PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="non/existing" PlugIn="ngamsNonExisting" PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="application/x-cfits"
            PlugIn="ngamsFitsPlugIn" 
            PlugInPars="compression=compress -f,
                        checksum_util=utilFitsChecksum,
                        checksum_result=0/0000000000000000">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="application/x-gfits" 
            PlugIn="ngamsFitsPlugIn" 
            PlugInPars="compression=compress -f,
                        checksum_util=utilFitsChecksum,
                        checksum_result=0/0000000000000000">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="ngas/nglog" 
            PlugIn="ngamsNgLogPlugIn"
            PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="text/log-file"
            PlugIn="ngamsNgLogPlugIn"
            PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
    <Stream MimeType="application/x-tar"
            PlugIn="ngasTarBallPlugIn"
            PlugInPars="">
      <StorageSetRef StorageSetId="StorageSet1"/>
      <StorageSetRef StorageSetId="StorageSet2"/>
      <StorageSetRef StorageSetId="StorageSet3"/>
      <StorageSetRef StorageSetId="StorageSet4"/>
    </Stream>
  </Streams>

  <Processing Id="Processing-Std"
              ProcessingDirectory="/NGAS">
    <PlugIn Name="ngamsEsoArchDppi" 
            PlugInPars="">
      <MimeType Name="image/x-fits"/>
      <MimeType Name="application/x-gfits"/>
      <MimeType Name="application/x-cfits"/>
    </PlugIn>
    <PlugIn Name="ngamsExtractFitsHdrDppi" 
            PlugInPars="">
      <MimeType Name="image/x-fits"/>
      <MimeType Name="application/x-gfits"/>
      <MimeType Name="application/x-cfits"/>
    </PlugIn>
    <PlugIn Name="ngasWfiPreview" 
            PlugInPars="">
      <MimeType Name="image/x-fits"/>
      <MimeType Name="application/x-gfits"/>
      <MimeType Name="application/x-cfits"/>
    </PlugIn>
  </Processing>

  <Register Id="Register-Std">
    <PlugIn Name="ngamsFitsRegPlugIn" 
            PlugInPars="checksum_util=utilFitsChecksum,
                        checksum_result=0/0000000000000000">
      <MimeType Name="image/x-fits"/>
      <MimeType Name="application/x-gfits"/>
      <MimeType Name="application/x-cfits"/>
    </PlugIn>
  </Register>

  <DataCheckThread Id="DataCheckThread-Test"
                   Active="1" 
                   ChecksumPlugIn="ngamsGenCrc32"  
                   ChecksumPlugInPars="" 
		   DiskSeq="SEQUENTIAL" 
                   FileSeq="SEQUENTIAL" 
                   ForceNotif="1" 
                   LogSummary="1" 
                   MaxProcs="4" 
                   MinCycle="01T00:00:00" 
                   Prio="0" 
                   Scan="0"/>

  <Log Id="Log-Test" 
       LocalLogFile="/NGAS/ngams_staging/log/LogFile.nglog" 
       LocalLogLevel="4" 
       LogBufferSize="0"
       LogRotateCache="30" 
       LogRotateInt="00T01:00:00" 
       SysLog="1" 
       SysLogPrefix="NGASLog"/>

  <Notification Id="Notification-Test"
                Active="1" 
                MaxRetentionSize="1" 
                MaxRetentionTime="00T00:30:00" 
                Sender="ngast@eso.org" 
                SmtpHost="smtphost.hq.eso.org">
    <AlertNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </AlertNotification>
    <ErrorNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </ErrorNotification>
    <DiskSpaceNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </DiskSpaceNotification>
    <DiskChangeNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </DiskChangeNotification>
    <NoDiskSpaceNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </NoDiskSpaceNotification>
    <DataCheckNotification>
      <EmailRecipient Address="DEFINE@eso.org"/>
    </DataCheckNotification>
  </Notification>

  <HostSuspension Id="HostSuspension-Test" 
                  IdleSuspension="0" 
                  IdleSuspensionTime="60" 
                  SuspensionPlugIn="ngamsSuspensionPlugIn" 
                  SuspensionPlugInPars="--SuspensionPlugInPars--" 
                  WakeUpCallTimeOut="200" 
                  WakeUpPlugIn="ngamsWakeUpPlugIn" 
                  WakeUpPlugInPars="eth0,eth1" 
                  WakeUpServerHost="dmdarc1"/>

  <SubscriptionDef Id="SubscriptionDef-Test" 
                   AutoUnsubscribe="1" 
                   BackLogExpTime="28T00:00:00" 
                   Enable="0" 
                   SuspensionTime="0T00:03:00">
    <Subscription  HostId="HostId1"
                   PortNo="1234"
                   Priority="1"
                   SubscriberUrl="http://test.url1"
                   FilterPlugIn="FilterPlugIn1"
                   FilterPlugInPars="1,2,3,4"/>
    <Subscription  HostId="HostId2"
                   PortNo="5678"
                   Priority="2"
                   SubscriberUrl="http://test.url2"
                   FilterPlugIn="FilterPlugIn2"
                   FilterPlugInPars="5,6,7,8"/>
  </SubscriptionDef>


  <Authorization Id="Authorization-Test"
                 Enable="1">
    <User Name="ngas" 
          Password="X05nYVNf"/>
    <User Name="ngasmgr" 
          Password="X05nYXNfTWdyXw=="/>
    <User Name="ngasweb"
          Password="X05nYXNfV2ViXw=="/>
    <User Nams="ngasext"
          Password="X05nYXNfRXh0Xw=="/>
  </Authorization>

</NgamsCfg>

"""

# EOF
