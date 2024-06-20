"""Functional Pipeline. A simple pipeline facility built on function composition.

Our composition operator is `pipeline`.
"""

from typing import (
    Any, Callable, Generator, Sequence, Union,
    Concatenate, Optional, ClassVar, cast, overload,
    NamedTuple)
from contextlib import contextmanager
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from functools import wraps

class Step[D,V](ABC):
    """An operation callable on the data context"""
    @abstractmethod
    def __call__(self, data: D) -> V:
        ...

class Condition[D](Step[D, bool]):
    """A condition on the data context"""

### Annotations

def stepfn[D,V, **P](fnx: Callable[Concatenate[D, P], V]) -> Callable[P, Step[D, V]]:
    """An annotation for defining step functions. All but the first argument are curried. """
    @wraps(fnx)
    def step_fn(*args: P.args, **kwargs: P.kwargs) -> Step[D,V]:
        return curry(fnx, *args, **kwargs) # type: ignore
    return step_fn

def conditionfn[D,V,**P](fnx: Callable[Concatenate[D, P], bool]) -> Callable[P, Condition[D]]:
    """An annotation for defining step functions. All but the first argument are curried. """
    @wraps(fnx)
    def condition_fn(*args: P.args, **kwargs: P.kwargs) -> Condition[D]:
        return curry(fnx, *args, **kwargs) # type: ignore
    return condition_fn

### Pipeline Variables

class AbstractVariable[T,V]:
    """Abstract base for pipeline"""
    __name__ = property(repr)
    value: V
    def __call__(self, data: T) -> V:
        return self.value

@dataclass
class Variable[T,V](AbstractVariable[T, V]):
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
class Attribute[T,V](AbstractVariable[T, V]):
    """
    Pipeline variable backed by an attribute on the data context
    """
    target: T = field(repr=False)
    name: str

    def __get(self):
        if isinstance(self.target, dict):
            return self.target[self.name]
        return getattr(self.target, self.name)

    def __set(self, value: V):
        value = cast(V, eval_vars(self.target, value))
        if isinstance(self.target, dict):
            self.target[self.name] = value
        else:
            setattr(self.target, self.name, value)
        return value

    def __del(self):
        # We leave attribute values behind after we exit scope
        # But we drop the ability to access them
        delattr(self, 'target')

    value = cast(V,property(__get, cast(Callable[[Any, V], None],__set), __del))

    def __repr__(self):
        if hasattr(self, 'target'):
            if hasattr(self.target, 'name'):
                return f'@<{getattr(self.target, 'name')}.{self.name}>'
            else:
                return f'@<???.{self.name}>'
        else:
            return f'@<####.{self.name}>'

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

@dataclass
class VariableContext[D]:
    """Context for pipeline variables"""
    target: D
    _variables: dict[str, AbstractVariable[D, Any]] = field(default_factory=dict)
    closed: bool = False

    @overload
    def variable[V](self, name1: str, *, cls: type[V]=type[object]) -> Variable[D,V]:
        ...
    @overload
    def variable[V](self, name1: str, *names: str,
                      cls: type[V]=type[object]
                      ) -> tuple[Variable[D,V]]:
        ...
    def variable[V](self, name1: str,
                    *names: str,
                    cls: type[V]=type[object]) -> Variable[D,V]|tuple[Variable[D,V],...]:
        """Obtain one or more variables"""
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Variable[D,V], find(names[0]))
        return tuple((cast(Variable[D,V], find(name)) for name in names))

    @overload
    def attribute[V](self, name1: str, *, cls: type[V]=type[object]) -> Attribute[D,V]:
        ...
    @overload
    def attribute[V](self, name1: str, *names: str,
                     cls: type[V]=type[object]) -> tuple[Attribute[D,V], ...]:
        ...
    def attribute[V](self, name1: str, *names: str,
                     cls: type[V]=type[object]
                  ) -> Attribute[D,V]|tuple[Attribute[D,V], ...]:
        """Obtain one or more attribute references"""
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Attribute(self.target, name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Attribute[D,V], find(names[0]))
        return tuple(cast(Attribute[D,V],find(name)) for name in names)

    def pipeline[V](self, *steps: Step[D,V]) -> Step[D,V]:
        """
        create and run a pipeline in this variable context
        """
        return cast(Step[D,V], pipeline(*steps)(self.target))

    def close(self):
        """On closing the context, make using the variables an error."""
        for (_, var) in self._variables.items():
            if hasattr(var, 'value'):
                delattr(var, 'value')  # future references to .value will error.
        self._variables.clear()
        self.closed = True     # Future uses of this context will error.

