"""Automated smoke test: python tests_smoke.py  (uses a throw-away database)"""
import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
import app as A
c = A.app.test_client()

st = c.get("/api/stats").get_json()
assert st["total_words"] >= 5000, st
print("words in database:", st["total_words"], st["words_by_difficulty"])

# every difficulty returns a word of that difficulty, and the secret is hidden
for lv in ("easy", "medium", "hard"):
    g = c.post("/api/game/new", json={"difficulty": lv}).get_json()
    assert "word" not in g and g["status"] == "playing" and g["remaining"] == A.LEVELS[lv]["max_attempts"]
assert c.post("/api/game/new", json={"difficulty": "x"}).status_code == 400

def secret(gid):
    db = A.sqlite3.connect(A.DB_PATH)
    return db.execute("SELECT w.word FROM game_sessions s JOIN words w ON w.id=s.word_id WHERE s.id=?", (gid,)).fetchone()[0]

# WIN path: correct letters reveal every occurrence, duplicates are free, score formula holds
g = c.post("/api/game/new", json={"difficulty": "medium"}).get_json(); gid = g["game_id"]; w = secret(gid)
wrong = next(ch for ch in "qxzjkvw" if ch not in w)
r = c.post(f"/api/game/{gid}/guess", json={"letter": wrong}).get_json(); assert r["remaining"] == 5
r = c.post(f"/api/game/{gid}/guess", json={"letter": wrong}).get_json(); assert r["remaining"] == 5 and r["duplicate"]
first = w[0]; r = c.post(f"/api/game/{gid}/guess", json={"letter": first}).get_json()
assert all((p == first) == (ch == first) for p, ch in zip(r["pattern"], w)), "all matching occurrences revealed"
for ch in sorted(set(w)):
    r = c.post(f"/api/game/{gid}/guess", json={"letter": ch}).get_json()
assert r["status"] == "won" and r["word"] == w
assert r["score"] == 2 * (100 + 10 * len(w) + 25 * 5), r["score"]
assert c.post(f"/api/game/{gid}/guess", json={"letter": "a"}).status_code == 409
assert c.post(f"/api/game/{gid}/score", json={"name": ""}).status_code == 400
s = c.post(f"/api/game/{gid}/score", json={"name": "  Ayesha  "}).get_json(); assert s["rank"] == 1 and s["name"] == "Ayesha"
assert c.post(f"/api/game/{gid}/score", json={"name": "again"}).status_code == 409

# LOSS path
g = c.post("/api/game/new", json={"difficulty": "hard"}).get_json(); gid = g["game_id"]; w = secret(gid)
for ch in [x for x in "abcdefghijklmnopqrstuvwxyz" if x not in w][:5]:
    r = c.post(f"/api/game/{gid}/guess", json={"letter": ch}).get_json()
assert r["status"] == "lost" and r["score"] == 0 and r["word"] == w
assert c.post(f"/api/game/{gid}/guess", json={"letter": "1"}).status_code in (400, 409)

lb = c.get("/api/leaderboard").get_json(); assert len(lb) == 1 and lb[0]["name"] == "Ayesha"
print("ALL TESTS PASSED")
