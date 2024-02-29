import json
from logging import getLogger

from example.api.handler import (
    EventModel,
    HandlerError,
    build_shared_dependencies,
    steps,
)
from example.api.response import response_400, response_500
from lambda_pipeline.pipeline import make_pipeline
from lambda_pipeline.types import LambdaContext, PipelineData

shared_dependencies = build_shared_dependencies()


def handler(event: dict, context: LambdaContext) -> dict[str, str]:
    pipeline = make_pipeline(
        steps=steps,
        event=EventModel(**event),
        context=context,
        dependencies=shared_dependencies,
        logger=getLogger(__name__),
    )

    try:
        return pipeline(data=PipelineData()).to_dict()
    except HandlerError as exc:
        return response_400(body=json.dumps({"message": str(exc)}))
    except Exception as exc:
        return response_500(details=f"{type(exc)}: {exc}")
