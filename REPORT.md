# EF101-P01: Web-Based Hangman Game with Leaderboard

**Project report** | Group size: 3 | Submission: Week 13, Monday 9 November 2026

Group members: _(write your three names here)_  |  Live URL: _(paste your hosted link here)_

---

## 1. What is Hangman?

Hangman is a classic word-guessing game for one or two players.

1. A secret word is chosen. The player only sees one blank for each letter, for example `_ _ _ _ _ _` for a six-letter word.
2. The player guesses one letter at a time.
3. If the letter is in the word, it is written into every blank where it belongs.
4. If the letter is not in the word, it counts as a wrong guess and one more piece of a stick-figure drawing (a gallows with a hanging person) is added.
5. The player **wins** by filling in every blank before the drawing is complete. The player **loses** when the drawing is finished.

In this project the computer chooses the word and keeps the rules, so one person can play alone. We then added a scoring system and a leaderboard so players can compete.

## 2. What the project demonstrates

The assignment asks us to show how a web application combines four parts. Here is where each one lives:

| Part | What it does in our game | Where it is |
|---|---|---|
| User interface | Draws the gallows, word tiles, keyboard, dialogs and leaderboard in the browser | `static/index.html`, `style.css`, `app.js` |
| Application logic | Chooses a random word, checks guesses, ignores duplicates, detects win/loss, calculates score | `app.py` (Python / Flask) |
| Word database | Stores 7,149 words with difficulty tags | table `words` in SQLite |
| Persistent scores | Stores every game and every saved score so the leaderboard survives closing the browser | table `game_sessions` in SQLite |

**How they talk to each other.** The browser never decides anything. When the player clicks a letter, the browser sends it to the server (`POST /api/game/<id>/guess`). The server checks it against the secret word, updates the database, and replies with the new state. The browser then redraws the screen from that reply. Because the secret word stays on the server until the game ends, a player cannot cheat by viewing the page source or network traffic.

```
 Browser (HTML/CSS/JS)  --- HTTP + JSON --->  Flask server (app.py)  --- SQL --->  SQLite file (hangman.db)
 draws screen, sends letters                  rules, scoring, random word          words + game_sessions
```

## 3. Technology choices

* **Python + Flask**: small, readable web framework; the whole backend is one file.
* **SQLite**: a real relational database stored in a single file, so no database server needs installing. It is persistent (data stays on disk) and supports SQL queries and indexes.
* **Plain HTML, CSS and JavaScript** on the front end: no build tools, easy to explain.
* **Gunicorn / WSGI** for hosting.

## 4. Vocabulary (requirement: at least 5,000 valid words)

The database holds **7,149 words**: 3,344 Easy, 2,725 Medium and 1,080 Hard.

How the list was built (`tools/build_words.py`):

1. Start from the open-source **Hunspell en_US** dictionary, so every word is a valid English word.
2. Keep only plain lowercase words of 4 to 14 letters (no names, hyphens or apostrophes).
3. Remove obscure words: the script counts how often each word appears in a large body of real English text and keeps words that occur at least 10 times.
4. Remove a small block-list of inappropriate words.
5. Tag each remaining word with a difficulty (next section).

The words are loaded from `data/words.csv` into the `words` table the first time the server starts. They are **not** hard-coded in the webpage.

## 5. Difficulty rule (documented as required)

Each word gets a **difficulty score** D:

```
D = (number of letters in the word) + (rarity points of each letter)
```

Rarity points reflect how hard a letter is to guess, based on how common it is in English:

| Letters | Points |
|---|---|
| e t a o i n s h r d l u (very common) | 0 |
| c m f y w g p b | 1 |
| v k | 2 |
| j x q z (very rare) | 3 |

Then:

| Level | Rule | Wrong guesses allowed | Score multiplier |
|---|---|---|---|
| Easy | D ≤ 8 | 8 | ×1 |
| Medium | 9 ≤ D ≤ 12 | 6 | ×2 |
| Hard | D ≥ 13 | 5 | ×3 |

Worked examples: `speech` = 6 + (p=1, c=1, others 0) = **8, Easy**. `necessary` = 9 + (c=1, y=1, others 0) = **11, Medium**. `choreographic` = 13 letters + (c=1, g=1, p=1, c=1 = 4 points) = **17, Hard**.

