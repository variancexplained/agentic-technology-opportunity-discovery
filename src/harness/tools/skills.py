#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/harness/tools                                                               #
# Filename   : skills.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday July 1st 2026                                                             #
# Modified   : Wednesday July 1st 2026                                                             #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server exposing Sciven skills through progressive-disclosure tools.

Skills live under ``SKILL_FOLDER/<name>`` following the Claude Code layout: a ``SKILL.md`` main
file plus ``references/``, ``scripts/``, and ``examples/`` subdirectories. The :class:`Skills`
catalog encapsulates discovery, parsing, resolution, rendering, and execution; the module-level
``@mcp.tool`` functions are thin wrappers that delegate to it. Access is lazy: each call reads
only the files it needs, and file contents cross the boundary only when requested. The module
reuses the pure Sciven utilities (``fill_template``, ``read_markdown``, ``get_interpreter_prefix``)
and does not depend on the ``Skill`` class.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Annotated

import yaml
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.domain.core import EnumClass, Stage
from sciven.utils.interpreter import get_interpreter_prefix
from sciven.utils.markdown import read_markdown
from sciven.utils.templating import fill_template
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
load_dotenv()
logger = logging.getLogger(__name__)

# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #
SKILL_FOLDER = Path(os.getenv("SKILL_FOLDER", "sciven/ai/skills"))

_EXPECTED_ERRORS = (LookupError, FileNotFoundError, ValueError, RuntimeError)


# ------------------------------------------------------------------------------------------------ #
class SkillAsset(EnumClass):
    """Structural names within a skill directory.

    Attributes:
        SKILL_FILE: The main instruction file.
        REFERENCES: Subdirectory of reference (knowledge) files.
        SCRIPTS: Subdirectory of executable scripts.
        EXAMPLES: Subdirectory of example files.
    """

    SKILL_FILE = "SKILL.md"
    REFERENCES = "references"
    SCRIPTS = "scripts"
    EXAMPLES = "examples"


