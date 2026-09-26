# app/core/logging_config.py
import os
import sys
from logging.config import dictConfig

LOG_LEVEL = "INFO"

# Vercel's filesystem is read-only outside /tmp - a RotatingFileHandler on a
# relative path would raise on the very first log call, crashing every cold
# start. Vercel sets this on every deployment/runtime, so use it to skip the
# file handler there and let stdout (which Vercel already captures as
# function logs) carry everything instead.
_ON_VERCEL = os.getenv("VERCEL") is not None

_handler_names = ["console"] if _ON_VERCEL else ["console", "file"]

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        },
        **(
            {}
            if _ON_VERCEL
            else {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": "app.log",
                    "maxBytes": 10_000_000,
                    "backupCount": 5,
                },
            }
        ),
    },
    "loggers": {
        "": {
            "handlers": _handler_names,
            "level": LOG_LEVEL,
        },
        "uvicorn": {"handlers": _handler_names, "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": _handler_names, "level": "INFO", "propagate": False},
    },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
