"""Small helpers of the instrument.

`format_value` gives a value short, for display.

`evaluate` gives the number a component value stands for: a McStas expression of instrument
parameters ("-chi", "2.0*omega + 5") is parsed with `ast` and computed as McStas would, with only
what McStas offers allowed (no code is run).
"""

import ast
import math
import operator

# what an expression may use: McStas's constants and its C math functions
CONSTANTS = {"PI": math.pi, "DEG2RAD": math.pi / 180, "RAD2DEG": 180 / math.pi}
FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sqrt": math.sqrt,
    "fabs": math.fabs,
    "exp": math.exp,
    "log": math.log,
    "pow": math.pow,
}
_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def evaluate(entry, params: dict) -> float:
    """The number `entry` stands for: itself if a number, else the value of the McStas expression
    it is, with `params` (the instrument parameters by name). An expression may use numbers,
    instrument parameters, `CONSTANTS`, + - * /, signs, brackets and `FUNCTIONS`; anything else
    raises a ValueError. A division of two integers raises too: C would round it down (write 1.0/2).

    With params = {"omega": 30, "chi": 5}:
        evaluate(1.5, params)                     -> 1.5
        evaluate("omega", params)                 -> 30
        evaluate("-chi", params)                  -> -5
        evaluate("2.0*omega + chi", params)       -> 65.0
        evaluate("atan2(1, 1)*RAD2DEG", params)   -> 45.0
    """
    if not isinstance(entry, str):
        return entry

    def value(node):
        match node:
            case ast.Constant(value=int() | float() as number) if not isinstance(number, bool):
                return number
            case ast.Name(id=name) if name in params:
                return params[name]
            case ast.Name(id=name) if name in CONSTANTS:
                return CONSTANTS[name]
            case ast.BinOp(left=left, op=op, right=right) if type(op) in _BINARY:
                a, b = value(left), value(right)
                if isinstance(op, ast.Div) and isinstance(a, int) and isinstance(b, int):
                    msg = f"{entry!r}: C divides integers rounding down; write 1.0/2"
                    raise ValueError(msg)  # noqa: TRY004 (a bad expression, like the others)
                return _BINARY[type(op)](a, b)
            case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARY:
                return _UNARY[type(op)](value(operand))
            case ast.Call(func=ast.Name(id=name), args=args, keywords=[]) if name in FUNCTIONS:
                return FUNCTIONS[name](*(value(a) for a in args))
        raise ValueError(
            f"{entry!r}: {ast.unparse(node)!r} is not a number, an instrument parameter, a "
            "constant, + - * /, or a McStas math function"
        )

    try:
        tree = ast.parse(entry, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"{entry!r} is not an expression: {error.msg}") from None
    return value(tree.body)


def format_value(value) -> str:
    """`value` formatted for display: a number with at most 6 significant digits, a list of them
    in brackets, anything else as it is."""
    if isinstance(value, list):
        return "[" + ", ".join(format_value(v) for v in value) + "]"
    if isinstance(value, float | int) and not isinstance(value, bool):
        return f"{value:.6g}"
    return str(value)
