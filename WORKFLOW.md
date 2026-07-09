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

## 2. Who Does What

| Person | Role | Responsibility |
|--------|------|----------------|
| **Owner (fadil013)** | Maintainer | Reviews Pull Requests, merges them into `main`, resolves conflicts, keeps `main` stable |
| **Intern A** | Agent Architecture | Works on branch `dev/agents` → folder `agents/` |
| **Intern B** | Knowledge & Tools | Works on branch `dev/rag-tools` → folders `rag/`, `tools/` |
| **Intern C** | Backend & Product | Works on branch `dev/product` → folders `backend/`, `frontend/`, `deployment/` |

---

## 3. Branch Model

```
                          main   (stable, protected — never commit here directly)
                           |
        +------------------+------------------+
        |                  |                  |
   dev/agents        dev/rag-tools       dev/product
   (Intern A)          (Intern B)         (Intern C)
```

- `main` — always working, always presentable. This is what gets graded/demoed.
- `dev/*` — one long-lived branch per person. You build here, then open a PR.

---

## 4. One-Time Setup (each intern does this once)

> First, the owner must add you as a **collaborator** (Settings → Collaborators).
> You'll get an email invite — accept it before continuing.

```bash
# 1. Clone the repository to your computer
git clone https://github.com/fadil013/multi-agent.git
cd multi-agent

# 2. Switch to YOUR branch (example: Intern A)
git checkout dev/agents

# 3. Confirm you're on the right branch
git branch          # the one with a * is your current branch
```

That's it — you now have the whole project locally and are on your own branch.

---

## 5. The Daily Workflow (each intern, every day)

```bash
# 1. Make sure you're on your branch
git checkout dev/agents

# 2. Pull the latest official work into your branch, so you don't fall behind
git pull origin main

# 3. ... do your work: write code, edit files ...

# 4. Stage your changes
git add -A

# 5. Save a snapshot with a clear message
git commit -m "Add task planner to manager agent"

# 6. Upload your branch to GitHub
git push origin dev/agents
```

Repeat steps 3–6 as often as you like. **Commit small and often.**

---

## 6. Shipping Work to `main` (Pull Requests)

When a feature is finished and working:

1. Push your branch (step 6 above).
2. Go to the repo on GitHub → you'll see a **"Compare & pull request"** button.
3. Open a **Pull Request** from `dev/agents` → `main`.
4. Write a short description of what you built.
5. The **owner reviews it**, and merges it into `main`.

Once merged, everyone else picks it up next time they run `git pull origin main`.

---

## 7. What the Owner Does

```bash
# Review pull requests on GitHub (Pull Requests tab)
# - read the changes
# - request fixes if needed
# - click "Merge pull request" when it's good

# Keep your own copy of main current
git checkout main
git pull origin main
```

The owner is the **gatekeeper of `main`**: nothing enters `main` without a merged PR.

---

## 8. Staying in Sync & Avoiding Conflicts

A **conflict** happens when two people change the same lines. To minimise them:

- **Each person owns their own folders** (see the table in §2). Stay in your lane.
- **Pull `main` into your branch daily** (`git pull origin main`).
- Communicate before touching shared files (e.g. `requirements.txt`, `docker-compose.yml`).

If you hit a conflict, Git marks the file with `<<<<<<<` / `>>>>>>>`. Edit the file
to keep the correct version, remove the markers, then:

```bash
git add -A
git commit -m "Resolve merge conflict"
git push origin dev/agents
```

---

## 9. Golden Rules

1. **Never commit directly to `main`.** Always work on your `dev/*` branch.
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
| Switch to my branch | `git checkout dev/agents` |
| See which branch I'm on | `git branch` |
| Get everyone's latest work | `git pull origin main` |
| Stage my changes | `git add -A` |
| Save a snapshot | `git commit -m "message"` |
| Upload my work | `git push origin dev/agents` |
| See what changed | `git status` |
| See history | `git log --oneline` |

---

**Summary:** interns **push** to their own `dev/*` branch and open Pull Requests;
the owner **reviews and merges** into `main`; everyone **pulls** `main` to stay in
sync. `main` is always the clean, demo-ready version.
