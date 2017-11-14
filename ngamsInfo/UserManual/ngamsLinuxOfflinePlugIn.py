#*******************************************************************************
# ALMA - Atacama Large Millimeter Array
# Copyright (c) ESO - European Southern Observatory, 2011
# (in the framework of the ALMA collaboration).
# All rights reserved.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#*******************************************************************************
#******************************************************************************
# ESO/DMD
#
# "@(#) $Id: ngamsLinuxOfflinePlugIn.py,v 1.2 2011/11/24 13:06:42 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/05/2001  Created.
#

"""
Module that contains a System Offline Plug-In used by the ESO NGAS
installations.
"""

from   ngams import *
import ngamsPlugInApi
import ngamsLinuxSystemPlugInApi, ngamsEscaladeUtils


def ngamsLinuxOfflinePlugIn(srvObj,
                            reqPropsObj = None):
    """
    Function unmounts all NGAMS disks and removes the kernel module for
    the IDE controller card.

    srvObj:        Reference to instance of the NG/AMS Server class
                   (ngamsServer).

    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).

    Returns:       Void.
    """
    rootMtPr = srvObj.getCfg().getMountRootDirectory()    
    parDicOnline = ngamsPlugInApi.\
                   parseRawPlugInPars(srvObj.getCfg().getOnlinePlugInPars())

    # Old format = unfortunately some Disk IDs of WDC/Maxtor were
    # generated wrongly due to a mistake by IBM, which lead to a wrong
    # implementation of the generation of the Disk ID.
    if (not parDicOnline.has_key("old_format")):
        raise Exception, "Missing Online Plug-In Parameter: old_format=0|1"
    else:
        oldFormat = int(parDicOnline["old_format"])

    # The controllers Plug-In Parameter, specifies the number of controller
    # in the system.
    if (not parDicOnline.has_key("controllers")):
        controllers = None
    else:
        controllers = parDicOnline["controllers"]

    # Select between 3ware WEB Interface and 3ware Command Line Tool.
    if (parDicOnline["uri"].find("http") != -1):
        diskDic = ngamsEscaladeUtils.\
                  parseHtmlInfo(parDicOnline["uri"], rootMtPr)
    else:
        diskDic = ngamsEscaladeUtils.parseCmdLineInfo(rootMtPr, controllers,
                                                      oldFormat)
        
    parDicOffline = ngamsPlugInApi.\
                    parseRawPlugInPars(srvObj.getCfg().getOfflinePlugInPars())
    
    # This is only unmounting the NGAMS disks and may lead to problems
    # if someone mounts other disks off-line.
    if (parDicOffline.has_key("unmount")):
        unmount = int(parDicOffline["unmount"])
    else:
        unmount = 1
    if (unmount):
        ngamsLinuxSystemPlugInApi.ngamsUmount(diskDic,
                                              srvObj.getCfg().getSlotIds())
        stat = ngamsLinuxSystemPlugInApi.rmMod(parDicOnline["module"])
        if (stat):
            errMsg = "Problem executing ngamsLinuxOfflinePlugIn! " +\
                     "The system is in not in a safe state!"
            errMsg = genLog("NGAMS_ER_OFFLINE_PLUGIN", [errMsg])
            error(errMsg)
            raise Exception, errMsg
        msg = "Kernel module " + parDicOnline["module"] + " unloaded"
        info(1,msg)


if __name__ == '__main__':
    """
    Main function.
    """
    import sys
    import ngamsConfig, ngamsDb

    setLogCond(0, "", 0, "", 1)

    if (len(sys.argv) != 2):
        print "\nCorrect usage is:\n"
        print "% python ngamsLinuxOfflinePlugIn <NGAMS cfg>\n"
        sys.exit(0)    
    
    ngamsCfgObj = ngamsConfig.ngamsConfig()
    ngamsCfgObj.load(sys.argv[1])
    dbConObj = ngamsDb.ngamsDb(ngamsCfgObj.getDbServer(),
                               ngamsCfgObj.getDbName(),
                               ngamsCfgObj.getDbUser(),
                               ngamsCfgObj.getDbPassword())
    dbConObj.query("use " + ngamsCfgObj.getDbName())
    ngamsLinuxOfflinePlugIn(dbConObj, ngamsCfgObj)


# EOF
