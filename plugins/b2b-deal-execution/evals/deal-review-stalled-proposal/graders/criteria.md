---
type: llm
---

The user's request, word for word:
<request>
I'm an account executive selling a workflow automation product. Review my deal and tell me what to do next.

Facts: the buyer is a mid sized logistics company. We are at proposal stage and have been there 30 days. Their VP of operations is my champion: she explains our case to her team when I'm not in the room, she shared their budget timeline with me, and she got me a meeting with their head of IT. The CFO is named as the person who approves spend but has not joined any call yet. They run the process on spreadsheets today and no other vendor is in the deal. One blocker: IT wants a security review and nobody owns it yet. Their target signature date is Friday 18 December 2026.

Don't ask me questions first. Mark anything missing as not given.
</request>

The user gave these facts: proposal stage for 30 days; the VP of operations is the champion (explains the case internally, shared the budget timeline, gave access to the head of IT); the CFO is named as the spend approver and has not joined any call; spreadsheets today and no other vendor; one blocker, an IT security review with no owner; target signature Friday 18 December 2026.

PASS only if all of these hold:
1. It reads back the deal facts without changing their meaning (for example it does not say the CFO is engaged, or that IT has approved anything).
2. It names the CFO not being engaged and the security review with no owner among the main risks, and ties each to a concrete action.
3. It gives next actions, each with an owner (the seller, the champion, or a buyer seat by role, or "to be named by the buyer") and either a suggested date or a note that the date is to be agreed with the buyer.
4. It lists facts that were not given (for example who signs, the buyer's approval or procurement steps, holidays) instead of filling them in.
5. If it shows a deal health score, it shows the factors behind it and labels the point values as example defaults the user can change, or it says no score was computed. It never presents a score as a win probability or forecast.

FAIL if any of these happen, whatever else the reply does well:
- It invents a fact or figure the user did not give: a named person or company, a customer, a competitor, a result, a statistic, a benchmark, a typical or industry value, a deadline or a money amount. Arithmetic on the user's own figures is allowed only when it is correct. A suggestion clearly marked as a suggestion, an example default labelled as one, a placeholder such as "[User to add: ...]", and naming which of its own reference notes it used (marked as something to confirm or test) are not invented facts. Restating what the user wrote in the request above is not invention.
- It recommends buying, adopting or switching to a named software product, tool or vendor. (Pointing the user to another plugin or skill by name for work outside this request is a hand off, not a software recommendation.)
- It names any real company or person as the user's client, prospect, buyer or customer.
- It is not plain English: hype or marketing words (for example "game changer", "supercharge", "unlock", "seamless", "robust"), exclamation marks, or jargon left unexplained for the reader named in the request.
- It uses a dash as punctuation: an em dash, an en dash, or a hyphen with a space on each side between words. Hyphens inside compound words, hyphens that start a list item and hyphens in table borders are fine.
