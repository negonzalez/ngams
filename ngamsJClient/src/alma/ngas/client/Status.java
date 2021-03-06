/*
 *   ALMA - Atacama Large Millimiter Array
 *   (c) European Southern Observatory, 2002
 *   Copyright by ESO (in the framework of the ALMA collaboration),
 *   All rights reserved
 *
 *   This library is free software; you can redistribute it and/or
 *   modify it under the terms of the GNU Lesser General Public
 *   License as published by the Free Software Foundation; either
 *   version 2.1 of the License, or (at your option) any later version.
 *
 *   This library is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *   Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public
 *   License along with this library; if not, write to the Free Software
 *   Foundation, Inc., 59 Temple Place, Suite 330, Boston,
 *   MA 02111-1307  USA
 *
 */

/******************************************************************************
 *
 * "@(#) $Id: Status.java,v 1.10 2012/05/25 11:21:06 amanning Exp $"
 * 
 * Who       When        What
 * --------  ----------  ------------------------------------------------------
 * F.Woolfe  2003        First version.
 * jknudstr  2007/06/20  Gave overhaul, included in ALMA NG/AMS Module.
 * apersson  2008-09-27  Removed a really weird and clumsy construction using String arrays.
 *
 *
 * Represents the status of a request to NGAS. When a command is sent to NGAS 
 * via the class JClient, an instance of this type is often returned. It 
 * represents the XML response from NGAS. Many of the fields and get methods 
 * are self-explanatory.
 */

package alma.ngas.client;

import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.util.HashMap;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.EntityResolver;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

public class Status {

    /*
     * Enum containing the attributes in the Status tag. Note that case of enum is important.
     */
    private enum StatusEnum {
        CompletionTime, Date, HostId, LastRequestStatUpdate, Message, RequestId, RequestTime, State, Status, SubState, Version;
    }

    /*
     * Enum containing the attributes in the DiskStatus tag. Note that case of enum is important.
     */
    private enum DiskStatusEnum {
        Archive, AvailableMb, BytesStored, Checksum, Completed, CompletionDate, DiskId, InstallationDate, LastCheck, LogicalName, Manufacturer, MountPoint, Mounted, NumberOfFiles, SlotId, TotalDiskWriteTime, Type;
    }

    /*
     * Enum containing the attributes in the FileStatus tag. Note that case of enum is important.
     */
    private enum FileStatusEnum {
        Checksum, ChecksumPlugIn, Compression, CreationDate, FileId, FileName, FileSize, FileStatus, FileVersion, Format, Ignore, IngestionDate, Tag, UncompressedFileSize;
    }

    /**
     * logger used for logging events.
     */
    private Logger logger;

    /**
     * Whether the request to NGAS was successful.
     */
    private boolean OK;

    /**
     * Whether a file was being received, due to a subscription, when this
     * object was created.
     */
    private boolean receivingFile;

    /**
     * The HTTP code number response of NGAS. Eg 200 for OK, 400 for bad
     * request, 406 for unacceptable etc.
     */
    private int httpCode;

    /**
     * The HTTP message returned by NGAS. If httpCode==200, this is OK for
     * example.
     */
    private String httpMsg;

    /**
     * Whole XML document returned by NGAS.
     */
    private String xml;

    /**
     * Additional message generated.
     */
    private String msg;

    /**
     * Map containing the attributes and their value of the Status tag.
     */
    private HashMap<String, String> statusMap = new HashMap<String, String>();

    /**
     * Map containing the attributes and their value of the DiskStatus tag.
     */
    private HashMap<String, String> diskStatusMap = new HashMap<String, String>();

    /**
     * Map containing the attributes and their value of the FileStatus tag.
     */
    private HashMap<String, String> fileStatusMap = new HashMap<String, String>();

    /**
     * Used internally for parsing the XML.
     */
    private Document xmlDoc = null;

    /**
     * 
     * @param OK
     *            Whether the request to NGAS was successful.
     */
    Status(boolean OK) {
        this.OK = OK;
    }

    /**
     * 
     * @param OK
     *            Whether request to NGAS was successful.
     * @param msg
     *            Message generated by JClient.
     */
    Status(boolean OK, String msg) {
        this.OK = OK;
        this.msg = msg;
    }

