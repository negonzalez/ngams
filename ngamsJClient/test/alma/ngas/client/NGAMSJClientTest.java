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
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

import junit.framework.Assert;
import junit.framework.TestCase;

/**
 * @author apersson
 */
public class NGAMSJClientTest extends TestCase {
	private final static Logger logger = Logger.getLogger("NGAMSJClientTest");
	private String myLocalHost;

	private static final int TEST_PORT1 = 53241;

	private static final int TEST_PORT2 = 53242;

	private static final int REDIRECT_TEST_PORT = 53240;

	/**
	 * 
	 * @param name
	 * @throws Exception
	 */
	public NGAMSJClientTest(String name) throws Exception {
		super(name);
		this.myLocalHost = InetAddress.getLocalHost().getHostAddress();
	}

	/**
	 * When we provide the ngamsJClient with a number of NGAMS servers to use, I
	 * expect it to distribute the load across all of the available servers, and
	 * not just to send all requests to a single server.
	 * 
	 * @throws Exception
	 */
	public void testClientUsesFullCluster() throws Exception {
		final int numServers = 10;
		FakeServer[] servers = new FakeServer[numServers];
		List<InetSocketAddress> serverAddresses = new ArrayList<InetSocketAddress>();
		for (int i = 0; i < numServers; i++) {
			final int portNumber = TEST_PORT1 + i;
			serverAddresses.add(new InetSocketAddress(this.myLocalHost,
					portNumber));

			servers[i] = new FakeServer(portNumber);
			servers[i].start();
		}
		Thread.sleep(1000);

		try {
			int[] serverUsageStatistics = new int[numServers];
			JClient client = new JClient(serverAddresses, logger);
			for (int i = 0; i < 100; i++) {
				Status status = client.status();
				int serverId = Integer.valueOf(status.getHostId().substring(
						status.getHostId().indexOf(':') + 1))
						- TEST_PORT1;
				serverUsageStatistics[serverId]++;
			}
			for (int usageCount : serverUsageStatistics) {
				logger.info("server contacted " + usageCount + " times");
				Assert.assertTrue(usageCount > 0);
			}
		} finally {
			for (FakeServer nextServer : servers) {
				nextServer.terminate();
			}
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(1000);
		}
	}

	/**
	 * ICT-1269 Archive commands were only being sent to a single node.
	 * 
	 * @throws Exception
	 */
	public void testClientUsesFullClusterForWrites() throws Exception {
		final int numServers = 10;
		FakeServer[] servers = new FakeServer[numServers];
		List<InetSocketAddress> serverAddresses = new ArrayList<InetSocketAddress>();
		for (int i = 0; i < numServers; i++) {
			final int portNumber = TEST_PORT1 + i;
			serverAddresses.add(new InetSocketAddress(this.myLocalHost,
					portNumber));

			servers[i] = new FakeServer(portNumber);
			servers[i].start();
		}
		Thread.sleep(1000);

		try {
			int[] serverUsageStatistics = new int[numServers];
			JClient client = new JClient(serverAddresses, logger);
			byte[] data = new byte[1000];
			for (int i = 0; i < 100; i++) {
				InputStream is = new ByteArrayInputStream(data);
				Status status = client.archiveStream(is, "application/x-tar",
						"file" + i);
				int serverId = Integer.valueOf(status.getHostId().substring(
						status.getHostId().indexOf(':') + 1))
						- TEST_PORT1;
				serverUsageStatistics[serverId]++;
			}
			for (int usageCount : serverUsageStatistics) {
				logger.info("server contacted " + usageCount + " times");
				Assert.assertEquals(10, usageCount);
			}
		} finally {
			for (FakeServer nextServer : servers) {
				nextServer.terminate();
			}
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(1000);
		}
	}

	/**
	 * 
	 * @throws Exception
	 */
	public void testCommands() throws Exception {
		FakeServer server = new FakeServer(TEST_PORT1);
		server.start();
		Thread.sleep(1000);
		try {
			List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
			list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT1));
			JClient client = new JClient(list, logger);

