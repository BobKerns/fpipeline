"""
Decorators for fpipeline step and condition functions.
"""

from typing import (
    Callable, Concatenate, Optional, cast, overload,
    )
from functools import wraps

from .types import Step, Condition
from .functions import curry

### Annotations

def stepfn[C,V, **P](fnx: Optional[Callable[Concatenate[C,P], V]] = None) -> Callable[P, Step[C, V]]:
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
    return step_(fnx, _final=True)

@overload
def step_[C, V, **P](fnx: Optional[Callable[Concatenate[C,P], V]] = None) -> Callable[P, Step[C, C]]:
    ...
@overload
def step_[C, V, **P](_final: True) -> Callable[P, Step[C, V]]:
    ...
@overload
def step_[C, **P](_final: False) -> Callable[P, Step[C, C]]:
    ...
@overload
def step_[C, V, **P](_final: bool) -> Callable[P, Step[C, V]|Step[C, C]]:
    ...
def step_[C,V, **P](fnx: Optional[Callable[Concatenate[C,P],V]] = None, /,
                    _final: bool=False
                    ) -> Callable[P, Step[C, V]]|Step[C,C]|Step[C,V]:
    """
    An annotation for defining step functions. All but the first argument are curried.
    
    Parameters
    ----------
        fnx : `Callable[Concatenate[C, P], V]`
            The function to be annotated
        _final : bool, optional, keyword-only
            If True, the return type of the step function will be `Step[C, V]` instead of `Step[C, C]`

    Returns
    -------
        Callable[P, Step[C, C]] - a function that accepts the given arguments and returns a step function.
        Callable[P, Step[C, V]] - a function that accepts the given arguments and returns a step function, if _final=True

    Type Parameters
    ---------------
        C: The context type
        V: The return type
        P: The arguments type
    """
    def step_fn(*args: P.args, **kwargs: P.kwargs) -> Step[C,V]:
        if _final:
            return wraps(fnx)(curry(fnx, *args, **kwargs))
        def step_fn_return(ctx: C) -> V:
            fnx(ctx, *args, **kwargs)
            return ctx
        return wraps(fnx)(step_fn_return) # type: ignore
    if fnx:
        return wraps(fnx)(step_fn)
    def step_fn_(fnx: Callable[Concatenate[C,P], V]) -> Step[C,V]:
        return wraps(fnx)(step_fn)
    return wraps(step_)

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
    return condition_(fnx)

def condition_[C,V,**P](fnx: Optional[Callable[Concatenate[C,P], V]] = None) -> Callable[P, Condition[C]]:
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
    return cast(Condition[C], step_(fnx, _final=True))
