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
# ESO/DFS
#
# "@(#) $Id: ngamsExtractFitsHdrDppi.py,v 1.2 2011/11/24 13:06:42 amanning Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# awicenec  26/09/2002  Created
# awicenec  31/03/2004  Support for extraction of certain headers
#

"""
Contains a DDPI which is used to extract the main header from FITS files.
"""

from ngams import *
import ngamsPlugInApi, ngamsDppiStatus
import printhead


def ngamsExtractFitsHdrDppi(srvObj,
                            reqPropsObj,
                            filename):
    """
    This DPPI extracts the main header from a FITS file
    requested from the ESO Archive.

    srvObj:        Reference to instance of the NG/AMS Server
                   class (ngamsServer).
    
    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).
    
    filename:      Name of file to process (string).

    Returns:       DPPI return status object (ngamsDppiStatus).

    Side effect:   This DPPI works directly on the archived file, since it is
                   read-only access.

    SPECIFIC DOCUMENTATION:

        This DPPI controls the call to the printhead module. If the 

	Example URL (single line):

	http://ngasdev1:7777/RETRIEVE
		?file_id=MIDI.2004-02-11T04:16:04.528&
		processing=ngamsExtractFitsHdrDppi&
		processing_pars='header=99'
	
	The header parameter is optional, if not specified the primary header
	is returned.
	Valid values for the header parameter are numbers between 1 and 99 and
	the strings 'vo' or 'xf'. If numbers are specified which are either
	outside the range or bigger than the number of headers (including the
	primary) the primary header will be returned. Headers are counted from
	1 starting with the primary header. 99 is a special value as it returns
 	all headers concatenated in a single file.

	If 'vo' is specified all headers are returned using a slightly modified
	VOTable (XML) format. If 'xf' is specified all headers are returned
	using the XFits (XML) format.
    """
    statusObj = ngamsDppiStatus.ngamsDppiStatus()

    pH = printhead.FitsHead(filename,struct=1)

    hind = 1 # first header only by default
    head = ''
    if (reqPropsObj.hasHttpPar("processing_pars")): 
	pars = ngamsPlugInApi.parseRawPlugInPars(\
		reqPropsObj.getHttpPar("processing_pars"))
	if not pars.has_key('header'):
	    ext = '.hdr'
	    hind = 1    # first header only by default
	else:           # if processing_par 'header' exists check its contents
	    phead = pars['header']
	    if phead.lower() in ['vo','xf']:
		ext = '.xml'
		hind = -1
		pH.parseFitsHead()
		if phead.lower() == 'vo':
		    pH.voImageHead(outfile='')
		    head = '\n'.join(pH.VoImageHead)
		else:
		    pH.xmlHead(outfile='')
		    head = '\n'.join(pH.XmlHead)
	    else:
		ext = '.hdr'
		try: 
	            hind = int(pars['header'])
		    if hind <= 0: hind = 1
		except:
		    hind = 1
    	hind = hind - 1  # index starts at 0 

    if hind == 98:
	head = ''.join(pH.HEAD)
    elif hind >= 0 and hind < len(pH.HEAD):
	head = pH.HEAD[hind]
    elif hind > len(pH.HEAD):
	head = pH.HEAD[0]

    pos = filename.rfind('.fits')
    file_id = filename[:pos]

    resFilename = file_id + ext
    try:
    	mimeType = ngamsPlugInApi.determineMimeType(srvObj.getCfg(),\
		 resFilename)
    except:
	if ext == '.xml': 
	    mimeType = 'text/xml'
	else:
	    mimeType = 'text/ascii'
	
    resObj = ngamsDppiStatus.ngamsDppiResult(NGAMS_PROC_DATA, mimeType,
                                             head, resFilename, '')
    statusObj.addResult(resObj)

    return statusObj


# EOF
