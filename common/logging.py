# common/logging.py (No changes necessary, but used for RA logging)
import logging
import os


def setup_logger():
    logger = logging.getLogger("LegalCaseResearcher")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("audit.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logger()