			/*
			 * Since the fake server does not return any xml the log will get
			 * error messages regarding premature end of file. These can be
			 * ignored.
			 */
			client.init();
			String expected = "INIT";
			String actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.setProcessingParameters("nisse");
			client.init();
			expected = "INIT&processing_pars=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.init();
			expected = "INIT";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.exit();
			expected = "EXIT";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.online();
			expected = "ONLINE";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.clone("nisse");
			expected = "CLONE?file_id=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.clone("orvar", "nisse");
			expected = "CLONE?disk_id=orvar&file_id=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.clone("orvar", "nisse", "bosse");
			expected = "CLONE?disk_id=orvar&file_id=nisse&file_version=bosse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.label("orvar");
			expected = "LABEL?slot_id=orvar";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.label("orvar", "nisse");
			expected = "LABEL?slot_id=orvar&host_id=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.offline();
			expected = "OFFLINE";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.offlineForce();
			expected = "OFFLINE?force";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.register("orvar");
			expected = "REGISTER?path=orvar";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.register("orvar", "nisse");
			expected = "REGISTER?path=orvar&mime_type=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remdisk("orvar", false);
			expected = "REMDISK?disk_id=orvar&execute=0";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remdisk("orvar", true);
			expected = "REMDISK?disk_id=orvar&execute=1";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("orvar", "nisse", "bosse", false);
			expected = "REMFILE?disk_id=orvar&file_id=nisse&file_version=bosse&execute=0";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("orvar", "nisse", "bosse", true);
			expected = "REMFILE?disk_id=orvar&file_id=nisse&file_version=bosse&execute=1";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("orvar", "nisse", false);
			expected = "REMFILE?disk_id=orvar&file_id=nisse&execute=0";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("orvar", "nisse", true);
			expected = "REMFILE?disk_id=orvar&file_id=nisse&execute=1";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("nisse", false);
			expected = "REMFILE?file_id=nisse&execute=0";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.remfile("nisse", true);
			expected = "REMFILE?file_id=nisse&execute=1";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.status();
			expected = "STATUS";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.diskStatus("orvar");
			expected = "STATUS?disk_id=orvar";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.fileStatus("nisse");
			expected = "STATUS?file_id=nisse";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.flushLog();
			expected = "STATUS?flush_log";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.configStatus();
			expected = "STATUS?configuration_file";
			actual = server.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));
		} finally {
			server.terminate();
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(1000);
		}
	}

	public void testStatus() throws Exception {
		FakeServer server = new FakeServer(TEST_PORT1);
		server.start();
		Thread.sleep(1000);
		try {
			List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
			list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT1));
			JClient client = new JClient(list, logger);

			Status status = client.status();

			String expected = "CompletionTimeValue";
			String actual = status.getCompletionTime();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "DateValue";
			actual = status.getDate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FakeNgamsServer:" + TEST_PORT1;
			actual = status.getHostId();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "LastRequestStatUpdateValue";
			actual = status.getLastRequestStatUpdate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "MessageValue";
			actual = status.getMessage();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "RequestIdValue";
			actual = status.getRequestId();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "RequestTimeValue";
			actual = status.getRequestTime();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "StateValue";
			actual = status.getState();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "StatusValue";
			actual = status.getStatus();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "SubStateValue";
			actual = status.getSubState();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "VersionValue";
			actual = status.getVersion();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "ArchiveValue";
			actual = status.getArchive();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "AvailableMbValue";
			actual = status.getAvailableMb();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "BytesStoredValue";
			actual = status.getBytesStored();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "DiskChecksumValue";
			actual = status.getDiskChecksum();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "CompletedValue";
			actual = status.getCompleted();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "CompletionDateValue";
			actual = status.getCompletionDate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "DiskIdValue";
			actual = status.getDiskId();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "InstallationDateValue";
			actual = status.getInstallationDate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "LastCheckValue";
			actual = status.getLastCheck();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "LogicalNameValue";
			actual = status.getLogicalName();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "ManufacturerValue";
			actual = status.getManufacturer();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "MountPointValue";
			actual = status.getMountPoint();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "MountedValue";
			actual = status.getMounted();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "NumberOfFilesValue";
			actual = status.getNumberOfFiles();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "SlotIdValue";
			actual = status.getSlotId();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "TotalDiskWriteTimeValue";
			actual = status.getTotalDiskWriteTime();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "TypeValue";
			actual = status.getType();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileChecksumValue";
			actual = status.getFileChecksum();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "ChecksumPlugInValue";
			actual = status.getChecksumPlugIn();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "CompressionValue";
			actual = status.getCompression();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "CreationDateValue";
			actual = status.getCreationDate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileIdValue";
			actual = status.getFileId();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileNameValue";
			actual = status.getFileName();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileSizeValue";
			actual = status.getFileSize();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileStatusValue";
			actual = status.getFileStatus();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FileVersionValue";
			actual = status.getFileVersion();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "FormatValue";
			actual = status.getFormat();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "IgnoreValue";
			actual = status.getIgnore();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "IngestionDateValue";
			actual = status.getIngestionDate();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "TagValue";
			actual = status.getTag();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			expected = "UncompressedFileSizeValue";
			actual = status.getUncompressedFileSize();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

		} finally {
			server.terminate();
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(1000);
		}
	}

	public void testRedirect1() throws Exception {
		redirectTest(1, REDIRECT_TEST_PORT, TEST_PORT1);
	}

	/**
	 * By default the HtpUrlConnection will bottle-out once it reaches 20
	 * redirection instructions
	 * 
	 * @throws Exception
	 */
	public void testRedirect19() throws Exception {
		// I change the port numbers because previously we were connecting to a
		// wrong server and
		// it wasn't immediately obvious.
		redirectTest(19, REDIRECT_TEST_PORT + 10, TEST_PORT1 + 10);
	}

	/**
	 * By default the HtpUrlConnection will bottle-out once it reaches 20
	 * redirection instructions
	 */
	public void testRedirect20() throws Exception {
		// there appears to be some caching going on in the redirects. If I use
		// the same port as before
		// for the redirect server then it jumps straight to the redirected
		// address
		redirectTest(20, REDIRECT_TEST_PORT + 20, TEST_PORT1 + 20);
	}

	/**
	 * 
	 * @param inRepeats
	 * @param redirectPort
	 * @param testPort
	 * @throws Exception
	 */
	private void redirectTest(int inRepeats, int redirectPort, int testPort)
			throws Exception {
		RedirectServer redirectServer = new RedirectServer(inRepeats,
				redirectPort, testPort);
		FakeServer server = new FakeServer(testPort);
		try {
			server.start();
			try {
				redirectServer.start();
				Thread.sleep(5000);
				List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
				list.add(new InetSocketAddress(myLocalHost, redirectPort));
				JClient client = new JClient(list, logger);

				Status status = client.status();
				if (status.getOK()) {
					String expected = "STATUS";
					String actual = server.getReceivedCommand();
					if (inRepeats < 20) {
						assertTrue("Returned string was [" + actual
								+ "], expected was [" + expected + "]",
								expected.equals(actual));
					} else {
						throw new RuntimeException(status.getMsg());
					}
				} else {
					if (inRepeats < 20) {
						throw new RuntimeException(status.getMsg());
					}
				}
			} finally {
				redirectServer.terminate();
			}
		} finally {
			server.terminate();
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(2000);
		}
	}

	/**
	 * 
	 * @throws Exception
	 */
	public void testServerFailOver() throws Exception {
		FakeServer server1 = null;
		FakeServer server2 = null;
		try {
			Logger logger = Logger.getAnonymousLogger();
			logger.setLevel(Level.FINEST);
			logger.setUseParentHandlers(false);
			logger.addHandler(new Handler() {

				@Override
				public void publish(LogRecord record) {
					String string = record.getLevel() + " [Thread-"
							+ record.getThreadID() + "]";
					string += " "
							+ record.getSourceClassName().substring(
									record.getSourceClassName()
											.lastIndexOf('.') + 1) + "."
							+ record.getSourceMethodName();
					string += ": " + record.getMessage();
					System.out.println(string);
				}

				@Override
				public void flush() {
					// TODO Auto-generated method stub

				}

				@Override
				public void close() throws SecurityException {
					// TODO Auto-generated method stub

				}

			});
			List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
			list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT1));
			list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT2));
			JClient client = new JClient(list, logger);

			Status status = client.status();
			assertTrue("Expected was that no servers are available.",
					!status.getOK());

			server1 = new FakeServer(TEST_PORT1);
			server2 = new FakeServer(TEST_PORT2);
			server1.start();
			server2.start();
			Thread.sleep(1000);

			// Even though the servers have started they should still not be
			// considered available since there is a 10 minute retry timeout.
			status = client.status();
			assertTrue("Expected was that no servers are available.",
					!status.getOK());

			client.setRetryTime(0);
			client.status();
			String expected = "STATUS";
			String actual = server1.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			// Verify that the fake server resets the received command.
			expected = null;
			actual = server1.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected == actual);

			client.status();
			expected = "STATUS";
			actual = server2.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

			client.status();
			expected = "STATUS";
			actual = server1.getReceivedCommand();
			assertTrue("Returned string was [" + actual + "], expected was ["
					+ expected + "]", expected.equals(actual));

		} finally {
			server1.terminate();
			server2.terminate();
			/*
			 * Sleep to allow thread the time to shutdown in case the server is
			 * reused in following test cases. Risk of bind() exception
			 * otherwise.
			 */
			Thread.sleep(1000);
		}
	}

	/**
	 * make sure we don't get out of memory exceptions when handling large files
	 * We attempt to send a 70MB file to a dummy NGAS client. Previously the
	 * sending method used to load the entire file into memory and blow the heap
	 * space.
	 * 
	 * @throws Exception
	 */
	public void testLargeFiles() throws Exception {
		FakeReceiver server = null;
		try {
			server = new FakeReceiver(TEST_PORT1);
			Logger logger = Logger.getAnonymousLogger();
			List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
			list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT1));
			JClient client = new JClient(list, logger);

			server.start();
			Thread.sleep(1000);

			createBigFile();
			// trying to send the big file resulted in an OutOfMemoryError
			Status status = client.archive("bigfile.txt", "text/plain");
			assertTrue(status.getMsg(), status.getOK());
		} finally {
			server.terminate();
			Thread.sleep(1000);
			deleteBigFile();
		}
	}

	/**
	 * test that the dppi settings are correctly received by the server.
	 * 
	 * @throws Exception
	 */
	public void testRetrieveStream() throws Exception {
		FakeServer server = new FakeServer(TEST_PORT1);
		List<InetSocketAddress> list = new ArrayList<InetSocketAddress>();
		list.add(new InetSocketAddress(this.myLocalHost, TEST_PORT1));
		JClient client = new JClient(list, logger);
		server.start();
		Thread.sleep(1000);
		String dppiName = "TESTDPPI";
		String dppiPars = "TESTDPPIPARS";
		client.retrieveStream("Any File", new JClient.Dppi(dppiName, dppiPars));
		String receivedCommand = server.getReceivedCommand();
		assertTrue(receivedCommand.contains("processing=" + dppiName));
		assertTrue(receivedCommand.contains("processing_pars=" + dppiPars));
		client.retrieveStream("Any File");
		receivedCommand = server.getReceivedCommand();
		assertTrue(!receivedCommand.contains("processing=" + dppiName));
		assertTrue(!receivedCommand.contains("processing_pars=" + dppiPars));
	}

	/**
	 * Create a file that is big enough to blow the heap size if it's laoded
	 * into memory. The default size of the heap, at the time of writing this
	 * test, is still 64MB. So we create a file of 70MB size.
	 */
	private void createBigFile() throws Exception {
		FileOutputStream fos = null;
		try {
			fos = new FileOutputStream("bigfile.txt");
			for (int i = 0; i < 700000; i++) {
				// this string is 100 characters long.
				fos.write("aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeeeffffffffffgggggggggghhhhhhhhhhiiiiiiiiiijjjjjjjjjj"
						.getBytes());
				fos.flush();
			}
			fos.write("\n\n".getBytes());
			fos.write('\n');
			fos.flush();
			fos.close();
		} finally {
			if (fos != null)
				fos.close();
		}
	}

	/**
	 * Tidy up the big file that we created.
	 */
	private void deleteBigFile() {
		File f = new File("bigfile.txt");
		f.delete();
	}
}
