from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ALLOWED_SKILL_TYPES = frozenset(
    {"tool", "programming_language", "framework", "domain_concept", "certification"}
)
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "skills_extraction.txt"


@dataclass(frozen=True)
class ExtractedSkill:
    name: str
    skill_type: str


class SkillsExtractor:
    """Extract skills through an injected LLM call without classifying AV jobs."""

    def __init__(self, complete: Callable[[str], str]) -> None:
        self.complete = complete

    def extract(self, title: str, description: str) -> tuple[ExtractedSkill, ...]:
        response = self.complete(self.build_prompt(title, description))
        return self.parse_response(response)

    @staticmethod
    def build_prompt(title: str, description: str) -> str:
        template = PROMPT_PATH.read_text(encoding="utf-8")
        return template.replace("{{job_title}}", title).replace(
            "{{job_description}}", description
        )

    @staticmethod
    def parse_response(response: str) -> tuple[ExtractedSkill, ...]:
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
        payload = json.loads(text)
        skills = payload.get("skills", [])
        if not isinstance(skills, list):
            raise ValueError("LLM response field 'skills' must be a list")

        extracted: list[ExtractedSkill] = []
        seen: set[str] = set()
        for item in skills:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            skill_type = str(item.get("skill_type") or "").strip().casefold()
            normalized_name = name.casefold()
            if not name or skill_type not in ALLOWED_SKILL_TYPES or normalized_name in seen:
                continue
            extracted.append(ExtractedSkill(name=name, skill_type=skill_type))
            seen.add(normalized_name)
        return tuple(extracted)
