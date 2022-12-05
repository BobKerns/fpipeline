# fpipeline — Functional Pipeline

Simple but flexible python pipelines based on function composition.

Build your workflow step by step, then flexibly combine the steps to make a bigger step. Conditional
execution and branching are also supported.

## Steps

A step is a function of one argument, which we will
call the _context_. The context can be any object, including a dict, according to the needs of the application.

This single argument will be the same for all steps in an application.

Often, it will be an object representing the data the
pipeline is to operate on. It can also be contained in
an object or `dict` along with various metadata.

Steps taking only a single argument would seem very
limiting. But we have a solution! `Step` is defined to
be `Callable[[CTX], V].

So we transform this:

```python
def my_step(CTX, A, B, C) -> V:
```

into:

```python
def my_step(A, B, C) -> Step:
```

or

```python
def my_step(A, B, C) -> (CTX) -> V
```

That is, we supply everything _except_ the first
argument, then apply the context parameter for
each data value processed by the pipeline.

It might seem that this limits us to constant values.
However, the use of
[_pipeline variables_](#pipeline-variables) allow
different values to be injected at each execution.

Using a simple protocol based on single-argument functions allows us to use them as building blocks, to combine them into entire pipelines, and to combine pipelines into larger pipelines, all following the same protocol.

## Pipeline variables

To allow passing values between pipeline `Step`s in a flexible way, we provide two forms of _pipeline variables_, that allow capture of the return value of a `Step`, and then supply it as an argument to a `StepFn`, all handled by the behind the scenes.

Pipeline variables will hold any value.

A pipeline variable is also callable as a `Step`, allowing them to be used in a
pipeline to provide a return value for the pipeline.

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
def merge(data: Data, outdir: str) -> Step:
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
