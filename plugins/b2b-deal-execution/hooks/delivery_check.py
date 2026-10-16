"""delivery_check.py: the B2B Deal Execution plugin's Stop hook (Claude Code only; adapted in run 36B from the run 35C hook of
b2b-icp-and-customer-insight). When one of this plugin's skills ran its claim ledger (scripts/claim_ledger.py) in the current turn, it checks, before Claude stops, that the reply Claude is about to send is exactly the text the
ledger last checked, and sends Claude back with the reason when it is not:
  1. the last claim_ledger.py run of the turn is a passing `check --final` run (its first line: "claim_ledger --final: PASS, reply digest <d>");
  2. no tool that can change a file ran after it (Write, Edit, MultiEdit, NotebookEdit, or a shell command that is not a plain read);
  3. the reply's digest (the ledger's digest rule: line ends and trailing spaces ignored) is that digest. The reply is all the text Claude
     wrote after that run, joined, so a line before the checked text counts too.
Only a python run of a claim_ledger.py with --user, whose output carries this ledger's verdict line or whose path names one of the four skills, starts the check; a turn without one
is left alone, so the hook does nothing in any other conversation. It sends Claude back at most twice per turn, then lets the reply through.
What it guarantees: the final reply of the turn (the result of `claude -p`, and the last message in interactive use) and the saved files
the --final run checked. In interactive use the screen also shows any text written earlier in the turn; the skills write none.

What it reads: the Stop hook input (on standard input) and the session transcript file it names, both on this computer. What it writes: one
small counter file per session in a folder of your own in the system temporary folder (b2b-deal-claim-ledger-<user id>/), so it never sends Claude back more than twice.
It sends nothing anywhere, makes no network call and reads no environment variable. Standard library only. It always exits 0; on any error it lets the reply through.
"""
import hashlib, json, os, re, sys, tempfile

MARK = "[b2b-deal-execution claim ledger delivery check]"
MAX_SEND_BACKS = 2
READ_ONLY = re.compile(r"^\s*(cat|type|ls|dir|head|tail|wc|sha256sum|md5sum|echo|pwd|cut|sort|grep|cd|Get-Content|gc)\b[^>|;&]*$")
SPLIT = r"\|\||&&|[|;\n]"   # run 36B: "cd x && cat y" and "ls; cat y" are reads too


def reads_only(cmd):
    return all(READ_ONLY.match(s) for s in re.split(SPLIT, cmd) if s.strip())
CHANGERS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SHELLS = ("Bash", "PowerShell")
SKILLS = ("deal-review-and-close-plan", "discovery-and-buying-group", "negotiation-and-champion", "sales-sequences")
VERDICT = r"^(?:claim_ledger --final: |LEDGER (?:PASS|FAIL)\s*$|CLAIM LEDGER SCAN)"
RUN = re.compile(r"\b(?:python[0-9.]*(?:\.exe)?|py(?:\.exe)?(?:\s+-3[0-9.]*)?)\s[^|;&\n]*?(?<![\w-])claim_ledger\.py\b[^|;&\n]*--user\b")


def digest(text):
    t = "\n".join(l.rstrip() for l in (text or "").replace("\r\n", "\n").strip().splitlines())
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def body(c):
    b = c.get("content")
    b = "\n".join(y.get("text", "") for y in b if isinstance(y, dict)) if isinstance(b, list) else (b or "")
    return b.replace("\r\n", "\n")


def is_prompt(m):
    """A message the person typed (not a tool result, a compaction summary or any hook's feedback)."""
    if m.get("type") != "user" or m.get("isMeta") or m.get("isCompactSummary") or m.get("isVisibleInTranscriptOnly"):
        return False
    c = (m.get("message") or {}).get("content")
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
            return False
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return isinstance(c, str) and MARK not in c and not c.lstrip().startswith(("Stop hook feedback", "This session is being continued"))


ARGS = re.compile(r"--(answer|asset|source|user|ledger|file)[ =]+(\"[^\"]+\"|'[^']+'|[^\s;&|<>]+)")
WRITES = re.compile(r">|\btee\b|\bsed\s+(?:-[a-zA-Z]*\s+)*-i|\bcp\b|\bmv\b|Out-File|Set-Content|Add-Content|open\([^)]*['\"][wa]")
TARGET = re.compile(r"(?:>>?|\btee(?:\s+-a)?|Out-File(?:\s+-FilePath)?|Set-Content(?:\s+-Path)?)\s*(\"[^\"]+\"|'[^']+'|[^\s;&|<>()]+)")


def npath(s):
    s = str(s or "").strip("\"'").replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def args(cmd, kinds=("answer", "asset", "source", "user", "ledger", "file")):
    return [npath(v) for k, v in ARGS.findall(str(cmd)) if k in kinds]


