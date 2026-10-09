"""Правила 3 и 5 знаков, фиксация хода хэшем, матч."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from game.core import commit as cm
from game.core.match import Match
from game.core.rules import (LIZARD, LOSS, PAPER, ROCK, SCISSORS, SPOCK, TIE, WIN, beaters, beats,
                             best_responses, expected, outcome)


def test_classic_three():
    assert beats(PAPER, ROCK, 3) and beats(SCISSORS, PAPER, 3) and beats(ROCK, SCISSORS, 3)
    assert not beats(ROCK, PAPER, 3) and not beats(ROCK, ROCK, 3)
    assert outcome(ROCK, SCISSORS) == WIN and outcome(ROCK, PAPER) == LOSS and outcome(ROCK, ROCK) == TIE


def test_lizard_spock_table():
    """Все десять правил «ножницы режут бумагу…» из игры Шелдона."""
    rules = [(SCISSORS, PAPER), (PAPER, ROCK), (ROCK, LIZARD), (LIZARD, SPOCK), (SPOCK, SCISSORS),
             (SCISSORS, LIZARD), (LIZARD, PAPER), (PAPER, SPOCK), (SPOCK, ROCK), (ROCK, SCISSORS)]
    for a, b in rules:
        assert beats(a, b, 5) and not beats(b, a, 5), (a, b)
    pairs = {(a, b) for a in range(5) for b in range(5) if beats(a, b, 5)}
    assert pairs == set(rules)


@pytest.mark.parametrize("k", [3, 5])
def test_each_sign_beats_half_of_others(k):
    for m in range(k):
        assert len(beaters(m, k)) == (k - 1) // 2
        assert sum(outcome(m, x, k) for x in range(k)) == 0


@given(st.sampled_from([3, 5]), st.integers(0, 4), st.integers(0, 4))
def test_outcome_antisymmetric(k, a, b):
    a, b = a % k, b % k
    assert outcome(a, b, k) == -outcome(b, a, k)


def test_best_response():
    assert best_responses([1, 0, 0], 3) == [PAPER]
    assert best_responses([0, 0, 1], 3) == [ROCK]
    assert best_responses([1 / 3] * 3, 3) == [0, 1, 2]
    assert expected([1, 0, 0], 3) == [0, 1, -1]
    assert set(best_responses([1, 0, 0, 0, 0], 5)) == {PAPER, SPOCK}


def test_commit_reveal():
    h, nonce = cm.commit(3, 7, PAPER)
    assert len(h) == 64 and len(nonce) == 32
    assert cm.verify(h, 3, 7, PAPER, nonce)
    assert not cm.verify(h, 3, 7, ROCK, nonce)
    assert not cm.verify(h, 3, 8, PAPER, nonce)          # чужой раунд
    assert not cm.verify(h, 5, 7, PAPER, nonce)
    assert not cm.verify(h, 3, 7, PAPER, "0" * 32)
    # ключ случайный: один и тот же ход даёт разные хэши
    assert cm.commit(3, 7, PAPER)[0] != cm.commit(3, 7, PAPER)[0]


class Fixed:
    def __init__(self, moves):
        self.moves = list(moves)
        self.seen = []

    def choose(self, history):
        self.seen.append(len(history))
        return self.moves[len(history)], {"x": 1}

    def observe(self, r):
        pass


def test_match_flow_and_score():
    ai = Fixed([ROCK, PAPER, SCISSORS])
    m = Match(3, 3)
    for human in (PAPER, PAPER, PAPER):
        h = m.prepare(ai)
        assert m.prepare(ai) == h                     # повторный prepare не перевыбирает
        rv = m.play(human, ai)
        assert rv.commit == h and rv.verified(3)
    assert m.over and ai.seen == [0, 1, 2]
    assert m.score() == {"wins": 1, "ties": 1, "losses": 1}
    assert m.outcome_for_human() == "draw"
    assert m.ai_share_curve() == [0, 0, pytest.approx(1 / 3)]
    with pytest.raises(RuntimeError):
        m.prepare(ai)


def test_play_requires_prepare_and_valid_move():
    m = Match(5, 0)
    with pytest.raises(RuntimeError):
        m.play(ROCK)
    m.prepare(Fixed([SPOCK]))
    with pytest.raises(ValueError):
        m.play(5)
    rv = m.play(LIZARD)
    assert rv.result == WIN
    assert not m.over
    m.end()
    assert m.over and m.outcome_for_human() == "win"


def test_bad_variant():
    with pytest.raises(ValueError):
        Match(4)
