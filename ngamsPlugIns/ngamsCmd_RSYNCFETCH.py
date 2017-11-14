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
# "@(#) $Id: ngamsCmd_RSYNCFETCH.py,v 1.1 2012/11/22 21:48:22 amanning Exp $"
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
from ngams import TRACE, info, error, warning, checkCreatePath, getHostName
from ngamsFailedDownloadException import FailedDownloadException, PostponeException
from ngams.ngamsLib import ngamsHighLevelLib, ngamsLib
from pcc.pccUt import PccUtTime
import binascii
import socket

def calculateCrc(filename, blockSize):
    crc = 0
    fdin= None
    try:
        fdin = open(filename, "r")
        buff = "-"
        while len(buff) > 0:
            buff = fdin.read(blockSize)
            crc = binascii.crc32(buff, crc)
    except Exception, e:
        # so we can't compute the CRC. So what. The computed CRC will not match the expected
        warning(str(e))
    finally:
        if fdin is not None: fdin.close()
    return crc

def get_full_qualified_name(srvObj):
    """
    Get full qualified server name for the input NGAS server object
    
    INPUT:
        srvObj  ngamsServer, Reference to NG/AMS server class object 
    
    RETURNS:
        fqdn    string, full qualified host name (host name + domain + port)
    """

    # Get hots_id, domain and port using ngamsLib functions
    hostName = getHostName()
    domain = ngamsLib.getDomain()
    # Concatenate all elements to construct full qualified name
    # Notice that host_id may contain port number
    fqdn = hostName + "." + domain

    # Return full qualified server name
    return fqdn

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
    
    source_host = reqPropsObj.getFileInfo()['sourceHost']
    file_version = reqPropsObj.getFileInfo()['fileVersion']
    file_id = reqPropsObj.getFileInfo()['fileId']

    info(4,"Creating path: " + trgFilename + " ...")
    checkCreatePath(os.path.dirname(trgFilename))
    timer = PccUtTime.Timer()
    fetchCommand = "http://" + source_host + "/RSYNC?file_version=" + file_version 
    fetchCommand += "&targetHost=" + get_full_qualified_name(srvObj)
    fetchCommand += "&targetLocation=" + trgFilename
    # the file_id MUST be last due to restrictions in the ngamsDAPIMirroring class. :(
    fetchCommand += "&file_id=" + file_id
    fileUri = fetchCommand
    reqPropsObj.setFileUri(fileUri)
    info(1, "fileUri: " + fileUri)

    originalTimeout = socket.getdefaulttimeout()
    readFd = None
    try:
        rx_timeout = 30 * 60
        if srvObj.getCfg().getVal("Mirroring[1].rx_timeout"):
            rx_timeout = int(srvObj.getCfg().getVal("Mirroring[1].rx_timeout"))
        info(1, 'setting the socket timeout to %s seconds' % str(rx_timeout))
        socket.setdefaulttimeout(rx_timeout)
        info(1, 'opening the socket')
        readFd = ngamsHighLevelLib.openCheckUri(fileUri, startByte)
        response = getResponse(readFd, blockSize)
        if "FAILURE" in response: raise Exception(response)
    finally:
        info(1, 'closing the socket')
        socket.setdefaulttimeout(originalTimeout)
        if readFd is not None: readFd.close()
        info(1, 'closed the socket')
    
    deltaTime = timer.stop()
    msg = "Saved data in file: %s. Bytes received: %d. Time: %.3f s. " +\
          "Rate: %.2f Bytes/s"
    info(2,msg % (trgFilename, int(reqPropsObj.getBytesReceived()),
                  deltaTime, (float(reqPropsObj.getBytesReceived()) /
                              deltaTime)))

    # now check the CRC value against what we expected
    sourceChecksum = reqPropsObj.getChecksum()
    timer2 = PccUtTime.Timer()
    crc = calculateCrc(trgFilename, blockSize)
    deltaTime2 = timer2.stop()
    info(3, "crc computed in %s s" % str(deltaTime2))
    info(3, 'source checksum: ' + str(sourceChecksum) + " - current checksum: " + str(crc))
    if (crc != int(sourceChecksum)):
        msg = "checksum mismatch: source=" + str(sourceChecksum) + ", received: " + str(crc)
        raise FailedDownloadException(msg)

    return [deltaTime, crc]

def getResponse(readFd, blockSize):
    response = ""
    while True:
        buf = readFd.read(blockSize)
        sizeRead = len(buf)
        info(1, 'read: ' + str(buf))
        if sizeRead == 0: break
        response += buf
    return response

# EOF