#!/usr/bin/env python3
"""Glyphmatics Math command-grid and execution-graph prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

ROWS = 19
COLS = 18
COMMAND_LIMIT = 333
PACK_BASE = 333


COMMANDS = {
    0: "END", 1: "LITERAL", 2: "IDENTIFIER", 3: "COMMENT",
    4: "NEWLINE", 5: "INDENT", 6: "DEDENT",
    10: "MODULE", 11: "IMPORT", 12: "FROM_IMPORT", 13: "AS",
    14: "GLOBAL", 15: "NONLOCAL",
    20: "ASSIGN", 21: "ADD_ASSIGN", 22: "SUB_ASSIGN", 23: "MUL_ASSIGN",
    24: "DIV_ASSIGN", 25: "WALRUS", 26: "DELETE",
    30: "FUNCTION", 31: "ASYNC_FUNCTION", 32: "RETURN", 33: "YIELD",
    34: "YIELD_FROM", 35: "LAMBDA", 36: "CALL", 37: "ARGUMENTS",
    40: "IF", 41: "ELIF", 42: "ELSE", 43: "FOR", 44: "ASYNC_FOR",
    45: "WHILE", 46: "BREAK", 47: "CONTINUE", 48: "PASS",
    50: "TRY", 51: "EXCEPT", 52: "FINALLY", 53: "RAISE",
    54: "ASSERT", 55: "WITH", 56: "ASYNC_WITH",
    60: "CLASS", 61: "ATTRIBUTE", 62: "INDEX", 63: "SLICE",
    64: "LIST", 65: "TUPLE", 66: "SET", 67: "DICTIONARY",
    70: "ADD", 71: "SUBTRACT", 72: "MULTIPLY", 73: "DIVIDE",
    74: "FLOOR_DIVIDE", 75: "MODULO", 76: "POWER", 77: "MATRIX_MULTIPLY",
    80: "EQUAL", 81: "NOT_EQUAL", 82: "LESS", 83: "LESS_EQUAL",
    84: "GREATER", 85: "GREATER_EQUAL", 86: "IS", 87: "IS_NOT",
    88: "IN", 89: "NOT_IN",
    90: "AND", 91: "OR", 92: "NOT", 93: "BIT_AND", 94: "BIT_OR",
    95: "BIT_XOR", 96: "BIT_NOT", 97: "SHIFT_LEFT", 98: "SHIFT_RIGHT",
    100: "NONE", 101: "TRUE", 102: "FALSE", 103: "INTEGER",
    104: "FLOAT", 105: "STRING", 106: "BYTES", 107: "F_STRING",
    108: "LIST_LITERAL", 109: "DICT_LITERAL",
    110: "PRINT", 111: "INPUT", 112: "LEN", 113: "RANGE",
    114: "ENUMERATE", 115: "ZIP", 116: "MAP", 117: "FILTER",
    118: "SUM", 119: "SORTED", 120: "OPEN", 121: "READ",
    122: "WRITE", 123: "APPEND", 124: "CLOSE",
    130: "INT", 131: "FLOAT_CAST", 132: "STRING_CAST", 133: "BOOL",
    134: "LIST_CAST", 135: "TUPLE_CAST", 136: "SET_CAST",
    137: "DICT_CAST", 138: "TYPE", 139: "ISINSTANCE",
    140: "DECORATOR", 141: "PROPERTY", 142: "STATIC_METHOD",
    143: "CLASS_METHOD", 144: "SUPER", 145: "SELF", 146: "INIT",
    147: "MATCH", 148: "CASE", 149: "AWAIT",
    150: "LOAD_TOKENIZER", 151: "TOKENIZE", 152: "TOKEN_IDS",
    153: "TOKEN_EMBEDDING", 154: "POSITION_INDEX", 155: "LAYER_BEGIN",
    156: "RMS_NORM_ATTENTION", 157: "PROJECT_QUERY", 158: "PROJECT_KEY",
    159: "PROJECT_VALUE", 160: "APPLY_ROPE", 161: "ATTENTION_SCORES",
    162: "CAUSAL_MASK", 163: "ATTENTION_SOFTMAX", 164: "ATTENTION_VALUES",
    165: "PROJECT_ATTENTION_OUTPUT", 166: "RESIDUAL_ATTENTION",
    167: "RMS_NORM_MLP", 168: "MLP_GATE", 169: "MLP_UP",
    170: "SILU_GATE", 171: "MLP_MULTIPLY", 172: "MLP_DOWN",
    173: "RESIDUAL_MLP", 174: "LAYER_END", 175: "FINAL_RMS_NORM",
    176: "LM_HEAD", 177: "LOGITS", 178: "TEMPERATURE",
    179: "TOP_K", 180: "TOP_P", 181: "SAMPLE_TOKEN",
    182: "APPEND_TOKEN", 183: "STOP_CHECK", 184: "DETOKENIZE",
    185: "OUTPUT_TEXT", 186: "KV_CACHE_READ", 187: "KV_CACHE_WRITE",
    188: "NEXT_LAYER", 189: "NEXT_TOKEN",
    200: "WEIGHT_TOKEN_EMBEDDING", 201: "WEIGHT_ATTN_NORM",
    202: "WEIGHT_QUERY", 203: "WEIGHT_KEY", 204: "WEIGHT_VALUE",
    205: "WEIGHT_ATTN_OUTPUT", 206: "WEIGHT_MLP_NORM",
    207: "WEIGHT_MLP_GATE", 208: "WEIGHT_MLP_UP", 209: "WEIGHT_MLP_DOWN",
    210: "WEIGHT_FINAL_NORM", 211: "WEIGHT_LM_HEAD",
    212: "WEIGHT_QUERY_BIAS", 213: "WEIGHT_KEY_BIAS",
    214: "WEIGHT_VALUE_BIAS", 215: "WEIGHT_ATTN_OUTPUT_BIAS",
    216: "WEIGHT_MLP_GATE_BIAS", 217: "WEIGHT_MLP_UP_BIAS",
    218: "WEIGHT_MLP_DOWN_BIAS", 219: "WEIGHT_LM_HEAD_BIAS",
    220: "WEIGHT_ROPE_FREQUENCIES", 221: "WEIGHT_POSITION_EMBEDDING",
    250: "SEQUENCE_PLUS", 251: "DELTA_MINUS", 252: "REPEAT_TIMES",
    253: "UNPACK_DIVIDE", 254: "GROUP", 255: "REFERENCE",
}


@dataclass(frozen=True)
class Node:
    command: int
    name: str
    row: int
    column: int
    category: str
    kind: str
    color: str


def visual_assignment(command: int) -> tuple[str, str]:
    if 150 <= command <= 189:
        return "llm_execution", "#55e6a5"
    if command in {200, 221}:
        return "weight_embedding", "#4da3ff"
    if command in {201, 206, 210}:
        return "weight_norm", "#ffd166"
    if 202 <= command <= 205 or 212 <= command <= 215 or command == 220:
        return "weight_attention", "#b388ff"
    if 207 <= command <= 209 or 216 <= command <= 218:
        return "weight_mlp", "#ff9f43"
    if command in {211, 219}:
        return "weight_output", "#ff6384"
    if 250 <= command <= 255:
        return "glyphmath_operator", "#e8f06a"
    return "python_command", "#a6ffcb"


def category(command: int) -> str:
    bands = {
        0: "structure", 1: "module", 2: "assignment", 3: "function",
        4: "control", 5: "exception", 6: "container", 7: "arithmetic",
        8: "comparison", 9: "logic", 10: "literal", 11: "builtin",
        12: "io", 13: "conversion", 14: "advanced",
        25: "glyphmath",
    }
    return bands.get(command // 10, "reserved")


def node(command: int) -> Node:
    if not 0 <= command < COMMAND_LIMIT:
        raise ValueError(f"command must be in 000..332: {command}")
    kind, color = visual_assignment(command)
    return Node(
        command=command,
        name=COMMANDS.get(command, f"RESERVED_{command:03d}"),
        row=command // COLS,
        column=command % COLS,
        category=category(command),
        kind=kind,
        color=color,
    )


def grid() -> list[list[int | None]]:
    return [
        [r * COLS + c if r * COLS + c < COMMAND_LIMIT else None for c in range(COLS)]
        for r in range(ROWS)
    ]


def spatial_neighbors(command: int) -> list[int]:
    """Return orthogonal grid neighbors. These are navigation, not execution."""
    n = node(command)
    result = []
    for row, column in ((n.row - 1, n.column), (n.row + 1, n.column),
                        (n.row, n.column - 1), (n.row, n.column + 1)):
        candidate = row * COLS + column
        if 0 <= row < ROWS and 0 <= column < COLS and candidate < COMMAND_LIMIT:
            result.append(candidate)
    return result


def execution_edges(commands: Iterable[int]) -> list[dict[str, int | str]]:
    """Create directed edges for the exact supplied execution sequence."""
    sequence = list(commands)
    for command in sequence:
        node(command)
    return [
        {"step": step, "from": left, "to": right, "operator": "+"}
        for step, (left, right) in enumerate(zip(sequence, sequence[1:]))
    ]


def delta_encode(commands: Iterable[int]) -> list[int]:
    sequence = list(commands)
    if not sequence:
        return []
    for command in sequence:
        node(command)
    return [sequence[0], *(b - a for a, b in zip(sequence, sequence[1:]))]


def delta_decode(values: Iterable[int]) -> list[int]:
    values = list(values)
    if not values:
        return []
    result = [values[0]]
    for difference in values[1:]:
        result.append(result[-1] + difference)
        node(result[-1])
    return result


def run_length_encode(commands: Iterable[int]) -> list[dict[str, int]]:
    result: list[dict[str, int]] = []
    for command in commands:
        node(command)
        if result and result[-1]["command"] == command:
            result[-1]["times"] += 1
        else:
            result.append({"command": command, "times": 1})
    return result


def pack_pair(left: int, right: int) -> int:
    node(left)
    node(right)
    return left * PACK_BASE + right


def unpack_pair(packed: int) -> tuple[int, int]:
    left, right = divmod(packed, PACK_BASE)
    node(left)
    node(right)
    return left, right


def graph(sequence: list[int]) -> dict[str, object]:
    used = sorted(set(sequence))
    return {
        "version": 1,
        "grid": {"rows": ROWS, "columns": COLS, "commands": COMMAND_LIMIT},
        "nodes": [asdict(node(command)) for command in used],
        "execution_edges": execution_edges(sequence),
        "delta_minus": delta_encode(sequence),
        "repeat_times": run_length_encode(sequence),
        "packed_pairs": [pack_pair(a, b) for a, b in zip(sequence[::2], sequence[1::2])],
    }


def render_svg(sequence: list[int], cell_size: int = 48) -> str:
    """Render the command graph as a deterministic, self-describing SVG image."""
    payload = ",".join(str(value) for value in sequence)
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
    width, height = COLS * cell_size, ROWS * cell_size
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<metadata id="glyphmatics" version="1" base="333" sha256="{digest}">{payload}</metadata>',
        '<rect width="100%" height="100%" fill="#0b1020"/>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#58d6ff"/></marker></defs>',
    ]
    centers = {}
    for command in sorted(set(sequence)):
        value = node(command)
        centers[command] = ((value.column + 0.5) * cell_size,
                            (value.row + 0.5) * cell_size)
    for edge in execution_edges(sequence):
        x1, y1 = centers[int(edge["from"])]
        x2, y2 = centers[int(edge["to"])]
        if (x1, y1) == (x2, y2):
            parts.append(
                f'<circle cx="{x1}" cy="{y1}" r="{cell_size * .28}" fill="none" '
                'stroke="#58d6ff" stroke-width="2" marker-end="url(#arrow)"/>'
            )
        else:
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                'stroke="#58d6ff" stroke-width="2" marker-end="url(#arrow)"/>'
            )
    for command, (cx, cy) in centers.items():
        value = node(command)
        parts.extend([
            f'<rect x="{cx-cell_size*.42}" y="{cy-cell_size*.42}" '
            f'width="{cell_size*.84}" height="{cell_size*.84}" rx="6" '
            f'fill="#18213b" stroke="{value.color}" stroke-width="2"/>',
            f'<text x="{cx}" y="{cy+4}" text-anchor="middle" '
            f'font-family="monospace" font-size="12" fill="{value.color}">{command:03d}</text>',
            f'<title>{value.name}</title>',
        ])
    parts.append('</svg>')
    return "\n".join(parts)


def decode_svg(path: Path) -> list[int]:
    root = ElementTree.parse(path).getroot()
    metadata = root.find("{http://www.w3.org/2000/svg}metadata")
    if metadata is None or metadata.attrib.get("id") != "glyphmatics":
        raise ValueError("image has no Glyphmatics metadata")
    payload = metadata.text or ""
    actual = hashlib.sha256(payload.encode("ascii")).hexdigest()
    if actual != metadata.attrib.get("sha256"):
        raise ValueError("Glyphmatics image checksum mismatch")
    sequence = parse_sequence(payload)
    for command in sequence:
        node(command)
    return sequence


def parse_sequence(text: str) -> list[int]:
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("grid", help="print the 19x18 command grid")
    trace = sub.add_parser("trace", help="emit a directed execution graph")
    trace.add_argument("sequence", help="comma-separated command IDs")
    inspect = sub.add_parser("inspect", help="inspect one grid command")
    inspect.add_argument("command", type=int)
    render = sub.add_parser("render", help="render an execution graph SVG container")
    render.add_argument("sequence", help="comma-separated command IDs")
    render.add_argument("output", type=Path)
    decode = sub.add_parser("decode-svg", help="recover a sequence from an SVG container")
    decode.add_argument("image", type=Path)
    args = parser.parse_args()

    if args.action == "grid":
        for row in grid():
            print(" ".join("   " if value is None else f"{value:03d}" for value in row))
    elif args.action == "inspect":
        value = asdict(node(args.command))
        value["spatial_neighbors"] = spatial_neighbors(args.command)
        print(json.dumps(value, indent=2))
    elif args.action == "render":
        sequence = parse_sequence(args.sequence)
        args.output.write_text(render_svg(sequence), encoding="utf-8")
        print(args.output)
    elif args.action == "decode-svg":
        print(",".join(map(str, decode_svg(args.image))))
    else:
        print(json.dumps(graph(parse_sequence(args.sequence)), indent=2))


if __name__ == "__main__":
    main()
