from contextlib import contextmanager
import json
import os
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

import boto3 as _boto3
import pytest
import sh

from example.api.tests import example_event

REGION_NAME = "us-east-1"
ENDPOINT_URL = "http://localhost:4566"
ROLE_NAME = "lambda-creator"
PKG_NAME = "lambda_pipeline"
EXAMPLES_NAME = "example"
BUILD_DIR = "build"
LAMBDA_ZIP = "lambda.zip"
INDEX_FILE = "index.py"
IGNORE_PATTERNS = [
    "tests",
    "__pycache__",
    ".dist-info",
    ".so",
    "boto3",
    "botocore",
]


def boto3_client(*args, **kwargs):
    return _boto3.client(
        endpoint_url=ENDPOINT_URL, region_name=REGION_NAME, *args, **kwargs
    )


@pytest.fixture()
def event():
    return deepcopy(example_event())


@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    os.environ["AWS_DEFAULT_REGION"] = REGION_NAME
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="session")
def lambda_client():
    yield boto3_client("lambda")


@pytest.fixture(scope="session")
def lambda_role():
    iam = boto3_client("iam")
    yield iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )["Role"]["Arn"]
    iam.delete_role(RoleName=ROLE_NAME)


def get_root_path():
    path = Path(__file__).parent
    assert path.name == EXAMPLES_NAME
    return path.parent


def filtered_glob(path: Path):
    for entry in path.rglob("*"):
        if any(pattern in str(entry) for pattern in IGNORE_PATTERNS):
            continue
        yield entry


def write_to_zip(zip_file: zipfile.ZipFile, path: Path, relative_to: Path):
    for entry in filtered_glob(path):
        zip_file.write(entry, entry.relative_to(relative_to))


def get_venv_path(build_path: Path) -> Path:
    venv_path = build_path / "_venv"
    reqs_path = build_path / "_requirements.txt"
    sh.poetry("export", "--output", reqs_path, "--without-hashes")
    sh.pip("install", "-r", reqs_path, "-t", venv_path)
    return venv_path


@contextmanager
def named_temp_dir(path: Path):
    path.mkdir()

    error = None
    try:
        yield
    except Exception as _error:
        error = _error

    shutil.rmtree(path)
    if error:
        raise error from None


def create_lambda_zip(lambda_name: str) -> bytes:
    root_path = get_root_path()
    package_path = root_path / PKG_NAME
    examples_path = root_path / EXAMPLES_NAME
    build_path = root_path / BUILD_DIR
    zipfile_path = build_path / LAMBDA_ZIP
    handler_path = examples_path / lambda_name / INDEX_FILE

    with named_temp_dir(path=build_path):
        venv_path = get_venv_path(build_path)

        with zipfile.ZipFile(zipfile_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            write_to_zip(zip_file=zip_file, path=package_path, relative_to=root_path)
            write_to_zip(zip_file=zip_file, path=examples_path, relative_to=root_path)
            write_to_zip(zip_file=zip_file, path=venv_path, relative_to=venv_path)
            zip_file.write(handler_path, INDEX_FILE)

        with open(zipfile_path, "rb") as file_data:
            bytes_content = file_data.read()

    return bytes_content
