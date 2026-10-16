#!/usr/bin/env python3
"""claim_ledger.py: the claim ledger and the asset skeletons of the B2B Deal Execution skills (standard library only).

Commands
  skeleton --type T     print the fixed skeleton of a buyer side asset. Types: champion-email, talking-points, memo,
                        objection-answers, risk-register, forward-note, buyer-email, mutual-plan, seat-map. Every line about the buyer side is a
                        "[User to add: ...]" slot; fill a slot only with the seller's own words, or leave it.
  scan  --answer F --user F [--asset F ...] [--source F ...]
                        list every sentence of the exact text you will deliver (--answer) that states something about
                        the buyer side (what a seat said, asked, saw, knows, agreed, wants, must do, owns, plans, a
                        deadline, a motive, a source, an "only" or "nobody"), every sentence of a buyer voice asset
                        (--asset, each saved to its own file and also inside the answer), and every figure.
                        --user is the seller's message saved word for word; --source is a file holding a script's
                        printed output or the text of a page opened in this session.
  check --answer F --user F --ledger F [--asset F ...] [--source F ...]
                        verify the ledger: one line per sentence the scan marked NEEDS SOURCE, in the form
                          S12 | user | "the seller's exact words"
                          S12 | script | "the script line, copied exactly"
                          S12 | page | "the words on the opened page, copied exactly"
                        A quote must appear word for word in the seller's message (user) or in a --source file
                        (script, page); every strong word of the sentence (agreed, seen, nobody, only, wants, must,
                        pilot, deadline, told, ...) must appear in its quotes; a figure must be in the seller's message
                        or a --source file. On LEDGER PASS the script prints the sha256 of the checked answer: deliver
                        the text --final prints (below), with nothing reworded, added or dropped.
  check --final ...     the same check as your last tool call before you answer: on LEDGER PASS it prints first
                        "claim_ledger --final: PASS, reply digest <d>", a digest line per file checked, and the answer between
                        "=== BEGIN CHECKED REPLY <d> ===" and "=== END CHECKED REPLY <d> ===". Your reply is exactly that text.
Statuses that need no ledger line: a "[User to add: ...]" slot, a question, a hedge ("may", "might", "worth checking",
"if", "whether", "not known"), advice to the seller that starts with a verb ("Ask ...", "Send ...") and carries no buyer
claim, a heading. Exit codes: 0 done or LEDGER PASS, 1 LEDGER FAIL, 2 a usage error or a missing file.
"""
import argparse, hashlib, io, os, re, sys

SKELETONS = {
    "champion-email": """Subject: [User to add: subject, in the champion's words]
To: [the reader the seller named]. From: [the champion the seller named].
The problem: [the problem in the seller's own words about the buyer or the problem in our words]
What we propose: [what the seller offers, as the seller described it]
What it costs: [the seller's figure, as the script printed it]
How we will measure it: [User to add: the measure we will use]
Where things stand: [User to add: the status of each review or approval, unless the seller reported it]
Risks and what reduces them: [only what the seller offered or reported or what reduces this risk]
Decision requested: [the one decision the seller asked for], by [User to add: date].""",
    "talking-points": """For: [the reader the seller named]. Said by: [the champion the seller named].
1. The problem: [the seller's own words about the buyer's problem or the problem in our words]
2. The option: [what the seller offers, as the seller described it]
3. The cost: [the seller's figure, as the script printed it]
4. The evidence: [User to add: a result measured here or a cited source; no return figure otherwise]
5. Where things stand: [User to add: the status of each review or approval, unless the seller reported it]
6. The risks: [only what the seller offered or reported or what reduces this risk]
7. The ask: [the one decision the seller asked for], by [User to add: date].""",
    "memo": """To: [the reader the seller named]. From: [the champion the seller named].
Recommendation: [the one decision the seller asked for, in one sentence]
What it is: [what the seller offers, as the seller described it]
Why now: [User to add: why now, in our words, unless the seller gave the reason]
Alternatives considered: [User to add: the options we looked at, including doing nothing]
Cost: [the seller's figure, as the script printed it]
Where things stand: [User to add: the status of each review or approval, unless the seller reported it]
Risks: [only what the seller offered or reported or what reduces this risk]
Decision requested: [the decision], by [User to add: date].""",
    "objection-answers": """For: [the champion the seller named], to answer their colleagues.
| A colleague may ask | Our answer, in our words | What could go wrong, honestly |
|---|---|---|
| [User to add: a question a colleague may ask, or one the seller reported] | [the seller's own answer, or User to add: our answer] | [User to add: the honest risk] |""",
    "risk-register": """| Risk | Likelihood, in the champion's words (never a made up percentage) | What reduces it (only what the seller offered or reported) | Owner |
|---|---|---|---|
| [User to add: a risk] | [User to add: likelihood] | [User to add: what reduces it] | [User to add: owner, a role] |""",
    "forward-note": """For: [the reader the seller named, for example the trustee or the CFO].
Points they raised: [the points the buyer raised, in the seller's words; a question stays a question; what the demo showed only if the seller said it]
What the vendor offers: [the seller's offer, with its source]
Open questions: [each question the buyer asked, still open or the answer]
Next step: [the next step as the seller named it; never "agreed" unless the seller said so], on [User to add: date].""",
    "buyer-email": """Subject: [User to add: subject]
Hi [User to add: first name],
[One point the buyer raised, as the seller reported it; a question stays a question]
[The seller's offer or proof, with its source, or nothing]
[One ask]
[User to add: your name]""",
    "mutual-plan": """Mutual plan: [the buyer as the seller described it] and [the seller]
| Milestone | Owner | Date | Status |
|---|---|---|---|
| [a step the seller named] | [the owner the seller named or owner] | [the date the seller gave, or the script's date labelled example default] | [User to add: status, unless the seller reported it] |
Signature target: [the date the seller gave, with the reason only if the seller gave it].""",
    "seat-map": """| Seat | Your words, quoted | Status, as you gave it | Usual concern of this seat (sector notes, not this person) | Question for the call |
|---|---|---|---|---|
| [a seat the seller named] | [the seller's own words, quoted] | [User to add: status, unless the seller gave it; "not known" otherwise] | [the seat's usual concern, labelled as usual] | [one question] |
| [User to add: a seat the seller did not name] | not given | not known | [usual concern] | [who is this, and are they involved?] |""",
}

STOP = set("the a an and or but of to in on at for with by from as is are was were be been being it its this that these those there their they them we our us you your i my me he she his her not no do does did have has had will would can could should may might than then so if into about over per each any all very just also more most such what which who whom whose when where why how".split())
BUYER = r"\b(?:cfo|ceo|cto|coo|cio|ciso|cro|chro|founder|head|heads|vp|director|manager|managers|controller|procurement|legal|finance|compliance|security|admin|trustee|trustees|board|champion|buyer|buyers|customer|prospect|committee|signatory|signer|signers|approver|chief|team|teams|staff|they|them|their|theirs|we|our|us|ours|nobody|everyone|everybody|anyone|someone|operations|seat|seats)\b"
HEDGE = r"\b(?:may|might|perhaps|possibly|probably|likely|unlikely|often|usually|usual|typically|whether|assumption|i assume|not known|unknown|not sure|do not know|don't know|worth checking|worth asking|could be|seems|suggests|your guess|your estimate|your assumption)\b"
CONDITIONAL = r"^(?:if|unless|once|in case|provided)\b"
QWORD = r"^(?:what|who|whom|whose|how|which|when|where|why|is|are|was|were|do|does|did|can|could|would|will|shall|should|has|have|had|may|might)\b"
NOT_GIVEN = r"\b(?:you (?:did not|didn't|have not|haven't) (?:yet )?(?:tell|told|say|said|give|gave|given|mention|mentioned|share|shared)|not given|not in your message|not decided|not known|not asked|not shown|not met)\b"
CHECKLIST = r":\s*(not met|not shown|partly shown|partly met|met|shown)\.?$"
FRAMEWORK_PARTS = r"\b(?:Need|Needs|Budget|Authority|Timeline|Metrics|Champion|Competition|Pain|Impact|Critical Event|Decision Criteria|Decision Process|Paper Process|Economic Buyer|Identify Pain)\b"
SELLER_START = r"^(?:you|your|you're|you've|you'd|i|i'm|i've|i'd|we|we're|we've|we'd|our|the script|this|that|it|it's|these|those|here|there|each|every|one|two|three|step|email|the email|the asset|the note)\b"
NEG = {"not", "never", "no", "without", "didn't", "hasn't", "haven't", "isn't", "wasn't", "weren't", "aren't", "don't", "doesn't", "won't", "cannot", "can't", "couldn't", "hadn't", "nor"}
ADVICE = r"^(?:ask|send|book|offer|confirm|check|get|use|keep|name|hold|trade|propose|find|call|tell|share|request|write|add|fill|put|run|bring|set|follow|give|don't|do|never|avoid|make|start|open|close|lead|map|test|prepare|plan|agree|decide|leave|replace|remove|price|quote|say|reply|answer|wait|try|cut|move|list|note|treat|read|draft|copy|paste|consider|frame|position|anchor|walk|escalate|loop|thank|attach|include|mention|show|label|mark|record|track|log|update|book|schedule|invite|line up|secure)\b"
PROPOSAL = r"^(?:i propose|i recommend|i suggest|i would like|i'd like|i am asking|i'm asking|we could|can we|should we|let us|let's|please)\b"
IRREG = {"seen": "see", "saw": "see", "sees": "see", "knew": "know", "known": "know", "knows": "know", "told": "tell", "tells": "tell", "said": "say", "says": "say",
         "met": "meet", "meets": "meet", "heard": "hear", "spoke": "speak", "spoken": "speak", "wrote": "write", "written": "write", "built": "build", "bought": "buy",
         "sat": "sit", "ran": "run", "chose": "choose", "chosen": "choose", "gave": "give", "given": "give"}
