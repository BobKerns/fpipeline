"""Functional Pipeline. A simple pipeline facility built on function composition.

Our composition operator is `pipeline`.
"""

from typing import (
    Callable, Concatenate, cast,
    )
from functools import wraps

from .types import Step, Condition
from .functions import curry

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