def same(path, arg):
    path, arg = npath(path), npath(arg)
    return bool(arg) and (path == arg or path.endswith("/" + arg) or arg.endswith("/" + path.lstrip("/")))


def plain(cmd):
    """The shell command without heredoc bodies, inline code (-c "..."), quoted strings after echo or print, and stream redirects to
    another stream or /dev/null: what is left can name a file it writes (run 36B gate audit round 3, C1)."""
    c = str(cmd).replace("\r\n", "\n")
    c = re.sub(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?(?:\n\2[ \t]*(?=\n|$)|$)", r" \3", c, flags=re.S)
    c = re.sub(r"(?:-c|-Command)\s+(\"(?:[^\"\\]|\\.)*\"|'[^']*')", " ", c)
    return re.sub(r"\d?>&\d|\d?>\s*/dev/null|-Encoding\s+\S+", " ", c)


def writes(cmd):
    return bool(WRITES.search(plain(cmd)))


def targets(cmd):
    """Files a shell command writes (redirections, tee, Out-File, Set-Content), as file names with an extension; paths with a shell
    variable, and relative paths after a cd into .deal-check, are left out (they are the ledger's working files or cannot be resolved)."""
    c = plain(cmd)
    into_check = re.search(r"\bcd\s+[^;&|\n]*\.deal-check", c)
    out = []
    for x in TARGET.findall(c):
        x = npath(x)
        if not x or x.startswith(("&", "-")) or "$" in x or "%" in x or not re.search(r"\.[A-Za-z0-9]{1,5}$", x):
            continue
        if into_check and not x.startswith(("/", "~")) and ".deal-check" not in x:
            continue
        out.append(x)
    return out


def written(cmd):
    """Files a shell command writes or changes: targets(), the file a sed -i edits, the destination of cp or mv (C2: a copy of a checked file
    to somewhere else does not change it)."""
    c = plain(cmd)
    out = targets(cmd)
    for seg in re.split(SPLIT, c):
        w = seg.split()
        if w and w[0] == "sed" and any(x.startswith("-i") or (x.startswith("-") and "i" in x[1:]) for x in w[1:]):
            out += [npath(x) for x in w[1:] if not x.startswith("-") and re.search(r"\.[A-Za-z0-9]{1,5}$", x)]
        if w and w[0] == "perl" and any(x.startswith("-") and "i" in x[1:] for x in w[1:]):   # run 37B re-check 2 Z7: perl -i, like sed -i
            out += [npath(x.strip("'\"")) for x in w[1:] if not x.startswith("-") and re.search(r"\.[A-Za-z0-9]{1,5}$", x.strip("'\""))]
        if w and w[0] in ("cp", "mv") and len(w) >= 3:
            out.append(npath(w[-1]))
    # run 36B loop 1 re-check G1, run 37B close-recheck X4: python code (a heredoc body or -c) that writes a file: open(target, 'w'|'a'|'x', or
    # mode='w'), Path(...).write_text(...), p.write_text(...). A target that is a string, a name set to a string or a Path, or os.path.join of
    # strings is resolved; any other target (a loop variable, an expression) counts every file name written as a string in the code as written.
    raw = str(cmd)
    names = dict(re.findall(r"\b(\w+)\s*=\s*['\"]([^'\"\n]+)['\"]", raw))
    names.update(re.findall(r"\b(\w+)\s*=\s*(?:pathlib\.)?Path\(\s*['\"]([^'\"\n]+)['\"]\s*\)", raw))
    lits = re.findall(r"['\"]([^'\"\n]*\.[A-Za-z0-9]{1,5})['\"]", raw)

    def resolve(x):
        x = x.strip()
        m = re.fullmatch(r"(?:pathlib\.)?Path\(\s*(.+?)\s*\)", x)
        if m:
            x = m.group(1)
        m = re.fullmatch(r"os\.path\.join\((.*)\)", x)
        if m and re.fullmatch(r"\s*(?:['\"][^'\"]*['\"]\s*,?\s*)+", m.group(1)):
            return ["/".join(re.findall(r"['\"]([^'\"]*)['\"]", m.group(1)))]
        if re.fullmatch(r"['\"][^'\"]*['\"]", x):
            return [x.strip("'\"")]
        m = re.fullmatch(r"[fF]['\"]([^'\"{]*)", x.split("{")[0] if "{" in x else x)   # run 37B re-check 1 Y7: an f-string, by its literal start
        if m and m.group(1) and ("/" in m.group(1)):
            return [m.group(1) + "x"]
        if x in names:
            return [names[x]]
        return [l for l in lits if re.search(r"\.[A-Za-z0-9]{1,5}$", l)]

    def first_arg(s, i):
        depth, j = 1, i
        while j < len(s) and depth:
            depth += {"(": 1, ")": -1}.get(s[j], 0)
            j += 1
        inner = s[i:j - 1]
        parts, d, cur = [], 0, ""
        for ch in inner:
            if ch == "," and d == 0:
                parts.append(cur); cur = ""
                continue
            d += {"(": 1, ")": -1, "[": 1, "]": -1}.get(ch, 0)
            cur += ch
        parts.append(cur)
        return parts

    paths = []
    for m in re.finditer(r"\bopen\(", raw):
        parts = first_arg(raw, m.end())
        if any(re.fullmatch(r"\s*(?:mode\s*=\s*)?['\"][^'\"]*[wax][^'\"]*['\"]\s*", x) for x in parts[1:]):
            paths += resolve(parts[0])
    for m in re.finditer(r"((?:pathlib\.)?Path\([^()]*\)|\b\w+)\.write_(?:text|bytes)\(", raw):
        paths += resolve(m.group(1))
    # run 37B re-check 1 Y7: Path(...).open('w'), shutil copy or move, os.replace or os.rename: the destination is written
    for m in re.finditer(r"((?:pathlib\.)?Path\([^()]*\)|\b\w+)\.open\(", raw):
        parts = first_arg(raw, m.end())
        if any(re.fullmatch(r"\s*(?:mode\s*=\s*)?['\"][^'\"]*[wax][^'\"]*['\"]\s*", x) for x in parts):
            paths += resolve(m.group(1))
    for m in re.finditer(r"\b(?:shutil\.(?:copy\w*|move)|os\.(?:replace|rename))\(", raw):
        parts = first_arg(raw, m.end())
        if len(parts) >= 2:
            paths += resolve(parts[1])
    into_check = re.search(r"\bcd\s+[^;&|\n]*\.deal-check", raw)
    for x in paths:
        x = x.strip().strip("'\"")
        if into_check and "/" not in x:
            x = ".deal-check/" + x
        out.append(npath(x))
    return out


def turn(path):
    """The messages of the current turn: everything after the last message the person typed. Also returns the --answer and --asset
    paths of every earlier passing check --final run of the session (run 36B: a later change to them needs a new check)."""
    msgs, prompts, checked = [], 0, set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if isinstance(m, dict):
                if is_prompt(m):
                    for x in msgs:
                        c = (x.get("message") or {}).get("content")
                        for y in (c if isinstance(c, list) else []):
                            if isinstance(y, dict) and y.get("type") == "tool_use" and y.get("name") in SHELLS:
                                cmd = str((y.get("input") or {}).get("command", ""))
                                if RUN.search(cmd) and "--final" in cmd:
                                    checked.update(args(cmd, ("answer", "asset")))
                    msgs, prompts = [], prompts + 1
                else:
                    msgs.append(m)
    return msgs, prompts, checked


def decide(inp):
    msgs, prompts, checked = turn(inp["transcript_path"])
    inp["_turn"] = prompts
    calls, results, order, texts, feedback = {}, {}, [], [], -1
    for m in msgs:
        c = (m.get("message") or {}).get("content")
        if m.get("type") == "user" and not (isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c)):
            feedback = len(order)   # hook feedback or any other message in the turn: the reply starts after it
            texts = [(n, s) for n, s in texts if n > feedback]
            if isinstance(c, list):
                continue
        if not isinstance(c, list):
            continue
        for x in c:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "tool_use":
                calls[x.get("id")] = (x.get("name"), x.get("input") or {})
                order.append(x.get("id"))
            elif x.get("type") == "tool_result" and x.get("tool_use_id") in calls:
                results[x.get("tool_use_id")] = body(x)
            elif x.get("type") == "text" and m.get("type") == "assistant":
                texts.append((len(order), x.get("text", "")))
    led = [i for i in order if calls[i][0] in SHELLS and RUN.search(str(calls[i][1].get("command", "")))
           and (re.search(VERDICT, results.get(i, ""), re.M) or any(s in str(calls[i][1].get("command", "")) for s in SKILLS))]
    def changes_checked_file(i):
        """A later turn's change to the answer or a saved file an earlier check --final read (run 36B gate audits, gap 1 and R3)."""
        name, ti = calls[i]
        if name in CHANGERS:
            pth = npath(ti.get("file_path") or ti.get("notebook_path"))
            return ".deal-check/answer" in pth or any(same(pth, a) for a in checked)
        cmd = str(ti.get("command", "")).replace("\\", "/")
        return name in SHELLS and any(".deal-check/answer" in w or any(same(w, a) for a in checked) for w in written(cmd))
    if not led:
        if any(changes_checked_file(i) for i in order):
            return ("You changed the checked answer or a file it saved in this turn but did not run the claim ledger. Run claim_ledger.py check "
                    "(until LEDGER PASS) and then check --final on the changed files as your last tool call, and send exactly the text between its "
                    "BEGIN CHECKED REPLY and END CHECKED REPLY lines.")
        return None   # this plugin's ledger did not run in this turn: not ours to check
    last = led[-1]
    out = results.get(last, "")
    begin = re.search(r"^claim_ledger --final: PASS, reply digest ([0-9a-f]{16})$", out, re.M) or re.search(r"^=== BEGIN CHECKED REPLY ([0-9a-f]{16}) ===$", out, re.M)
    if "--final" not in str(calls[last][1].get("command", "")) or not begin:
        return ("The claim ledger ran in this turn, but its last run was not a passing --final run. Fix every NEEDS line, then run "
                "claim_ledger.py check --final with the same files as your last tool call (no pipe, no grep), and send as your whole reply exactly "
                "the text between its BEGIN CHECKED REPLY and END CHECKED REPLY lines.")
    read = args(calls[last][1].get("command", ""))
    read += [a for i in order[:order.index(last)] if calls[i][0] in SHELLS for a in args(calls[i][1].get("command", ""), ("file",))]
    for i in order[:order.index(last)]:   # run 36B gate audits (gap 2, R3, R4): a file saved in the turn must be one the --final run read
        name, ti = calls[i]
        paths = [npath(ti.get("file_path"))] if name in CHANGERS else (targets(ti.get("command", "")) if name in SHELLS else [])
        for pth in paths:
            if not pth or ".deal-check/" in pth or pth.startswith(".deal-check") or "/.claude/" in pth or pth.startswith("/dev/") or any(same(pth, a) for a in read):
                continue
            return (f"You saved {pth} in this turn, but the last claim_ledger.py check --final did not read it. Pass it as --asset when it is "
                    "written for the buyer or the seller to send (it must also be in the answer word for word), or as --source when it is a working "
                    "file, an export of a table already in the answer, or the seller's own file; then run check --final again as your last tool call "
                    "and send exactly the text it prints.")
    for i in order[order.index(last) + 1:]:
        name, ti = calls[i]
        if not (name in CHANGERS or (name in SHELLS and not reads_only(str(ti.get("command", ""))))):
            continue
        return (f"A tool that can change a file ({name}) ran after the last claim_ledger.py --final run, so the checked text may not be what "
                "you deliver. Run claim_ledger.py check --final again on the answer file and every saved file (--asset) as your last tool call, and send exactly "
                "the text between its BEGIN CHECKED REPLY and END CHECKED REPLY lines.")
    want = begin.group(1)
    k = order.index(last) + 1
    after = [x for n, x in texts if n >= k]   # texts written before the last feedback message were dropped above
    reply = "\n\n".join(after) if after else (inp.get("last_assistant_message") or "")
    if len(after) == 1 and inp.get("last_assistant_message") is not None:
        reply = inp["last_assistant_message"]
    if digest(reply) == want:
        return None
    return (f"Your reply is not the text the claim ledger checked (digest {want}). Send as your whole reply exactly the text between "
            f"=== BEGIN CHECKED REPLY {want} === and === END CHECKED REPLY {want} === in the last claim_ledger.py check --final output: nothing "
            "before it (no summary, no 'here it is'), nothing after it, no word or line changed. To say anything else, put it in the answer "
            "file and run check --final again.")


def main():
    try:
        raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        inp = json.loads(raw.decode("utf-8", errors="replace") or "{}")
        if not isinstance(inp, dict) or not inp.get("transcript_path"):
            return 0
        reason = decide(inp)
        uid = os.getuid() if hasattr(os, "getuid") else "user"
        d = os.path.join(tempfile.gettempdir(), f"b2b-deal-claim-ledger-{uid}")
        sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(inp.get("session_id") or "nosession"))[:80]
        p = os.path.join(d, sid + ".json")
        if reason is None:
            if os.path.exists(p):
                os.remove(p)   # the turn ends cleanly: the next turn starts a new count
            return 0
        os.makedirs(d, mode=0o700, exist_ok=True)
        if os.path.islink(d) or os.path.islink(p):
            return 0
        try:
            with open(p, encoding="utf-8") as f:
                st = json.load(f)
            n = int(st.get("n", 0)) if st.get("turn") == inp["_turn"] else 0
        except (OSError, ValueError, AttributeError, TypeError):
            n = 0
        if n >= MAX_SEND_BACKS:
            return 0
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"turn": inp["_turn"], "n": n + 1}, f)
        print(json.dumps({"decision": "block", "reason": f"{MARK} {reason}"}))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
