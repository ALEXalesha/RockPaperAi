"""Предсказатели, мета-выбор, защита, боты, разбор привычек."""
import random

import pytest

from game.ai import predictors as P
from game.ai.arena import ai_results, play, run, summary
from game.ai.bots import BOTS, HABIT_BOTS, make_bot
from game.ai.habits import analyse, caught_at
from game.ai.net import OnlineNet
from game.ai.player import AiPlayer, make_ai
from game.core.match import Round
from game.core.rules import LOSS, PAPER, ROCK, SCISSORS, TIE, WIN, beaters, outcome


def feed(p, pairs):
    for h, a in pairs:
        p.update(h, a)
    return p


def close(d, i, at_least=0.6):
    return d is not None and d[i] >= at_least and abs(sum(d) - 1) < 1e-5


def test_frequency_all_and_window():
    f = feed(P.Frequency(3), [(ROCK, 0)] * 20 + [(PAPER, 0)] * 5)
    assert close(f.predict(), ROCK)
    w = feed(P.Frequency(3, 5), [(ROCK, 0)] * 20 + [(PAPER, 0)] * 5)
    assert close(w.predict(), PAPER, 0.8)
    assert P.Frequency(3).predict() is None


def test_markov_on_human_ai_and_pairs():
    cyc = [(i % 3, 0) for i in range(30)]
    assert close(feed(P.Markov(3, 1, "h"), cyc).predict(), 30 % 3)
    # человек играет то, что побило бы прошлый ход ИИ
    rng = random.Random(1)
    pairs, prev_ai = [], 0
    for _ in range(60):
        a = rng.randrange(3)
        pairs.append(((prev_ai + 1) % 3, a))
        prev_ai = a
    m = feed(P.Markov(3, 1, "a"), pairs)
    assert close(m.predict(), (prev_ai + 1) % 3)
    two = feed(P.Markov(3, 2, "ha"), [(0, 1), (1, 2), (2, 0)] * 10)
    assert close(two.predict(), 0)
    assert P.Markov(3, 2, "h").predict() is None


def test_markov_forgets_old_habit():
    m = feed(P.Markov(3, 1, "h"), [(0, 0)] * 40 + [(0, 0), (1, 0)] * 15)
    d = m.predict()        # последним был ход 1, после него раньше шёл 0
    assert close(d, 0)
    m = feed(P.Markov(3, 1, "h"), [(0, 0), (0, 0)] * 30 + [(0, 0), (2, 0)] * 15 + [(0, 0)])
    assert close(m.predict(), 2)      # после 0 теперь чаще 2: старое затухло


def test_reaction_win_stay_lose_shift():
    bot = make_bot("wsls", 3, seed=1)
    rng = random.Random(2)
    p = P.Reaction(3, "ai")
    s = P.Reaction(3, "self")
    hist = []
    for _ in range(80):
        h = bot.move(tuple(hist))
        a = rng.randrange(3)
        hist.append(Round(h, a, outcome(h, a)))
        p.update(h, a)
        s.update(h, a)
    last = hist[-1]
    if last.result == LOSS:
        assert close(p.predict(), beaters(last.ai)[0])
    elif last.result == WIN:
        assert close(s.predict(), last.human)


def test_reaction_reference_moves():
    """«От своего хода»: человек всегда повторяет себя; «от хода ИИ»: всегда копирует ИИ.
    На пяти знаках: на трёх исход и свой ход однозначно задают ход ИИ, и опоры не различить."""
    rng = random.Random(3)
    me, ai_ref = P.Reaction(5, "self"), P.Reaction(5, "ai")
    h = 0
    for _ in range(60):
        a = rng.randrange(5)
        me.update(h, a)
    assert close(me.predict(), h, 0.8)
    last_a = 0
    for _ in range(60):
        a = rng.randrange(5)
        ai_ref.update(last_a, a)
        last_a = a
    assert close(ai_ref.predict(), last_a, 0.8)


