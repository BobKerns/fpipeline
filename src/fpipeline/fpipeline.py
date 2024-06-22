"""Functional Pipeline. A simple pipeline facility built on function composition.

Our composition operator is `pipeline`.
"""

from typing import (
    Any, Callable, Generator, Sequence, Union,
    Concatenate, Optional, cast, overload,
    )
from contextlib import contextmanager
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from functools import wraps

# Core types

class Step[C,V](ABC):
    """
    An operation callable on the ctx context.

    Normally, a step will return the ctx argument, possibly modified.
    Thus, normally, the return type V is the same as the context type C.
    However, the last step in a pipeline may return a different type.
    
    Type Parameters
    ---------------
        `C`: The context type
        `V`: The return type
    """
    @abstractmethod
    def __call__(self, ctx: C) -> V:
        """
        Invoke the step on the context.

        Normally, the return value is the context, possibly modified.
        However, the last step in a pipeline may return a different type.

        Parameters
        ----------
            ctx : C
                The context

        Returns
        -------
            V: the result of the step.
        """
        ...

class Pipeline[C,V](Step[C, V]):
    """
    A series of steps to be executed in order.

    if the resulting Pipeline object is called without a context,
    it will create a new context initialized with the variables
    supplied as keyword arguments.
   
    Type Parameters
    ---------------
        C: The context type
        V: The return type
    """
    @abstractmethod
    def __call__(self, ctx: Optional[C]=None, /,
                **kwargs) -> V:
        """
        Invoke the pipeline on the context.

        Normally, the return value is the context, possibly modified.
        However, the last step in a pipeline may return a different type.

        Parameters
        ----------
            ctx : C
                The context

        Returns
        -------
            V: the result of the step.
        """
        ...

class Condition[C](Step[C, bool]):
    """
    A condition on the ctx context.
    
    Type Parameters
    ---------------
        C: The context type
    """
    ...

### Annotations

def stepfn[C,V, **P](fnx: Callable[Concatenate[C, P], V]) -> Callable[P, Step[C, V]]:
    """
    An annotation for defining step functions. All but the first argument are curried.
    
    Parameters
    ----------
        fnx : `Callable[Concatenate[C, P], V]`
            The function to be annotated

    Returns
    -------
        Callable[P, Step[C, V]] - a function that accepts the given arguments and returns a step function.

    Type Parameters
    ---------------
        C: The context type
        V: The return type
        P: The arguments type
    """
    @wraps(fnx)
    def step_fn(*args: P.args, **kwargs: P.kwargs) -> Step[C,V]:
        return curry(fnx, *args, **kwargs) # type: ignore
    return step_fn

def conditionfn[C,**P](fnx: Callable[Concatenate[C, P], bool]) -> Callable[P, Condition[C]]:
    """
    An annotation for defining step functions. All but the first argument are curried.
    
    Parameters
    ----------
        fnx : `Callable[Concatenate[C, P], bool]`
            The function to be annotated

    Returns
    -------
        `Callable[P, Condition[C]]` - a function that accepts the given arguments and returns a condition function.

    Type Parameters
    ---------------
        C: The context type
        P: The arguments type
    """
    @wraps(fnx)
    def condition_fn(*args: P.args, **kwargs: P.kwargs) -> Condition[C]:
        return curry(fnx, *args, **kwargs) # type: ignore
    return condition_fn

### Pipeline Variables

class AbstractVariable[C,V]:
    """
    Abstract base for pipeline.
    
    Type Parameters
    ---------------
        C: The context type
        V: The value type
    """
    __name__ = property(repr)
    value: V
    def __call__(self, ctx: C) -> V:
        return self.value

