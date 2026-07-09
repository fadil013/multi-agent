# Team Git Workflow

This guide explains **exactly** how the team collaborates on this repository:
who does what, when to push, when to pull, and how work reaches `main`.
Read it once fully before you start.

---

## 1. The Mental Model (read this first)

- **`push`** = **upload** your commits from your computer to GitHub.
- **`pull`** = **download** the latest changes from GitHub to your computer.
- **`main`** = the single, stable, "official" version of the project.
- **Your branch** = your private workspace where you build your part safely.

> You **push** your own branch. You **pull** `main` to stay up to date with
> everyone else. Nobody edits `main` directly — changes get into `main` only
> through a **Pull Request (PR)** that the owner reviews and merges.

---

## 2. Who Owns What

| Person | Branch | Folders they own |
|--------|--------|------------------|
| **Owner — Fadil (fadil013)** | `main` | Reviews & merges every Pull Request, keeps `main` stable |
| **Danish** — Agent Architecture | `danish/agents` | `agents/` |
| **Manan** — RAG & Knowledge | `manan/rag` | `rag/` |
| **Ahmad** — Tools + Backend/Product | `ahmad/backend-tools` | `tools/`, `backend/`, `frontend/`, `deployment/`, `database/` |

---

## 3. Branch Model

```
                          main   (stable, protected - never commit here directly)
                           |
        +------------------+------------------+
        |                  |                  |
   danish/agents      manan/rag        ahmad/backend-tools
     (Danish)          (Manan)             (Ahmad)
```

- `main` — always working, always presentable. This is what gets graded/demoed.
- `<name>/<area>` — one long-lived branch per person. Build here, then open a PR.

---

## 4. One-Time Setup (each person does this once)

> First, the owner adds you as a **collaborator** (repo → Settings → Collaborators).
> You'll get an email invite — accept it before continuing.

```bash
# 1. Clone the repository to your computer
git clone https://github.com/fadil013/multi-agent.git
cd multi-agent

# 2. Switch to YOUR branch
git checkout danish/agents      # Danish
# git checkout manan/rag        # Manan
# git checkout ahmad/backend-tools   # Ahmad

# 3. Confirm you're on the right branch
git branch                      # the one with a * is your current branch
```

You now have the whole project locally and are on your own branch.

---

## 5. The Daily Workflow (each person, every day)

Replace `<your-branch>` with your own (e.g. `danish/agents`).

```bash
# 1. Make sure you're on your branch
git checkout <your-branch>

# 2. Pull the latest official work into your branch so you don't fall behind
git pull origin main

# 3. ... do your work: write code in YOUR folders ...

# 4. Stage your changes
git add -A

# 5. Save a snapshot with a clear message
git commit -m "Add task planner to manager agent"

# 6. Upload your branch to GitHub
git push origin <your-branch>
```

Repeat steps 3–6 as often as you like. **Commit small and often.**

---

## 6. Shipping Work to `main` (Pull Requests)

When a feature is finished and working:

1. Push your branch (step 6 above).
2. Open the repo on GitHub → click **"Compare & pull request"**.
3. Open a **Pull Request** from your branch → `main`, and describe what you built.
4. The **owner reviews it** and merges it into `main`.

Once merged, everyone else picks it up next time they run `git pull origin main`.

---

## 7. What the Owner Does

```bash
# Review pull requests on GitHub (Pull Requests tab):
#   - read the changes
#   - request fixes if needed
#   - click "Merge pull request" when it's good

# Keep your own copy of main current
git checkout main
git pull origin main
```

The owner is the **gatekeeper of `main`**: nothing enters without a merged PR.

---

## 8. Staying in Sync & Avoiding Conflicts

A **conflict** happens when two people change the same lines. To minimise them:

- **Everyone owns their own folders** (see §2). Stay in your lane.
- **Pull `main` into your branch daily** (`git pull origin main`).
- Communicate before touching shared files (`requirements.txt`,
  `docker-compose.yml`, `.env.example`).

If you hit a conflict, Git marks the file with `<<<<<<<` / `>>>>>>>`. Edit the
file to keep the correct version, remove the markers, then:

```bash
git add -A
git commit -m "Resolve merge conflict"
git push origin <your-branch>
```

---

## 9. Golden Rules

1. **Never commit directly to `main`.** Always work on your own branch.
2. **Pull before you start** each session (`git pull origin main`).
3. **Commit small, commit often**, with clear messages.
4. **One Pull Request per feature** — keep them focused.
5. **Stay in your own folders** to avoid conflicts.
6. **Ask before editing shared config files.**

---

## 10. Command Cheat Sheet

| I want to... | Command |
|--------------|---------|
| Get the project the first time | `git clone https://github.com/fadil013/multi-agent.git` |
| Switch to my branch | `git checkout <your-branch>` |
| See which branch I'm on | `git branch` |
| Get everyone's latest work | `git pull origin main` |
| Stage my changes | `git add -A` |
| Save a snapshot | `git commit -m "message"` |
| Upload my work | `git push origin <your-branch>` |
| See what changed | `git status` |
| See history | `git log --oneline` |

---

**Summary:** each person **pushes** to their own branch and opens Pull Requests;
the owner **reviews and merges** into `main`; everyone **pulls** `main` to stay in
sync. `main` is always the clean, demo-ready version.
