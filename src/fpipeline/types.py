"""
Core types
"""

from abc import ABC, abstractmethod
from typing import (
    Callable, Optional, Sequence, Protocol, runtime_checkable,
)

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

@runtime_checkable
class Closeable(Protocol):
    """An abstract class for objects implementing a close method."""
    def close(self) -> None:
        ...

type ContextFactory[C] = Callable[[], C]