# class name, pattern, group key (None means each word is its own key)
STRONG = [
    ("widen", r"\b(?:only|nobody|no one|neither|none|everyone|everybody|everything|anyone|nothing|all of)\b", None),
    ("agree", r"\b(?:cleared|clears|signed off|signs off|agree|agrees|agreed|agreeing|commit|commits|committed|commitment|confirmed|accepted|accepts|promised|promises)\b", "AGREE"),
    ("say", r"\b(?:said|says|say|told|tell|tells|mentioned|mentions|mention|stated|states|raised|wrote|written|shared|quoted|explained|complained|noted)\b", "SAY"),
    ("ask", r"\b(?:asked|asks|ask|asking|requested|requests|queried)\b", "ASK"),
    ("know", r"\b(?:seen|saw|sees|knows|knew|known|aware|heard|engaged|engagement|met|replied|replies|spoke|spoken|talked|contacted|contact with|in touch|taken to|been taken|introduced you|brought you|sat in|joined|attended)\b", None),
    ("motive", r"\b(?:leverage|goal|goals|motive|worry|worried|worries|afraid|fear|fears|concern|concerned|concerns|pressure|bluff|bluffing|want|wants|wanted|prefer|prefers|preferred|keen|happy|unhappy|frustrated|tactic|interested|excited|likes|liked|backs|trusts|doubts|on board|on side|onside|ready to|stalling|stall|stalled|squeeze|blocking|blocks|blocked|resists|resisting|push back|pushing back|supportive|supports|behind us|sold on|convinced|fine with|aligned|positive|bought in|buy in|green light|green lit|greenlit|go ahead|go-ahead|okay with|ok with|endorsed|endorses|sanctioned|reads for|looks for|looks at|will look|will judge|judges the|judges it|cares about|care about|watches|will ask|asks about)\b", None),
    ("require", r"\b(?:must|has to|have to|had to|require|requires|required|requirement|need|needs|needed|insist|insists)\b", "REQUIRE"),
    ("do", r"\b(?:reviewing|reviewed|reviews|approve|approves|approved|approval|decided|decides|owns|owned|owner|using|uses|used|building|builds|built|migrating|switching|switch|evaluating|evaluated|evaluation|signs|signed|signing|signature|sign|comparing|compared|budget|budgets|runs|tested|testing|carries the most|carry the most|carries most|most work|workload|moves onto|move onto|carries the work|carries the integration|carries the load|carries the effort)\b", None),
    ("deadline", r"\b(?:deadline|deadlines|quarter|year end|month end|cut off|cutoff)\b", None),
    ("project", r"\b(?:pilot|pilots|migration|rollout|roll out|tender|rfp|project|projects|expansion|launch|poc|proof of concept|trial)\b", None),
    ("trend", r"\b(?:ramp|ramps|ramping|volumes? (?:build|grow|rise|increase)|growing|growth|scale up|scaling)\b", None),
    ("yousaid", r"\b(?:as you told me|you told me|you mentioned|you said|as you said)\b", "YOUSAID"),
    ("locate", r"\b(?:sits with|(?:sits in|belongs to|lives in)(?! (?:\w+ ){0,3}(?:email|emails|note|asset|answer|table|draft|plan|sequence|case|appendix|proposal|deck|memo|register|one pager|section|row|column|slot|list)\b)|sits partly|sits mainly|lives with|the decision is yours|decision is yours|yours to make|is yours to decide)\b", None),
    ("effect", r"\b(?:lowers|reduces|raises|cuts|removes|increases|lower|reduce)\s+(?:\w+\s+){0,2}risks?\b|\b(?:lowers|reduces|raises|cuts|removes|increases)\s+(?:\w+\s+){0,2}(?:costs?|spend|exposure|churn)\b|\btakes? (?:\w+\s+){0,2}risk off\b|\bis what decides\b|\bwhat decides whether\b", None),
    # a pain stated with its content: "pains (a; b)", "pains in the buyer's terms (a; b)", "their pain is ..." (run 36B r1 trace, DBG-3);
    # a count ("pain (three)"), a framework part ("identify pain") or a plan line ("one pain per email") is not a claim
    ("pain", r"(?<!\bidentify )\b(?:pain points|pains)\b(?=[^.(;:]{0,40}\((?:[^)]*[;,]|[^)]*$))|\bpain(?: points?)?\s*\((?!\s*(?:one|two|three|four|five|\d+|your words|their words)\s*\))(?!\s*pain\s*\d)(?!\s*(?:what|how|who|where|when|which|why)\b)|\b(?:their|the buyer's) (?:main |biggest |real |top )?pain (?:is|was)\b"
     # run 37B (close-recheck X3): "Pain: x", "Pain points: x and y", "Three pains, kept separate: (1) ...", "A pain I keep hearing ...: x"
     # (not a line about where the pains are used, "Pains not used: ...", and not a pain in the seller's quoted words)
     r"|\bpains?\b(?: points?)?(?![^.:;()\[\]]{0,48}\b(?:not used|unused|used|kept for|left out|covered|carries|without an email|without its own|per email)\b)[^.:;()\[\]]{0,48}:\s*"
     r"(?!\[|you did|you have not|you haven't|not |none\b|unknown|no \w+ (?:given|yet)|see |listed|each |every |all |email|the emails|your message|(?:the )?(?:one|two|three|four|five|six|\d+)\b|[^.]*\")\(?\w", "PAIN"),
    # run 36B r2 trace (NEG-6): a reason about the seller's own cost or margin the seller never gave
    ("ourside", r"\bcovers? our (?:cost|costs)\b|\bour (?:cost|costs|margin|margins|policy)\b", None),
    # run 37B round r1 trace (DBG-2): "both from the inbound form" credits a named source with each item it covers
    ("fromsrc", r"(?:,\s*(?:both|all|each|all three|all two)(?: of them)?\s+|\(\s*)from (?:the|their|his|her|our|its|that|this|a|an) (?:[\w'-]+ ){0,2}?(?:form|forms|post|posts|email|emails|note|call|demo|meeting|rfp|deck|brief|survey|ticket|tickets|chat|thread|review|report|reply|message)\b", "FROMSRC"),
    # run 37B round r2 trace (NEG-3): the seller's own authority stated from a role ("as founder you decide the discount"); run 38B re-check 1
    # R1 to R4: read by auth_hits() below (one key, AUTH), so this pattern never matches by itself
    ("selfauth", r"(?!x)x", None),
    # run 38B round r1 trace (NEG-7): a value judgement on a trade ("worth less than the term", "the cheapest trade for you") the seller never gave
    ("tradevalue", r"\bworth (?:less|more|little|much|a lot|nothing|far less|far more|very little)\b|\bcosts? (?:you|us|them) (?:little|nothing|less|more|very little)\b"
     r"|\b(?:cheap|cheaper|cheapest|easy|easier|easiest|costly|expensive|free|safe|safer|safest) (?:for (?:you|us) )?to (?:give|offer|trade|concede)\b"
     r"|\b(?:cheapest|cheap|cheaper|low.cost|high.value|low.value|free) (?:trade|concession|give)s?\b|\b(?:most|least|more|less) valuable\b", "VALUE"),
    # run 38B round r1 trace (NEG-3): a buyer effort clause ("when you carry the setup effort", "their team does most of the setup work")
    ("effort", r"\b(?:(?:carry|carries|carrying|carried|bear|bears|bearing|take on|takes on|taking on|handle|handles|handling|put in|puts in)\s+(?:(?:the|their|your)\s+)?"
     r"|(?:do|does|doing|carry|carries|carrying|bear|bears|take on|takes on|handle|handles)\s+)(?:(?:most of the|most|all the|all of the|much of the|the bulk of the|a lot of the|more of the|the most)\s+)"
     r"?(?:[\w-]+\s+){0,2}?(?:effort|workload|burden|heavy lifting|setup work|onboarding work|migration work|integration work|setup load|onboarding load)\b"
     r"|\b(?:do|does|doing)\s+(?:most of the|all the|all of the|much of the|the bulk of the|a lot of the|more of the|the most)\s+(?:[\w-]+\s+){0,2}?(?:work|load|lifting)\b", "EFFORT"),
    ("source", r"\b(?:according to|the form|their form|their post|as set out|as discussed|as we discussed|in my last email|as i said)\b", None),
]
PROBLEM = r"\b(?:pain|pains|problem|problems|issue|issues|worry|worried|worries|concern|concerned|complain\w*|expensive|costly|costs? (?:too much|a lot|more than|us|them|lakhs?|crores?)|high costs?|rising costs?|cost overruns?|slow|slower|delay\w*|late|miss|missed|misses|missing|error|errors|mistake\w*|wrong|fake|duplicate|fraud\w*|break|breaks|broken|manual|manually|by hand|hard|difficult|struggl\w*|fail\w*|lost|lose|losing|churn\w*|attrition|stuck|bottleneck\w*|backlog|waste\w*|only|too many|too few|not enough|can't|cannot|unable|still|leak\w*|risk|risks|gap|gaps|frustrat\w*|unhappy|takes days|takes weeks|takes hours|twice|again|re-?key\w*|re-?enter\w*|(?:don't|doesn't|do not|does not|isn't|aren't|won't|never|didn't|did not)\s+(?:\w+\s+)?(?:match|show|arrive|reach|work|tally|reconcile|load|sync|turn)\w*|mismatch\w*|no.?shows?|re-?plan\w*|overdue|penalt\w*|disput\w*|rework\w*|bounc\w*|pil\w+ up|nobody|no one|up this year|rising|spik\w*|outage\w*|downtime|stock.?outs?|write.?offs?|chargebacks?|escalat\w*|reject\w*|tak(?:e|es|ing|en) (?:\d+|a few|several|\w+) (?:minutes?|hours?|days?|weeks?))\b"
STRONG_YOUSAID = [p for c, p, _g in STRONG if c == "yousaid"][0]
STRONG_FROMSRC = [p for c, p, _g in STRONG if c == "fromsrc"][0]
NO_ADVICE = {"widen", "source", "yousaid", "fromsrc"}
ALWAYS = {"source", "fromsrc", "selfauth", "trend", "yousaid", "locate", "effect", "ourside", "tradevalue", "effort", "ownmarket"}
NO_ADVICE |= {"tradevalue"}
DIRECTION = r"\b(?:below|above|increase|increases|increased|decrease|decreases|decreased|higher|lower|short|shortfall|over|under|more|less|cut|gain|loss|rise|fall|drop|gap)\b"
MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
FIG = re.compile(r"(?<![\w.])([+\-−])?(?:(?:rs\.?|inr|usd|us\$|\$|₹|eur|€)\s*)?(\d[\d,]*(?:\.\d+)?)\s*(%|percent|per cent|lakh|lakhs|crore|crores|cr\b|k\b|million|mn\b|bn\b|billion|points?\b|pts\b|l\b|m\b)?", re.I)
NUMWORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
NUMWORDS.update({w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())})
SCALE = {"l": 1e5, "m": 1e6, "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7, "k": 1e3, "million": 1e6, "mn": 1e6, "bn": 1e9, "billion": 1e9}


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').lower()
    s = re.sub(r"[*_`]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def bare(s):
    return re.sub(r"[^a-z0-9%' ]+", " ", norm(s)).split()


def key_of(word, group):
    if group:
        return group
    w = norm(word)
    if " " in w:
        return w
    w = IRREG.get(w, w)
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    return w


def key_match(k, keys):
    if k in keys:
        return True
    if k.isupper() or " " in k or len(k) < 5:
        return False
    return any(len(q) >= 5 and not q.isupper() and (q.startswith(k) or k.startswith(q)) for q in keys)


def negated(tokens, i):
    return any(t in NEG or t.endswith("n't") for t in tokens[max(0, i - 4):i])


def polarity_ok(word, claim, quotes):
    """The strong word is negated in the claim exactly as it is in some quote that holds it."""
    k = key_of(word, None)
    ct = bare(claim)
    wt = bare(word)
    pos = [i for i in range(len(ct)) if ct[i:i + len(wt)] == wt]
    if not pos:
        return True
    want = negated(ct, pos[0])
    seen = []
    for q in quotes:
        qt = bare(q)
        for i, t in enumerate(qt):
            if key_match(key_of(t, None), {k}) or t == wt[0]:
                seen.append(negated(qt, i))
    return not seen or want in seen


def strong_hits(text):
    hits = []
    t = norm(text)
    said = [m.span() for m in re.finditer(STRONG_YOUSAID, t)]
    for cls, pat, group in STRONG:
        for m in re.finditer(pat, t):
            if cls != "yousaid" and any(a <= m.start() < b for a, b in said):
                continue
            if cls in ("say", "ask") and (re.search(r"\b(?:script|page|site|document|tool|output)\s+(?:\w+\s+)?$", t[:m.start()]) or re.search(r"(?:^|\b)(?:i|we|you|to|i'll|we'll|you'll|i'd|we'd|you'd|let|(?:i|we|you) (?:will|can|should|could|would|may|might)|(?:i|we|you) (?:don't|do not|didn't|did not|haven't|have not|never))\s+$", t[:m.start()])):
                continue   # "the script says" is not a buyer statement
            key = key_of(m.group(0), group)
            if cls == "ourside":   # run 37B (close-recheck observation): "covers our cost" and "cover our cost of onboarding" share one key, per noun
                key = "OUR " + re.search(r"(cost|margin|policy)", m.group(0)).group(1).upper()
            hits.append((cls, m.group(0), key))
    hits += auth_hits(t)
    hits += own_market_hits(t)
    return hits


# Run 38B round r1 trace (DBG-5): a first person claim about the seller's own customers, users or market ("I work with lenders", "most of our
# customers ...", "lenders like you tell us ...") needs the seller's own words, hedged or not; verify() wants a first person quote of the seller
# that names the same group.
GROUPS = (r"(?:lenders|banks|nbfcs|fintechs|insurers|companies|teams|brands|retailers|customers|clients|users|businesses|firms|startups|enterprises|"
          r"manufacturers|operators|carriers|shippers|3pls|sellers|merchants|organisations|organizations|players|cfos|ctos|cios|founders|marketers|"
          r"hospitals|schools|lawyers|agencies|distributors|exporters|logistics companies|d2c brands|saas companies|people like you|apps|platforms|marketplaces|"
          r"heads|leaders|contact cent(?:re|er)s|call cent(?:re|er)s|support teams|ops teams|sales teams|finance teams|it teams|insurtechs|telcos|"
          r"retailers|shops|stores|suppliers|vendors|partners)")   # run 39B re-check 1 gap 1
OWN_MARKET = (r"\b(?:i|we)\s+(?:(?:mostly|mainly|usually|often|already|also|typically|generally|largely|only|regularly)\s+)?(?:work with|serve|sell to|help|partner with|support|talk to|speak with|see|hear from)\s+"
              r"(?!you\b|your\b)(?:(?:many|most|several|a lot of|lots of|dozens of|hundreds of|\d+|other|indian|large|mid-?size|small|leading|top|big|the)\s+)*(?:[\w-]+\s+){0,2}?" + GROUPS + r"\b"
              r"|\b(?:our|my) (?:customers?|clients?|users?|customer base|install base|buyers?)\s+(?:are|is|include|includes|tell|told|say|said|use|love|like|want|see|saw|report|reported|get|got|cut|save|saved|typically|usually|mostly|often)\b"
              r"|\b(?:most|many|all|some|several|half|none|one|two|three|a few|the rest) of (?:our|my) (?:customers|clients|users|buyers)\b"
              r"|\b" + GROUPS + r" like (?:you|yours)\b"
              # run 39B re-check 1 gap 1: the group before the verb ("lending apps we work with", "most lenders I speak with"), and "we power ... for lenders"
              r"|\b" + GROUPS + r"\s+(?:that |who )?(?:i|we)\s+(?:(?:mostly|usually|often|also)\s+)?(?:work with|speak with|speak to|talk to|talk with|serve|sell to|see|meet|hear from|deal with)\b"
              r"|\b(?:i|we)\s+(?:power|run|handle|process|automate)\s+(?:[\w-]+\s+){0,4}?for\s+(?:(?:many|most|several|dozens of|hundreds of|\d+|other|leading|top)\s+)?(?:[\w-]+\s+){0,2}?" + GROUPS + r"\b")


def own_market_hits(t):
    # the seller's own words quoted inside a line ("the one claim is "we help schools ..."") are not a new claim; a talk track that is the whole line is
    inner = [mq.span() for mq in re.finditer(r'"[^"]{3,}"', t) if t[:mq.start()].strip(" ([") or t[mq.end():].strip(" .,;:)]")]
    return [("ownmarket", m.group(0), "OWNMARKET") for m in re.finditer(OWN_MARKET, t) if not any(a <= m.start() < b for a, b in inner)]


# Run 38B re-check 1 (R1 to R4): the seller's own authority (who decides, approves, signs off or sets the price on the seller's side) stated as fact.
# A claim is "you" with an authority verb AND a role ("as founder"), "alone", "yourself", "the one who", or an authority object (the discount,
# pricing, terms); or an authority noun that is "yours" ("the discount is your call", "you have the final say", "you are the approver"); or a label
# ("Approval path: you ..."). Advice that hands a choice back ("you decide what it is worth", "helps you decide", "you decide the floor") and
# conditions ("before you decide") are not claims. Every hit has the key AUTH, which only a seller quote in the first person that grants the
# authority clears ("I decide discounts myself", "Pricing is my call", "I sign off on every discount"); a negated quote does not.
AUTH_ROLE = r"(?:the )?(?:founder|co-?founder|ceo|owner|md|managing director)"
AUTH_VERB = r"(?:decides?|deciding|approves?|approving|sign(?:s|ing)? off(?: on)?|signs?|signing|sets?|setting|owns?|make the call|makes the call)"
AUTH_OBJ = r"(?:(?:the|your|your own|any|every|each|all|a|our) )?(?:discounts?(?!\s+(?:floor|level|ladder|range|steps?|limit)\b)|pricing(?: decisions?)?(?!\s+(?:floor|for|of)\b)|terms|deal terms|commercials|approvals?)\b"   # run 38B second look gap 4: a price, a floor or a walk away point is advice to the seller, not authority
AUTH_MARK = r"\b(?:alone|personally|yourself|on your own|by yourself|the one who|the one)\b"
AUTH_SKIP = r"\b(?:before|when|if|once|until|unless|whether|who|how|after|as soon as|so|so that|help|helps|helping|let|lets|to|what|which)\s+$"
AUTH_YOU = (r"\byou(?:'re| are)?(?:,? as " + AUTH_ROLE + r",?)?(?:\s+(?:alone|personally|can|could|will|get to|also|always|the one who|the one))*,?\s+(" + AUTH_VERB + r")\b([^.;:!?]{0,60})")
AUTH_NOUN = (r"\b(?:(?:the )?(?:discount|pricing|price|approval|decision|sign.?off|authority|discount call|pricing call|final call|call)(?: on your side| on (?:the )?discounts?| on (?:the )?pricing)?"
             r" (?:is|sits|rests|stays) (?:your call|yours|your decision|with you|up to you)\b(?! to (?:run|lead|chair|open|take|host|start)\b)"
             r"|\byou(?:'re| are)? (?:have|hold|get) (?:the )?final (?:say|call|word)\b|\bfinal (?:say|call|word) (?:is|sits|rests) with you\b"
             r"|\byou(?:'re| are) the (?:approver|final approver|decision maker|signer|sign.?off))")
AUTH_LABEL = (r"^\W*(?:the )?(?:approval(?: path)?|approver|(?:discount |pricing )?authority|sign.?off|decision maker|who (?:approves|decides|signs)[^:|?]{0,40})"
              r"\s*[:|]\s*(?:yours\b|you\b(?!\s+(?:decide|approve|set|choose)\s+(?:what|which|whether|how|if|when)\b)(?!\s+(?:may|might|could|should|would)\b))")
AUTH_DAY = r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|demo|discovery|next|first|second|kick ?off|review|weekly|tomorrow's|today's)\s+$"
SELLER_AUTH = (r"\b(?:i|we)\s+(?:(?:alone|personally|also|always|usually|can|still|myself|ourselves)\s+)?(?:decide|approve|sign off|sign|set(?! up)|own the|make the call|call the shots|have the final say|hold the final say)\b"
               r"|\bi can (?:give|offer|approve|do|discount|go up to|go to)\b[^.;]{0,40}?\b(?:myself|on my own|without (?:any )?(?:approval|sign.?off|asking))\b|\bup to [^.;]{0,20}?\b(?:is )?(?:my call|mine)\b"   # run 38B second look gap 2
               r"|\bmy (?:call|decision)\b|\bup to me\b|\bi(?:'m| am) the (?:approver|decision maker|one who (?:decides|approves|signs))\b|\b(?:i|we) (?:hold|have) (?:the )?(?:discount |pricing |approval )?authority\b")


def auth_hits(t):
    hits = []
    for m in re.finditer(AUTH_YOU, t):
        if re.search(AUTH_SKIP, t[:m.start()]):
            continue   # "before you decide", "helps you decide": a condition or advice
        rest = m.group(2) or ""
        if re.match(r"^\s*(?:what|which|how|whether|if|when|with)\b", rest):
            continue   # "you decide what it is worth": a choice handed back
        role = re.search(r"\bas " + AUTH_ROLE + r"\b", t)
        mark = re.search(AUTH_MARK, m.group(0) + rest)
        obj = re.match(r"^\s*(?:\w+\s+){0,1}?" + AUTH_OBJ, rest) and not re.match(r"^(?:sets?|setting)$", m.group(1))
        if role or mark or obj:
            hits.append(("selfauth", t[m.start():m.end(1)].strip(), "AUTH"))   # the words up to the verb (second look gap 3: the rest may be another clause)
    for m in re.finditer(AUTH_NOUN, t):
        if m.group(0).startswith("call") and re.search(AUTH_DAY, t[:m.start()]):
            continue   # "the Tuesday call is yours": a meeting
        if re.search(r"\b(?:before|when|if|once|until|unless|whether)\s+(?:\w+\s+){0,3}$", t[:m.start()]):
            continue
        hits.append(("selfauth", m.group(0).strip(), "AUTH"))
    return hits


# Run 38B round r1 trace (DRC-4): a bold heading ("**The incumbent is free and familiar.**"), a numbered heading ("3. The incumbent is free and
# familiar. ...") or a markdown heading that states something about a third party is read as a sentence; each word of its predicate must be in a quote.
HEAD_SKIP_SUBJ = r"(?:email|emails|plan|close plan|note|notes|table|draft|answer|script|score|scores|figure|figures|total|shape|step|steps|question|questions|ask|line|lines|version|sequence|structure|deal|review|summary|checklist|section|next step|ledger|template|asset|call|meeting|agenda|recap|proposal|offer|option|options|trade|trades|price|discount|map|list|order|math|result|results|rule|label|labels|stage|check|test|item|items|point|points|reply|subject|cadence|day|days|date|dates)"


def heading_claim(text):
    """The predicate words of a heading that states something about a third party, or [] when the heading states nothing that needs a source."""
    t = norm(re.sub(r"^\W*#+\s*", "", text)).strip()
    t = re.sub(r"^\d+[.)]?\s+", "", t).strip(" .!")
    if not t or t.endswith(":") or is_question(text) or "[user to add" in t or re.search(HEDGE, t) or re.search(NOT_GIVEN, t) or re.match(CONDITIONAL, t) \
            or re.match(QWORD, t) or re.match(r"^(?:what|who|how|why|where|when|which)\b", t) or re.match(ADVICE, t) or re.match(SELLER_START, t) or ":" in t:
        return []
    m = re.match(r"^(?:(?:the|their|this|that|a|an|his|her|its)\s+)?((?:[\w'-]+\s+){0,4}?)(?:is|are|was|were|has|have|had|feels|looks|seems|stays|remains|wants|needs)\s+(.+)$", t)
    if not m or not m.group(1).strip() or re.search(r"\b" + HEAD_SKIP_SUBJ + r"\s*$", m.group(1).strip()):
        return []
    return [w for w in bare(m.group(2)) if w not in STOP and len(w) >= 3 and not w.isdigit()]


TALK = set()   # sentences in a line to say (run 39B second look gap 1), filled by split_units()
EFFORT_BUYER = r"\b(?:they|their|them|theirs|buyer|buyers|buyer's|client|client's|customer|customer's|cfo|cto|ceo|coo|cio|ciso|operator|operator's|platform team|ops team|it team|procurement|finance)\b"


def effort_is_buyer(clause, word, sentence):
    """Run 39B re-check 1 gap 3: a buyer effort clause has the buyer as its subject, or "you" inside a quoted line to say (where "you" is the buyer);
    the seller's own effort ("our team handles the onboarding work") and advice are not buyer claims."""
    i = clause.find(word)
    before = clause[:i] if i >= 0 else clause
    # run 39B second look gaps 1 and 2: the subject is the words of this clause before the effort verb, after the last comma or joining word
    subj = re.split(r",|;|:|\b(?:when|while|as|because|since|where|if|so|and|but|in exchange for|for)\b", before)[-1].strip(" \"'“(")
    if not subj or re.match(r"^(?:we|our|i|my|us|we'll|we'd|we're)\b", subj):
        return False   # advice with no subject, or the seller's own give
    talk = sentence.count('"') % 2 == 1 or sentence.lstrip().startswith(('"', "“")) or sentence.rstrip().endswith(('"', "”")) or norm(sentence) in TALK
    if re.match(r"^(?:you|your)\b", subj):
        return bool(talk)   # in a line to say, "you" is the buyer
    return bool(re.search(EFFORT_BUYER, subj) or re.match(r"^(?:the|a)\s+(?:[\w-]+\s+){0,3}?(?:team|teams|department|function|staff|engineers|admins?)\b", subj))


def drops_hedge(head, body):
    """A heading that states a predicate its own body states only with a hedge ("may feel free and familiar") drops that hedge."""
    hw = heading_claim(head)
    if not hw:
        return False
    for sent in re.split(r"(?<=[.!?])\s+", body):
        n = norm(sent)
        for h in re.finditer(HEDGE, n):   # the hedge governs a word the heading states: it comes within four words before it
            near = n[h.end():].split()[:4]
            if any(re.sub(r"\W", "", x) in hw for x in near):
                return True
    return False


def auth_label(sentence):
    m = re.search(AUTH_LABEL, norm(sentence))
    return m.group(0).strip() if m else None


def numwords(text):
    """twenty percent -> 20 percent, so a seller's figure in words is found."""
    def one(m):
        a, b = m.group(1).lower(), (m.group(2) or "").lower()
        return str(NUMWORDS[a] + (NUMWORDS[b] if b else 0)) + " " + m.group(3)
    pat = r"\b(" + "|".join(NUMWORDS) + r")(?:[ -](" + "|".join(k for k in NUMWORDS if NUMWORDS[k] < 10) + r"))?\s+(percent|per cent|lakh|lakhs|crore|crores|million)\b"
    return re.sub(pat, one, text, flags=re.I)


def keys_in(text):
    ks = set()
    for _cls, _w, k in strong_hits(text):
        ks.add(k)
    for w in bare(text):   # loose keys too, so "approve" in a quote meets "approval" in a sentence
        ks.add(key_of(w, None))
    return ks


def figures(text):
    out = []
    text = numwords(re.sub(r"`[^`]*[/\\][^`]*`", " ", text))   # paths in inline code are not figures
    for m in FIG.finditer(text):
        if not m.group(3) and re.match(r"[A-Za-z0-9]|-[A-Za-z0-9]", text[m.end(2):m.end(2) + 2]):
            continue
        sign, num, unit = m.group(1), m.group(2), (m.group(3) or "").lower().strip()
        start, end = m.start(2), m.end()
        after = text[end:end + 12].lower()
        before = text[max(0, start - 12):start].lower()
        raw = num.replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        if re.match(r"\s*" + MONTHS, after) or re.search(MONTHS + r"\s*$", before):
            continue   # a date
        if re.match(r"\d{4}-\d{2}", text[start:start + 7]) or re.match(r"-\d", text[end:end + 2]):
            continue
        if not unit and not sign and (len(raw.split(".")[0]) < 4 or (1900 <= val <= 2100 and "," not in num)):
            continue   # small counts, list numbers and years are not checked
        unit = {"percent": "%", "per cent": "%", "pts": "points", "point": "points"}.get(unit, unit)
        neg = sign in ("-", "−")
        pos = sign == "+"
        out.append({"text": m.group(0).strip(), "value": val, "unit": unit, "neg": neg, "pos": pos})
    return out


def values(fig):
    v = fig["value"]
    if fig["unit"] in SCALE:
        return {round(v * SCALE[fig["unit"]], 2)}
    if fig["unit"] in ("%", "points"):
        return {round(v, 4)}
    return {round(v, 2)}


def fig_in(fig, pool):
    want = values(fig)
    for f in pool:
        if fig["unit"] in ("%", "points") and f["unit"] not in ("%", "points", ""):
            continue
        if (fig["neg"] or fig["pos"]) and (f["neg"] != fig["neg"] or not (f["neg"] or f["pos"] or fig["unit"])):
            continue
        if want & values(f) or (fig["unit"] not in ("%", "points") and want & {round(f["value"], 2)}):
            return True
        # a rounded restatement ("about 10 lakh" for 999,999.99) is the same figure within one part in a thousand
        if fig["unit"] not in ("%", "points") and any(abs(w - v) <= 0.001 * max(abs(v), 1) for w in want for v in values(f)):
            return True
    return False


def split_units(answer):
    """Sentences of the answer outside code blocks, plus the lines inside code blocks."""
    sents, blocks, fence, header = [], [], False, []
    lines = answer.splitlines()
    talk_head = False
    for li, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            if line.strip():
                blocks.append(line.strip())
            continue
        s = line.strip()
        if not s or re.fullmatch(r"[|\-: ]+", s) or re.fullmatch(r"-{3,}|\*{3,}", s):
            continue
        if not s.startswith("|"):
            header = []
        if s.startswith("#"):   # run 39B second look gap 1: lines under a heading such as "What to say" or "Opening" are lines to say
            talk_head = bool(re.search(r"\b(?:say|says|talk track|opening|script|wording|lines? to use|reply|replies|counter)\b", s, re.I))
        is_talk = talk_head or s.startswith(">") or bool(re.match(r"^(?:[-*+]\s+)?(?:\*\*)?(?:say|try|ask them|line to say|you say|reply)(?:\*\*)?\s*:", s, re.I))
        numbered = re.match(r"^\d+[.)]\s+", s)
        s = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)", "", s)
        bold = re.match(r"^(?:\*\*|__)[^*_]+?[.!](?:\*\*|__)", s)
        s = re.sub(r"\*\*|__", "", s)
        if s.startswith("|") and li + 1 < len(lines) and re.fullmatch(r"\|?[\s:|\-]+\|?", lines[li + 1].strip() or "x") and "-" in lines[li + 1]:
            header = [h.strip().lower() for h in s.strip("|").split("|")]
            continue   # a table header row
        if s.startswith("|"):
            for ci, cell in enumerate(s.strip("|").split("|")):
                if header and ci < len(header) and re.search(r"\busual", header[ci]) and cell.strip():
                    sents.append("USUAL::" + cell.strip())   # a column labelled "usual" holds the sector notes for the seat
                    continue
                if header and ci < len(header) and re.search(r"\b(?:status|stance|engagement|engaged)\b", header[ci]) and cell.strip():
                    sents.append("STATUS::" + cell.strip())
                    continue
                if cell.strip() and not re.fullmatch(r"[\-: ]+", cell.strip()):
                    sents.extend(x.strip() for x in re.split(r"(?:(?<=[.!?])|(?<=[.!?][\"'”]))\s+(?=[A-Z\[\"'(0-9“])", cell.strip()) if x.strip())
            continue
        parts = [x.strip() for x in re.split(r"(?:(?<=[.!?])|(?<=[.!?][\"'”]))\s+(?=[A-Z\[\"'(0-9“])", s) if x.strip()]
        for pi, part in enumerate(parts):
            # run 38B round r1 trace (DRC-4): a bold heading, the short first sentence of a numbered item, or a markdown heading ("## 3. The incumbent
            # is free" splits after the number) that states as fact what its own body hedges is read as a claim; the parts are the same as before
            if s.startswith("#"):
                body = []
                for nxt in lines[li + 1:li + 6]:
                    if nxt.strip().startswith("#"):
                        break
                    body.append(nxt)
                if (pi or not re.match(r"^#+\s*\d+[.)]?$", part)) and drops_hedge(re.sub(r"^#+\s*", "", part), " ".join(body)):
                    part = "HASH::" + re.sub(r"^#+\s*", "", part)
            elif pi == 0 and len(parts) > 1 and (bold or (numbered and len(part.split()) <= 8)) and drops_hedge(part, " ".join(parts[1:])):
                part = "HEAD::" + part
            if is_talk and not s.startswith("#"):
                TALK.add(norm(part))
            sents.append(part)
    return sents, blocks


