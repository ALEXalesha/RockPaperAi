"""Паспорт ИИ: все проверки на месте, заявленная сила, и первые матчи пересчитываются с
теми же зёрнами раунд в раунд."""
import json
import os

import pytest

from game.ai.arena import run
from game.train.passport import PATH, checks, chi2_sf, hindsight_edge

REPLAY = 1


@pytest.fixture(scope="module")
def passport():
    if not os.path.exists(PATH):
        pytest.skip("паспорт ещё не посчитан")
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)


def find(pp, k, level, bot):
    return next(c for c in pp["checks"] if c["k"] == k and c["level"] == level and c["bot"] == bot)


def test_every_check_present(passport):
    for k, level, bot, seed in checks():
        c = find(passport, k, level, bot)
        assert c["seed"] == seed and c["matches"] == passport["matches_per_check"]
        assert len(c["sample"]) >= REPLAY and len(c["sample"][0]) == passport["rounds_per_match"]
    assert passport["fairness"] and passport["seconds"] > 0


def test_strength_claims(passport):
    """Сильный после 30-го раунда выигрывает больше 70 % против повторяющего, цикла,
    «выиграл - остался, проиграл - сменил» и Маркова 2 (на пяти знаках у Маркова 2 - 25
    контекстов, за 100 раундов их не выучить так же: там больше 65 %); против случайного -
    поровну; зеркало не уводит его ниже равенства."""
    for k in (3, 5):
        for bot in ("repeat", "cycle", "wsls", "markov2"):
            need = 0.65 if (k, bot) == (5, "markov2") else 0.7
            assert find(passport, k, "strong", bot)["after30"]["win"] > need, (k, bot)
        r = find(passport, k, "strong", "random")["all"]
        even = (k - 1) / 2 / k
        assert abs(r["win"] - even) < 0.03 and abs(r["loss"] - even) < 0.03
        m = find(passport, k, "strong", "mirror")["all"]
        assert m["win"] >= m["loss"]
        for bot in ("biased", "human"):
            s = find(passport, k, "strong", bot)["all"]
            assert s["win"] > s["loss"], (k, bot)


def test_fairness_against_random(passport):
    """Против случайного - поровну. Даже знай человек задним числом все таблицы ходов ИИ
    (порядка 0-2), он выигрывал бы за раунд не больше чем на 3 % больше, чем против
    честного генератора той же длины."""
    for f in passport["fairness"]:
        k = f["k"]
        assert abs(f["win"] - (k - 1) / 2 / k) < 0.02
        assert f["p_moves"] > 0.001
        for o, edge in f["hindsight_edge"].items():
            assert edge - f["hindsight_edge_true_random"][o] < 0.03, (k, o)


@pytest.mark.slow
@pytest.mark.parametrize("k,level,bot,seed", [c for c in checks() if c[2] != "exploit"])
def test_sample_replays_with_same_seeds(passport, k, level, bot, seed):
    c = find(passport, k, level, bot)
    lines = run(level, bot, c["matches"], c["rounds"], seed, k, indices=range(REPLAY))
    assert lines == c["sample"][:REPLAY]


def test_chi2_sf_known_values():
    assert chi2_sf(3.841, 1) == pytest.approx(0.05, abs=1e-3)
    assert chi2_sf(5.991, 2) == pytest.approx(0.05, abs=1e-3)
    assert chi2_sf(15.507, 8) == pytest.approx(0.05, abs=1e-3)
    assert chi2_sf(0.5, 4) == pytest.approx(0.9735, abs=1e-3)


def test_hindsight_edge():
    assert hindsight_edge([0, 1, 2] * 50, 3, 1) == pytest.approx(1.0)      # цикл виден насквозь
    assert hindsight_edge([0] * 100, 3, 0) == pytest.approx(1.0)
