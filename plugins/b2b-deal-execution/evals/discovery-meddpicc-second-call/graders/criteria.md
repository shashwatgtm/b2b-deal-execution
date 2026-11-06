---
type: llm
---

The user's request, word for word:
<request>
I sell a contract review tool for in house legal teams. I have a second call on Thursday with the general counsel of a mid sized insurer.

Pains from the first call: their lawyers spend most of Monday triaging NDAs, and they cannot tell which contracts are waiting on the business side. We use MEDDPICC. What I know so far: the general counsel is keen on us, and they told me the COO approves new tools.

What should I ask on the call?
</request>

The user gave: a second call with the general counsel of a mid sized insurer; two pains (lawyers spend most of Monday triaging NDAs; they cannot tell which contracts are waiting on the business side); MEDDPICC; the general counsel is keen; the COO approves new tools (as told to the seller).

PASS only if all of these hold:
1. The questions are grouped by MEDDPICC parts (metrics, economic buyer, decision criteria, decision process, paper process, identify pain, champion, competition).
2. Each of the two pains gets its own question, in the buyer's terms; neither pain is dropped or merged into the other.
3. It does not treat the general counsel as a confirmed champion just because they are keen: it labels them a potential champion or gives a question that tests whether they will sell internally or give access.
4. It asks a question that confirms the COO's role as approver rather than stating it as settled.
5. It gives an opening for the call and a close that ends in a next step to agree with the buyer.
6. No question contains a statistic, benchmark or claim about a competitor that the user did not give.

FAIL if any of these happen, whatever else the reply does well:
- It invents a fact or figure the user did not give: a named person or company, a customer, a competitor, a result, a statistic, a benchmark, a typical or industry value, a deadline or a money amount. Arithmetic on the user's own figures is allowed only when it is correct. A suggestion clearly marked as a suggestion, an example default labelled as one, a placeholder such as "[User to add: ...]", and naming which of its own reference notes it used (marked as something to confirm or test) are not invented facts. Restating what the user wrote in the request above is not invention.
- It recommends buying, adopting or switching to a named software product, tool or vendor. (Pointing the user to another plugin or skill by name for work outside this request is a hand off, not a software recommendation.)
- It names any real company or person as the user's client, prospect, buyer or customer.
- It is not plain English: hype or marketing words (for example "game changer", "supercharge", "unlock", "seamless", "robust"), exclamation marks, or jargon left unexplained for the reader named in the request.
- It uses a dash as punctuation: an em dash, an en dash, or a hyphen with a space on each side between words. Hyphens inside compound words, hyphens that start a list item and hyphens in table borders are fine.