def test_thoughts_name_the_right_shift():
    """Человек всегда играет камень: ИИ ждёт камень (сдвиг 0) и бьёт его бумагой."""
    ai = make_ai("medium", 3, seed=2)
    from game.core.match import Match
    m = Match(3, 0)
    for _ in range(30):
        m.prepare(ai)
        m.play(ROCK, ai)
    move, th = ai.choose(m.history())
    assert th["mode"] == "predict" and th["shift"] == 0
    assert max(range(3), key=lambda i: th["dist"][i]) == ROCK and move == PAPER


def test_history_match_finds_longest_repeat():
    seq = [0, 1, 2, 2, 1, 0, 0, 2]
    hm = feed(P.HistoryMatch(3, "h"), [(x, 0) for x in seq * 3])
    d = hm.predict()
    assert close(d, seq[0], 0.8) and hm.found >= 8
    assert P.HistoryMatch(3, "h").predict() is None


def test_online_net_learns_a_cycle():
    net = OnlineNet(3, seed=0)
    for i in range(150):
        net.update(i % 3, (i * 7) % 3)
    assert close(net.predict(), 150 % 3, 0.7)
    assert net.parameters() == (3 * 9) * 24 + 24 + 24 * 3 + 3


def test_levels_have_expected_predictors():
    assert {p.key for p in AiPlayer(3, "novice").predictors} == {"freq", "freq10"}
    assert len(AiPlayer(3, "novice").shifts) == 1 and not AiPlayer(3, "novice").guard
    med = {p.key for p in AiPlayer(3, "medium").predictors}
    assert "markov_h3" in med and "net" not in med
    strong = {p.key for p in AiPlayer(5, "strong").predictors}
    assert {"net", "match_ha", "react_ai", "markov_a1", "markov_ha3", "markov_h5"} <= strong
    assert AiPlayer(5, "strong").shifts == [0, 1, 2, 3, 4]
    with pytest.raises(ValueError):
        AiPlayer(3, "godlike")


def test_shift_catches_second_guesser():
    """Человек играет то, что бьёт его же прошлый ход (он думает, что ИИ его побьёт)."""
    lines = []
    for i in range(3):
        ai = make_ai("medium", 3, seed=i)

        class Second:
            def move(self, history):
                return (history[-1].human + 1) % 3 if history else 0
        lines.append(ai_results(play(ai, Second(), 80, 3)))
    assert summary(lines)["after30"]["win"] > 0.9


def test_strong_beats_habits_quickly():
    """Против цикла и «выиграл - остался, проиграл - сменил» ИИ выигрывает почти всё
    после 30-го раунда; против повторяющего - больше 70 %."""
    for bot in ("cycle", "wsls", "repeat"):
        s = summary(run("strong", bot, 2, 100, 5, 3))
        assert s["after30"]["win"] > (0.9 if bot != "repeat" else 0.7), (bot, s)


def test_random_ai_moves_are_uniform_and_unpredictable_vs_random():
    """Против честного случайного игрока - около трети побед, ходы ИИ ровные."""
    ai = make_ai("strong", 3, seed=11)
    m = play(ai, make_bot("random", 3, seed=12), 1500, 3)
    res = ai_results(m)
    for c in "WTL":
        assert abs(res.count(c) / 1500 - 1 / 3) < 0.05
    moves = [r.ai for r in m.rounds]
    for x in range(3):
        assert abs(moves.count(x) / 1500 - 1 / 3) < 0.05


def guarded_vs_peeker(guard, seed=3, rounds=300):
    """Соперник знает каждый ход ИИ «по прогнозу», но не его случайные ходы - так, как если
    бы человек разгадал все предсказатели ИИ."""
    from game.core.match import Match
    ai = AiPlayer(3, "strong", seed=seed, guard=guard)
    rng = random.Random(seed)
    m = Match(3, rounds)
    while not m.over:
        m.prepare(ai)
        p = m.pending
        h = beaters(p.move)[0] if p.thoughts["mode"] == "predict" else rng.randrange(3)
        m.play(h, ai)
    s = m.score()
    return ai, (s["wins"] - s["losses"]) / rounds


