from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from scrapers.service.llm.json_response import strip_code_fence
from scrapers.service.llm.skill import ExtractedSkill, parse_skills

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "skills_extraction.txt"


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
        payload = json.loads(strip_code_fence(response))
        return parse_skills(payload.get("skills", []))
