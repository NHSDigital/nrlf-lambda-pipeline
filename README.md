# lambda-pipeline

Robust implementation of step chaining for AWS Lambda executions.

# For users

## Installation

Bleeding edge:

```
pip install git+https://github.com/NHSDigital/nrlf-lambda-pipeline.git
```

or a specific tag:

```
pip install git+https://github.com/NHSDigital/nrlf-lambda-pipeline.git@v0.1.0
```

## Usage

### 1. Define a list of steps

The list of steps indicates to `make_pipeline` the order in which to apply sequential steps on to the source event, e.g.

```python
steps = [
    authorise,
    validate_x_request_url,
    a_flaky_step,
    intermediate_step,
    read_document_from_db,
]
```

### 2. Define your pipeline steps as functions with the required signature

All pipeline steps must be annotated with and adhere to the following signature:

```python
def func(data: PipelineData, context: LambdaContext, event: EventModel, dependencies: FrozenDict[str, Any]) -> PipelineData
```

Noting that:

- `make_pipeline` will explicitly enforce this signature internally.
- You provide the `EventModel` class. It is recommended to use one of the predefined models from [aws-lambda-powertools](https://awslabs.github.io/aws-lambda-powertools-python/latest/utilities/parser/#built-in-models).
- `PipelineData` is used to pass data between sequential steps
- `PipelineData` objects are `FrozenDict` objects internally, and are therefore immutable and so you must create a new `PipelineData` in the response of each step,
- `make_pipeline` will force both `event` and `dependencies` to be immutable, so that they can be shared deterministically between steps (and in the case of `dependencies` between lambda invocations).
- While `context` is technically mutable within a step, changes to `context` are not persisted between steps.

### 3. Wrap up any external functions to match the function signature

For example:

```python
def _validate_x_request_url(x_request_url: str):
    """Doesn't match the required step signature!"""
    if x_request_url == "something":
        raise ValueError("Invalid value for 'x_request_url'")


def validate_x_request_url(
    data: PipelineData,
    event: EventModel,
    context: LambdaContext,
    dependencies: FrozenDict[str, Any],
) -> PipelineData:

    """An example of standardising an unstandardised third party tool by wrapping"""
    try:
        _validate_x_request_url(x_request_url=event.headers.get("x-request-url"))
    except ValueError as exc:
        raise PipelineError(str(exc))
    return data
```

### 4. Import your steps from your handler module to build your pipeline

```python
from example.api.handler import EventModel, build_shared_dependencies, steps
from lambda_pipeline.pipeline import make_pipeline
from lambda_pipeline.types import PipelineData, LambdaContext

shared_dependencies = build_shared_dependencies()

def handler(event: dict, context: LambdaContext = None) -> dict[str, str]:
    if context is None:
        context = LambdaContext()

    pipeline = make_pipeline(
        steps=steps,
        event=EventModel(**event),
        context=context,
        dependencies=shared_dependencies,
    )

    return pipeline(data=PipelineData()).to_dict()
```

## Examples from this repo

Set yourself up with (for example with `ipython`):

```python
from example.api.index import handler
from example.api.tests import example_event
```

### 1. Happy path

```python
event = example_event(headers={"auth_level": 10, "x-request-url": "example.com"})
handler(event=event)

>>> [... some logging ...]
{
    'status_code': '200',
    'body': '{"id": 123, "content-type": "application/json", "message": "hello, world"}'
}
```

### 2. Authorisation fails

```python
event = example_event(headers={"auth_level": 1, "x-request-url": "example.com"})
handler(event=event)

>>> [... some logging ...]
{
    'status_code': '400',
    'body': '{"message": "Minimum authorisation not satisfied"}'
}
```

### 3. Simulate a transient error

```python
import os
os.environ["FLAKE_OUT"] = "True"
event = example_event(headers={"auth_level": 10, "x-request-url": "example.com"})
handler(event=event)

>>> [... some logging ...]
{
    'status_code': '500',
    'body': '{"message": "Internal Server Error"}'
}
```

# For Developers

## Setup

Install dependencies with `poetry`:

```
poetry config virtualenvs.in-project true
poetry install
source .venv/bin/activate
```

Hook-up pre-commit hooks:

```
pre-commit install
```

## Tests

### Unit

```
python -m pytest -m 'not integration'
```

### Integration

This will run tests against the lambda(s) in `example` by deploying to localstack. There is an assumed dependency on docker client, which you should
install against the instructions for your operating system. [Docker Desktop](https://www.docker.com/products/docker-desktop/)
is a good place to start if you don't have opinions on the matter.

```
python -m pytest -m 'integration'
```

### Build

Create a build of this package

```
poetry build
```

## TODO

- Migrate to GitHb
- Update URLs in this README and pyproject.toml
- Update author / maintainer info in pyproject.toml
- Decide on publish via github or pypi
- Add `scripts` for CI (lint / version increment check / test:unit (python 3.9 - 3.10) / test:integration (python 3.9 - 3.10) / build / publish)
- Add GitHub Actions
