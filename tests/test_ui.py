"""Окно без экрана (Qt offscreen): матч мышью и клавишами, отпечаток до хода и проверка
после, «Мысли ИИ» о сыгранном раунде и подглядывание вне статистики, разбор, показ
«ИИ против бота», темы, языки, остановка, место окна. Ожидания - с тайм-аутом."""
import json
import os
import time

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QShortcut
from PySide6.QtWidgets import QApplication, QLabel

from aikit.widgets import Combo
from game import APP_NAME, GAME_INFO, create_widget
from game.ai.bots import make_bot
from game.ui.i18n import EN, RU

QWIDGETSIZE_MAX = (1 << 24) - 1


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
    yield w
    w.game.shutdown()
    w.close()


def wait(app, cond, limit=20.0):
    end = time.time() + limit
    while not cond() and time.time() < end:
        app.processEvents()
        time.sleep(0.002)
    return cond()


def play_with_bot(g, key="human", seed=1):
    bot = make_bot(key, g.session.k, seed=seed)
    while not g.session.over:
        g.on_sign(bot.move(g.session.match.history()))


def test_translations_complete():
    assert set(RU) == set(EN)


def test_match_to_the_end_records_stats_and_review(app, win):
    g = win.game
    g.change("length", 50)
    g.start_match(seed=3)
    assert g.current_page() == "play"
    play_with_bot(g, "cycle")
    assert len(g.session.rounds) == 50
    e = g.ctx.stats.entry("3/strong")
    assert e["games"] == 1 and e["losses"] == 1             # цикл ИИ ловит: матч за ИИ
    rounds = json.load(open(os.path.join(g.ctx.data_dir, "rounds.json"), encoding="utf-8"))
    assert sum(rounds["3/strong"]) == 50
    pp = g.play
    assert pp.review.isVisibleTo(pp) and "•" in pp.review_text.text()
    assert all(not b.isEnabled() for b in pp.sign_buttons)
    g.on_sign(0)                                             # после конца ходы не идут
    assert len(g.session.rounds) == 50


def test_commit_shown_before_and_verified_after(app, win):
    g = win.game
    g.start_match(seed=5)
    for i in range(6):
        h = g.session.commit
        assert h[:16] in g.play.commit.text()
        g.on_sign(i % 3)
        rv = g.session.last_reveal()
        assert rv.commit == h and rv.verified(3)
        assert "✓" in g.play.verify.text()