Longer words and words with rare letters are harder because there are more blanks to fill and fewer helpful letters to start with. Harder levels also give fewer wrong guesses.

## 6. Scoring formula (written in the report as required)

When a game is **won**:

```
Score = M × ( 100 + 10 × L + 25 × R )
```

* **M** = difficulty multiplier (Easy 1, Medium 2, Hard 3)
* **L** = number of letters in the word
* **R** = wrong guesses still unused when the word was completed

A **lost** game scores 0.

Example: a 9-letter Medium word solved with 5 of 6 wrong guesses unused: 2 × (100 + 90 + 125) = **630**.

So the score rewards winning (base 100), harder levels (M), longer words (L) and accurate play (R). The screen shows **"Score if solved now"**, which updates after every guess (it falls each time you guess wrong), and a **Session total** of all points won since the page was opened.

## 7. Database design (data model)

**Table `words`**

| Column | Meaning |
|---|---|
| id (primary key) | word ID |
| word (unique) | the word text |
| difficulty | easy / medium / hard |
| length | number of letters |
| difficulty_score | the value D from section 5 |
| freq | how common the word is in real text |
| category | optional category (left empty) |

**Table `game_sessions`** (one row per game played)

| Column | Meaning |
|---|---|
| id (primary key) | random game ID |
| word_id → words.id | which word was chosen (foreign key) |
| difficulty | level played |
| guessed | letters guessed so far |
| wrong_count, max_attempts | attempts used and allowed |
| status | playing / won / lost (the **result**) |
| score | final score |
| player_name | filled only when the player saves the score |
| created_at, finished_at | date/time |

The leaderboard is a query on this table: won games with a saved name, ordered by score, limited to 50 rows. The optional `Users` table is not implemented because the assignment makes authentication optional.

## 8. How each mandatory requirement is met

| Requirement | How it is met |
|---|---|
| 5,000+ words in a database | 7,149 words in SQLite table `words` |
| Easy, Medium, Hard | Three levels chosen on the start screen |
| Documented difficulty rule | Section 5 |
| Random word by difficulty | Server picks a random row of the chosen level (`/api/game/new`) |
| Show hidden letters, guessed letters, attempts, score | Word tiles, keyboard colours, wrong-letter list, "wrong guesses left" and "score if solved now" |
| Duplicates do not cost attempts | Server detects a repeated letter, changes nothing, and tells the player |
| Correct guess reveals all occurrences | Server returns the full pattern; checked in the automated test |
| Win and loss detection | Server sets status `won` when no blanks remain, `lost` when wrong guesses reach the limit |
| Scoring formula in report | Section 6 |
| Ask for name before saving | A name box appears in the win dialog; the score is saved only after a name is entered |
| Persistent scores | Saved in the SQLite file on the server |
| Top 50 leaderboard | `/api/leaderboard`, with All / Easy / Medium / Hard filters |
| Top 3 badges and larger names | Gold, silver and bronze circle badges; names for ranks 1 to 3 are 1.75rem versus 1rem for the rest |
| New game / Play again | "New game", "Change difficulty" and "Play again" buttons; no reinstall or database change |
| Hosted at a URL | See section 10 |

## 9. Testing

`python tests_smoke.py` runs an automated test on a temporary database. It checks: at least 5,000 words; all three levels return the right word and never leak the secret; invalid input is rejected; duplicate guesses cost nothing; every matching letter is revealed; the win score matches the formula; a finished game rejects further guesses; empty names are rejected; a score can only be saved once; the loss path scores 0; and the leaderboard returns the saved score. Result: **all tests passed**. The interface was also tested in a real browser (start screen, playing, duplicate guess, loss dialog, leaderboard, mobile layout) with no errors.

## 10. Hosting

See `README.md` for step-by-step instructions (PythonAnywhere is recommended because its disk is permanent, so the leaderboard survives restarts).

## 11. Limitations and possible improvements

* There are no user accounts, so a player name is not verified (anyone can type any name).
* The word list comes from a general dictionary and is not hand-checked, so an occasional unusual word may appear.
* Possible additions: user registration, a hint button that costs points, word categories, a daily challenge, per-player statistics.