def clauses(sentence):
    # a short label before a colon ("Customer data: ...") is not a claim; the text after it is
    sentence = re.sub(r"\[user to add:[^\]]*\]", "[user to add]", sentence, flags=re.I)
    parts = re.split(r"(?<=:)\s+", sentence)
    if len(parts) > 1 and parts[0].endswith(":") and len(parts[0].split()) <= 8:
        parts = parts[1:]   # only the first short label is dropped
    sentence = " ".join(parts)
    out = []
    for c in re.split(r"[;:]\s+|,\s+(?=(?:and|but|so|because|which|who|while|when|as|since|although|though)\b)|\s+(?=(?:because|while|since|although|so)\b)|\s+but\s+|\s+and\s+(?=(?:probably|likely|perhaps|possibly|usually|may|might|could|would|will|should|can|has|have|had|is|are|was|were|will|wants|said|asked|knows|agreed|signed|approved|legal|the|their|they|he|she)\b)|(?<=[?])[\"'”]?\s+|,\s+(?=(?:does|do|did|is|would|will|can|could|shall)\s+(?:that|this|it)\s+[^,]{0,30}\?[\"'”)]*\s*$)", sentence):
        if not c.strip():
            continue
        if is_question(c) and "," in c and re.match(r"^(?:since|now that|given that|as|because|after|seeing that|considering|with|when)\b", norm(c).lstrip("\"'“(")):
            lead, rest = c.split(",", 1)   # "Since your CFO has approved the budget, can we book the signing?": the lead is a statement
            out += [lead, rest]
            continue
        if re.match(CONDITIONAL, norm(c)) and "," in c:
            cond, rest = c.split(",", 1)   # "If the pilot goes well, the CFO has agreed": the condition is not a claim, the rest is
            out.append(cond)
            if not re.search(r"\b(?:will|'ll|would|'d|could|can|should|may|might)\b", norm(rest)):
                out.append(rest)
        else:
            out.append(c)
    return out


