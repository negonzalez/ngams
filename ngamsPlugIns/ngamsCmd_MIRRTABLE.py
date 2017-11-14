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
from ngams.ngamsPlugIns.ngamsCmd_RSYNC import _handleCmd

#******************************************************************************
#
# "@(#) $Id: ngamsCmd_MIRRTABLE.py,v 1.23 2012/11/22 21:48:22 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jagonzal  2009/12/14  Created
#

"""
NGAS Command Plug-In, implementing a command to fill the mirroring_bookkeping_table 

NOTES: By default only the last version found in the source cluster is synchronized
       to the target cluster. To synchronize all existing versions specify all_versions=1.
       In case of remote data-base mirroring it is necessary to enable data-base links
       to the source/target data-bases in the local data-base. If the target data-base
       is the local one is not neccesary to specify a target data-base link, (by default 
       the local data base is the target data base)

PARAMETERS:
	-source_cluster	[mandatory] source cluster name
	-target_cluster	[mandatory] target cluster name
	-source_dbl	[optional] source archive data base link (remote data base mirroring)
	-target_dbl	[optional] target archive data base link (remote data base mirroring)    
	-all_versions	[optional] (=1) mirror all missing versions of each file, default (=0)
	-archive_cmd	[optional] custom archive command, default (=MIRRARCHIVE)
	-retriev_cmd	[optional] custom retrieve command, default (=RETRIEVE)

EXAMPLES:
	- Local data base mirroring with custom ARCHIVE command
		http://ngas05.hq.eso.org:7778/MIRRTABLE?target_cluster=ngas05:7778&source_cluster=ngas02:7778&archive_cmd=QARCHIVE?
    
"""
from ngams import error, TRACE, info, warning, getHostId
from ngams.ngamsLib import ngamsLib
import time;
from time import strftime, localtime, gmtime
import thread
import httplib
import socket

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    info(3, 'handleCmd started')
    try:
        __handleCmd(srvObj, reqPropsObj, httpRef)
    except Exception, e:
        # this clause should never be reached
        error("Mirroring failed:  " + str(e))
    finally:
        info(3, 'handleCmd finished')
    
