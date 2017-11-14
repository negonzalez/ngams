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

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.URL;
import java.util.Date;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

interface ConnectionSetup {
	void configure(HttpURLConnection connection) throws IOException;
}

public class ConnectionManager {
	private static final long RETRY_TIMEOUT = 30 * 1000; // in other words 30
															// seconds

	// 15 seconds seems a reasonable time to wait for a socket to connect. If
	// not achieved in this time then the
	// server will be removed from the list of servers for RETRY_TIMEOUT seconds
	// to give it a chance to recover
	// with no new incoming connections. I'm thinking of the case here where a
	// server becomes overloaded and can't
	// respond in a sensible time, not that a server is unavailable and needs to
	// be restarted.
	private int connectTimeOut = 15 * 1000;
	// how long do we wait for the server to return data before we have an
	// IOException? This is the time to return some
	// data, not an entire file e.g. we try to read a byte from a socket but no
	// single byte is received in this time.
	private int readTimeOut = 15 * 1000;

	private LinkedHashMap<InetSocketAddress, Date> myConnectionMap = new LinkedHashMap<InetSocketAddress, Date>();

	private Iterator<Map.Entry<InetSocketAddress, Date>> myConnectionIterator;

	private Logger logger = Logger.getLogger("ConnectionManager");

	private long retryTime = RETRY_TIMEOUT;

	/**
	 * Will retrieve a 'CONNECTED' HttpURLConnection to an NGAS server.
	 * <p>
	 * The method will connect to the servers specified in
	 * {@link #setConnectionList(List)} using round-robin. In case no servers
	 * have been set an IOException is thrown. In case a server causes an
	 * IOException the server will be marked as unusable for the amount of time
	 * stated by {@link #setRetryTime(long)} which default is 10 minutes. If no
	 * server is deemed to be available an IOException is thrown.
	 * <p>
	 * In case a redirect (HTTP code 301 - 303) is returned by a server the
	 * method will follow redirects 20 times before bailing out with an
	 * IOException.
	 * 
	 * @param inCommand
	 *            a String being the command that will be sent.
	 * 
	 * @return a 'CONNECTED' HttpURLConnection object, in other words, the
	 *         command has already been sent and the response from the server is
	 *         ready to be retrieved from the returned connection object.
	 * 
	 * @throws IOException
	 *             in case of communication error.
	 */
	private HttpURLConnection getConnection(String inCommand,
			ConnectionSetup connectionSetup) throws IOException {
		if (logger.isLoggable(Level.FINER))
			logger.finer("-> getConnection");
		URL url = null;
		HttpURLConnection outConnection = null;
		if (myConnectionMap.size() == 0) {
			throw new IOException(
					"The connections to use has not been defined.");
		}
		// This MUST be set before the connection is created, otherwise it has
		// no effect.
		HttpURLConnection.setFollowRedirects(true);
		int connectionRetrievalCount = 0;
		boolean done = false;
		while (!done) {
			// First retrieve a connection that has not been marked as not
			// working.
			connectionRetrievalCount++;
			if (logger.isLoggable(Level.FINER))
				logger.finer("connection retrieval count: "
						+ connectionRetrievalCount);
			if (connectionRetrievalCount > this.myConnectionMap.size()) {
				/*
				 * The connection map does not contain any addresses that are
				 * currently not considered broken.
				 */
				throw new IOException(
						"There are currently no working NGAS servers available.");
			}
			InetSocketAddress address = getNextAvailableServer();
			if (address != null) {
				String host = address.getHostName();
				int port = address.getPort();
				try {
					url = new URL("http", host, port, inCommand);
					outConnection = (HttpURLConnection) url.openConnection();
					outConnection.setConnectTimeout(connectTimeOut);
					outConnection.setReadTimeout(readTimeOut);
					connectionSetup.configure(outConnection);
					if (logger.isLoggable(Level.FINER))
						logger.finer("connecting to " + host + ": " + port);
					outConnection.connect();
					done = true;
				} catch (IOException e) {
					logger.log(Level.SEVERE, e.getMessage(), e);
					// Mark address as broken by adding current time.
					this.logger
							.warning("Connection "
									+ address
									+ " is not responding and will not be used for the next "
									+ this.retryTime + " milliseconds.");
					this.myConnectionMap.put(address, new Date());
				}
			}
		}
		if (logger.isLoggable(Level.FINER))
			logger.finer("<- getConnection");
		return outConnection;
	}