# Run 36B (close-recheck G2): in a hand off, only a status claim (signed, approved, received, live, started, was ...) outside a condition
# ("when", "once", "after", "if" ...) or a buyer side claim stops it being a plain hand off; project and deadline nouns pass.
HANDOFF_STATUS = r"\b(?:signed|approved|agreed|received|came through|cleared|went live|is live|are live|live now|is done|are done|completed|complete|started|starts|begins|began|kicked off|was|were|has been|have been|decided|reviewed|accepted|confirmed)\b"
HANDOFF_COND = r"^\W*(?:(?:hand ?offs?|next|then)\s*:?\s*)?(?:when|once|if|after|before|until|as soon as|in case|unless)\b"


def hand_off_ok(rest):
    rest = re.sub(r"\bready to (?:send|share|go|use)\b", " ", rest)
    rest = re.sub(r"\b(?:belongs?|goes|go) to\s*(?=$|[.;,])", " ", rest)
    rest = re.sub(r"\bwritten (?=(?:proposal|plan|case|summary|note|answer|reply|version|business case)\b)", " ", rest)   # "a written proposal" names a document   # "... belongs to <plugin> / <skill>": the name was taken out above
    for c in re.split(r"[;,]|\s+and\s+|\s+so\s+", rest):
        c = c.strip(" .:")
        if not c:
            continue
        cond = re.match(HANDOFF_COND, c)
        # run 36B gate audit gap 3: "after" or "before" with a past event ("after the CFO signed last Tuesday") is a status claim, not a condition
        if cond and not (re.search(r"\b(?:after|before)\b", cond.group(0)) and re.search(r"(?<!\bis )(?<!\bare )(?<!\bbe )(?<!\bbeen )(?<!\bgets )(?<!\bget )(?<!\bhas )(?<!\bhave )\b(?:signed|approved|agreed|received|cleared|decided|came through|accepted|confirmed|was|were)\b", c)):
            continue
        if re.search(HANDOFF_STATUS, c):
            return False
        hits = strong_hits(c)
        if [h for h in hits if h[0] not in ("deadline", "project", "do")]:
            return False
        if re.search(BUYER, c) and ([h for h in hits if h[0] == "do"] or re.search(r"\b(?:is|are|has|have|had|will)\b", c)):
            return False
    return True


# Run 36B (close-recheck G3): a cell of a "usual concern" column holds the sector notes for a seat. It needs a source only when it says
# something about this person: a past event (told, signed, approved ...), or a motive, agreement, knowledge or words with a person or seat
# as the subject ("the CFO wants ...", "Ravi is keen ..."). A part that opens with "whether", "if", "how", "what" or "who" asks; it passes.
USUAL_EVENT = r"\b(?:told|said|wrote|signed|signed off|approved|agreed|met|decided|confirmed|promised|asked|replied|backed|chose|picked|rejected)\b"


