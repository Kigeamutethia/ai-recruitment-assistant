from app.services.scoring import compute_score

CRITERIA = [
    {"key": "python", "label": "Python", "weight": 3, "must_have": True},
    {"key": "sql", "label": "SQL", "weight": 1, "must_have": False},
]


def test_weighted_score():
    r = compute_score(CRITERIA, [{"key": "python", "score": 5}, {"key": "sql", "score": 0}])
    assert r.overall == 75.0  # (3*5 + 1*0) / (4*5)
    assert r.must_have_met is True


def test_must_have_flag_when_below_threshold():
    r = compute_score(CRITERIA, [{"key": "python", "score": 2}, {"key": "sql", "score": 5}])
    assert r.must_have_met is False


def test_missing_criterion_scores_zero_and_is_marked():
    r = compute_score(CRITERIA, [{"key": "python", "score": 4}])
    sql = next(c for c in r.criteria if c["key"] == "sql")
    assert sql["score"] == 0 and sql["assessed"] is False


def test_scores_are_clamped():
    r = compute_score(CRITERIA, [{"key": "python", "score": 9}, {"key": "sql", "score": -3}])
    assert [c["score"] for c in r.criteria] == [5, 0]


def test_reweighting_changes_ranking():
    a = [{"key": "python", "score": 5}, {"key": "sql", "score": 1}]
    b = [{"key": "python", "score": 2}, {"key": "sql", "score": 5}]
    assert compute_score(CRITERIA, a).overall > compute_score(CRITERIA, b).overall
    sql_heavy = [{**CRITERIA[0], "weight": 1}, {**CRITERIA[1], "weight": 5}]
    assert compute_score(sql_heavy, a).overall < compute_score(sql_heavy, b).overall


def test_no_criteria():
    assert compute_score([], []).overall == 0.0