def __handleCmd(srvObj,
                reqPropsObj,
                httpRef):
    """
    Handle Command MIRRTABLE to populate bookkeeping table in target cluster
    
    INPUT:
    	srvObj:         ngamsServer, Reference to NG/AMS server class object
    
    	reqPropsObj:	ngamsReqProps, Request Property object to keep track
                    	of actions done during the request handling 
        
   	httpRef:        ngamsHttpRequestHandler, Reference to the HTTP request
                    	handler object
        
    RETURNS:		Void.
    """
    TRACE()

    # Get command parameters.
    target_cluster = srvObj.getCfg().getVal("Mirroring[1].target_cluster")
    if (reqPropsObj.hasHttpPar("target_cluster")):
        target_cluster = reqPropsObj.getHttpPar("target_cluster")
    source_cluster = srvObj.getCfg().getVal("Mirroring[1].source_cluster")
    if (reqPropsObj.hasHttpPar("source_cluster")):
        source_cluster = reqPropsObj.getHttpPar("source_cluster")    
    source_dbl = "@" + srvObj.getCfg().getVal("Mirroring[1].source_dbl")
    if (reqPropsObj.hasHttpPar("source_dbl")):
        source_dbl = "@" + reqPropsObj.getHttpPar("source_dbl")
    target_dbl = ""
    if (reqPropsObj.hasHttpPar("target_dbl")):
        target_dbl = "@" + reqPropsObj.getHttpPar("target_dbl")
    all_versions = srvObj.getCfg().getVal("Mirroring[1].all_versions")
    if (reqPropsObj.hasHttpPar("all_versions")):
        all_versions = int(reqPropsObj.getHttpPar("all_versions"))
    
    # what was the date of the last succesful mirroring iteration? We will only compare files
    # from local and remote databases from that date (the start of the iteration, just to allow
    # some error margin)
    siteId = getCurrentSite(srvObj)
    validArcs = ['EU', 'EA', 'NA', 'SCO', 'OSF']
    if not (siteId in validArcs): raise Exception("Can not mirror, The table ngas_cfg_pars_properties does not contain an element 'siteId' with one of these values: " + str(validArcs))

    # we're overlapping mirroring iterations now. First check is to see if there are any spare threads
    # for this iteration to use
    # TODO needs a complete rewrite - this ignores the indiviual number of downloads per
    # server - we may end up with a very unbalanced download count per ngas node
    numAvailableDownloadThreads = getNumAvailableDownloadThreads(srvObj)
    if numAvailableDownloadThreads <= 0: 
        info(2, "All the available download threads are busy. Skipping this mirroring iteration.")
        return
    info(2, "there are %s threads available for downloading files " % str(numAvailableDownloadThreads))

    baselineDate = getMirroringBaselineDate(srvObj)
    if baselineDate is None or baselineDate == "None":
        startDate = "None"
    else:
        # work out the time window to compare files. We use the last succesful iteration and then subtract 100 for safety
        startDate = findDateOfLastSuccessfulMirroringIteration(srvObj)
        # however, if this is the first mirroring iteration of a new day then we perform a complete mirror
        lastIteration = findDateOfLastMirroringIteration(srvObj)
        if (lastIteration is None or lastIteration == "None" or lastIteration[8:10] != strftime('%d', localtime())): 
            info(2, 'performing a full mirroring')
            startDate = "None"
        # unless, of course, the baselineDate has been set. We never ever extend beyond that.
        if startDate == "None" and baselineDate: 
            info(2, 'using the baseline data from the config table: baselineDate')
            startDate = baselineDate + "T00:00:00:000"
    rows_limit = getIterationFileLimit(srvObj)
    
    # Get target cluster active nodes
    target_active_nodes = get_cluster_active_nodes(target_dbl, target_cluster, srvObj)

    # Get source cluster active nodes
    source_active_nodes = get_cluster_active_nodes(source_dbl, source_cluster, srvObj) 

    if len(source_active_nodes) == 0:
        warning("there are no active source nodes. Skipping this iteration.")
    else:
        # Construct sub-query for source cluster
        source_query = generate_source_files_query(srvObj, startDate, source_dbl, source_cluster, all_versions)
        info(4, "SQL sub-query to get source cluster files-hosts information: %s" % source_query)
    
        # Construct sub-query for target cluster 
        target_query = generate_target_files_query(startDate, target_cluster, all_versions)
        info(4, "SQL sub-query to get target cluster files-hosts information: %s" % target_query)

        # Construct sub-query for  table
        diff_query = generate_diff_ngas_files_query(source_query, target_query)
        info(4, "SQL sub-query to get diff between source and target files: %s" % diff_query)

        # Get iteration nmumber
        iteration = get_mirroring_iteration(srvObj)

        # Populate book keeping table
        info(3, "Populating ngas_mirroring_bookkeeping_table, source_cluster=%s , target_cluster=%s, all_versions=%s" \
             % (source_cluster + source_dbl, target_cluster + target_dbl, str(all_versions)))
        populate_mirroring_bookkeeping_table(diff_query, startDate, target_dbl, target_cluster, iteration, srvObj)
        
        # grab any toresume fetches for this iteration
        reassign_broken_downloads(iteration, srvObj)

        # de-schedule any files which have been blocked from the SCO
        deschedule_exclusions(iteration, 'EU', source_dbl, srvObj);

        # de-schedule any files which have been blocked by the ARC
        # deschedule_exclusions(iteration, 'HERE', target_dbl, srvObj);
        
        # limit the number of files that we will fetch in a single iteration
        if rows_limit is not None and rows_limit != 'None': 
            limitMirroredFiles(srvObj, iteration, rows_limit)

        # remove the source nodes which do not have any files for mirroring during this iteration
        working_source_nodes = remove_empty_source_nodes(iteration, source_active_nodes, target_cluster, srvObj)
   
        # Assign book keeping table entries
        info(3, "Updating entries in ngas_mirroring_bookkeeping_table to assign target nodes")
        totalFilesToMirror = assign_mirroring_bookkeeping_entries(iteration, target_active_nodes, working_source_nodes, target_dbl, target_cluster, srvObj)

        info(2, "There are " + str(totalFilesToMirror) + " files are to be mirrored in iteration " + str(iteration))
        target_node_conn = None
        if totalFilesToMirror > 0:
            thread.start_new_thread(executeMirroring, (srvObj, iteration))
    return