def usual_cell_claims(cell):
    out = []
    cell = re.sub(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s+(?:(?:the|their|our)\s+)?[^,]{1,40},", r"\1", cell.strip())   # "Ravi, the CFO, is pushing": the name is the subject
    for part in re.split(r"[;,]|\s+and\s+(?=(?:he|she|they|the|their|[a-z]+s)\b)", cell):
        raw = part.strip()
        pn = norm(raw)
        if not pn or re.match(r"^(?:whether|if|how|what|who|which|when)\b", pn):
            continue
        ev = re.search(USUAL_EVENT, pn)
        if not ev and re.search(HEDGE, pn):
            continue   # run 36B gate audit gap 4: "the CFO usually wants ..." is the sector note the skill asks for
        if ev and not re.search(r"\b(?:is|are|be|being)\s+" + re.escape(ev.group(0)) + r"\s+by\b", pn):
            out.append(ev.group(0))
            continue
        subject = re.match(r"^(?:the|their|our|his|her)\s+(?:[\w-]+\s+){0,2}?" + BUYER[2:], pn) or re.match(r"^(?:he|she|they)\b", pn) \
            or re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:is|was|has|had|wants|wanted|told|said|backs|likes|thinks|will|would|keeps|seems)\b", raw)
        hits = [h for h in strong_hits(raw) if h[0] in ("motive", "agree", "know", "say", "ask", "require", "do")]
        hits += [(None, w) for w in re.findall(r"\b(?:running|reviewing|evaluating|comparing|signing|testing|building|piloting)\b", pn) if w not in [h[1] for h in hits]]
        if subject and hits:
            out += [h[1] for h in hits]
        elif subject and re.search(r"\b(?:pushing|keen|backing|championing|driving|blocking)\b", pn):
            out.append(re.search(r"\b(?:pushing|keen|backing|championing|driving|blocking)\b", pn).group(0))
    return out


# Run 37B (close-recheck X1): a status cell that opens with a status word ("not met: ...", "engaged: ...") is read after the word.
STATUS_WORD = r"^(?:not met|partly met|partly shown|partly|met|not shown|shown|not known|not engaged|engaged|not in contact|in contact|yes|no)\s*[:;]\s*"
# a part that says what the seller's notes do not give ("no economic buyer named yet", "champion test not run") or grades it ("a potential champion")
STATUS_NOTES = r"\b(?:no|not|none|nobody|no one)\b[^;]*\b(?:named|identified|given|shown|run|tested|known|in your notes|on your notes|in your message|confirmed yet)\b|\b(?:potential|possible|candidate|at most)\b"
STATUS_OK = r"(?:not known|not known yet|not given|unknown|not shown|none given|not decided|not started|planned|proposed|suggested|sent|to be named|to be named by the buyer|open|not met|partly shown|partly met|partly|\[user to add\]|\[user to add:[^\]]*\]|\"[^\"]*\"|“[^”]*”)"
SEATS = {"cfo": r"cfo|chief financial officer", "ceo": r"ceo|chief executive(?: officer)?", "cto": r"cto|chief technology officer", "cio": r"cio|chief information officer",
         "ciso": r"ciso|chief information security officer", "chro": r"chro|chief human resources officer|chief people officer", "coo": r"coo|chief operating officer",
         "founder": r"founders?", "procurement": r"procurement", "legal": r"legal", "finance": r"finance|financial", "compliance": r"compliance", "security": r"security",
         "trustee": r"trustees?", "trustees": r"trustees?", "board": r"board", "committee": r"committee",
         "chief risk officer": r"chief risk officer|cro", "audit committee": r"audit committee", "risk committee": r"risk committee"}   # run 37B (re-check 1 Y6): "at risk" is a status, not a seat
SEAT_RE = r"\b(?:" + "|".join(SEATS) + r")\b"
CONTACT_CLAIM = r"\b(?:no contact|not (?:yet )?(?:engaged|in contact|contacted|met|reached)|in contact|engaged|silent|no reply|not replied|has not replied|have not replied|never replied|unreachable)\b"
CONTACT_WORD = r"\b(?:contact\w*|met|meet\w*|call\w*|spoke|spoken|speak\w*|talk\w*|repl\w*|joined|attended|silent|engaged|heard|demo\w*|emails?|emailed|reached|introduc\w*|sat in)\b"


def status_cell(cell):
    """None when the cell states nothing that needs a source, else the reason; status_parts() gives the parts that need it."""
    return (status_parts(cell) or [None])[0] and "status cell: " + status_parts(cell)[0][:60] if status_parts(cell) else None


def status_parts(cell):
    """The parts of a status cell that state something (run 37B re-check 1 Y1: a hedged or "not known" part is not read as a claim)."""
    v = norm(cell).strip(" .")
    if not v or re.fullmatch(STATUS_OK, v):
        return []
    rest = re.sub(STATUS_WORD, "", v)
    if rest == v:   # no status word first: any cell is a claim unless it is hedged ("possibly met: ... may be in contact") or says what the notes lack
        if (re.search(HEDGE, v) or re.search(STATUS_NOTES, v)) and not re.search(r"\b(?:agreed|approved|signed|confirmed|accepted|committed|said|told)\b", v):
            return []
        return [v]
    out = []
    subs = []
    for seg in re.split(r";", rest):   # run 37B re-check 2 Z3: a hedge or "not known" hides only its own clause
        subs += re.split(r",\s*(?:but|which|while)\s+|\s+but\s+|\s+and\s+(?=(?:may|might|could|probably|possibly|likely|perhaps|whether)\b)", seg)
    for seg in subs:
        sn = seg.strip(" .,")
        if not sn or re.fullmatch(STATUS_OK, sn) or re.search(HEDGE, sn) or re.search(NOT_GIVEN, sn) or is_question(sn) or re.match(ADVICE, sn) \
                or (re.search(STATUS_NOTES, sn) and not re.search(CONTACT_CLAIM, sn)):
            continue
        if re.search(SEAT_RE, sn) or re.search(BUYER, sn) or re.search(CONTACT_CLAIM, sn) or strong_hits(sn):
            out.append(sn)
    return out


# Run 37B (close-recheck X2): a line about what the seller's product offers or does
OWN = set()
OFFER_VERBS = (r"(?:offers?|supports?|handles?|provides?|dubs|covers|works (?:in|with)|does|integrates? (?:with|into)|connects? (?:to|with)|plugs? (?:into|in to)|can \w+|lets you|gives you|syncs? with|reads from|pulls from"
               r"|(?:also )?(?:is available in|comes with|includes?|ships|automates|translates|runs on|is built for|is certified|is compliant with))")   # run 37B re-check 1 Y3
def own_names(user):
    own = {norm(x) for x in re.findall(r"\b(?:at|from|of)\s+([A-Z][\w.-]+)", user)} | {norm(x) for x in re.findall(r"\b([A-Z][\w.-]+)\s*\(", user)}
    own |= {norm(x) for x in re.findall(r"\b(?:[Ii]|[Ww]e) sell\s+([A-Z][\w.-]+)|\b[Oo]ur (?:product|platform|tool|app) is\s+([A-Z][\w.-]+)", user) for x in x if x}   # run 37B re-check 2 Z8
    return {o.rstrip(".") for o in own if len(o) > 2}


def offer_line(text, own, context=None):
    # run 37B re-check 2 Z1: "it" is the seller's product only when the seller's own name comes earlier in the line ("Their WMS ...; it runs on Oracle" is not)
    it_ok = any(re.search(r"\b" + re.escape(o) + r"\b.*\bit\b", context or text, re.I) for o in own)
    subj = r"(?:[Ww]e|" + (r"[Ii]t|" if it_ok else "") + r"[Tt]he (?:product|platform|tool|service)|[Oo]ur (?:product|platform|tool|service)" + "".join("|" + re.escape(o) for o in sorted(own)) + r")"
    verbs = OFFER_VERBS
    _unused = (r"(?:offers?|supports?|handles?|provides?|dubs|covers|works (?:in|with)|does|integrates? (?:with|into)|connects? (?:to|with)|plugs? (?:into|in to)|can \w+|lets you|gives you|syncs? with|reads from|pulls from"
             r"|(?:also )?(?:is available in|comes with|includes?|ships|automates|translates|runs on|is built for|is certified|is compliant with))")   # run 37B re-check 1 Y3
    if re.search(r"\b(?:whether|if|asked|asks|ask)\s+" + subj + r"\s+" + verbs, text, re.I):
        return False
    return bool(re.search(r"\bwhat [\w.-]+ offers\b", text, re.I) or re.search(r"(?:^|[\s(\[\"'“])" + subj + r"\s+" + verbs + r"\b", text, re.I)
                or re.search(r"\bwith " + subj + r",? you (?:get|can)\b", text, re.I))


GENERIC = set("BANT MEDDIC MEDDPICC SPICED CHAMP GPCTBA RFP RFPs RFQ SOW MSA NDA POC PoC AP AR SOC ISO GDPR DPDP AI API APIs CRM ERP CFO CEO CTO CIO COO CISO CHRO CRO IT HR SMS PDF UI UX SaaS B2B B2C D2C KPI KPIs ROI SLA SLAs US UK EU GST TDS WMS TMS HRMS CMMS NBFC NBFCs MSME MSMEs SME SMEs OTP KYC QA CSV MIS VP".split())
DAYS = r"^(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december|i|user|add)$"


def offer_names(text, own):
    """The names (capitalised words) on an offer line other than the seller's own company and the first word of a sentence."""
    text_ns = re.sub(r"\[User to add:[^\]]*\]", lambda m: " " * len(m.group(0)), text, flags=re.I)   # a slot names nothing
    text_ns = re.sub(r"\"[^\"]{3,}\"|“[^”]{3,}”", lambda m: " " * len(m.group(0)), text_ns)   # the seller's words in quotes are checked as quotes
    out = []
    # run 37B re-check 1 Y3: names in capitals or camel case (SAP, AWS, NetSuite, S/4HANA) too; generic abbreviations are not names
    for m in re.finditer(r"(?<![\w/])([A-Z][A-Za-z0-9/-]*[A-Z0-9][A-Za-z0-9/-]*|[A-Z][a-z]{2,})\b", text_ns):
        w = m.group(1)
        if w in GENERIC:
            continue
        before = text_ns[:m.start()]
        if not before.strip() or before.strip().endswith("::") or re.search(r"[.!?:]\s*$|[\[\"'(“]$", before) or re.match(DAYS, w.lower()) or any(o.startswith(w.lower()) for o in own):
            continue
        out.append(w)
    return out


def pain_item_ok(item, iw, q):
    """Run 37B re-check 2 Z4: a pain item matches a problem quote when the item's own problem word is in the quote, or (with no problem word
    in the item) the item shares a word with the quote's problem words or most of its words with the quote; a shared actor alone is not enough."""
    qk = {key_of(x, None) for x in bare(q)}
    qk |= {k[3:] for k in qk if k.startswith("mis") and len(k) > 6} | {"mis" + k for k in qk}
    pw = {key_of(w, None) for m in re.finditer(PROBLEM, norm(item)) for w in bare(m.group(0))} - {"no", "not", "do", "does", "don't", "doesn't", "never", "didn't", "did"}
    if pw:
        return any(key_match(w, qk) for w in pw)
    span = {key_of(w, None) for m in re.finditer(PROBLEM, norm(q)) for w in bare(m.group(0))} - {"no", "not", "do", "don't"}
    hit = [w for w in iw if key_match(w, qk)]
    return any(key_match(w, span) for w in iw) or len(hit) * 3 >= len(iw) * 2


SRC_GENERIC = {"known", "already", "both", "pain", "pains", "point", "points", "item", "items", "fact", "facts", "detail", "details", "figure", "figures",
               "number", "numbers", "question", "questions", "one", "two", "three", "four", "five", "six", "given", "gave", "give", "them", "said", "told",
               "also", "here", "there", "what", "which", "these", "those", "everything", "all", "both", "each", "the", "their", "your", "you", "as", "it"}


def source_items(text, qtexts):
    """Run 37B round r1 trace (DBG-2): for each "from the <source>" in a part of the line, every item that part credits to the source (the words
    before the phrase, or after it when it opens the part, or the words before a bracket that holds it) must be in a quote that names the source."""
    problems = []
    for seg in re.split(r";|(?<=[.!?])\s+", text):
        for m in re.finditer(STRONG_FROMSRC, seg, re.I):
            noun = re.search(r"(\w+)$", m.group(0)).group(1).lower()
            sq = [q for q in qtexts if re.search(r"\b" + re.escape(noun[:5]), norm(q))]
            before = seg[:m.start()]
            if m.group(0).lstrip().startswith("("):   # "(from the form)": the words before the bracket, back to the last bracket or comma
                before = re.split(r"[),]", before)[-1]
            items = before if before.strip(" :,(") and not re.fullmatch(r"\W*", before) else seg[m.end():].split("(")[0]
            items = re.sub(r"^.*?:\s*", "", items) if ":" in items and len(items.split(":")[0].split()) <= 3 else items
            words = [w for w in bare(items) if w not in STOP and w not in SRC_GENERIC and len(w) >= 3 and not w.isdigit()]
            qk = {key_of(x, None) for q in sq for x in bare(q)}
            for w in dict.fromkeys(words):
                if not sq or not key_match(key_of(w, None), qk):
                    problems.append(f'"{w}" is credited to "{m.group(0).strip()}", but no quote that names that source holds it')
    return problems


