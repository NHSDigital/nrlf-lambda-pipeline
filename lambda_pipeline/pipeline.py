from logging import Logger
from typing import Any, Callable, Dict, Iterable, Union

from pydantic import BaseModel

from lambda_pipeline.step_decorators import (
    do_not_persist_changes_to_context,
    enforce_step_signature,
    validate_arguments,
    validate_output,
)
from lambda_pipeline.types import FrozenDict, LambdaContext, PipelineData


def _make_template_step(event_type: type) -> Callable:
    """
    Create a template step function.

    Args:
        event_type (type): The type of event that the step function expects.

    Returns:
        Callable: The template step function.

    """

    def _TEMPLATE_STEP(
        data: PipelineData,
        event: event_type,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
        logger: Logger,
    ) -> PipelineData:
        raise NotImplementedError

    return _TEMPLATE_STEP


def _decorate_step(step: Callable, decorators: list[Callable]) -> Callable:
    """
    Decorates a step function with a list of decorators in reverse order.

    Args:
        step (Callable): The step function to be decorated.
        decorators (list[Callable]): The list of decorators to be applied.

    Returns:
        Callable: The decorated step function.
    """
    for deco in reversed(decorators):
        step = deco(step)
    return step


def _chain_steps(
    steps: Iterable[Callable],
    event: BaseModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
    logger: Logger,
) -> Callable:
    """
    Chains a series of steps together and returns a callable function that executes the steps in sequence.

    Args:
        steps (Iterable[Callable]): The steps to be executed in sequence.
        event (BaseModel): The event data.
        context (LambdaContext): The Lambda context.
        dependencies (FrozenDict[str, Any]): The dependencies required by the steps.
        logger (Logger): The logger object.

    Returns:
        Callable: A function that executes the steps in sequence.
    """

    def chain(data: PipelineData) -> PipelineData:
        for step in steps:
            data = step(
                data=data,
                event=event,
                context=context,
                dependencies=dependencies,
                logger=logger,
            )
        return data

    return chain


@validate_arguments
def make_pipeline(
    steps: list[Callable],
    event: BaseModel,
    context: LambdaContext,
    dependencies: Union[Dict[str, Any], FrozenDict[str, Any]],
    logger: Logger,
    verbose=False,
) -> Callable:
    """
    Creates a pipeline by chaining together a series of steps.

    Args:
        steps (list[Callable]): A list of callable steps to be executed in the pipeline.
        event (BaseModel): The input event for the pipeline.
        context (LambdaContext): The Lambda execution context.
        dependencies (Union[Dict[str, Any], FrozenDict[str, Any]]): The dependencies required by the pipeline steps.
        logger (Logger): The logger to be used for logging.
        verbose (bool, optional): Whether to enable verbose logging. Defaults to False.

    Returns:
        Callable: A callable representing the pipeline.
    """

    event.model_config["frozen"] = True

    if not isinstance(dependencies, FrozenDict):
        dependencies = FrozenDict(dependencies)

    template_step = _make_template_step(event_type=type(event))

    # Decorators to be applied to each step
    step_decorators = [
        enforce_step_signature(template_step=template_step),
        validate_arguments,
        validate_output(template_step=template_step),
        do_not_persist_changes_to_context(initial_context=context),
    ]

    decorated_steps = [_decorate_step(step, step_decorators) for step in steps]

    return _chain_steps(
        steps=decorated_steps,
        event=event,
        context=context,
        dependencies=dependencies,
        logger=logger,
    )
