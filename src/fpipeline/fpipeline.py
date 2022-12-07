"""Functional Pipeline. A simple pipeline facility built on function composition.

Our composition operator is `pipeline`.
"""

from __future__ import annotations
from typing import Callable, Union, TypeVar, Generic, ParamSpec, Concatenate, Optional, ClassVar
from contextlib import contextmanager
from dataclasses import dataclass, field
from abc import ABCMeta
from collections import namedtuple

D = TypeVar('D')  # Data
T = TypeVar('T')  # "Target"
V = TypeVar('V')  # "Value"
A = TypeVar('A')  # Arglist
P = ParamSpec('P')

class Step(Callable[[D], any], metaclass=ABCMeta):
    """An operation callable on the data context"""

class Condition(Callable[[D], bool], metaclass=ABCMeta):
    """A condition on the data context"""

### Annotations

def stepfn(fnx: Callable[Concatenate[D, P], any]) -> Callable[P, Step[D]]:
    """An annotation for defining step functions. All but the first argument are curried. """
    def step_fn(*args: P.args, **kwargs: P.kwargs) -> Step[D]:
        return curry(fnx, *args, **kwargs)
    return step_fn

def conditionfn(fnx: Callable[Concatenate[D, P], bool]) -> Callable[P, Condition[D]]:
    """An annotation for defining step functions. All but the first argument are curried. """
    def condition_fn(*args: P.args, **kwargs: P.kwargs) -> Condition[D]:
        return curry(fnx, *args, **kwargs)
    return condition_fn

### Pipeline Variables

class AbstractVariable(Generic[T, V]):
    """Abstract base for pipeline"""
    __name__ = property(repr)
    value: V
    def __call__(self, data: T) -> V:
        return self.value

@dataclass
class Variable(AbstractVariable[T, V]):
    """Pipeline variable"""
    name: str
    def __init__(self, name: str):
        self.name = name
    def __repr__(self):
        if hasattr(self, 'value'):
            return f"<{self.name}={repr(self.value)}>"
        else:
            return f"<{self.name}=???>"
    # Pipeline variables are identity-hashed.
    def __hash__(self):
        return id(self)
    def __eq__(self, other):
        return self is other

@dataclass
class Attribute(AbstractVariable[T, V]):
    """Pipeline variable backed by an attribute on the data context"""
    target: T = field(repr=False)
    name: str

    def __get(self):
        if isinstance(self.target, dict):
            return self.target[self.name]
        return getattr(self.target, self.name)

    def __set(self, value: V):
        value = eval_vars(self.target, value)
        if isinstance(self.target, dict):
            self.target[self.name] = value
        else:
            setattr(self.target, self.name, value)
        return value

    def __del(self):
        # We leave attribute values behind after we exit scope
        # But we drop the ability to acccess them
        delattr(self, 'target')

    value: ClassVar[V] = property(__get, __set, __del)

    def __repr__(self):
        if hasattr(self, 'target'):
            if hasattr(self.target, 'name'):
                return f'@<{self.target.name}.{self.name}>'
            else:
                return f'@<???.{self.name}>'
        else:
            return f'@<####.{self.name}>'

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

