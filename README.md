# fpipeline — Functional Pipeline

Simple but flexible python pipelines based on function composition.

Build your workflow step by step, then flexibly combine the steps to make a bigger step. Conditional
execution and branching are also supported.

Organizing a data application as a pipeline brings many benefits:

* By naming each top-level operation, a degree of natural self-documentation is provided.
* Each step can easily be independently tested.
* The pipeline focuses on the overall sequence of operation and dataflow.
* A clear boundary between levels of abstraction. Details live in steps and conditions.

The pipeline orchestrates these pieces, while remaining entirely
agnostic about what the operations do.

## Steps

A step is a function of one argument, which we will
call the _context_. The context can be any object, including a dict, according to the needs of the application.

This single argument will be the same for all steps in an application, but different for each invocation.

Often, it will be an object representing the data the
pipeline is to operate on. It can also be contained in
an object or `dict` along with various metadata.

### _type_ `Step`[_D_,_V_]

A `Step` type hint is defined to be:

```python
Step = Callable[[D],V]
```

Where `D` and `V` are type variables,

Steps taking only a single argument would seem very
limiting. But we have a solution!

### _decorator_ `@stepfn`

To define a step function, we use the decorator [`@stepfn`](#decorator-stepfn). The function's first positional argument is interpreted as the context
argument. The function is replaced with a new function
that accepts all the other arguments, and returns a
new function that accepts the context argument (thus,
a [`Step`](#type-stepdv)), and invokes the original
function with all its arguments.

We transform this:

```python
@stepfn
def my_step(ctx; CTX, a; A, b: B, c: C) -> V:
```

into:

```python
def my_step(a: A, b: B, c: C) -> Step[CTX,V]:
```

or more informally

```python
my_step(A, B, C) -> (CTX) -> V
```

That is, we supply everything _except_ the first
argument, then apply the context parameter for
each data value processed by the pipeline.

It might seem that this limits us to constant values. However, the use of
[_pipeline variables_](#pipeline-variables) allow
different values to be injected at each execution. Pipelne variables are evaluated at each execution.

Using a simple protocol based on single-argument functions allows us to use them as building blocks, to combine them into entire pipelines, and to combine pipelines into larger pipelines, all following the same protocol.

## Pipeline variables

To allow passing values between pipeline [`Step`s](#type-stepdv) in a flexible way, we provide two forms of _pipeline variables_, that allow capture of the return value of a [`Step`](#type-stepdv), and then supply it as an argument to a later step
function, all handled by the behind the scenes.

Pipeline variables will hold any value.

A pipeline variable is also callable as a [`Step`](#steps), allowing them to be used in a
pipeline to provide a return value for the pipeline.

### _function_ `variables`(_context_)

`variables` returns a [`VariableContext`](#class-variablecontext), which is a python [context manager](https://docs.python.org/3/library/stdtypes.html#context-manager-types). This is used in a `with ... as ...` statement.

The resulting [`VariableContext`](#class-variablecontext) gives out pipeline variables and manages their scope.

### _class_ `VariableContext`

A [context manager](https://docs.python.org/3/library/stdtypes.html#context-manager-types) that manages [pipeline variables](#pipeline-variables).

Usage goes like this:

```python
# Dummy StepFns to illustrate
@stepfn
def readAssetStep(data: Data, path: str) -> Asset:
    return path

@stepfn
def mergeAssetsStep(data: Data, asset1: Asset, asset2: Asset) -> Asset:
    return f"{asset1}+{asset2}"

@stepfn
def writeAssetStep(data: Data, asset: Asset, path: str) -> Asset:
    print(f"{path}: ${asset}")

# a `StepFn` (a pipeline is a `Step`) that takes two src paths to assets,
# merges them, stores the result in data.result, and writes it to a file.
# The asset paths are provided per-invocation in the context
# The output directory is configured as an argument
# when creating the pipeline.
@stepfn
def merge(data: Data, outdir: str) -> Asset:
    with variables() as vars:
        # declare the pipeline variables that we need
        src1, src2 = vars.attribute('src1', 'src2')
        asset1 = vars.variable('asset1', 'asset2')
        result = vars.variable('result') # stors in data.result
        return vars.pipeline(
            store(asset2, readAssetStep(src2)),
            store(asset1, readAssetStep(src1),
            store(result, mergeAssetsStep(asset1, asset2),
            writeAssetStep(result, outdir),
            result
        )(data)
```

`merge` can now be invoked by omitting the _data_ argument, giving a function of one
argument (_data_).

```python
pair1 = {
    'asset1': '/data/assets/src1',
    'asset2': '/data/assets/src2'
}
merge_and_store = merge(outdir='/data/assets/merged')

# Perform the operation
merged = merge_and_store(pair1)
```

Our new [`Step`](#type-stepdv) (`merge_and_store`) can then be calld for
each merger to be performed.

If we have two directories of files to be merged, this will take them
pairwise and feed each pair through the
pipeline.

```python
def get_assets(asset1, asset2):
    list1 = glob.glob(asset1)
    list2 = glob.glob(asset2)
    paired = zip(list1, list2)
    return ({'asset1': a1, 'asset2': a2}
            for (a1, a2) in paired)
left = '/data/assets1/*.asset'
right = '/data/assets2/*.asset'
results = list(map(merge_and_store, get_assets(left, right)))
```

#### _method_ `VariableContext.variable`(`*`_names_)

Returns a [`Variable`](#class-variable), or a tuple of [`Variable`s](#class-variable) if more than one name is given.

This allows assignment of multiple
variables in a single statement:

```python
    a, b = vars.variable('a', 'b')
```

#### _method_ `VariableContext.attribute`(`*`_names_)

Returns a type of pipeline variable called [`Attribute](#class-attribute), or a tuple of [`Attribute`s](#class-attribute) if
more than one name is given.

This allows assignment of multiple
attribute variables in a single statement:

```python
    a, b = vars.attribute('a', 'b')
```

### _class_ `Variable`

Represents a place to store and retrieve values between steps.

#### _attribute_ `Variable.value`

The value of a [`Variable`](#class-variable). Not usually referenced directly; rather the variable is passed to step functions, or assigned with the [`store`](#function-storevariable-step) step function.

#### _attribute_ `Variable.name`

The name of the variable. It must be unique within a [`VariableContext`](#class-variablecontext). Multiple uses of the same name will yield the same variable.

### _class_ `Attribute`

A pipeline variable that access the context. The name names the field or key to access.

#### _attribute_ `Attribute.value`

The value of a [`Attribute`](#class-variable). Not usually referenced directly; rather the variable is passed to step functions, or assigned with the [`store`](#function-storevariable-step) step function.

#### _attribute_ `Attribute.name`

The name of the variable. It must be unique within a [`VariableContext`](#class-variablecontext). Multiple uses of the same name will yield the same variable.

It is also the name of the field or key in the context.

### _function_ `store`(_variable_, _step_)

Store the result of _step_ into the _variable_.

## Conditional execution

A pipeline that executes every step on every input would severely limit flexibility.

`fpipeline` provides for branching, allowing steps to be skipped where
they don't apply, or entire different flows be selected.

The primary means is via the [`if_`](#stepfn-if_cond-then-else) step function.

> These functions have a '_' suffix to avoid conflicts
while maintaining readability. They are not in any
sense private; they ae a fully public part of the
interface.

### _`@stepfn`_ `if_`(_cond_, _then_, _else_)

_cond_ is a `Condition`, which is like a `Step` except the return value is a `bool`. It should be defined using the
`@conditionfn` decorator in the same way as
`@stepfn` is used for step functions.

_then_ and _else_ are steps (or pipelines),
executed according to the value of _cond_.
They may be omitted or supplied as None.

### _`@condfn`_ `not_`(_cond_)

`not_` returns a new `Condition` with the opposite sense.

### _`@condfn`_ `and_`(`*`_conds_)

`and_` returns a new `Condition` that returns
`False` if any of its arguments return `False`,
and `True` otherwise.

### _`@condfn`_ `or_`(`*`_conds_)

`or_` returns a new `Condition` that returns
`True` if any of its arguements return `True`,
and `False` otherwise.
