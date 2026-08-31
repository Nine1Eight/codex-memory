import ast
import operator
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Math Service")

# Safe operators for evaluation
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

class EvaluateRequest(BaseModel):
    expression: str

class EvaluateResponse(BaseModel):
    result: float

class ValidateRequest(BaseModel):
    state: float
    action: str   # one of '+', '-', '*', '/'

class ValidateResponse(BaseModel):
    valid: bool
    reason: str = ""

def safe_eval(expr: str) -> float:
    """Evaluate a mathematical expression safely using AST."""
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError:
        raise ValueError("Invalid syntax")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type}")
            return ALLOWED_OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type}")
            return ALLOWED_OPERATORS[op_type](operand)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value}")
        else:
            raise ValueError(f"Unsupported node: {type(node)}")

    try:
        return float(_eval(tree))
    except Exception as e:
        raise ValueError(f"Evaluation error: {str(e)}")

@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_endpoint(req: EvaluateRequest):
    try:
        result = safe_eval(req.expression)
        return EvaluateResponse(result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/validate", response_model=ValidateResponse)
async def validate_endpoint(req: ValidateRequest):
    valid = True
    reason = ""

    if req.action not in ('+', '-', '*', '/'):
        valid = False
        reason = "Action must be one of '+', '-', '*', '/'"
    elif req.action == '/' and req.state == 0:
        valid = False
        reason = "Division by zero"

    return ValidateResponse(valid=valid, reason=reason)
