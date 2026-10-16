"""Брошенный матч (решение автора 16.10, как в Дураке): после первого сыгранного раунда он
идёт в статистику и графики поражением, даже если вы вели по счёту. Бросить - «Новый матч»
(кнопка или N), «В меню» (кнопка или Esc), закрыть окно. До первого раунда матч не
считается. «Завершить матч» - как и раньше, итог по счёту раундов. Подглядывание и показ
«ИИ против бота» в статистику не идут. Окно без экрана (Qt offscreen)."""
import time

import pytest
from PySide6.QtWidgets import QApplication

from game import APP_NAME, GAME_INFO, create_widget
from game.ui.i18n import EN, RU


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path):
    from aikit.host import make_window
    w, ctx = make_window(GAME_INFO, create_widget, APP_NAME, root=str(tmp_path / "home"))
    w.resize(1280, 800)
    w.show()
    app.processEvents()
    g = w.game
    g.change("level", "novice")
    g.change("length", 50)
    yield w
    w.game.shutdown()
    w.close()


def wait(app, cond, limit=20.0):
    end = time.time() + limit
    while not cond() and time.time() < end:
        app.processEvents()
        time.sleep(0.002)
    return cond()


def win_rounds(g, n):
    """n раундов, выигранных вами: тест (не игрок) знает закрытый ход ИИ. На 3 знаках
    ход a бьёт b, если (a - b) mod 3 нечётно, - то есть a = b + 1."""
    s = g.session
    for _ in range(n):
        g.on_sign((s.match.pending.move + 1) % s.k)


def leave(app, g, how):
    if how == "menu":
        g.show_page("menu")
    elif how == "new":
        g.start_match(seed=99)
    else:
        g.shutdown()
    app.processEvents()


def entry(g, key="3/novice"):
    return g.ctx.stats.entry(key)


@pytest.mark.parametrize("how", ["menu", "new", "close"])
def test_left_after_first_round_is_a_loss_even_when_leading(app, win, how):
    g = win.game
    g.start_match(seed=3)
    win_rounds(g, 3)
    assert g.session.match.score() == {"wins": 3, "ties": 0, "losses": 0}
    leave(app, g, how)
    e = entry(g)
    assert (e["games"], e["losses"], e["wins"], e["draws"]) == (1, 1, 0, 0), how
    # раунды сыграны - они в итогах раундов и в графике по матчам
    assert g.round_totals()["3/novice"] == [3, 0, 0]
    hist = g.match_history()
    assert len(hist) == 1 and hist[0]["rounds"] == 3 and hist[0]["wins"] == 3
    assert hist[0].get("abandoned") is True


@pytest.mark.parametrize("how", ["menu", "new", "close"])
def test_left_before_first_round_is_not_counted(app, win, how):
    g = win.game
    g.start_match(seed=3)
    leave(app, g, how)
    assert entry(g)["games"] == 0
    assert g.round_totals() == {} and g.match_history() == []


def test_endless_match_left_without_the_button_is_a_loss(app, win):
    g = win.game
    g.change("length", 0)
    g.start_match(seed=4)
    win_rounds(g, 2)
    g.show_page("menu")
    assert entry(g)["losses"] == 1


def test_end_button_still_counts_by_the_score(app, win):
    g = win.game
    g.change("length", 0)
    g.start_match(seed=4)
    win_rounds(g, 2)
    g.end_match()
    g.show_page("menu")
    g.start_match(seed=5)
    g.shutdown()
    e = entry(g)
    assert (e["games"], e["wins"], e["losses"]) == (1, 1, 0)
    assert len(g.match_history()) == 1 and "abandoned" not in g.match_history()[0]


def test_left_once_is_counted_once(app, win):
    g = win.game
    g.start_match(seed=3)
    win_rounds(g, 1)
    g.show_page("menu")
    g.show_page("stats")
    g.show_page("menu")
    g.shutdown()
    assert entry(g)["games"] == 1 and len(g.match_history()) == 1


def test_peeked_or_demo_match_left_is_not_counted(app, win):
    g = win.game
    g.change("peek", True)
    g.start_match(seed=3)
    win_rounds(g, 2)
    g.show_page("menu")
    g.change("peek", False)
    g.change("mode", "demo")
    g.change("delay_ms", 0)
    g.start_match(seed=2)
    assert wait(app, lambda: len(g.session.rounds) >= 3, 20)
    g.show_page("menu")
    g.change("mode", "play")
    assert entry(g)["games"] == 0 and g.match_history() == [] and g.round_totals() == {}


def test_stats_note_explains_the_count():
    assert "брош" in RU["stats_note"].lower() and "поражение" in RU["stats_note"]
    assert "left" in EN["stats_note"].lower() and "loss" in EN["stats_note"]