def executeMirroring(srvObj, iteration):
    info(3, 'executeMirroring for iteration ' + str(iteration))
    try:
        # this should be set in every ngams server instance so that if, for example, the conenction to the DB
        # is not reachable then the socket comms do not hang forever. Ideally this should be done in the ngamsServer
        # startup but I'm localising the changes to the mirroring plugin for the moment. When we have a callback
        # from the startup then we can move this code there.
        rx_timeout = 30 * 60
        if srvObj.getCfg().getVal("Mirroring[1].rx_timeout"):
            rx_timeout = int(srvObj.getCfg().getVal("Mirroring[1].rx_timeout"))

        local_server_full_qualified_name = get_full_qualified_name(srvObj)
        originalTimeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(None)
        target_node_conn = httplib.HTTPConnection(local_server_full_qualified_name)
        # Perform mirroring tasks
        n_threads = getNumberOfSimultaneousFetchesPerServer(srvObj)
        target_node_conn.request("GET","MIRREXEC?"+\
                                   "mirror_cluster=2"+\
                                   "&iteration=" + str(iteration) +\
                                   "&rx_timeout=" + str(rx_timeout) +\
                                   "&n_threads=" + n_threads)
        socket.setdefaulttimeout(originalTimeout)
        response = target_node_conn.getresponse()
        # need a slight delay here to allow the MIRREXEC thread to close the
        # socket. Otherwise we encounter the occasional "Peer disconnected" exception.
        # TODO look at the response code
        time.sleep(0.5)
    finally:
        if target_node_conn != None: target_node_conn.close()
        failRemainingTransfers(srvObj, iteration);
        info(3, 'executeMirroring for iteration ' + str(iteration) + ' complete')
 
    # remove some of the older bookkeeping entries
    clean_mirroring_bookkeeping_entries(srvObj)

def getNumAvailableDownloadThreads(srvObj):
    sql = "select numHosts * fetchesPerServer - currentFetches as availableFetches"
    sql += " from"
    sql += " ( select count(c.host_id) as numHosts"
    sql += "   from ngas_cfg_pars p"
    sql += "     inner join ngas_hosts h on h.host_id = p.cfg_val"
    sql += "     inner join ngas_hosts c on h.cluster_name = c.cluster_name"
    sql += "   where p.cfg_par = 'masterNode')," 
    sql += " ( select count(*) as currentFetches"
    sql += "   from ngas_mirroring_bookkeeping"
    sql += "   where status = 'FETCHING')," 
    sql += " ( select cfg_val as fetchesPerServer"
    sql += "   from ngas_cfg_pars"
    sql += "   where cfg_par = 'numParallelFetches')"

    res = srvObj.getDb().query(sql, maxRetries = 1, retryWait = 0)
    numAvailable = int(res[0][0][0])
    return numAvailable

def failRemainingTransfers(srvObj, iteration):
    info(3, 'making sure there are no READY entries left for iteration ' + str(iteration))
    sql = "update ngas_mirroring_bookkeeping set status = 'FAILURE' where status = 'READY' and iteration = :iteration"
    
    parameters = {"iteration": str(iteration)}
    srvObj.getDb().query(sql, maxRetries = 1, retryWait = 0, parameters = parameters)


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

def reassign_broken_downloads(currentIteration, srvObj):
    sql = "insert into ngas_mirroring_bookkeeping"
    sql += " (file_id, file_version, file_size, disk_id, host_id, format, status,"
    sql += " target_cluster, target_host, source_host, "
    sql += " ingestion_date, ingestion_time, iteration, checksum, staging_file, attempt, source_ingestion_date)"
    sql += " select file_id, file_version, file_size, disk_id, host_id, format, 'READY' as status,"
    sql += " target_cluster, target_host, source_host,"
    sql += " ingestion_date, ingestion_time, :1 as iteration, checksum, staging_file, attempt, source_ingestion_date"
    sql += " from ngas_mirroring_bookkeeping "
    sql += " where status = 'TORESUME'"
    srvObj.getDb().query(sql, parameters = [currentIteration])
    
    # we've grabbed 
    sql = "update ngas_mirroring_bookkeeping"
    sql += " set status = 'FAILURE',staging_file = null"
    sql += " where status = 'TORESUME' and iteration < :1"
    srvObj.getDb().query(sql, parameters = [currentIteration])