@dataclass
class Variable[C,V](AbstractVariable[C, V]):
    """
    Pipeline variable.
    
    Type Parameters
    ---------------
        C: The context type
    """
    name: str
    "The name of the variable"
    
    @overload
    def __init__(self, name: str):
        ...
    @overload
    def __init__(self, name: str, value: V):
        ...
    def __init__(self, name: str, *values):
        """
        Parameters
        ----------
        name : `str`
            The name of the variable
        value : `V`, optional
            The initial value of the variable
        """
        self.name = name
        if values:
            self.value = values[0]
    
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
class Attribute[C,V](AbstractVariable[C, V]):
    """
    Pipeline variable backed by an attribute on the ctx context.

    The value of an `Attribute` is the value of the attribute on the target object.
    Setting the value sets the attribute on the target object.

    The target object can be a dictionary or an object with attributes.
    If it is a dictionary, the attribute is the key in the dictionary.

    Type Parameters
    ---------------
        C: The context type
        V: The value type
    """
    target: C = field(repr=False)
    "The context target, which can be a dictionary or an object with attributes."
    name: str
    "The name of the attribute or key in the target object"


    @overload
    def __init__(self, ctx: C, name: str):
        ...
    @overload
    def __init__(self, ctx: C, name: str, value: V):
        ...
    def __init__(self, ctx: C, name: str, *values):
        """
        Parameters
        ----------
        name : `str`
            The name of the variable
        value : `V`, optional
            The initial value of the variable
        """
        self.target = ctx
        self.name = name
        if values:
            self.value = values[0]

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
    """
    The value of an `Attribute` is the value of the attribute on the target object.
    Setting the value sets the attribute on the target object.

    The target object can be a dictionary or an object with attributes.
    If it is a dictionary, the attribute is the key in the dictionary.
    """

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
class VariableContext[C]:
    """
    Context for pipeline variables. This provides a scope for variables, and acts as a context manager for
    their values.

    Type Parameters
    ---------------
        C: The context type
    """
    target: C
    _variables: dict[str, AbstractVariable[C, Any]] = field(default_factory=dict)
    closed: bool = False

    @overload
    def variable[V](self, name1: str, *, cls: type[V]=type[Any]) -> Variable[C,V]:
        ...
    @overload
    def variable[V](self, name1: str, *names: str,
                      cls: type[V]=type[object]
                      ) -> tuple[Variable[C,V],...]:
        ...
    def variable[V](self, name1: str,
                    *names: str,
                    _cls: type[V]=type[object]) -> Variable[C,V]|tuple[Variable[C,V],...]:
        """
        Obtain a single variable.

        Compatibility
        -------------       
        Since 1.4.0:
        For multiple variables, use the `variables` method.

        Parameters
        ----------
            name : str
                The name of a single variable
            _cls : type[V]
                The type of the variable, default=Any

        Returns
            `Variable[C,V]` The variable
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Variable[C,V], find(names[0]))
        return tuple((cast(Variable[C,V], find(name)) for name in names))
    
    def variables[V](self, name1: str,
                    *names: str,
                    _cls: type[V]=type[object],
                    **kwargs: V,
                    ) -> tuple[Variable[C,V],...]:
        """
        Obtain one or more variables.

        Parameters
        ----------
            names : `str`
                The names of uninitialized variables to obtain
            **kwargs : `V`
                The names and values of initialized variables
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        kvars: tuple[Variable[C,V],...] = ()
        vars: tuple[Variable[C,V],...] = tuple(
            cast(Variable[C,V], find(name))
            for name in names
        )
        if len(kwargs) > 0:
            kvars =({k:Variable(k,v) for k,v in kwargs.items()},)
        return vars + kvars

    @overload
    def attribute[V](self, name1: str, *, cls: type[V]=type[object]) -> Attribute[C,V]:
        ...
    @overload
    def attribute[V](self, name1: str, *names: str,
                     cls: type[V]=type[object]) -> tuple[Attribute[C,V], ...]:
        ...
    def attribute[V](self, name1: str, *names: str,
                     cls: type[V]=type[object]
                  ) -> Attribute[C,V]|tuple[Attribute[C,V], ...]:
        """
        Obtain a single attribute reference.

        An attribute reference is a variable that is backed by an attribute on the context object.

        Compatibility
        -------------
            Since 1.4.0:
            For multiple attributes, use the `attributes` method.
       
        Parameters
        ----------
            name: str - the name of a single attribute  

        Returns
        -------
            An `Attribute[C,V]` referring to the context object's attribute.
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Attribute(self.target, name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Attribute[C,V], find(names[0]))
        return tuple(cast(Attribute[C,V],find(name)) for name in names)

    def attributes[V](self, name1: str,
                        *names: str,
                        _cls: type[V]=type[object],
                        **kwargs: V,
                        ) -> tuple[Variable[C,V],...]:
        """
        Obtain one or more attribute references.

        An attribute reference is a variable that is backed by an attribute on the context object.

        Attribute references created without initialization will have the pre-existing values
        in the context, if any.

        Parameters
        ----------
            names : str
                The names of uninitialized attribute references to obtain
            **kwargs : V
                The names and values of initialized attribute references
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        kvars: tuple[Variable[C,V],...] = ()
        vars: tuple[Variable[C,V],...] = tuple(
            cast(Variable[C,V], find(name))
            for name in names
        )
        if len(kwargs) > 0:
            kvars =({k:Variable(k,v) for k,v in kwargs.items()},)
        return vars + kvars

    def pipeline[V](self, *steps: Step[C,V]) -> Pipeline[C,V]:
        """
        create and run a pipeline in this variable context.

        Parameters
        ----------
            *steps: Step[C,V]
                The steps in the pipeline
        """
        return cast(Pipeline[C,V], pipeline(*steps)(self.target))

    def close(self):
        """
        On closing the context, make using the variables an error.
        """
        for (_, var) in self._variables.items():
            if hasattr(var, 'value'):
                delattr(var, 'value')  # future references to .value will error.
        self._variables.clear()
        self.closed = True     # Future uses of this context will error.

