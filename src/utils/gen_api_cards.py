#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : docs.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Thursday June 4th 2026 12:56:08 am                                                  #
# Modified   : Thursday June 4th 2026 01:23:49 am                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
r"""Generate Markdown API cards from Python classes for use as skill references.

Imports each target by dotted path, reads its live signatures with ``inspect``,
parses its Google-style docstrings, and writes one Markdown card per class to an
output directory. A target may be a single class (``pkg.mod.MyClass``) or a whole
module (``pkg.mod``), in which case every public class *defined in* that module is
documented. The signature is the source of truth for the parameter list and types;
the docstring supplies prose. Parameters documented but absent from the signature
are reported as staleness warnings on stderr, which is half the point of generating
rather than hand-writing the cards.

Usage:
    python -m sciven.utils.gen_api_cards --out docs/api --tree \\
        sciven.domain.reflection \\
        sciven.adapters.arxiv.search.ArxivSearchRequestBuilder

Run it in the environment where the targets import (e.g. the ``sciven`` conda
env), since import-based introspection loads the class and its deps.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import Any

# Sections recognized in a Google-style docstring. Anything before the first is
# the summary/description.
_SECTION_HEADERS = (
    "Args",
    "Arguments",
    "Returns",
    "Yields",
    "Raises",
    "Attributes",
    "Example",
    "Examples",
    "Note",
    "Notes",
)
_SECTION_RE = re.compile(rf"^({'|'.join(_SECTION_HEADERS)}):\s*$")
# An Args entry: "name (type): description" or "name: description".
_ARG_RE = re.compile(r"^(?P<name>\*{0,2}\w+)\s*(?:\((?P<type>.+?)\))?\s*:\s*(?P<desc>.*)$")


# ------------------------------------------------------------------------------------------------ #
def kebab(name: str) -> str:
    """Converts a CamelCase class name to a kebab-case filename stem."""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return s.lower()


# ------------------------------------------------------------------------------------------------ #
def parse_google_docstring(doc: str | None) -> dict[str, Any]:
    """Splits a Google-style docstring into summary, description, and sections.

    Args:
        doc: The raw docstring, already dedented by ``inspect.getdoc``.

    Returns:
        A dict with keys 'summary', 'description', 'args' (name -> (type, desc)),
        'returns', 'raises', 'attributes', and 'examples'.
    """
    result: dict[str, Any] = {
        "summary": "",
        "description": "",
        "args": {},
        "returns": "",
        "raises": [],
        "attributes": {},
        "examples": "",
    }
    if not doc:
        return result

    lines = doc.splitlines()
    section: str | None = None
    preamble: list[str] = []
    buckets: dict[str, list[str]] = {}

    for line in lines:
        header = _SECTION_RE.match(line.strip())
        if header:
            section = header.group(1)
            buckets.setdefault(section, [])
            continue
        if section is None:
            preamble.append(line)
        else:
            buckets[section].append(line)

    preamble_text = "\n".join(preamble).strip()
    if preamble_text:
        parts = preamble_text.split("\n\n", 1)
        result["summary"] = parts[0].strip().replace("\n", " ")
        result["description"] = parts[1].strip() if len(parts) > 1 else ""

    # Args / Attributes: parse entries with indented continuation lines.
    for key, target in (("Args", "args"), ("Arguments", "args"), ("Attributes", "attributes")):
        for name, typ, desc in _parse_entries(buckets.get(key, [])):
            result[target][name] = (typ, desc)

    for key in ("Returns", "Yields"):
        if buckets.get(key):
            result["returns"] = _join_block(buckets[key])

    if buckets.get("Raises"):
        for name, _typ, desc in _parse_entries(buckets["Raises"]):
            result["raises"].append((name, desc))

    for key in ("Example", "Examples"):
        if buckets.get(key):
            result["examples"] = _format_example_block(buckets[key])

    return result


def _parse_entries(block: list[str]) -> list[tuple[str, str | None, str]]:
    """Parses an Args/Raises block into (name, type, description) tuples."""
    entries: list[tuple[str, str | None, str]] = []
    current: list[str] | None = None
    name = typ = None
    for raw in block:
        stripped = raw.strip()
        if not stripped:
            continue
        match = _ARG_RE.match(stripped)
        # A new entry starts when the line matches and is at the block's base indent.
        base_indent = len(raw) - len(raw.lstrip())
        if match and base_indent <= _min_indent(block):
            if name is not None:
                entries.append((name, typ, " ".join(current or []).strip()))
            name = match.group("name")
            typ = match.group("type")
            current = [match.group("desc")]
        elif current is not None:
            current.append(stripped)
    if name is not None:
        entries.append((name, typ, " ".join(current or []).strip()))
    return entries


def _min_indent(block: list[str]) -> int:
    """Returns the smallest leading-space count among non-empty lines."""
    indents = [len(line) - len(line.lstrip()) for line in block if line.strip()]
    return min(indents) if indents else 0


def _join_block(block: list[str]) -> str:
    """Joins a section block into a single trimmed paragraph."""
    return " ".join(line.strip() for line in block if line.strip())


def _format_example_block(block: list[str]) -> str:
    """Dedents an Example/Examples block while preserving line breaks.

    Unlike ``_join_block``, this keeps newlines and interior blank lines so that
    doctest-style examples (``>>>`` prompts and their expected output) render as a
    faithful code block instead of collapsing onto a single line.

    Args:
        block: The raw lines captured under an ``Example``/``Examples`` header,
            still carrying their docstring indentation.

    Returns:
        The block with surrounding blank lines trimmed and the common leading
        indentation removed, lines rejoined with newlines.
    """
    lines = list(block)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    return "\n".join(line[indent:] if line.strip() else "" for line in lines)


# ------------------------------------------------------------------------------------------------ #
def fmt_annotation(annotation: Any) -> str | None:
    """Renders a parameter or return annotation as a readable string."""
    if annotation is inspect.Parameter.empty or annotation is inspect.Signature.empty:
        return None
    if isinstance(annotation, str):  # postponed (from __future__ import annotations)
        return annotation
    name = getattr(annotation, "__name__", None)
    return name or str(annotation).replace("typing.", "")


class _Factory:
    """Sentinel default rendered as ``<factory>`` for ``default_factory`` fields.

    Plain dataclasses expose ``<factory>`` through their generated ``__init__``;
    this reproduces that marker when the signature is rebuilt from fields. It is
    deliberately not callable so :func:`fmt_default` falls through to its ``repr``.
    """

    def __repr__(self) -> str:
        return "<factory>"


_FACTORY = _Factory()


def fmt_default(default: Any) -> str | None:
    """Renders a parameter default as a readable string."""
    if default is inspect.Parameter.empty:
        return None
    if callable(default):
        return getattr(default, "__name__", repr(default))
    return repr(default)


def signature_from_fields(cls: type) -> inspect.Signature:
    """Builds a constructor signature from a dataclass's fields.

    Pydantic dataclasses replace the generated ``__init__`` with an opaque
    ``(*args, **kwargs)``, so ``inspect.signature`` can't see the real parameters.
    ``dataclasses.fields`` exposes the canonical field list (with inherited fields,
    in order) for both plain and pydantic dataclasses, so it is the reliable source
    of truth. Fields are rendered keyword-only to sidestep default-ordering rules.
    """
    params = []
    for f in dataclasses.fields(cls):
        if not f.init:
            continue
        if f.default is not dataclasses.MISSING:
            default = f.default
        elif f.default_factory is not dataclasses.MISSING:
            default = _FACTORY
        else:
            default = inspect.Parameter.empty
        params.append(
            inspect.Parameter(
                f.name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=f.type
            )
        )
    return inspect.Signature(params, return_annotation=None)


def constructor_signature(cls: type) -> inspect.Signature:
    """Returns the constructor signature, robust to pydantic dataclasses.

    Falls back to the field-derived signature only when ``cls`` is a dataclass
    whose ``__init__`` exposes no real named parameters (the pydantic-dataclass
    case); plain dataclasses and ordinary classes keep their introspected
    signature unchanged.
    """
    sig = inspect.signature(cls.__init__)
    named = [
        p
        for p in sig.parameters.values()
        if p.name not in ("self", "cls", "__dataclass_self__")
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    if dataclasses.is_dataclass(cls) and not named:
        return signature_from_fields(cls)
    return sig


def defining_class(cls: type, name: str) -> str | None:
    """Returns the name of the class in the MRO that defines ``name``, if inherited."""
    for base in cls.__mro__:
        if name in vars(base):
            return None if base is cls else base.__name__
    return None


def inherited_attributes(cls: type) -> dict[str, tuple[str | None, str]]:
    """Collects ``Attributes:`` docstring entries across the MRO.

    For a dataclass the inherited fields become constructor parameters, so a
    subclass card should describe them using the base classes' docstrings. Bases
    are walked first and the subclass last, so a more-derived class's
    documentation overrides a base's for the same attribute name.
    """
    merged: dict[str, tuple[str | None, str]] = {}
    for base in reversed(cls.__mro__):
        if base is object:
            continue
        merged.update(parse_google_docstring(inspect.getdoc(base))["attributes"])
    return merged


# ------------------------------------------------------------------------------------------------ #
def render_params(
    sig: inspect.Signature, doc_args: dict[str, tuple[str | None, str]], owner: str
) -> tuple[list[str], list[str]]:
    """Renders the parameter rows for a signature; signature drives the list.

    Returns the rendered lines and any staleness warnings (params documented but
    not present in the signature).
    """
    lines: list[str] = []
    sig_names: set[str] = set()
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        sig_names.add(pname)
        typ = fmt_annotation(param.annotation)
        doc_typ, doc_desc = doc_args.get(pname, (None, ""))
        shown_type = typ or doc_typ or "Any"
        default = fmt_default(param.default)
        prefix = f"`{pname}` (`{shown_type}`"
        prefix += f", default `{default}`)" if default is not None else ")"
        desc = doc_desc.strip() or "_undocumented_"
        lines.append(f"- {prefix}: {desc}")

    warnings = [
        f"{owner}: documented param '{d}' is absent from the signature (stale docstring?)"
        for d in doc_args
        if d not in sig_names
    ]
    return lines, warnings


def render_callable(cls: type, name: str) -> tuple[str, list[str]] | None:
    """Renders one public method/classmethod/staticmethod/property card section."""
    static = inspect.getattr_static(cls, name, None)
    origin = defining_class(cls, name)
    origin_tag = f" _(inherited from `{origin}`)_" if origin else ""

    if isinstance(static, property):
        if static.fget is None:
            return None
        doc = parse_google_docstring(inspect.getdoc(static.fget))
        ret = fmt_annotation(inspect.signature(static.fget).return_annotation)
        ret_tag = f" -> `{ret}`" if ret else ""
        body = f"- `{name}`{ret_tag} _(property)_{origin_tag}: {doc['summary'] or '_undocumented_'}"
        return body, []

    if isinstance(static, staticmethod):
        func, kind = static.__func__, "staticmethod"
    elif isinstance(static, classmethod):
        func, kind = static.__func__, "classmethod"
    elif inspect.isfunction(static):
        func, kind = static, "method"
    else:
        return None

    sig = inspect.signature(func)
    doc = parse_google_docstring(inspect.getdoc(func))
    rendered_sig = _render_signature(name, sig)
    kind_tag = "" if kind == "method" else f" _({kind})_"
    header = f"#### `{rendered_sig}`{kind_tag}{origin_tag}"
    body_lines = [header, "", doc["summary"] or "_undocumented_"]

    param_lines, warnings = render_params(sig, doc["args"], f"{cls.__name__}.{name}")
    real_params = [p for p in sig.parameters if p not in ("self", "cls")]
    if real_params:
        body_lines += ["", "**Parameters**", *param_lines]
    if doc["returns"]:
        body_lines += ["", f"**Returns:** {doc['returns']}"]
    if doc["raises"]:
        body_lines += ["", "**Raises**"]
        body_lines += [f"- `{n}`: {d}" for n, d in doc["raises"]]
    if doc["examples"]:
        body_lines += ["", "**Example**", "", "```python", doc["examples"], "```"]
    return "\n".join(body_lines), warnings


def _render_signature(name: str, sig: inspect.Signature) -> str:
    """Renders a compact call signature string for a method header."""
    parts: list[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        typ = fmt_annotation(param.annotation)
        piece = pname + (f": {typ}" if typ else "")
        default = fmt_default(param.default)
        if default is not None:
            piece += f" = {default}"
        parts.append(piece)
    ret = fmt_annotation(sig.return_annotation)
    ret_str = f" -> {ret}" if ret else ""
    return f"{name}({', '.join(parts)}){ret_str}"


# ------------------------------------------------------------------------------------------------ #
def render_members(cls: type, class_doc: dict[str, Any]) -> list[str]:
    """Renders the ``Members`` section for an Enum subclass.

    The live enum is the source of truth for the member list and values; the
    docstring's ``Attributes:`` section supplies each member's prose. Rendering
    members instead of a constructor is what keeps documented members from being
    mistaken for stale ``__init__`` parameters.
    """
    docs = class_doc["attributes"]
    lines = ["## Members", ""]
    for member in cls:
        desc = docs.get(member.name, (None, ""))[1].strip()
        suffix = f": {desc}" if desc else ""
        lines.append(f"- `{member.name}` = `{member.value!r}`{suffix}")
    return [*lines, ""]


def build_card(cls: type) -> tuple[str, list[str]]:
    """Builds the full Markdown card for a class. Returns (markdown, warnings)."""
    warnings: list[str] = []
    class_doc = parse_google_docstring(inspect.getdoc(cls))

    out = [f"# `{cls.__name__}`", "", f"`{cls.__module__}.{cls.__name__}`", ""]
    if class_doc["summary"]:
        out += [class_doc["summary"], ""]
    if class_doc["description"]:
        out += [class_doc["description"], ""]

    if issubclass(cls, enum.Enum):
        # Enums document their members under Attributes; render those instead of a
        # constructor so members are not flagged as stale __init__ parameters.
        out += render_members(cls, class_doc)
    else:
        # Constructor: merge inherited Attributes, then class-docstring Args, then
        # __init__-docstring Args, so the most specific documentation wins.
        try:
            init_sig = constructor_signature(cls)
            init_doc = parse_google_docstring(inspect.getdoc(cls.__init__))
            ctor_args = {**inherited_attributes(cls), **class_doc["args"], **init_doc["args"]}
            if init_doc["summary"] == inspect.getdoc(object.__init__):
                init_doc["args"] = {}
            rendered = _render_signature(cls.__name__, init_sig)
            out += ["## Constructor", "", f"`{rendered}`", ""]
            param_lines, ctor_warnings = render_params(
                init_sig, ctor_args, f"{cls.__name__}.__init__"
            )
            warnings += ctor_warnings
            real = [p for p in init_sig.parameters if p not in ("self", "cls")]
            if real:
                out += ["**Parameters**", *param_lines, ""]
        except (ValueError, TypeError):
            pass

    # Public methods, classmethods, staticmethods, properties.
    method_sections: list[str] = []
    properties: list[str] = []
    # Union the MRO's namespaces rather than trusting dir(): EnumMeta overrides
    # __dir__ and hides inherited mixin methods (e.g. a base EnumClass.from_value).
    names = set(dir(cls)).union(*(vars(base) for base in cls.__mro__))
    for name in sorted(names):
        if name.startswith("_"):
            continue
        rendered = render_callable(cls, name)
        if rendered is None:
            continue
        body, warns = rendered
        warnings += warns
        (properties if body.lstrip().startswith("- ") else method_sections).append(body)

    if properties:
        out += ["## Properties", "", *properties, ""]
    if method_sections:
        out += ["## Methods", "", *("\n".join([s, ""]) for s in method_sections)]

    if class_doc["examples"]:
        out += ["## Example", "", "```python", class_doc["examples"], "```", ""]

    if warnings:
        out += ["<!-- staleness warnings:", *(f"  - {w}" for w in warnings), "-->", ""]

    return "\n".join(out).rstrip() + "\n", warnings


# ------------------------------------------------------------------------------------------------ #
def import_class(dotted: str) -> type:
    """Imports a class from a fully-qualified dotted path."""
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(f"'{dotted}' is not a dotted path to a class.")
    module = importlib.import_module(module_path)
    obj = getattr(module, class_name)
    if not inspect.isclass(obj):
        raise TypeError(f"'{dotted}' resolved to {type(obj).__name__}, not a class.")
    return obj


def classes_in_module(module: Any) -> list[type]:
    """Returns the public classes *defined in* a module, in declaration order.

    Classes merely imported into the module are excluded by comparing
    ``__module__``, so each class is documented once, in its defining module.
    """
    return [
        obj
        for name, obj in vars(module).items()
        if not name.startswith("_")
        and inspect.isclass(obj)
        and obj.__module__ == module.__name__
    ]


def resolve_targets(dotted: str) -> list[type]:
    """Resolves a dotted path to the classes to document.

    Accepts either a module path (``sciven.domain.reflection``), expanding to the
    public classes defined in it, or a single class path
    (``sciven.domain.reflection.Reflection``). Mirrors the module-or-object
    addressing of the tool-card generator's ``resolve_server``.
    """
    try:
        module = importlib.import_module(dotted)
    except ImportError:
        return [import_class(dotted)]
    return classes_in_module(module)


def card_path(cls: type, out_dir: Path, tree: bool) -> Path:
    """Computes the output path for a class's card.

    With ``tree``, mirrors the module under ``out_dir`` and drops the top-level
    package, so ``sciven.domain.services.search.QuerySimilarity`` becomes
    ``<out>/domain/services/search/query-similarity.md``. Otherwise the card
    is written flat as ``<out>/query-similarity.md``.
    """
    filename = f"{kebab(cls.__name__)}.md"
    if not tree:
        return out_dir / filename
    parts = cls.__module__.split(".")[1:]  # drop the top-level package
    return out_dir.joinpath(*parts, filename)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate Markdown API cards from classes.")
    parser.add_argument(
        "targets",
        nargs="+",
        help="Dotted paths to classes or modules (a module documents all its public classes).",
    )
    parser.add_argument("--out", required=True, help="Output directory for cards.")
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Mirror each class's module path under --out (drops the top-level package).",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out)

    exit_code = 0
    for dotted in args.targets:
        try:
            classes = resolve_targets(dotted)
        except (ImportError, AttributeError, ValueError, TypeError) as exc:
            print(f"ERROR: {dotted}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        if not classes:
            print(f"  note: {dotted} defines no public classes", file=sys.stderr)
            continue
        for cls in classes:
            card, warnings = build_card(cls)
            path = card_path(cls, out_dir, args.tree)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(card, encoding="utf-8")
            print(f"wrote {path}")
            for warning in warnings:
                print(f"  WARN {warning}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