def clean_mirroring_bookkeeping_entries(srvObj):
    # TBD parameterise the time period
    info(3, 'cleaning up mirroring bookkeeping table - removing entries older than 60 days')
    
    query = "delete from ngas_mirroring_bookkeeping where iteration < ("
    query += "select max(iteration) from ("
    query += "select iteration from ngas_mirroring_bookkeeping"
    query += " group by iteration having min(status) = 'SUCCESS'"
    query += " and substr(max(ingestion_date), 1, 10) < to_char(sysdate - 60, 'YYYY-MM-DD')))"

    #srvObj.getDb().dbCursor(query)
    srvObj.getDb().query(query)

def findDateOfLastMirroringIteration(srvObj):
    query = "select min(ingestion_date)"
    query += " from ngas_mirroring_bookkeeping"
    query += " where iteration = ("
    query += " select max(iteration) from ngas_mirroring_bookkeeping)"

    # Execute query 

    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    timestamp = str(res[0][0][0])

    # Log info
    info(3, "the date of the last mirroring iteration was " + timestamp)

    # Return void
    return timestamp

def findDateOfLastSuccessfulMirroringIteration(srvObj):
    query = "select min(ingestion_date)"
    query += " from ngas_mirroring_bookkeeping"
    query += " where iteration = ("
    query += " select max(iteration) - 100 from ("
    query += " select iteration from ngas_mirroring_bookkeeping"
    query += " group by iteration having count(distinct(status)) = 1"
    query += " and min(status) = 'SUCCESS'))"

    # Execute query 
    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    timestamp = str(res[0][0][0])

    # Log info
    info(3, "The start of the sliding window is  " + timestamp)

    # Return void
    return timestamp

def getNumberOfSimultaneousFetchesPerServer(srvObj):
    query = "select cfg_val"
    query += " from ngas_cfg_pars"
    query += " where cfg_par = 'numParallelFetches'"

    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    n_threads = str(res[0][0][0])
    if n_threads == None or n_threads == "None": n_threads = 5
    
    return n_threads

def getMirroringBaselineDate(srvObj):
    query = "select cfg_val"
    query += " from ngas_cfg_pars"
    query += " where cfg_par = 'baselineDate'"

    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    baselineDate = str(res[0][0][0])
    
    info(3, "mirroring baseline date is " + baselineDate)
    return baselineDate

def getIterationFileLimit(srvObj):
    query = "select cfg_val"
    query += " from ngas_cfg_pars"
    query += " where cfg_par = 'iterationFileLimit'"

    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    limit = str(res[0][0][0])    
    return limit

def getCurrentSite(srvObj):
    query = "select cfg_val"
    query += " from ngas_cfg_pars"
    query += " where cfg_par = 'siteId'"

    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    siteId = str(res[0][0][0])
    if siteId == None or siteId == "None": siteId = '?'
    return siteId

