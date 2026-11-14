/* Hangman front end. The server owns all game rules; this file only displays state and sends guesses. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const LEVEL_NAMES = { easy: "Easy", medium: "Medium", hard: "Hard" };
  const ALPHABET = "abcdefghijklmnopqrstuvwxyz".split("");

  let game = null;          // latest state from the server
  let level = null;         // difficulty chosen by the player
  let busy = false;
  let sessionTotal = 0;
  let prevPattern = [];

  function store(key, val) { try { localStorage.setItem(key, val); } catch (e) { /* storage may be blocked */ } }
  function load(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }

  async function api(path, body) {
    const res = await fetch(path, body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok && !data.game_id) throw new Error(data.error || "Something went wrong. Try again.");
    return data;
  }

  /* ---------- views ---------- */
  function showView(name) {
    $("view-play").hidden = name !== "play";
    $("view-board").hidden = name !== "board";
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("is-active", t.dataset.view === name));
    if (name === "board") loadBoard();
  }
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showView(t.dataset.view)));

  /* ---------- building the keyboard (once) ---------- */
  const keys = $("keys");
  ALPHABET.forEach((c) => {
    const b = document.createElement("button");
    b.className = "key"; b.textContent = c; b.dataset.letter = c; b.setAttribute("aria-label", "Letter " + c.toUpperCase());
    b.addEventListener("click", () => guess(c));
    keys.appendChild(b);
  });

  /* ---------- rendering ---------- */
  function render() {
    const g = game;
    $("m-level").textContent = LEVEL_NAMES[g.difficulty];
    $("m-left").textContent = g.remaining + " of " + g.max_attempts;
    $("m-score").textContent = g.status === "playing" ? g.score : (g.status === "won" ? g.score : 0);

    // word tiles
    const word = $("word");
    word.textContent = "";
    g.pattern.forEach((ch, i) => {
      const t = document.createElement("div");
      t.className = "tile";
      if (ch) { t.textContent = ch; if (!prevPattern[i]) t.classList.add("pop"); }
      else if (g.status === "lost" && g.word) { t.textContent = g.word[i]; t.classList.add("miss"); }
      word.appendChild(t);
    });
    word.setAttribute("aria-label", "Word: " + g.pattern.map((c) => c || "blank").join(" "));
    prevPattern = g.pattern.slice();

    // wrong letters
    const w = $("wrong");
    w.textContent = "Wrong letters: ";
    if (g.wrong_letters.length) { const b = document.createElement("b"); b.textContent = g.wrong_letters.join(" "); w.appendChild(b); }
    else w.appendChild(document.createTextNode("none yet"));

    // keyboard
    keys.querySelectorAll(".key").forEach((k) => {
      const c = k.dataset.letter, used = g.guessed.includes(c);
      k.disabled = used || g.status !== "playing";
      k.classList.toggle("hit", used && !g.wrong_letters.includes(c));
      k.classList.toggle("miss", g.wrong_letters.includes(c));
    });

    // gallows: show proportional number of the 10 parts so every difficulty ends with a complete drawing
    const used = g.max_attempts - g.remaining;
    const shown = used === 0 ? 0 : Math.ceil((used * 10) / g.max_attempts);
    document.querySelectorAll("#gallows .part").forEach((p, i) => p.classList.toggle("on", i < shown));
    const stage = document.querySelector(".stage");
    stage.classList.toggle("lost", g.status === "lost");
    stage.classList.toggle("won", g.status === "won");

    // attempt pips
    const pips = $("pips");
    pips.textContent = "";
    for (let i = 0; i < g.max_attempts; i++) {
      const p = document.createElement("span");
      p.className = "pip" + (i < used ? " used" : "");
      pips.appendChild(p);
    }
  }

  function notice(msg) { $("notice").textContent = msg || ""; }

  /* ---------- game flow ---------- */
  async function startGame(lv) {
    if (busy) return;
    busy = true;
    try {
      level = lv;
      prevPattern = [];
      game = await api("/api/game/new", { difficulty: lv });
      $("start").hidden = true; $("game").hidden = false;
      notice("");
      render();
    } catch (e) { alert(e.message); }
    busy = false;
  }

  async function guess(letter) {
    if (!game || game.status !== "playing" || busy) return;
    busy = true;
    try {
      const res = await api("/api/game/" + game.game_id + "/guess", { letter });
      game = res;
      notice(res.duplicate ? "You already tried " + letter.toUpperCase() + ". No attempt was used." : "");
      render();
      if (game.status !== "playing") setTimeout(showEnd, 700);
    } catch (e) { notice(e.message); }
    busy = false;
  }

  document.querySelectorAll(".level").forEach((b) => b.addEventListener("click", () => startGame(b.dataset.level)));
  $("btn-new").addEventListener("click", () => startGame(level));
  $("btn-change").addEventListener("click", () => { $("game").hidden = true; $("start").hidden = false; });

  // physical keyboard
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if ($("end").open || $("view-play").hidden || $("game").hidden) return;
    if (/^[a-zA-Z]$/.test(e.key) && document.activeElement.tagName !== "INPUT") guess(e.key.toLowerCase());
  });

  /* ---------- end of game ---------- */
  function showEnd() {
    const won = game.status === "won";
    if (won) sessionTotal += game.score;
    $("m-total").textContent = sessionTotal;
    $("end-title").textContent = won ? "You solved it!" : "Out of attempts";
    $("end-word").textContent = "The word was " + game.word.toUpperCase() + ".";
    $("end-score").textContent = won ? game.score + " points" : "0 points";
    $("save-form").hidden = !won;
    $("saved-msg").hidden = true;
    $("save-err").textContent = "";
    $("btn-save").disabled = false;
    $("player").value = load("hangman-name") || "";
    $("end").showModal();
    if (won) $("player").focus();
  }

  $("save-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("player").value;
    $("btn-save").disabled = true;
    try {
      const r = await api("/api/game/" + game.game_id + "/score", { name });
      store("hangman-name", r.name);
      $("save-form").hidden = true;
      const m = $("saved-msg");
      m.textContent = "Saved. " + r.name + ", you are number " + r.rank + " on the all-time board.";
      m.hidden = false;
    } catch (err) {
      $("save-err").textContent = err.message;
      $("btn-save").disabled = false;
    }
  });
  $("btn-again").addEventListener("click", () => { $("end").close(); startGame(level); });
  $("btn-board").addEventListener("click", () => { $("end").close(); showView("board"); });

  /* ---------- leaderboard ---------- */
  let filter = "all";
  document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => {
    filter = c.dataset.filter;
    document.querySelectorAll(".chip").forEach((x) => x.classList.toggle("is-active", x === c));
    loadBoard();
  }));

  async function loadBoard() {
    const list = $("board");
    try {
      const rows = await api("/api/leaderboard?difficulty=" + filter);
      list.textContent = "";
      $("board-empty").hidden = rows.length > 0;
      rows.forEach((r) => {
        const li = document.createElement("li");
        li.className = "row" + (r.rank <= 3 ? " r" + r.rank : "");

        const left = document.createElement("div");
        if (r.rank <= 3) {
          const b = document.createElement("span");
          b.className = "badge"; b.textContent = r.rank; b.title = ["Gold", "Silver", "Bronze"][r.rank - 1];
          left.appendChild(b);
        } else {
          const n = document.createElement("span"); n.className = "rank"; n.textContent = r.rank; left.appendChild(n);
        }

        const mid = document.createElement("div");
        const name = document.createElement("span"); name.className = "name"; name.textContent = r.name;
        const sub = document.createElement("span"); sub.className = "sub";
        const when = new Date(r.date.replace(" ", "T") + "Z");
        sub.textContent = LEVEL_NAMES[r.difficulty] + ", " + r.length + " letters, " + when.toLocaleDateString();
        name.appendChild(sub); mid.appendChild(name);

        const pts = document.createElement("div"); pts.className = "pts"; pts.textContent = r.score;
        li.append(left, mid, pts);
        list.appendChild(li);
      });
    } catch (e) { list.textContent = e.message; }
  }
})();
