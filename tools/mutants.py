# Мутанты ядра, ИИ и окна для tools/mutate.py: (имя, файл, было, стало, проверки).
R = "game/core/rules.py"
C = "game/core/commit.py"
M = "game/core/match.py"
TR = "tests/test_rules.py"
TH = "tests/test_honesty.py"
MUTANTS = [
    ("rules: лучший ответ - худший", R, "top = max(ev)", "top = min(ev)", TR),
    ("rules: ожидание без знака", R, "sum(dist[b] * outcome(a, b, k) for b in range(k))",
     "sum(dist[b] * abs(outcome(a, b, k)) for b in range(k))", TR),
    ("commit: раунд не в отпечатке", C, 'f"rockpaperai:{int(k)}:{int(round_no)}:', 'f"rockpaperai:{int(k)}:0:', TR),
    ("commit: ключ постоянный", C, "nonce = nonce or make_nonce()", "nonce = nonce or '0' * 32", TR),
    ("match: prepare перевыбирает", M, "        if self.pending is None:\n            move, thoughts",
     "        if True:\n            move, thoughts", TR),
    ("match: ИИ видит раунд вперёд", M, "return tuple(self.rounds)", "return tuple(self.rounds) + ((self.rounds[-1],) if self.rounds else ())",
     TH),
    ("match: итог матча наоборот", M, 'if s["wins"] > s["losses"]:\n            return "win"',
     'if s["wins"] > s["losses"]:\n            return "loss"', TR),
]
P = "game/ai/predictors.py"
TA = "tests/test_ai.py"
MUTANTS += [
    ("predictors: окно частот не забывает", P, "                self.counts[self.recent[0]] -= 1", "                pass", TA),
    ("predictors: Маркова без затухания", P, "                row[i] *= self.decay\n            row[h] += 1",
     "                row[i] *= 1.0\n            row[h] += 1", TA),
    ("predictors: Маркова по чужому источнику", P,
     'return h if self.source == "h" else a if self.source == "a" else (h, a)\n\n    def update(self, h, a):\n        if len(self.tail)',
     'return a if self.source == "h" else h if self.source == "a" else (h, a)\n\n    def update(self, h, a):\n        if len(self.tail)', TA),
    ("predictors: реакция от чужого хода", P, 'return h if self.ref == "self" else a', 'return a if self.ref == "self" else h', TA),
    ("predictors: поиск по истории - короткий", P, "for L in range(min(self.max_len, n), 0, -1):",
     "for L in range(1, min(self.max_len, n) + 1):", TA),
]
PL = "game/ai/player.py"
MUTANTS += [
    ("player: бьёт не прогноз, а сам прогноз", PL, "q = [d[(b - j) % self.k] for b in range(self.k)]\n                    self.plans",
     "q = [d[(b - j - 1) % self.k] for b in range(self.k)]\n                    self.plans", TA),
    ("player: счёт стратегий наоборот", PL, "return sum(outcome(m, h, self.k) for m in moves) / len(moves)",
     "return sum(outcome(h, m, self.k) for m in moves) / len(moves)", TA),
    ("player: без защиты", PL, "            self.guard_left = self.guard_len * 2 ** min(self.strikes, 5)",
     "            self.guard_left = 0", TA),
    ("player: всегда уверен", PL, "        return float(min(1.0, max(0.0, v)))", "        return 1.0", TA),
    ("player: без сдвигов", PL, "self.shifts = list(range(k)) if shifts else [0]", "self.shifts = [0]", TA),
]
HB = "game/ai/habits.py"
MUTANTS += [
    ("habits: после проигрыша считает победы", HB, "lost = [(a, b) for a, b in pairs if a.result == LOSS]",
     "lost = [(a, b) for a, b in pairs if a.result == WIN]", TA),
    ("habits: порог заметности 0", HB, "Z_MIN = 2.0", "Z_MIN = 0.0", TA),
]
W = "game/ui/widget.py"
TU = "tests/test_ui.py"
MUTANTS += [
    ("ui: подглядывание идёт в статистику", W, "                s.peeked = True\n            self.refresh()",
     "                pass\n            self.refresh()", TU),
    ("ui: клавиши 4-5 на трёх знаках", W, "or sign >= s.k or", "or", TU),
    ("ui: бесконечный матч не записывается", W, "        s.end()\n        self._finish()", "        s.end()", TU),
    ("ui: показ не останавливается", W, '        """Окно закрывается: таймер показа стоп. Своих потоков у игры нет."""\n        self.timer.stop()',
     '        """Окно закрывается: таймер показа стоп. Своих потоков у игры нет."""', TU),
]
# 10.10: подглядывание, журнал матчей и графики статистики
MUTANTS += [
    ("ui: прогноз до хода виден без флажка", W, 'return (self.settings["peek"] and s is not None', 'return (s is not None', TU),
    ("ui: подсмотренный матч без пометки", W, 'pp.not_counted.setVisible(s.mode == "play" and s.peeked)',
     "pp.not_counted.setVisible(False)", TU),
    ("ui: подсмотренный матч в журнале", W, "        if outcome and s.counts():", "        if outcome:", TU),
    ("ui: линия ИИ рисует победы человека", W, '[(i + 1, m["losses"] / m["rounds"]) for i, m in enumerate(hist)]',
     '[(i + 1, m["wins"] / m["rounds"]) for i, m in enumerate(hist)]', TU),
    ("ui: статистика без минимального размера", W,
     "SetMinimumSize)\n        outer.setContentsMargins(26, 22, 26, 22)\n        outer.setSpacing(12)",
     "SetDefaultConstraint)\n        outer.setContentsMargins(26, 22, 26, 22)\n        outer.setSpacing(12)", TU),
    ("ui: подпись столбиков не говорит о прошлом раунде", W,
     'expected = t("expected_last_bot" if demo else "expected_last", n=rv.round_no + 1)',
     'expected = t("predicted_now")', TU),
]
# 16.10, независимая проверка: показ говорил «вы» о боте, подсказка не следовала за
# подглядыванием, уровни шли по алфавиту, матч без конца показывал несыгранный раунд
MUTANTS += [
    ("ui: в показе «Вы сыграли» о ходе бота", W, 'played = "bot_played" if s.mode == "demo" else "you_played"',
     'played = "you_played"', TU),
    ("ui: в показе «ждал от вас»", W, '"expected_last_bot" if demo else "expected_last"', '"expected_last"', TU),
    ("ui: в показе первый раунд «о вас»", W, 't("first_round_bot") if demo else t("first_round")',
     't("first_round")', TU),
    ("ui: подсказка мыслей не следует за подглядыванием", W,
     't("thoughts_hint_now") if self.peeking() else t("thoughts_hint")', 't("thoughts_hint")', TU),
    ("ui: уровни на графике по алфавиту", W, "            for lv in LEVELS:\n                w, ti, lo",
     "            for lv in sorted(LEVELS):\n                w, ti, lo", TU),
    ("ui: матч без конца - раунд после конца", W, 'n=n if s.over else n + 1', 'n=n + 1', TU),
]