	/**
	 * 
	 * @param command
	 * @return
	 */
	public HttpURLConnection post(String command, final String contentType,
			final String filename, final long filesize,
			final String noVersioning, final Map<String, String> parameters)
			throws IOException {
		return this.getConnection(command, new ConnectionSetup() {

			@Override
			public void configure(HttpURLConnection connection)
					throws IOException {
				connection.setRequestMethod("POST");
				connection.setDoInput(true);
				connection.setDoOutput(true);
				connection.setRequestProperty("User-Agent", "NG/AMS J-API");
				connection.setRequestProperty("Content-Type", contentType);
				// filesize is -1 if the stream to archive command is used
				if (filesize >= 0) {
					// workaround for java bug 5026745
					// which is supposed to be fixed in jdk1.6
					// for large files the content was stored in memory before
					// being sent
					// which results in OutOfMemoryException neing thrown
					if (filesize > Integer.MAX_VALUE) {
						throw new IOException("File too big");
					} else {
						connection.setFixedLengthStreamingMode((int) filesize);
					}
					connection.setRequestProperty("Content-Length",
							String.valueOf(filesize));
				}
				String contentDisposition = "attachment;";
				contentDisposition += "filename=\"" + filename + "\";";
				contentDisposition += "wait=\"1\";";
				contentDisposition += (noVersioning == "1") ? ""
						: " no_versioning=0";
				if (parameters != null) {
					for (String par : parameters.keySet())
						contentDisposition += par + "=\"" + parameters.get(par)
								+ "\";";
				}
				connection.setRequestProperty("Content-Disposition",
						contentDisposition);
			}
		});
	}

	/**
	 * 
	 * @param command
	 * @return
	 */
	public HttpURLConnection get(String command) throws IOException {
		return this.getConnection(command, new ConnectionSetup() {

			@Override
			public void configure(HttpURLConnection connection)
					throws IOException {
				connection.setRequestMethod("GET");
			}
		});
	}

	/**
	 * 
	 * @return
	 */
	private InetSocketAddress getNextAvailableServer() {
		InetSocketAddress address = null;
		int connectionsTried = 0;
		while (address == null
				&& connectionsTried < this.myConnectionMap.size()) {
			connectionsTried++;
			Map.Entry<InetSocketAddress, Date> entry = null;
			synchronized (this) {
				if (!this.myConnectionIterator.hasNext()) {
					if (logger.isLoggable(Level.FINER))
						logger.finer("resetting the connection iterator");
					this.myConnectionIterator = this.myConnectionMap.entrySet()
							.iterator();
				}
				entry = this.myConnectionIterator.next();
			}
			Date date = entry.getValue();
			if (date == null) {
				address = entry.getKey();
			} else {
				if (logger.isLoggable(Level.FINER))
					logger.finer("connection has been marked as unusable");
				if (System.currentTimeMillis() > date.getTime()
						+ this.retryTime) {
					if (logger.isLoggable(Level.FINER))
						logger.finer("time to retry the connection");
					// Retry this connection.
					this.logger
							.info("Connection "
									+ entry.getKey()
									+ " will now be attempted again after a retry time of "
									+ this.retryTime + " milliseconds.");
					entry.setValue(null);
				} else {
					continue;
				}
			}
		}
		return address;
	}

	public synchronized void setConnectionList(
			List<InetSocketAddress> inConnectionList) {
		// following line was breaking the unit tests as the connection manager
		// is a singleton.
		// if ((this.myConnectionMap == null) ||
		// (this.myConnectionMap.isEmpty())) {
		if (inConnectionList == null) {
			throw new IllegalArgumentException(
					"The supplied connection list may not be null.");
		}
		if (inConnectionList.isEmpty()) {
			throw new IllegalArgumentException(
					"The supplied connection list may not be empty.");
		}

		this.myConnectionMap = new LinkedHashMap<InetSocketAddress, Date>();
		for (InetSocketAddress address : inConnectionList) {
			this.myConnectionMap.put(address, null);
		}
		this.myConnectionIterator = this.myConnectionMap.entrySet().iterator();
	}

	public synchronized void setLogger(Logger inLogger) {
		this.logger = inLogger;
	}

	public synchronized void setRetryTime(long inMillis) {
		this.retryTime = inMillis;
	}

	/**
	 * read and connec time out are set to the same value
	 * 
	 * @param timeOut
	 */
	public synchronized void setTimeOut(int timeOut) {
		this.readTimeOut = timeOut * 1000;
		this.connectTimeOut = timeOut * 1000;
	}

}
