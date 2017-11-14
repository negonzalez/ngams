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
# "@(#) $Id: ngamsOracle.py,v 1.21 2012/11/22 21:47:45 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# awicenec  2005-03-15  Created
# jknudstr  2008-02-11  Removed usage of _queryRewrite(), not needed anymore.
#

"""
This module contains two classes:

The ngamsOracle class is an NG/AMS DB Interface Plug-In to be used for
interfacing with Oracle DB.

The ngamsOracleCursor class, which implements a cursor object based on
the NG/AMS Cursor Object API definition.
"""

import time, re
import cx_Oracle
import pcc, PccUtTime
from   ngams import *
from   mx import DateTime
 
class ngamsOracle:
    """
    Class to handle the connection to the NGAS DB when Oracle is used as DBMS.
    """
  
    def __init__(self,
                 server,
                 db,
                 user,
                 password,
                 application,
                 parameters):
        """
        Constructor method.

        server:          DB server name (string).

        db:              DB name (string).
        
        user:            DB user (string).
        
        password:        DB password (string).

        application:     Name of application (ID string) (string).

        parameters:      Parameters for the connection object (string).
        """
        try:
            self.__dbModVer = str(cx_Oracle.__version__)
        except:
            self.__dbModVer = "-1"
        self.createConnectionPool(server, db, user, password, application, parameters)


    def getDriverId(self):
        """
        Return DB driver ID.

        Return:    Driver version (string).
        """
        T = TRACE()
        
        return "NG/AMS_Oracle_" + self.__dbModVer
    
    def createConnectionPool(self,
                server,
                db,
                user,
                password,
                application,
                parameters):
        """
        Method to create connection to the DB server.

        server:          DB server name (string).

        db:              DB name (string).
        
        user:            DB user (string).
        
        password:        DB password (string).

        application:     Name of application (ID string) (string).

        parameters:      Parameters for the connection object (string).

        Returns:         Reference to object itself.
        """
        T = TRACE()
        # best details I found so far regarding the pool: http://www.dbaportal.eu/?q=node/151
        # TODO expose via the configuration file
        maxPoolSize = 20
        # protect every individual connection with a guard so that no two threads will be allowed
        # to use a single connection at the same time (cx_Oracle internal feature)
        isThreaded = True
        # if we try and execute a query and the pool has already lent all its connections out
        # (which is very unlikely) then we wait until one connection is returned to the pool
        mode = cx_Oracle.SPOOL_ATTRVAL_WAIT
        pool = cx_Oracle.SessionPool(user, password, db, min=1, max = maxPoolSize, increment=1,
                                     connectiontype=cx_Oracle.Connection, threaded = isThreaded,
                                     getmode = mode)
        # remove a connection from the pool after it has been idle for 1 minute
        pool.timeout = 60
        self.__pool = pool

        # Store connection parameters.
        self.__server      = server
        self.__db          = db
        self.__user        = user
        self.__password    = password
        self.__application = application
        self.__parameters  = parameters

        return self

        
    def connect(self,
                server,
                db,
                user,
                password,
                application,
                parameters):
        """
        Method to create connection to the DB server. Now that we're using a connection pool
        this is just a dummy method so that ngamsDbCore does not constantly create new pools.
        I use the mechanism in ngamsDbCore simply as a retry mechanism now.

        server:          DB server name (string).

        db:              DB name (string).
        
        user:            DB user (string).
        
        password:        DB password (string).

        application:     Name of application (ID string) (string).

        parameters:      Parameters for the connection object (string).

        Returns:         Reference to object itself.
        """
        T = TRACE()
        info(3, "dummy connect method called. The connection pool is _not_ being rebuilt")
        
    def close(self):
        """
        Close the DB connection.

        Returns:    Reference to object itself.
        """
        T = TRACE()
        info(3, "dummy close method called. The connection pool is _not_ being closed")

    def _execute(self,
                 query, parameters):
        """
        In the python Oracle module there is no direct execute, everything
        goes through cursors, thus we emulate the db.excute() method here.
        """
        T = TRACE(5)
        
        res = []
        connection = self.__pool.acquire()
        info(3, "acquired from pool: opened connections = " + str(self.__pool.opened) + ", busy = " + str(self.__pool.busy))
        cursor = connection.cursor()
        info(3, "Executing query: |%s|, parameters: %s" % (query, str(parameters)))
        try:
            cursor.execute(str(query), parameters)
            res = self._fetchAll(cursor, connection)
        except Exception, e:
            report = str(e)
            if ("ORA-00028"in report or "ORA-03113" in report or "ORA-03114" in report):
                # drop session from the pool in case
                # your session has been killed!
                # Otherwise pool.busy and pool.opened
                # will report wrong counters.
                self.__pool.drop(connection)
                warning("Connection dropped from the pool...")
            elif ("ORA-12899" in report):
                # value too large for column. No point retrying the SQL
                error(report)
            elif ("ORA-00942" in report):
                # no such table. No point retrying the SQL
                error(report)
            # it will fail on the next attempt, but I _do_ want it to fails
            # elif ("ORA-00001" in report):
                #unique constraint violated
                # error(report)
            else:
                errMsg = genLog("NGAMS_ER_DB_GENERIC", [report, query])
                error(errMsg)               
                # we need to rethrow the exception, for example if the DB is not available.
                # This allows higher-level handlers to re-establish the connection
                raise
        finally:
            cursor.close()
            del(cursor)
            self.__pool.release(connection)
            info(3, "released to pool: opened connections = " + str(self.__pool.opened) + ", busy = " + str(self.__pool.busy))
            
        if (len(res) > 0):
            info(5, "Leaving _execute() with results")
            return [res]
        else:
            info(5, "Leaving _execute() without results")
            return [[]]


    def _fetchAll(self, cursor, db):
        """
        Fetch all elements from the query and return this.
        The result will be returned as a list with the following format:

          [[<col1>, <col2>, <col3>, ...], ...]

        An empty list ([]) may be returned if there were no matches to the
        SQL query.
        
        query:      string containing the SQL statement to be executed.

        Return:     List containing tuples with the values queried
                    (list/list).
        """
        T = TRACE()

        startTime = time.time()

        try:
            res = cursor.fetchall()
        except Exception, e:
            if (str(e).find("not a query") != -1):
                db.commit()
                info(4, "Leaving fetchAll() without results")
                return []
            else:
                db.rollback()
                errMsg = "Leaving _fetchAll() after exception and " +\
                         "rollback: %s" % str(e)
                info(4, errMsg)
                return []
        deltaTime = (time.time() - startTime)
        
        if (len(res) > 0):
            info(4, "Leaving _fetchAll() with results: |%s| Time: %.4fs" %\
                 (str(res),deltaTime))
            return res
        else:
            info(4, "Leaving _fetchAll() without results. Time: %.4fs" %\
                 deltaTime)
            return []

    def query(self,
              query, parameters = {}):
        """
        Perform a query in the DB and return the result. The result will
        be returned as a list with the following format:

          [[<col1>, <col2>, <col3>, ...], ...]

        An empty list ([]) may be returned if there were no matches to the
        SQL query.

        query:         SQL query (string).

        Returns:       Result of SQL query (list).
        """
        T = TRACE()
        startTime = time.time()
        try:
            res = self._execute(query, parameters)
            deltaTime = (time.time() - startTime)
            info(4, "Leaving query() Time: %.4fs" % deltaTime)
            return res
        except Exception, e:
            for n in range(10):
                try:
                    pass
                except Exception, e:
                    time.sleep(0.1)
                break

            # Try to reconnect once if the connection is not available
            # - maybe it was lost.
            if ((str(e).find("connection is not open") != -1) or
                (str(e).find("connection has been marked dead") != -1) or
                (str(e).find("operation terminated due to disconnect") != -1)):
                time.sleep(2.0)
                self.connect(self.__server, self.__db, self.__user,
                             self.__password)
                info(1,"Reconnected to DB - performing SQL query: " + query)
                res = self._execute(query, parameters)
                return res
            else:
                raise e

 
    def cursor(self,
               query):
        """
        Create a DB cursor with the same connection properties for the
        given SQL query and return a cursor handle.

        query:       SQL query (string).

        Returns:     Cursor object (<NG/AMS Cursor Object API>.
        """
        T = TRACE()

        return ngamsOracleCursor(self.__server, self.__db, self.__user,
                                 self.__password,
                                 self.__application + ":" +\
                                 threading.currentThread().getName(),
                                 self.__parameters, query = query)


    def convertTimeStamp(self,
                         timeStamp):
        """
        Convert a timestamp in one of the following representations to
        a timestamp string, which can be used to set a column of the DBMS
        of type 'datetime'.

        timeStamp:    Timestamp represented in one of the following formats:

                        1. ISO 8601:  YYYY-MM-DDTHH:MM:SS[.s]
                        2. ISO 8601': YYYY-MM-DD HH:MM:SS[.s]
                        3. Secs since epoc.
                                                        (string|integer|float).

        Returns:      Timestamp in format, which can be written into
                      'datetime' column of the DBMS (string).
        """
        T = TRACE(5)
        
        if (str(timeStamp).find(":") != -1):
            if (timeStamp[10] != "T"): timeStamp[10] = "T"
            ts = timeStamp
            ts = PccUtTime.TimeStamp().\
                 initFromTimeStamp(timeStamp).getTimeStamp()
        else:
            ts = PccUtTime.TimeStamp().\
                 initFromSecsSinceEpoch(timeStamp).getTimeStamp()
        return ts

        
    def convertTimeStampToMx(self,
                             timeStamp):
        """
        Converts an ISO 8601 timestamp into an mx.DateTime object.
        
        timeStamp:  ISO 8601 Datetime string (string/ISO 8601).
        
        Returns:    Date time object (mx.DateTime).
        """
        T = TRACE(5)
        
        return DateTime.ISO.ParseDateTime(timeStamp)


