import pytest

from phase2_exercise import mock_model, parse_analysis


def test_mock_model_returns_valid_analysis():
    result = parse_analysis(mock_model("分析简历"))
    assert result.match_score == 0.78
    assert "Python" in result.matched_skills


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        '{"candidate_summary":"x","matched_skills":[],"missing_skills":[],"interview_questions":["q"]}',
        '{"candidate_summary":"x","matched_skills":[],"missing_skills":[],"match_score":1.2,"interview_questions":["q"]}',
    ],
)
def test_invalid_model_output_is_rejected(raw):
    with pytest.raises(ValueError):
        parse_analysis(raw)
