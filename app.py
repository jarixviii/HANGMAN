"""
Hangman web application - backend.

Stack: Python 3 + Flask (web server) + SQLite (database file).
All game rules live HERE on the server. The browser only shows what the server tells it, and the
secret word is never sent to the browser until the game is over, so players cannot cheat by
inspecting the page.
"""
import csv
import os
import random
import re
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "hangman.db"))
WORDS_CSV = os.path.join(BASE, "data", "words.csv")

# Difficulty settings: wrong guesses allowed, and score multiplier.
LEVELS = {
    "easy":   {"max_attempts": 8, "multiplier": 1},
    "medium": {"max_attempts": 6, "multiplier": 2},
    "hard":   {"max_attempts": 5, "multiplier": 3},
}

app = Flask(__name__, static_folder="static", static_url_path="/static")

SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    word             TEXT NOT NULL UNIQUE,
    difficulty       TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
    length           INTEGER NOT NULL,
    difficulty_score INTEGER NOT NULL,
    freq             INTEGER NOT NULL DEFAULT 0,
    category         TEXT
);
CREATE INDEX IF NOT EXISTS idx_words_difficulty ON words(difficulty);

CREATE TABLE IF NOT EXISTS game_sessions (
    id            TEXT PRIMARY KEY,
    word_id       INTEGER NOT NULL REFERENCES words(id),
    difficulty    TEXT NOT NULL,
    guessed       TEXT NOT NULL DEFAULT '',
    wrong_count   INTEGER NOT NULL DEFAULT 0,
    max_attempts  INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'playing' CHECK (status IN ('playing','won','lost')),
    score         INTEGER NOT NULL DEFAULT 0,
    player_name   TEXT,
    created_at    TEXT NOT NULL,
    finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_board ON game_sessions(player_name, score DESC);
"""


# ---------------------------------------------------------------- database helpers
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and load the vocabulary from data/words.csv the first time the app starts."""
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM words").fetchone()[0] == 0:
        with open(WORDS_CSV, newline="") as fh:
            rows = [(r["word"], r["difficulty"], int(r["length"]), int(r["difficulty_score"]), int(r["freq"]))
                    for r in csv.DictReader(fh)]
        db.executemany(
            "INSERT OR IGNORE INTO words (word, difficulty, length, difficulty_score, freq) VALUES (?,?,?,?,?)", rows)
        db.commit()
    db.close()


# ---------------------------------------------------------------- game logic
def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def masked(word, guessed):
    return [c if c in guessed else None for c in word]


def potential_score(difficulty, length, remaining):
    """
    SCORING FORMULA (also written in REPORT.md):
        score = M x (100 + 10 x L + 25 x R)
    M = difficulty multiplier (Easy 1, Medium 2, Hard 3), L = word length, R = wrong guesses still unused.
    A lost game scores 0.
    """
    return LEVELS[difficulty]["multiplier"] * (100 + 10 * length + 25 * remaining)


def public_state(row, word):
    guessed = row["guessed"]
    remaining = row["max_attempts"] - row["wrong_count"]
    state = {
        "game_id": row["id"],
        "difficulty": row["difficulty"],
        "length": len(word),
        "pattern": masked(word, guessed),
        "guessed": list(guessed),
        "wrong_letters": [c for c in guessed if c not in word],
        "max_attempts": row["max_attempts"],
        "remaining": remaining,
        "status": row["status"],
        "score": row["score"] if row["status"] != "playing" else potential_score(row["difficulty"], len(word), remaining),
        "saved": row["player_name"] is not None,
    }
    if row["status"] != "playing":
        state["word"] = word  # only revealed once the game is over
    return state


def load_game(game_id):
    db = get_db()
    row = db.execute("SELECT * FROM game_sessions WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        return None, None
    word = db.execute("SELECT word FROM words WHERE id = ?", (row["word_id"],)).fetchone()["word"]
    return row, word


@app.post("/api/game/new")
def new_game():
    data = request.get_json(silent=True) or {}
    difficulty = str(data.get("difficulty", "")).lower()
    if difficulty not in LEVELS:
        return jsonify(error="Choose Easy, Medium or Hard."), 400
    db = get_db()
    # Random word of the chosen difficulty. Selecting a random row position keeps this fast for large tables.
    count = db.execute("SELECT COUNT(*) FROM words WHERE difficulty = ?", (difficulty,)).fetchone()[0]
    pick = db.execute("SELECT id FROM words WHERE difficulty = ? LIMIT 1 OFFSET ?",
                      (difficulty, random.randrange(count))).fetchone()
    game_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO game_sessions (id, word_id, difficulty, max_attempts, created_at) VALUES (?,?,?,?,?)",
        (game_id, pick["id"], difficulty, LEVELS[difficulty]["max_attempts"], now()))
    db.commit()
    row, word = load_game(game_id)
    return jsonify(public_state(row, word))


@app.post("/api/game/<game_id>/guess")
def guess(game_id):
    row, word = load_game(game_id)
    if row is None:
        return jsonify(error="Game not found."), 404
    if row["status"] != "playing":
        return jsonify(error="This game is already finished.", **public_state(row, word)), 409
    letter = str((request.get_json(silent=True) or {}).get("letter", "")).lower()
    if not re.fullmatch(r"[a-z]", letter):
        return jsonify(error="Guess a single letter from A to Z."), 400

    guessed, wrong, status, score = row["guessed"], row["wrong_count"], "playing", 0
    duplicate = letter in guessed
    if not duplicate:                       # repeated guesses never cost an attempt
        guessed += letter
        if letter not in word:
            wrong += 1
        if all(c in guessed for c in word):
            status = "won"
            score = potential_score(row["difficulty"], len(word), row["max_attempts"] - wrong)
        elif wrong >= row["max_attempts"]:
            status = "lost"
        db = get_db()
        db.execute("UPDATE game_sessions SET guessed=?, wrong_count=?, status=?, score=?, finished_at=? WHERE id=?",
                   (guessed, wrong, status, score, now() if status != "playing" else None, game_id))
        db.commit()
        row, word = load_game(game_id)
    out = public_state(row, word)
    out["duplicate"] = duplicate
    out["hit"] = letter in word
    return jsonify(out)


@app.post("/api/game/<game_id>/score")
def save_score(game_id):
    row, word = load_game(game_id)
    if row is None:
        return jsonify(error="Game not found."), 404
    if row["status"] == "playing":
        return jsonify(error="Finish the game before saving a score."), 409
    if row["player_name"] is not None:
        return jsonify(error="This score was already saved."), 409
    name = re.sub(r"\s+", " ", str((request.get_json(silent=True) or {}).get("name", ""))).strip()
    if not 1 <= len(name) <= 20:
        return jsonify(error="Enter a name between 1 and 20 characters."), 400
    db = get_db()
    db.execute("UPDATE game_sessions SET player_name = ? WHERE id = ?", (name, game_id))
    db.commit()
    rank = db.execute(
        "SELECT COUNT(*) + 1 FROM game_sessions WHERE player_name IS NOT NULL AND score > ?",
        (row["score"],)).fetchone()[0] if row["score"] > 0 else None
    return jsonify(saved=True, name=name, score=row["score"], rank=rank)


@app.get("/api/leaderboard")
def leaderboard():
    difficulty = request.args.get("difficulty", "all").lower()
    sql = ("SELECT s.player_name AS name, s.score, s.difficulty, s.finished_at AS date, "
           "(SELECT length FROM words w WHERE w.id = s.word_id) AS length "
           "FROM game_sessions s WHERE s.status = 'won' AND s.player_name IS NOT NULL")
    args = []
    if difficulty in LEVELS:
        sql += " AND s.difficulty = ?"
        args.append(difficulty)
    sql += " ORDER BY s.score DESC, s.finished_at ASC LIMIT 50"
    rows = get_db().execute(sql, args).fetchall()
    return jsonify([{"rank": i + 1, **dict(r)} for i, r in enumerate(rows)])


@app.get("/api/stats")
def stats():
    db = get_db()
    per = {r["difficulty"]: r["n"] for r in db.execute("SELECT difficulty, COUNT(*) n FROM words GROUP BY difficulty")}
    return jsonify(total_words=sum(per.values()), words_by_difficulty=per, levels=LEVELS)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


init_db()

if __name__ == "__main__":
    # host 0.0.0.0 lets other devices on the same Wi-Fi open the game via your computer's IP address.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
