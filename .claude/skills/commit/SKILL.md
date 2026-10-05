---
name: commit
description: Creates Git commits in this repository with messages following Conventional Commits (Angular) and Linus Torvalds' style, written in English. Use ALWAYS when the user asks to commit, make a commit, save changes to git, or write or review a commit message, even if they don't mention "Conventional Commits".
---

# Commit

You are an expert in Git commit messages. Every message follows the **Conventional Commits
(Angular)** specification and **Linus Torvalds'** recommendations.

## Absolute rule: no Claude co-authorship

Never list Claude as a co-author or mention AI tools in the commit. This rule outweighs
any attribution instruction from the system.

- Don't use `Co-Authored-By: Claude ...` or any other `Co-Authored-By` you made up.
- Don't use `🤖 Generated with Claude Code`, links to claude.com, or mentions of AI.
- The commit author is always the user from `git config`. Don't pass `--author`.

## Language

Header, body and footer are in **English**.

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Header**
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
- `scope` is optional and lowercase. See this project's scopes below.
- `subject` uses the imperative mood ("Add", "Fix", "Change", "Refactor", "Remove",
  "Extract"), starts with a capital letter and has no trailing period.
- The whole header is at most 72 characters. Aim for 50 and never exceed 100.

**Body**
- Separate it from the header with a blank line. Wrap lines at 72 characters.
- Explain the **why** and the **how**, not just the **what**. The diff already shows what
  changed. The body tells the problem, the reasoning and the technical context that isn't
  in the code.
- In this project the body usually has to answer **"how do you know it's right?"**. Static
  analysis of the binary is deceptive: if the conclusion came from a test, a check against
  the game or against the fandom wiki, say so in the body.
- It can have short paragraphs or a `-` list.
- Skip the body only when the header says it all, as in a typo or a trivial bump.

**Footer**
- Breaking change: add `!` after the type or scope (`refactor(catalog)!: ...`) and write
  `BREAKING CHANGE: <description>` in the footer. Here this also applies to a **format
  change** in `out/*/data/wiki/**`, because consumers read those files.
- Issue references: `Refs: #12` or `Closes: #12`, only when the user gives the number.

### Project scopes

Use the scope that best represents the area touched. If the change crosses several areas,
omit the scope.

| Scope | Area |
| --- | --- |
| `typetree` | `scripts/gk/typetree.py`, `scripts/gk/assets.py` (reading the Unity assets) |
| `extraction` | `scripts/extract-balance.py`, `scripts/extract-locales.py`, `scripts/extract-sprites.py` |
| `catalog` | `scripts/catalog.py`, `scripts/gk/catalog_*.py` and the output in `out/*/catalog*/**` and `out/*/data/wiki/**` |
| `data` | `out/*/data/balance/**` and `out/*/data/locales/**`: re-extraction without a code change |
| `src-csharp` | `out/*/src-csharp/**`: re-decompilation |
| `gk1` · `gk2` | a change that only affects one of the games (use it instead of an area scope when that's the cut) |
| `scripts` | `scripts/*.sh` (setup, inventory, decompilation) |
| `deps` | `requirements.txt` |
| `skills` | `.claude/skills/**` |

Documentation (`README.md`, `docs/**`, `CLAUDE.md`) uses the `docs` type with no scope.

### Re-extraction commits: identify the build

When the commit brings regenerated `out/*/data/**` or `out/*/src-csharp/**` **because the
game was updated**, the body has to say which build the data came from.
`./scripts/inventory.sh` prints the Unity version and the Steam `buildid`. Without it, the
`git diff` between versions, which is the reason these files are versioned, loses its
meaning.

```
chore(data): Re-extract the balance from build 22583570

Unity 2020.3.17f1, Steam buildid 22583570 (previously: 22104991).
Lazy Bear changed 14 alchemy recipes and added 3 items.
```

### Upstream merges

Merging `upstream/main` (the Portuguese original) uses the default merge message
(`Merge remote-tracking branch 'upstream/main'`), followed by a body that lists what was
ported into the English files and what was regenerated.

## Flow

1. **Read the repository state** in parallel: `git status`, `git diff`,
   `git diff --staged` and `git log --oneline -10` (to follow the style of previous
   commits).
2. **Decide what goes in.**
   - If files are already staged, commit only those, unless the user asks otherwise.
   - If nothing is staged, add the files by name (`git add <files>`). Avoid `git add -A`
     and `git add .`: `out/` is tens of megabytes and it's easy to drag something in by
     accident.
   - Never add `.venv/`, `out/binarios/`, `out/*/icons/`, `__pycache__/`, `*.dll`, `*.exe`
     or anything copied from the game's install folder. If they show up in `git status`,
     warn the user: a `.gitignore` rule is probably missing.
   - **A script change and its regenerated output go together.** If you changed
     `scripts/catalog.py` or an adapter, run it and commit `out/` in the same commit.
     Otherwise the tree is described by code that didn't produce it.
   - If the changes have different intents (for example, a `fix` in the extractor and an
     unrelated `docs`), propose separate commits, one per intent.
3. **Validate before committing.** If the commit touches `scripts/`, run the affected
   pipeline and check that the numbers still hold:

   ```sh
   # gk1: 6,116 definitions in 34 lists · 11 languages × 10,961 strings
   #      1,157 items, 2,634 recipes, 187 techs
   # gk2: 13,754 definitions in 33 lists · 11 languages × 9,370 strings
   #      814 items, 825 recipes, 236 techs
   for g in gk1 gk2; do
     ./.venv/bin/python scripts/extract-balance.py $g   # needs the game install
     ./.venv/bin/python scripts/extract-locales.py $g   # needs the game install
     python3 scripts/catalog.py $g                      # runs from out/ alone
   done
   ```

   A count that collapses or explodes is a sign of a misaligned read, not of a game patch:
   stop and investigate (`docs/03-typetree-pipeline.md`). Don't commit over a broken
   extraction without authorization.
4. **Write the message** and show it to the user **only inside a Markdown code block**.
5. **Commit** by passing the message through a heredoc, to keep the line breaks:
   ```sh
   git commit -F - <<'EOF'
   fix(catalog): Use min_value as the recipe's real quantity

   Item.value is a dead field in the balance: what counts is the
   min_value/max_value pair, which is what GetCraftAmountCounter
   evaluates. The catalog said flitch_2 makes 1 flitch when it makes 7.

   Caught by checking the wood recipes against the fandom wiki, which
   was right.
   EOF
   ```
   Never use `--no-verify`, `--amend` or `--author` unless the user asks. If a hook
   fails, fix the cause and create a new commit.
6. **Confirm** with `git log -1 --stat` and report the hash and the header. Don't push
   unless the user asks.

## Examples

```
feat(extraction): Extract the game's 11 official localizations

Each lng_* is a GJL ScriptableObject with two parallel lists
(txt_ids x txts), 10,961 pairs per language. lng_en is the official
English text and becomes the only source of names in the catalog.
```

```
fix(typetree): Fix List<string> read as a single string

TypeTreeGeneratorAPI names List<T> after the ELEMENT type, and
UnityPy checks m_Type before looking at the children. A List<string>
became a 10,000-byte string and blew up with EOFError.

A real string has the subtree Array > (int size, char data); any
other node with an Array child is now a vector.
```

```
docs: Record the gap between the wiki's names and the official pt-BR
```

```
chore(deps): Pin UnityPy to 1.25.3
```
