"""
Functions for fpipeline.

Separated to avoid circular dependencies.
"""

from typing import cast, Callable, Optional, Concatenate
from collections.abc import Generator
from contextlib import contextmanager
from functools import wraps

from .types import Step, Value, Arg
from .variables import AbstractVariable
from .contexts import VariableContext, PipelineContext

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