# ================================================================================================ #
#                                            SKILLS                                                #
# ================================================================================================ #
class Skills:
    """Catalog of file-authored skills rooted at a skills directory.

    Encapsulates skill discovery (names, skillcards), ``SKILL.md`` parsing, reference/example/
    script resolution, body rendering, manifests, and script execution. Instances are cheap and
    stateless beyond their root, so tools construct one per call; the root defaults to the module
    ``SKILL_FOLDER`` and can be overridden for testing.

    Attributes:
        SCRIPT_TIMEOUT_SECONDS: Wall-clock limit for a script run.
        MAX_SCRIPT_OUTPUT_CHARS: Cap on returned stdout characters.
        MAX_STDERR_CHARS: Cap on stderr characters included in error messages.
    """

    SCRIPT_TIMEOUT_SECONDS = 60
    MAX_SCRIPT_OUTPUT_CHARS = 20_000
    MAX_STDERR_CHARS = 2_000

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else SKILL_FOLDER

    # -------------------------------------------------------------------------------------------- #
    @property
    def skills_root(self) -> Path:
        """The root directory that holds all skill directories."""
        return self._root

    # -------------------------------------------------------------------------------------------- #
    @property
    def skill_names(self) -> list[str]:
        """Names of all skills (directories containing a ``SKILL.md``)."""
        if not self._root.is_dir():
            return []
        return sorted(
            path.name
            for path in self._root.iterdir()
            if path.is_dir() and (path / SkillAsset.SKILL_FILE.value).is_file()
        )

    # -------------------------------------------------------------------------------------------- #
    def skill_dir(self, skill_name: str) -> Path:
        """Resolves and validates a skill's directory, jailed under the skills root.

        Args:
            skill_name: The skill identity (its directory name).

        Returns:
            The absolute path to the skill directory.

        Raises:
            LookupError: If the name escapes the skills root or no such skill exists.
        """
        root = self._root.resolve()
        directory = (root / skill_name).resolve()
        if directory != root and root not in directory.parents:
            raise LookupError(f"Invalid skill name {skill_name!r}.")
        if not directory.is_dir() or not (directory / SkillAsset.SKILL_FILE.value).is_file():
            raise LookupError(
                f"Skill {skill_name!r} not found. Available skills: {self.skill_names}."
            )
        return directory

    # -------------------------------------------------------------------------------------------- #
    @staticmethod
    def split_frontmatter(content: str) -> tuple[dict, str]:
        """Splits a ``SKILL.md`` document into its YAML frontmatter and markdown body."""
        stripped = content.lstrip("﻿").lstrip()
        if stripped.startswith("---"):
            parts = stripped.split("---", 2)
            if len(parts) == 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                return frontmatter, parts[2].lstrip("\n")
        return {}, content

    # -------------------------------------------------------------------------------------------- #
    def read_skill_md(self, directory: Path) -> tuple[dict, str]:
        """Reads and parses the ``SKILL.md`` file in a skill directory."""
        return self.split_frontmatter(read_markdown(str(directory / SkillAsset.SKILL_FILE.value)))

    # -------------------------------------------------------------------------------------------- #
    @staticmethod
    def stems(directory: Path, subdir: SkillAsset) -> list[str]:
        """Returns the file stems (names without extension) in a skill subdirectory."""
        sub = directory / subdir.value
        if not sub.is_dir():
            return []
        return sorted(path.stem for path in sub.iterdir() if path.is_file())

    # -------------------------------------------------------------------------------------------- #
    @staticmethod
    def resolve_stem(directory: Path, subdir: SkillAsset, stem: str) -> Path:
        """Resolves a file by stem within a skill subdirectory.

        Raises:
            LookupError: If no file with that stem exists in the subdirectory.
        """
        sub = directory / subdir.value
        if sub.is_dir():
            for path in sorted(sub.iterdir()):
                if path.is_file() and path.stem == stem:
                    return path
        raise LookupError(
            f"No {stem!r} in {subdir.value} of skill {directory.name!r}. "
            f"Available: {Skills.stems(directory, subdir)}."
        )

    # -------------------------------------------------------------------------------------------- #
    def skillcards(self, stage: str | None = None) -> list[dict]:
        """Returns skillcards for every skill, optionally filtered by stage."""
        cards = []
        for name in self.skill_names:
            frontmatter, _ = self.read_skill_md(self.skill_dir(name))
            cards.append(
                {
                    "name": name,
                    "description": frontmatter.get("description", ""),
                    "when_to_use": frontmatter.get("when_to_use"),
                    "stage": frontmatter.get("stage"),
                    "agent_name": frontmatter.get("agent_name"),
                }
            )
        if stage is not None:
            cards = [card for card in cards if card.get("stage") == stage]
        return cards

    # -------------------------------------------------------------------------------------------- #
    def frontmatter(self, skill_name: str) -> dict:
        """Returns the full parsed frontmatter mapping for a skill."""
        frontmatter, _ = self.read_skill_md(self.skill_dir(skill_name))
        result = dict(frontmatter)
        result.setdefault("name", skill_name)
        return result

    # -------------------------------------------------------------------------------------------- #
    def render_body(self, skill_name: str, variables: dict | None) -> str:
        """Renders a skill body, requiring every declared argument.

        Raises:
            LookupError: If the skill does not exist.
            ValueError: If any declared required argument is missing.
        """
        directory = self.skill_dir(skill_name)
        frontmatter, raw_body = self.read_skill_md(directory)
        variables = variables or {}
        required = frontmatter.get("arguments") or []
        missing = [name for name in required if name not in variables]
        if missing:
            raise ValueError(
                f"Missing required variable(s) for skill {skill_name!r}: {missing}. "
                f"Declared arguments: {list(required)}."
            )
        return fill_template(raw_body, {"SKILL_DIR": str(directory), **variables})

    # -------------------------------------------------------------------------------------------- #
    def manifest(self, skill_name: str) -> dict:
        """Builds a structured file inventory (path, size, sha256) for a skill."""
        directory = self.skill_dir(skill_name)
        files = []
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name.startswith("."):
                continue
            data = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "size": len(data),
                    "hash": f"sha256:{hashlib.sha256(data).hexdigest()}",
                }
            )
        return {"skill": skill_name, "files": files}

    # -------------------------------------------------------------------------------------------- #
    def run_script(self, skill_name: str, script_name: str, variables: dict | None) -> dict:
        """Runs a bundled script as a subprocess and returns its captured stdout.

        Raises:
            LookupError: If the skill or script does not exist.
            RuntimeError: If the script times out or exits with a non-zero status.
        """
        directory = self.skill_dir(skill_name)
        path = self.resolve_stem(directory, SkillAsset.SCRIPTS, script_name)
        env = {**os.environ, "SKILL_DIR": str(directory)}
        env.update({key: str(value) for key, value in (variables or {}).items()})
        try:
            result = subprocess.run(
                [*get_interpreter_prefix(str(path)), str(path)],
                cwd=str(directory),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.SCRIPT_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Script {script_name!r} in skill {skill_name!r} timed out after "
                f"{self.SCRIPT_TIMEOUT_SECONDS}s."
            ) from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"Script {script_name!r} in skill {skill_name!r} exited with code "
                f"{result.returncode}: {result.stderr.strip()[: self.MAX_STDERR_CHARS]}"
            )
        stdout = result.stdout
        return {
            "skill_name": skill_name,
            "script_name": script_name,
            "exit_code": result.returncode,
            "stdout": stdout[: self.MAX_SCRIPT_OUTPUT_CHARS],
            "truncated": len(stdout) > self.MAX_SCRIPT_OUTPUT_CHARS,
        }


# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
mcp = FastMCP("sciven-skills")


# ================================================================================================ #
#                                        DISCOVERY TOOLS                                           #
# ------------------------------------------------------------------------------------------------ #
#                                        SKILL LIST TOOL                                           #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_list",
    description=(
        "Lists every available skill as a skillcard. "
        "Takes no arguments. "
        "Returns a list of skillcard dicts, one per skill, each carrying 'name' (the skill "
        "identity, used for every other skill_* tool), 'description', 'when_to_use', 'stage' "
        "(the pipeline stage the skill applies to, or null), and 'agent_name' (the agent the "
        "skill is scoped to, or null). "
        "This is the entry point to progressive disclosure: call it first to see what skills "
        "exist and which one fits the task, then use skill_frontmatter and skill_body to "
        "activate the chosen skill. Bodies, references, scripts, and examples are not returned "
        "here."
    ),
)
def skill_list() -> ToolResult:
    try:
        return tool_result_list(Skills().skillcards())
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                   SKILL LIST BY STAGE TOOL                                       #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_list_by_stage",
    description=(
        "Lists the skills applicable to a single pipeline stage as skillcards. "
        "Expects 'stage' as one of 'discovery', 'development', 'validation', or 'strategy'. "
        "Returns a list of skillcard dicts (same shape as skill_list) whose 'stage' matches; the "
        "list is empty when no skill is scoped to that stage. "
        "Use this instead of skill_list when you already know the current stage and want only the "
        "skills that can fire there, avoiding the token cost of the full catalog."
    ),
)
def skill_list_by_stage(
    stage: Annotated[
        str,
        Field(
            description=(
                "Pipeline stage to filter by. One of 'discovery', 'development', "
                "'validation', 'strategy'."
            ),
        ),
    ],
) -> ToolResult:
    try:
        Stage.from_value(stage)
        return tool_result_list(Skills().skillcards(stage=stage))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ================================================================================================ #
