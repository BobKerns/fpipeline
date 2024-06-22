'''Functional Pipelines. A simple pipeline based on functional composition.'''

# The full package is exported from here for backwards compatibility.

from fpipeline.types import *
from fpipeline.variables import *
from fpipeline.contexts import *
from fpipeline.decorators import *
from fpipeline.functions import *
from fpipeline.steps import *
from ._version import *

FPIPELINE_ALL: list[str] = [
    'Step', 'Condition', 'Pipeline',
    'pipeline', 'variables', context, 'stepfn', 'conditionfn',
    'if_', 'not_', 'and_', 'or_',
    'Variable', 'Attribute', 'VariableContext', 'PipelineContext',
    'store', 'eval_vars',
    'list_', 'dict_', 'tuple_', '–set_', 'apply',
    '__version__', 'ID', 'FPIPELINE_ALL'
]
"Everything publicly exported in the package."

__ALL__ = FPIPELINE_ALL