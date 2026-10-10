<div align="center">

# Rock Paper Scissors vs AI

**Rock paper scissors (and the lizard-Spock variant) against an AI that learns your habits during the match. The AI's move is sealed with a fingerprint before you choose, so after each round you can check it did not peek.**

[Русская версия](README.ru.md)

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<img src="docs/preview_review.png" width="880" alt="End of a 50-round match: the score, the review of habits the AI found, the chart of won rounds, and the AI thoughts panel on the right">

</div>

People are bad at being random. They repeat, avoid three equal moves in a row, switch after a
loss. The AI watches for this and after about 30 rounds starts winning more than it loses.
Against a truly random player it cannot win, and the tests check that too.

## Features

- **3 signs** or **5 signs** (rock, paper, scissors, Spock, lizard).
- Matches of **50** or **100** rounds, or **endless** with an "End match" button.
- Three levels: **novice**, **medium**, **strong**, plus **AI vs bot** mode, where the AI plays one of
  the habit bots and you watch it catch the pattern.
- **Sealed move**: before your move the window shows the SHA-256 fingerprint of the AI's choice; after
  the round the move and the key are revealed and the fingerprint is checked.
- **AI thoughts**: how the AI expected you to play in the last round, which predictor led and why, the
  best strategies. Before your move only the fingerprint is visible; the switch "Peek at the AI's
  move (match not counted)" shows the move the AI has already chosen and its forecast, and such a
  match is marked and left out of statistics.
- **Review after the match**: habits the AI found, for example "after a loss you chose what would have
  beaten the AI's move 67% of the time (random: 33%)", and the round from which the AI stayed ahead.
- A chart of won rounds; statistics with charts: share of rounds won match by match, rounds by
  level, and the AI's strength from the passport as bars. Paint themes (dark and light), Russian and English, sounds, and the
  window reopens where it was closed. Signs are drawn by code, no images or emoji.

## How the AI plays

1. **Predictors** guess your next move from the history of past rounds:
   - frequencies over the whole match and the last 10 and 30 rounds;
   - Markov chains of order 1-5 on your moves, 1-3 on the AI's moves and on move pairs;
   - reaction to the result: what you do after a win, a tie and a loss, relative to your move and to
     the AI's move;
   - history matching, as in the Iocaine Powder bot: the longest piece of history that repeats its end;
   - a small numpy network (3 rounds in, 24 hidden, softmax) that trains **during the match**.
2. **Shifts**: every predictor also gets "you are one step ahead" and "two steps ahead" versions.
3. **Judges** with different memory (about 3, 10, 33 and 200 rounds) score every strategy with decay;
   the AI trusts the judge whose own choices worked best lately.
4. **Confidence**: with no clear edge the AI plays at random, since a random move cannot be beaten.
5. **Guard**: if the AI loses on its own predictions, someone has read it, and it plays at random for 20
   rounds (doubling if this repeats).

| Level | Predictors |
|---|---|
| Novice | frequencies only, no shifts, no guard |
| Medium | frequencies and Markov chains on your moves |
| Strong | everything above |

## Passport

`game/models/rockpaper-passport.json`, `python -m game.train.passport`: 40 matches of 100 rounds for
every check, 216 s on 2 processes. Share of rounds won / lost by the strong AI **after round 30**:

| Opponent | 3 signs | 5 signs |
|---|---|---|
| Repeater (repeats 80%) | 82.8% / 7.6% | 86.1% / 8.9% |
| Cycle rock → scissors → paper | 100% / 0% | 100% / 0% |
| Win-stay, lose-shift | 99.8% / 0.1% | 100% / 0% |
| Markov 2 (favourite move after each pair, 75%) | 75.4% / 10.7% | 69.6% / 19.0% |
| Loves rock (50/30/20) | 38.0% / 28.9% | 41.9% / 37.7% |
| Human-like (avoids triples, half-follows habits) | 43.8% / 27.8% | 46.8% / 34.8% |
| Random | 33.8% / 33.8% | 41.4% / 39.0% |
| Mirror (predicts the AI and beats it) | 41.7% / 30.4% | 46.6% / 35.5% |
| A copy of the same AI (worst case) | 32.8% / 34.2% | 38.1% / 42.7% |

With 5 signs a fair share is 40% wins, 20% ties, 40% losses.

**Against a random player** (5 matches of 4000 rounds): 33.6% / 33.4% / 33.0% with 3 signs and
40.1% / 19.8% / 40.1% with 5. Even if a person knew, after the fact, the full tables of "after these
0-2 AI moves the next one is distributed like this", they would win at most 2.4% per round more than
against a true random generator of the same length.

Tests replay the first match of every check with the same seeds and check the claims above.

## Honesty

- `tests/test_honesty.py`: with the same history and seed, the AI's move in round t is the same
  whatever you play in round t; the AI receives only a tuple of past rounds.
- Every round's fingerprint is checked in the window and in the self-test.
- "AI thoughts" show the past round. The current prediction is shown only with "peek", and the match is
  then left out of statistics.

## Run

```
pip install -r requirements.txt
python main.py
python main.py --selftest result.txt    # no screen: rules, AI against bots, a match through the window
```

Keys: 1-5 pick a sign, N new match, Esc menu, Space pauses the AI vs bot show.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest -q
python tools/mutate.py          # mutation check: deliberately broken code must fail the tests
python tools/make_previews.py   # screenshots in docs/
```

The window tests run without a screen (Qt offscreen).

## Layout

`game/` follows the AiGameRoom contract (`GAME_INFO` and `create_widget(ctx)`): `core/` rules, sealed
move and match without Qt, `ai/` predictors, the network, the meta-choice, bots, the habit review,
`train/passport.py`, `ui/` the window. `aikit/` is the shared kit of the AI games.

## License

MIT, see [LICENSE](LICENSE).
