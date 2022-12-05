'''Functional Pipelines. A simple pipeline based on functional composition.'''

from .fpipeline import pipeline, variables, stepfn, conditionfn, \
    if_, not_, and_, or_, Variable, Attribute, VariableContext, store, eval_, \
    list_, dict_, tuple_

from ._version import __version__
