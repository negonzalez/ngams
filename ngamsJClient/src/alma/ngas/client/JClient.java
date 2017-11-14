/*******************************************************************************
 * ALMA - Atacama Large Millimeter Array
 * Copyright (c) ESO - European Southern Observatory, 2011
 * (in the framework of the ALMA collaboration).
 * All rights reserved.
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 * 
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
 *******************************************************************************/
/*******************************************************************************
 * ESO/ALMA
 *
 * "@(#) $Id: JClient.java,v 1.14 2011/11/24 13:06:42 amanning Exp $"
 * 
 * Who       When        What
 * --------  ----------  -------------------------------------------------------
 * F.Woolfe  2003        First version together with S.Zampieri/ESO/DFS.
 * jknudstr  2007/06/20  Gave overhaul, included in ALMA NG/AMS Module.
 * apersson  2008-09-27  Removed a really weird and clumsy construction using String arrays.
 *
 * For communicating with NGAS; allows you to specify commands. These
 * are sent using HTTP and an instance of {@link Status} is returned
 * which represents the response from NGAS.
 */
package alma.ngas.client;

import java.io.BufferedReader;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

public class JClient {
	/**
	 * The number of bytes sent / retrieved at a time during data transfers.
	 */
	private final static int BLOCK_SIZE = 1024;

	// Dummy dppi to be used when a dppi parameter is required even if no
	// processing is needed
	public static final Dppi DUMMY_DPPI = new Dppi("", "");

	/**
	 * The port that the miniServer uses to listen for files coming from NGAS.
	 */
	private final int miniServerPort;

	/**
	 * True if and only if localUrl is subscribed to NGAMS.
	 */
	private boolean subscribed = false;

	/**
	 * When a subscribe command is sent a {@link MiniServer} is created and
	 * launched in a new thread; this then listens for HTTP ARCHIVE requests
	 * coming from NGAS.
	 */
	private static MiniServer miniServer;

	/**
	 * JClient uses log4j; this logger logs events.
	 */
	public Logger logger;

	/**
	 * The url to which JClient wants to subscribe.
	 */
	public String url;

	/**
	 * The path where incoming files are stored.
	 */
	private String dataRaw;

	private ConnectionManager myConnectionManager = new ConnectionManager();

	private String myProcessing;

	private String myProcessingParameters;

	// private Map<String, Double> connectTimes = new HashMap<String, Double>();

	/**
	 * 
	 * @param inConnectionList
	 *            List containing InetSocketAddress objects pointing to all NGAS
	 *            servers that can be accessed by the client.
	 * @param inMiniServerPort
	 *            The local port number on which to set up a miniServer (used
	 *            only for subscribe)
	 * @param inDataRaw
	 *            The directory to put incoming file in
	 * @param inURL
	 *            The url to which NGAMS will send files, if we subscribe; if
	 *            this is null it is taken to be the local URL by default
	 * @param inLogger
	 *            The log4j logger to log events with (must be properly set up
	 *            before passing it to JClient).
	 */
	public JClient(List<InetSocketAddress> inConnectionList,
			int inMiniServerPort, String inDataRaw, String inURL,
			Logger inLogger) {
		this.logger = inLogger;
		this.myConnectionManager.setConnectionList(inConnectionList);
		this.miniServerPort = inMiniServerPort;
		this.dataRaw = inDataRaw;
		// If the localUrl is given as null, take the local address as default.
		try {
			if (inURL == null)
				inURL = InetAddress.getLocalHost().getCanonicalHostName();
		} catch (UnknownHostException e) {
			String msg = "The parameter URL to the constructor JClient was "
					+ "specified as null. This means the constructor attempts to "
					+ "find the URL of the local machine using the method "
					+ "InetAddress.getLocalHost().getCanonicalHostName(). Note "
					+ "that JClient needs the URL of the local machine for "
					+ "handling SUBSCRIBE commands. In this case a miniServer "
					+ "object is set up by JClient in order to listen for files "
					+ "HTTP POST command. An error occured while trying to find "
					+ "the URL of the local machine. The exception message is: "
					+ e.getMessage();
			logger.severe(msg);
		}
		this.url = "http://" + inURL + ":" + inMiniServerPort + "/ARCHIVE";
	}

	/**
	 * 
	 * @param inConnectionList
	 *            List containing InetSocketAddress objects pointing to all NGAS
	 *            servers that can be accessed by the client.
	 * @param inMiniServerPort
	 *            The local port number on which to set up a miniServer (used
	 *            only for subscribe)
	 * @param inDataRaw
	 *            The directory to put incoming file in
	 * @param inURL
	 *            The url to which NGAMS will send files, if we subscribe; if
	 *            this is null it is taken to be the local URL by default
	 * @param inLogger
	 *            The log4j logger to log events with (must be properly set up
	 *            before passing it to JClient).
	 * @param timeOut
	 *            ngas node connection and read timeout (expressed in seconds)
	 */
	public JClient(List<InetSocketAddress> inConnectionList,
			int inMiniServerPort, String inDataRaw, String inURL,
			Logger inLogger, int timeOut) {
		this(inConnectionList, inMiniServerPort, inDataRaw, inURL, inLogger);
		this.myConnectionManager.setTimeOut(timeOut);
	}

	/**
	 * 
	 * @param inConnectionList
	 *            List containing InetSocketAddress objects pointing to all NGAS
	 *            servers that can be accessed by the client.
	 * @param inLogger
	 *            The log4j logger to log events with (must be properly set up
	 *            before passing it to JClient).
	 */
	public JClient(List<InetSocketAddress> inConnectionList, Logger inLogger) {
		if (inConnectionList.isEmpty()) {
			throw new IllegalArgumentException(
					"The supplied connection list may not be empty.");
		}
		this.myConnectionManager.setConnectionList(inConnectionList);
		this.logger = inLogger;
		this.miniServerPort = -1;
	}

