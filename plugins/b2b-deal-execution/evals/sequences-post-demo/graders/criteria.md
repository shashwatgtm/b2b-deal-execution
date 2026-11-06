---
type: llm
---

The user's request, word for word:
<request>
Write a 3 email follow up sequence after yesterday's demo. The reader is the head of customer support at a mid sized ecommerce company. Points they raised in the demo: their agents switch between four tabs for every ticket, and they need to answer customers in Hindi as well as English. I sell a support inbox product. The first email should go out tomorrow.
</request>

The user gave: a demo yesterday; the reader is the head of customer support at a mid sized ecommerce company; two demo points (agents switch between four tabs for every ticket; they need to answer in Hindi as well as English); the seller sells a support inbox product; 3 emails; the first goes out tomorrow. The user did NOT say what the product does about tabs or about Hindi, and gave no customer results.

PASS only if all of these hold:
1. There are exactly 3 emails, each with a subject and a body.
2. Each email has a single clear ask, and the same ask is not repeated across emails.
3. The emails use the two demo points the user gave.
4. It does not claim the product supports Hindi, removes tab switching, or achieves any result unless it marks that as something for the seller to confirm or fill in (for example a "[User to add: ...]" placeholder or a check before sending).
5. It states when each email goes out (a day or a gap between emails), and does not present a send day as a proven best practice.
6. No fake "Re:" or "Fwd:" subject, no false urgency, and no customer name, case study, statistic or result the user did not give.

FAIL if any of these happen, whatever else the reply does well:
- It invents a fact or figure the user did not give: a named person or company, a customer, a competitor, a result, a statistic, a benchmark, a typical or industry value, a deadline or a money amount. Arithmetic on the user's own figures is allowed only when it is correct. A suggestion clearly marked as a suggestion, an example default labelled as one, a placeholder such as "[User to add: ...]", and naming which of its own reference notes it used (marked as something to confirm or test) are not invented facts. Restating what the user wrote in the request above is not invention.
- It recommends buying, adopting or switching to a named software product, tool or vendor. (Pointing the user to another plugin or skill by name for work outside this request is a hand off, not a software recommendation.)
- It names any real company or person as the user's client, prospect, buyer or customer.
- It is not plain English: hype or marketing words (for example "game changer", "supercharge", "unlock", "seamless", "robust"), exclamation marks, or jargon left unexplained for the reader named in the request.
- It uses a dash as punctuation: an em dash, an en dash, or a hyphen with a space on each side between words. Hyphens inside compound words, hyphens that start a list item and hyphens in table borders are fine.
