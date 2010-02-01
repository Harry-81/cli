"""cli.log - logging applications

Copyright (c) 2008-2010 Will Maier <will@m.aier.us>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""

import logging
from logging import Formatter, StreamHandler

from cli.app import CommandLineApp

__all__ = ["LoggingApp"]

class FileHandler(logging.FileHandler):

    def close(self):
        """Override close().
        
        We leave the file open because the application may have
        multiple threads that still need to write to it. Python
        should GC the fd when it goes out of scope, anyway.
        """
        pass

class NullHandler(logging.Handler):
    """A blackhole handler.

    NullHandler simply ignores all messages it receives.
    """

    def emit(self, record):
        """Ignore the record."""
        pass

class CommandLineLogger(logging.Logger):
    """Provide extra configuration smarts for loggers.

    In addition to the powers of a regular logger, a CommandLineLogger can
    set its verbosity levels based on a populated argparse.Namespace.
    """
    default_level = logging.WARN
    silent_level = logging.CRITICAL

    def setLevel(self, ns=None):
        """Set the logging level of this handler.

        ns is an object (like an argparse.Namespace) with the following
        attributes:
            
            verbose     integer
            quiet       integer
            silent      True/False
        """
        level = 10 * (ns.quiet - ns.verbose)

        if ns.silent:
            level = self.silent_level
        elif level <= logging.NOTSET:
            level = logging.DEBUG

        self.level = level

class LoggingApp(CommandLineApp):
    """A command-line application that knows how to log.

    A LoggingApp provides a 'log' attribute, which is a logger (from
    the logging module). The logger's verbosity is controlled via
    handy options ('verbose', 'quiet', 'silent') and sends its
    output to stderr by default (though it will log to a file if the
    'logfile' attribute is not None). Non-stderr streams can be
    requested by setting the 'stream' attribute to something besides
    None.
    """

    def __init__(self, main, stream=sys.stdout, logfile=None,
            message_format="%(message)s", 
            date_format="%(asctime)s %(message)s", **kwargs):
        self.logfile = logfile
        self.stream = stream
        self.message_format = message_format
        self.date_format = date_format
        super(LoggingApp, self).__init__(main, **kwargs)

    def setup(self):
        super(LoggingApp, self).setup()

        # Add logging-related options.
        self.add_param("-l", "--logfile", default=self.logfile, 
                help="log to file (default: log to stdout)", action="count")
        self.add_param("-q", "--quiet", default=0, help="decrease the verbosity",
                action="count")
        self.add_param("-s", "--silent", default=False, help="only log warnings",
                action="store_true")
        self.add_param("-v", "--verbose", default=0, help="raise the verbosity",
                action="count")

        # Create logger.
        logging.setLoggerClass(CommandLineLogger)
        self.log = logging.getLogger(self.name)

        # Create formatters.
        message_formatter = Formatter(self.message_format)
        date_formatter = Formatter(self.date_format)
        verbose_formatter = Formatter()
        self.formatter = message_formatter

        self.log.level = self.log.default_level

    def pre_run(self):
        """Configure logging before running the app."""
        super(LoggingApp, self).pre_run()
        self.log.setLevel(self.args)

        if self.logfile is not None:
            file_handler = FileHandler(self.logfile)
            file_handler.setFormatter(self.formatter)
            self.log.addHandler(file_handler)
        elif self.stream is not None:
            stream_handler = StreamHandler(self.stream)
            stream_handler.setFormatter(self.formatter)
            self.log.addHandler(stream_handler)

        # The null handler simply drops all messages.
        if not self.log.handlers:
            self.log.addHandler(NullHandler())

