"""ИИ честный: свой ход выбирает до хода человека и видит только прошлые раунды.

Закон: при одной и той же истории и одном зерне ход ИИ в раунде t не зависит от того,
что человек сыграет в раунде t. Проверка: два матча с одинаковой историей до t и разными
ходами человека в раунде t - ход ИИ в раунде t один и тот же, и хэш раскрывается верно.
"""
import random

import pytest

from game.ai.player import make_ai
from game.core.match import Match


def play_prefix(level, k, seed, moves):
    ai = make_ai(level, k, seed=seed)
    m = Match(k, 0)
    for h in moves:
        m.prepare(ai)
        m.play(h, ai)
    return ai, m


@pytest.mark.parametrize("level", ["novice", "medium", "strong"])
@pytest.mark.parametrize("k", [3, 5])
def test_ai_move_does_not_depend_on_current_human_move(level, k):
    rng = random.Random(k)
    for trial in range(4):
        prefix = [rng.randrange(k) for _ in range(rng.randrange(0, 40))]
        moves = set()
        for human in range(k):
            ai, m = play_prefix(level, k, 100 + trial, prefix)
            m.prepare(ai)
            rv = m.play(human, ai)
            assert rv.verified(k)
            moves.add(rv.ai)
        assert len(moves) == 1


def test_ai_gets_only_past_rounds():
    """choose получает кортеж прошлых раундов и ничего о текущем."""
    seen = []

    class Spy:
        def __init__(self):
            self.inner = make_ai("strong", 3, seed=1)

        def choose(self, history):
            seen.append(history)
            return self.inner.choose(history)

        def observe(self, r):
            self.inner.observe(r)

    ai = Spy()
    m = Match(3, 12)
    while not m.over:
        m.prepare(ai)
        m.play(len(m.rounds) % 3, ai)
    for i, h in enumerate(seen):
        assert isinstance(h, tuple) and len(h) == i


def test_replaying_history_gives_same_choice():
    """choose(history) без observe даёт тот же ход, что и с observe: ИИ - функция истории."""
    a, ma = play_prefix("strong", 3, 9, [0, 1, 1, 2, 0, 0, 1, 2, 2, 1] * 3)
    b = make_ai("strong", 3, seed=9)
    # b видит всю историю сразу; генератор b должен пройти те же выборы
    for i in range(len(ma.rounds)):
        b.choose(ma.history()[:i])
    assert a.choose(ma.history())[0] == b.choose(ma.history())[0]


def test_new_match_needs_new_ai():
    ai, m = play_prefix("medium", 3, 1, [0, 1, 2])
    with pytest.raises(ValueError):
        ai.choose(())