class PipelineContext(VariableContext[Any]):
    """
    A context object for pipeline variables.

    This is a `VariableObject` that is also a pipeline context object.
    It is a general-purpose context object for use in a pipeline,
    and also acts as a `VariableContext` for pipeline variables.
    """
    def __init__(self, **initial_variables: Any):
        super().__init__(self)
        self.target = self
        forbidden = vars(self)
        for (k, v) in initial_variables.items():
            if k in forbidden:
                raise ValueError(f"Variable name {k} is reserved.")
            setattr(self, k, v)

# Would be a @stepfn, but we have to be able to receive the Variable unchanged.
# A @stepfn receives pipeline variable values, never variables
def store[C,V](var: AbstractVariable[C, V], step:Step[C, V]|Any) -> Step[C,V]:
    """
    Store the result of the step in the supplied variable.

    Rather than a step as a 2nd argument, you can supply a literal value to store,
    so long as that value is not a callable.

    Parameters
    ----------
        var : `AbstractVariable[C, V]`
            The variable to store the result in
        step : `Step[C,V] | Any`
            The step to execute, or a literal value to store
    """
    @wraps(store)
    def store_(ctx: C):
        if callable(step):
            value = step(ctx)
        else:
            value = step
        var.value = cast(V, eval_vars(ctx, value))
        return var.value
    return cast(Step[C,V], store_)

@contextmanager
def variables[C](target: C) -> Generator[VariableContext[C], None, None]:
    """
    Returns a `VariableContext`, for use in a `with` statement.

    Parameters
    ----------
        target : C
            The context object
    """
    vctx = VariableContext(target)
    try:
        yield vctx
    finally:
        vctx.close()

@contextmanager
def context(**initial_variables) -> Generator[PipelineContext, None, None]:
    """
    Returns a `PipelineContext`, for use in a `with` statement.

    Parameters
    ----------
        **initial_variables : Any
            Initial parameters to define in this context.
    """
    vctx = PipelineContext(**initial_variables)
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