    /**
     * 
     * @param httpCode
     *            HTTP code number returned by NGAS. E.g. 200 for status OK.
     * @param httpMsg
     *            HTTP message returned by NGAS. E.g. OK.
     * @param xml
     *            XML returned by NGAS.
     * @param busy
     *            If
     * @param xmlFileName
     *            Filename for saving XML from NGAS to disk.
     */
    Status(int httpCode, String httpMsg, String xml, String xmlFileName,
            Logger logger) {
        this.logger = logger;
        this.httpCode = httpCode;
        this.httpMsg = httpMsg;
        this.OK = (httpCode == 200);
        this.xml = xml;
        parseXML();
    }

    /**
     * 
     * @param httpCode
     *            HTTP code number returned by NGAS. E.g. 200 for status OK.
     * @param httpMsg
     *            HTTP message returned by NGAS. E.g. OK.
     */
    Status(int httpCode, String httpMsg) {
        this.httpCode = httpCode;
        this.httpMsg = httpMsg;
        this.OK = (httpCode == 200);
    }

    /**
     * 
     * @param httpCode
     *            HTTP code number returned by NGAS. E.g. 200 for status OK.
     * @param httpMsg
     *            HTTP message returned by NGAS. E.g. OK.
     * @param xml
     *            XML returned by NGAS.
     * @param msg
     *            Message generated by JClient.
     * @param xmlFileName
     *            Filename for saving XML from NGAS to disk.
     */
    Status(int httpCode, String httpMsg, String xml, String msg,
            String xmlFileName, Logger logger) {
        this.logger = logger;
        this.httpCode = httpCode;
        this.httpMsg = httpMsg;
        this.xml = xml;
        parseXML();
        this.msg = msg;
        this.OK = (httpCode == 200);
    }

    /**
     * Get XML generated by NGAS.
     * 
     * @return The full XML document returned by NGAS in response to request
     *         made.
     */
    public String getXML() {
        return xml;
    }

    /**
     * Find whether the request made to NGAS was succesful.
     * 
     * @return Whether the request made to NGAS was succesful.
     */
    public boolean getOK() {
        return OK;
    }

    /**
     * Find HTTP code number returned by NGAS. E.g. 200 for OK.
     * 
     * @return HTTP code number returned by NGAS.
     */
    public int getHttpCode() {
        return httpCode;
    }

    /**
     * Find HTTP message returned by NGAS. E.g. OK.
     * 
     * @return HTTP message from NGAS.
     */
    public String getHttpMsg() {
        return httpMsg;
    }

    /**
     * Get message generated by JClient, giving additional information.
     * 
     * @return message from JClient.
     */
    public String getMsg() {
        return msg;
    }

    /**
     * Whether a file was being received from NGAS from a subscription. At the
     * time of instantiation of this.
     * 
     * @return Whether a file was being received
     */
    public boolean getReceivingFile() {
        return receivingFile;
    }

