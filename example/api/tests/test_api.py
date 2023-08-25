import json
from copy import deepcopy
import pytest
from example.api.tests import example_event
from example.conftest import create_lambda_zip

LAMBDA_NAME = "api"
RUNTIME = "python3.9"
HEADERS_HAPPY = {"headers": {"auth_level": 10, "x-request-url": "example.com"}}
HEADERS_BAD_AUTH_LEVEL = {"headers": {"auth_level": 1, "x-request-url": "example.com"}}
HEADERS_ILLEGAL_AUTH_LEVEL = {
    "headers": {"auth_level": "foo", "x-request-url": "example.com"}
}
STATUS_OK = "200"
STATUS_BAD_REQUEST = "400"
STATUS_INTERNAL_ERROR = "500"


@pytest.fixture()
def event():
    return deepcopy(example_event())


@pytest.fixture(scope="session")
def lambda_function(lambda_client, lambda_role):
    lambda_zip_data = create_lambda_zip(lambda_name=LAMBDA_NAME)

    lambda_client.create_function(
        FunctionName=LAMBDA_NAME,
        Runtime=RUNTIME,
        Role=lambda_role,
        Handler="index.handler",
        Code={
            "ZipFile": lambda_zip_data,
        },
        Publish=True,
        Timeout=30,
        MemorySize=128,
    )

    waiter = lambda_client.get_waiter("function_active_v2")
    waiter.wait(FunctionName=LAMBDA_NAME)

    yield lambda **kwargs: lambda_client.invoke(FunctionName=LAMBDA_NAME, **kwargs)

    lambda_client.delete_function(FunctionName=LAMBDA_NAME)


@pytest.mark.integration
@pytest.mark.parametrize(
    ["event_overrides", "expected_status", "expected_body"],
    [
        (
            HEADERS_HAPPY,
            STATUS_OK,
            {
                "id": 123,
                "content-type": "application/json",
                "message": "hello, world",
            },
        ),
        (
            HEADERS_BAD_AUTH_LEVEL,
            STATUS_BAD_REQUEST,
            {"message": "Minimum authorisation not satisfied"},
        ),
        (
            HEADERS_ILLEGAL_AUTH_LEVEL,
            STATUS_INTERNAL_ERROR,
            {"message": "Internal Server Error"},
        ),
    ],
)
def test_api_lambda(
    lambda_function,
    event,
    event_overrides,
    expected_status,
    expected_body,
):
    event.update(event_overrides)

    aws_response = lambda_function(Payload=json.dumps(event).encode())
    lambda_response = json.loads(aws_response["Payload"].read())
    assert "status_code" in lambda_response, lambda_response

    assert lambda_response["status_code"] == expected_status, lambda_response

    assert "body" in lambda_response, lambda_response
    body = json.loads(lambda_response["body"])
    assert body == expected_body
