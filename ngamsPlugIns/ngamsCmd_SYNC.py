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
# "@(#) $Id: ngamsCmd_SYNC.py,v 1.2 2011/01/26 22:26:44 jagonzal Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jagonzal  2010/12/14  Created
#

"""
NGAS Command Plug-In, implementing a command to

NOTES: 

PARAMETER:

EXAMPLES:
    
"""

from ngams import *
import ngamsLib, ngamsStatus, ngamsDb
import urllib,httplib
import time
from threading import *

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle Command SYNC to
    
    INPUT:
    	srvObj:         ngamsServer, Reference to NG/AMS server class object
    
    	reqPropsObj:	ngamsReqProps, Request Property object to keep track
                    	of actions done during the request handling 
        
   	httpRef:        ngamsHttpRequestHandler, Reference to the HTTP request
                    	handler object
        
    RETURNS:		Void.
    """
    T = TRACE()

    sync_cluster = 0
    if (reqPropsObj.hasHttpPar("sync_cluster")):
        sync_cluster = int(reqPropsObj.getHttpPar("sync_cluster"))

    if (sync_cluster == 1):
        host_id = getHostId()
        cluster_name = get_cluster_name(srvObj,host_id)
        cluster_nodes = get_cluster_nodes(srvObj,cluster_name)
        forward_sync_command(srvObj,cluster_nodes)     
    else:
        file_list = get_file_list(srvObj)
        start_date = get_start_date(srvObj)
        set_start_date(srvObj,start_date)
        syncronization_by_subscription(srvObj,file_list)
     
    return


def get_subscriber_id(srvObj):

    host_id = getHostId()
    query = "select subscr_id from ngas_subscribers where host_id='" + host_id + "'" 
    info(3, "Executing SQL query to get subscriber_id for this server: %s" % query)
    subscriber_id = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    subscriber_id = subscriber_id[0][0][0]
    subscriber_id = subscriber_id.split('-')
    subscriber_id = subscriber_id[1]
    info(3, "Executed SQL query to get subscriber for host_id=%s (result subscriber_id=%s)" % (host_id,subscriber_id))
   
    return subscriber_id


def get_file_list(srvObj):

    host_id = getHostId()
    subscriber_id = get_subscriber_id(srvObj)
    cluster_name = get_cluster_name(srvObj,subscriber_id)

    query = "select fe.file_id,fe.file_version from "
    query += "(select nf.file_id file_id,nf.file_version file_version,nh.host_id host_id from "
    query += "ngas_files nf, ngas_disks nd, ngas_hosts nh "
    query += "where nf.disk_id = nd.disk_id and nd.host_id = nh.host_id and nh.host_id = '" + host_id + "') fe left join "
    query += "(select nf.file_id file_id, nf.file_version file_version, nh.host_id host_id from "
    query += "ngas_files nf, ngas_disks nd, ngas_hosts nh "
    query += "where nf.disk_id = nd.disk_id and nd.host_id = nh.host_id and nh.cluster_name = '"  + cluster_name + "') be on "
    query += "be.file_id = fe.file_id and be.file_version = fe.file_version where "
    query += "INSTR(fe.file_id,'NGAS-ngas')=0 and be.file_id is null"
  
    info(3, "Executing SQL query to get files missing in the subscriber server: %s" % query)
    file_list = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    file_list = file_list[0]
    info(3, "Executed SQL query to get files missing in the subscriber server (found %s)" % str(len(file_list)))

    return file_list


def get_start_date(srvObj):

    host_id = getHostId()
    subscriber_id = get_subscriber_id(srvObj)
    cluster_name = get_cluster_name(srvObj,subscriber_id)

    query = "select min(fe.ingestion_date) from "
    query += "(select nf.file_id file_id,nf.file_version file_version,nf.ingestion_date ingestion_date from "
    query += "ngas_files nf, ngas_disks nd, ngas_hosts nh "
    query += "where nf.disk_id = nd.disk_id and nd.host_id = nh.host_id and nh.host_id = '" + host_id + "') fe left join "
    query += "(select nf.file_id file_id, nf.file_version file_version, nh.host_id host_id from "
    query += "ngas_files nf, ngas_disks nd, ngas_hosts nh "
    query += "where nf.disk_id = nd.disk_id and nd.host_id = nh.host_id and nh.cluster_name = '"  + cluster_name + "') be on "
    query += "be.file_id = fe.file_id and be.file_version = fe.file_version where "
    query += "INSTR(fe.file_id,'NGAS-ngas')=0 and be.file_id is null"


    info(3, "Executing SQL query to get start date of files missing in the subscriber server: %s" % query)
    start_date = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    start_date = start_date[0][0][0]
    info(3, "Executed SQL query to get start date of missing files in the subscriber server: %s (result %s)" % (host_id,str(start_date)))

    return start_date


def set_start_date(srvObj,start_date):

    host_id = getHostId()
    subscriber_id = get_subscriber_id(srvObj)
    subscrId = host_id + "-" + subscriber_id
    subscrObj = srvObj.getSubscriberDic()[subscrId]
   
    prev_start_date = subscrObj.getStartDate()
    info(3, " Changing start date of subscription object from %s to %s" % (prev_start_date,start_date))
    subscrObj.setStartDate(start_date)


def syncronization_by_subscription(srvObj,file_list):

    info(3, "Starting syncronization by subscription")
    srvObj._subscriptionSem.acquire()
    n_total = len(file_list)
    n_partial = 0
    n_accumulated = 0
    srvObj._subscriptionFileList = []
    for file in file_list:
        srvObj._subscriptionFileList += [file]
        n_accumulated += 1
        n_partial += 1
        if (n_partial > 500):
            info(3, "Triggering subscritionThread, files left: %s" % str(n_total-n_accumulated))
            srvObj._subscriptionSem.release()
            srvObj.triggerSubscriptionThread()
            while (len(srvObj._subscriptionFileList) >= 1):
                time.sleep(1.0) 
            srvObj._subscriptionSem.acquire()
            srvObj._subscriptionFileList = []
            n_partial = 0    

    if (n_partial > 0):
        info(3, "Triggering subscritionThread, last batch of files: %s" % str(n_partial))
        srvObj._subscriptionSem.release()
        srvObj.triggerSubscriptionThread()
        while (len(srvObj._subscriptionFileList) >= 1):
            time.sleep(1.0)
    else:
       srvObj._subscriptionSem.release()
    
    info(3, "Finished syncronization by subscription")

    return


def get_cluster_name(srvObj,host_id):
    
    query = "select cluster_name from ngas_hosts where host_id='" + host_id + "'"
    info(3, "Executing SQL query to get local cluster name: %s" % query)
    cluster_name = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    cluster_name = cluster_name[0][0][0]
    info(3, "Executed SQL query to get local cluster name: %s" % str(cluster_name))

    return cluster_name


def get_cluster_nodes(srvObj,cluster_name):

    query = "select host_id from ngas_hosts where cluster_name='" + cluster_name + "'"
    info(3, "Executing SQL query to get nodes of cluster %s: %s" % (cluster_name,query))
    cluster_nodes = srvObj.getDb().query(query, maxRetries=1, retryWait=0)
    cluster_nodes = cluster_nodes[0]
    info(3, "Executed SQL query to get nodes of cluster %s: %s" % (cluster_name,str(cluster_nodes)))

    return cluster_nodes


def forward_sync_command(srvObj,cluster_nodes):

    threads_list = []
    for node in cluster_nodes:
        target_node = node[0]
        # Initialize sync_command_sender thread object
        sync_command_sender_obj = sync_command_sender(target_node)
        # Add sync_command_sender thread object to the list of threads
        threads_list.append(sync_command_sender_obj)
        # Start sync_command_sender thread object
        sync_command_sender_obj.start()

    # Join mirror_node threads
    for ith_thread in threads_list:
        ith_thread.join()

    # Return Void
    return


def send_sync_command(target_node):

    # Print log info
    info(3, "Sending SYNC command to %s" % (target_node))

    # Create target server connection
    target_node_conn = httplib.HTTPConnection(target_node)
    # Start clock
    start = time()
    # Send request to target node
    target_node_conn.request("GET","SYNC?")
    # Get response from target node
    response = target_node_conn.getresponse()
    # Get status
    status = "SUCCESS"
    return_code = 1
    if (response.read().find("FAILURE") >= 0):
        status="FAILURE"
        return_code = 0
    # Get time elapsed
    elapsed_time = (time() - start)

    # Print log info
    info(3, "SYNC command sent to %s was handled with status %s in %ss" % (target_node,status,str(elapsed_time)))

    # Return
    return return_code


class sync_command_sender(Thread):
    def __init__ (self,target_node):
        Thread.__init__(self)
        self.target_node = target_node
    def run(self):
        send_sync_command(self.target_node)


 
# EOF

