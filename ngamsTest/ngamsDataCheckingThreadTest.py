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
# "@(#) $Id: ngamsDataCheckingThreadTest.py,v 1.4 2010/10/04 19:13:26 jagonzal Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  18/11/2003  Created
#

"""
This module contains the Test Suite for the Data Consistency Checking Thread.
"""

import os, sys
from   ngams import *
from   ngamsTestLib import *


class ngamsDataCheckingThreadTest(ngamsTestSuite):
    """
    Synopsis:
    Data Consistency Checking Thread.

    Description:
    This Test Suite exercises the Data Consistency Checking facility.
    It is verified that the various checks are properly functioning, and that
    the DCC Thread is robust towards various errors that might occur.
    
    Missing Test Cases:
    This Test Suite is very basic. A thorough review should be done and the
    missing Test Cases added.

    In particular Test Cases for detecting the various points checked should
    be added.
    """

    
    def test_DataCheckThread_1(self):
        """
        Synopsis:
        Basic functioning of Data Checking Feature.
        
        Description:
        Test Test the basic functioning of the Data Check Thread. The
        Data Check Thread is started and it is checked that it performs
        a cycle whereby all files are checked, and a Data Check Entry is
        logged into the NG/AMS Local Log File.

        Expected Result:
        After a given period of time, the DCC Thread should have completed
        one check cycle and have detected possible problems. In this case
        there are no inconsistencies found.

        Test Steps:
        - Start standard NG/AMS Server configured to carry out DCC
          continuesly.
        - Archive a small file 3 times.
        - Wait until the DCC has finished one cycle (NGAMS_INFO_DATA_CHK_STAT
          log written in the log file).
        - Check that the report is OK/that all files were checked.

        Remarks:
        ...        
        """
        baseCfgFile = "src/ngamsCfg.xml"
        tmpCfgFile = "tmp/test_DataCheckThread_1_tmp.xml"
        cfg = ngamsConfig.ngamsConfig().load(baseCfgFile)
        cfg.storeVal("NgamsCfg.DataCheckThread[1].Active", "1")
        cfg.storeVal("NgamsCfg.DataCheckThread[1].Prio", "1")
        cfg.storeVal("NgamsCfg.DataCheckThread[1].MinCycle", "0T00:00:00")
        cfg.save(tmpCfgFile, 0)
        cfgObj, dbObj = self.prepExtSrv(8888, 1, 1, 1, tmpCfgFile)
        client = ngamsPClient.ngamsPClient(getHostName(), 8888)
        for n in range(3): client.archive("src/SmallFile.fits")

        # Wait a while to be sure that one check cycle has been completed.
        logFo = open(cfg.getLocalLogFile(), "r")
        startTime = time.time()
        run = 1
        while (run and ((time.time() - startTime) < 60)):
            lines = logFo.readlines()
            for line in lines:
                if (line.find("NGAMS_INFO_DATA_CHK_STAT") != -1):
                    if (int(float(line.split(" ")[7])) == 6):
                        run = 0
                        break
        logFo.close()
        if (not run):
            # jagonzal: Adapt to 64bits checksum generated fits testing files
            self.checkEqual("0.307", line.split(" MB. ")[0].split(" ")[-1], 
                            "Data Check Thread didn't perform check as "+\
                            "expected")
        else:
            self.fail("Data Check Thread didn't complete "+\
                      "check cycle within the expected period of time")


def run():
    """
    Run the complete test.

    Returns:   Void.
    """
    runTest(["ngamsDataCheckingThreadTest"])


if __name__ == '__main__':
    """
    Main program executing the test cases of the module test.
    """
    runTest(sys.argv)


# EOF
