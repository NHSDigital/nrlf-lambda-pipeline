import json
import os
from logging import Logger
from typing import Any

from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayProxyEventModel as EventModel,
)

from example.api.response import response_200
from example.some_third_party_lib.some_third_party_tool import (
    validate_x_request_url as _validate_x_request_url,
)
from lambda_pipeline.types import FrozenDict, LambdaContext, PipelineData

MIN_AUTH_LEVEL = 2


class HandlerError(Exception):
    pass


def build_shared_dependencies():
    return {}


def authorise(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of a step that may throw an exception"""
    auth_level = int(event.headers["auth_level"])
    if auth_level < MIN_AUTH_LEVEL:
        raise HandlerError("Minimum authorisation not satisfied")

    return data


def validate_x_request_url(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of standardising an unstandardised third party tool by wrapping"""
    try:
        _validate_x_request_url(x_request_url=event.headers.get("x-request-url"))
    except ValueError as exc:
        raise HandlerError(str(exc))
    return data


def a_flaky_step(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of a step that will raise a 500 in the right conditions"""
    if os.environ.get("FLAKE_OUT"):
        raise Exception("Some I/O flaked out!")
    return data


def intermediate_step(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of an intermediate step that mutates a pipeline data field"""
    return PipelineData(something_for_later="hello, world")


def read_document_from_db(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of a step that mutates the pipeline 'data' "body" field, which is used in the response"""

    return PipelineData(
        body={
            "id": 123,
            "content-type": "application/json",
            "message": data["something_for_later"],
        }
    )


def render_response(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> PipelineData:
    """An example of a step that mutates the pipeline 'data' "body" field, which is used in the response"""
    response = response_200(body=json.dumps(data["body"]))
    return PipelineData(response)


steps = [
    authorise,
    validate_x_request_url,
    a_flaky_step,
    intermediate_step,
    read_document_from_db,
    render_response,
]