def test_click_sign_button_plays(app, win):
    g = win.game
    g.start_match(seed=6)
    b = g.play.sign_buttons[1]
    pos = QPointF(b.width() / 2, b.height() / 2)
    b.mouseReleaseEvent(QMouseEvent(QMouseEvent.Type.MouseButtonRelease, pos, pos, Qt.MouseButton.LeftButton,
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    assert g.session.rounds[-1].human == 1


def test_keys_pick_signs_only_in_match(app, win):
    g = win.game
    shortcuts = {sc.key().toString(): sc for sc in g.findChildren(QShortcut)}
    assert {"1", "2", "3", "4", "5", "N", "Esc", "Space"} <= set(shortcuts)
    g.change("k", 5)
    g.start_match(seed=7)
    shortcuts["5"].activated.emit()
    assert g.session.rounds[-1].human == 4
    g.change("k", 3)
    g.start_match(seed=7)
    shortcuts["5"].activated.emit()                       # на трёх знаках клавиши 4-5 молчат
    g.on_sign(4)
    assert not g.session.rounds
    shortcuts["Esc"].activated.emit()
    assert g.current_page() == "menu"
    shortcuts["2"].activated.emit()                       # в меню ход не идёт
    assert not g.session.rounds


def test_thoughts_are_about_the_played_round(app, win):
    g = win.game
    g.change("peek", False)
    g.change("show_thoughts", True)
    g.start_match(seed=8)
    pp = g.play
    assert not pp.bars.isVisibleTo(pp)                    # раунда ещё не было
    for i in range(12):
        g.on_sign([0, 0, 1][i % 3])
        rv = g.session.last_reveal()
        assert pp.th_title.text() == RU["thoughts_round"].format(n=rv.round_no + 1)
        assert pp.bars.dist == rv.thoughts["dist"]
        assert rv.thoughts["round"] == rv.round_no != g.session.pending_thoughts()["round"]
    assert g.ctx.stats.entry("3/strong")["games"] == 0
    g.change("show_thoughts", False)
    assert not pp.bars.isVisibleTo(pp)


def test_without_peek_the_forecast_for_this_move_is_hidden(app, win):
    """Без флажка до хода виден только отпечаток: панель прямо говорит, что прогноз скрыт,
    а столбики подписаны как ожидание ИИ в ПРОШЛОМ раунде (жалоба Алексея 10.10: «прогноз
    показывается всегда»)."""
    g = win.game
    g.change("peek", False)
    g.start_match(seed=21)
    pp = g.play
    for _ in range(8):
        g.on_sign(0)
    rv = g.session.last_reveal()
    assert pp.forecast_note.isVisibleTo(pp) and pp.forecast_note.text() == RU["forecast_hidden"]
    assert pp.bars_caption.text() == RU["expected_last"].format(n=rv.round_no + 1)
    assert pp.bars.dist == rv.thoughts["dist"]
    assert not pp.ai_move_peek.isVisibleTo(pp)
    assert not pp.not_counted.isVisibleTo(pp)
    assert g.session.commit[:16] in pp.commit.text()


def test_peek_shows_this_move_and_keeps_match_out_of_stats(app, win):
    g = win.game
    g.change("length", 50)
    g.start_match(seed=9)
    g.on_sign(0)
    g.change("peek", True)
    pp = g.play
    assert g.session.peeked
    assert pp.bars_caption.text() == RU["predicted_now"]
    assert pp.bars.dist == g.session.pending_thoughts()["dist"]
    assert not pp.forecast_note.isVisibleTo(pp)
    planned = RU[["rock", "paper", "scissors"][g.session.match.pending.move]]
    assert pp.ai_move_peek.isVisibleTo(pp) and planned in pp.ai_move_peek.text()
    assert pp.not_counted.isVisibleTo(pp) and pp.not_counted.text() == RU["not_counted"]
    play_with_bot(g, "repeat")
    assert g.ctx.stats.entry("3/strong")["games"] == 0
    assert not os.path.exists(os.path.join(g.ctx.data_dir, "rounds.json"))
    assert g.match_history() == []
    g.change("peek", False)
    assert pp.not_counted.isVisibleTo(pp)                 # выключили поздно - матч всё равно вне статистики
    g.start_match(seed=10)                                # новый матч без подглядывания - считается
    assert not g.session.peeked and not pp.not_counted.isVisibleTo(pp)


def test_peek_switch_says_what_it_does(app, win):
    g = win.game
    g.start_match(seed=1)
    box = g.play.peek_box
    assert box.text() == "Подсматривать ход ИИ (матч не идёт в статистику)"
    assert "отпечаток" in box.toolTip() and "статистик" in box.toolTip()
    win.ctx.set_lang("en")
    assert "not counted" in box.text() and "fingerprint" in box.toolTip()
    win.ctx.set_lang("ru")


def test_endless_match_ends_by_button(app, win):
    g = win.game
    g.change("length", 0)
    g.change("level", "novice")
    g.start_match(seed=11)
    for i in range(15):
        g.on_sign(i % 3)
    assert g.play.end_button.isVisibleTo(g.play)
    g.end_match()
    assert g.session.over and g.ctx.stats.entry("3/novice")["games"] == 1
    assert not g.play.end_button.isVisibleTo(g.play)


def test_five_signs(app, win):
    g = win.game
    g.change("k", 5)
    g.start_match(seed=12)
    assert all(b.isVisibleTo(g.play) for b in g.play.sign_buttons)
    for i in range(10):
        g.on_sign(4 - i % 5)
    assert g.session.rounds[-1].human in range(5)
    g.change("k", 3)
    g.start_match(seed=12)
    assert not g.play.sign_buttons[4].isVisibleTo(g.play)


def test_demo_plays_itself_and_is_not_recorded(app, win):
    g = win.game
    g.change("mode", "demo")
    g.change("bot", "wsls")
    g.change("length", 50)
    g.change("delay_ms", 0)
    g.start_match(seed=13)
    assert wait(app, lambda: g.session.over, 30)
    sc = g.session.match.score()
    assert sc["losses"] > sc["wins"]                      # ИИ поймал бота
    assert g.ctx.stats.entry("3/strong")["games"] == 0
    g.change("mode", "play")


def test_demo_pause(app, win):
    g = win.game
    g.change("mode", "demo")
    g.change("delay_ms", 0)
    g.start_match(seed=14)
    g.toggle_pause()
    n = len(g.session.rounds)
    t0 = time.time()
    while time.time() - t0 < 0.2:
        app.processEvents()
    assert len(g.session.rounds) == n
    g.toggle_pause()
    assert wait(app, lambda: len(g.session.rounds) > n, 5)
    g.change("mode", "play")


def test_theme_and_language_on_the_fly(app, win):
    g = win.game
    g.start_match(seed=15)
    g.on_sign(0)
    win.ctx.set_theme("light")
    assert g.play.sign_buttons[0].theme == "light" and g.play.chart.theme == "light"
    assert not g.play.grab().toImage().isNull()
    win.ctx.set_lang("en")
    assert g.play.sign_buttons[0].text == "Rock" and g.play.new_button.text() == "New match"
    win.ctx.set_lang("ru")
    win.ctx.set_theme("dark")
    assert g.play.sign_buttons[0].text == "Камень"


def test_wrapped_labels_fit_at_minimum_size(app, win):
    """Подписи с переносом без потолка высоты; в окне минимального размера текст не режется."""
    g = win.game
    g.change("length", 50)
    g.start_match(seed=16)
    play_with_bot(g, "wsls")
    win.resize(win.minimumSize())
    app.processEvents()
    for w in g.findChildren(QLabel):
        if w.wordWrap():
            assert w.maximumHeight() == QWIDGETSIZE_MAX, w.text()
            if w.isVisible() and w.text():
                assert w.heightForWidth(w.width()) <= w.height() + 1, w.text()
    assert len(g.findChildren(Combo)) >= 3


def test_stats_charts_follow_matches_levels_and_passport(app, win):
    """Графики статистики (правило Алексея 10.10 для всех игр с ИИ): доля выигранных раундов
    по матчам, по уровням и сила ИИ из паспорта столбиками."""
    g = win.game
    st = g.stats
    g.show_page("stats")
    assert not st.chart_matches.has_data() and not st.chart_levels.has_data()
    assert st.chart_ai.has_data() and len(st.chart_ai.groups) == 9
    pp = g.passport()
    cyc = next(c for c in pp["checks"] if c["k"] == 3 and c["level"] == "strong" and c["bot"] == "cycle")
    assert st.chart_ai.series[0][2][1] == cyc["after30"]["win"]
    g.change("length", 50)
    for level, seed in (("strong", 1), ("strong", 2), ("novice", 3)):
        g.change("level", level)
        g.start_match(seed=seed)
        play_with_bot(g, "cycle", seed)
    g.show_page("stats")
    hist = g.match_history()
    assert [m["level"] for m in hist] == ["strong", "strong", "novice"] and all(m["rounds"] == 50 for m in hist)
    assert st.chart_matches.points == [(i + 1.0, m["wins"] / 50) for i, m in enumerate(hist)]
    assert st.chart_matches.second == [(i + 1.0, m["losses"] / 50) for i, m in enumerate(hist)]
    assert st.chart_matches.has_data()
    assert st.chart_levels.groups == ["3 · Новичок", "3 · Сильный"]
    tot = g.round_totals()["3/strong"]
    assert st.chart_levels.series[1][2][1] == tot[2] / sum(tot)
    win.ctx.set_theme("light")
    assert all(c.theme == "light" for c in st.charts())
    for c in st.charts():
        assert not c.grab().toImage().isNull()
    win.ctx.set_lang("en")
    assert st.chart_matches.title == "Share of rounds won, match by match"
    win.ctx.set_lang("ru")
    win.ctx.set_theme("dark")


def test_stats_cards_do_not_overlap_and_side_panel_is_not_clipped(app, win):
    """Кадр 10.10: графики статистики налезали друг на друга (страница в прокрутке не
    росла вслед за содержимым), а длинная подпись флажка раздвигала боковую панель и
    обрезала «Мысли ИИ» справа. Шаги - как у того кадра."""
    g = win.game
    g.change("length", 50)
    for level, seed in (("strong", 1), ("strong", 2), ("medium", 3), ("novice", 4)):
        g.change("level", level)
        g.start_match(seed=seed)
        play_with_bot(g, "human", seed)
    g.change("level", "strong")
    g.start_match(seed=9)
    for i in range(7):
        g.on_sign(i % 3)
    app.processEvents()
    win.grab()
    g.change("peek", True)
    app.processEvents()
    win.grab()
    side = g.play.thoughts_box.parentWidget()
    view = side.parentWidget()                      # окно прокрутки боковой панели
    assert side.width() <= view.width() + 1
    g.change("peek", False)
    g.show_page("stats")
    app.processEvents()
    st = g.stats
    cards = [st.table, *st.charts(), st.pp]
    spans = sorted((w.geometry().top(), w.geometry().bottom()) for w in cards)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 < b0, spans


def test_broken_match_history_is_ignored(app, win):
    g = win.game
    with open(os.path.join(g.ctx.data_dir, "matches.json"), "w", encoding="utf-8") as f:
        json.dump([{"k": 3, "level": "strong", "rounds": 10, "wins": 9, "ties": 9, "losses": 9}, "x",
                   {"k": 4, "level": "strong", "rounds": 1, "wins": 1, "ties": 0, "losses": 0},
                   {"k": 3, "level": "medium", "rounds": 2, "wins": 1, "ties": 0, "losses": 1}], f)
    assert g.match_history() == [{"k": 3, "level": "medium", "rounds": 2, "wins": 1, "ties": 0, "losses": 1}]
    g.show_page("stats")


def test_stats_page_shows_passport(app, win):
    g = win.game
    g.show_page("stats")
    assert g.stats.pp.rowCount() == 9 and g.stats.pp.columnCount() == 7
    g.show_page("settings")
    g.show_page("menu")


def test_shutdown_within_two_seconds_in_demo(app, win):
    g = win.game
    g.change("mode", "demo")
    g.change("length", 0)
    g.change("delay_ms", 0)
    g.start_match(seed=17)
    wait(app, lambda: len(g.session.rounds) > 5, 5)
    t0 = time.time()
    assert g.shutdown()
    assert time.time() - t0 < 2
    n = len(g.session.rounds)
    t1 = time.time()
    while time.time() - t1 < 0.1:
        app.processEvents()
    assert len(g.session.rounds) == n
    g.change("mode", "play")
    g.change("length", 100)


def test_window_remembers_size(app, tmp_path):
    from aikit.host import make_window
    root = str(tmp_path / "home2")
    w, _ = make_window(GAME_INFO, create_widget, APP_NAME, root=root)
    w.resize(1111, 777)
    w.show()
    app.processEvents()
    w.close()
    app.processEvents()
    data = json.load(open(os.path.join(root, "window.json"), encoding="utf-8"))
    assert data["width"] == 1111 and data["height"] == 777