class ngamsOracleCursor:
    """
    Cursor class used to fetch sequentially the result of an SQL query.
    """

    def __init__(self,
                 server,
                 db,
                 user,
                 password,
                 application,
                 parameters,
                 query = None):
        """
        Constructor method creating a cursor connection to the DBMS.

        server:       DB server name (string).
 
        db:           DB name (string).
        
        user:         DB user (string).
        
        password:     DB password (string).

        query:        Query to execute (string/SQL).

        application:  Application name (string).

        parameters:   Parameters for the connection object (string).
        """
        T = TRACE()

        tns = db
        self.__cursorObj = None
        self.__dbDrv = cx_Oracle.connect(user, password, tns, threaded = 1)
        if ((query != None) and (len(query) != 0)): self._initQuery(query)
        

    def __del__(self):
        """
        Destructor method free'ing the internal DB connection + cursor objects.
        """
        T = TRACE()
        
        if (self.__cursorObj): del self.__cursorObj
        if (self.__dbDrv): del self.__dbDrv
        
                     
    def _initQuery(self,
                   query):
        """
        Initialize the query.
        
        query:    The query to execute (string)
        
        Returns pointer to itself.
        """
        T = TRACE()
        
        # Query replace to catch DB specifics.
        #query = self._queryRewrite(query)
        self.__cursorObj = self.__dbDrv.cursor()
        info(4, "Executing query: |%s|" % query)
        self.__cursorObj.execute(str(query))
        return self
        

    def fetch(self,
              maxEls):
        """
        Fetch a number of elements from the query and return this.
        The result will be returned as a list with the following format:

          [[<col1>, <col2>, <col3>, ...], ...]

        An empty list ([]) may be returned if there were no matches to the
        SQL query.
        
        query:      string containing the SQL statement to be executed.

        maxEls:     Maximum number of elements/rows to return (integer).

        Return:     List containing tuples with the values queried
                    (list/list).
        """
        T = TRACE()
        
        if (self.__cursorObj):
            res = self.__cursorObj.fetchmany(maxEls)
            if len(res) > 0:
                info(4, "Leaving fetch with %d results" % len(res))
                return res
            else:
                info(4, "Leaving fetch without results")
                return []
        else:
            info(4, "Leaving fetch without results (no valid cursor object)")
            return []



    def _queryRewrite(self,
                      query):
        """
        Method holds query replacements to catch differences between the SQL
        queries as coded in ngamsDb and the actual SQL query as supported by
        the DB.

        query:    The query as send by ngamsDb (string)
        
        Returns the modified query string.
        """
        T = TRACE()

        # The following block replaces the ignore column name (reserved word
        # in mySQL) with file_ignore.
        regex1 = re.compile('ignore')
        pquery = regex1.sub('file_ignore',query)

        # Remove the Sybase specific noholdlock keyword
        info(5, "Original query: %s" % query)
        regex2 = re.compile('noholdlock')
        pquery = regex2.sub('', query)
        
        #regex1 = re.compile('max\(right\(logical\_name, 6\)\)')
        #pquery = str(regex1.sub('max(substr(logical_name, -6))', pquery))
        info(5, "Rewritten query: %s" % pquery)
        return pquery


if __name__ == '__main__':
    """
    Main function to test the module.
    """
    pass

# EOF