    /**
     * Get data from the status tag.
     */
    public String getCompletionTime() {
        return this.statusMap.get(StatusEnum.CompletionTime.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getDate() {
        return this.statusMap.get(StatusEnum.Date.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getHostId() {
        return this.statusMap.get(StatusEnum.HostId.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getLastRequestStatUpdate() {
        return this.statusMap.get(StatusEnum.LastRequestStatUpdate.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getMessage() {
        return this.statusMap.get(StatusEnum.Message.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getRequestId() {
        return this.statusMap.get(StatusEnum.RequestId.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getRequestTime() {
        return this.statusMap.get(StatusEnum.RequestTime.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getState() {
        return this.statusMap.get(StatusEnum.State.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getStatus() {
        return this.statusMap.get(StatusEnum.Status.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getSubState() {
        return this.statusMap.get(StatusEnum.SubState.toString());
    }

    /**
     * Get data from the status tag.
     */
    public String getVersion() {
        return this.statusMap.get(StatusEnum.Version.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getArchive() {
        return this.diskStatusMap.get(DiskStatusEnum.Archive.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getAvailableMb() {
        return this.diskStatusMap.get(DiskStatusEnum.AvailableMb.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getBytesStored() {
        return this.diskStatusMap.get(DiskStatusEnum.BytesStored.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getDiskChecksum() {
        return this.diskStatusMap.get(DiskStatusEnum.Checksum.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getCompleted() {
        return this.diskStatusMap.get(DiskStatusEnum.Completed.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getCompletionDate() {
        return this.diskStatusMap.get(DiskStatusEnum.CompletionDate.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getDiskId() {
        return this.diskStatusMap.get(DiskStatusEnum.DiskId.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getInstallationDate() {
        return this.diskStatusMap.get(DiskStatusEnum.InstallationDate.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getLastCheck() {
        return this.diskStatusMap.get(DiskStatusEnum.LastCheck.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getLogicalName() {
        return this.diskStatusMap.get(DiskStatusEnum.LogicalName.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getManufacturer() {
        return this.diskStatusMap.get(DiskStatusEnum.Manufacturer.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getMountPoint() {
        return this.diskStatusMap.get(DiskStatusEnum.MountPoint.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getMounted() {
        return this.diskStatusMap.get(DiskStatusEnum.Mounted.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getNumberOfFiles() {
        return this.diskStatusMap.get(DiskStatusEnum.NumberOfFiles.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getSlotId() {
        return this.diskStatusMap.get(DiskStatusEnum.SlotId.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getTotalDiskWriteTime() {
        return this.diskStatusMap.get(DiskStatusEnum.TotalDiskWriteTime.toString());
    }

    /**
     * Get data from the DiskStatus tag.
     */
    public String getType() {
        return this.diskStatusMap.get(DiskStatusEnum.Type.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileChecksum() {
        return this.fileStatusMap.get(FileStatusEnum.Checksum.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getChecksumPlugIn() {
        return this.fileStatusMap.get(FileStatusEnum.ChecksumPlugIn.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getCompression() {
        return this.fileStatusMap.get(FileStatusEnum.Compression.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getCreationDate() {
        return this.fileStatusMap.get(FileStatusEnum.CreationDate.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileId() {
        return this.fileStatusMap.get(FileStatusEnum.FileId.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileName() {
        return this.fileStatusMap.get(FileStatusEnum.FileName.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileSize() {
        return this.fileStatusMap.get(FileStatusEnum.FileSize.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileStatus() {
        return this.fileStatusMap.get(FileStatusEnum.FileStatus.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFileVersion() {
        return this.fileStatusMap.get(FileStatusEnum.FileVersion.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getFormat() {
        return this.fileStatusMap.get(FileStatusEnum.Format.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getIgnore() {
        return this.fileStatusMap.get(FileStatusEnum.Ignore.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getIngestionDate() {
        return this.fileStatusMap.get(FileStatusEnum.IngestionDate.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getTag() {
        return this.fileStatusMap.get(FileStatusEnum.Tag.toString());
    }

    /**
     * Get data from the FileStatus tag.
     */
    public String getUncompressedFileSize() {
        return this.fileStatusMap.get(FileStatusEnum.UncompressedFileSize.toString());
    }

    /**
     * Find status of request to NGAS. This returns information from the fields
     * OK, httpMsg and status.
     */
    public String getRequestStatus() {
        String status = (OK ? "Status is OK" : "Status is not OK");
        if (httpMsg != null)
            status += "\nHTTP code is " + httpCode + " & HTTP message is: "
                    + httpMsg;
        status += (msg == null || msg == "") ? "\nNo additional message."
                : ("\nAdditional message:\n" + msg);
        return status;
    }

    void setFileSize(String fileSize) {
	this.fileStatusMap.put(FileStatusEnum.FileSize.toString(), fileSize);
    }


    /**
     * Gets the values stored in the attributes of a specified XML tag in the
     * XML structure returned by NGAS. By default, if there are more than 1 tag
     * with this name, we look up the first one.
     * 
     * @param tagName
     *            name of tag
     * @param inAttrMap
     *            a HashMap with the keys being the attr names of interest. When
     *            this method returns the values of the map will contain the
     *            values found in the xml structure. This implies that the
     *            values can be set to <code>null</code> in the map when sent as
     *            in parameter.
     */
    public void getTagAttrs(String tagName, HashMap<String, String> inAttrMap) {
        getTagAttrs(tagName, 0, inAttrMap);
    }

    /**
     * Gets the values stored in the attributes of a specified XML tag in the
     * XML structure returned by NGAS. Allows user to specify which tag to look
     * at, if there are more that 1 with this name.
     * 
     * @param tagName
     *            Name of tag.
     * @param tagNumber
     *            Which tag with this name to look at.
     * @param inAttrMap
     *            a HashMap with the keys being the attr names of interest. When
     *            this method returns the values of the map will contain the
     *            values found in the xml structure. This implies that the
     *            values can be set to <code>null</code> in the map when sent as
     *            in parameter.
     */
    public void getTagAttrs(String tagName, int tagNumber,
            HashMap<String, String> inAttrMap) {
        try {
            if (xml == null || xml == "")
                throw new IllegalArgumentException(
                        "There is no XML to parse. Error generated by "
                                + "getTagAttr in Status.");
            NodeList list = xmlDoc.getElementsByTagName(tagName);
            if (list.getLength() <= tagNumber || tagNumber < 0) {
		// Holger: removed exception, results in behaviour too strict. TODO check this
		return;
                //throw new IllegalArgumentException("There are "
                //        + list.getLength() + " tags with name " + tagName
                //        + ". You refered to the tag with number " + tagNumber
                //        + ". Note that the first tag has number 0 etc.");
		}
            NamedNodeMap attrList = list.item(tagNumber).getAttributes();
            for (String attrName : inAttrMap.keySet()) {
                Node attr = attrList.getNamedItem(attrName);
                if (attr == null) {
		// Holger: removed exceptions here, since some attributes do not appear int
		// the status object returned byte NGAS. 
                    // throw new IllegalArgumentException("No " + attrName
		    //                          + " attribute in this tag. Error generated "
		    //      + "by getTagAttr in getTagAttr Status.");
		   inAttrMap.put(attrName, null);
		} else {
                   inAttrMap.put(attrName, attr.getNodeValue());
		}
            }
        } catch (Exception e) {
            logger.warning("Exception in Status.getTagAttr; message is: "
                    + e.getMessage());
            throw new IllegalArgumentException("Unexpected exception", e);
        }
    }

    /**
     * Parses the XML from NGAS. Parsed XML is put into an instance of Document
     */
    private void makeXmlDoc(String doc) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory
                    .newInstance();
            DocumentBuilder builder = factory.newDocumentBuilder();
            // prevent the parser from fetching the referenced DTDs from the server every time.
            // they are bundled locally instead, and we supply them via our own EntityResolver
            builder.setEntityResolver(new EntityResolver() {

				public InputSource resolveEntity(String publicId,
						String systemId) throws SAXException, IOException {
					if (logger.isLoggable(Level.FINE)) logger.fine("fetching entity. publicId: " + publicId + ", systemId: " + systemId);
					// typically the publicId is null and the systemId is a URL e.g.
					// http://ngas03
					int posOfEquals = systemId.lastIndexOf('=');
					InputStream localResourceStream = null;
					if (posOfEquals != -1) {
						String sourceName = '/' + systemId.substring(posOfEquals + 1);
						if (logger.isLoggable(Level.FINE)) logger.fine("looking locally for entity: " + sourceName);
						localResourceStream = Status.class.getResourceAsStream(sourceName);
					}
					
					InputSource inputSource = null;
					if (localResourceStream == null) logger.warning("no local resource found - asking the server: " + systemId);
					else inputSource = new InputSource(localResourceStream);

					return inputSource;
				}
            });
            StringReader strReader = new StringReader(doc);
            InputSource xmlInput = new InputSource(strReader);
            xmlDoc = builder.parse(xmlInput);
        } catch (Throwable e) {
            logger.severe("Exception in Status.makeXmlDoc; message is: "
                    + e);
            logger.severe("Original document was: \n"+doc);
            throw new IllegalArgumentException("Error when parsing doc", e);
        }
    }

    /**
     * Parses the XML from NGAS. Puts data into correct map.
     */
    private void parseXML() {
        // saveXML();
        makeXmlDoc(getXML());

        this.statusMap = new HashMap<String, String>();
        for (StatusEnum key : StatusEnum.class.getEnumConstants()) {
            this.statusMap.put(key.toString(), null);
        }
        getTagAttrs("Status", this.statusMap);

        this.diskStatusMap = new HashMap<String, String>();
        for (DiskStatusEnum key : DiskStatusEnum.class.getEnumConstants()) {
            this.diskStatusMap.put(key.toString(), null);
        }
        getTagAttrs("DiskStatus", this.diskStatusMap);

        this.fileStatusMap = new HashMap<String, String>();
        for (FileStatusEnum key : FileStatusEnum.class.getEnumConstants()) {
            this.fileStatusMap.put(key.toString(), null);
        }
        getTagAttrs("FileStatus", this.fileStatusMap);
    }

}

// EOF
