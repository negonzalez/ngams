"""
<?xml version="1.0" encoding="UTF-8"?>  

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
   XML Standards Project - Standard XML Header Element

   "@(#) $Id: XmlStd.dtd,v 1.3 2008/08/19 20:51:50 jknudstr Exp $" 

   Who        When        What
   *********  **********  ***************************************************
   jknudstr   01/01/2000  Created.
   jknudstr/
   kzagar     28/02/2001  Changed status to enumurated list.

   **************************************************************************

   Following people have contributed to the definition of the 
   LOGML Schema Language:

      o Miguel Albrecht,  - - - - - - - -,    European Southern Observatory.
      o Gianluca Chiozzi, gchiozzi@eso.org,    European Southern Observatory.
      o Preben Grosbol,   pgrosbol@eso.org,    European Southern Observatory.
      o Jens Knudstrup,   jknudstr@eso.org,    European Southern Observatory.
      o Klemen Zagar,     klemen.zagar@ijs.si, Jozef Stefan Institute.
      o Andreas Wicenec,  awicenec@eso.org,    European Southern Observatory.

   **************************************************************************

   The attributes are as follows:

       Name:      A name for the XML document.

       Type:      Type of this XML document. Could e.g. be "LOGFILE" or "PAF".

       Context:   The context in which the document is used.

       Release:   A version number, e.g. "1.2" indicating the version of the
                  syntax of the XML document.

       Uri:       Location of oficial reference of this document, if this
                  document is a copy.

       Source:    The source (origin) of the document.

       Revision:  The revision string as used e.g. by RCS.
   -->
  <!ELEMENT Header (Description?, History*, Meta*)>
  <!ATTLIST Header Name      CDATA   #REQUIRED
                   Type      CDATA   #REQUIRED
                   Context   CDATA   #IMPLIED
                   Release   CDATA   #IMPLIED
                   Uri       CDATA   #IMPLIED              
                   Source    CDATA   #IMPLIED
                   Revision  CDATA   #IMPLIED>
  <!ELEMENT Description (#PCDATA)>
  <!ELEMENT History  (#PCDATA)>
  <!ATTLIST History  User     CDATA #REQUIRED
                     Date     CDATA #REQUIRED
                     Status   (draft|reviewed|released|obsolete) #REQUIRED>

  <!-- The Meta (tag) Element is used to define special tags used for e.g. 
       browsing and classifying XML documents. -->
  <!ELEMENT Meta (#PCDATA)>
  <!ATTLIST Meta Name     CDATA #REQUIRED
                 Content  CDATA #REQUIRED>


<!-- EOF -->

"""

# EOF