def generate_source_files_query(srvObj,startDate, db_link,
                                       cluster_name,
                                       all_versions):
    """
    Specify an alias table that extends ngas_files 
    table including host_id/domain/srv_port information

    INPUT:
        db_link        string, Name for the data base link hosting the cluster
    cluster_name    string, Name of the cluster involved in the operation
    all_versions    int, Parameter to determine if all-versions mode is desired
    
    RETURNS:
        query       string, Sub-Query to be aliased in a whole query
    """    
       
    # Query create table statement (common)
    query = "(select nf.file_id file_id, nf.file_version file_version, "
    query += "min(ingestion_date) ingestion_date, "
    query += "substr(min(nf.disk_id || nh.host_id || nh.srv_port),1,length(min(nd.disk_id))) disk_id, "
    query += "substr(min(nf.disk_id || nh.host_id || nh.srv_port),1+length(min(nd.disk_id)),length(min(nh.host_id))) host_id, "
    query += "substr(min(nf.disk_id || nh.host_id || nh.srv_port),1+length(min(nd.disk_id))+length(min(nh.host_id)),length(min(nh.srv_port))) srv_port, "
    query += "min(nf.format) format, min(nf.file_size) file_size, min(nf.checksum) checksum, min(nh.domain) domain "
    query += "from "
    # Depending on all_versions parameter we select only last version or not
    if all_versions:
        query += "ngas_files" + db_link + " nf inner join ngas_disks" + db_link + " nd on nd.disk_id = nf.disk_id "
        query += "inner join ngas_hosts" + db_link + " nh on nh.host_id = nd.host_id "
    else:
        query += "(select file_id, max(file_version) file_version from ngas_files" + db_link + " group by file_id) nflv "
        query += "inner join ngas_files" + db_link + " nf on nf.file_id = nflv.file_id and nf.file_version = nflv.file_version "
        query += "inner join ngas_disks" + db_link + " nd on nd.disk_id = nf.disk_id "
        query += "inner join ngas_hosts" + db_link + " nh on nh.host_id = nd.host_id "
    # for clarity,I used to insert all entries and then remove them according to the exclusion rules in a second step.
    # The problem with that (in the dev environment) is the performance. It brings over way more rows from the source
    # DB than is required. 
    query += " left join alma_mirroring_exclusions c "
    # replace(ingestion_date, ':60.000', ':59.999'): 
    # some "timestamps" (stored as varchar2 in Oracle) have 60 as the seconds value due to an 
    # earlier NGAS bug. We can't convert that to an Oracle timestamp so have to hack it.
    query += " on file_id like c.file_pattern and to_timestamp(replace(ingestion_date, ':60.000', ':59.999'), 'YYYY-MM-DD\"T\"HH24:MI:SS.FF') between c.ingestion_start and c.ingestion_end and arc = 'HERE'"
    query += "where "
    # ignore certain mime types
    query += "nf.format not in ('application/octet-stream', 'text/log-file', 'unknown') and "
    # no longer ignore files where the file_status is not 0. Always replicate to the ARCs.
    query += "nf.ignore=0 and "
    # Query join conditions to reach host_id (common) and check cluster name
    query += "nh.cluster_name='" + cluster_name + "' "
    if startDate is not None and startDate != "None":
        query += " and ingestion_date > :startDate "
    query += " group by nf.file_id,nf.file_version"
    query += " having (max(rule_type) is null or max(rule_type) <> 'EXCLUDE')"
    query += ")"

    # Return query
    return query

def generate_target_files_query(startDate,
                                cluster_name,
                                all_versions):
    """
    Specify an alias table that extends ngas_files 
    table including host_id/domain/srv_port information

    INPUT:
        db_link        string, Name for the data base link hosting the cluster
    cluster_name    string, Name of the cluster involved in the operation
    all_versions    int, Parameter to determine if all-versions mode is desired
    
    RETURNS:
        query       string, Sub-Query to be aliased in a whole query
    """    
    
    # Query create table statement (common)
    query = "(select nf.file_id file_id, nf.file_version file_version "
    query += "from "
    # Depending on all_versions parameter we select only last version or not
    if all_versions:
        query += "ngas_files nf inner join ngas_disks nd on nd.disk_id = nf.disk_id "
        query += "inner join ngas_hosts nh on nh.host_id = nd.last_host_id "
    else:
        query += "(select file_id, max(file_version) file_version from ngas_files group by file_id) nflv "
        query += "inner join ngas_files nf on nf.file_id = nflv.file_id and nf.file_version = nflv.file_version "
        query += "inner join ngas_disks nd on nd.disk_id = nf.disk_id "
        query += "inner join ngas_hosts nh on nh.host_id = nd.last_host_id "
    query += "where "
    # ICT-1988 - cannot take file_status into consideration
    # query += "nf.ignore=0 and nf.file_status=0 and "
    query += "nf.ignore=0 and "
    # Query join conditions to reach host_id (common) and check cluster name
    query += "nh.cluster_name='" + cluster_name + "' "
    if startDate is not None and startDate != "None":
        query += "and ingestion_date > :startDate "
    query += "group by nf.file_id,nf.file_version"
    # these are the files that are currently downloading. We include them in the union so 
    # that they wil not be re-considered for mirroring
    query += " union all"
    # query += " select nf.file_id file_id, nf.file_version file_version from"
    # query += " (select file_id, file_version, target_host from ngas_mirroring_bookkeeping "
    # query += " where status in ('READY', 'TORESUME', 'FETCHING')) nf"
    # query += " inner join ngas_hosts h on replace(h.host_id, ':', '.' || domain || ':') = nf.target_host"
    # query += " group by nf.file_id, nf.file_version))"
    query += " select file_id, file_version from ngas_mirroring_bookkeeping "
    query += " where status in ('READY', 'TORESUME', 'FETCHING')"
    query += " group by file_id, file_version)"

    # Return query
    return query


