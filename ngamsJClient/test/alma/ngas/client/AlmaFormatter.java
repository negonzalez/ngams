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
import java.io.PrintWriter;
import java.io.StringWriter;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.logging.Formatter;
import java.util.logging.LogRecord;

/**
 * Added by amanning because I can't stand the jul logging output format. 
 * 
 * A <code>SimpleFormatter</code> formats log records into
 * short human-readable messages, typically one or two lines.
 *
 * @author Sascha Brawer (brawer@acm.org)
 */
public class AlmaFormatter extends Formatter
{

  /**
   * An instance of a DateFormatter that is used for formatting
   * the time of a log record into a human-readable string,
   * according to the rules of the current locale.  The value
   * is set after the first invocation of format, since it is
   * common that a JVM will instantiate a SimpleFormatter without
   * ever using it.
   */
  private DateFormat dateFormat;

  /**
   * The character sequence that is used to separate lines in the
   * generated stream. Somewhat surprisingly, the Sun J2SE 1.4
   * reference implementation always uses UNIX line endings, even on
   * platforms that have different line ending conventions (i.e.,
   * DOS). The GNU implementation does not replicate this bug.
   *
   * @see Sun bug parade, bug #4462871,
   * "java.util.logging.SimpleFormatter uses hard-coded line separator".
   */
  static final String lineSep = System.getProperty("line.separator");


  /**
   * Formats a log record into a String.
   *
   * @param record the log record to be formatted.
   *
   * @return a short human-readable message, typically one or two
   *   lines.  Lines are separated using the default platform line
   *   separator.
   *
   * @throws NullPointerException if <code>record</code>
   *         is <code>null</code>.
   */
  public String format(LogRecord record)
  {
    StringBuffer buf = new StringBuffer(180);

    if (dateFormat == null)
      dateFormat = new SimpleDateFormat("HH:mm:ss.SSS");

    buf.append(dateFormat.format(new Date(record.getMillis())));
    buf.append(" [").append(Thread.currentThread().getName()).append("] ");
    String className = record.getSourceClassName();
    buf.append(className.substring(className.lastIndexOf(".") + 1));
    buf.append(' ');
    buf.append(record.getSourceMethodName());
    buf.append(": ");

    buf.append(record.getLevel());
    buf.append(": ");
    buf.append(formatMessage(record));

    buf.append(lineSep);

    Throwable throwable = record.getThrown();
    if (throwable != null)
      {
        StringWriter sink = new StringWriter();
        throwable.printStackTrace(new PrintWriter(sink, true));
        buf.append(sink.toString());
      }

    return buf.toString();
  }
}
