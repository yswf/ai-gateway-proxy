import os
import logging
from logging.handlers import TimedRotatingFileHandler
import sys

def setup_logging():
    # Ensure logs directory exists
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Root logger configuration
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    # Formatting
    formatter = logging.Formatter(
        "%(asctime)s | %(name)-15s | %(levelname)-7s | %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File output with daily rotation
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30, 
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logger
