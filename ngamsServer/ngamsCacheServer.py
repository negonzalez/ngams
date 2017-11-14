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
# "@(#) $Id: ngamsCacheServer.py,v 1.1 2008/08/24 15:32:03 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  14/05/2008  Created
#

"""
This module facilitates running the NG/AMS Server in 'caching mode'.
"""

import sys

from   ngams import *
import ngamsServer


if __name__ == '__main__':
    """
    Main function instatiating the NG/AMS Server Class and starting the server.
    """
    T = TRACE()

    ngamsSrv = ngamsServer.ngamsServer()
    ngamsSrv._cacheArchive = True
    ngamsSrv._serverName   = "ngamsCacheServer"
    ngamsSrv.init(sys.argv)


# EOF
