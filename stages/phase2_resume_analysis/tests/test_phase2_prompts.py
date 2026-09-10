from stages.phase2_resume_analysis.app.prompts import SYSTEM_PROMPT, build_analysis_prompt


def test_prompt_places_input_in_user_content_only():
    prompt = build_analysis_prompt("resume text", "job text")
    assert "resume text" in prompt
    assert "job text" in prompt
    assert "只根据用户提供的内容" in SYSTEM_PROMPT
    assert "resume text" not in SYSTEM_PROMPT


def test_system_prompt_defines_complete_output_contract():
    required_fields = [
        "candidate_summary",
        "matched_skills",
        "missing_skills",
        "match_score",
        "years_of_experience",
        "interview_questions",
    ]
    for field in required_fields:
        assert field in SYSTEM_PROMPT
    assert "不要使用 assessment 字段" in SYSTEM_PROMPT


def test_system_prompt_contains_few_shot_example():
    assert "示例输入" in SYSTEM_PROMPT
    assert "示例输出" in SYSTEM_PROMPT
    assert '"candidate_summary"' in SYSTEM_PROMPT
