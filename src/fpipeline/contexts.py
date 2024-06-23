"""
Contexts for pipeline variables.
"""

from dataclasses import dataclass, field
from typing import Any, cast, overload, Optional

from fpipeline.types import Pipeline, Step
from fpipeline.variables import AbstractVariable, Variable, Attribute, Resource

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
    "The context for the pipeline steps."
    parent: Optional['VariableContext[C]'] = None
    "The parent context, if any"
    _variables: dict[str, AbstractVariable[C, Any]] = field(default_factory=dict)
    closed: bool = False
    "Flag indicating this context is closed and no longer valid."

    @overload
    def variable[V](self, name1: str, *,
                    cls: type[V]=type[Any]
                    ) -> Variable[C,V]:
        ...
    @overload
    def variable[V](self, name1: str, *names: str,
                      cls: type[V]=type[object]
                      ) -> tuple[Variable[C,V],...]:
        ...
    @overload
    def variable[V](self, name1: str, *,
                    create: bool,
                    cls: type[V]=type[Any]
                    ) -> Variable[C,V] | None:
        ...
    @overload
    def variable[V](self, name1: str, *names: str,
                      create: bool,
                      cls: type[V]=type[object]
                      ) -> tuple[Variable[C,V],...] | None:
        ...
    def variable[V](self, name1: str,
                    *names: str,
                    create: bool=True,
                    _cls: type[V]=type[object]
                    ) -> Variable[C,V] | tuple[Variable[C,V],...] | None:
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
            create: bool
                Whether to create the variable if it does not exist (default `True`)
            _cls : type[V]
                The type of the variable, default=Any

        Returns
            `Variable[C,V]` The variable, or
            `None` if the variable does not exist and `create` is `False`.
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                if self.parent:
                    var = self.parent.variable(name, _cls=_cls)
                    if var:
                        return var
                if not create:
                    return None
                var = Variable(name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Variable[C,V], find(names[0]))
        return tuple((cast(Variable[C,V], find(name)) for name in names))
    
    @overload
    def variables[V](self, name1: str,
                    *names: str,
                    _cls: type[V]=type[object],
                    **kwargs: V,
                    ) -> tuple[Variable[C,V],...]:
        ...
    @overload
    def variables[V](self, name1: str,
                    *names: str,
                    create: bool,
                    _cls: type[V]=type[object],
                    **kwargs: V,
                    ) -> tuple[Variable[C,V] | None,...]:
        ...
    def variables[V](self, name1: str,
                    *names: str,
                    create: bool=True,
                    _cls: type[V]=type[object],
                    **kwargs: V,
                    ) -> tuple[Variable[C,V] | None,...]:
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
                if self.parent:
                    var = self.parent.variable(name, create=False, _cls=_cls)
                    if var:
                        return var
                if not create:
                    return None
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
    def attribute[V](self, name1: str, *,
                     cls: type[V]=type[object]) -> Attribute[C,V]:
        ...
    @overload
    def attribute[V](self, name1: str, *names: str,
                     cls: type[V]=type[object]
                     ) -> tuple[Attribute[C,V], ...]:
        ...
    @overload
    def attribute[V](self, name1: str, *,
                     create: bool,
                     cls: type[V]=type[object]
                     ) -> Attribute[C,V] | None:
        ...
    @overload
    def attribute[V](self, name1: str, *names: str,
                     create: bool,
                     cls: type[V]=type[object]
                     ) -> tuple[Attribute[C,V], ...] | None:
        ...
    def attribute[V](self, name1: str, *names: str,
                     create: bool=True,
                     cls: type[V]=type[object]
                  ) -> Attribute[C,V] | tuple[Attribute[C,V], ...] | None:
        """
        Obtain a single attribute reference.

        An attribute reference is a variable that is backed by an attribute on the context object.

        Compatibility
        -------------
            Since 1.4.0:
            For multiple attributes, use the `attributes` method.
       
        Parameters
        ----------
            name: str
                The name of a single attribute 
            create: bool
                Whether to create the attribute if it does not exist (default `True`)

        Returns
        -------
            An `Attribute[C,V]` referring to the context object's attribute.
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                if self.parent:
                    var = self.parent.variable(name, create=False)
                    if var:
                        return var
                if not create:
                    return None
                var = Attribute(self.target, name)
                self._variables[name] = var
            return self._variables[name]
        if len(names) == 1:
            return cast(Attribute[C,V], find(names[0]))
        return tuple(cast(Attribute[C,V],find(name)) for name in names)

    @overload

    def attributes[V](self, name1: str,
                        *names: str,
                        _cls: type[V]=type[object],
                        **kwargs: V,
                        ) -> tuple[Variable[C,V],...]:
        ...
    def attributes[V](self, name1: str,
                        *names: str,
                        create: bool,
                        _cls: type[V]=type[object],
                        **kwargs: V,
                        ) -> tuple[Variable[C,V],...] | None:
        ...
    def attributes[V](self, name1: str,
                        *names: str,
                        create: bool=True,
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
            create: bool
                Whether to create the attribute if it does not exist (default `True`)
            **kwargs : V
                The names and values of initialized attribute references

        Returns
        -------
            tuple[Attribute[C,V],...]
                The attribute references
        """
        names = (name1, *names)
        def find(name):
            if not name in self._variables:
                if self.parent:
                    var = self.parent.variable(name, create=False)
                    if var:
                        return var
                if not create:
                    return None
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
        from .functions import pipeline
        return cast(Pipeline[C,V], pipeline(*steps)(self.target))

    def close(self):
        """
        On closing the context, make using the variables an error.
        """
        for (_, var) in self._variables.items():
            if hasattr(var, 'value'):
                if isinstance(var, Resource):
                    var.close()
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
    def __init__(self,
                 parent: Optional[VariableContext[Any]] = None,
                 **initial_variables: Any):
        super().__init__(self, parent=parent)
        self.target = self
        forbidden = vars(self)
        for (k, v) in initial_variables.items():
            if k in forbidden:
                raise ValueError(f"Variable name {k} is reserved.")
            setattr(self, k, v)
