"""Functional Pipeline. A simple pipeline facility built on function composition.

Our composition operator is `pipeline`.
"""

from __future__ import annotations
from typing import Callable, Union, TypeVar, Generic, ParamSpec, Concatenate, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field
from abc import ABCMeta

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
    """Abstract base for pipeline variables"""
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
        return f"<{self.name}={repr(self.value)}>"

@dataclass
class Attribute(AbstractVariable[T, V]):
    """Pipeline variable backed by an attribute on the data context"""
    target: T
    name: str

    def __get(self):
        return getattr(self.target, self.name)

    def __set(self, value: V):
        setattr(self.target, self.name, value)

    def __del(self):
        # We leave attribute values behind after we exit scope
        # But we drop the ability to acccess them
        delattr(self, 'target')
    value: V = property(__get, __set, __del)

    def __repr__(self):
        if hasattr(self, 'target'):
            if hasattr(self.target, 'name'):
                return f'@<{self.target.name}.{self.name}>'
            else:
                return f'@<???.{self.name}>'
        else:
            return f'@<####.{self.name}>'

@dataclass
class VariableContext(Generic[D]):
    """Context for pipeline variables"""
    target: D
    variables: dict[str, AbstractVariable[D]] = field(default_factory=dict)

    def variable(self, *names: list[str]) -> Variable[D]:
        """Obtain one or more variables"""
        def find(name):
            var = self.variables.get(name)
            if var is None:
                var = Variable(name)
                self.variables[name] = var
            return var
        return tuple(*(find(name) for name in names))

    def attribute(self, *names: list[str]) -> Attribute[D]:
        """Obtain one or more attribute references"""
        return tuple(*(Attribute(self.target, name) for name in names))

    def pipeline(self, *steps: list[Step[T]]) -> Step[T]:
        """Create a pipeline in this variable context"""
        inner = pipeline(*steps)
        def outer(data: D) -> any:
            try:
                return inner(data)
            finally:
                self.close()
        return outer

    def close(self):
        """On closing the context, make using the variables an error."""
        for (_, var) in self.variables.items():
            delattr(var, 'value')  # future references to .value will error.
        self.variables.clear()
        del self.variables     # Future uses of this context will error.

@contextmanager
def variables(target: D):
    """Returns a `VariableContext`, for use in a `with` statement."""
    vctx = VariableContext(target)
    try:
        yield vctx
    finally:
        vctx.close()

### Currying support

def curry(step_fn: Callable[Concatenate[D, P], any],
          *args,
          name: Optional[str] = None,
          store: Optional[AbstractVariable[D]] = None,
          **kwargs
         ) -> Step[D]:
    """Configure a Step, currying all but the first argument."""
    if name is None:
        name = step_fn.__name__
    def val(var: Union[Variable, any]):
        return var.value if isinstance(var, Variable) else var
    def step(data: D):
        nonlocal val, args, kwargs, store
        args = [val(a) for a in args]
        value = step_fn(data, *args, **kwargs)
        if store:
            store.value = value
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
        return result
    run_pipeline.__name__ = name
    return run_pipeline

### Condition Modifiers

def not_(cond_: Condition[D], name: Optional[str]) -> Condition[D]:
    """Negate a Condition"""
    if name is None:
        name = cond_.__name__

    def negator(data: D) -> Condition[D]:
        return not cond_(data)
    negator.__name__ = name
    return negator

def or_(conditions: list[Condition[D]], name: Optional[str] = None) -> Condition[D]:
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

def and_(conditions: list[Condition[D]], name: Optional[str] = None) -> Condition[D]:
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
    then_: Step[D],
    else_: Optional[Step[D]] = None,
    name: Optional[str] = None
) -> Step[D]:
    "Evaluate cond_. If true, call then_, otherwise else_. If no else_, return None"
    if name is None:
        if else_ is None:
            name = f"{cond_.__name__}?{then_.__name__}"
        else:
            name = f"{cond_.__name__}?{then_.__name__}:{else_.__name__}"

    def step(data: D):
        if cond_(data):
            return then_(data)
        elif else_ is not None:
            return else_(data)
        else:
            return None
    step.__name__ = name
    return step
