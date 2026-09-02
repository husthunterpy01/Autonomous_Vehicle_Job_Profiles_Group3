import json

from scrapers.service.silver_cleaning.skills_extractor import ExtractedSkill, SkillsExtractor


def test_extractor_requests_skills_without_av_classification():
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        return json.dumps(
            {
                "skills": [
                    {"name": "Python", "skill_type": "programming_language"},
                    {"name": "ROS", "skill_type": "framework"},
                ]
            }
        )

    skills = SkillsExtractor(complete).extract("Engineer", "Python and ROS are required.")

    assert skills == (
        ExtractedSkill("Python", "programming_language"),
        ExtractedSkill("ROS", "framework"),
    )
    assert "do not assign an AV category" in prompts[0]


def test_parser_deduplicates_names_and_discards_invalid_types():
    response = """```json
{"skills":[
  {"name":"Python","skill_type":"programming_language"},
  {"name":"python","skill_type":"tool"},
  {"name":"Teamwork","skill_type":"soft_skill"}
]}
```"""

    assert SkillsExtractor.parse_response(response) == (
        ExtractedSkill("Python", "programming_language"),
    )
