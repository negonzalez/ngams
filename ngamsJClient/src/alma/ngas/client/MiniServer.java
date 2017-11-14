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

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.Vector;
import java.util.logging.Logger;

/**
 * Listens for incoming files from NGAS. This class is instantiated and the
 * instance launched in its own thread when a subscribe command is executed.
 */
class MiniServer implements Runnable {
    /**
     * Port for incoming files. This object listens for requests arriving on
     * this port.
     */
    int port;

    /**
     * Whether to carry on listening. If serve is set to false, the thread in
     * which the mini server is running will end.
     */
    boolean serve = true;

    /**
     * Whether a file is currently being saved to disk.
     */
    boolean takingFile = false;

    /**
     * Whether the server is set up and ready to listen for incoming files.
     * Subscribe waits for this to be set to true before sending the SUBSCRIBE
     * command.
     */
    boolean ready = false;

    /**
     * The log4j logger for recording events.
     */
    Logger logger;

    /**
     * The FileReceivedEventListeners who are notified of file arrivals from a
     * subscription.
     */
    Vector<FileReceivedEventListener> listOfFileReceivedEventListeners = new Vector<FileReceivedEventListener>();

    /**
     * The directory where to save incoming files.
     */
    String dataRaw;

    /**
     * The number of bytes to read at a time for incoming files.
     */
    int blockSize = 1024;

    /**
     * Instantiate the class MiniServer.
     * 
     * @param port
     *            The port on which to listen for incoming requests.
     * @param blockSize
     *            The number of bytes to read at a time from incoming files.
     * @param dataRaw
     *            The directory where to store incoming files.
     * @param logger
     *            The log4j logger (properly set up already) to record events.
     */
    MiniServer(int port, int blockSize, String dataRaw, Logger logger) {
        this.port = port;
        this.blockSize = blockSize;
        this.dataRaw = dataRaw;
        this.logger = logger;
    }

    /**
     * Sends a message to all the registered FileReceivedEventListeners (stored
     * in the Vector listOfFileReceivedEventListeners) that a new file has
     * arrived. Note: the number sent is the total number of files received in
     * this session so far. A session is a lifetime of the thread containing the
     * miniserver and corresponds to a single subscribe command
     * 
     * @param numFiles
     *            The number of files so far received.
     */
    void notifyListenersOfFileArrival(int numFiles) {
        FileReceivedEventListener listener;
        for (int i = 0; i < listOfFileReceivedEventListeners.size(); i++) {
            listener = (FileReceivedEventListener) listOfFileReceivedEventListeners
                    .elementAt(i);
            listener.fileReceived(new FileReceivedEvent(numFiles));
        }
        logger.info("miniServer is sending message to listeners that a new "
                + "file has arrived");
    }

    /**
     * Main body of server. Contains a while (serve) { ... } loop, so setting
     * serve to false makes running terminate.
     */
    public void run() {
        takingFile = false;
        try {
            ServerSocketChannel ssc = ServerSocketChannel.open();
            ssc.configureBlocking(false);
            InetAddress inetAddress = InetAddress.getLocalHost();
            InetSocketAddress socketAddress = new InetSocketAddress(
                    inetAddress, port);
            ssc.socket().bind(socketAddress);
            int i = 0;
            while (serve) {
                ready = true;
                SocketChannel sc = ssc.accept();
                if (sc != null) {
                    Socket client = sc.socket();
                    takingFile = true;
                    takeBinaryFile(client, i);
                    takingFile = false;
                    sc.close();
                    i = i + 1;
                    notifyListenersOfFileArrival(i);
                }
            }
            ssc.close();
            ready = false;
        } catch (IOException e) {
            logger.warning("IOException in MiniServer.run; description is: "
                    + e.toString());
        } catch (IllegalArgumentException e) {
            logger.warning("IllegalArgumentException in Miniserver.run; "
                    + "description is: " + e.toString());
        }
    }

