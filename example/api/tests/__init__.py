import json
from functools import cache

import requests

TEST_EVENT_URL = (
    "https://raw.githubusercontent.com/awsdocs/"
    "aws-lambda-developer-guide/main/sample-apps"
    "/nodejs-apig/event.json"
)


@cache
def _example_event():
    response = requests.get(TEST_EVENT_URL)
    return response.text


def example_event(**overrides):
    response_text = _example_event()
    event = json.loads(response_text)
    event.update(**overrides)
    return event
