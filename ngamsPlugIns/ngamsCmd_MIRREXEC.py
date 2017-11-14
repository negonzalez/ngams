#
#    ALMA - Atacama Large Millimiter Array
#    (c) European Southern Observatory, 2009
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
# "@(#) $Id: ngamsCmd_MIRREXEC.py,v 1.29 2012/11/22 21:48:22 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jagonzal  2009/12/15  Created
#

"""
NGAS Command Plug-In, implementing a command to actually perform mirroring tasks

NOTES:
    By default it performs pending mirroring tasks assigned to the NGAS server
    handling the command, but when mirror_cluster is specified (=1), default (=0),
    all pending mirroring tasks assigned to the local cluster are processed.

PARAMETERS:
    -mirror_cluster [optional]    (=0), process all pending mirroring tasks assigned to the NGAS server handling the command
                    (=1), process all pending mirroring tasks assigned to the local cluster
                          (distributing the process to the active nodes in the local cluster

EXAMPLES:
    - Carry out pending mirroring tasks for this NGAS server using 4 threads per source node
    http://ngas05.hq.eso.org:7778/MIRREXEC?n_threads=4
    - Carry out all pending mirroring tasks assigned to the local cluster using 2 threads per source node
    http://ngas05.hq.eso.org:7778/MIRREXEC?mirror_cluster=1&n_threads=2
    
"""

from ngams import error, TRACE, info, warning, getHostId, alert, genUniqueId, NGAMS_STAGING_DIR
from ngams.ngamsLib import ngamsDb, ngamsDbCore, ngamsDiskInfo, ngamsLib
import os
import socket
import httplib
from time import time, sleep, strftime, gmtime
from threading import Thread
import ngamsCmd_MIRRARCHIVE
from ngamsFailedDownloadException import *
from ngams.ngamsLib import ngamsReqProps
from collections import deque

GET_AVAIL_VOLS_QUERY = "SELECT %s FROM ngas_disks nd WHERE completed=0 AND " +\
                       "host_id='%s' order by available_mb desc"


