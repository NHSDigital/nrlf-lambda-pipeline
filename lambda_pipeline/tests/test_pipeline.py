import json
from functools import cache
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest
from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayProxyEventModel as EventModel,
)
from lambda_pipeline.pipeline import (
    LambdaContext,
    _chain_steps,
    _decorate_step,
    _make_template_step,
    make_pipeline,
)
from lambda_pipeline.step_decorators import (
    PipelineSignatureError,
    PipelineStepOutputError,
)
from lambda_pipeline.types import FrozenDict, PipelineData
from pydantic import ValidationError


@cache
def _get_event():
    with open(Path(__file__).parent / "event.json") as f:
        return json.load(f)


@pytest.fixture()
def event():
    return EventModel(**_get_event())


@pytest.fixture()
def context():
    return LambdaContext()


@pytest.fixture()
def dependencies():
    return FrozenDict()


@pytest.fixture
def steps():
    def first_step(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        return PipelineData(first_step_result=data["input_data"].title())

    def second_step(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        return PipelineData(
            second_step_result=data["first_step_result"].upper(), **data
        )

    def third_step(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        _data = data.to_dict()
        return PipelineData(
            third_step_result=_data.pop("second_step_result") + " bar", **_data
        )

    return [first_step, second_step, third_step]


def __setitem(dictlike, key, value):
    dictlike[key] = value


def test__make_template_step():
    template_step = _make_template_step(str)
    assert template_step.__annotations__ == {
        "context": LambdaContext,
        "data": PipelineData,
        "dependencies": FrozenDict[str, Any],
        "event": str,
        "return": PipelineData,
    }

    with pytest.raises(NotImplementedError):
        template_step(data="foo", event="bar", context="spam", dependencies="eggs")


def test__decorate_step():
    def _undecorated_function(some_input: str) -> str:
        return some_input

    ##################################
    # Define some decorators here
    def _cast_inputs_to_ints(func):
        def wrapper(*args):
            args_as_ints = list(map(int, args))
            return func(*args_as_ints)

        return wrapper

    def _double_inputs(func):
        def wrapper(*args):
            doubled_args = list(map(lambda x: x * 2, args))
            return func(*doubled_args)

        return wrapper

    def _cast_output_to_string(func):
        def wrapper(*args):
            result = func(*args)
            return str(result)

        return wrapper

    decorators = [_cast_inputs_to_ints, _double_inputs, _cast_output_to_string]
    _decorated_function: FunctionType = _decorate_step(
        step=_undecorated_function, decorators=decorators
    )

    ##################################

    assert _undecorated_function("123") == "123"
    assert _decorated_function("123") == "246"


def test__chain_steps(steps, event, context, dependencies):
    chain = _chain_steps(
        steps=steps, event=event, context=context, dependencies=dependencies
    )
    result = chain(data=PipelineData(input_data="foo"))
    assert result.to_dict() == {
        "first_step_result": "Foo",
        "third_step_result": "FOO bar",
    }


def test_make_pipeline(steps, event, context, dependencies):
    pipeline = make_pipeline(
        steps=steps, event=event, context=context, dependencies=dependencies
    )
    result = pipeline(data=PipelineData(input_data="foo"))
    assert result.to_dict() == {
        "first_step_result": "Foo",
        "third_step_result": "FOO bar",
    }


@pytest.mark.parametrize(
    ("mutator", "exception_text"),
    (
        (
            lambda data, event, context, dependencies: __setitem(data, "foo", "bar"),
            "'PipelineData' object does not support item assignment",
        ),
        (
            lambda data, event, context, dependencies: setattr(event, "body", "foo"),
            '"APIGatewayProxyEventModel" is immutable and does not support item assignment',
        ),
        (
            lambda data, event, context, dependencies: __setitem(
                dependencies, "foo", "bar"
            ),
            "'FrozenDict' object does not support item assignment",
        ),
    ),
)
def test_make_pipeline__chain_inputs_are_immutable(
    event, context, mutator, exception_text
):
    def mutate_some_state(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        mutator(data=data, event=event, context=context, dependencies=dependencies)
        assert False, "should never get here!"

    pipeline = make_pipeline(
        steps=[mutate_some_state],
        event=event,
        context=context,
        dependencies={},
    )
    with pytest.raises(TypeError, match=exception_text):
        pipeline(data=PipelineData())


def test_make_pipeline__context_mutations_not_persisted(event):
    def mutate_some_state(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        context._function_name = "foo, bar"
        return PipelineData()

    context = LambdaContext()
    context._function_name = "spam, eggs"
    pipeline = make_pipeline(
        steps=[mutate_some_state],
        event=event,
        context=context,
        dependencies={},
    )
    pipeline(data=PipelineData())
    assert context._function_name == "spam, eggs"


def test_make_pipeline__step_signature_enforced(event, context):

    pipeline = make_pipeline(
        steps=[lambda x: x],
        event=event,
        context=context,
        dependencies={},
    )
    with pytest.raises(PipelineSignatureError):
        pipeline(data=PipelineData())


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "steps": ["not a FunctionType"],
            "event": event,
            "context": context,
            "dependencies": dependencies,
        },
        {
            "steps": steps,
            "event": "not an EventModel",
            "context": context,
            "dependencies": dependencies,
        },
        {
            "steps": steps,
            "event": event,
            "context": "not a LambdaContext",
            "dependencies": dependencies,
        },
        {
            "steps": steps,
            "event": event,
            "context": context,
            "dependencies": "not a dict-like",
        },
    ],
)
def test_make_pipeline__arguments_validated(kwargs):

    with pytest.raises(ValidationError):
        make_pipeline(**kwargs)


def test_make_pipeline__output_is_data_pipeline(event, context):
    def bad_step(
        data: PipelineData,
        event: EventModel,
        context: LambdaContext,
        dependencies: FrozenDict[str, Any],
    ) -> PipelineData:
        return "not a data pipeline"

    pipeline = make_pipeline(
        steps=[bad_step],
        event=event,
        context=context,
        dependencies={},
    )
    with pytest.raises(PipelineStepOutputError):
        pipeline(data=PipelineData())
