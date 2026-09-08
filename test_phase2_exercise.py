import pytest

from phase2_exercise import mock_model, parse_analysis


def test_mock_model_returns_valid_analysis():
    result = parse_analysis(mock_model("分析简历"))

    assert result.match_score == 0.78
    assert "Python" in result.matched_skills


@pytest.mark.parametrize(
    "raw",
    [
        # 1. 完全不是 JSON
        "not-json",

        # 2. 缺少 match_score
        (
            '{"candidate_summary":"Python 后端候选人",'
            '"matched_skills":["Python"],'
            '"missing_skills":["Docker"],'
            '"interview_questions":["如何设计异步 API？"]}'
        ),

        # 3. match_score 超过 1
        (
            '{"candidate_summary":"Python 后端候选人",'
            '"matched_skills":["Python"],'
            '"missing_skills":["Docker"],'
            '"match_score":1.2,'
            '"interview_questions":["如何设计异步 API？"]}'
        ),

        # 4. years_of_experience 小于 0
        (
            '{"candidate_summary":"Python 后端候选人",'
            '"matched_skills":["Python"],'
            '"missing_skills":["Docker"],'
            '"match_score":0.78,'
            '"years_of_experience":-1,'
            '"interview_questions":["如何设计异步 API？"]}'
        ),

        # 5. interview_questions 为空
        (
            '{"candidate_summary":"Python 后端候选人",'
            '"matched_skills":["Python"],'
            '"missing_skills":["Docker"],'
            '"match_score":0.78,'
            '"years_of_experience":2,'
            '"interview_questions":[]}'
        ),
    ],
)
def test_invalid_model_output_is_rejected(raw):
    with pytest.raises(ValueError):
        parse_analysis(raw)