def risk_items(text, qtexts):
    """Run 37B round r1 trace (NEG-7, NEG-8): on a risks line ("The risks: ...", "Risks and what reduces them: ..."), each risk not hedged, not a
    slot and not a condition must be in the seller's words: most of its words in the quotes, not one shared word."""
    m = re.match(r"^\W*(?:\d+[.)]\s*)?(?:the |key |main )?risks?(?: and what (?:reduces|lowers) (?:them|it|each))?\s*:\s*(.+)$", text, re.I)
    if not m:
        return []
    qk = {key_of(x, None) for q in qtexts for x in bare(q)}
    problems = []
    for item in m.group(1).split(";"):
        item = re.sub(r"\[user to add[^\]]*\]", " ", item, flags=re.I)
        item = re.split(r",\s*(?:if|when|unless|once|until)\b", re.sub(r"\([^)]*\)", " ", item))[0]
        n = norm(item).strip(" .")
        if not n or re.search(HEDGE, n) or re.match(CONDITIONAL, n) or is_question(item):
            continue
        words = [key_of(w, None) for w in bare(n) if w not in STOP and w not in SRC_GENERIC and len(w) >= 3 and not w.isdigit()
                 and w not in ("risk", "risks", "reduce", "reduces", "here", "now", "our", "we")]
        hit = [w for w in words if key_match(w, qk)]
        if words and len(hit) * 3 < len(words) * 2:
            problems.append(f'risk "{n}" is not in the seller\'s words (only {", ".join(hit) or "no word"} is): name only a risk the seller reported, hedge it, or leave a slot')
    return problems


def proposal_items(text, qtexts, own, user=""):
    """Run 39B round r1 judge J4 (NEG-8): on a proposal line of a buyer side asset ("What we propose: ...", "Recommendation: ...", "The option: ..."),
    each item (split at "with", "and", ";") not a slot, not hedged and not a condition must be in the seller's words: most of its words in the quotes."""
    m = re.match(r"^\W*(?:\d+[.)]\s*)?(?:what we propose|recommendation|the option|what it is|proposal|our proposal|what the vendor offers)\s*:\s*(.+)$", text, re.I)
    if not m:
        return []
    qk = {key_of(x, None) for q in list(qtexts) + [user] for x in bare(q)}   # the seller's whole message: a proposal item must be in the seller's words
    problems = []
    body = re.sub(r"\[user to add[^\]]*\]", " ", m.group(1), flags=re.I)
    for item in re.split(r";|,\s*(?:and|with|then|plus)\s+|,\s+(?=with\b)|\s+and\s+(?=(?:a|an|the|then)\s)", body):
        item = re.sub(r"\([^)]*\)", " ", item)
        if offer_line(item, own, context=text):
            continue   # what the seller's product does is read by the offer check
        n = norm(item).strip(" .")
        if not n or re.search(HEDGE, n) or re.match(CONDITIONAL, n) or is_question(item):
            continue
        words = [key_of(w, None) for w in bare(n) if w not in STOP and w not in SRC_GENERIC and len(w) >= 3 and not w.isdigit()
                 and w not in own and w not in ("first", "propose", "proposal", "option", "recommend")]
        hit = [w for w in words if key_match(w, qk)]
        if len(words) >= 2 and len(hit) * 3 < len(words) * 2:
            miss = [w for w in words if w not in hit]
            problems.append(f'proposal item "{n}" is not in the seller\'s words ({", ".join(miss)} not quoted): give only what the seller offered, or leave a [User to add: ...] slot')
    return problems


def offer_text(text, own=None):
    """The clauses of an offer line that state an offer (run 37B re-check 1 Y1, re-check 2 Z1 and Z2): no slot text; a bracketed aside is dropped
    (it states no name of the offer); a clause is read up to its first hedge or "not given" after the offer verb, and dropped when the hedge or a
    question comes before the verb; clauses that are not about the seller's product are left to the usual checks."""
    own = OWN if own is None else own
    keep = []
    label = re.search(r"\bwhat [\w.-]+ offers?\s*:", text, re.I)   # "What Dubverse offers: ..." makes everything after the label the offer
    for c in clauses(text):
        c2 = re.sub(r"\[user to add[^\]]*\]", " ", c, flags=re.I)
        c2 = re.sub(r"\([^)]*\)", " ", c2)
        n = norm(c2).strip(" .")
        if not n or is_question(c2) or not (label or offer_line(c2, own, context=text)):
            continue
        cut = re.search(HEDGE + r"|" + NOT_GIVEN + r"|\b(?:is|are) not (?:given|known|shown)\b", c2, re.I)
        verb = re.search(OFFER_VERBS, c2, re.I)
        if cut and (verb and cut.start() < verb.start() or (label and not verb and cut.start() == 0)):
            continue
        keep.append((c2[:cut.start()] if cut else c2).strip())
    return "; ".join(k for k in keep if k)


def is_question(c):
    return c.rstrip().rstrip("\"'”)]*").endswith("?")


def classify(sentence, in_asset):
    """Return (status, reasons, claims): status OK:<why> or NEEDS SOURCE; claims are the clauses that need a source."""
    if sentence.startswith("HASH::"):
        hw = heading_claim(sentence[6:])
        return ("NEEDS SOURCE", ["a heading states what its body hedges: " + ", ".join(hw)], [sentence[6:]]) if hw and not in_asset else ("OK:heading", [], [])
    if sentence.startswith("HEAD::"):
        st, rs, cs = classify(sentence[6:], in_asset)
        hw = heading_claim(sentence[6:])
        if hw and st != "NEEDS SOURCE":
            return "NEEDS SOURCE", ["a heading states what its body hedges: " + ", ".join(hw)], [sentence[6:]]
        return st, rs, cs
    original = sentence
    s = norm(sentence)
    if s.startswith("#"):
        return "OK:heading", [], []
    if re.match(r"^(?:to|from|for|said by|cc)\s*:", s) and in_asset:
        return "OK:header", [], []
    if s.endswith(":") and len(s.split()) <= 8:
        return "OK:heading", [], []
    if sentence.startswith("STATUS::"):
        parts = status_parts(sentence[8:])
        return ("NEEDS SOURCE", ["status cell: " + parts[0][:60]], parts) if parts else ("OK:status", [], [])
    rest_of_hand_off = re.sub(r"\bb2b-[a-z-]+\s*/\s*[a-z-]+", " ", s)
    if re.search(r"\bb2b-[a-z-]+\s*/\s*[a-z-]+", s) and hand_off_ok(rest_of_hand_off):
        return "OK:hand off", [], []   # a hand off names a plugin and skill, not a buyer fact
    chk = re.search(CHECKLIST, s)
    if chk and chk.group(1).startswith(("not", "partly")):
        return "OK:checklist", [], []
    sentence = re.sub(FRAMEWORK_PARTS, "Part", sentence)   # framework part names (Need, Budget) are labels, not claims
    s = norm(sentence)
    if is_question(sentence):
        tag = re.search(r",\s*(?:right|correct|yes|no|ok|okay|isn't it|aren't they|didn't they|hasn't it|haven't they|hasn't (?:he|she|it|they)|wasn't it|true)\s*\?[\"'”)]*\s*$", sentence, re.I)
        tail = re.search(r"(?:,\s*|\s+)(?=(?:since|given that|now that|seeing that|considering that)\b)|,\s*(?=(?:as|because)\b)", sentence, re.I)
        if tag:
            sentence = sentence[:tag.start()] + "."   # a statement with a question tag is a statement
            s = norm(sentence)
        elif tail:
            # the reason given after the question is a statement, and the question before it is read as well
            st, rs, rc = classify(sentence[tail.end():].rstrip(" ?\"'”)") + ".", in_asset)
            ht, hr, hc = classify(sentence[:tail.start()].rstrip(" ,") + "?", in_asset)
            if st == "NEEDS SOURCE" or ht == "NEEDS SOURCE":
                return "NEEDS SOURCE", hr + rs, hc + rc
            return "OK:question", [], []
    after_label = re.sub(r"^[^:\"]{1,40}:\s+", "", s)
    if is_question(sentence) and (re.match(QWORD, s.lstrip("\"'“(")) or re.match(QWORD, after_label.lstrip("\"'“("))) and not (re.match(r"^when\s+(?!does|do|did|is|are|was|were|will|would|can|could|should|shall|has|have|might|may)\b", s.lstrip("\"'“(")) and "," in s):
        return "OK:question", [], []   # a question that opens with a question word asks; it states nothing
    buyer = bool(re.search(BUYER, s)) or bool(re.search(r"\bIT\b", sentence))
    reasons, claims = [], []
    subj = re.search(r"(?:^|:\s)\W*(you|i|we)\b", s)
    parts = []
    for c in clauses(sentence):
        inner = re.findall(r"\(([^)]*)\)", c)
        # run 36B (fresh re-check G4): a bracket of 4 or more words without a quote is read on its own, and the clause is read without it;
        # it is skipped when it asks (opens with a question word) or when its sentence is a question, a condition, a hedge, a "not known"
        # or advice, unless the bracket states a past buyer event (agreed, said, met, signed, approved ...). Short and quoted brackets stay in the clause.
        long_br = [x for x in inner if len(x.split()) >= 4 and '"' not in x]
        main = c
        for x in long_br:
            main = main.replace("(" + x + ")", " ")
        parts.append(main)
        mn = norm(main).strip(" \"'“”(")
        exempt = is_question(main) or re.match(CONDITIONAL, mn) or re.search(HEDGE, mn) or re.search(NOT_GIVEN, mn) \
            or re.search(r"\b(?:does not|doesn't|did not|didn't) (?:show|say)\b", mn) or (re.match(ADVICE, mn) and not in_asset)
        for x in long_br:
            hx = strong_hits(x)
            if not hx or re.match(r"^\W*(?:who|what|how|which|whether|when|where|why)\b", norm(x)):
                continue
            event = [h for h in hx if h[0] in ("agree", "say", "know", "ask") or h[1] in ("signed", "approved", "decided", "reviewed")
                     or (h[0] in ("motive", "require") and re.search(BUYER, norm(x)))]
            # run 36B gate audit round 2 (R1): a past action with a buyer or a person as its subject is an event too ("the head of IT ran the pilot")
            if re.search(r"\b(?:ran|set up|shared|took|sent|pushed|tested|piloted|chose|picked|requested)\b", norm(x)) and (re.search(BUYER + r"|\b(?:he|she)\b", norm(x)) or re.search(r"\b[A-Z][a-z]+\b", x)):
                event = event or [("do", "past action")]
            if exempt and not event:
                continue
            parts.append(x)
    for c in parts:
        if subj and re.match(r"^\W*(?:didn't|did not|haven't|have not|don't|do not|never)\b", norm(c)):
            c = subj.group(1) + " " + c   # "You named two people but didn't say ...": the subject carries over
        if "[user to add" in norm(c):
            # a slot answers only what it replaces: the words around it are still read
            c = re.sub(r"\[user to add[^\]]*\]", " ", c, flags=re.I)
            if len([w for w in bare(c) if w not in STOP]) < 2:
                continue
        cn = norm(c).strip(" \"'“”(")
        bare_c = re.sub(r"\([^)]*\)", " ", cn)   # a label in brackets ("date not given") does not hedge the clause
        bare_c = re.sub(r"\b\d{1,2}\s+may\b|\bmay\s+\d{1,2}\b", " ", bare_c)   # the month of May is not a hedge
        if c.startswith("USUAL::"):
            hits = usual_cell_claims(c[7:])
            if hits:
                reasons.append("a usual concern cell states something about this person: " + ", ".join(hits))
                claims.append(c[7:])
            continue
        if c.startswith("STATUS::"):
            v = norm(c[8:]).strip(" .")
            if v and not re.fullmatch(r"(?:not known|not known yet|not given|unknown|not shown|none given|not decided|not started|planned|proposed|suggested|sent|to be named|to be named by the buyer|open|\[user to add\]|\"[^\"]*\"|“[^”]*”)", v):
                reasons.append("status cell")
                claims.append(c[8:])
            continue
        bare_h = re.sub(r"\b(?:is what decides|what decides|decides) whether\b", " ", bare_c)   # run 36B: "is what decides whether" states, it does not hedge
        if is_question(c) or re.match(CONDITIONAL, cn) or re.search(HEDGE, bare_h) or re.search(NOT_GIVEN, bare_c):
            own_m = [] if is_question(c) or re.match(CONDITIONAL, cn) else own_market_hits(cn)
            if own_m and not in_asset:   # run 38B r1 (DBG-5): "we usually work with lenders" is still a claim about the seller's own market
                reasons.append(", ".join(sorted({h[1] for h in own_m})))
                claims.append(c)
            continue
        hits = strong_hits(c)
        hits = [h for h in hits if h[0] != "effort" or effort_is_buyer(cn, h[1], original)]   # run 39B re-check 1 gap 3
        # asking for a decision is the asset's purpose, not a claim that one was made
        hits = [h for h in hits if not (h[0] == "do" and re.search(r"\b(?:your|for|the)\s+" + re.escape(h[1]) + r"\b", norm(c)) and h[1] in ("approval", "decision", "sign off", "signature"))]
        classes = {h[0] for h in hits}
        if re.match(ADVICE, cn) and not (classes & NO_ADVICE) and not in_asset:
            continue
        if re.match(PROPOSAL, cn) and not (classes - {"require", "do"}) and all(h[1] in ("approve", "approval", "sign", "signature", "signed") for h in hits if h[0] == "do"):
            continue
        if in_asset and re.match(r"^(?:subject)\b", cn) and not classes:
            continue
        if in_asset:
            if len(bare(c)) >= 3 or classes:
                reasons.append("asset line" + (": " + ", ".join(sorted({h[1] for h in hits})) if hits else ""))
                claims.append(c)
            continue
        flagged = [h for h in hits if h[0] in ALWAYS or buyer or not re.match(SELLER_START, cn) or (h[0] == "widen" and h[1] in ("nobody", "no one", "everyone", "everybody", "anyone"))]
        if flagged:
            reasons.append(", ".join(sorted({h[1] for h in flagged})))
            claims.append(c)
    if auth_label(original) and not in_asset and not is_question(original) and not any(h[2] == "AUTH" for c in claims for h in strong_hits(c)):
        reasons.append("authority: " + auth_label(original))   # run 38B re-check 1 R1: "Approval path: you (founder)" states it in a label the clause split drops
        claims.append(original)
    if not reasons and not in_asset and [h for h in strong_hits(original) if h[2] == "PAIN"] and not re.search(HEDGE, norm(original)):
        reasons, claims = ["pain"], [re.sub(FRAMEWORK_PARTS, "Part", original)]   # run 37B re-check 1 Y2: a framework label is not a claim; run 36B: "Pain (x): ..." states a pain in its label, which the clause split drops
    if reasons:
        return "NEEDS SOURCE", reasons, claims
    return ("OK:slot" if "[user to add" in s else "OK:no buyer claim"), [], []


