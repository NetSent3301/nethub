"""
Sistema de logging estructurado para NetHUB Ultimate.
Reemplaza print() con niveles, timestamps y salida a archivo.
"""
import os
import sys
import logging
import traceback
from datetime import datetime

_LOG_FILE = None
_LOGGERS = {}

LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def _get_log_path():
    global _LOG_FILE
    if _LOG_FILE is None:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        _LOG_FILE = os.path.join(log_dir, "nethub.log")
    return _LOG_FILE


class ModuleFilter(logging.Filter):
    def __init__(self, module_name):
        super().__init__()
        self.module_name = module_name

    def filter(self, record):
        return True


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        record.msg = f"{color}{record.msg}{self.RESET}" if color else record.msg
        return super().format(record)


def get_logger(name="nethub"):
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # File handler (always, with rotation-like append)
    try:
        fh = logging.FileHandler(_get_log_path(), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(fh)
    except Exception:
        pass

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))
    logger.addHandler(ch)

    _LOGGERS[name] = logger
    return logger


def log_exception(logger, msg="", level="error"):
    """Log an exception with traceback."""
    tb = traceback.format_exc()
    log_fn = getattr(logger, level, logger.error)
    if tb and tb != "NoneType: None\n":
        log_fn(f"{msg} | {tb.strip().split(chr(10))[-1]}" if msg else tb.strip())
    elif msg:
        log_fn(msg)