def generate_diff_ngas_files_query(source_ext_ngas_files_query,
                                   target_ext_ngas_files_query):
    """
    Specify an alias table to handle the result 
    of the left join (diff) query between source
    and target extended ngas files sub-queries

    INPUT:
        source_ext_ngas_files_query	string, Sub-Query defining ngas_files information in source cluster
        target_ext_ngas_files_query	string, Sub-Query defining ngas_files information in target cluster
    
    RETURNS:
        query   			string, Sub-Query to be aliased in a whole query
    """
    
    # Query create table statement (common)
    query = "(select source.file_id, source.file_version, source.disk_id,"
    query += " source.format, source.file_size, source.checksum,"
    query += " source.host_id, source.domain, source.srv_port," 
    # replace: some "timestamps" (stored as varchar2 in Oracle) have 60 as the seconds value due to an 
    # earlier NGAS bug. We can't convert that to an Oracle timestamp so have to hack it.
    query += " to_timestamp(replace(source.ingestion_date, ':60.000', ':59.999'), 'YYYY-MM-DD\"T\"HH24:MI:SS:FF') as ingestion_date" 
    query += " from "

    # Query left join condition
    query += source_ext_ngas_files_query + " source left join " + target_ext_ngas_files_query + " target on "
    query += "target.file_id = source.file_id and target.file_version = source.file_version "
    # Get no-matched records
    query += "where target.file_id is null)"

    # Log info
    info(4, "SQL sub-query to generate extended ngas_files table: %s" % query)

    # Return query
    return query    


def get_mirroring_iteration(srvObj):

    """
    Get iteration number for next mirroring loop
    """

    # Construct query
    query = "select max(iteration)+1 from ngas_mirroring_bookkeeping"

    # Execute query 
    res = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    iteration = str(res[0][0][0])

    if (iteration == 'None'): iteration = '1'
    info(3, "next mirroring iteraion: %s" % iteration)

    # Return void
    return iteration


def populate_mirroring_bookkeeping_table(diff_ngas_files_query,
                                         startDate,
                                         dbLink,
                                         cluster_name,
                                         iteration,
                                         srvObj):
    """
    Populate mirroring book keeping table with the
    diff between the source and target tables.
    
    INPUT:
        diff_ngas_files_query	string, Sub-Query defining the diff between the ngas_files
					in the source and target clusters 
    	dbLink			string, Name for the data base link hosting the target cluster
	cluster_name		string, Name of the target cluster
        iteration		string, Iteration number for next mirroring loop
	srvObj			ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:		Void.
    """
    
    ## First dump information from diff_ngas_files into book keeping table
    
    # Insert query statement
    query = "insert into ngas_mirroring_bookkeeping" + dbLink + " "
    # Fields to be filled
    query += "(file_id, file_version, disk_id, host_id, "
    query += "file_size, format, status, target_cluster, "
    query += "source_host, ingestion_date, "
    query += "iteration, checksum, source_ingestion_date)"
    query += "select "
    # file_id: Direct from diff_ngas_files table
    query += "d.file_id, "
    # file_version: Direct from diff_ngas_files table
    query += "d.file_version, "
    # disk_id: Direct from diff_ngas_files table
    query += "d.disk_id, "
    # host_id: Direct from diff_ngas_files table
    query += "d.host_id, "
    # file_size: Direct from diff_ngas_files table
    query += "d.file_size, "
    # format: Direct from diff_ngas_files table
    query += "d.format, "
    # status: Must be filled with 0 in case of no-ready entry
    query += "'LOCKED'," 
    # target_host: We can temporary use the name of the target cluster 
    #              rather than the target host to lock the table entry
    query += "'" + cluster_name + "', "
    # source_host: We concatenate host_id (without port)
    query += "substr(d.host_id,0,instr(d.host_id || ':',':')-1) || '.' || "
    #              With domain name and port number
    query += "d.domain || ':' || d.srv_port, "
    # ingestion_date: We have to assign it a default value because it is part of the primary key
    query += ":ingestionDate, "
    # iteration: In order to distinguish from different runs
    query += ":iteration, "
    # the checksum from the source node
    query += "d.checksum, d.ingestion_date"
    # All this info comes from the diff table
    query += " from " + diff_ngas_files_query + " d"
    #if rows_limit is not None and rows_limit != "None":
    #    query += " where rownum <= " + str(rows_limit)
    
    # this is potentially a long-running SQL command. Therefore we run it using a dedicated connection and cursor
    #srvObj.getDb().dbCursor(query)
    parameters = {
        "startDate": startDate,
        "ingestionDate": strftime("%Y-%m-%dT%H:%M:%S:000", gmtime()),
        "iteration": iteration
    }
    srvObj.getDb().query(query, parameters = parameters, maxRetries=0, retryWait=0)

    # Return void
    return


