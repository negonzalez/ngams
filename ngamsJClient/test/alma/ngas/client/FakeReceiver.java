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
import java.io.OutputStreamWriter;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.logging.Level;
import java.util.logging.Logger;

/*
 * Special dummy server which reads accepts large files from the client and simply throws all the data away
 */
class FakeReceiver extends Thread {

    private boolean terminate = false;
    private String receivedCommand;
    private int portNumber;

    /**
     * 
     * @param inPortNumber
     */
    public FakeReceiver(int inPortNumber) {
        this.portNumber = inPortNumber;
    }

    /**
     * 
     * @return
     */
    public synchronized String getReceivedCommand() {
        String outString = this.receivedCommand;
        this.receivedCommand = null;
        return outString;
    }

    /**
     * 
     */
    @Override
    public void run() {
        ServerSocketChannel channel = null;
        try {
            channel = ServerSocketChannel.open();
            channel.configureBlocking(false);
            InetAddress inetAddress = InetAddress.getLocalHost();
            InetSocketAddress socketAddress = new InetSocketAddress(
                    inetAddress, this.portNumber);
            channel.socket().bind(socketAddress);
            while (!isTerminated()) {
                SocketChannel sc = channel.accept();
                Thread.sleep(100);
                if (sc != null) {
                    Socket socket = sc.socket();
                    // set a timeout because the read blocks instead of returning end-of-stream
                    socket.setSoTimeout(5000);
                    InputStreamReader isr = new InputStreamReader(socket.getInputStream()); 
                    
                    int count = 0;
                    try {
                    	while (isr.read() != -1) {
                    		count++;
                    	}
                        System.out.println("received " + count + " bytes");
                    }
                    catch (SocketTimeoutException e) {
                    	// nothing to be done
                    	// except maybe to understand why '-1' was never received
                    	// by the read() method...
                    	// why is that? The sender appears to close properly. The large file
                    	// is terminated by a newline, but the read() method never returns -1
                    	// if someone has time to find out, please let me know....
                    }                    	

                    OutputStreamWriter out = new OutputStreamWriter(socket
                            .getOutputStream());
                    out.write("HTTP/1.0 200 OK\n");
                    out.write("Content-Type: text/html\n");
                    out.write("\n");
                    out.write("<DocTag>\n");
                    out.write("<Status ");
                    out.write("CompletionTime=\"CompletionTimeValue\" ");
                    out.write("Date=\"DateValue\" ");
                    out.write("HostId=\"HostIdValue\" ");
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
        	e.printStackTrace();
            Logger.getAnonymousLogger().log(Level.SEVERE,
                    "Connection issue", e);
        } finally {
            try {
                channel.socket().close();
            } catch (Exception e) {
            }
            try {
                channel.close();
            } catch (Exception e) {
            }
        }
    }

    /**
     * 
     */
    public synchronized void terminate() {
        this.terminate = true;
        this.notifyAll();
    }
    
    /**
     * 
     * @return
     */
    private boolean isTerminated() {
    	return terminate;
    }
}