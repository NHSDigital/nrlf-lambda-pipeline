import collections.abc
from importlib import import_module
from typing import Dict, Generic, TypeVar

try:
    lambda_context = import_module("awslambdaric.lambda_context")
    LambdaContext = lambda_context.LambdaContext
except ModuleNotFoundError:
    pass

try:
    lambda_executors = import_module("localstack.services.awslambda.lambda_executors")
    LambdaContext = lambda_executors.LambdaContext
except ModuleNotFoundError:
    pass

if "LambdaContext" not in locals():
    from aws_lambda_powertools.utilities.typing import LambdaContext


FDKey = TypeVar("FDKey", bound=str)
FDValue = TypeVar("FDValue")


class FrozenDict(collections.abc.Mapping, Generic[FDKey, FDValue]):
    """An implementation of a frozen dict, lifted from https://stackoverflow.com/a/2704866/1571593"""

    def __init__(self, *args: Dict[FDKey, FDValue], **kwargs: FDValue):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self) -> int:
        return len(self._d)

    def __getitem__(self, key: FDKey) -> FDValue:
        return self._d[key]

    def __str__(self) -> str:
        return str(self._d)

    def __repr__(self) -> str:
        return repr(self._d)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenDict):
            return other._d == self._d
        return False

    def __hash__(self):
        # It would have been simpler and maybe more obvious to
        # use hash(tuple(sorted(self._d.iteritems()))) from this discussion
        # so far, but this solution is O(n). I don't know what kind of
        # n we are going to run into, but sometimes it's hard to resist the
        # urge to optimize when it will gain improved algorithmic performance.
        if self._hash is None:
            hash_ = 0
            for pair in self.items():
                hash_ ^= hash(pair)
            self._hash = hash_
        return self._hash

    def to_dict(self):
        return dict(self._d)


class PipelineData(FrozenDict[FDKey, FDValue]):
    """
    A dict-object for passing data between pipeline steps.
    Pipeline will force this to be immutable on ingestion to a step.
    """

    pass