@dataclass
class VariableContext(Generic[D]):
    """Context for pipeline variables"""
    target: D
    _variables: dict[str, AbstractVariable[D]] = field(default_factory=dict)
    closed: bool = False

    def variable(self, *names: list[str]) -> Variable[D]:
        """Obtain one or more variables"""
        def find(name):
            if not name in self._variables:
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return find(names[0])
        return [*(find(name) for name in names)]

    def attribute(self, *names: list[str]) -> Attribute[D]:
        """Obtain one or more attribute references"""
        def find(name):
            if not name in self._variables:
                var = Attribute(self.target, name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return find(names[0])
        return [*(find(name) for name in names)]

    def pipeline(self, *steps: list[Step[T]]) -> Step[T]:
        """Create and run a pipeline in this variable context"""
        return pipeline(*steps)(self.target)

    def close(self):
        """On closing the context, make using the variables an error."""
        for (_, var) in self._variables.items():
            if hasattr(var, 'value'):
                delattr(var, 'value')  # future references to .value will error.
        self._variables.clear()
        self.closed = True     # Future uses of this context will error.

# Would be a @stepfn, but we have to be able to receive the Variable unchanged.
# A @stepfn receives pipeline variable values, never variables
def store(var: AbstractVariable[D, V], step:Step[any, V]) -> V:
    """Store the result of the step in the supplied variable"""
    def store_(data: D):
        var.value = eval_vars(data, step(data))
        return var.value
    return store_

@contextmanager
def variables(target: D):
    """Returns a `VariableContext`, for use in a `with` statement."""
    vctx = VariableContext(target)
    try:
        yield vctx
    finally:
        vctx.close()

def eval_vars(ctx: D, val: Union[AbstractVariable, any], /, depth=10):
    """Evaluate a pipeline variable, or any list, tuple, or dict that may contain them,
    up to _depth_ (default 10) depth"""
    if isinstance(val, AbstractVariable):
        return eval_vars(ctx, val.value, depth=depth-1)
    if depth == 0:
        return val
    if isinstance(val, list):
        return [eval_vars(ctx, v, depth=depth-1) for v in val]
    t = type(val)
    if hasattr(t, '_make'):
        return t._make((eval_vars(ctx, v, depth=depth-1) for v in val))
    if isinstance(val, tuple):
        return tuple((eval_vars(ctx, v, depth=depth-1) for v in val))
    if isinstance(val, dict):
        return {k:eval_vars(ctx, v, depth=depth-1) for (k, v) in val.items()}
    if isinstance(val, frozenset):
        return frozenset((eval_vars(ctx, v, depth=depth-1) for v in val))
    if isinstance(val, set):
        return {eval_vars(ctx, v, depth=depth-1) for v in val}
    if callable(val):
        return val(ctx)
    return val

### Currying support

def curry(step_fn: Callable[Concatenate[D, P], any],
          *args,
          name: Optional[str] = None,
          **kwargs
         ) -> Step[D]:
    """Configure a Step, currying all but the first argument."""
    if name is None:
        name = step_fn.__name__
    def step(data: D):
        nonlocal args, kwargs
        args = [eval_vars(data, a) for a in args]
        value = step_fn(data, *args, **kwargs)
        if isinstance(value, AbstractVariable):
            raise TypeError(f"Pipeline variable {value.name} being returned.")
        return value
    step.__name__ = name
    return step

### Collect steps into a pipeline (itself a step)

def pipeline(*steps: list[Step[D]], name: Optional[str] = None) -> Step[D]:
    """Return a new function that calls each function on the same arguments,
    returning the last return value"""
    if name is None:
        name = ','.join((s.__name__ for s in steps))

    def run_pipeline(data:D):
        result = None
        for fun in steps:
            result = fun(data)
        return eval_vars(data, result)
    run_pipeline.__name__ = name
    return run_pipeline

### Condition Modifiers

def not_(cond_: Condition[D], name: Optional[str] = None) -> Condition[D]:
    """Negate a Condition"""
    if name is None:
        name = cond_.__name__

    def negator(data: D) -> Condition[D]:
        return not cond_(data)
    negator.__name__ = name
    return negator

def or_(*conditions: list[Condition[D]], name: Optional[str] = None) -> Condition[D]:
    """Combine conditions with OR"""
    if name is None:
        name = '|'.join((c.__name__ for c in conditions))

    def cond(data: D) -> bool:
        for lcond in conditions:
            if lcond(data):
                return True
        return False
    cond.__name__ = name
    return cond

def and_(*conditions: list[Condition[D]], name: Optional[str] = None) -> Condition[D]:
    """Combine conditions with AND"""
    if name is None:
        name = '&'.join((c.__name__ for c in conditions))

    def cond(data: D) -> bool:
        for lcond in conditions:
            if not lcond(data):
                return False
        return True
    cond.__name__ = name
    return cond

### Step wrappers


def if_(
    cond_: Condition[D],
    then_: Optional[Union[Step[D],list[Step[D]]]],
    else_: Optional[Union[Step[D], list[Step[D]]]] = None,
    /,
    name: Optional[str] = None
) -> Step[D]:
    "Evaluate cond_. If true, call then_, otherwise else_. If no else_, return None"
    if name is None:
        if else_ is None:
            name = f"{cond_.__name__}?{then_.__name__}"
        else:
            name = f"{cond_.__name__}?{then_.__name__}:{else_.__name__}"

    if isinstance(then_, list):
        then_ = pipeline(*then_)
    if isinstance(else_, list):
        else_ = pipeline(*else_)
    def step(data: D):
        if cond_(data):
            if then_ is None:
                return None
            return then_(data)
        elif else_ is not None:
            return else_(data)
        else:
            return None
    step.__name__ = name
    return step

### Utility Steps

@stepfn
def apply(ctx: D, expr: Callable[P, V], *args: P.args, **kwargs: P.kwargs) -> V:
    """A step that applies a function to the supplied arguments and returns the values.
    This is a stepfn, so pipeline variables can be supplied as arguments and be
    evaluated before calling the function.

    It's a StepFn, so it returns a Step that can be used anywhere steps (or conditions)
    are allowed.
    """
    return expr(ctx, *args, **kwargs)

@stepfn
def list_(data: D, *args):
    return list(map(eval_vars, args))

@stepfn
def dict_(data: D, **kwargs):
    return {k:eval_vars(v) for (k, v) in kwargs}

@stepfn
def tuple_(data: D, *args):
    return tuple(map(eval_vars, args))

@stepfn
def set_(data: D, *args):
    return set(map(eval_vars, args))
