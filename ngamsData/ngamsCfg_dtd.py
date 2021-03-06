"""
<?xml version="1.0" encoding="UTF-8"?>
<!ENTITY % XmlStd SYSTEM "http://www.eso.org/projects/esoxml/XmlStd.dtd">
%XmlStd;
<!ENTITY % NgamsInternal SYSTEM "ngamsInternal.dtd">
%NgamsInternal;

<!--
     ALMA - Atacama Large Millimiter Array
     (c) European Southern Observatory, 2002
     Copyright by ESO (in the framework of the ALMA collaboration),
     All rights reserved
  
     This library is free software; you can redistribute it and/or
     modify it under the terms of the GNU Lesser General Public
     License as published by the Free Software Foundation; either
     version 2.1 of the License, or (at your option) any later version.
  
     This library is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
     Lesser General Public License for more details.
  
     You should have received a copy of the GNU Lesser General Public
     License along with this library; if not, write to the Free Software
     Foundation, Inc., 59 Temple Place, Suite 330, Boston,
     MA 02111-1307  USA
  
 -->

<!-- 
  "@(#) $Id: ngamsCfg.dtd,v 1.3 2008/08/19 20:51:50 jknudstr Exp $"

  Who        When        What
  ********   **********  ***************************************************
  jknudstr   04.04.2001  Created
  **************************************************************************
  ngamsCfgNau.dtd defines the contents and lay-out of the
  configuration file loaded by the NG/AMS Server at start-up.

  Consult the DTD ngamsInternal.dtd for further information. It contains the 
  actual definition of the elements of the NG/AMS Configuration.
  -->

<!-- 
  The NgamsCfg element is the root element of the NG/AMS
  Configuration for NG/AMS NAU Systems.
  -->
<!ELEMENT NgamsCfg (Header, 
                    (Ngams, Db, MimeTypes, StorageSet*,
                     Stream*, Processing, Register, FileHandling, Monitor, 
		     Log, Notification?, HostSuspension))>


<!-- EOF -->

"""

# EOF