	/**
	 * 
	 * @param inConnectionList
	 *            List containing InetSocketAddress objects pointing to all NGAS
	 *            servers that can be accessed by the client.
	 * @param inLogger
	 *            The log4j logger to log events with (must be properly set up
	 *            before passing it to JClient).
	 * @param timeOut
	 *            ngas node connection and read timeout (expressed in seconds)
	 */
	public JClient(List<InetSocketAddress> inConnectionList, Logger inLogger,
			int timeOut) {
		this(inConnectionList, inLogger);
		this.myConnectionManager.setTimeOut(timeOut);
	}

	/**
	 * Called by the public archive methods. Contains the code that actually
	 * connects to NGAS.
	 * 
	 * @param filename
	 *            The name of the file to archive.
	 * @param contentType
	 *            The mime type of the file to archive.
	 * @param noVersioning
	 *            Used to deal with the possibility of many files with the same
	 *            ID. Please see NGAMS users manual.
	 * @param parameters
	 *            Additional parameters passed to the archiving plugin
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	private Status _archive(String filename, String contentType,
			String noVersioning, Map<String, String> parameters) {
		try {
			File myFile = new File(filename);
			long filesize = myFile.length();
			String basename = myFile.getName();
			String command = prepareCommand("ARCHIVE",
					Collections.<String, String> emptyMap(), null);
			HttpURLConnection con = myConnectionManager.post(command,
					contentType, basename, filesize, noVersioning, parameters);
			DataInputStream in = new DataInputStream(
					new FileInputStream(myFile));
			writeContent(in, con.getOutputStream());
			return getStatus(con);
		} catch (IOException e) {
			e.printStackTrace();
			logger.warning("IOException in JClient._archive. Please see "
					+ "instance of Status returned for more details");
			return new Status(false, "Error generated by myArchive in "
					+ "JClient. Description:\n" + e.toString());
		}
	}

	/**
	 * 
	 * @param con
	 * @return
	 * @throws IOException
	 */
	private Status getStatus(HttpURLConnection con) throws IOException {
		int code = con.getResponseCode();
		String msg = con.getResponseMessage();
		BufferedReader reader = null;
		// If there's a problem, log it!
		if (code != 200)
			logger.warning("NGAS returned HTTP code: " + code
					+ " in response to archive request, in "
					+ "JClient.myArchive. Please see instance of "
					+ "Status returned for more information.");
		reader = new BufferedReader(new InputStreamReader(
				(code == 200) ? con.getInputStream() : con.getErrorStream()));
		String xml = "";
		String line = null;
		while ((line = reader.readLine()) != null)
			xml = xml + line + "\n";
		reader.close();
		con.disconnect();
		return new Status(code, msg, xml, dataRaw + "ngams.xml", logger);
	}

	/**
	 * Called by the public archiveStream method. Contains the code that
	 * actually connects to NGAS.
	 * 
	 * Holger Meuss: this method is a modified version of
	 * 
	 * @see _archive.
	 * 
	 * @param inStream
	 *            The data stream to archive.
	 * @param content_type
	 *            The mime-type of the data to archive
	 * @param filename
	 *            The name.
	 * @param noVersioning
	 *            used to deal with the possibility of many files with the same
	 *            id. Please see NGAMS users manual.
	 * @return Object representing the response of NGAMS to the command sent.
	 * 
	 *         In fact, the filename parameter is mainly ignored. The file is
	 *         stored under the name provided in the MIME header of the digested
	 *         stream.
	 */
	private Status _ArchiveStream(InputStream inStream, String contentType,
			String filename, String noVersioning) {
		HttpURLConnection con = null;
		try {
			// long start = System.currentTimeMillis();
			String command = prepareCommand("ARCHIVE",
					Collections.<String, String> emptyMap(), null);
			con = myConnectionManager.post(command, contentType, filename, -1L,
					noVersioning, Collections.<String, String> emptyMap());
			// this.connectTimes.put(Thread.currentThread().getName(),
			// ((System.currentTimeMillis() - start) / 1000.0));
			writeContent(new DataInputStream(inStream), con.getOutputStream());
			return getStatus(con);
		} catch (IOException e) {
			StringWriter sw = new StringWriter();
			PrintWriter pw = new PrintWriter(sw);
			e.printStackTrace(pw);
			logger.warning("IOException in JClient._ArchiveStream. "
					+ sw.toString());
			return new Status(false, "Error generated by myArchive in "
					+ "JClient. Description:\n" + e.toString());
		} finally {
			if (con != null)
				con.disconnect();
		}
	}

	/**
	 * 
	 * @param inStream
	 * @param con
	 * @throws IOException
	 */
	private void writeContent(InputStream in, OutputStream outputStream)
			throws IOException {
		DataOutputStream out = new DataOutputStream(outputStream);
		try {
			byte[] buf = new byte[BLOCK_SIZE];
			int nRead = 0;
			while ((nRead = in.read(buf, 0, BLOCK_SIZE)) > 0) {
				out.write(buf, 0, nRead);
				out.flush();
			}
		} finally {
			if (in != null)
				try {
					in.close();
				} catch (IOException e) {
					logger.warning(e.getMessage());
				}
			if (out != null)
				try {
					out.close();
				} catch (IOException e) {
					logger.warning(e.getMessage());
				}
		}
	}

