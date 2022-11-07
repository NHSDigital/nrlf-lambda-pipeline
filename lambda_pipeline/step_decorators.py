from copy import deepcopy
from functools import wraps
from types import FunctionType

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import validate_arguments as _validate_arguments


class PipelineSignatureError(Exception):
    pass


class PipelineStepOutputError(Exception):
    pass


def enforce_step_signature(
    step: FunctionType, template_step: FunctionType
) -> FunctionType:
    if step.__annotations__ != template_step.__annotations__:
        raise PipelineSignatureError(
            f"step {step.__name__} does not meet the expected signature:\n"
            f"{template_step.__annotations__}\nGot:\n{step.__annotations__}"
        )
    return step


def validate_arguments(step: FunctionType):
    return _validate_arguments(config=dict(arbitrary_types_allowed=True))(step)


def validate_output(step: FunctionType, template_step: FunctionType) -> FunctionType:
    expected_type = template_step.__annotations__["return"]

    @wraps(step)
    def wrapper(*args, **kwargs):
        result = step(*args, **kwargs)
        if type(result) != expected_type:
            raise PipelineStepOutputError(
                f"step {step.__name__}: was expecting a return type '{expected_type}', but got '{type(result)}'"
            )
        return result

    return wrapper


def do_not_persist_changes_to_context(
    step: FunctionType, initial_context: LambdaContext
) -> FunctionType:
    initial_context = deepcopy(initial_context)

    @wraps(step)
    def wrapper(context: LambdaContext, *args, **kwargs):
        return step(context=initial_context, *args, **kwargs)

    return wrapper
