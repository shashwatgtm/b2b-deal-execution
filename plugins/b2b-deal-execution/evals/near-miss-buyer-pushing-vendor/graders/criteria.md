---
type: llm
---

The user's request, word for word:
<request>
I'm on the buying side. Our software vendor wants a 12% price increase at renewal next quarter. How do I push back and get the price down?
</request>

The user gave: they are the buyer; the vendor wants a 12% increase at renewal next quarter. Nothing else (no contract value, no usage, no alternatives).

PASS only if all of these hold:
1. It gives practical steps a buyer can take to push back on the 12% increase.
2. It does not state a typical, market or industry range for software price increases or discounts, and does not invent the vendor's costs, the contract value or alternatives.

FAIL if any of these happen, whatever else the reply does well:
- It invents a fact or figure the user did not give: a named person or company, a customer, a competitor, a result, a statistic, a benchmark, a typical or industry value, a deadline or a money amount. Arithmetic on the user's own figures is allowed only when it is correct. A suggestion clearly marked as a suggestion, an example default labelled as one, a placeholder such as "[User to add: ...]", and naming which of its own reference notes it used (marked as something to confirm or test) are not invented facts. Restating what the user wrote in the request above is not invention.
- It recommends buying, adopting or switching to a named software product, tool or vendor. (Pointing the user to another plugin or skill by name for work outside this request is a hand off, not a software recommendation.)
- It names any real company or person as the user's client, prospect, buyer or customer.
- It is not plain English: hype or marketing words (for example "game changer", "supercharge", "unlock", "seamless", "robust"), exclamation marks, or jargon left unexplained for the reader named in the request.
- It uses a dash as punctuation: an em dash, an en dash, or a hyphen with a space on each side between words. Hyphens inside compound words, hyphens that start a list item and hyphens in table borders are fine.
