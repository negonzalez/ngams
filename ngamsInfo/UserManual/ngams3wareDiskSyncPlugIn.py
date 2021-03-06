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
# "@(#) $Id: ngams3wareDiskSyncPlugIn.py,v 1.2 2011/11/24 13:06:42 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/05/2001  Created.
#

"""
Module that contains a Disk Dync Plug-In for the 3ware Controller.
"""

from   ngams import *
import ngamsPlugInApi


def ngams3wareDiskSyncPlugIn(srvObj):
    """
    Disk Sync Plug-In to flush the cache of the 3ware controller.

    srvObj:        Reference to instance of NG/AMS Server class (ngamsServer).

    Returns:       Void.
    """
    info(4,"Entering ngams3wareDiskSyncPlugIn() ...")

    # Sync filesystem to ensure file received on disk.
    # IMPL: Set log levels to 4 when 'sync problem' has been solved.
    info(3,"Performing OS sync command ...")
    commands.getstatusoutput("sync")
    info(3,"Performed OS sync command")
    logFlush()   # IMPL: Remove this line when 'sync problem' solved.

    info(4,"Leaving ngams3wareDiskSyncPlugIn()")


if __name__ == '__main__':
    """
    Main function.
    """
    pass


# EOF