def test_guard_switches_to_random_when_exploited():
    on = [guarded_vs_peeker(True, s) for s in (3, 4, 5)]
    off = [guarded_vs_peeker(False, s) for s in (3, 4, 5)]
    assert all(ai.guard_triggers >= 1 for ai, _ in on) and all(ai.guard_triggers == 0 for ai, _ in off)
    net_on = sum(n for _, n in on) / 3
    net_off = sum(n for _, n in off) / 3
    assert net_on < net_off - 0.03          # с защитой разгадавший выигрывает меньше
    assert net_on < 0.1


def test_mirror_and_exploiter_do_not_beat_strong():
    for bot in ("mirror", "exploit"):
        s = summary(run("strong", bot, 2, 150, 9, 3))["all"]
        assert s["win"] - s["loss"] > -0.08, (bot, s)


def test_all_bots_play_both_variants():
    for k in (3, 5):
        for key in BOTS:
            b = make_bot(key, k, seed=1)
            hist = []
            for _ in range(10):
                h = b.move(tuple(hist))
                assert 0 <= h < k
                hist.append(Round(h, 0, outcome(h, 0, k)))
    assert set(HABIT_BOTS) <= set(BOTS)


def test_bots_have_their_habits():
    hist = []
    b = make_bot("cycle", 3, seed=1)
    for _ in range(6):
        h = b.move(tuple(hist))
        hist.append(Round(h, 0, outcome(h, 0)))
    assert all((y.human - x.human) % 3 == 2 for x, y in zip(hist, hist[1:]))   # К→Н→Б
    hist = []
    b = make_bot("biased", 3, seed=1)
    for _ in range(2000):
        hist.append(Round(b.move(()), 0, 0))
    assert abs(sum(r.human == ROCK for r in hist) / 2000 - 0.5) < 0.04


def rounds_of(pairs, k=3):
    return [Round(h, a, outcome(h, a, k)) for h, a in pairs]


def test_habits_found_for_loss_shift_and_favorite():
    bot = make_bot("wsls", 3, seed=4)
    rng = random.Random(5)
    hist = []
    for _ in range(100):
        h = bot.move(tuple(hist))
        a = rng.randrange(3)
        hist.append(Round(h, a, outcome(h, a)))
    keys = [x["key"] for x in analyse(hist)]
    assert "loss_beat_ai" in keys and "win_stay" in keys
    # после проигрыша бьёт ход ИИ, после победы - копирует ход ИИ (не бьёт его)
    hist = []
    for _ in range(120):
        a = rng.randrange(3)
        if hist and hist[-1].result == LOSS:
            h = beaters(hist[-1].ai)[0]
        elif hist and hist[-1].result == WIN:
            h = hist[-1].ai
        else:
            h = rng.randrange(3)
        hist.append(Round(h, a, outcome(h, a)))
    lb = [x for x in analyse(hist) if x["key"] == "loss_beat_ai"]
    assert lb and lb[0]["rate"] == 1.0
    fav = analyse(rounds_of([(SCISSORS, 0)] * 30 + [(ROCK, 1)] * 5))
    assert any(x["key"] == "favorite" and x["move"] == SCISSORS for x in fav)


def test_no_habits_for_random_player():
    rng = random.Random(8)
    hist = rounds_of([(rng.randrange(3), rng.randrange(3)) for _ in range(300)])
    assert len(analyse(hist)) <= 1


def test_caught_at():
    rs = rounds_of([(ROCK, PAPER)] * 20)               # человек всё время проигрывает
    assert caught_at(rs) == 10
    rs = rounds_of([(PAPER, ROCK)] * 20)
    assert caught_at(rs) is None
    rs = rounds_of([(PAPER, ROCK)] * 5 + [(ROCK, PAPER)] * 20 + [(ROCK, ROCK)])
    assert caught_at(rs) == 11
    assert TIE == 0
