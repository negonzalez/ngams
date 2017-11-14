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
# "@(#) $Id: ngamsCmd_COMPRESSLOG.py,v 1.1 2010/07/05 15:49:39 mbauhofe Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# mbauhofe  01/07/2010  Created
#

from pprint import pformat
from tempfile import TemporaryFile

from ngams import info
from ngamsPlugInApi import getFileSize, execCmd
from ngamsGenCrc32 import ngamsGenCrc32
from ngamsFileInfo import ngamsFileInfo

_getNgasFilesCols = None
_file_buffer_size = 4048
_compress_command = 'gzip -4'
_compress_ext = 'gz'
_compress_mime_type = 'application/x-gzip'


def backupfile(fileName, tempFile):
    file = open(fileName, 'rb')
    try:
        buffer = True
        while buffer:
            buffer = file.read(_file_buffer_size)
            if buffer:
                tempFile.write(buffer)
                if len(buffer) < _file_buffer_size:
                    buffer = False
    finally:
        if file:
            file.close()

def compressFile(fileName):
    #tempFile = TemporaryFile('w+b')
    #backupfile(fileName, tempFile)
    exitCode, cmdOutput = execCmd('%s %s' % (_compress_command, fileName))
    if exitCode == 0:
        if _compress_ext:
            fileName += '.' + _compress_ext
        archFileSize = getFileSize(fileName)
        checksum = ngamsGenCrc32(None, fileName)
        return (fileName, archFileSize, checksum)
    raise Exception('Could not compress %s.\n%s' % (fileName, cmdOutput.read()))

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle Command COMPRESSLOG to compress existing log files.
        
    srvObj:         Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).
        
    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).
        
    Returns:        Void.
    """
    # Get log file list, which have not been compressed, yet.
    #srvObj.getDb().
    db = srvObj.getDb()
    ngasFilesMap = db.getNgasFilesMap()
    hostId = srvObj.getHostInfoObj().getHostId()
    files = {}
    disks = {}
    for disk in db.getDiskIdsMtPtsMountedDisks(hostId):
        diskId = disk[0]
        disks[diskId] = disk[1]
        for fileRow in db.getFileInfoList(diskId, '*', -1).fetch(-1):
            fileId = fileRow[ngasFilesMap['file_id']]
            file = files.get(fileId, None)
            if not file:
                file = files[fileId] = []
            file.append(fileRow)
            
    # Only use the latest version of a file.
    fileVersionColIdx = ngasFilesMap['file_version']
    for file in files.values():
        file.sort(cmp=lambda x,y:
                      (x[fileVersionColIdx] < y[fileVersionColIdx] and 
                       -11 or 
                       (x[fileVersionColIdx] > y[fileVersionColIdx] and 
                        1 or 
                        0)))
    fileList = [f[-1] for f in files.values() 
                if f[-1][ngasFilesMap['format']] == 
                   'application/octet-stream' and
                   f[-1][ngasFilesMap['file_name']].
                   split('/')[-1].startswith('logOutput') and
                   (not f[-1][ngasFilesMap['compression']] or
                    f[-1][ngasFilesMap['compression']] == 'NONE')]
    #info(3, pformat(fileList))
    for f in fileList:
        fileName = '%s/%s' % (disks[f[ngasFilesMap['disk_id']]], 
                              f[ngasFilesMap['file_name']])
        info(3, 'Processing %s...' % fileName)
        #info(3, f[ngasFilesMap['format']])
        #info(3, str(getFileSize(fileName)))
        fileName, archFileSize, checksum = compressFile(fileName)
        
        fileInfo = ngamsFileInfo().read(
            db, f[ngasFilesMap['file_id']], f[ngasFilesMap['file_version']], 
            f[ngasFilesMap['disk_id']])
        fileInfo.setCompression(_compress_command)
        fileInfo.setFormat(_compress_mime_type)
        fileInfo.setChecksum(checksum)
        fileInfo.setChecksumPlugIn('ngamsGenCrc32')
        fileInfo.setUncompressedFileSize(fileInfo.getFileSize())
        fileInfo.setFileSize(archFileSize)
        fileInfo.setFilename(fileName)
        fileInfo.write(db, updateDiskInfo=1)
        info(3, '[DONE] Processing %s' % fileName)
        
    return