def read(p):
    with io.open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def build(a):
    for p in [a.answer, a.user] + (a.asset or []) + (a.source or []) + ([a.ledger] if getattr(a, "ledger", None) else []):
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
    answer, user = read(a.answer), read(a.user)
    assets = [read(p) for p in (a.asset or [])]
    sources = [read(p) for p in (a.source or [])]
    sents, blocks = split_units(answer)
    asset_sents = set()
    missing_assets = []
    nans = norm(answer)
    for i, t in enumerate(assets):
        aset, _ = split_units(t)
        if norm(re.sub(r"```.*?```", "", t, flags=re.S)) and not all(norm(x) in nans for x in aset):
            missing_assets.append(a.asset[i])
        asset_sents.update(norm(x) for x in aset)
    user_figs, src_figs = figures(user), [f for s in sources for f in figures(s)]
    own = own_names(user)
    OWN.clear(); OWN.update(own)
    TALK.clear()
    split_units(answer)   # fills TALK for the answer
    rows = []
    for n, s in enumerate(sents, 1):
        in_asset = norm(s) in asset_sents
        status, reasons, claims = classify(s, in_asset)
        figs = []
        for f in figures(s):
            if fig_in(f, user_figs):
                figs.append((f, "seller"))
            elif fig_in(f, src_figs):
                figs.append((f, "script"))
            else:
                figs.append((f, "NOT FOUND"))
        if offer_text(s, own) and offer_names(offer_text(s, own), own):   # run 37B (X2): an offer line that names anything
            if status != "NEEDS SOURCE":
                status, reasons, claims = "NEEDS SOURCE", ["a line about what the seller offers names " + ", ".join(offer_names(offer_text(s, own), own)) + ": quote the seller's own words about the product"], [offer_text(s, own)]
        if any(w == "script" for _, w in figs) and status != "NEEDS SOURCE" and "[user to add" not in norm(s):
            status, reasons, claims = "NEEDS SOURCE", ["a script or page figure: quote the line it comes from"], []
        rows.append({"id": f"S{n}", "text": s, "asset": in_asset, "status": status, "reasons": reasons, "figs": figs, "claims": claims})
    src_lines = {norm(l) for s in sources for l in s.splitlines() if l.strip()}
    bad_blocks = [b for b in blocks if norm(b) not in src_lines]
    return answer, user, sources, rows, bad_blocks, missing_assets


def closest(sentence, user):
    best, score = "", 0
    words = {w for w in bare(sentence) if w not in STOP and len(w) > 3}
    for u in re.split(r"(?<=[.!?;])\s+", user):
        sc = len(words & {w for w in bare(u) if w not in STOP and len(w) > 3})
        if sc > score:
            best, score = u.strip(), sc
    return best


def report(rows, bad_blocks, missing_assets, user):
    out = []
    need = [r for r in rows if r["status"] == "NEEDS SOURCE"]
    nf = [(r, f) for r in rows for f, w in r["figs"] if w == "NOT FOUND"]
    for r in rows:
        if r["status"] == "NEEDS SOURCE" or any(w != "seller" for _, w in r["figs"]):
            tag = " (asset)" if r["asset"] else ""
            out.append(f'{r["id"]}{tag} [{r["status"]}] {"; ".join(r["reasons"])}\n    "{r["text"]}"')
            if r["status"] == "NEEDS SOURCE":
                c = closest(r["text"], user)
                out.append(f'    closest seller words: "{c}"' if c else "    closest seller words: none")
            for f, w in r["figs"]:
                if w == "NOT FOUND":
                    out.append(f'    FIGURE NOT FOUND: {f["text"]} is in neither the seller\'s message nor a --source file')
                elif w == "script":
                    out.append(f'    figure {f["text"]}: from a --source file, not the seller\'s message')
    for b in bad_blocks:
        out.append(f'script block line not in any --source file: "{b}"')
    for m in missing_assets:
        out.append(f"asset {m} not found in the answer word for word")
    labels = sorted({m.group(0) for r in rows for m in re.finditer(r"\[User to add:[^\]]*\]|your figures|example default|hypothetical|as pasted, not yet checked|from a search result, page not opened|worked out by (?:the )?script|worked out by reading", r["text"], re.I)})
    out.append(f"SUMMARY: {len(rows)} sentences; {len(need)} need a source; {len(nf)} figures not found; {len(bad_blocks)} script block lines not matched; {len(labels)} distinct labels kept")
    if labels:
        out.append("labels: " + " | ".join(labels[:40]))
    return out


def parse_ledger(text):
    entries = {}
    for line in text.splitlines():
        m = re.match(r'\s*(S\d+)\s*\|\s*(user|script|page)\s*\|\s*(.+?)\s*$', line, re.I)
        if m:
            q = m.group(3).strip()
            if len(q) >= 2 and q[0] in "\"'“" and q[-1] in "\"'”":
                q = q[1:-1]
            entries.setdefault(m.group(1).upper(), []).append((m.group(2).lower(), q))
    return entries


