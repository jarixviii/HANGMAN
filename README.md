# Lamplight Hangman

Web Hangman game with 7,149-word database, three difficulty levels, scoring and a top-50 leaderboard.
Python 3 + Flask + SQLite. Full explanation, formulas and data model are in **REPORT.md**.

## Files

```
app.py              backend: database, game rules, scoring, API
data/words.csv      the vocabulary (loaded into the database on first start)
static/             the web page (index.html, style.css, app.js)
tools/build_words.py how the word list and difficulty tags were produced
tests_smoke.py      automated tests
requirements.txt, Procfile, wsgi.py   hosting files
```

## 1. Run on your own computer

```
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The file `hangman.db` is created automatically on first start.
To let a phone on the same Wi-Fi open it, find your computer's IP address (for example 192.168.1.20) and visit `http://192.168.1.20:5000`.

Run the tests with `python tests_smoke.py`.

## 2. Put it online with a public URL (PythonAnywhere, free)

The assignment needs a URL that works from another device. PythonAnywhere is recommended because its disk is permanent, so your leaderboard is not erased. (Many free hosts wipe files on restart, which would delete scores.)

1. Create a free "Beginner" account at pythonanywhere.com. Your site will be `https://YOURUSERNAME.pythonanywhere.com`.
2. Go to **Files**, create a folder `hangman`, and upload everything from this project (you can upload the zip and unzip it in a **Bash console** with `unzip hangman.zip`).
3. Go to the **Web** tab, click **Add a new web app**, choose **Manual configuration**, then pick the newest Python 3 version offered.
4. On the Web tab, click the link to the **WSGI configuration file**, delete its contents and paste:

```python
import sys
path = '/home/YOURUSERNAME/hangman'
if path not in sys.path:
    sys.path.insert(0, path)
from app import app as application
```

5. On the Web tab, set **Source code** to `/home/YOURUSERNAME/hangman`.
6. If Flask is not already available, open a Bash console and run `pip install --user flask`.
7. Click the green **Reload** button, then open your URL.

Notes:
* Free PythonAnywhere web apps expire after one month without being extended. Log in and use the **Run until 1 month from today** button on the Web tab shortly before your demonstration (the deadline is 9 November 2026).
* If something fails, the **Error log** link on the Web tab shows the exact message.
* To start with an empty leaderboard before the demo, delete `hangman.db` and click Reload. It is recreated with all words.

### Other hosts
Render, Railway or Fly.io also work (`Procfile` is included), but you must attach a persistent disk/volume and set the environment variable `DB_PATH` to a path on it, otherwise scores are lost when the app restarts.
