# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality for creating a global logger for the maya submitter.
"""
from __future__ import absolute_import, print_function

import logging
import logging.handlers
import os
import tempfile
from typing import Any

import maya.OpenMaya as om  # type: ignore # pylint: disable=import-error

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


class MayaConsoleHandler(logging.Handler):
    """A handler using maya functions to output messages to the scriptEditor."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record: Any) -> None:
        """
        Directs a given record to Maya's script editor.
        """
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            om.MGlobal.displayError(msg)
        elif record.levelno == logging.WARNING:
            om.MGlobal.displayWarning(msg)
        elif record.levelno <= logging.INFO:
            om.MGlobal.displayInfo(msg)


class MayaLogger(logging.Logger):
    def __init__(self, name):
        super().__init__(name)

        console_handler = MayaConsoleHandler()
        fmt = logging.Formatter(
            "[%(name)s] %(levelname)8s:  (%(threadName)-10s)"
            "  %(module)s %(funcName)s: %(message)s"
        )
        console_handler.setFormatter(fmt)

        self.addHandler(console_handler)

        log_file = os.path.expanduser("~/.deadline/logs/submitters/maya.log")

        if not os.path.exists(os.path.dirname(log_file)):
            # make sure the directories exist.
            try:
                os.makedirs(os.path.dirname(log_file))
            except (IOError, OSError):
                log_file = os.path.join(tempfile.gettempdir(), f"rfm.{os.getpid()}.log")

        if not os.access(os.path.dirname(log_file), os.W_OK | os.R_OK):
            # if we can't access the log file use a temp file.
            log_file = os.path.join(tempfile.gettempdir(), f"rfm.{os.getpid()}.log")

        disk_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=5
        )

        # we use a different format for the disk log, to get a time stamp.
        fmtf = logging.Formatter(
            "%(asctime)s %(levelname)8s {%(threadName)-10s}"
            ":  %(module)s %(funcName)s: %(message)s"
        )
        disk_handler.setFormatter(fmtf)
        self.addHandler(disk_handler)

        self.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Retrieves the specified logger.
    """
    logging_class = logging.getLoggerClass()
    logging.setLoggerClass(MayaLogger)
    logger = logging.getLogger(name)
    logging.setLoggerClass(logging_class)

    return logger
