"""
Builds data/words.csv  (word,difficulty,length,difficulty_score,freq)

Pipeline
1. Start from the open-source Hunspell en_US dictionary (valid English words).
2. Keep only plain lowercase a-z words of 4-14 letters (no proper nouns, hyphens, apostrophes).
3. Drop words that are very rare in real-world English text. "Rare" is measured by counting how often
   each word appears in a large body of text (hundreds of MB of documentation on disk).
   Words that appear fewer than MIN_FREQ times are discarded so players are not given obscure words.
4. Remove a small block-list of offensive words (the game is for a classroom demo).
5. Assign difficulty with the documented rule (see REPORT.md):
       D = word length + sum of letter-rarity points
   Easy: D <= EASY_MAX   Medium: EASY_MAX < D <= MEDIUM_MAX   Hard: D > MEDIUM_MAX

The finished data/words.csv is already included in the project, so you do NOT need to run this
script to use the game. It is included so the vocabulary can be explained and reproduced.

Run:  python tools/build_words.py
"""
import csv, os, re, collections

DICT = "/usr/share/hunspell/en_US.dic"
TEXT_ROOTS = ["/usr/lib/python3", "/usr/share/doc", "/usr/share/texlive/texmf-dist/doc",
              "/usr/local/lib/python3.12", "/usr/share/common-licenses", "/usr/share/perl", "/usr/share/man"]
TEXT_EXT = (".txt", ".md", ".rst", ".html", ".tex", ".py", ".pod", ".pm", ".1", ".7")
MIN_FREQ = 10
EASY_MAX, MEDIUM_MAX = 8, 12

# Letter rarity points (more points = harder letter to guess in English)
RARITY = {**{c: 0 for c in "etaoinshrdlu"},
          **{c: 1 for c in "cmfywgpb"},
          **{c: 2 for c in "vk"},
          **{c: 3 for c in "jxqz"}}

BLOCK = set("""anal anus arse bitch bastard blowjob boner bugger cock crap cunt damn dick dildo fuck fucker
homo horny jizz kike nazi negro nigger orgasm penis piss porn prick pussy queer rape raped rapist sex sexy shit slut
tits whore wank cocaine heroin genital genitals vagina vulva testicle erection""".split())


def difficulty_score(w):
    return len(w) + sum(RARITY[c] for c in w)


def main():
    words = set()
    for line in open(DICT, encoding="utf-8", errors="ignore").read().splitlines()[1:]:
        w = line.split("/")[0].strip()
        if re.fullmatch(r"[a-z]{4,14}", w) and w not in BLOCK:
            words.add(w)
    freq = collections.Counter()
    for root in TEXT_ROOTS:
        for d, _, files in os.walk(root):
            for f in files:
                if f.endswith(TEXT_EXT) or f.startswith(("README", "LICENSE", "copyright")):
                    p = os.path.join(d, f)
                    try:
                        if os.path.getsize(p) > 3_000_000:
                            continue
                        freq.update(re.findall(r"[a-z]{4,14}", open(p, encoding="utf-8", errors="ignore").read().lower()))
                    except OSError:
                        pass
    rows = []
    for w in sorted(words):
        if freq[w] < MIN_FREQ:
            continue
        d = difficulty_score(w)
        level = "easy" if d <= EASY_MAX else "medium" if d <= MEDIUM_MAX else "hard"
        rows.append((w, level, len(w), d, freq[w]))
    out = os.path.join(os.path.dirname(__file__), "..", "data", "words.csv")
    with open(out, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["word", "difficulty", "length", "difficulty_score", "freq"])
        wr.writerows(rows)
    c = collections.Counter(r[1] for r in rows)
    print("total", len(rows), dict(c))


if __name__ == "__main__":
    main()