def get_cluster_active_nodes(db_link,
                             cluster_name,
                             srvObj):
    """
    Return active nodes in a NG/AMS cluster

    INPUT:
        dbLink		string, Name for the data base link of the cluster
        cluster_name	string, Name of the cluster to check
        srvObj 		ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
    	active_nodes	list[strings], List of the active nodes in the cluster
    """
    
    # Construct query
    # TODO but only if there is a disk available....
    query = "select substr(host_id,0,instr(host_id || ':',':')-1) || '.' || domain || ':' || srv_port "
    query += "from ngas_hosts" + db_link + " where "
    query += "cluster_name='" + cluster_name + "' and srv_state='ONLINE' and srv_archive=1"
    
    # Execute query
    active_nodes_object = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    
    # Re-dimension query results array
    active_nodes_object = active_nodes_object[0]
    active_nodes = []
    for node in active_nodes_object:
        active_nodes.append(node[0])
    
    # Log info
    info(3, "Active nodes found in cluster %s: %s" % (cluster_name + db_link, str(active_nodes)))

    # Return active nodes list
    return active_nodes


def remove_empty_source_nodes(iteration, 
                              source_active_nodes,
                              cluster_name,
                              srvObj):
    """
    Remove source active nodes that don't contain any file to mirror

    INPUT:
        source_active_nodes	string, List of active nodes in the source cluster
        cluster_name    	string, Name of the target_cluster
        srvObj          	ngamsServer, Reference to NG/AMS server class object
    
    RETURNS:
        source_nodes    list[strings], List of the active source nodes
    """

    # Construct query
    query = "select source_host from ngas_mirroring_bookkeeping where target_cluster='" + cluster_name + "' "
    query += " and (status='LOCKED' or status = 'READY') and iteration = " + iteration + " group by source_host"

    source_nodes_object = srvObj.getDb().query(query, maxRetries=1, retryWait=0)

    # Re-dimension query results array
    source_nodes_object = source_nodes_object[0]
    source_nodes = []
    for node in source_nodes_object:
        source_nodes.append(node[0])
    info(3, "source nodes: " + str(source_nodes))

    # Compute the intersection of both lists
    working_nodes = []
    for node in source_active_nodes:
        if (source_nodes.count(node) > 0): working_nodes.append(node)
    info(3, "active source nodes: " + str(working_nodes))
    
    # Return working nodes list
    return working_nodes

def deschedule_exclusions(iteration, arc, dbLink, srvObj):
    sql = "delete from ngas_mirroring_bookkeeping b where b.rowid in ("
    sql += "select min(f.rowid) from ngas_mirroring_bookkeeping f"
    sql += " left join alma_mirroring_exclusions" + dbLink + " c on f.file_id like c.file_pattern"
    sql += " and f.source_ingestion_date between c.ingestion_start and c.ingestion_end"
    sql += " and arc = :arc and iteration = :iteration"
    sql += " group by f.file_id, f.file_version having max(rule_type) = 'EXCLUDE')"
                
    info(3, 'removing SCO exclusions')
    try:
        srvObj.getDb().query(sql, parameters = {"iteration": iteration, "arc": arc}, maxRetries=1, retryWait=0)
    except Exception, e:
        # this clause should never be reached
        error("Fetch failed in an unexpected way: " + str(e))

