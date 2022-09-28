from pathlib import Path

from aws_lambda_powertools import Logger

PKG_NAME = Path(__file__).parent.name
logger = Logger(service_name=PKG_NAME)