#                                       ACTIVATION TOOLS                                           #
# ================================================================================================ #
#                                    SKILL FRONTMATTER TOOL                                        #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_frontmatter",
    description=(
        "Returns the full frontmatter of a skill as a dict. "
        "Expects 'skill_name' (the identity from a skillcard). "
        "Returns the parsed frontmatter mapping, which typically includes 'name', 'description', "
        "'when_to_use', 'arguments' (the names of the variables skill_body requires), "
        "'allowed_tools', 'disallowed_tools', 'model', 'effort', 'stage', and 'agent_name'. "
        "Fields not present in the skill's frontmatter are omitted. "
        "Use this before skill_body to learn which variables the skill requires and which tools "
        "it permits while active."
    ),
)
def skill_frontmatter(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
) -> ToolResult:
    try:
        return tool_result_single(Skills().frontmatter(skill_name))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                       SKILL BODY TOOL                                            #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_body",
    description=(
        "Activates a skill and returns its rendered instruction body (frontmatter stripped). "
        "Expects 'skill_name' and optional 'variables', a dict of values for the skill's declared "
        "arguments (see the 'arguments' field from skill_frontmatter). Every declared argument is "
        "required and must appear in 'variables'; a missing one raises an error naming it. "
        "'${SKILL_DIR}' is supplied automatically. All '${NAME}' placeholders in the body are "
        "replaced from the merged values. "
        "Returns {'skill_name': <str>, 'body': <rendered markdown>}. "
        "This is a single-call activation: pass all required variables at once. Use it after "
        "choosing a skill to obtain the procedure the agent should follow."
    ),
)
def skill_body(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
    variables: Annotated[
        dict | None,
        Field(
            description=(
                "Values for the skill's declared arguments, e.g. {'RUN_ID': 'run-1', "
                "'QUERY': '...'}. Every name in the skill's 'arguments' frontmatter must be "
                "present. Optional only when the skill declares no arguments."
            ),
        ),
    ] = None,
) -> ToolResult:
    try:
        body = Skills().render_body(skill_name, variables)
        return tool_result_single({"skill_name": skill_name, "body": body})
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ================================================================================================ #
#                                      INSPECTION TOOLS                                            #
# ================================================================================================ #
#                                     SKILL MANIFEST TOOL                                          #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_manifest",
    description=(
        "Returns a structured file inventory for a skill. "
        "Expects 'skill_name'. "
        "Returns {'skill': <name>, 'files': [{'path': <relative path>, 'size': <bytes>, "
        "'hash': 'sha256:<hex>'}, ...]} covering SKILL.md and every file under references/, "
        "scripts/, and examples/ (hidden files and __pycache__ excluded). "
        "Use this to discover exactly which supporting files a skill bundles and to detect "
        "changes via the content hashes; use skill_reference, skill_example, or skill_run_script "
        "to actually read or run a listed file."
    ),
)
def skill_manifest(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
) -> ToolResult:
    try:
        return tool_result_single(Skills().manifest(skill_name))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                     SKILL REFERENCE TOOL                                         #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_reference",
    description=(
        "Reads a named reference file from a skill's references/ subdirectory. "
        "Expects 'skill_name' and 'reference_name' (the file stem, without the .md extension). "
        "Returns {'skill_name': <str>, 'reference_name': <str>, 'content': <file text>}. Raises "
        "an error listing the available reference names if the name is not found. "
        "Use this to load detailed guidance (rubrics, schemas, checklists) that the skill body "
        "points to, only when the body directs you to it."
    ),
)
def skill_reference(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
    reference_name: Annotated[
        str,
        Field(description="The reference file stem (filename without the .md extension)."),
    ],
) -> ToolResult:
    try:
        skills = Skills()
        path = skills.resolve_stem(
            skills.skill_dir(skill_name), SkillAsset.REFERENCES, reference_name
        )
        return tool_result_single(
            {
                "skill_name": skill_name,
                "reference_name": reference_name,
                "content": read_markdown(str(path)),
            }
        )
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                   SKILL LIST EXAMPLES TOOL                                       #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_list_examples",
    description=(
        "Lists the example files bundled with a skill. "
        "Expects 'skill_name'. "
        "Returns a list of example file stems (filenames without extension) from the skill's "
        "examples/ subdirectory; the list is empty when the skill bundles no examples. "
        "Use this to discover which examples exist before reading one with skill_example."
    ),
)
def skill_list_examples(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
) -> ToolResult:
    try:
        skills = Skills()
        return tool_result_list(skills.stems(skills.skill_dir(skill_name), SkillAsset.EXAMPLES))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                      SKILL EXAMPLE TOOL                                          #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_example",
    description=(
        "Reads a named example file from a skill's examples/ subdirectory. "
        "Expects 'skill_name' and 'example_name' (the file stem, without extension). "
        "Returns {'skill_name': <str>, 'example_name': <str>, 'content': <file text>}. Raises an "
        "error listing available example names if the name is not found, or if the example is a "
        "non-text (binary) file that cannot be returned as text. "
        "Use this to load a concrete worked example the skill body refers to."
    ),
)
def skill_example(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
    example_name: Annotated[
        str,
        Field(description="The example file stem (filename without extension)."),
    ],
) -> ToolResult:
    try:
        skills = Skills()
        path = skills.resolve_stem(skills.skill_dir(skill_name), SkillAsset.EXAMPLES, example_name)
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Example {example_name!r} in skill {skill_name!r} is not UTF-8 text "
                f"(file: {path.name}) and cannot be returned as text."
            ) from exc
        return tool_result_single(
            {"skill_name": skill_name, "example_name": example_name, "content": content}
        )
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ================================================================================================ #
#                                        SCRIPT TOOLS                                              #
# ================================================================================================ #
#                                    SKILL SCRIPT LIST TOOL                                        #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_script_list",
    description=(
        "Lists the scripts bundled with a skill. "
        "Expects 'skill_name'. "
        "Returns a list of script file stems (filenames without extension) from the skill's "
        "scripts/ subdirectory; the list is empty when the skill bundles no scripts. "
        "Use this to discover which scripts exist before running one with skill_run_script. "
        "Script source is not returned; scripts are meant to be executed, not read."
    ),
)
def skill_script_list(
    skill_name: Annotated[
        str,
        Field(description="The skill identity (its directory name), from a skillcard."),
    ],
) -> ToolResult:
    try:
        skills = Skills()
        return tool_result_list(skills.stems(skills.skill_dir(skill_name), SkillAsset.SCRIPTS))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    SKILL RUN SCRIPT TOOL                                         #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="skill_run_script",
    description=(
        "Runs a bundled script and returns its standard output. "
        "Expects 'skill_name', 'script_name' (the script's file stem, without extension), and "
        "optional 'variables', a dict exported to the script as environment variables. The "
        "interpreter is chosen from the file extension (.py, .sh/.bash); 'SKILL_DIR' is exported "
        "automatically and the script runs with the skill directory as its working directory. "
        "Returns {'skill_name', 'script_name', 'exit_code', 'stdout', 'truncated'}; 'stdout' is "
        "truncated to a token-safe limit and 'truncated' flags when that happened. Raises an "
        "error if the script is not found, exits non-zero (message includes stderr), or times "
        "out. "
        "Use this to execute a skill's deterministic step (e.g. persisting or transforming data) "
        "rather than reproducing its logic yourself."
    ),
)
def skill_run_script(
    skill_name: Annotated[
        str,
        Field(description="The skill that owns the script (its directory name)."),
    ],
    script_name: Annotated[
        str,
        Field(description="The script file stem (filename without extension)."),
    ],
    variables: Annotated[
        dict | None,
        Field(
            description=(
                "Values exported to the script as environment variables, e.g. "
                "{'RUN_ID': 'run-1'}. Optional."
            ),
        ),
    ] = None,
) -> ToolResult:
    try:
        return tool_result_single(Skills().run_script(skill_name, script_name, variables))
    except _EXPECTED_ERRORS as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
if __name__ == "__main__":
    logging.getLogger().setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    mcp.run()
