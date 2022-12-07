""" Simple Test Framework for notebook-based tests."""

from dataclasses import dataclass
from typing import Callable, cast, TypeVar, ParamSpec, Concatenate
from abc import ABC, abstractmethod

P = ParamSpec('P')
T = ParamSpec('T')
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
    handle_exceptions: bool = True
    negated: bool = False
    # Errors propagate
    error: bool = False
    reported: bool = False
    def _check(self, pred: Callable[[any, any], bool], value: any, /, allow_error=False):
        if self.reported:
            return # We've already reported the error.
        if self.error and not allow_error:
            self.reported = True
            TEST_REPORTER.error(self.name, self.result)
            return
        success: bool = False
        if self.handle_exceptions:
            try:
                success = bool(pred(self.result, value)) ^ self.negated
            except Exception as ex: # pylint: disable=broad-except
                self.reported = True
                TEST_REPORTER.error(self.name, ex)
                return
        else:
            success = bool(pred(self.result, value)) ^ self.negated
        if success:
            TEST_REPORTER.success(self.name, self.result)
        else:
            TEST_REPORTER.failure(self.name, self.result)
        self.reported = True
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
        return Test(self.name, self.result,
                    negated=not self.negated,
                    error=self.error,
                    reported=self.reported,
                    handle_exceptions = self.handle_exceptions)
    @property
    def exec(self):
        """Execute the result value as a function of no arguments"""
        if self.error:
            return self
        if not self.handle_exceptions:
            return Test(self.name, cast(Callable, self.result)(),
                        handle_exceptions=False)
        try:
            return Test(self.name, cast(Callable, self.result)())
        except Exception as ex: # pylint: disable=broad-except
            return Test(self.name, ex, error=True)
    def apply(self, *args: P.args, **kwargs: P.kwargs) -> V:
        """Apply the fresult to the supplied arguments and return the result"""
        if self.error:
            return self
        if not self.handle_exceptions:
            return Test(
                self.name,
                cast(Callable[P, V], self.result)(*args, **kwargs),
                handle_exceptions=False
            )
        try:
            return Test(
                self.name,
                cast(Callable[P, V], self.result)(*args, **kwargs)
            )
        except Exception as ex: # pylint: disable=broad-except
            return Test(self.name, ex, error=True, negated=self.negated)
    def call(self, fnctn: Callable[Concatenate[any, P], V], *args: P.args, **kwargs: P.kwargs):
        """Call the supplied function and substitute the result."""
        if self.error:
            return self
        handle = self.handle_exceptions
        if not self.handle_exceptions:
            return Test(self.name, fnctn(self.result, *args, **kwargs),
                        negated=self.negated,
                        handle_exceptions=handle)
        try:
            return Test(self.name, fnctn(self.result, *args, **kwargs),
                        negated=self.negated,
                        handle_exceptions=self.handle_exceptions)
        except Exception as ex: # pylint: disable=broad-except
            return Test(self.name, ex, error=True)
    def is_exception(self, ex=Exception):
        """Test if the result is an exception"""
        self._check(isinstance, ex, allow_error=True)
    def isinstance(self, cls):
        """Test if the result is an instance of the specified class"""
        self._check(isinstance, cls)
    def attribute(self, name: str):
        """Extract the attribute"""
        if self.error:
            return self
        def read_attr():
            handle = self.handle_exceptions
            if isinstance(self.result, dict):
                return Test(self.name, self.result[name], negated=self.negated, handle_exceptions=handle)
            return Test(self.name, getattr(self.result, name), negated=self.negated, handle_exceptions=handle)
        if not self.handle_exceptions:
            return read_attr()
        try:
            return read_attr()
        except Exception as ex:
            return Test(self.name, ex, error=True)
    @property
    def raise_exception(self):
        """For debugging, raise any exception"""
        if isinstance(self.result, Exception):
            raise self.result
        return self
