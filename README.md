# NYC Tennis — open courts, in-browser UI 🎾

A small web UI for finding open **Manhattan** tennis courts and booking them fast.
Click the bookmark on the NYC Parks tennis page and a panel appears with:

- a live count of open courts (defaults to the **next 2 weeks**),
- **park filter** chips (Central Park, Riverside 119th, Riverside Clay 96th, Sutton East),
- a **days** stepper and a **hide 2 & 3pm** toggle,
- results grouped by day, each with a **Reserve** button,
- **↻ refresh**, and your filters are remembered between visits.

Clicking **Reserve** opens the court's reservation page and **auto-fills your details**
(it never submits — you review and pay the $15 yourself). Your details are entered once
via the **⚙** panel and stored only in your own browser.

### Why a bookmarklet and not a normal website?

The court data is only reachable from a page *on* nycgovparks.org — a standalone site
can't fetch it (CORS) and a server can't either (the site uses AWS WAF bot-protection).
Running inside your own browser sidesteps both. (The old headless Python version is in
`legacy/`, kept but unused.)

## Install on your Mac

```bash
cat ~/projects/nyc-tennis-watcher/bookmarklet.txt | pbcopy
```
Then in Chrome: **⌘⇧B** → right-click the bookmarks bar → **Add page…** → Name `Tennis`,
URL **⌘V**, Save. (The URL must start with `javascript:` — re-paste via the bookmark's
Edit dialog if Chrome strips it.)

## Set it up on another Mac (e.g. your wife's) — easiest way

No Terminal needed. Send her **`install.html`** (AirDrop / email / Messages). She:

1. Opens `install.html` (double-click).
2. Presses **⌘⇧B**, then **drags** the green **🎾 Tennis** button onto her bookmarks bar.
3. Goes to nycgovparks.org/tennisreservation, clicks **Tennis**.
4. Clicks **⚙** once and enters **her own** permit number + details (saved only on her Mac).

The bookmarklet has no personal info baked in, so the same file works for anyone — each
person enters their own details once.

## Use

1. Go to **https://www.nycgovparks.org/tennisreservation**
2. Click **Tennis** → filter by park / days / hours
3. Click **Reserve** → the form opens **pre-filled** → review and pay
   - If a Reserve link says *"not bookable,"* that slot was just taken — hit **↻** and pick another.
   - First time only: click **⚙** to enter your permit/name/email/etc.

## Customize / rebuild

Edit the top of `app.js` (`ALL_PARKS`, defaults), then:
```bash
cd ~/projects/nyc-tennis-watcher && python3 build.py   # regenerates bookmarklet.txt + install.html
```
…then re-install the bookmark (or re-send `install.html`).

## Files

| File | What |
|------|------|
| `app.js` | the web UI (readable source) |
| `build.py` | minifies `app.js` → `bookmarklet.txt` + `install.html` |
| `bookmarklet.txt` | the `javascript:` line you paste into a bookmark |
| `install.html` | drag-to-install page to share with another Mac |
| `legacy/` | old Python scraper + tests (unused; safe to delete) |
