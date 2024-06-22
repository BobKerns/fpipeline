'''Functional Pipelines. A simple pipeline based on functional composition.'''

from .fpipeline import pipeline, variables, context, stepfn, conditionfn, \
    if_, not_, and_, or_, Variable, Attribute, VariableContext, PipelineContext, \
    store, eval_vars, \
    list_, dict_, tuple_, set_, apply

from ._version import __version__, ID

__all__ = [
    'pipeline', 'variables', context, 'stepfn', 'conditionfn',
    'if_', 'not_', 'and_', 'or_',
    'Variable', 'Attribute', 'VariableContext', 'PipelineContext',
    'store', 'eval_vars',
    'list_', 'dict_', 'tuple_', 'set_', 'apply',
    '__version__', 'ID',
]