	/**
	 * Retrieve a file. This is called by all the public retrieve methods. It
	 * contains code for connecting to NGAS.
	 * 
	 * @param cmd
	 *            The command to send.
	 * @param fileNameDestination
	 *            The name for the file when it reaches your computer.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	private Status _Retrieve(String cmd, String fileNameDestination) {
		try {
			HttpURLConnection con = this.myConnectionManager.get(cmd);
			int code = con.getResponseCode();
			String msg = con.getResponseMessage();
			if (code != 200) { // Error handling here: HTTP says all is not OK
				String xml = "";
				BufferedReader reader = null;
				reader = new BufferedReader(new InputStreamReader(
						con.getErrorStream()));
				String line = null;
				while ((line = reader.readLine()) != null) {
					xml = xml + line + "\n";
				}

				reader.close();
				// Log an error message.
				String logMsg = "Error when attempting to send a retrieve "
						+ "command:\n" + cmd
						+ " to NGAS. For further information, "
						+ "consult the instance of Status returned.";
				logger.warning(logMsg);
				return new Status(code, msg, xml, dataRaw + "ngams.xml", logger);
			}

			// Create objects to read data from the socket and store it in
			// a file.
			File fileDestination = new File(fileNameDestination);
			DataInputStream in = new DataInputStream(con.getInputStream());
			DataOutputStream out = new DataOutputStream(new FileOutputStream(
					fileDestination));
			byte[] buf = new byte[BLOCK_SIZE];
			int nRead = 0;
			while ((nRead = in.read(buf, 0, BLOCK_SIZE)) > 0) {
				// System.out.println("Read " + totRead + " bytes");
				out.write(buf, 0, nRead);
				out.flush();
			}
			in.close();
			out.close();
			code = con.getResponseCode();
			msg = con.getResponseMessage();
			con.disconnect();
			// Log a message.
			logger.info("Sent retrieve message to NGAMS: " + cmd);
			return new Status(code, msg);
		} catch (IOException e) {
			logger.warning("IOException sending retrieve command to NGAS. "
					+ "Tried to send command: " + cmd);
			return new Status(false, "Error generated by _Retrieve in "
					+ "JClient. Description:\n" + e.toString());
		}
	}

	/**
	 * Retrieve a file. This is called by all the public retrieve methods. It
	 * contains code for connecting to NGAS.
	 * 
	 * @param cmd
	 *            The command to send.
	 * @param fileNameDestination
	 *            The name for the file when it reaches your computer.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	private Status _RetrieveStream(String cmd, OutputStream outStream) {
		return _RetrieveStream(cmd, outStream, true);
	}

	/**
	 * Retrieve a file. This is called by all the public retrieve methods. It
	 * contains code for connecting to NGAS.
	 * 
	 * @param cmd
	 *            The command to send.
	 * @param fileNameDestination
	 *            The name for the file when it reaches your computer.
	 * @param closeOutputStream
	 *            If true closes the given outputStream
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	private Status _RetrieveStream(String cmd, OutputStream outStream,
			boolean closeOutputStream) {
		HttpURLConnection con = null;
		try {
			con = this.myConnectionManager.get(cmd);
			logger.info("Sent retrieve message to NGAMS: " + cmd);
			int code = con.getResponseCode();
			String msg = con.getResponseMessage();
			if (code != 200) { // Error handling here: HTTP says all is not OK
				String xml = "";
				BufferedReader reader = null;
				reader = new BufferedReader(new InputStreamReader(
						con.getErrorStream()));
				String line = null;
				while ((line = reader.readLine()) != null) {
					xml = xml + line + "\n";
				}
				reader.close();
				// Log an error message.
				String logMsg = "Error when attempting to send a retrieve "
						+ "command:\n" + cmd
						+ " to NGAS. For further information, "
						+ "consult the instance of Status returned.";
				logger.warning(logMsg);
				return new Status(code, msg, xml, dataRaw + "ngams.xml", logger);
			}
			DataInputStream in = new DataInputStream(con.getInputStream());
			DataOutputStream out = new DataOutputStream(outStream);
			String contentLength = con.getHeaderField("content-length");

			byte[] buf = new byte[BLOCK_SIZE];
			int nRead = 0;
			while ((nRead = in.read(buf, 0, BLOCK_SIZE)) > 0) {
				// System.out.println("Read " + totRead + " bytes");
				out.write(buf, 0, nRead);
				out.flush();
			}
			in.close();

			if (closeOutputStream) {
				out.close();
			}

			code = con.getResponseCode();
			msg = con.getResponseMessage();
			Status status = new Status(code, msg);
			status.setFileSize(contentLength);
			return status;
		} catch (IOException e) {
			StringWriter sw = new StringWriter();
			PrintWriter pw = new PrintWriter(sw);
			e.printStackTrace(pw);
			logger.warning("failed during NGAS command: " + cmd + ": "
					+ sw.toString());
			return new Status(false, "Error generated by _Retrieve in "
					+ "JClient. Description:\n" + e.toString());
		} finally {
			if (con != null)
				con.disconnect();
		}
	}

	/**
	 * Request notification of file arrival from subscription. Note that the
	 * number sent to event listeners is the number of files received SO FAR in
	 * this session. Thus when the first file arrives it will be 1, when the
	 * second file arrives it will be 2 etc. A session is the lifetime of the
	 * thread holding the miniserver object and corresponds to a single
	 * SUBSCRIBE command.
	 * 
	 * @param e
	 *            Listener to notify when files arrive.
	 * @return False if there is no subscription at present; true if request is
	 *         succesful.
	 */
	public boolean addFileReceivedEventListener(FileReceivedEventListener e) {
		if (miniServer == null) {
			logger.warning("addFileReceivedEventListener failed to add a "
					+ "listener since miniServer == null. Call "
					+ "subscribe to initialise miniServer.");
			return false;
		}
		if (!miniServer.listOfFileReceivedEventListeners.add(e)) {
			logger.warning("Error adding FileReceivedEventListener()");
			return false;
		}
		logger.info("Added FileReceivedEventListener");
		return true;
	}

	/**
	 * Archive a file. The content type is guessed based on the file extension.
	 * no_versioning is given the default value true.
	 * 
	 * @param filename
	 *            File to archive.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status archive(String filename) {
		return archive(filename, null, true, null);
	}

	/**
	 * Archives a file. Parameter no_versioning is given the default value true.
	 * 
	 * @param filename
	 *            File to archive.
	 * @param content_type
	 *            mime type of file
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status archive(String filename, String contentType) {
		return archive(filename, contentType, true, null);
	}

	/**
	 * Archive a file.
	 * 
	 * @param filename
	 *            Name of file to archive.
	 * @param contentType
	 *            Mime-type of file to archive (guessed from extension if
	 *            contentType is null)
	 * @param noVersioning
	 *            Used to deal with the possibility of many files with the same
	 *            id. Please see NGAMS users manual.
	 * @return Object representing the response of NGAMS to the command sent
	 */
	public Status archive(String filename, String contentType,
			boolean noVersioning) {
		return _archive(filename, contentType, noVersioning ? "1" : "0", null);
	}

