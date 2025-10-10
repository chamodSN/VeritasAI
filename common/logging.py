import logging
import os
from common.config import Config

def setup_logging():
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(Config.LOG_DIR, 'app.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)