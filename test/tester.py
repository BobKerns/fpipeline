""" Simple Test Framework for notebook-based tests."""

from dataclasses import dataclass
from typing import Callable, cast, TypeVar, ParamSpec
from abc import ABC, abstractmethod

P = ParamSpec('P')
V = TypeVar('V')

class TestReporter(ABC):
    """Abstract base class for reporting test results"""
    @abstractmethod
    def success(self, name: str, result: any):
        """Handle test success"""
    @abstractmethod
    def failure(self, name: str, result: any):
        """Handle test failure"""
    @abstractmethod
    def error(self, name:str, result: any):
        """Handle errors while testing"""

class DefaultTestReporter(TestReporter):
    """The default test reporter"""
    def success(self, name: str, result: any):
        """Handle test success"""
        print(f"✅: {name}")

    def failure(self, name: str, result: any):
        """Handle test failure"""
        print(f"❌: {name}")

    def error(self, name: str, result: any):
        """Handle errors while testing"""
        print(f"❌❌❌; {name} {result}")

TEST_REPORTER = DefaultTestReporter()

def set_test_reporter(reporter: TestReporter):
    """Set what TestReporter to use"""
    global TEST_REPORTER # pylint: disable=global-statement
    TEST_REPORTER = reporter

@dataclass
class Test:
    """One test case"""
    name: str
    result: any
    negated: bool = False
    def _check(self, pred: Callable[[any, any], bool], value: any):
        success: bool = False
        try:
            success = bool(pred(self.result, value)) ^ self.negated
        except Exception as ex: # pylint: disable=broad-except
            TEST_REPORTER.error(self.name, ex)
            return
        if success:
            TEST_REPORTER.success(self.name, self.result)
        else:
            TEST_REPORTER.failure(self.name, self.result)
    def equals(self, value: any):
        """Test if the result is equal to the supplied value"""
        self._check(lambda a, b: a == b, value)
    def is_same(self, value: any):
        """Test if the result is the exact same object as the supplied value"""
        self._check(lambda a, b: a is b, value)
    def is_true(self):
        """Test if the result is true"""
        self._check(lambda a, b: not not a, True) # pylint: disable=unneeded-not
    def is_false(self):
        """test if the result is false"""
        self._check(lambda a, b: not a, False)
    @property
    def negate(self):
        """Negate the test"""
        return Test(self.name, self.result, negated=not self.negated)
    @property
    def exec(self):
        """Execute the result value as a function"""
        try:
            return Test(self.name, cast(Callable, self.result)())
        except Exception as ex: # pylint: disable=broad-except
            return Test(self.name, ex)
    def apply(self, *args: P.args, **kwargs: P.kwargs) -> V:
        """Apply the fresult to the supplied arguments and return the result"""
        try:
            return Test(self.name, cast(Callable[P, V], self.result)(*args, **kwargs))
        except Exception as ex: # pylint: disable=broad-except
            return Test(self.name, ex)
    def is_exception(self):
        """Test if the result is an exception"""
        self._check(isinstance, Exception)
    def isinstance(self, cls):
        """Test if the result is an instance of the specified class"""
        self._check(isinstance, cls)
