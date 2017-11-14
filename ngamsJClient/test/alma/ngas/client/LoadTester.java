/*
 *    ALMA - Atacama Large Millimiter Array
 *    (c) European Southern Observatory, 2002
 *    Copyright by ESO (in the framework of the ALMA collaboration),
 *    All rights reserved
 *
 *    This library is free software; you can redistribute it and/or
 *    modify it under the terms of the GNU Lesser General Public
 *    License as published by the Free Software Foundation; either
 *    version 2.1 of the License, or (at your option) any later version.
 *
 *    This library is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *    Lesser General Public License for more details.
 *
 *    You should have received a copy of the GNU Lesser General Public
 *    License along with this library; if not, write to the Free Software
 *    Foundation, Inc., 59 Temple Place, Suite 330, Boston, 
 *    MA 02111-1307  USA
 *
 *    Created on Mar 17, 2005
 *
 */
package alma.ngas.client;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

import junit.framework.TestCase;

// I really _hate_ the JUL logging. Make the output a little more bearable.
class LogHandler extends Handler {
	@Override
	public void publish(LogRecord record) {
		String string = record.getLevel() + " [Thread-" + record.getThreadID()
				+ "]";
		string += " "
				+ record.getSourceClassName().substring(
						record.getSourceClassName().lastIndexOf('.') + 1) + "."
				+ record.getSourceMethodName();
		string += ": " + record.getMessage();
		System.out.println(string);
	}

	@Override
	public void flush() {
		// nothing to be done
	}

	@Override
	public void close() throws SecurityException {
		// nothing to be done
	}
}

class NullOutputStream extends OutputStream {
	long bytesRead = 0;

	@Override
	public void write(int b) throws IOException {
		bytesRead++;
	}

	long getBytesRead() {
		return bytesRead;
	}
};

class ReadThread extends Thread {
	private double time = 0;
	private String filename;
	private long bytesReceived = 0;
	private String location;
	private JClient ngas;
	private Logger logger;

	public ReadThread(String location, String filename, JClient client,
			Logger logger) {
		this.filename = filename;
		this.location = location;
		this.ngas = client;
		this.logger = logger;
	}

	public void run() {
		try {
			time = System.currentTimeMillis();
			NullOutputStream os = new NullOutputStream();
			Status s = ngas.retrieveStream(filename, os, null);
			bytesReceived = os.getBytesRead();
			os.close();
			os = null;
			time = (System.currentTimeMillis() - time) / 1000.0;
			logger.info(location + " " + filename + " read " + bytesReceived
					+ " bytes in " + time + "s: " + s.getStatus());
		} catch (Exception e) {
			logger.log(Level.SEVERE, "read " + location + ": " + filename
					+ " failed", e);
		}
	}

	public long getBytesRetrieved() {
		return bytesReceived;
	}
}

class Worker extends Thread {
	private long bytesReceived = 0;
	private double time = 0;
	private boolean sentOk = false;
	private double sentTime = 0;
	private double connectTime = 0.0;
	private boolean success = false;
	private JClient ngas;
	private Logger logger;
	private byte[] data;

	public Worker(byte[] data, JClient client, Logger logger) {
		this.data = data;
		this.ngas = client;
		this.logger = logger;
	}

	public void run() {
		try {
			time = System.currentTimeMillis();
			String filename = "file" + Thread.currentThread().getName() + "_"
					+ System.currentTimeMillis() + ".tar";
			InputStream is = new ByteArrayInputStream(data);
			Status si = ngas.archiveStream(is, "application/x-tar", filename);
			sentTime = (System.currentTimeMillis() - time) / 1000.0;
			sentOk = "SUCCESS".equals(si.getStatus());
			connectTime = ngas.getConnectTime() == null ? 0.0 : ngas
					.getConnectTime();

			ReadThread local = new ReadThread("local", filename, ngas, logger);
			ReadThread eu = new ReadThread("eu", filename, ngas, logger);
			ReadThread na = new ReadThread("na", filename, ngas, logger);
			ReadThread ea = new ReadThread("ea", filename, ngas, logger);
			time = System.currentTimeMillis();
			local.start();
			eu.start();
			na.start();
			ea.start();
			local.join();
			eu.join();
			na.join();
			ea.join();
			time = (System.currentTimeMillis() - time) / 1000.0;
			success = eu.getBytesRetrieved() == data.length
					&& local.getBytesRetrieved() == data.length
					&& na.getBytesRetrieved() == data.length
					&& ea.getBytesRetrieved() == data.length;
		} catch (Exception e) {
			logger.log(Level.SEVERE, e.getMessage(), e);
		}
	}

	public long getBytesReceived() {
		return bytesReceived;
	}

	public double getTime() {
		return time;
	}

	public boolean getSentOk() {
		return sentOk;
	}

	public double getSentTime() {
		return sentTime;
	}

	public double getConnectTime() {
		return connectTime;
	}

	public boolean getSuccess() {
		return success;
	}
};

/**
 * @author apersson
 */
public class LoadTester extends TestCase {
	private final static Logger logger = Logger.getLogger("NGAMSJClientTest");

	static {
		logger.setUseParentHandlers(false);
		logger.setLevel(Level.FINER);
		logger.addHandler(new LogHandler());
	}

	/**
	 * What happens if NGAS is not particularly responsive?
	 * 
	 * @throws Exception
	 */
	public void testSlowRealServer() throws Exception {
		List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
		list.add(new InetSocketAddress("ora04.hq.eso.org", 7777));
		final JClient client = new JClient(list, logger);

		final int numThreads = 2;
		final byte[] data = new byte[1000000];
		Arrays.fill(data, (byte) 65);
		Worker[] threads = new Worker[numThreads];
		for (int i = 0; i < numThreads; i++) {
			threads[i] = new Worker(data, client, logger);
			threads[i].start();
			logger.info("xx thread " + i + " started");
		}
		double minConnect = Double.MAX_VALUE;
		double maxConnect = 0;
		double totalConnect = 0;
		double minSent = Double.MAX_VALUE;
		double maxSent = 0;
		double totalSent = 0;
		double minRead = Double.MAX_VALUE;
		double maxRead = 0;
		double totalRead = 0;
		int sent = 0;
		int success = 0;
		for (int i = 0; i < numThreads; i++) {
			threads[i].join();
			logger.info("xx thread " + i + ", bytes: "
					+ threads[i].getBytesReceived() + ", connect: "
					+ threads[i].getConnectTime() + ", send: "
					+ threads[i].getSentTime() + ", read: "
					+ threads[i].getTime());
			if (threads[i].getSentOk())
				sent++;
			if (threads[i].getSuccess()) {
				success++;
				minConnect = Math.min(minConnect, threads[i].getConnectTime());
				maxConnect = Math.max(maxConnect, threads[i].getConnectTime());
				totalConnect += threads[i].getConnectTime();
				minSent = Math.min(minConnect, threads[i].getSentTime());
				maxSent = Math.max(maxConnect, threads[i].getSentTime());
				totalSent += threads[i].getSentTime();
				minRead = Math.min(minConnect, threads[i].getTime());
				maxRead = Math.max(maxConnect, threads[i].getTime());
				totalRead += threads[i].getTime();
			}
		}
		logger.info("xx successful sentok: " + sent + ", recevied: " + success);
		logger.info("" + success + " connect: " + minConnect + " .. "
				+ maxConnect + " " + totalConnect / success + " write "
				+ minSent + " .. " + maxSent + " " + totalSent / success
				+ " read " + minRead + " .. " + maxRead + " " + totalRead
				/ success + " : " + (totalConnect + totalSent + totalRead)
				/ success);
		;
	}

}
