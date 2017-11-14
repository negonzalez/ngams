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
# "@(#) $Id: ngamsCmd_HTTPFETCH.py,v 1.1 2012/11/22 21:48:22 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jagonzal  2010/17/01  Created
#

"""
NGAS Command Plug-In, implementing an Archive Command specific for Mirroring 

This works in a similar way as the 'standard' ARCHIVE Command, but has been
simplified in a few ways:
  
  - No replication to a Replication Volume is carried out.
  - Target disks are selected randomly, disregarding the Streams/Storage Set
    mappings in the configuration. This means that 'volume load balancing' is
    provided.
  - Archive Proxy Mode is not supported.
  - No probing for storage availability is supported.
  - In general, less SQL queries are performed and the algorithm is more
    light-weight.
  - crc is computed from the incoming stream
  - ngas_files data is 'cloned' from the source file
"""

import os
from ngams import TRACE, info, genLog, checkCreatePath
from ngamsFailedDownloadException import FailedDownloadException
from ngams.ngamsLib import ngamsLib, ngamsHighLevelLib
from pcc.pccUt import PccUtTime
import binascii
import socket

def calculateCrc(filename, blockSize):
    crc = 0
    try:
        fdin = open(filename, "r")
        buff = "-"
        while len(buff) > 0:
            buff = fdin.read(blockSize)
            crc = binascii.crc32(buff, crc)
    finally:
        fdin.close()
    return crc

def saveToFile(srvObj,
                       ngamsCfgObj,
                       reqPropsObj,
                       trgFilename,
                       blockSize,
                       startByte):
    """
    Save the data available on an HTTP channel into the given file.
    
    ngamsCfgObj:     NG/AMS Configuration object (ngamsConfig).

    reqPropsObj:     NG/AMS Request Properties object (ngamsReqProps).
        
    trgFilename:     Target name for file where data will be
                     written (string).

    blockSize:       Block size (bytes) to apply when reading the data
                     from the HTTP channel (integer).

    mutexDiskAccess: Require mutual exclusion for disk access (integer).

    diskInfoObj:     Disk info object. Only needed if mutual exclusion
                     is required for disk access (ngamsDiskInfo).
            
    Returns:         Tuple. Element 0: Time in took to write
                     file (s) (tuple).
    """
    TRACE()
    
    info(4, "Setting reference in request handle object to the read socket.")
    disk_id = reqPropsObj.getFileInfo()['diskId']
    source_host = reqPropsObj.getFileInfo()['sourceHost']
    host_id = reqPropsObj.getFileInfo()['hostId']
    file_version = reqPropsObj.getFileInfo()['fileVersion']
    file_id = reqPropsObj.getFileInfo()['fileId']
    fetchCommand = "http://" + source_host + "/RETRIEVE?disk_id=" + disk_id
    fetchCommand += "&host_id=" + host_id
    fetchCommand += "&quick_location=1&file_version=" + file_version 
    fetchCommand += "&file_id=" + file_id
    fileUri = fetchCommand
    reqPropsObj.setFileUri(fileUri)
    info(1, "fileUri: " + fileUri)

    originalTimeout = socket.getdefaulttimeout()
    try:
        rx_timeout = 30 * 60
        if srvObj.getCfg().getVal("Mirroring[1].rx_timeout"):
            rx_timeout = int(srvObj.getCfg().getVal("Mirroring[1].rx_timeout"))
        socket.setdefaulttimeout(rx_timeout)
        readFd = ngamsHighLevelLib.openCheckUri(fileUri, startByte)
    finally:
        socket.setdefaulttimeout(originalTimeout)
    # can we resume a previous download?
    downloadResumeSupported = serverSupportsResume(readFd)

    info(4,"Creating path: " + trgFilename + " ...")
    checkCreatePath(os.path.dirname(trgFilename))
    if startByte != 0: info(3, "resume requested")
    if startByte != 0 and downloadResumeSupported:
        info(3, "Resume requested and mirroring source supports resume. Appending data to previously started staging file")
        crc = calculateCrc(trgFilename, blockSize)
        reqPropsObj.setBytesReceived(startByte)
        fdOut = open(trgFilename, "a")
    else:
        if (startByte > 0): info(2, "Resume of download requested but server does not support it. Starting from byte 0 again.")
        fdOut = open(trgFilename, "w")
        crc = 0
    timer = PccUtTime.Timer()
    try:

        # Distinguish between Archive Pull and Push Request. By Archive
        # Pull we may simply read the file descriptor until it returns "".
        info(3,"It is an HTTP Archive Pull Request: trying to get Content-length")
        httpInfo = readFd.info()
        headers = httpInfo.headers
        hdrsDict = ngamsLib.httpMsgObj2Dic(''.join(headers))
        if hdrsDict.has_key('content-length'):
            remSize = int(hdrsDict['content-length'])
            info(3,"Content-length is: %s" % str(remSize))
        else:
            info(3,"No HTTP header parameter Content-length!")
            info(3,"Header keys: %s" % hdrsDict.keys())
            remSize = int(1e11)

        # Receive the data.
        buf = "-"
        rdSize = blockSize
        while (remSize > 0):
            if (remSize < rdSize): rdSize = remSize
            buf = readFd.read(rdSize)
            sizeRead = len(buf)
            if sizeRead == 0: 
                raise Exception("server is unreachable")
            else:
                crc = binascii.crc32(buf, crc)
                remSize -= sizeRead
                reqPropsObj.setBytesReceived(reqPropsObj.getBytesReceived() +\
                                         sizeRead)
                fdOut.write(buf)

        deltaTime = timer.stop()
        msg = "Saved data in file: %s. Bytes received: %d. Time: %.3f s. " +\
              "Rate: %.2f Bytes/s"
        info(2,msg % (trgFilename, int(reqPropsObj.getBytesReceived()),
                      deltaTime, (float(reqPropsObj.getBytesReceived()) /
                                  deltaTime)))

        # Raise exception if less byes were received as expected.
        if (remSize != 0):
            msg = genLog("NGAMS_ER_ARCH_RECV",
                         [fileUri, reqPropsObj.getSize(),
                          (reqPropsObj.getSize() - remSize)])
            raise FailedDownloadException(msg)
        
        # now check the CRC value against what we expected
        sourceChecksum = reqPropsObj.getChecksum()
        info(3, 'source checksum: ' + str(sourceChecksum) + " - current checksum: " + str(crc))
        if (crc != int(sourceChecksum)):
            msg = "checksum mismatch: source=" + str(sourceChecksum) + ", received: " + str(crc)
            raise FailedDownloadException(msg)

        return [deltaTime,crc]
    finally:
        info(4, 'closing read file descriptor (http socket)')
        readFd.close()
        info(4, 'closing file output descriptor')
        fdOut.close()
        info(4, 'releasing disk resources')

        
def serverSupportsResume(fd):
    ranges = ""
    try:
        ranges = fd.headers.getfirstmatchingheader("Accept-Ranges")
    except KeyError:
        pass
    return ("bytes" in str(ranges)) 

# EOF

