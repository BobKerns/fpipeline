""" Simple Test Framework for notebook-based tests."""

from dataclasses import dataclass
from typing import Callable, cast
from IPython.display import display

@dataclass
class Test:
    """One test case"""
    name: str
    result: any
    negated: bool = False
    def _success(self):
        display({"text/html": f"✅: {self.name}"}, raw=True)
    def _failure(self):
        display(
            {"text/html": f"<span style='color:red'>❌: {self.name}</span>"}, raw=True)
    def _check(self, pred: Callable[[any, any], bool], value: any):
        if bool(pred(self.result, value)) ^ self.negated:
            self._success()
        else:
            self._failure()
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
    def is_exception(self):
        """Test if the result is an exception"""
        self._check(isinstance, Exception)
    def isinstance(self, cls):
        """Test if the result is an instance of the specified class"""
        self._check(isinstance, cls)
