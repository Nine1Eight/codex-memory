# PRODUCTION TASK — TERMUX / ANDROID SAFE

You are running inside **Termux on Android**.

Your objective is to prepare, validate, and submit my ADL strategy report for the Kaggle competition:

**Competition:** The Pokémon Company - PTCG AI Battle Challenge Strategy  
**Slug:** `pokemon-tcg-ai-battle-challenge-strategy`  
**Competition URL:**  
`https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy`

**Writeups URL:**  
`https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy/writeups`

**Track:** Main Track

**Title:**  
`ADL: Learning the Differences That Change the Outcome`

**Subtitle:**  
`AI Difference Learning for Robust Pokémon TCG Decision-Making`

---

# TERMUX SAFETY RULES

You are not running on a normal Linux desktop.

Assume:

- Android + Termux
- no root
- no systemd
- no desktop Chrome
- no Selenium
- no Playwright unless it is already proven functional
- no GUI automation assumptions
- no `/usr/bin` assumptions
- home directory is normally `$HOME`
- writable shared storage, if enabled, is normally under `$HOME/storage`
- Android browser interaction should use `termux-open-url` when available

Do not install giant browser runtimes merely to submit this report.

Do not modify Android system files.

Do not require root.

Do not run destructive commands.

Do not delete unrelated files.

Do not overwrite unrelated Kaggle credentials.

Do not print authentication secrets.

---

# 1. PREFLIGHT

Run a lightweight environment check.

Use commands compatible with Termux:

```sh
printf 'HOME=%s\n' "$HOME"
uname -a
command -v python || command -v python3 || true
command -v sha256sum || true
command -v wc || true
command -v termux-open-url || true
command -v kaggle || true
```

Do not fail merely because `kaggle` CLI is absent.

Create a workspace:

```sh
mkdir -p "$HOME/kaggle-adl-ptcg"
cd "$HOME/kaggle-adl-ptcg"
```

All files created for this task must stay inside this directory unless there is a specific reason otherwise.

---

# 2. DO NOT EXPOSE KAGGLE CREDENTIALS

Kaggle credentials may exist in locations such as:

```text
$HOME/.kaggle/kaggle.json
```

You may check whether the file exists.

You may check its permissions.

You must NOT:

```sh
cat ~/.kaggle/kaggle.json
```

Do not print:

- usernames
- API keys
- cookies
- session tokens
- authorization headers
- browser credentials

Never commit Kaggle credentials to Git.

Never copy them into the report.

Never include them in logs.

---

# 3. SAVE THE EXACT SOURCE

Create:

```text
$HOME/kaggle-adl-ptcg/pokemon_tcg_adl_strategy_writeup.md
```

The body of that file must be the **EXACT SOURCE REPORT** supplied at the bottom of this instruction.

Do not rewrite it.

Do not summarize it.

Do not improve it.

Do not replace terminology.

Do not fabricate experimental results.

Use UTF-8.

A safe Termux method is Python so that shell quoting cannot corrupt Unicode characters such as:

```text
Δ
π
λ
β
γ
→
│
▼
```

For example, implement the save operation with Python using a triple-quoted UTF-8 string.

Do not rely on complex `echo` commands for the report body.

---

# 4. VERIFY THE FILE

After writing it, calculate:

```sh
sha256sum pokemon_tcg_adl_strategy_writeup.md
wc -w pokemon_tcg_adl_strategy_writeup.md
wc -c pokemon_tcg_adl_strategy_writeup.md
```

Also use Python to calculate a second word count based on whitespace tokenization.

Print:

```text
Source path
SHA-256
Word count
Character/byte count
```

The competition has a report length constraint.

If the source exceeds the allowed word count:

- preserve the original unchanged;
- report the measured count;
- do not silently remove sections;
- do not fabricate compliance.

---

# 5. CREATE A SUBMISSION COPY

Keep the archival source immutable.

Create:

```text
pokemon_tcg_adl_strategy_submission.md
```

Initially it must be byte-identical to:

```text
pokemon_tcg_adl_strategy_writeup.md
```

Verify:

```sh
cmp -s pokemon_tcg_adl_strategy_writeup.md pokemon_tcg_adl_strategy_submission.md
```

If identical, print:

```text
SOURCE/SUBMISSION MATCH: YES
```

Otherwise stop and fix the copy.

---

# 6. OPTIONAL CLIPBOARD SUPPORT

If `termux-clipboard-set` exists, the complete submission body may be copied to the Android clipboard:

```sh
termux-clipboard-set < pokemon_tcg_adl_strategy_submission.md
```

Do not make clipboard support mandatory.

If Termux:API is not installed, continue normally.

---

# 7. KAGGLE SUBMISSION METHOD

This competition uses a **Kaggle Writeup**, not a conventional CSV prediction upload.

Therefore:

## DO NOT do this

```sh
kaggle competitions submit ...
```

for the strategy document unless Kaggle officially documents that command specifically for Writeups.

Do not pretend a conventional competition-file upload is equivalent to a Writeup.

Do not invent commands such as:

```text
kaggle writeups submit
kaggle competitions writeup
kaggle reports push
```

unless the installed official Kaggle client actually exposes and documents such functionality.

---

# 8. CHECK THE INSTALLED KAGGLE CLIENT SAFELY

If `kaggle` exists, inspect help only:

```sh
kaggle --help
```

and where appropriate:

```sh
kaggle competitions --help
```

Determine whether the **installed official client actually supports Writeup creation/submission**.

If no documented Writeup operation exists, do not attempt to reverse-engineer Kaggle's private API.

Do not POST to guessed endpoints.

Do not scrape authentication cookies.

Do not attempt CSRF-token bypasses.

