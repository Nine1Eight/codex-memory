import ast
import random
import hashlib

MAX_DEPTH = 3

LIB_GENES = ["json", "requests", "threading"]

def random_genome():
    return {k: random.choice([True, False]) for k in LIB_GENES}

def crossover(g1, g2):
    return {k: random.choice([g1[k], g2[k]]) for k in LIB_GENES}

# -----------------------------
# AST NODE GENERATION
# -----------------------------

def random_value():
    return random.choice([
        ast.Constant(value=random.randint(0, 10)),
        ast.Constant(value=random.random())
    ])

def random_binary():
    return ast.BinOp(
        left=random_value(),
        op=random.choice([ast.Add(), ast.Sub(), ast.Mult()]),
        right=random_value()
    )

def random_statement(depth=0):
    if depth > MAX_DEPTH:
        return ast.Expr(value=random_value())

    choices = [
        ast.Expr(value=random_binary()),
        ast.Assign(
            targets=[ast.Name(id="x", ctx=ast.Store())],
            value=random_binary()
        ),
        ast.If(
            test=ast.Compare(
                left=random_value(),
                ops=[ast.Gt()],
                comparators=[random_value()]
            ),
            body=[random_statement(depth+1)],
            orelse=[]
        ),
        ast.For(
            target=ast.Name(id="i", ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id="range", ctx=ast.Load()),
                args=[ast.Constant(value=random.randint(1,5))],
                keywords=[]
            ),
            body=[random_statement(depth+1)],
            orelse=[]
        )
    ]

    return random.choice(choices)

def build_function():
    body = [random_statement() for _ in range(random.randint(1,5))]
    body.append(ast.Return(value=random_value()))

    return ast.FunctionDef(
        name="evolved",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[]
        ),
        body=body,
        decorator_list=[]
    )

def build_ast(genome):
    module = ast.Module(body=[], type_ignores=[])

    for lib in LIB_GENES:
        if genome[lib]:
            module.body.append(ast.Import(names=[ast.alias(name=lib, asname=None)]))

    func = build_function()
    module.body.append(func)

    module.body.append(
        ast.Expr(
            value=ast.Call(
                func=ast.Name(id="evolved", ctx=ast.Load()),
                args=[],
                keywords=[]
            )
        )
    )

    ast.fix_missing_locations(module)
    return module