    /**
     * Saves a single file to disk. The file is sent by NGAS.
     * 
     * @param client
     *            The Socket object which NGAS sends data through.
     * @param fileNumber
     *            As files arrive they are given temporary names based on how
     *            many other files have already been received. This name is
     *            "serverOut" + fileNumber. So the temporary name of the first
     *            file to be received in a session is serverOut0 etc. This
     *            parameter is passed by the run() method. Note: the code for
     *            parsing the HTTP POST header can be replaced by a standard
     *            class written for this purpose this could provide extra
     *            flexibility.
     * @return Object giving information that comes from the HTTP header
     *         received by NGAS.
     */
    FileInfo takeBinaryFile(Socket client, int fileNumber) {
        String fileName = dataRaw + "serverOut" + fileNumber;
        String fileNameFromHeader = null;
        String newline = "\r\n";
        DataOutputStream fileOutputStream = null;
        try {
            // Set up objects for reading/writing text/data to client/local
            // file.
            DataInputStream in = new DataInputStream(client.getInputStream());
            PrintWriter textOut = new PrintWriter(new OutputStreamWriter(client
                    .getOutputStream()));
            // Get the header.
            // System.out.println("about to get header");
            String header = "";
            char c;
            do {
                c = (char) in.readByte();
                header = header + String.valueOf(c);
            } while (!header.endsWith(newline + newline));
            // System.out.println(":"+header+":");
            // Get the filename from the header, to determine the mime type
            int i = header.indexOf("filename=\"");
            int j = header.indexOf("\"", i + 10);
            if (i == -1 || j == -1) {
                // So such substring found
                logger.warning("Filename wasn't specified in the HTTP header "
                        + "sent by NGAS, for file " + fileNumber);
                return new FileInfo(null, null);
            } else {
                // We have found the filename from the header.
                // obtain the correct file extension, and set up the
                // FileOutputStream to write data to this file.
                fileNameFromHeader = header.substring(i + 10, j);
                File outFile = new File(fileName);
                if (outFile.exists())
                    outFile.delete();
                FileOutputStream fos = new FileOutputStream(outFile);
                fileOutputStream = new DataOutputStream(fos);
            }
            // Get the length from the header.
            i = header.indexOf("length: ");
            if (i == -1) {
                logger.warning("Length wasn't specified in the HTTP header "
                        + "sent by NGAS, for file " + fileNumber
                        + " with name " + fileNameFromHeader);
                ;
                return new FileInfo(null, fileNameFromHeader);
            }
            j = header.indexOf(newline, i);
            int length = Integer.valueOf(header.substring(i + 8, j)).intValue();
            // Get the file from the client; storing it into the file.
            byte[] buf = new byte[blockSize];
            int nRead = 0, totalRead = 0;
            // System.out.println("about to enter while, length is "+length);
            while (totalRead < length
                    && (nRead = in.read(buf, 0, blockSize)) > 0) {
                totalRead = totalRead + nRead;
                fileOutputStream.write(buf, 0, nRead);
                fileOutputStream.flush();
                // System.out.println("have read "+ totalRead + " of " +length+
                // "
                // so far; and " + nRead + " this time.");
            }
            // System.out.println("end of while");
            // Say 'goodbye' to the client.
            textOut.print("HTTP/1.0 200\nContent-Type: text/plain\n\n");
            // Close down the (in/out)putstreams.
            in.close();
            textOut.close();
            fileOutputStream.close();
            return new FileInfo(null, fileNameFromHeader);
        } catch (IOException e) {
            logger.warning("IOEXception in MiniServer.takeBinaryFile; file "
                    + "name is: "
                    + ((fileNameFromHeader == null) ? "unknown"
                            : fileNameFromHeader) + "; description is: "
                    + e.toString());
            return new FileInfo(null, fileNameFromHeader);
        }
        finally {
        	if (fileOutputStream != null) try {fileOutputStream.close();} catch (IOException e) {logger.warning(e.getMessage());}
        }
    }
}