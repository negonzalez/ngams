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
package alma.ngas.client;

import java.util.logging.Logger;
import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;

/**
 * Implementation of an input stream representing an http connection
 * 
 * @author cmoins
 * 
 */
public class HttpInputStream extends InputStream {

	/**
	 * JClient uses log4j; this logger logs events.
	 */
	private Logger logger;
	private BufferedInputStream inputStream = null;
	private HttpURLConnection httpConnection = null;
	private Status status = null;

	/**
	 * 
	 * @param httpConnection
	 *            connection to which the input stream is associated
	 * @param dataRaw
	 *            The path where incoming files are stored.
	 * @param inLogger
	 */
	public HttpInputStream(HttpURLConnection httpConnection, Logger inLogger) {
		if ((httpConnection == null) || (inLogger == null)) {
			throw new IllegalArgumentException(
					"Missing httpConnection or dataRaw or inLogger parameters");
		}
		try {
			this.httpConnection = httpConnection;
			this.logger = inLogger;
			int code = httpConnection.getResponseCode();
			String msg = httpConnection.getResponseMessage();
			if (code != 200) { // Error handling here: HTTP says all is not OK
				String xml = "";
				BufferedReader reader = null;
				reader = new BufferedReader(new InputStreamReader(
						httpConnection.getErrorStream()));
				String line = null;
				while ((line = reader.readLine()) != null) {
					xml = xml + line + "\n";
				}
				reader.close();
				// Log an error message.
				String logMsg = "Error when attempting to send a retrieve "
						+ "command:\n" + httpConnection.getURL().getFile()
						+ " to NGAS. For further information, "
						+ "consult the instance of Status returned.";
				logger.warning(logMsg);
				status = new Status(code, msg, xml, "/tmp/ngams.xml",
						logger);
			} else {
				String contentLength = httpConnection
						.getHeaderField("content-length");
				// Create objects to read data from the socket and out into a
				// file.
				this.inputStream = new BufferedInputStream(this.httpConnection
						.getInputStream());
				// Log a message.
				logger.info("Sent retrieve message to NGAMS: "
						+ httpConnection.getURL().getFile());
				this.status = new Status(code, msg);
				this.status.setFileSize(contentLength);
			}
		} catch (IOException e) {
			logger.warning("IOException sending retrieve command to NGAS. "
					+ "Tried to send command: "
					+ httpConnection.getURL().getFile());
			status = new Status(false, "Error generated by _Retrieve in "
					+ "JClient. Description:\n" + e.toString());
		}
	}

	
	@Override
	public int read(byte[] b, int off, int len) throws IOException {
		return inputStream.read(b, off, len);
	}

	@Override
	/**
	 * close the streams and the http connection
	 */
	public void close() {
		try {
			inputStream.close();
		} catch (IOException e) {
			logger.warning("Could not close data stream");
		}
		httpConnection.disconnect();
	}

	@Override
	public int read() throws IOException {
		// TODO Auto-generated method stub
		return inputStream.read();
	}

	public Status getStatus() {
		return status;
	}

}