def verify(row, entries, user, sources):
    problems = []
    nuser, nsrc = norm(user), [norm(s) for s in sources]
    quotes = []
    for kind, q in entries:
        nq = norm(q)
        if len(nq.split()) < 2:
            problems.append(f'quote too short: "{q}"')
            continue
        if kind == "user" and nq not in nuser:
            problems.append(f"quote not in the seller's message word for word: \"{q}\"")
            continue
        if kind in ("script", "page") and not any(nq in s for s in nsrc):
            problems.append(f'quote not in any --source file word for word: "{q}"')
            continue
        quotes.append((kind, q))
    if problems or not quotes:
        return problems or ["no usable quote"]
    qkeys = set()
    for _k, q in quotes:
        qkeys |= keys_in(q)
    qtexts = [q for _k, q in quotes]
    claim_text = " ".join(row["claims"]) if row["claims"] else row["text"]
    hits = strong_hits(claim_text)
    if not any(k == "PAIN" for _c, _w, k in hits):
        hits += [h for h in strong_hits(row["text"]) if h[2] == "PAIN"]   # the clause split can cut a bracketed list of pains in two
    flagged_words = " ".join(row["reasons"])
    hits = [h for h in hits if h[0] not in ("tradevalue", "effort", "ownmarket") or h[1] in flagged_words]   # run 39B: the new classes speak only where they flagged the row
    if row["asset"]:
        hits = [h for h in hits if h[2] != "AUTH"]   # run 38B second look gap 1: in an asset "you" is the reader (the buyer), not the seller
    elif auth_label(row["text"]) and not any(h[2] == "AUTH" for h in hits):
        hits.append(("selfauth", auth_label(row["text"]), "AUTH"))
    auth_words = [w for _c, w, k in hits if k == "AUTH"]
    if auth_words:   # the AUTH rule speaks for the authority verbs inside its own match only (second look gap 3: "their CFO signs" is still read)
        hits = [h for h in hits if not (h[0] == "do" and any(re.search(r"\b" + re.escape(h[1]) + r"\b", a) for a in auth_words))]
    auth_ok = False
    for cls, word, key in hits:
        if key == "AUTH":
            # run 38B re-check 1 R1, R3, R4: the seller's own authority needs the seller's own first person words that grant it, not negated
            auth_ok = any(k == "user" and re.search(SELLER_AUTH, norm(q)) for k, q in quotes)
            if not auth_ok:
                problems.append(f'"{word}" states the seller\'s own authority (who decides, approves or signs off): the seller\'s own words must say it ("I decide discounts myself"); otherwise make it a question or a [User to add: ...] slot')
            continue
        if key == "YOUSAID":
            # "as you told me" to the seller needs the seller's own words; "you told me" or "you mentioned" as a statement, or any of them said to a buyer, means the buyer said it
            if (row["asset"] or not word.startswith("as ")) and not ({"SAY", "ASK"} & qkeys):
                problems.append(f'"{word}" means the buyer said it: the seller\'s words must say the buyer said or asked it')
            if not any(k == "user" for k, _q in quotes):
                problems.append(f'"{word}" needs the seller\'s own words')
            continue
        if key == "FROMSRC":
            continue   # read below, item by item
        if key == "OWNMARKET":
            # run 38B round r1 trace (DBG-5): the seller's own first person words must name the same group
            grp = re.findall(GROUPS, word)
            fp = [q for k, q in quotes if k == "user" and re.search(r"\b(?:i|we|our|my|us)\b", norm(q))]
            # run 39B re-check 1 gap 2: only a quote that states the seller's own market clears it, and it must name the same group; "Pains I hear"
            # clears only a hearing line ("I hear from support teams ...")
            mq = [q for q in fp if own_market_hits(norm(q))]
            # run 39B second look gap 3: the pool's own wording ("I sell our credit decisioning to lenders", "cash flow management for small businesses")
            mq += [q for k, q in quotes if k == "user" and re.search(r"\b(?:sell|sells|selling|sold)\b[^.;]{0,60}?\bto\s+(?:[\w-]+\s+){0,3}?" + GROUPS + r"\b|\bfor\s+(?:[\w-]+\s+){0,3}?" + GROUPS + r"\b", norm(q))]
            gk = {key_of(x, None) for q in mq for x in bare(q)}
            said = bool(mq) and (not grp or any(key_match(key_of(g.split()[-1], None), gk) for g in grp))
            heard = re.search(r"\b(?:hear|hearing|see|seeing)\b", word) and any(re.search(r"\b(?:i|we) (?:hear|see|keep hearing|keep seeing)\b", norm(q)) for q in fp)
            if not (said or heard):
                problems.append(f'"{word}" is a claim about the seller\'s own customers or market: the seller\'s own words must say it ("most of our customers are lenders"); otherwise cut it or make it a [User to add: ...] slot')
            continue
        if key == "PAIN":
            # run 36B r1 trace (DBG-3): a pain needs a quote that states a problem, not only a role or a task ("books trucks today")
            pq = [q for q in qtexts if re.search(PROBLEM, norm(q))]
            if not pq:
                problems.append(f'"{word.strip()}" (a pain): no quote states a problem (a cost, a delay, an error, a worry); a role or a task is not a pain')
                continue
            # each pain listed in a bracket after the word must share a word with a quote that states a problem
            lst = re.search(r"\bpains?\b[^(]{0,60}\(([^)]*)\)", row["text"], re.I)
            items = re.split(r";|,|\band\b", lst.group(1)) if lst else []
            col = re.search(r"\bpains?\b(?: points?)?[^.:;()\[\]]{0,48}:\s*(.+)$", row["text"], re.I)   # run 37B (X3): a colon list
            if col:
                items += [x for x in re.split(r";|,|\band\b|\(\d+\)", col.group(1)) if x.strip()]
            for item in items:
                iw = {key_of(w, None) for w in bare(item) if w not in STOP and len(w) > 3} - {"word", "gave", "given", "them"}
                if re.match(r"^\s*(?:from|as|in|per|by|said by|raised by)\b", item):
                    continue   # a source or a label in the bracket, not a pain
                if iw and not any(pain_item_ok(item, iw, q) for q in pq):
                    problems.append(f'"{item.strip()}" is listed as a pain, but no quote that states a problem names it')
            continue
        if not key_match(key, qkeys):
            problems.append(f'"{word}" ({cls}) is not in the quoted words')
        elif cls != "widen" and not polarity_ok(word, claim_text, qtexts):
            problems.append(f'"{word}" is negated in one and not in the other: the sentence says the opposite of the quote')
    htext = row["text"][6:] if row["text"].startswith(("HEAD::", "HASH::")) else None
    if htext is not None and any(r.startswith("a heading states") for r in row["reasons"]):
        for w in heading_claim(htext):   # run 38B round r1 trace (DRC-4): each word the heading states must be in a quote
            if not key_match(key_of(w, None), qkeys):
                problems.append(f'"{w}" is stated in a heading, but no quote holds it: hedge the heading, make it a question, or cut it')
    problems += source_items(row["text"], qtexts)
    problems += risk_items(row["text"], qtexts)
    if row["asset"]:
        problems += proposal_items(row["text"], qtexts, own_names(user), user)
    # run 36B r2 trace (DBG-1), run 37B close-recheck X1: a status cell names each seat it reports on, and each seat must be in a quote (whole words,
    # "CFO" or "chief financial officer"); a contact status ("no contact yet", "engaged", "silent") needs a quote that says something about contact
    if row["text"].startswith("STATUS::"):
        qn = norm(" ".join(qtexts))
        for seg in re.split(r";|,(?=\s*(?:no contact|not|silent|engaged|in contact)\b)", re.sub(STATUS_WORD, "", norm(row["text"][8:]))):
            sn = norm(seg)
            if re.search(HEDGE, sn) or re.search(r"\b(?:not known|not given|unknown|not shown)\b", sn) or '"' in seg or "“" in seg:
                continue
            for seat in sorted(set(re.findall(SEAT_RE, sn))):
                if not re.search(r"\b(?:" + SEATS[seat] + r")\b", qn):
                    problems.append(f'"{seat}" is reported on in this status cell, but no quote names it')
            cc = re.search(CONTACT_CLAIM, sn)
            if cc and not re.search(CONTACT_WORD, qn.replace("contact centre", " ").replace("contact center", " ")):
                problems.append(f'"{cc.group(0)}" reports on contact with a seat, but no quote says anything about contact')
    # run 36B r2 trace (SEQ-4), run 37B close-recheck X2: every name on a line about what the seller's product offers or does (a product, a place,
    # a language, a person) must be in a quote about the seller's own product (one that names the seller's company or speaks as "we" or "our"),
    # so a buyer side quote does not make it the seller's offer; the seller's own company name is exempt
    own = own_names(user)
    if offer_text(row["text"], own):
        # run 37B re-check 1 Y4: a quote is about the seller's product when it names the seller's company or product, or says "we" or "our"
        # with an offer word; a first person sentence about the buyer ("I spoke to their head of collections, who wants Tamil") is not
        own_q = norm(" ".join(q for q in qtexts if any(re.search(r"\b" + re.escape(o) + r"\b", norm(q)) for o in own)
                              or (re.search(r"\b(?:we|our)\b(?:\s+\w+){0,3}?\s+(?:offer|support|handle|provide|dub|cover|work|integrat|connect|plug|sync|ship|run|translat|automat|product|platform|tool|service|app)\w*", norm(q))
                                  and not re.search(r"\b(?:their|they|them|wants?|wanted|asked|needs?)\b", norm(q)))))   # run 37B re-check 2 Z6
        for w in offer_names(offer_text(row["text"], own), own):
            if not re.search(r"\b" + re.escape(w.lower()) + r"\b", own_q):
                problems.append(f'"{w}" is named on a line about what the seller offers, but in no quote about the seller\'s own product')
    # run 38B second look gap 3: when the AUTH rule is met, the shared word check reads only the parts of the claim that hold no authority claim
    shared_text = " ".join(p for p in re.split(r"[;]|\.\s", claim_text) if not any(a in norm(p) for a in auth_words)) if auth_ok else claim_text
    words = {key_of(w, None) for w in bare(shared_text) if w not in STOP and len(w) > 3}
    qwords = {key_of(w, None) for _k, q in quotes for w in bare(q) if w not in STOP and len(w) > 3}
    if words and not any(key_match(w, qwords) for w in words) and not any(w == "script" for _f, w in row["figs"]):
        problems.append("the quote shares no word with the sentence")
    script_q = " ".join(q for k, q in quotes if k in ("script", "page"))
    for f, w in row["figs"]:
        if w == "script" and not fig_in(f, figures(script_q)):
            problems.append(f'figure {f["text"]} is not in the quoted script or page line')
    if script_q:
        for m in re.finditer(DIRECTION, norm(row["text"])):
            if key_of(m.group(0), None) not in {key_of(w, None) for w in bare(script_q)}:
                problems.append(f'"{m.group(0)}" changes the meaning of the script line')
    return problems


def run(argv):
    buf = io.StringIO()
    ap = argparse.ArgumentParser(prog="claim_ledger.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sk = sub.add_parser("skeleton")
    sk.add_argument("--type", required=True)
    for name in ("scan", "check"):
        p = sub.add_parser(name)
        p.add_argument("--answer", required=True)
        p.add_argument("--user", required=True)
        p.add_argument("--asset", action="append")
        p.add_argument("--source", action="append")
        if name == "check":
            p.add_argument("--ledger", required=True)
            p.add_argument("--final", action="store_true")
    if not argv or argv[0] in ("-h", "--help"):
        return 0, ap.format_help()
    try:
        old = sys.stderr
        sys.stderr = buf
        a = ap.parse_args(argv)
    except SystemExit as e:
        sys.stderr = old
        return (0 if e.code == 0 else 2), buf.getvalue()
    finally:
        sys.stderr = old
    if a.cmd is None:
        return 2, ap.format_help()
    if a.cmd == "skeleton":
        if a.type not in SKELETONS:
            return 2, f"unknown type {a.type}; types: {', '.join(SKELETONS)}"
        body = SKELETONS[a.type].replace("[the ", "[User to add: the ").replace("[what ", "[User to add: what ").replace("[only ", "[User to add: only ").replace("[one ", "[User to add: one ").replace("[a ", "[User to add: a ").replace("[each ", "[User to add: each ").replace("[usual", "[User to add: usual").replace("[who", "[User to add: who").replace("User to add: User to add:", "User to add:").replace("[User to add: User to add", "[User to add")
        return 0, (f"Skeleton {a.type}. Fill every slot the seller's message, a cited page or a script line answers (record the quote in the ledger); "
                   "leave \"[User to add: ...]\" only where nothing does. Add no line about the buyer side that is not in a slot.\n" + body)
    try:
        answer, user, sources, rows, bad_blocks, missing_assets = build(a)
    except FileNotFoundError as e:
        return 2, f"file not found: {e}"
    lines = report(rows, bad_blocks, missing_assets, user)
    if a.cmd == "scan":
        return 0, "\n".join(["CLAIM LEDGER SCAN (the exact text you will deliver)"] + lines) + "\n"
    entries = parse_ledger(read(a.ledger))
    fails = []
    for r in rows:
        for f, w in r["figs"]:
            if w == "NOT FOUND":
                fails.append(f'{r["id"]}: figure {f["text"]} is in neither the seller\'s message nor a --source file')
        if r["status"] != "NEEDS SOURCE":
            continue
        if r["id"] not in entries:
            fails.append(f'{r["id"]}: no ledger line; give the seller\'s exact words, a script or page line, or rewrite it as a slot, a question or a hedge: "{r["text"]}"')
            continue
        for p in verify(r, entries[r["id"]], user, sources):
            fails.append(f'{r["id"]}: {p}: "{r["text"]}"')
    for b in bad_blocks:
        fails.append(f'script block line not in any --source file: "{b}"')
    for m in missing_assets:
        fails.append(f"asset {m} not found in the answer word for word")
    if fails:
        head = [f"claim_ledger --final: NOT DELIVERABLE, {len(fails)} to fix"] if a.final else []
        return 1, "\n".join(head + ["LEDGER FAIL"] + fails + ["Fix each line (rewrite, slot, question, or a correct quote), save the answer again, and re run check"
                                                             + (" --final as your last tool call." if a.final else ".")]) + "\n"
    normed = "\n".join(l.rstrip() for l in answer.replace("\r\n", "\n").strip().splitlines())
    sha = hashlib.sha256(normed.encode("utf-8")).hexdigest()
    if not a.final:
        return 0, "\n".join(["LEDGER PASS"] + lines + [f"checked text sha256: {sha}", "Next: run the same check with --final as your last tool call and send exactly the text it prints between its marker lines."]) + "\n"
    # --final (run 36B, after run 35C): the verdict first, the digest of every file checked, then the reply itself between marker lines, so the
    # text to send is printed by the last tool call and the plugin's Stop hook can compare the reply with it
    d = digest(answer)
    out = [f"claim_ledger --final: PASS, reply digest {d}", "LEDGER PASS", f"digest {a.answer}: {d}"]
    out += [f"digest {pth}: {digest(read(pth))}" for pth in (a.asset or [])]
    out += [f"checked text sha256: {sha}",
            "DELIVER: send as your whole reply exactly the text between the two marker lines below: nothing before or after it, no word "
            "changed. Saved files checked: " + (", ".join(a.asset) if a.asset else "none") + ". To change anything, edit the file and run check --final again.",
            f"=== BEGIN CHECKED REPLY {d} ===", normed, f"=== END CHECKED REPLY {d} ==="]
    return 0, "\n".join(out) + "\n"


def digest(text):
    """The delivery digest (run 35C rule): line ends and trailing spaces ignored, nothing else; 16 hex characters of sha256."""
    t = "\n".join(l.rstrip() for l in (text or "").replace("\r\n", "\n").strip().splitlines())
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    code, out = run(sys.argv[1:])
    sys.stdout.write(out)
    sys.exit(code)