def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle Command MIRRTABLE to populate bookkeeping table in target cluster
    
    INPUT:
        srvObj:         ngamsServer, Reference to NG/AMS server class object
    
        reqPropsObj:    ngamsReqProps, Request Property object to keep track
                        of actions done during the request handling 
        
       httpRef:        ngamsHttpRequestHandler, Reference to the HTTP request
                        handler object
        
    RETURNS:        Void.
    """
    TRACE()

    # Get command parameters.
    mirror_cluster = 0
    n_threads = 2
    rx_timeout = None
    if (reqPropsObj.hasHttpPar("mirror_cluster")):
        mirror_cluster = int(reqPropsObj.getHttpPar("mirror_cluster")) 
    if (reqPropsObj.hasHttpPar("n_threads")):
        n_threads = int(reqPropsObj.getHttpPar("n_threads"))
    if (reqPropsObj.hasHttpPar("rx_timeout")):
        rx_timeout = int(reqPropsObj.getHttpPar("rx_timeout"))
    current_iteration = int(reqPropsObj.getHttpPar("iteration"))

    # Distributed cluster mirroring
    if (mirror_cluster):
        # Get cluster name
        local_cluster_name = get_cluster_name(srvObj)
        # Get active target nodes
        active_target_nodes = get_active_target_nodes(local_cluster_name, current_iteration, srvObj)
        # Start mirroring
        distributed_mirroring(active_target_nodes,n_threads, rx_timeout, current_iteration)
    else:
        # Get full qualified name of this server
        local_server_full_qualified_name = get_full_qualified_name(srvObj)
        # Format full qualified name as a list
        active_target_nodes = [local_server_full_qualified_name]
        # Get active source nodes
        active_source_nodes = get_active_source_nodes(srvObj,current_iteration, full_qualified_name=local_server_full_qualified_name)
        # Start mirroring process driven by this host
        info(3,"Performing mirroring tasks from (%s) to (%s) using %s threads per source node and target node" \
        % (str(active_source_nodes),str(active_target_nodes),str(n_threads)))
        try:
            # Set mirroring running flag to avoid data check thread and janitor thread
            srvObj.setMirroringRunning(1)
            multithreading_mirroring(active_source_nodes, n_threads, rx_timeout, current_iteration, srvObj)
        finally:
            # Set mirroring running flag to trigger data check thread and janitor thread
            srvObj.setMirroringRunning(0)

    # Return Void 
    return


def get_cluster_name(srvObj):
    """
    Get cluster name corresponding to the processing NGAMS server
    
    INPUT:
        srvObj          ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
        cluster_name    string, name of the cluster corresponding to the input host_id
    """
    # Construct query
    query = "select cluster_name from ngas_hosts where host_id='" + getHostId() + "'"

    # Execute query
    info(4, "Executing SQL query to get local cluster name: %s" % query)
    cluster_name = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    cluster_name = str(cluster_name[0][0][0])
    info(3, "Local cluster name: %s" % cluster_name)

    # Return cluster_name
    return cluster_name


def get_full_qualified_name(srvObj):
    """
    Get full qualified server name for the input NGAS server object
    
    INPUT:
        srvObj  ngamsServer, Reference to NG/AMS server class object 
    
    RETURNS:
        fqdn    string, full qualified host name (host name + domain + port)
    """

    # Get hots_id, domain and port using ngamsLib functions
    host_id = getHostId()
    domain = ngamsLib.getDomain()
    port = str(srvObj.getCfg().getPortNo())
    # Concatenate all elements to construct full qualified name
    # Notice that host_id may contain port number
    fqdn = (host_id.rsplit(":"))[0] + "." + domain + ":" + port

    # Return full qualified server name
    return fqdn


def get_active_source_nodes(srvObj, current_iteration, cluster_name="none", full_qualified_name="none"):
    """
    Get active source nodes containing files to mirror
    for input cluster name or full qualified server name

    INPUT:
    cluster_name        string, Name of the cluster to process mirroring tasks
        full_qualified_name    string, Full qualified name of ngams server to process mirroring tasks
    srvObj              ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
    active_source_nodes    list[string], List of active source nodes with files to mirror
    """

    # Construct query
    if (full_qualified_name == "none"):
        query = "select source_host from ngas_mirroring_bookkeeping where status='READY' and target_cluster='" + cluster_name +"' and iteration = :iteration group by source_host"
        info(3, "Executing SQL query to get active nodes with files to mirror for cluster %s: %s" % (cluster_name, query))
    else:
        query = "select source_host from ngas_mirroring_bookkeeping where status='READY' and target_host='" + full_qualified_name +"' and iteration = :iteration group by source_host"
        info(3, "Executing SQL query to get active nodes with files to mirror for local server %s: %s" % (full_qualified_name, query))

    # Execute query
    source_nodes = srvObj.getDb().query(query, parameters = {"iteration": str(current_iteration)}, maxRetries=1, retryWait=0)

    # Re-dimension query results array and check status
    source_nodes = source_nodes[0]
    active_source_nodes = []
    for node in source_nodes:
        if ngams_server_status(node[0]): active_source_nodes.append(node[0]) 
        else: info(2, "Source node " + node[0] + " is not ONLINE. Not considering for this mirroring iteration")
    
    # Return result
    return active_source_nodes
    
    
def get_active_target_nodes(cluster_name, current_iteration, srvObj):
    """
    Get active target nodes ready to process mirroring tasks

    INPUT:
        cluster_name        string, Name of the cluster to process mirroring tasks
    srvObj              ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
        active_target_nodes    list[string], List of active target nodes with files to mirror
    """

    # Construct query
    query = "select target_host from ngas_mirroring_bookkeeping where status='READY' and target_cluster='" + cluster_name + "' and iteration = :iteration group by target_host"
    info(3, "Executing SQL query to get active nodes with files to mirror for cluster %s: %s" % (cluster_name,query))

    # Execute query
    target_nodes = srvObj.getDb().query(query, parameters = {"iteration": str(current_iteration)}, maxRetries=1, retryWait=0)

    # Re-dimension query results array and check status
    target_nodes = target_nodes[0]
    active_target_nodes = []
    for node in target_nodes:
        if ngams_server_status(node[0]): active_target_nodes.append(node[0]) 
        else: removeTasks(node[0], cluster_name, srvObj)

    # Log info
    info(3, "Active nodes found in cluster %s: %s" % (cluster_name,str(active_target_nodes)))

    # Return result
    return active_target_nodes


def ngams_server_status(ngams_server):
    """
    Check NGAMS server status

    INPUT:
        ngams_server    string, Full qualified name of ngams_server
    
    RETURNS:
    status         bool, True if active False if unactive
    """

    try:
        server_conn = httplib.HTTPConnection(ngams_server)
        server_conn.request("GET","/STATUS?")
        status = server_conn.getresponse().read().find("ONLINE") >= 0
    except:
        info(3, "Problem trying to reach %s, setting status to OFFLINE (0)" % ngams_server )
        status = 0
    finally:
        server_conn.close()
        
    return status

def removeTasks(ngamsServer, clusterName, srvObj):
    warning(str(ngamsServer) + " has gone OFFLINE. Marking all it's pending fetches as ABORTED so that other nodes can take over.")
    sql = "update ngas_mirroring_bookkeeping"
    sql += " set status = 'ABORTED'"
    sql += " where status in ('READY', 'FETCHING', 'TORESUME')"
    sql += " and target_host = '" + ngamsServer + "' and target_cluster = '" + clusterName + "'"  
    srvObj.getDb().query(sql)
    
def get_list_mirroring_tasks(currentIteration, source_node,target_node,srvObj):
    """
    Check pending mirroring tasks in the ngas_bookkeeping
    table assigned to the input host name

    INPUT:
        source_node     string, Node source of the files to be mirrored
        target_node     string, Node target of the files to be mirrored 
        srvObj          ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
        mirroring_tasks list[string], List of files to be mirrored from the source_node to the target_node
    """

    # pull out the fields from the mirroring bookkeeping table that we may need in order to fetch files.
    # the individual fields are passed around and eventually formed into a command in process_mirroring_tasks
    query = "select file_size, staging_file, rowid, "
    query += "format, checksum, source_host, disk_id, "
    query += "host_id, file_version, file_id"
    query += " from ngas_mirroring_bookkeeping"
    query += " where source_host=:sourceNode and target_host=:targetNode"
    query += " and iteration = :iteration and status='READY'"
    query += " order by file_size"

    # Execute query to get mirroring tasks list
    info(3, "Executing SQL query to get list of mirroring tasks from (%s) to (%s): %s" % (source_node,target_node,query))
    parameters = {"iteration": str(currentIteration), "sourceNode": source_node, "targetNode": target_node}
    mirroring_tasks_list = srvObj.getDb().query(query, parameters = parameters, maxRetries=1, retryWait=0)
    mirroring_tasks_list = mirroring_tasks_list[0]
   
    # Return mirroring tasks list
    return mirroring_tasks_list

def reorder_list_of_mirroring_tasks_for_target(currentIteration, source_nodes_list,target_node,mirroring_tasks_list,srvObj):

    # Construct query to get average file size and number of tasks
    parameters = [target_node]
    query = "select count(*), sum(file_size/(1024*1024))/count(*) from ngas_mirroring_bookkeeping where target_host = :1"
    position = 2
    query += " and (1 = 0"
    if source_nodes_list:
        for node in source_nodes_list:
            query += " or source_host = :" + str(position)
            position += 1
            parameters.append(node)
    query += ")"
    query += " and status='READY' and iteration = :" + str(position)
    parameters.append(currentIteration)

    # Execute query to get average file size and number of tasks
    info(3, "Executing SQL query to get average file size and number of mirroring tasks to (%s): %s" % (target_node,query))
    result = srvObj.getDb().query(query, parameters = parameters, maxRetries=1, retryWait=0)
    total_tasks = int(result[0][0][0])
    target_avg_file_size = 0
    # if we divide by zero in the oracle query then we get an empty result back for average file size
    if (total_tasks > 0): 
        target_avg_file_size = float(result[0][0][1])
    info(3, "Average file size and number of mirroring tasks to (%s): nTasks=%s Avg[MB]=%s" % (target_node,str(total_tasks),str(target_avg_file_size)))

    n_sources = len(source_nodes_list)
    sources_iterator = range(n_sources)
    ascending_index = range(n_sources)
    descending_index = range(n_sources)
    source_total_tasks = range(n_sources)
    source_processed_tasks = range(n_sources)
    reordered_mirroring_tasks_list = deque()
    next_source_ascending_index = 0
    next_source_descending_index = 0

    for ith_source in sources_iterator:
        ascending_index[ith_source] = 0
        descending_index[ith_source] = -1
        source_total_tasks[ith_source] = len(mirroring_tasks_list[ith_source])
        source_processed_tasks[ith_source] = 0

    avg_file_size = 0
    processed_tasks = 0
    processed_size = 0

    info(3,"Start reordering mirroring tasks for %s" % (target_node))

    # process files one after the other
    #     if (
    iteration = 0
    # this a complex algorithm and I've seen it hang on occasion. This is to prevent an infinite loop occurring.
    # There are too many variables for me to reason about this and too little time. We will deploy and watch out
    # for iterations where not all files are mirrored.
    # the 2M iterations count has the side effect that only 1M files will be processed in a single
    # iteration
    emergency_breakpoint = 2000000
    while (processed_tasks < total_tasks):
        info(4, "outer loop iteration: " + str(iteration))
        iteration += 1
        if (iteration > emergency_breakpoint):
            alert("re-ordering is not exiting - performing an emergency exit")
            break
           
        # Add big file if the current avg is below the total avg
        info(4, "average: " + str(avg_file_size) + " / " + str(target_avg_file_size))
        next_source = 0
        task_index = None
        smallFile = (avg_file_size < target_avg_file_size)
        if (smallFile):
            next_source = next_source_descending_index
            next_source_descending_index = (next_source_descending_index + 1) % n_sources
            task_index = descending_index[next_source]
        else:
            next_source = next_source_ascending_index
            next_source_ascending_index = (next_source_ascending_index + 1) % n_sources
            task_index = ascending_index[next_source]
            
        info(4, "    next_source: " + str(next_source))
        processed = source_processed_tasks[next_source]
        total = source_total_tasks[next_source]
        if (processed >= total):
            info(4, "all tasks for " + str(source_nodes_list[next_source]) + " have been assigned already")
        else:
            completion = calculatePercentageDone(processed, total)
            total_completion = calculatePercentageDone(processed_tasks + 1, total_tasks)
            info(4, "if completion: " + str(completion) + " > " + str(total_completion))
            # this will fail if there is a single source, or group of sources, where the completion is always 
            # greater than the total projected completion
            if (completion > total_completion):
                info(4, "    Skipping next file from source %s -> Completion :%s%% Total Completion: %s%%" % \
                        (str(next_source),str(completion),str(total_completion)))
            else:
                mirroring_task = mirroring_tasks_list[next_source][task_index]
                info(4, "    mirroring_task: " + str(mirroring_task))
                reordered_mirroring_tasks_list.append(mirroring_task)

                file_size = float(mirroring_task[0])
                processed_size += file_size
                
                source_processed_tasks[next_source] += 1
                processed_tasks += 1
                avg_file_size = processed_size / processed_tasks
                info(4, "    Appending file: tasks=%s source=%s index=%s processed=%s total=%s size=%s MB avg=%s" % \
                    (str(processed_tasks),str(next_source),str(task_index),str(processed),str(total),str(file_size),str(avg_file_size)))
                if (smallFile):
                    descending_index[next_source] -= 1
                else:
                    ascending_index[next_source] += 1                
        info(4, "    1 total:     " + str(source_total_tasks))
        info(4, "    1 processed: " + str(source_processed_tasks))
        info(4, "    1 desc:      " + str(descending_index))
        info(4, "    1 asc:       " + str(ascending_index))
               
    info(3,"Done reordering mirroring tasks for %s" % (target_node))

    # Return reordered lists
    return reordered_mirroring_tasks_list

def calculatePercentageDone(numComplete, total):
    completion = 1.0
    if (float(total) > 0.0):
        completion = float(numComplete) / float(total)
    return completion

def get_sublist_mirroring_tasks(tasks, n_threads, ith_thread, reverse_flag):
    """
    Generate a sub-list containing the ith-element of
    every n elements. Reverse the list is specified.

    INPUT:
        list            list, Original list
        n_threads    int, Number of threads
        ith_thread    int, pos-th to be selected
        reverse_flag    bool, True if the list has to be reversed

    RETURNS:
        filtered_list   list, Filtered list
    """

    # Filter list loop
    filtered_list = []
    for i, element in enumerate(tasks):
        if ((i % n_threads) == ith_thread): filtered_list.append(element)

    # Reverse if specified
    if (reverse_flag): filtered_list.reverse()

    # Return filter list
    return filtered_list


def process_mirroring_tasks(mirroring_tasks_queue,target_node,ith_thread,n_tasks,srvObj):
    """
    Process mirroring tasks described in the input mirroring_tasks list

    INPUT:
        mirroring_tasks_queue    Queue of the mirroring tasks assigned to the input server
    target_node        string, Full qualified name of the target node
    ith_thread        int, Thread number 
        n_tasks            int, Initial size of the queue
    srvObj            ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:            Void
    """
   
    info(3,"Inside mirror worker worker %s to mirror files to %s" % (str(ith_thread),target_node))
 
    try:
        # Loop on the mirroring_tasks_queue
        while 1: 
            # Get tasks from queue
            if (len(mirroring_tasks_queue)):
                try:
                    if (ith_thread % 2): item = mirroring_tasks_queue.pop()
                    else: item = mirroring_tasks_queue.popleft()
                except: break
            else: break
            # get all the fields we're interested in and form them into a command to fetch the files.
            # these fields were extracted in get_list_mirroring_tasks()
            info(3, "next task: " + str(item))
            staging_file = str(item[1])
            mimeType = str(item[3])
            checksum = str(item[4])
            rowid = str(item[2])
            file_id = str(item[9])
            fileSize = str(item[0])
            fileInfo = {}
            fileInfo['sourceHost'] = str(item[5])
            fileInfo['diskId'] = str(item[6])
            fileInfo['hostId'] = str(item[7])
            fileInfo['fileVersion'] = str(item[8])
            fileInfo['fileId'] = file_id
            
            info(2, "Processing mirroring task (Target node: %s, file size: %s, Thread: %s) file info: %s" % \
                   (target_node, fileSize, str(ith_thread), str(fileInfo)))
            # Initialize ngamsReqProps object by just specifing the fileURI and the mime type
            reqPropObj = ngamsReqProps.ngamsReqProps()
            reqPropObj.setMimeType(mimeType)
            reqPropObj.setChecksum(checksum)
            reqPropObj.setFileInfo(fileInfo)
            reqPropObj.setSize(fileSize)
            
            # Start clock
            start = time()
            (stgFilename, targetDiskInfo) = calculateStagingName(srvObj, file_id, staging_file)
            reqPropObj.setStagingFilename(stgFilename)
            reqPropObj.setTargDiskInfo(targetDiskInfo)
            try:
                # Construct query to update ingestion date, ingestion time and status
                query = "update ngas_mirroring_bookkeeping set status='FETCHING', "
                query += "staging_file = :stagingFilename, "
                query += "attempt = nvl(attempt + 1, 1) "
                query += "where rowid = :id"
                # Add query to the queue
                srvObj.getDb().query(query, parameters = {"id": rowid, "stagingFilename": reqPropObj.getStagingFilename()})

                info(2, "Mirroring file: " + file_id)
                ngamsCmd_MIRRARCHIVE.handleCmd(srvObj,reqPropObj)
                status = "SUCCESS"
            except FailedDownloadException, e:
                # Something bad happened...
                error("Failed to fetch %s. Cause: %s" % (file_id, str(e)))
                status = "FAILURE"
            except AbortedException, e:
                warning("File fetch aborted: %s" % (file_id))
                status = "ABORTED"
            except PostponeException, e:
                error("Failed to fetch %s - will try to resume on next iteration. Cause: %s" % (file_id, str(e)))
                status = "TORESUME"
            except Exception, e:
                # this clause should never be reached
                error("Fetch failed in an unexpected way: " + str(e))
                status = "FAILURE"

            # Get time elapsed
            elapsed_time = (time() - start)
            # Construct query to update ingestion date, ingestion time and status
            query = "update ngas_mirroring_bookkeeping set status = :status,"
            if (status != 'TORESUME'): query += "staging_file = null, "
            query += "ingestion_date = :ingestionDate,"
            query += "ingestion_time = nvl(ingestion_time, 0.0) + :elapsedTime "
            query += "where rowid = :id"
            srvObj.getDb().query(query, parameters = {"status": status, 
                                                      "ingestionDate": strftime("%Y-%m-%dT%H:%M:%S:000", gmtime()),
                                                      "elapsedTime": str(elapsed_time),
                                                      "id": rowid})
            # Log message for mirroring task processed
            completion = 100*(n_tasks - len(mirroring_tasks_queue))/float(n_tasks)
            info(3, "Mirroring task (Target node: %s Thread: %s) processed in %ss (%s), completion: %s%%: %s" % \
                (target_node,str(ith_thread),str(elapsed_time),status,str(completion), str(fileInfo))) 

        info(3, "Mirroring Worker complete")
    except Exception, e:
        error(str(e))
        
    # Return Void
    return

def calculateStagingName(srvObj, fileId, existingStagingFile):
    # Generate staging filename.
    stgFilename = None
    if existingStagingFile != "None":
        info(3, "An existing staging file was specified: " + existingStagingFile)
        if os.path.exists(existingStagingFile):
            info(3, "the file still exists on disk")
            stgFilename = existingStagingFile
            mountPoint = stgFilename.split(NGAMS_STAGING_DIR)[0][:-1]
            info(1, 'mount point: ' + mountPoint)
            targDiskInfo = getMountedDiskInfo(srvObj, mountPoint)
            info(1, 'disk info: ' + str(targDiskInfo))
        else:
            info(3, "the file no longer exists on disk")
    if stgFilename == None:
        baseName = os.path.basename(fileId)
        targDiskInfo = getTargetVolume(srvObj)
        stgFilename = os.path.join("/", targDiskInfo.getMountPoint(),
                               NGAMS_STAGING_DIR,
                               genUniqueId() + "___" + baseName)
    return (stgFilename, targDiskInfo)

def getTargetVolume(srvObj):
    """
    Get the volume with most space available

    srvObj:         Reference to NG/AMS server class object (ngamsServer).
        
    Returns:        Target volume object or None (ngamsDiskInfo | None).
    """

    sqlQuery = GET_AVAIL_VOLS_QUERY % (ngamsDbCore.getNgasDisksCols(),getHostId())
    res = srvObj.getDb().query(sqlQuery, ignoreEmptyRes=0)
    if (res == [[]]):
        return None
    else:
        return ngamsDiskInfo.ngamsDiskInfo().unpackSqlResult(res[0][0])

def getMountedDiskInfo(srvObj, mountPoint):

    sqlQuery = "SELECT %s FROM ngas_disks nd WHERE mount_point = '%s'" % (ngamsDbCore.getNgasDisksCols(), mountPoint)
    res = srvObj.getDb().query(sqlQuery, ignoreEmptyRes=0)
    if (res == [[]]):
        return None
    else:
        return ngamsDiskInfo.ngamsDiskInfo().unpackSqlResult(res[0][0])

def multithreading_mirroring(source_nodes_list, n_threads, rx_timeout, current_iteration, srvObj):
    """
    Creates n threads per source node and target node to process the corresponding mirroring tasks
    Each thread starts from big files or small files alternating 

    INPUT:
    source_nodes_list    list[string], List of active source nodes in the source cluster
    n_threads        int, Number of threads per source-target connection
        srvObj              ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:            Void
    """

    # Get local host name
    target_node = get_full_qualified_name(srvObj)
    
    # Get tasks from each target-source pair
    all_sources_mirroring_tasks_list = []
    # Get mirroring tasks from each source
    source_index = 0
    for source_node in source_nodes_list:
        # Get mirroring taks list for this pair target-source
        ith_source_mirroring_tasks_list = get_list_mirroring_tasks(current_iteration, source_node,target_node,srvObj)
        # Assign list to all sources mirroring tasks list
        all_sources_mirroring_tasks_list.append(ith_source_mirroring_tasks_list)
        # Increase source index counter
        source_index += 1

    # Reorder lists to mix big/small files and put in queue format
    mirroring_tasks_queue = reorder_list_of_mirroring_tasks_for_target(current_iteration, source_nodes_list, target_node,all_sources_mirroring_tasks_list,srvObj)

    # Start threads iterator
    threads_range = range(n_threads)
    threads_list = []

    # Start multi-threading mirroring
    for ith_thread in threads_range:
        info(3,"Inititalizing mirror worker %s to mirror files to %s" % (str(ith_thread+1),target_node))
        ith_mirror_worker = mirror_worker(mirroring_tasks_queue, target_node, ith_thread + 1, srvObj)
        ith_mirror_worker.start()
        threads_list.append(ith_mirror_worker)

    # Block until there are not remaining mirroring tasks in the queue
    for ith_thread_obj in threads_list: ith_thread_obj.join()

    # Return Void
    return


class mirror_worker(Thread):
    def __init__ (self,mirroring_tasks_queue,target_node,ith_thread,srvObj):
        Thread.__init__(self)
        self.mirroring_tasks_queue = mirroring_tasks_queue
        self.total_tasks = len(mirroring_tasks_queue)
        self.target_node = target_node
        self.ith_thread = ith_thread
        self.srvObj = srvObj
    def run(self):
        process_mirroring_tasks(self.mirroring_tasks_queue,self.target_node,self.ith_thread,self.total_tasks,self.srvObj)

def sort_target_nodes(target_nodes_list):
    """
    Sort target_nodes_list to balance priority
    
    INPUT:
        target_nodes_list       list[string], List of active target nodes in the target cluster
    
    RETURNS:                    list[string], Sorted active target nodes list
    """

    # Initialize machine/port dictionary
    machines_list = {}
    for target_node in target_nodes_list:
        machine = target_node.split(":")[0]
        machines_list[machine] = []

    # Fill port list in machine/port dictionary
    for target_node in target_nodes_list:
        machine = target_node.split(":")[0]
        port = target_node.split(":")[1]
        machines_list[machine].append(port)

    # Create sorted target nodes list
    found_one = True
    sorted_target_nodes_list = []
    while (found_one):
        found_one = False
        for machine in machines_list:
            if len(machines_list[machine])>0:
                sorted_target_nodes_list.append(machine+':'+machines_list[machine].pop())
                found_one = True

    # Log info
    info(3, "Target nodes order to send MIRREXEC command: %s" % (str(sorted_target_nodes_list)))    # Add higher port (machines sort-descending)
    
    # Return sorted target nodes list
    return sorted_target_nodes_list


def distributed_mirroring(target_nodes_list,n_threads, rx_timeout, iteration):
    """
    Send MIRREXEC command to each nodes in the target nodes
    list in order to have a distributed mirroring process
    
    INPUT:
        target_nodes_list    list[string], List of active target nodes in the target cluster
    n_threads        int, Number of threads per source-target connection
    
    RETURNS:                Void
    """

    # Get sorted_target_nodes_list
    sorted_target_nodes_list = sort_target_nodes(target_nodes_list)
    
    # Main loop
    threads_list = []
    for target_node in sorted_target_nodes_list:
        # Initialize mirrexec_command_sender thread object
        mirrexec_command_sender_obj = mirrexec_command_sender(target_node, n_threads, rx_timeout, iteration)
        # Add mirrexec_command_sender thread object to the list of threads
        threads_list.append(mirrexec_command_sender_obj)
        # Start mirrexec_command_sender thread object
        mirrexec_command_sender_obj.start()

    # Join mirror_node threads
    for ith_thread in threads_list:
        ith_thread.join()

    # Return Void
    return

class mirrexec_command_sender(Thread):
    def __init__ (self,target_node,n_threads, rx_timeout, iteration):
        Thread.__init__(self)
        self.target_node = target_node
        self.n_threads = n_threads
        self.rx_timeout = rx_timeout
        self.iteration = iteration
    def run(self):
        try:
            originalTimeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(None)
            self.send_mirrexec_command()
            socket.setdefaulttimeout(originalTimeout)
        except Exception, e:
            error("MIRREXEC command failed: %s" % str(e))
    def send_mirrexec_command(self):
        """
        Send MIRREXEC command to the input source_node
        
        INPUT:
            source_node    string, Target node to send MIRREXEC
            n_threads       int, Number of threads per source-target connection
            rx_timeout        int, the socket timeout time in seconds
    
        RETURNS:        Void
        """

        # Print log info
        info(3, "sending MIRREXEC command to %s with (n_threads=%s)" % (self.target_node, str(self.n_threads)))

        try:
            # Create target server connection
            self.target_node_conn = httplib.HTTPConnection(self.target_node)
            # Start clock
            start = time()
            # Send request to target node
            self.target_node_conn.request("GET","MIRREXEC?n_threads="+str(self.n_threads)+"&rx_timeout="+str(self.rx_timeout) + "&iteration=" + str(self.iteration))
            # Get response from target node
            response = self.target_node_conn.getresponse()
            # Get status
            status = "SUCCESS"
            if (response.read().find("FAILURE") >= 0): status="FAILURE"
            # Get time elapsed
            elapsed_time = (time() - start)
            # Print log info
            if status == 'FAILURE':
                error("MIRREXEC command sent to %s with (n_threads=%s) was handled  with status %s in %ss" % \
                    (self.target_node,str(self.n_threads),status,str(elapsed_time)))
            else:
                info(3, "MIRREXEC command sent to %s with (n_threads=%s) was handled  with status %s in %ss" % \
                    (self.target_node,str(self.n_threads),status,str(elapsed_time)))
        except Exception,e:
            error("Problems sending MIRREXEC command to %s: %s" % (self.target_node,str(e)))
        finally:
            self.target_node_conn.close()

        # Return Void
        return

# EOF
