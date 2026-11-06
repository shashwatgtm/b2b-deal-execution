---
type: llm
---

The user's request, word for word:
<request>
Procurement at a mid sized bank is asking for a 15% discount on the first year. The deal is 48 lakh rupees a year, with a 3 year term on the table. My walk away point is 10%. My champion is their head of collections.

What do I concede, what do I ask for in return, and what do I say on Thursday's call?
</request>

The user gave: a 15% first year discount asked by procurement; deal value 48 lakh rupees a year; a 3 year term on the table; the seller's walk away point is 10%; the champion is the head of collections; a call on Thursday. Correct arithmetic on these figures: 15% of 48 lakh is 7.2 lakh; 10% of 48 lakh is 4.8 lakh; 48 lakh less 10% is 43.2 lakh.

PASS only if all of these hold:
1. Every concession it suggests is paired with something the buyer gives in return (for example a signed 3 year term, a case study, a faster signature), in an "if you do X, we can do Y" form or plainly equivalent.
2. It never concedes more than the 10% walk away point.
3. It gives one question to find what is really behind the discount ask.
4. Any money figure is either the user's or correct arithmetic on the user's figures, and is not presented as a market or typical figure.
5. It gives words the seller can use on Thursday's call.
6. It does not invent an approval level, a policy, a competitor price or a typical discount range.

FAIL if any of these happen, whatever else the reply does well:
- It invents a fact or figure the user did not give: a named person or company, a customer, a competitor, a result, a statistic, a benchmark, a typical or industry value, a deadline or a money amount. Arithmetic on the user's own figures is allowed only when it is correct. A suggestion clearly marked as a suggestion, an example default labelled as one, a placeholder such as "[User to add: ...]", and naming which of its own reference notes it used (marked as something to confirm or test) are not invented facts. Restating what the user wrote in the request above is not invention.
- It recommends buying, adopting or switching to a named software product, tool or vendor. (Pointing the user to another plugin or skill by name for work outside this request is a hand off, not a software recommendation.)
- It names any real company or person as the user's client, prospect, buyer or customer.
- It is not plain English: hype or marketing words (for example "game changer", "supercharge", "unlock", "seamless", "robust"), exclamation marks, or jargon left unexplained for the reader named in the request.
- It uses a dash as punctuation: an em dash, an en dash, or a hyphen with a space on each side between words. Hyphens inside compound words, hyphens that start a list item and hyphens in table borders are fine.
