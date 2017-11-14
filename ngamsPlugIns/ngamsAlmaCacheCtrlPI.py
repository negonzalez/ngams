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
# "@(#) $Id: ngamsAlmaCacheCtrlPI.py,v 1.8 2012/03/03 21:06:15 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  24/07/2008  Created
#

"""
This is an example Cache Control Plug-In, which can be used as template
when implementing this type of plug-in.

It simply deletes files from the cache after a given expiration time.
"""

import os, string
from time import *
import PccUtTime
from   ngams import *
import ngamsPlugInApi, ngamsDiskUtils, ngamsDiskInfo


def ngamsAlmaCacheCtrlPI(srvObj,cacheEntryObj):
    """
    srvObj:         Reference to NG/AMS Server Object (ngamsServer).

    cacheEntryObj:  Cache Entry Object containing the information for the
                    cached file (ngamsCacheEntry).

    Returns:        Returns True if the file can be deleted from the cache,
                    otherwise False (boolean). 
    """
    T = TRACE()

    file_id = str(cacheEntryObj.getFileId())
    file_version = str(cacheEntryObj.getFileVersion())
    format = str(cacheEntryObj.getFormat())

    # First find configuration to apply depending on the format
    formats_list = srvObj.getCfg().getVal("Caching[1].Formats")
    formats_list = formats_list.split(";")
    format_parameters = "Caching[1].FormatParsDefault"
    format_index = 1
    for ith_format in formats_list:
        if (format == ith_format):
            format_parameters = "Caching[1].FormatPars" + str(format_index)
            break
        else:
            format_index += 1
    info(3, "format parameters: " + str(format_parameters))
    
    # Get plug-in parameters diccionary
    plugInPars = srvObj.getCfg().getVal(format_parameters)
    plugInParDic = ngamsPlugInApi.parseRawPlugInPars(plugInPars)
    # Get data base links list
    db_links_list = plugInParDic["db_links_list"]
    db_links_list = db_links_list.split(";")
    # Get cluster names list
    cluster_names_list = plugInParDic["cluster_names_list"]
    cluster_names_list = cluster_names_list.split(";")
    # Get minimum number of copies
    min_copies = int(plugInParDic["min_copies"])
    # Get minimum caching time
    min_cache_time = int(plugInParDic["min_cache_time"])
    # Log info
    info(3, "Plug-In Parameters (applying %s format settings): db_links_list=%s cluster_names_list=%s min_copies=%s min_cache_time=%s" % \
             (str(format_parameters),str(db_links_list),str(cluster_names_list),str(min_copies),str(min_cache_time)))
       
    # Compute total number of copies among cluster list
    n_clusters = len(db_links_list)
    clusters_iterator = range(n_clusters)
    n_copies = 0
    for ith_cluster in clusters_iterator:
        db_link = db_links_list[ith_cluster].strip()
        cluster_name = cluster_names_list[ith_cluster].strip()
        query = "select count(*) from ngas_files@" + db_link + " nf ,ngas_disks@"  + db_link + " nd ,ngas_hosts@" + db_link + " nh "
        query += "where nf.disk_id = nd.disk_id and nd.host_id = nh.host_id and nh.cluster_name='" + cluster_name + "' "
        query += "and file_id='" + file_id + "' and file_version='" + file_version + "' "
        try:
            info(3, "Executing SQL query: %s" % query)
            result = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
            result = result[0][0][0]
            info(3, "SQL query result: %s" % str(result))
            n_copies += int(result)
        except:
            notice("Problem accessing db-link: %s, sleeping for 10 minutes (query was: %s)" % (db_link,query))
            sleep(600)


    # Compute caching time
    cache_time = cacheEntryObj.getCacheTime()
    delta_time = time.time() - cache_time

    # Mark file for deletion if conditions are matched
    if ((n_copies >= min_copies) and (delta_time >= min_cache_time)):
        info(3, "file_id: %s file_version: %s format: %s ncopies: %s cache_time: %s (Marked for deletion)" % \
                (file_id,file_version,format,str(n_copies),str(cache_time)))
        return 1
    else:
        info(3, "file_id: %s file_version: %s format: %s n_copies: %s cache_time: %s (Omitted for deletion)" % \
                (file_id,file_version,format,str(n_copies),str(cache_time)))
        return 0

# EOF