# Would be a @stepfn, but we have to be able to receive the Variable unchanged.
# A @stepfn receives pipeline variable values, never variables
def store[D,V](var: AbstractVariable[D, V], step:Step[D, V]) -> Step[D,V]:
    """
    Store the result of the step in the supplied variable
    """
    @wraps(store)
    def store_(data: D):
        var.value = cast(V, eval_vars(data, step(data)))
        return var.value
    return cast(Step[D,V], store_)

@contextmanager
def variables[D](target: D) -> Generator[VariableContext[D], None, None]:
    """Returns a `VariableContext`, for use in a `with` statement."""
    vctx = VariableContext(target)
    try:
        yield vctx
    finally:
        vctx.close()

type Arg[V] = V \
    |list[Arg[V]] \
    |tuple[Arg[V],...] \
    |dict[str,Arg[V]] \
    |set[Arg[V]] \
    |frozenset[Arg[V]]

type Value[V] = V \
    |Sequence[Arg[V]] \
    |dict[str,Arg[V]] \
    |set[Arg[V]] \
    |frozenset[Arg[V]]

def eval_vars[T,V](ctx: T, val: Arg[V|AbstractVariable[T,V]], /,
                          depth: int=10
    ) -> Value[V]|Value[tuple[V,...]]|Value[list[V]]|Value[dict[str,V]]|Value[set[V]]|Value[frozenset[V]]:
    """Evaluate a pipeline variable, or any list, tuple, or dict that may contain them,
    up to _depth_ (default 10) depth
    """
    match val:
        case AbstractVariable():
            return eval_vars(ctx, val.value, depth=depth-1)
        case _ if depth == 0:
            return cast(V,val)
        case list():
            vx = [eval_vars(ctx, v, depth=depth-1) for v in val]
            return cast(Value[V],vx)
        case _ if hasattr(type(val), '_make'):
            # NamedTuple, etc.
            mk: Callable[[Arg[V]],Value[V]] = getattr(type(val), '_make')
            typ = type(val)
            nval = (eval_vars(ctx, v, depth=depth-1) for v in val)
            return typ(*nval)
        case tuple():
            vtuple: tuple[V,...] = cast(tuple[V], val)
            typ = type(val)
            nval = typ((eval_vars(ctx, v, depth=depth-1) for v in vtuple))
            return cast(Value[V], nval)
        case dict():
            vdict: dict[str,V] = cast(dict[str,V],val)
            ndict = {k:eval_vars(ctx, v, depth=depth-1) for (k, v) in vdict.items()}
            return cast(dict[str,V], ndict)
        case frozenset():
            vfset = (eval_vars(ctx, v, depth=depth-1) for v in val)
            return cast(frozenset[V], frozenset(vfset))
        case set():
            vfset = {cast(V, eval_vars(ctx, v, depth=depth-1)) for v in val}
            return cast(set[V], vfset)
        case _ if callable(val):
            return val(ctx)
        case _:
            return val

### Currying support

