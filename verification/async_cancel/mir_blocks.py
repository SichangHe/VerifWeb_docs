"""Shared parser for the compiler's textual basic-block format."""

import re


def blocks(text: str) -> dict[str, list[str]] | str:
    """Read compiler-formatted blocks and reject duplicate or empty blocks."""
    result: dict[str, list[str]] = {}
    for match in re.finditer(
        r"^    (bb\d+)(?: \(cleanup\))?: \{\n(.*?)^    }",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        name, body = match.groups()
        if name in result:
            return "duplicate block"
        result[name] = [line.strip() for line in body.splitlines() if line.strip()]
        if not result[name]:
            return "empty block"
    return result if result else "no basic blocks"
