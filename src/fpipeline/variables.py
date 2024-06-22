"""
Pipeline Variable
-----------------

Pipeline variables are used to store and retrieve values in the pipeline. They communicate between steps,
storing intermediate results, or communicate results from and to the outside world.

Pipeline variables may be free-standing, or they may be tied to a context object, as attributes or as
dictionary keys.

If tied to a context object, they may support a context manager, allowing usage similar to a `with` statement,
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast, overload

class AbstractVariable[C,V]:
    """
    Abstract base for pipeline variables.
    
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
        # Import here to avoid circular imports      
        from .functions import eval_vars
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
