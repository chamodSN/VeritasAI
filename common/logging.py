import logging
import json

logger = logging.getLogger("legal_agents")
logger.setLevel(logging.INFO)

def log_json(event: dict):
    print(json.dumps(event))