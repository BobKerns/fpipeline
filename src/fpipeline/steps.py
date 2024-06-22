"""
Various `StepFn` implementations. Loaded last.
"""

from typing import Any, Callable, Concatenate, Optional, cast
from functools import wraps

from .types import Step, Condition
from .variables import AbstractVariable
from .decorators import stepfn, conditionfn
from .functions import eval_vars, pipeline

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
