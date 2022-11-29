# fpipeline — Functional Pipeline

Simple Python but flexible pipelines based on function composition.

Build your workflow step by step, then flexibly combine the steps to make a bigger step.

## Pipeline variables

To allow passing values between pipeline `Step`s in a flexible way, we provide two forms of _pipeline variables_, that allow capture of the return value of a `Step`, and then supply it as an argument to a `StepFn`, all handled by the `step` function.

Pipeline variables will hold any value.

A pipeline variable is also callable as a `Step`, allowing them to be used in a
pipeline to provide a return value for the pipeline.

usage goes like this:

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
@stepfn
def merge(data: Data, outdir: str) -> Step:
    with variables() as vars:
        # declare the pipeline variables that we need
        src1, src2 = vars.attribute('src1', 'src2')
        asset1 = vars.variable('asset1', 'asset2')
        result = vars.variable('result') # stors in data.result
        return vars.pipeline(
            readAssetStep(src2, store=asset2),
            readAssetStep(src1, store=asset1),
            mergeAssetsStep(asset1, asset2, store=result),
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
