from copy import deepcopy
from functools import wraps
from typing import Callable

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import validate_call


class PipelineSignatureError(Exception):
    """
    Exception raised when there is an error with the pipeline signature.
    """


class PipelineStepOutputError(Exception):
    """
    Exception raised when there is an error with the output of a pipeline step.
    """


def enforce_step_signature(template_step: Callable) -> Callable:
    """
    Decorator that enforces the signature of a step function.

    Args:
        template_step (Callable): The template step function with the expected signature.

    Returns:
        Callable: The decorated step function.

    Raises:
        PipelineSignatureError: If the step function does not meet the expected signature.
    """

    def _enforce_signature(step: Callable):
        if step.__annotations__ != template_step.__annotations__:
            raise PipelineSignatureError(
                f"step {step.__name__} does not meet the expected signature:\n"
                f"{template_step.__annotations__}\nGot:\n{step.__annotations__}"
            )
        return step

    return _enforce_signature


def validate_arguments(step: Callable):
    """
    Decorator that applies argument validation to a step function.

    Args:
        step (Callable): The step function to be decorated.

    Returns:
        Callable: The decorated step function with argument validation applied.
    """
    return validate_call(config={"arbitrary_types_allowed": True})(step)


def validate_output(template_step: Callable) -> Callable[[Callable], Callable]:
    """
    Decorator that validates the output of a step function.

    Args:
        template_step (Callable): The template step function.

    Returns:
        Callable[[Callable], Callable]: The decorated step function.

    Raises:
        PipelineStepOutputError: If the output of the step function does not match the expected type.
    """
    expected_type = template_step.__annotations__["return"]

    def wrapper(step: Callable):
        @wraps(step)
        def _check_output(*args, **kwargs):
            result = step(*args, **kwargs)
            if type(result) != expected_type:
                raise PipelineStepOutputError(
                    f"step {step.__name__}: was expecting a return type '{expected_type}', but got '{type(result)}'"
                )
            return result

        return _check_output

    return wrapper


def do_not_persist_changes_to_context(initial_context: LambdaContext) -> Callable:
    """
    Decorator that prevents changes made to the context from being persisted.

    Args:
        initial_context (LambdaContext): The initial context to be used.

    Returns:
        Callable: The decorated function.
    """
    initial_context = deepcopy(initial_context)

    def wrapper(step: Callable):
        @wraps(step)
        def _replace_context(context: LambdaContext, *args, **kwargs):
            return step(context=initial_context, *args, **kwargs)

        return _replace_context

    return wrapper