def eval_vars[C,V](ctx: C, val: Arg[V|AbstractVariable[C,V]], /,
                          depth: int=10
    ) -> Value[V]|Value[tuple[V,...]]|Value[list[V]]|Value[dict[str,V]]|Value[set[V]]|Value[frozenset[V]]:
    """
    Evaluate a pipeline variable, or any list, tuple, or dict
    that may contain them, up to _depth_ (default 10) depth.

    This is intended to evaluate variables in code literals,
    rather than a general object traversal.

    Parameters
    ----------
    ctx : C
            the context
    val : Arg[V]
        The value to evaluate
    depth : int
        The maximum depth to evaluate

    Returns
    -------
    V
        The evaluated value or structure with values substituted.

    Example:
    --------
        ```python
        ctx = {'a': 1, 'b': 2}
        with variables(ctx) as vctx:
            a, b = vctx.variables('a', 'b')
            assert eval_vars(ctx, [a, b]) == [1, 2]
        ```
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

def curry[C,V,**P](step_fn: Callable[Concatenate[C, ...], V],
          *args: P.args,
          **kwargs: P.kwargs,
         ) -> Step[C,V]:
    """
    Configure a `Step`, currying all but the first argument.
    The result is a function of one argument, the context.
    The curried arguments are evaluated in the context before calling the function.
    Thus, variables and attribute references will be resolved at runtime.

    Parameters
    ----------
        step_fn: `Callable[Concatenate[C, ...], V]` - the function to curry
        *args: `P.args` - the arguments to curry
        **kwargs: `P.kwargs` - the keyword arguments to curry

    Returns
    -------
        Step[C,V] - the curried step function

    Type Parameters
    ---------------
        C: The context type
        V: The return type
        P: The arguments type    
    """
    @wraps(step_fn)
    def step(ctx: C) -> V:
        nonlocal args, kwargs
        nargs = cast(list[V], args)
        xargs= [eval_vars(cast(C,ctx), cast(V,a)) for a in nargs]
        value = step_fn(ctx, *xargs, **kwargs)
        if isinstance(value, AbstractVariable):
            raise TypeError(f"Pipeline variable {value.__name__} being returned.")
        return value
    return cast(Step[C,V], step)

### Collect steps into a pipeline (itself a step)

def pipeline[C,V](*steps: Step[C,V], name: Optional[str] = None) -> Step[C,V]:
    """
    Return a new function that calls each function on the same arguments,
    returning the last return value.
    
    Parameters
    ----------
        *steps : `Step[C,V]`
            The steps in the pipeline

    Returns
    -------
        `Step[C,V]` - the pipeline function
    """
    @wraps(steps[0] if steps else None)
    def run_pipeline(ctx:C) -> V:
        result = None
        for fun in steps:
            result = fun(ctx)
        return cast(V,eval_vars(ctx, result))
    return cast(Step[C,V], run_pipeline)

### Condition Modifiers

def not_[C](cond_: Condition[C], name: Optional[str] = None) -> Condition[C]:
    """
    Negate a Condition
    
    Parameters
    ----------
        cond_ : `Condition[C]`
            the condition to negate

    Returns
    -------
        `Condition[C]` - the negated condition
    """
    @wraps(cond_)
    def negator(ctx: C) -> bool:
        return not cond_(ctx)
    return cast(Condition[C], negator)

def or_[C](*conditions: Condition[C], name: Optional[str] = None) -> Condition[C]:
    """
    Combine conditions with OR

    Parameters
    ----------
        *conditions : `Condition[C]`
            The conditions to combine

    Returns
    -------
        `Condition[C]` - the combined condition
    """
    if name is None:
        name = '|'.join((getattr(c, '__name__') for c in conditions))
    fn = conditions[0] if conditions else None
    @wraps(fn)
    def cond(ctx: C) -> bool:
        for lcond in conditions:
            if lcond(ctx):
                return True
        return False
    return cast(Condition[C], cond)

def and_[C](*conditions: Condition[C], name: Optional[str] = None) -> Condition[C]:
    """
    Combine conditions with AND

    Parameters
    ----------
        *conditions : `Condition[C]`
            the conditions to combine

    Returns
    -------
        `Condition[C]` - the combined condition

    """
    @wraps(conditions[0] if conditions else None)
    def cond(ctx: C) -> bool:
        return all((lcond(ctx) for lcond in conditions))
    return cast(Condition[C], cond)

### Step wrappers


def if_[C,V](
    cond_: Condition[C],
    then_: Step[C,V] | list[Step[C,V]] | None,
    else_: Optional[Step[C,V] | list[Step[C,V]]] = None,
    /,
) -> Step[C,V]:
    """
    Evaluate `cond_`. If true, call `then_`, otherwise `else_`. If no `else_`, return `None`.
    
   Parameters
   ----------
        cond_ : `Condition[C]`
            The condition to evaluate
        then_ : `Step[C,V], | list[Step[C,V]] | None`
            The step(s) to execute if the condition is true
        else_ : `Step[C,V], | list[Step[C,V]]`, optional
            The step(s) to execute if the condition is false

    Returns
    -------
        `Step[C,V]` - the if-then-else step
    """
    if isinstance(then_, list):
        then_ = pipeline(*then_)
    if isinstance(else_, list):
        else_ = pipeline(*else_)
    @wraps(if_)
    def if_step(ctx: C):
        if cond_(ctx):
            if then_ is None:
                return None
            return then_(ctx)
        elif else_ is not None:
            return else_(ctx)
        else:
            return None
    return cast(Step[C, V], if_step)

### Utility Steps

@stepfn
def apply[C,V,**P](ctx: C, expr: Callable[Concatenate[C,P], V],
                   *args: P.args,
                   **kwargs: P.kwargs) -> V:
    """
    A step that applies a function to the supplied arguments and returns the values.
    This is a `StepFn`, so pipeline variables can be supplied as arguments and be
    evaluated before calling the function.

    It's a `StepFn`, so it returns a `Step` that can be used anywhere steps (or conditions)
    are allowed.

    Parameters
    ----------
        ctx : `C`
            The context
        expr : `Callable[Concatenate[C,P], V]`
            The function to call
        *args : P.args
            The arguments to the function
        **kwargs : P.kwargs
            The keyword arguments to the function

    Returns
    -------
        `V` - the result of the function call
    """
    return expr(ctx, *args, **kwargs)

@stepfn
def list_[V](ctx: object, *args: V) -> list[V]:
    """
    Create a `list`, evaluating any variables found.

    Parameters
    ----------
        ctx : object
            The context
        *args: V
            The list elements

    Returns
    -------
        list[V] - the list
    """
    val = [eval_vars(ctx, v) for v in args]
    return cast(list[V], val)

@stepfn
def dict_[V](ctx: object, **kwargs:V) -> dict[str,V]:
    """
    Create a `dict` object, evaluating any variables found.

    Parameters
    ----------
        ctx : `object`
            The context
        **kwargs: `V`
            The key-value pairs
    
    Returns
    -------
        `dict[str,V]` - the dictionary
    """
    val = {k:eval_vars(ctx, v) for k,v in kwargs.items()}
    return cast(dict[str, V], val)

@stepfn
def tuple_[V](ctx: object, *args:V) -> tuple[V, ...]:
    """
    Create a tuple, evaluating any variables found.

    Unlike the tuple function, this takes arguments like list.
    Use the * to unpack an iterable into the arguments.

    Parameters
    ----------
        ctx : `object`
            The context
        *args: `V`
            The tuple elements

    Returns
    -------
        `tuple[V, ...]` - the tuple
    """
    val = tuple((eval_vars(ctx, v) for v in args))
    return cast(tuple[V,...], val)

@stepfn
def set_[V](ctx: object, *args: V) -> set[V]:
    """
    Create a set, evaluating any variables found.

    Parameters
    ----------
        ctx : `object`
            The context
        *args: `V`
            The set elements
    """
    val = set((eval_vars(ctx, v) for v in args))
    return cast(set[V], val)
