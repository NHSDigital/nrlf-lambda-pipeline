import json
from pathlib import Path

from aws_lambda_powertools import Logger
from pydantic import BaseModel

PKG_NAME = Path(__file__).parent.name
logger = Logger(service_name=PKG_NAME)


class Response(BaseModel):
    status_code: str
    body: str

    def __init__(self, status_code, body, details=""):
        if int(status_code) >= 300:
            logger.error(body if not details else details)
        else:
            logger.info(body)
        return super().__init__(status_code=status_code, body=body)


def response_200(body: str) -> dict:
    return Response(status_code="200", body=body).dict()


def response_400(body: str) -> dict:
    return Response(status_code="400", body=body).dict()


def response_500(details: str) -> dict:
    return Response(
        status_code="500",
        body=json.dumps({"message": "Internal Server Error"}),
        details=details,
    ).dict()