def limitMirroredFiles(srvObj, iteration, fileLimit):
    # this is just used in development. I recommend not to use it in production, otherwise
    # we risk losing partially downloaded file.
    info(3, 'limiting the number of files to fetch to ' + str(fileLimit))
    sql = "delete from ngas_mirroring_bookkeeping where rowid in ("
    sql += "select myrowid from ("
    sql += "select rowid as myrowid, rownum as myrownum from ngas_mirroring_bookkeeping where iteration = :iteration"
    # prefer files which are already downloading - otherwise we risk losing the data that has already been downloaded
    sql += " order by staging_file"
    sql += ") where myrownum > :fileLimit)"
    
    srvObj.getDb().query(sql, parameters = {"iteration": iteration, "fileLimit": fileLimit}, maxRetries = 1, retryWait = 0)
    

def assign_mirroring_bookkeeping_entries(iteration,
                                         target_cluster_active_nodes,
                                         source_cluster_active_nodes,
                                         db_link,
                                         cluster_name,
                                         srvObj):
    """
    Update target_cluster field in the book keeping 
    table in order to assign entries to each node.

    The entries are assigned to target cluster nodes
    making sure that the file-size distribution is 
    balanced. To do it so the entries to be assigned
    are first file-size sorted and then the 1st entry
    is assigned to the first node, the 2nd entry to
    the 2nd node and so on until all the nodes have
    been assigned one entry and then it starts again.
    
    At the end all the nodes should have been assigned
    the same number of files, the same total load in Mb
    and the same distribution of files in terms of file size.

    INPUT:
        target_cluster_active_nodes	list[strings], List of the active nodes in the target cluster	
	target_cluster_source_nodes     list[strings], List of the active nodes in the source cluster
        db_link				string, Name for the data base link hosting the target cluster			
        cluster_name			string, Name of the target cluster
	srvObj				ngamsServer, Reference to NG/AMS server class object			
    
    RETURNS:			Void.
    """
    
    totalFilesToMirror = 0
    
    n_target_nodes = len(target_cluster_active_nodes)

    # Source nodes loop
    for source_node in source_cluster_active_nodes:
        i = 0
        # Target nodes loop
        for target_node in target_cluster_active_nodes:
            # Construct query, for every update the nodes left are n_nodes-i
            query = "update ngas_mirroring_bookkeeping set status='READY',target_host=:1 where rowid in "
            query += "("
            query += "  select inner_rowid from "
            query += "  ("
            query += "    select rowid as inner_rowid, rownum as inner_rownum from ngas_mirroring_bookkeeping"
            query += "    where target_cluster=:2"
            query += "    and target_host is null and iteration = :3"
            query += "    order by file_size"
            query += "  ) "
            query += "  where mod(inner_rownum, :4) = 0"
            query += ")"
            # Perform query
            parameters = [target_node, cluster_name, iteration, str(n_target_nodes - i)]
            info(3, "SQL to assign entries from source node %s to target node %s: %s %s" % (source_node, target_node, query, str(parameters)))
            srvObj.getDb().query(query, maxRetries=1, retryWait=0, parameters=parameters)
            i += 1
            # Log info
            query = "select count(*),sum(file_size/(1024*1024)) from ngas_mirroring_bookkeeping where status='READY' " 
            query += "and source_host = :1 and target_host = :2 "
            query += "and iteration = :3"
            parameters = [source_node, target_node, iteration]
            res = (srvObj.getDb().query(query, maxRetries=1, retryWait=0, parameters=parameters))[0]
            n_files = str(res[0][0])
            totalFilesToMirror += res[0][0]
            total_load = str(res[0][1])
            info(3, "Mirroring tasks from source host %s assigned to target host %s: %s tasks, %s MB" % (source_node, target_node, n_files, total_load))

    # Return void
    return totalFilesToMirror

  
# EOF

