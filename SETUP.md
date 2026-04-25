# NC Festivals Auto-Update Pipeline
## Setup Guide — Step by Step

---

## What This Does
Every **Thursday at 9 AM Eastern**, GitHub Actions automatically:
1. Scrapes 3 NC festival websites for new events
2. Asks Claude to compare against your current list
3. Opens a **Pull Request** with proposed additions for your review
4. You merge the PR → run `apply_updates.py` → done

You stay in control. Nothing changes without your approval.

---

## Step 1: Create a GitHub Account (if needed)
Go to https://github.com and sign up. Free account is all you need.

---

## Step 2: Create a New Repository

1. Go to https://github.com/new
2. Name it: `nc-festivals-2026`
3. Set to **Public** (required for free GitHub Pages hosting)
4. Click **Create repository**

---

## Step 3: Get a Claude API Key (if needed)

1. Go to https://console.anthropic.com
2. Sign up / log in
3. Go to **API Keys** → **Create Key**
4. Copy the key — you won't see it again

**Cost estimate:** Each weekly run uses ~$0.05–0.15 in API credits.
Free tier should cover several months.

---

## Step 4: Add Your API Key as a GitHub Secret

1. In your GitHub repo, click **Settings**
2. Left sidebar → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: paste your API key
6. Click **Add secret**

---

## Step 5: Upload Your Files

Upload these files to the **root** of your repository:
- `nc-festivals-2026.html` ← your app
- `update_festivals.py`
- `apply_updates.py`

And this file to `.github/workflows/`:
- `.github/workflows/weekly-festival-update.yml`

**Easiest way:** Drag and drop in the GitHub web interface, or use GitHub Desktop (free app).

---

## Step 6: Enable GitHub Pages (host your app online)

1. In your repo, click **Settings**
2. Left sidebar → **Pages**
3. Source: **Deploy from a branch**
4. Branch: `main` / folder: `/ (root)`
5. Click **Save**

In ~2 minutes your app will be live at:
`https://YOUR-USERNAME.github.io/nc-festivals-2026/`

Share this URL — it works great as a PWA on iPad (tap Share → Add to Home Screen).

---

## Step 7: Test the Workflow Manually

1. In your repo, click **Actions** tab
2. Click **Weekly Festival Update**
3. Click **Run workflow** → **Run workflow**
4. Watch it run (takes ~1–2 minutes)
5. If new festivals were found, a Pull Request appears in the **Pull requests** tab

---

## Weekly Workflow (After Setup)

**Every Thursday:**
1. GitHub emails you: "PR opened — X new festivals found"
2. Open the PR, read the report
3. 🟢 High confidence = probably safe to merge
4. 🟡 Medium = check the source URL quickly
5. 🔴 Low confidence = verify manually before including
6. Click **Merge pull request**
7. On your computer, run: `python apply_updates.py`
8. Commit and push the updated HTML

**If nothing was found:** No PR is created, you get no email. Easy week.

---

## Running apply_updates.py Locally

```bash
# Preview changes without writing anything
python apply_updates.py --dry-run

# Apply high + medium confidence festivals
python apply_updates.py

# Apply everything including low-confidence
python apply_updates.py --include-low
```

---

## Troubleshooting

**Action fails with API error:**
Check that your `ANTHROPIC_API_KEY` secret is set correctly in repo Settings.

**No PR even though festivals exist:**
The scraper may not have found them. You can manually run `update_festivals.py` locally with your API key set as an environment variable.

**Festival appears twice:**
The apply script checks for duplicates by name. If it slipped through, open the HTML and delete the duplicate entry manually.

**Want to add more sources?**
Edit the `SOURCES` list in `update_festivals.py`.

---

## Files Reference

| File | Purpose |
|------|---------|
| `nc-festivals-2026.html` | Your app — the live file |
| `update_festivals.py` | Scraper + Claude analysis (runs in GitHub Actions) |
| `apply_updates.py` | Patches the HTML with approved updates (run locally) |
| `.github/workflows/weekly-festival-update.yml` | Schedules the Thursday automation |
| `festival_update_report.json` | Weekly report (auto-generated, gitignored) |

---

*Built with Claude · NC Festivals 2026*
