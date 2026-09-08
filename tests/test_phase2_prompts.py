from phase2.prompts import SYSTEM_PROMPT, build_analysis_prompt


def test_prompt_places_input_in_user_content_only():
    prompt = build_analysis_prompt("resume text", "job text")
    assert "resume text" in prompt
    assert "job text" in prompt
    assert "只根据用户提供的内容" in SYSTEM_PROMPT
    assert "resume text" not in SYSTEM_PROMPT