def curry[D,V,**P](step_fn: Callable[Concatenate[D, ...], V],
          *args: P.args,
          **kwargs: P.kwargs,
         ) -> Step[D,V]:
    """Configure a Step, currying all but the first argument."""
    @wraps(step_fn)
    def step(data: D) -> V:
        nonlocal args, kwargs
        nargs = cast(list[V], args)
        xargs= [eval_vars(cast(D,data), cast(V,a)) for a in nargs]
        value = step_fn(data, *xargs, **kwargs)
        if isinstance(value, AbstractVariable):
            raise TypeError(f"Pipeline variable {value.__name__} being returned.")
        return value
    return cast(Step[D,V], step)

### Collect steps into a pipeline (itself a step)

def pipeline[D,V](*steps: Step[D,V], name: Optional[str] = None) -> Step[D,V]:
    """Return a new function that calls each function on the same arguments,
    returning the last return value"""
    @wraps(steps[0] if steps else None)
    def run_pipeline(data:D) -> V:
        result = None
        for fun in steps:
            result = fun(data)
        return cast(V,eval_vars(data, result))
    return cast(Step[D,V], run_pipeline)

### Condition Modifiers

def not_[D](cond_: Condition[D], name: Optional[str] = None) -> Condition[D]:
    """Negate a Condition"""
    @wraps(cond_)
    def negator(data: D) -> bool:
        return not cond_(data)
    return cast(Condition[D], negator)

def or_[D](*conditions: Condition[D], name: Optional[str] = None) -> Condition[D]:
    """Combine conditions with OR"""
    if name is None:
        name = '|'.join((getattr(c, '__name__') for c in conditions))
    fn = conditions[0] if conditions else None
    @wraps(fn)
    def cond(data: D) -> bool:
        for lcond in conditions:
            if lcond(data):
                return True
        return False
    return cast(Condition[D], cond)

def and_[D](*conditions: Condition[D], name: Optional[str] = None) -> Condition[D]:
    """
    Combine conditions with AND
    """
    @wraps(conditions[0] if conditions else None)
    def cond(data: D) -> bool:
        return all((lcond(data) for lcond in conditions))
    return cast(Condition[D], cond)

### Step wrappers


def if_[D,V](
    cond_: Condition[D],
    then_: Optional[Union[Step[D,V],list[Step[D,V]]]],
    else_: Optional[Union[Step[D,V], list[Step[D,V]]]] = None,
    /,
) -> Step[D,V]:
    "Evaluate cond_. If true, call then_, otherwise else_. If no else_, return None"
    if isinstance(then_, list):
        then_ = pipeline(*then_)
    if isinstance(else_, list):
        else_ = pipeline(*else_)
    @wraps(if_)
    def step(data: D):
        if cond_(data):
            if then_ is None:
                return None
            return then_(data)
        elif else_ is not None:
            return else_(data)
        else:
            return None
    return cast(Step[D, V], step)

### Utility Steps

@stepfn
def apply[D,V,**P](ctx: D, expr: Callable[Concatenate[D,P], V],
                   *args: P.args,
                   **kwargs: P.kwargs) -> V:
    """A step that applies a function to the supplied arguments and returns the values.
    This is a stepfn, so pipeline variables can be supplied as arguments and be
    evaluated before calling the function.

    It's a StepFn, so it returns a Step that can be used anywhere steps (or conditions)
    are allowed.
    """
    return expr(ctx, *args, **kwargs)

@stepfn
def list_[V](ctx: object, *args: V) -> list[V]:
    val = [eval_vars(ctx, v) for v in args]
    return cast(list[V], val)

@stepfn
def dict_[V](ctx: object, **kwargs:V) -> dict[str,V]:
    val = {k:eval_vars(ctx, v) for k,v in kwargs.items()}
    return cast(dict[str, V], val)

@stepfn
def tuple_[V](ctx: object, *args:V) -> tuple[V, ...]:
    val = tuple((eval_vars(ctx, v) for v in args))
    return cast(tuple[V,...], val)

@stepfn
def set_[V](ctx: object, *args: V) -> set[V]:
    val = set((eval_vars(ctx, v) for v in args))
    return cast(set[V], val)
