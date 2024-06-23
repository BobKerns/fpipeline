#!/usr/bin/env python -m unittest -v

from unittest import TestCase, skip
from dataclasses import dataclass, field
from collections import namedtuple

from fpipeline import (
    stepfn, conditionfn,
    pipeline,variables, context,
    store, eval_vars,
    if_, not_, and_, or_,
    Variable,
    VariableContext, PipelineContext
)

# Setup

@dataclass
class Ctx:
    value: any = None
    result: any = None # Used for testing store()
    trace: list[tuple] = field(default_factory=list)

@stepfn
def tstep(data: Ctx, *args, **kwargs):
    d = (*args, {**kwargs})
    data.trace.append(d)
    return data

def get_trace(data: Ctx):
    return data.trace

@stepfn
def ok(_: Ctx):
    return 'OK'

@stepfn
def fail(_: Ctx):
    return "Failed"

@conditionfn
def has_value(data: Ctx, value):
    return data.value == value

@conditionfn
def true(_: Ctx):
    return True

@conditionfn
def false(_: Ctx):
    return False

class TestFPipeline(TestCase):
    def test_step_single_arg(self):
        self.assertEqual(tstep(7, 8).__code__.co_argcount, 1)

    def test_condition_single_arg(self):
        self.assertEqual(has_value(7, 8).__code__.co_argcount, 1)
        
    def test_step_capture_args(self):
        data = Ctx()
        tstep(1, 2, 3, a=4, b=5)(data)
        self.assertEqual(data.trace, [(1, 2, 3, {'a': 4, 'b': 5})])

    def test_condition_capture_args_true(self):
        data = Ctx(7)
        self.assertTrue(has_value(7)(data))

    def test_condition_capture_args_false(self):
        data = Ctx()
        self.assertFalse(has_value(7)(data))

    @skip("Python bug makes @wrap unreliable")
    def test_stepfn_name(self):
        import sys
        self.assertEqual(tstep.__code__.co_name, "step_fn")
        self.assertEqual(tstep.__name__, 'tstep')
    
    @skip("Python bug makes @wrap unreliable")
    def test_conditionfn_name(self):
        self.assertEqual(has_value.__code__.co_name, "condition_fn")
        self.assertEqual(has_value.__name__, 'has_value')   

    def test_simple_pipeline(self):
        ctx = Ctx()
        p = pipeline(
                tstep(7),
                tstep(78),
        )
        p(ctx)
        self.assertEqual(get_trace(ctx), [(7, {}),
                                          (78, {})])

    def test_if_true(self):
        s = if_(
            true(),
            ok()
        )
        self.assertEqual(s(Ctx()), 'OK')

    def test_if_false(self):
        p = if_(
            false(),
            ok()
        )
        self.assertTrue(p(Ctx()) is None)
    
    def test_if_true_else(self):
        p = if_(
            true(),
            ok(),
            fail()
        )
        self.assertEqual(p(Ctx()), 'OK')
    
    def test_if_false_else(self):
        p = if_(
            false(),
            fail(),
            ok()
        )
        self.assertEqual(p(Ctx()), 'OK')

    def test_if_not_true(self):
        p = not_(true())
        self.assertFalse(p(Ctx()))
    
    def test_if_not_false(self):
        p = not_(false())
        self.assertTrue(p(Ctx()))

    def test_or_0(self):
        p = or_()
        self.assertFalse(p(Ctx()))

    def test_or_true(self):
        p = or_(true())
        self.assertTrue(p(Ctx()))

    def test_or_false(self):
        p = or_(false())
        self.assertFalse(p(Ctx()))

    def test_or_t_f(self):
        p = or_(true(), false())
        self.assertTrue(p(Ctx()))

    def test_or_f_t(self):
        p = or_(false(), true())
        self.assertTrue(p(Ctx()))

    def test_or_t_t(self):
        p = or_(true(), true())
        self.assertTrue(p(Ctx()))

    def test_or_f_f(self):
        p = or_(false(), false())
        self.assertFalse(p(Ctx()))

    def test_and_0(self):
        p = and_()
        self.assertTrue(p(Ctx()))

    def test_and_true(self):
        p = and_(true())
        self.assertTrue(p(Ctx()))
    
    def test_and_false(self):
        p = and_(false())
        self.assertFalse(p(Ctx()))

    def test_and_f_f(self):
        p = and_(false(), false())
        self.assertFalse(p(Ctx()))  

    def test_and_t_f(self):
        p = and_(true(), false())
        self.assertFalse(p(Ctx()))

    def test_and_t_f(self):
        p = and_(true(), false())
        self.assertFalse(p(Ctx()))

    def test_and_f_t(self):
        p = and_(false(), true())
        self.assertFalse(p(Ctx()))

    def test_and_t_t(self):
        p = and_(true(), true())
        self.assertTrue(p(Ctx()))

    def test_and_f_f(self):
        p = and_(false(), false())
        self.assertFalse(p(Ctx()))

    def test_close_vars(self):
        def f0(ctx: Ctx):
            with variables(ctx) as vars:
                return vars
        ctx = Ctx()
        r = f0(ctx)
        self.assertTrue(r.closed)

    def test_clear_vars(self):
        @stepfn
        def f1(ctx: Ctx):
            with variables(ctx) as vars:
                v1, v2 = vars.variable('v1', 'v2')
                a1, a2 = vars.attribute('value', 'a2')
                return vars
        ctx = f1()(Ctx())
        self.assertEqual(len(ctx._variables), 0)

    def test_check_vars_lifecycle(self):
        @stepfn
        def f2(ctx: Ctx):
            c = VariableContext(ctx)
            v = c.variable('v')
            a = c.attribute('a')
            c.close()
        self.assertIsNone(f2()(Ctx()))

    def test_check_vars_recorded(self):
        @stepfn
        def f3(ctx: Ctx):
            with variables(ctx) as vars:
                v1, v2 = vars.variable('v1', 'v2')
                a1, a2 = vars.attribute('a1', 'a2')
                return list(vars._variables.keys())
        self.assertEqual(f3()(Ctx()), ['v1', 'v2', 'a1', 'a2'])
    
    def test_check_Attribute_value(self):
        @stepfn
        def f4(ctx: Ctx):
            with variables(ctx) as vars:
                a = vars.attribute('value')
                return a.value
        self.assertEqual(f4()(Ctx(7)), 7)

    def test_check_Attribute_return(self):
        @stepfn
        def f5(ctx: Ctx):
            with variables(ctx) as vars:
                a = vars.attribute('value')
                return a
        self.assertRaises(Exception, f5(Ctx(55)))
    
    def test_variables(self):
        "::  with variables:"
        @stepfn
        def f6(ctx: Ctx):
            with variables(ctx) as vars:
                v1, v2 = vars.variable('v1', 'v2')
                v1.value = 'a'
                v2.value = v1.value
                return v2.value
        self.assertEqual(f6()(Ctx()), 'a')

    def test_variable_return_forbidden(self):
        ":: Variables should not be returned from steps"
        @stepfn
        def f7(ctx: Ctx):
            with variables(ctx) as vars:
                v = vars.variable('value')
                return v
        self.assertRaises(Exception, f7(Ctx(55)))

    def test_variable_pipeline_return_variable(self):
        ":: Variables should not be returned from pipelines"
        @stepfn
        def f8(ctx: Ctx):
            with variables(ctx) as vars:
                v = vars.variable('value')
                v.value = 55
                return v.value
        self.assertEqual(f8()(Ctx(55)), 55)
    
    def test_store(self):
        @stepfn
        def f9(ctx: Ctx):
            with variables(ctx) as vars:
                v, r = vars.attribute('value', 'result')
                return vars.pipeline(
                    store(r, v)
                )
        self.assertEqual(f9()(Ctx(7)), 7)
    
    def test_store_ctx_result(self):
        @stepfn
        def f10(ctx: Ctx):
            with variables(ctx) as vars:
                v, r = vars.attribute('value', 'result')
                return vars.pipeline(
                    store(r, v),
                    lambda data: data # Return the context data for examination
                )
        ctx = Ctx(72)
        f10()(ctx)
        self.assertEqual(ctx.result, 72)

    def test_eval_vars_simple(self):
        self.assertEqual(eval_vars({}, [3, {'a': 5}, (7, 3)]),
                            [3, {'a': 5}, (7, 3)])

    def test_eval_vars_variable(self):
        vv = Variable('vv')
        vv.value = 77
        self.assertEqual(eval_vars({}, vv), 77)
    
    def test_eval_vars_named_tuple(self):
        snt = Variable('snt')
        snt.value = 77
        tup = namedtuple('typ', ['x', 'y'])
        self.assertEqual(eval_vars({}, tup(3, snt)),
                         tup(3, 77))
        
    def test_eval_vars_set(self):
        vset = Variable('vset')
        vset.value = 42
        self.assertEqual(eval_vars({}, {8, vset, 42}),
                         {8, 42})
    
    def test_pipeline_struct_return(self):
        @stepfn
        def f11(ctx: Ctx):
            with variables(ctx) as vars:
                x, y = vars.attribute('x', 'y')
                return vars.pipeline(lambda data: (y, x))
        self.assertEqual(f11()({'x': 5, 'y': 7}),
                         (7, 5))
    
    def test_PipelineContext(self):
        @stepfn
        def f12(ctx: PipelineContext, v1: int, v2: int):
            return (v1, v2)
        def f12a():
            with context(x=5, y=17) as ctx:
                x, y = ctx.attribute('x', 'y')
                return ctx.pipeline(f12(x, y))
        self.assertEqual(f12a(), (5, 17))

    def test_PipelineContext_attrs_on_context(self):
        @stepfn
        def f13(ctx: PipelineContext, v1: int, v2: int):
            return (v1, v2)
        def f13a():
            with context(x=5, y=17) as ctx:
                x, y = ctx.attribute('x', 'y')
                ctx.pipeline(f13(x, y))
                return (ctx.x, ctx.y)
        self.assertEqual(f13a(), (5, 17))
    
    def test_PipelineContext_variables(self):
        @stepfn
        def f14(ctx: PipelineContext, v1: int, v2: int):
            return (v1, v2)
        def f14a():
            with context() as ctx:
                x, y = ctx.variables('x', 'y')
                return ctx.pipeline(
                    store(x, 5),
                    store(y, 17),
                    f14(x, y)
                )
        self.assertEqual(f14a(),
                         (5, 17))
        