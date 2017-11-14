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

class RedirectServer extends Thread {
	private Logger logger = Logger.getLogger("RedirectServer");
    private final int REDIRECT_TEST_PORT;

	private final int TEST_PORT1;

	private boolean terminate = false;

    private int myRepeats;

    public RedirectServer(int inRepeats, int redirectPort, int port) {
        this.myRepeats = inRepeats;
        this.REDIRECT_TEST_PORT = redirectPort;
        this.TEST_PORT1 = port;
    }

    @Override
    public void run() {
        ServerSocketChannel ssc = null;
        try {
            ssc = ServerSocketChannel.open();
            ssc.configureBlocking(false);
            InetAddress inetAddress = InetAddress.getLocalHost();
            InetSocketAddress socketAddress = new InetSocketAddress(
                    inetAddress, REDIRECT_TEST_PORT);
            ssc.socket().bind(socketAddress);
            logger.info("waiting on " + REDIRECT_TEST_PORT);
            while (!isTerminated()) {
                Thread.sleep(500);
                SocketChannel sc = ssc.accept();
                if (sc != null) {
                    Socket socket = sc.socket();
                    int port = REDIRECT_TEST_PORT;
                    this.myRepeats--;
                    if (this.myRepeats == 0) {
                        port = TEST_PORT1;
                    }
                    LineNumberReader in = new LineNumberReader(
                            new InputStreamReader(socket.getInputStream()));
                    String input = in.readLine();
                    String receivedCommand = input.substring(4, input
                            .length() - 9).replaceAll("/", "").trim();
                    logger.info("" + myRepeats + ": redirecting to " + port);
                    OutputStreamWriter out = new OutputStreamWriter(socket
                            .getOutputStream());
                    out.write("HTTP/1.0 301 Moved Permanently\n");
                    out.write("Location: http://" + inetAddress.getHostAddress()
                            + ":" + port + "/" + receivedCommand + "\n");
                    out.write("\n\n");
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
                ssc.socket().close();
            } catch (Exception e) {
            }
            try {
                ssc.close();
            } catch (Exception e) {
            }
        }
        logger.info("stopped");
    }

    public synchronized void terminate() {
        this.terminate = true;
        this.notifyAll();
    }
    
     boolean isTerminated() {
    	return this.terminate;
    }
}