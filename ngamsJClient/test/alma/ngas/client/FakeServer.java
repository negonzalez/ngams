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

import java.io.InputStreamReader;
import java.io.LineNumberReader;
import java.io.OutputStreamWriter;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.logging.Level;
import java.util.logging.Logger;

class FakeServer extends Thread {
	private Logger logger = Logger.getLogger("FakeServer");
    private boolean terminate = false;

    private String receivedCommand;

    private int portNumber;
	private long responseTimeMs = 100;

    public FakeServer(int inPortNumber) {
        this.portNumber = inPortNumber;
    }

    public FakeServer(int inPortNumber, long responseTimeMs) {
        this.portNumber = inPortNumber;
        this.responseTimeMs = responseTimeMs;
    }

    public synchronized String getReceivedCommand() {
        String outString = this.receivedCommand;
        this.receivedCommand = null;
        return outString;
    }

    @Override
    public void run() {
        ServerSocketChannel channel = null;
        try {
            channel = ServerSocketChannel.open();
            channel.configureBlocking(false);
            InetAddress inetAddress = InetAddress.getLocalHost();
            InetSocketAddress socketAddress = new InetSocketAddress(
                    inetAddress, this.portNumber);
            logger.info("waiting on port " + portNumber);
            channel.socket().bind(socketAddress);
            while (!isTerminated()) {
                SocketChannel sc = channel.accept();
                Thread.sleep(this.responseTimeMs );
                if (sc != null) {
                    Socket socket = sc.socket();
                    LineNumberReader in = new LineNumberReader(
                            new InputStreamReader(socket.getInputStream()));
                    String input = in.readLine();
                    /*
                     * Strip initial "GET " and trailing " HTTP/1.0". No
                     * need to synchronize this with the client call since
                     * the code sequence can be considered synchronous.
                     * Using wait without a timeout will actually cause a
                     * deadlock.
                     */
                    this.receivedCommand = input.substring(4, input
                            .length() - 9).replaceAll("/", "").trim();
                    OutputStreamWriter out = new OutputStreamWriter(socket
                            .getOutputStream());
                    out.write("HTTP/1.0 200 OK\n");
                    out.write("Content-Type: text/html\n");
                    out.write("\n");
                    out.write("<DocTag>\n");
                    out.write("<Status ");
                    out.write("CompletionTime=\"CompletionTimeValue\" ");
                    out.write("Date=\"DateValue\" ");
                    out.write("HostId=\"FakeNgamsServer:" + portNumber + "\" ");
                    out
                            .write("LastRequestStatUpdate=\"LastRequestStatUpdateValue\" ");
                    out.write("Message=\"MessageValue\" ");
                    out.write("RequestId=\"RequestIdValue\" ");
                    out.write("RequestTime=\"RequestTimeValue\" ");
                    out.write("State=\"StateValue\" ");
                    out.write("Status=\"StatusValue\" ");
                    out.write("SubState=\"SubStateValue\" ");
                    out.write("Version=\"VersionValue\" ");
                    out.write("/>\n");

                    out.write("<DiskStatus ");
                    out.write("Archive=\"ArchiveValue\" ");
                    out.write("AvailableMb=\"AvailableMbValue\" ");
                    out.write("BytesStored=\"BytesStoredValue\" ");
                    out.write("Checksum=\"DiskChecksumValue\" ");
                    out.write("Completed=\"CompletedValue\" ");
                    out.write("CompletionDate=\"CompletionDateValue\" ");
                    out.write("DiskId=\"DiskIdValue\" ");
                    out
                            .write("InstallationDate=\"InstallationDateValue\" ");
                    out.write("LastCheck=\"LastCheckValue\" ");
                    out.write("LogicalName=\"LogicalNameValue\" ");
                    out.write("Manufacturer=\"ManufacturerValue\" ");
                    out.write("MountPoint=\"MountPointValue\" ");
                    out.write("Mounted=\"MountedValue\" ");
                    out.write("NumberOfFiles=\"NumberOfFilesValue\" ");
                    out.write("SlotId=\"SlotIdValue\" ");
                    out
                            .write("TotalDiskWriteTime=\"TotalDiskWriteTimeValue\" ");
                    out.write("Type=\"TypeValue\" ");
                    out.write("/>\n");

                    out.write("<FileStatus ");
                    out.write("Checksum=\"FileChecksumValue\" ");
                    out.write("ChecksumPlugIn=\"ChecksumPlugInValue\" ");
                    out.write("Compression=\"CompressionValue\" ");
                    out.write("CreationDate=\"CreationDateValue\" ");
                    out.write("FileId=\"FileIdValue\" ");
                    out.write("FileName=\"FileNameValue\" ");
                    out.write("FileSize=\"FileSizeValue\" ");
                    out.write("FileStatus=\"FileStatusValue\" ");
                    out.write("FileVersion=\"FileVersionValue\" ");
                    out.write("Format=\"FormatValue\" ");
                    out.write("Ignore=\"IgnoreValue\" ");
                    out.write("IngestionDate=\"IngestionDateValue\" ");
                    out.write("Tag=\"TagValue\" ");
                    out
                            .write("UncompressedFileSize=\"UncompressedFileSizeValue\" ");
                    out.write("/>\n");
                    out.write("</DocTag>\n");
                    /*
                     * Important to close stream, otherwise the client might
                     * not terminate the input and hang waiting for more
                     * data.
                     */
                    out.close();
                }
            }
        } catch (Exception e) {
            Logger.getAnonymousLogger().log(Level.SEVERE,
                    "Connection issue", e);
        } finally {
            try {
                channel.socket().close();
            } catch (Exception e) {
            	e.printStackTrace();
            }
            try {
                channel.close();
            } catch (Exception e) {
            	e.printStackTrace();
            }
        }
        logger.info("stopped");
    }

    public synchronized void terminate() {
        this.terminate = true;
        notifyAll();
    }
    
    public synchronized boolean isTerminated() {
    	return this.terminate;
    }
}