Do not circumvent CAPTCHA, MFA, or account-security mechanisms.

---

# 9. ANDROID BROWSER HANDOFF

If Kaggle Writeup submission requires the website, use the user's authenticated Android browser.

If available:

```sh
termux-open-url 'https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy/writeups'
```

If `termux-open-url` is unavailable, print the URL clearly.

The required Kaggle UI operation is:

```text
Competition
    ↓
Writeups
    ↓
New Writeup
    ↓
Title
    ↓
Subtitle
    ↓
Paste exact Markdown
    ↓
Select Main Track
    ↓
Save
    ↓
Submit
```

The report body should already be available either:

1. in the generated `.md` file; or
2. in the Android clipboard if `termux-clipboard-set` was available.

---

# 10. EXISTING WRITEUP HANDLING

Before intentionally creating duplicates, check whether an existing Writeup titled:

```text
ADL: Learning the Differences That Change the Outcome
```

already exists.

If the authenticated browser shows an existing draft with this title:

- update the existing draft where appropriate;
- do not create needless duplicates.

If an already-submitted version exists:

- inspect its content;
- do not delete it blindly;
- only replace/resubmit if Kaggle's interface permits it and the supplied source needs updating.

---

# 11. CONTENT INTEGRITY

The following terminology is intentional and must remain intact:

```text
AI Difference Learning
ADL
Difference Ledger
DifferenceFusion
decision-difference credit assignment
criticality-weighted learning
graceful degradation
deck and policy co-optimization
```

Preserve mathematical expressions including:

```text
π(a | o)

D(o,a_i,a_j)

Δφ_ij

Score(a)
=
S_base(a)
+
λDθ(o,a)
-
βR(o,a)

Robust(a)
=
E[V(a)]
-
γ Var[V(a)]
```

Do not invent:

- ladder ratings
- Elo scores
- win rates
- matchup percentages
- statistical significance
- measured policy improvements
- measured deck improvements

unless they exist in real evidence supplied separately.

---

# 12. NO FAKE SUCCESS

There are three distinct states.

## State A

```text
LOCAL FILE CREATED
```

This means only that the Markdown exists locally.

## State B

```text
KAGGLE WRITEUP SAVED
```

This means Kaggle contains a saved draft.

## State C

```text
KAGGLE WRITEUP SUBMITTED
```

This means Kaggle visibly confirms the Writeup has been submitted to the competition.

Never confuse these states.

If Android browser interaction must be completed manually, state:

```text
KAGGLE WRITEUP SUBMISSION: BROWSER ACTION REQUIRED
```

Do not say it was submitted.

---

# 13. IF DIRECT SUBMISSION IS POSSIBLE

If an **official, authenticated, documented Kaggle mechanism** available in Termux supports Writeup submission, it may be used.

Before making any write operation:

1. inspect its help/schema;
2. confirm it specifically targets competition Writeups;
3. confirm competition slug;
4. confirm title;
5. confirm Main Track;
6. confirm source body;
7. execute once;
8. inspect the returned result.

Do not use undocumented internal APIs.

Do not bypass normal Kaggle authorization.

---

# 14. TERMUX-SAFE FINAL REPORT

When finished, print:

```text
=== PTCG ADL STRATEGY — TERMUX ===

Workspace:
$HOME/kaggle-adl-ptcg

Source:
pokemon_tcg_adl_strategy_writeup.md

Submission copy:
pokemon_tcg_adl_strategy_submission.md

SHA-256:
<actual hash>

Word count:
<actual count>

Competition:
pokemon-tcg-ai-battle-challenge-strategy

Track:
Main Track

Title:
ADL: Learning the Differences That Change the Outcome

Source preserved:
YES/NO

Source/submission identical:
YES/NO

Android browser opened:
YES/NO

Kaggle Writeup saved:
YES/NO/UNVERIFIED

Kaggle Writeup submitted:
YES/NO/UNVERIFIED

Submission verified:
YES/NO

Writeup URL:
<actual URL if known, otherwise UNAVAILABLE>

Blocking issue:
NONE or exact blocker

===================================
```

Only print:

```text
KAGGLE WRITEUP SUBMITTED: VERIFIED
```

when the authenticated Kaggle interface or an official supported API actually confirms it.

---

# 15. TERMUX ERROR RECOVERY

If Python is missing:

```sh
pkg install python
```

only if installation is necessary.

If `termux-open-url` exists, use it directly.

Do not install a full desktop environment.

Do not install Chromium solely for this task.

Do not start VNC.

Do not use `sudo`.

Do not use `systemctl`.

Do not assume `/tmp` behaves like desktop Linux when `$PREFIX/tmp` or the workspace can be used instead.

Do not modify `$PREFIX` packages unnecessarily.

---

# 16. COMPLETION CRITERIA

The task is complete when either:

### Successful automated path

```text
Exact source written
+
integrity verified
+
official Kaggle Writeup submitted
+
submitted status verified
```

or:

### Safe Android handoff path

```text
Exact source written
+
integrity verified
+
submission Markdown prepared
+
clipboard populated when supported
+
correct Kaggle Writeups page opened
+
remaining browser action explicitly identified
```

Never sacrifice account security merely to automate the last browser click.

---

# EXACT SOURCE REPORT

Insert the complete approved report beginning with:

```text
# ADL: Learning the Differences That Change the Outcome

## AI Difference Learning for Robust Pokémon TCG Decision-Making
```

and ending exactly with:

```text
That is the purpose of **AI Difference Learning**.
```

Use the previously approved ADL report without semantic changes.

Before submission, verify that the source begins and ends with those exact strings and that the SHA-256 remains stable after the archival file is created.