	/**
	 * Archive a file.
	 * 
	 * @param filename
	 *            Name of file to archive.
	 * @param contentType
	 *            Mime-type of file to archive (guessed from extension if
	 *            contentType is null)
	 * @param noVersioning
	 *            Used to deal with the possibility of many files with the same
	 *            id. Please see NGAMS users manual.
	 * @param parameters
	 *            Additional parameters passed to the archiving plugin
	 * @return Object representing the response of NGAMS to the command sent
	 */
	public Status archive(String filename, String contentType,
			boolean noVersioning, Map<String, String> parameters) {
		File check = new File(filename);
		if (!check.exists()) {
			logger.warning("Errror: the file you wish to send does not exist "
					+ "on your system. Error generated by archive in "
					+ "JClient.");
			return new Status(false, "Errror: the file you wish to send does "
					+ "not exist on your system. Error generated by "
					+ "archive in JClient.");
		}
		if (contentType == null) {
			String msg = "Error: No content type specified.";
			logger.warning(msg);
			return new Status(false, msg);
		}
		return _archive(filename, contentType, noVersioning ? "1" : "0",
				parameters);
	}

	/**
	 * Archives a stream. Parameter no_versioning is given the default value
	 * true (i.e. "1").
	 * 
	 * @param in
	 *            Stream to archive
	 * @param contentType
	 *            Mime-type of stream.
	 * @param filename
	 *            The name (in our case uid, e.g. X0123456789abcdef:X01234567)
	 *            of the file to be archived
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status archiveStream(InputStream in, String contentType,
			String filename) {
		return _ArchiveStream(in, contentType, filename, "1");
	}

	/**
	 * Sends CLONE command to NGAMS.
	 * 
	 * @param fileId
	 *            The File ID of the file to clone.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status clone(String fileId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		return sendSimpleCmd("CLONE", parameterMap);
	}

	/**
	 * Sends CLONE command to NGAMS.
	 * 
	 * @param diskId
	 *            The disk holding the file to clone.
	 * @param fileId
	 *            The file to clone.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status clone(String diskId, String fileId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		parameterMap.put("file_id", fileId);
		return sendSimpleCmd("CLONE", parameterMap);
	}

	/**
	 * Sends CLONE command to NGAMS. Any parameters specified passed with value
	 * null are omitted from the string sent to NGAS.
	 * 
	 * @param diskId
	 *            The disk holding the file to clone.
	 * @param fileId
	 *            The file to clone.
	 * @param fileVersion
	 *            The version of the file to clone.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status clone(String diskId, String fileId, String fileVersion) {
		if (diskId == null && fileId == null)
			return new Status(false, "This combination of arguments is "
					+ "illegal, when calling the CLONE command. At "
					+ "least one of disk_id and file_id must be "
					+ "specified. Error generated by clone in " + "JClient.");
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		return sendSimpleCmd("CLONE", parameterMap);
	}

	/**
	 * Find the configuration used by the NGAMS server.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status configStatus() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("configuration_file", null);
		return sendSimpleCmd("STATUS", parameterMap);
	}

	/**
	 * Find the status of a particular disk.
	 * 
	 * @param diskId
	 *            The Disk ID.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status diskStatus(String diskId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		return sendSimpleCmd("STATUS", parameterMap);
	}

	/**
	 * Sends EXIT command to NGAMS.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status exit() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		return sendSimpleCmd("EXIT", parameterMap);
	}

	/**
	 * Find the status of a particular file.
	 * 
	 * @param fileId
	 *            The File ID.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status fileStatus(String fileId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		return sendSimpleCmd("STATUS", parameterMap);
	}

	/**
	 * Tell NGAMS to flush logs it may have cached internally into an internal
	 * log file.
	 * 
	 * @return Status object representing the response from NGAMS.
	 */
	public Status flushLog() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("flush_log", null);
		return sendSimpleCmd("STATUS", parameterMap);
	}

	/**
	 * Whether miniserver is now receiving a file. When a subscribe command
	 * executed, a miniserver is launched on your machine. This listens for
	 * incoming files from NGAS. This tests whether miniserver is in the process
	 * of saving a file to disk. If it is and the application that instantiated
	 * JClient quits the process will be interrupted and problems may result.
	 * 
	 * @return whether miniserver is now taking a file
	 */
	public boolean getMiniServerTakingFile() {
		if (miniServer != null)
			return miniServer.takingFile;
		else
			return false;
	}

	/**
	 * Sends INIT command to NGAMS.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status init() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		return sendSimpleCmd("INIT", parameterMap);
	}

	/**
	 * Sends a LABEL command to NGAMS.
	 * 
	 * @param slotId
	 *            The Slot ID of the disk to label.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status label(String slotId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("slot_id", slotId);
		return sendSimpleCmd("LABEL", parameterMap);
	}

	/**
	 * Sends a LABEL command to NGAMS (used if you want to label a disk on a
	 * host other than the host in ngamsHost field of this object).
	 * 
	 * @param slotId
	 *            The slot containing the disk to label.
	 * @param hostId
	 *            The host with that disk on it.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status label(String slotId, String hostId) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("slot_id", slotId);
		parameterMap.put("host_id", hostId);
		return sendSimpleCmd("LABEL", parameterMap);
	}

	/**
	 * Sends OFFLINE command to NGAMS.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status offline() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		return sendSimpleCmd("OFFLINE", parameterMap);
	}

	/**
	 * Forces NGAMS to go Offline even if it is in the middle of an operation -
	 * USE WITH CARE.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status offlineForce() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("force", null);
		return sendSimpleCmd("OFFLINE", parameterMap);
	}

	/**
	 * Sends ONLINE command to NGAMS.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status online() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		return sendSimpleCmd("ONLINE", parameterMap);
	}

	/**
	 * Formats a command to send to NGAS. Commands accepted by ngas may have
	 * parameters. Some of these parameters take values, others do not. A
	 * command to send to NGAS is represented internally by a map of parameters
	 * and their values. If the command should have no parameters then an empty
	 * map should be provided. If the value for a key in the map is
	 * <code>null</code>, this is assumed to be a parameter taking no value.
	 * This method puts the command into the correct HTTP form. '?' separates
	 * the command name from the parameter list. '&' is used to separate
	 * parameters from each other. '=' is used to specify the value of a
	 * parameter.
	 * 
	 * @param inCommand
	 *            Command name e.g. "SUBSCRIBE".
	 * @param inParameterMap
	 *            The parameter map to give to the command.
	 * @param dppi
	 *            Data Processing plug-in, null if not needed
	 * 
	 * @return a String being a URL in a form recognizable by NGAS.
	 */
	private String prepareCommand(String inCommand,
			Map<String, String> inParameterMap, Dppi dppi) {
		StringBuilder builder = new StringBuilder(inCommand);
		if (inParameterMap.size() > 0) {
			builder.append("?");
			for (String key : inParameterMap.keySet()) {
				String value = inParameterMap.get(key);
				builder.append(key);
				if (value != null) {
					builder.append("=");
					builder.append(value);
				}
				builder.append("&");
			}
			// remove last &
			builder.setLength(builder.length() - 1);
		}

		// Two ways to speficify a dppi: as a parameter passed to the method or
		// as a data member. Parameters have the precedency
		String processing = ((dppi != null && !dppi.name.isEmpty()) ? dppi.name
				: this.myProcessing);
		String processingParameters = ((dppi != null && !dppi.parameters
				.isEmpty()) ? dppi.parameters : this.myProcessingParameters);
		if ((processing != null) && !processing.isEmpty()) {
			builder.append("&processing=");
			builder.append(processing);
			this.myProcessing = null;
		}
		if ((processingParameters != null) && !processingParameters.isEmpty()) {
			builder.append("&processing_pars=");
			builder.append(processingParameters);
			this.myProcessingParameters = null;
		}
		return builder.toString();
	}

	/**
	 * Register existing files on a disk.
	 * 
	 * @param path
	 *            The starting path under which ngams will look for files to
	 *            register.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status register(String path) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("path", path);
		return sendSimpleCmd("REGISTER", parameterMap);
	}

	/**
	 * Register existing files on a disk.
	 * 
	 * @param path
	 *            the starting path under which ngams will look for files to
	 *            register.
	 * @param mime
	 *            Comma separated list of mime-types to take into account, files
	 *            with different mime-types will be ignored.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status register(String path, String mime) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("path", path);
		parameterMap.put("mime_type", mime);
		return sendSimpleCmd("REGISTER", parameterMap);
	}

	/**
	 * Remove information about entire disks - USE WITH CARE.
	 * 
	 * @param diskId
	 *            The disk to remove information about
	 * @param execute
	 *            If this is false no information is deleted; a report is
	 *            returned saying what information would be deleted if execute
	 *            were true
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status remdisk(String diskId, boolean execute) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		parameterMap.put("execute", execute ? "1" : "0");
		return sendSimpleCmd("REMDISK", parameterMap);
	}

	/**
	 * Delete a file.
	 * 
	 * @param fileId
	 *            the file to delete
	 * @param execute
	 *            execute if false no files are actually removed; a report is
	 *            returned saying what information would be removed if execute
	 *            were true.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status remfile(String fileId, boolean execute) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("execute", execute ? "1" : "0");
		return sendSimpleCmd("REMFILE", parameterMap);
	}

	/**
	 * Delete file on a certain disk.
	 * 
	 * @param diskId
	 *            The disk on which the file to delete is stored.
	 * @param fileId
	 *            The file to delete.
	 * @param execute
	 *            If false no files are actually removed; a report is returned
	 *            saying what information would be removed if execute were true.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status remfile(String diskId, String fileId, boolean execute) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		parameterMap.put("file_id", fileId);
		parameterMap.put("execute", execute ? "1" : "0");
		return sendSimpleCmd("REMFILE", parameterMap);
	}

	/**
	 * Delete files; some parameters are optional; please see the NGAMS manual.
	 * Optional parameters may be omitted by giving them the value null.
	 * 
	 * @param diskId
	 *            The Disk ID.
	 * @param fileId
	 *            The File ID.
	 * @param fileVersion
	 *            The File Version.
	 * @param execute
	 *            If false no files are actually removed; a report is returned
	 *            saying what information would be removed if execute were true.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status remfile(String diskId, String fileId, String fileVersion,
			boolean execute) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("disk_id", diskId);
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		parameterMap.put("execute", execute ? "1" : "0");
		return sendSimpleCmd("REMFILE", parameterMap);
	}

	/**
	 * Cease notification of file arrival from subscription.
	 * 
	 * @param e
	 *            listener who is, as of now, not to be notified of file arrival
	 *            from subscription.
	 * @return false if there is no subscription at present. True is request is
	 *         succesfull or if e is not currently receiving notification of
	 *         file arrival from subscription. False if there is no subscription
	 *         at current time.
	 */
	public boolean removeFileReceivedEventListener(FileReceivedEventListener e) {
		if (miniServer == null) {
			logger.warning("removeFileReceivedEventListener failed to "
					+ "remove a listener since miniServer == null. "
					+ "Call subscribe to initialise miniServer.");
			return false;
		}
		miniServer.listOfFileReceivedEventListeners.removeElement(e);
		logger.info("removed FileReceivedEventListener");
		return true;
	}

	/**
	 * Retrieve a file.
	 * 
	 * @param fileId
	 *            the file id of the file to retrieve
	 * @param fileNameDestination
	 *            the file name to give the file on your system
	 * @param dppi
	 *            Data Processing plug-in, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileNameDestination, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _Retrieve(cmd, fileNameDestination);
	}

	/**
	 * Retrieve a file.
	 * 
	 * @param fileId
	 *            the file id of the file to retrieve
	 * @param fileNameDestination
	 *            the file name to give the file on your system
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileNameDestination) {
		return retrieve(fileId, fileNameDestination, DUMMY_DPPI);
	}

	/**
	 * Retrieve a file.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param fileVersion
	 *            The version of the file to retrieve.
	 * @param fileNameDestination
	 *            The name to give the file on your computer.
	 * @param dppi
	 *            Data Processing plug-in, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileVersion,
			String fileNameDestination, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _Retrieve(cmd, fileNameDestination);
	}

	/**
	 * Retrieve a file.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param fileVersion
	 *            The version of the file to retrieve.
	 * @param fileNameDestination
	 *            The name to give the file on your computer.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileVersion,
			String fileNameDestination) {
		return retrieve(fileId, fileVersion, fileNameDestination, DUMMY_DPPI);
	}

	/**
	 * Retrieve a file. Parameters that are given the value null are omitted
	 * from the final string sent to NGAS.
	 * 
	 * @param fileId
	 *            the file id of the file to get.
	 * @param fileVersion
	 *            the version of the file to get.
	 * @param internal
	 *            whether the file is internal or not.
	 * @param fileNameDestination
	 *            the name to give the file on your system.
	 * @param dppi
	 *            Data Processing plug-in, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileVersion, String internal,
			String fileNameDestination, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		parameterMap.put("internal", internal);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _Retrieve(cmd, fileNameDestination);
	}

	/**
	 * Retrieve a file. Parameters that are given the value null are omitted
	 * from the final string sent to NGAS.
	 * 
	 * @param fileId
	 *            the file id of the file to get.
	 * @param fileVersion
	 *            the version of the file to get.
	 * @param internal
	 *            whether the file is internal or not.
	 * @param fileNameDestination
	 *            the name to give the file on your system.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieve(String fileId, String fileVersion, String internal,
			String fileNameDestination) {
		return retrieve(fileId, fileVersion, internal, fileNameDestination,
				DUMMY_DPPI);

	}

	/**
	 * Retrieve an internal file. Could be a log definition file for example.
	 * 
	 * @param fileId
	 *            The id of the file to get.
	 * @param filename
	 *            The name of the file to get.
	 * @param fileNameDestination
	 *            the name to give the file on your computer
	 * @param dppi
	 *            Data Processing plug-in, null if not needed
	 * @return object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveInternal(String fileId, String filename,
			String fileNameDestination, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("internal", filename);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _Retrieve(cmd, fileNameDestination);
	}

	/**
	 * Retrieve an internal file. Could be a log definition file for example.
	 * 
	 * @param fileId
	 *            The id of the file to get.
	 * @param filename
	 *            The name of the file to get.
	 * @param fileNameDestination
	 *            the name to give the file on your computer
	 * 
	 * @return object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveInternal(String fileId, String filename,
			String fileNameDestination) {
		return retrieveInternal(fileId, filename, fileNameDestination,
				DUMMY_DPPI);

	}

	/**
	 * Retrieve a log file.
	 * 
	 * @param fileId
	 *            the id of the file to get.
	 * @param fileNameDestination
	 *            The name to give the file on your system.
	 * @param dppi
	 *            Data Processg plug-in, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveLog(String fileId, String fileNameDestination,
			Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("ng_log", null);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _Retrieve(cmd, fileNameDestination);
	}

	/**
	 * Retrieve a log file.
	 * 
	 * @param fileId
	 *            the id of the file to get.
	 * @param fileNameDestination
	 *            The name to give the file on your system.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveLog(String fileId, String fileNameDestination) {
		return retrieveLog(fileId, fileNameDestination, DUMMY_DPPI);
	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param closeOutputStream
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, OutputStream outStream,
			boolean closeOutputStream, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _RetrieveStream(cmd, outStream, closeOutputStream);
	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param closeOutputStream
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, OutputStream outStream,
			boolean closeOutputStream) {
		return retrieveStream(fileId, outStream, closeOutputStream, DUMMY_DPPI);

	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, OutputStream outStream,
			Dppi dppi) {
		return retrieveStream(fileId, outStream, true, dppi);
	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, OutputStream outStream) {
		return retrieveStream(fileId, outStream, DUMMY_DPPI);
	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param fileVersion
	 *            The version of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, String fileVersion,
			OutputStream outStream, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _RetrieveStream(cmd, outStream);
	}

	/**
	 * Retrieve a file into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param fileVersion
	 *            The version of the file to retrieve.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, String fileVersion,
			OutputStream outStream) {
		return retrieveStream(fileId, fileVersion, outStream, DUMMY_DPPI);
	}

	/**
	 * Retrieve a file. Parameters that are given the value null are omitted
	 * from the final string sent to NGAS.
	 * 
	 * @param fileId
	 *            the file id of the file to get.
	 * @param fileVersion
	 *            the version of the file to get.
	 * @param internal
	 *            whether the file is internal or not.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, String fileVersion,
			String internal, OutputStream outStream, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		parameterMap.put("file_version", fileVersion);
		parameterMap.put("internal", internal);
		String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		return _RetrieveStream(cmd, outStream);
	}

	/**
	 * Retrieve a file. Parameters that are given the value null are omitted
	 * from the final string sent to NGAS.
	 * 
	 * @param fileId
	 *            the file id of the file to get.
	 * @param fileVersion
	 *            the version of the file to get.
	 * @param internal
	 *            whether the file is internal or not.
	 * @param outStream
	 *            Stream to which the file contents is written.
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status retrieveStream(String fileId, String fileVersion,
			String internal, OutputStream outStream) {
		return retrieveStream(fileId, fileVersion, internal, outStream,
				DUMMY_DPPI);
	}

	/**
	 * Retrieves a file from a Ngas server into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * @param dppi
	 *            Data Process Plug-In, null if not needed
	 * @return the stream associated to the file to be retrieved
	 */
	public HttpInputStream retrieveStream(String fileId, Dppi dppi) {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("file_id", fileId);
		final String cmd = prepareCommand("RETRIEVE", parameterMap, dppi);
		HttpInputStream dataStream = null;
		try {
			final HttpURLConnection con = this.myConnectionManager.get(cmd);
			dataStream = new HttpInputStream(con, logger);
		} catch (IOException e) {
			logger.warning("IOException sending retrieve command to NGAS. "
					+ "Tried to send command: " + cmd);
		}
		return dataStream;
	}

	/**
	 * Retrieves a file from a Ngas server into a stream.
	 * 
	 * @param fileId
	 *            The File ID of the file to retrieve.
	 * 
	 * @return the stream associated to the file to be retrieved
	 */
	public HttpInputStream retrieveStream(String fileId) {
		return retrieveStream(fileId, DUMMY_DPPI);
	}

	/**
	 * Sets the DPPI that should be used to process the next command. This will
	 * affect ONLY the next issued command and then the DPPI parameters will be
	 * cleared.
	 * 
	 * @param inParameters
	 *            a String stating the parameters that should be added to the
	 *            next issued command.
	 */
	public void setProcessing(String inProcessing) {
		this.myProcessing = inProcessing;
	}

	/**
	 * Sets the DPPI that should be used to process the next command. This will
	 * affect ONLY the next issued command and then the DPPI will be cleared.
	 * 
	 * @param inParameters
	 *            a String stating the parameters that should be added to the
	 *            next issued command.
	 */
	public void setProcessingParameters(String inParameters) {
		this.myProcessingParameters = inParameters;
	}

	/**
	 * Sends a simple command. Just calls the other method with the same name
	 * and the same parameters but passes false for receivingFile.
	 * <p>
	 * See {@link #prepareCommand(String, LinkedHashMap)} for details on input.
	 * 
	 * @param inCommand
	 *            The command to send.
	 * @param inParameterMap
	 *            The parameter map to give to the command.
	 * 
	 * @return Status object representing the response of NGAMS to the command
	 *         sent.
	 * 
	 * @see {@link #prepareCommand(String, LinkedHashMap)}
	 */
	private Status sendSimpleCmd(String inCommand,
			LinkedHashMap<String, String> inParameterMap) {
		return sendSimpleCmd(inCommand, inParameterMap, false);
	}

	public Double getConnectTime() {
		// return connectTimes.get(Thread.currentThread().getName());
		return 0.0;
	}

	/**
	 * Sends simple commands to NGAS. A simple command is one where all we have
	 * to do is send a string and wait for the response. For example STATUS, but
	 * not ARCHIVE or RETRIEVE. This method contains the code that actually
	 * connects to NGAS via HTTP.
	 * <p>
	 * See {@link #prepareCommand(String, LinkedHashMap)} for details on input.
	 * 
	 * @param inCommand
	 *            The command to send.
	 * @param inParameterMap
	 *            The parameter map to give to the command.
	 * @param busy
	 *            Whether the miniServer is currently receiving a file. Used by
	 *            the SUBSCRIBE and UNSUBSCRIBE commands.
	 * 
	 * @return Status object representing the response of NGAMS to the command
	 *         sent.
	 * 
	 * @see {@link #prepareCommand(String, LinkedHashMap)}
	 */
	private Status sendSimpleCmd(String inCommand,
			LinkedHashMap<String, String> inParameterMap, boolean busy) {
		Status returnStatus = null;
		HttpURLConnection con = null;
		try {
			String completeCommand = prepareCommand(inCommand, inParameterMap,
					null);
			// long start = System.currentTimeMillis();
			con = this.myConnectionManager.get(completeCommand);
			// this.connectTimes.put(Thread.currentThread().getName(),
			// (System.currentTimeMillis() - start) / 1000.0);
			int code = con.getResponseCode();
			String msg = con.getResponseMessage();
			InputStream stream = con.getInputStream();
			if (code != 200) {
				stream = con.getErrorStream();
			}
			BufferedReader reader = new BufferedReader(new InputStreamReader(
					stream));
			String line = null;
			StringBuilder xml = new StringBuilder();
			while ((line = reader.readLine()) != null) {
				xml.append(line).append("\n");
			}
			// not the end of the world if this fails
			reader.close();

			if (code == 200) {
				String logMsg = "Succesfully sent the following command to "
						+ "NGAS, via HTTP GET: ";
				logMsg += completeCommand;
				logger.info(logMsg);
			} else {
				String logMsg = "Error sending the following command to "
						+ "NGAS, via HTTP GET: ";
				logMsg += completeCommand;
				logMsg += "For more information on the error, consult the "
						+ "instance of Status ";
				logMsg += "returned by this method.";
				logger.warning(logMsg);
			}
			returnStatus = new Status(code, msg, xml.toString(), dataRaw
					+ "ngams.xml", logger);
		} catch (IOException e) {
			returnStatus = new Status(false,
					"Error generated by sendSimpleCmd in "
							+ "JClient. Description: " + e.toString());
		} finally {
			// we must always close the connection to prevent socket leaks
			if (con != null)
				con.disconnect();
		}
		return returnStatus;
	}

	/**
	 * Find the status of the NGAS system.
	 * 
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status status() {
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		return sendSimpleCmd("STATUS", parameterMap);
	}

	/**
	 * Used if you want to retrieve many files from NGAS. A mini server is
	 * launched on your machine that listens for the HTTP POST commands from
	 * NGAS and saves incoming files. If the url specified (implicitly or
	 * explicitly) is the same as the URL stored in the URL field, and this
	 * JClient has already subscribed to NGAS, nothing is sent to NGAS and a
	 * warning is logged. Apart from the URL, if an argument is given the value
	 * null it will be omitted from the string sent to NGAS.
	 * 
	 * @param filterPlugIn
	 *            Filter to apply to the files before they are sent.
	 * @param plugInPars
	 *            Parameters to send to the filter.
	 * @param priority
	 *            Priority for the data delivery; high numbers indicate low
	 *            priority
	 * @param startDate
	 *            NGAS will send only files whose date is after the specified
	 *            startDate.
	 * @param url
	 *            The URL to which NGAS should send the files; if specified as
	 *            null this is taken to be whatever is in the url field of this
	 *            JClient instance.
	 * @param fileNamesOptions
	 *            Specifies what names the files should have when they are saved
	 *            in the directory dataRaw.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status subscribe(String filterPlugIn, String plugInPars,
			String priority, String startDate, String url) {
		if (url == null) {
			logger.info("The call to JClient.subscribe speficified the URL "
					+ "parameter as null. Using default url: " + this.url);
			url = this.url;
		}
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("filter_plug_in", filterPlugIn);
		parameterMap.put("plug_in_pars", plugInPars);
		parameterMap.put("priority", priority);
		parameterMap.put("start_date", startDate);
		parameterMap.put("url", url);
		// Set up the server to listen for incoming files
		miniServer = new MiniServer(miniServerPort, BLOCK_SIZE, dataRaw, logger);
		Thread miniServerThread = new Thread(miniServer);
		miniServerThread.start();
		while (!miniServer.ready)
			; // Wait till the mini server finishes.
		// End subscribe message to NGAMS
		if (!subscribed && url.equals(this.url)) {
			subscribed = true;
			return sendSimpleCmd("SUBSCRIBE", parameterMap);
		} else if (!url.equals(this.url)) {
			logger.info("the call to JClient.subscribe refers to a URL: " + url
					+ " which is different from the default URL: " + this.url);
			return sendSimpleCmd("SUBSCRIBE", parameterMap);
		} else {
			String msg = "The call to JClient.subscribe either specified the "
					+ "parameter URL as null (meaning the default value: "
					+ this.url
					+ " is used) or explicitly passed parameter URL as "
					+ this.url
					+ ". But this URL has previously subscribed to "
					+ "NGAS. A second subscribe command has NOT been sent. You can "
					+ "find out whether the miniServer was receiving a file when "
					+ " this error message was generated by calling "
					+ "status.getReceivingFile() where status is the object "
					+ "returned by this method. At any other time you can find "
					+ "out whether the miniServer is taking a file by calling "
					+ "JClient.getMiniServerTakingFile().";
			logger.warning(msg);
			return new Status(true, msg);
		}
	}

	/**
	 * Unsubscribe to data from NGAS. If the URL is the same as the URL
	 * specified in the URL field of this instance of JClient, and we are not
	 * currently subscribed, then nothing is send to NGAS and a warning is
	 * logged.
	 * 
	 * @param url
	 *            The URL which NGAS should stop sending data to; if specified
	 *            as null this is taken to be the URL field of this instance of
	 *            JClient.
	 * @return Object representing the response of NGAMS to the command sent.
	 */
	public Status unsubscribe(String url) {
		if (url == null) {
			logger.info("URL specified as null in call to "
					+ "JClient.unsubscribe. Using default: " + this.url);
			url = this.url;
		}
		LinkedHashMap<String, String> parameterMap = new LinkedHashMap<String, String>();
		parameterMap.put("url", url);
		// Stop the server running on this machine, listening for files
		// from NGAMS.
		if (miniServer != null)
			miniServer.serve = false;
		// Tell NGAMS to stop sending files
		if (subscribed && url.equals(this.url)) {
			subscribed = false;
			return sendSimpleCmd("UNSUBSCRIBE", parameterMap,
					miniServer.takingFile);
		} else if (!url.equals(this.url)) {
			logger.info("the call to JClient.unsubscribe specifies a url "
					+ url + " different to the default url: " + this.url);
			return sendSimpleCmd("UNSUBSCRIBE", parameterMap,
					miniServer.takingFile);
		} else {
			String msg = "The call to JClient.unsubscribe either specified the "
					+ "parameter url as null (meaning the default value: "
					+ this.url
					+ "is used) or explicitly passed parameter URL as "
					+ this.url
					+ ". But this URK is NOT currently subscribed to "
					+ "NGAS. An unnecessary UNSUBSCRIBE command has NOT been sent "
					+ "to NGAS. You can find out whether the miniServer was "
					+ "receiving a file when this error message was generated by "
					+ "calling status.getReceivingFile() where status is the "
					+ "object returned by this method. At any other time you can "
					+ "find out whether the miniServer is taking a file by "
					+ "calling JClient.getMiniServerTakingFile().";
			logger.warning(msg);
			return new Status(true, msg);
		}
	}

	public static void main(String[] args) {
		Logger logger = Logger.getLogger("ArchiverTest logger");
		logger.setLevel((Level) Level.ALL);
		List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
		list.add(new InetSocketAddress("ga004786", 7777));
		JClient client = new JClient(list, logger);
		Status status = client.status();
		System.out.println("XML Status Document:\n" + status.getXML());
		status = client.retrieve("TEST.2001-05-08T15:25:00.123",
				"TEST.2001-05-08T15:25:00.123.fits.Z");
		System.out.println("XML Status Document:\n" + status.getXML());
		status = client.retrieve("NON-EXISTING", "");
		System.out.println("XML Status Document:\n" + status.getXML());
		try {
			FileOutputStream outStream = new FileOutputStream(
					"NCU.2003-11-11T11:11:11.111.fits.Z");
			status = client.retrieveStream("NCU.2003-11-11T11:11:11.111",
					outStream, null);
			System.out.println("XML Status Document:\n" + status.getXML());
		} catch (FileNotFoundException e) {
			logger.warning("FileNotFoundException while retrieving file. "
					+ "Error: " + e.toString());
		}
		// Status status = client.subscribe(null, null, null,
		// "2000-01-01", null);
		// miniServer = new MiniServer(7777, blockSize);
		// Thread miniServerThread = new Thread(miniServer);
		// miniServerThread.start();
	}

	/**
	 * 
	 * @param i
	 */
	public void setRetryTime(int i) {
		this.myConnectionManager.setRetryTime(i);
	}

	/**
	 * Class representing Data Processing plug-ins to be applied on data when
	 * they are being retrieve from the archive. Name and parameters data
	 * members are set to empty string if not initialized
	 * 
	 * @author cmoins
	 * 
	 */
	static public class Dppi {

		private final String name;
		private final String parameters;

		public Dppi(String name, String parameters) {
			this.name = (name != null) ? name : "";
			this.parameters = (parameters != null) ? parameters : "";
		}

		private Dppi() {
			name = "";
			parameters = "";
		}

	}
}
