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

/**
 * Info from NGAS about incoming files. Specifically, files that are received by
 * the miniserver as a result of a SUBSCRIBE command are sent via HTTP POST.
 */
class FileInfo {
    /**
     * The mime type extracted from the HTTP header.
     */
    String mimeType;

    /**
     * The file name extracted from the HTTP header.
     */
    String fileName;

    /**
     * Constructs an instance of this class, with particular information stored
     * in it.
     * 
     * @param mimeType
     *            The mime-type.
     * @param fileName
     *            The filename.
     */
    FileInfo(String mimeType, String fileName) {
        this.mimeType = mimeType;
        this.fileName = fileName;
    }
}