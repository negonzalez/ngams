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
# "@(#) $Id: ngamsLinuxOnlinePlugIn.py,v 1.2 2011/11/24 13:06:42 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/05/2001  Created.
#

"""
Module that contains a System Online Plug-In used by the ESO NGAS
installations.
"""

from   ngams import *
import ngamsPlugInApi
import ngamsLinuxSystemPlugInApi, ngamsEscaladeUtils


def ngamsLinuxOnlinePlugIn(srvObj,
                           reqPropsObj = None):
    """
    Function mounts all NGAMS disks and loads the kernel module for the IDE
    controller card. It returns the NGAMS specific disk info dictionary.

    srvObj:        Reference to instance of the NG/AMS Server
                   class (ngamsServer).

    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).

    Returns:       Disk info dictionary (dictionary).
    """
    info(4,"Entering ngamsLinuxOnlinePlugIn() ...")
    rootMtPr = srvObj.getCfg().getMountRootDirectory()
    parDic = ngamsPlugInApi.\
             parseRawPlugInPars(srvObj.getCfg().getOnlinePlugInPars())
    stat = ngamsLinuxSystemPlugInApi.insMod(parDic["module"])
    if (stat == 0):
        msg = "Kernel module " + parDic["module"] + " loaded"
        info(1, msg)

        # Old format = unfortunately some Disk IDs of WDC/Maxtor were
        # generated wrongly due to a mistake by IBM, which lead to a wrong
        # implementation of the generation of the Disk ID.
        if (not parDic.has_key("old_format")):
            raise Exception, "Missing Online Plug-In Parameter: old_format=0|1"
        else:
            oldFormat = int(parDic["old_format"])

        # The controllers Plug-In Parameter, specifies the number of controller
        # in the system.
        if (not parDic.has_key("controllers")):
            controllers = None
        else:
            controllers = parDic["controllers"]

        # Get start index for the 3ware disk devices.
        if (not parDic.has_key("dev_start_idx")):
            devStartIdx = "a"
        else:
            devStartIdx = parDic["dev_start_idx"]
            
        # Select between 3ware WEB Interface and 3ware Command Line Tool.
        if (parDic["uri"].find("http") != -1):       
            diskDic = ngamsEscaladeUtils.parseHtmlInfo(parDic["uri"], rootMtPr)
        else:
            diskDic = ngamsEscaladeUtils.\
                      parseCmdLineInfo(rootMtPr,
                                       controllers,
                                       oldFormat,
                                       slotIds = ["*"],
                                       buf = "",
                                       devStartIdx = devStartIdx)

        ngamsLinuxSystemPlugInApi.removeFstabEntries(diskDic)
        ngamsLinuxSystemPlugInApi.ngamsMount(srvObj, diskDic,
                                             srvObj.getCfg().getSlotIds())
        info(4,"Leaving ngamsLinuxOnlinePlugIn()")
        return diskDic
    else:
        errMsg = "Problem executing ngamsLinuxOnlinePlugIn"
        errMsg = genLog("NGAMS_ER_ONLINE_PLUGIN", [errMsg])
        error(errMsg)
        raise Exception, errMsg


if __name__ == '__main__':
    """
    Main function.
    """
    import sys
    import ngamsConfig, ngamsDb

    setLogCond(0, "", 0, "", 1)
    
    if (len(sys.argv) != 2):
        print "\nCorrect usage is:\n"
        print "% python ngamsLinuxOnlinePlugIn <NGAMS cfg>\n"
        sys.exit(0)
        
    ngamsCfgObj = ngamsConfig.ngamsConfig()
    ngamsCfgObj.load(sys.argv[1])
    dbConObj = ngamsDb.ngamsDb(ngamsCfgObj.getDbServer(),
                               ngamsCfgObj.getDbName(),
                               ngamsCfgObj.getDbUser(),
                               ngamsCfgObj.getDbPassword())
    dbConObj.query("use " + ngamsCfgObj.getDbName())
    diskDic = ngamsLinuxOnlinePlugIn(dbConObj, ngamsCfgObj)
    print "Disk Dictionary = ", str(diskDic)


# EOF
