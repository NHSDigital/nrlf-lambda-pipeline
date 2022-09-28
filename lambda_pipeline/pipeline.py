from functools import reduce
from types import FunctionType
from typing import Any


from pydantic import BaseModel

from lambda_pipeline.step_decorators import (
    do_not_persist_changes_to_context,
    enforce_step_signature,
    logging,
    validate_arguments,
    validate_output,
)
from lambda_pipeline.types import FrozenDict, PipelineData, LambdaContext


def _make_template_step(event_type: type) -> FunctionType:
    """A factory method for creating the template for steps"""

    def _TEMPLATE_STEP(
        data: PipelineData,
        event: event_type,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        raise NotImplementedError

    return _TEMPLATE_STEP


def _decorate_step(step: FunctionType, decorators: list[FunctionType]) -> FunctionType:
    for deco in reversed(decorators):
        step = deco(step)
    return step


def _chain_steps(
    steps: list[FunctionType],
    event: BaseModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
) -> FunctionType:
    return lambda data: reduce(
        lambda _data, step: step(
            data=_data,
            event=event,
            context=context,
            dependencies=dependencies,
        ),
        steps,
        data,
    )


@validate_arguments
def make_pipeline(
    steps: list[FunctionType],
    event: BaseModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
) -> FunctionType:

    event.__config__.allow_mutation = False
    dependencies = FrozenDict(dependencies)

    template_step = _make_template_step(event_type=type(event))
    step_decorators = [
        lambda step: enforce_step_signature(step=step, template_step=template_step),
        validate_arguments,
        lambda step: validate_output(step=step, template_step=template_step),
        lambda step: do_not_persist_changes_to_context(
            step=step, initial_context=context
        ),
        logging,
    ]

    decorated_steps = map(
        lambda step: _decorate_step(step=step, decorators=step_decorators),
        steps,
    )

    return _chain_steps(
        steps=decorated_steps,
        event=event,
        context=context,
        dependencies=dependencies,
    )
