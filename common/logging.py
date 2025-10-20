import logging
import os
from common.config import Config


def setup_logging():
    """Setup logging configuration and return logger instance"""
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(Config.LOG_DIR, 'app.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'  # Append mode
    )
    
    # Also add console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.addHandler(console_handler)
    
    return logger


# Create a global logger instance
logger = setup_logging()
