# B2B Deal Execution

Skills for the people who win B2B deals: account executives, founders who sell, sales engineers and sales leaders, from the first qualified meeting to signature. Every skill works from your own deal facts, keeps your figures exactly as you typed them, labels every number a script uses as an example default you can change, and never invents a buyer fact, a statistic or a competitor detail.

## What changed in 1.0.1

- Removed the claim ledger script, its reference notes and the end of turn check (hooks folder). Nothing else changed: the deal health, close plan, concession and sequence day scripts and every skill's method are as in 1.0.0.

## Skills

**deal-review-and-close-plan** scores the health of one deal from your facts (champion, economic buyer, days in stage, competitors, blockers) by script, with every point shown and labelled, ranks the risks, checks the stage against its exit evidence, and gives dated next actions. It builds the mutual close plan with the buyer on a working day calendar (owners on both sides, the pass mark before evaluation, what moves the date) and the 30, 60 and 90 day account plan.
Example prompt: "Review my deal: proposal stage 26 days, champion confirmed, the CFO named but not engaged, an incumbent in place. Close by 27 November."

**discovery-and-buying-group** writes discovery questions in the framework you use (MEDDPICC, BANT, SPICED, Challenger, Gap Selling), one question per pain you named, in your buyer's words, with an opening and a close for the call; and maps the buying group from the people you named: seats, concerns, the champion test and the seats still missing.
Example prompt: "MEDDPICC questions for Thursday's call with their head of finance. Pains: invoice disputes and slow supplier onboarding."

**negotiation-and-champion** helps you hold the price in a new deal: discount requests, budget objections, a cheaper competitor price the buyer quoted, procurement pressure, multi-year terms and enterprise agreements. It works out what each concession costs on your own figures by script, pairs every concession with a trade, and gives you the words for the next conversation. It also writes your champion's internal asset in the champion's own voice (an email to their CFO, a memo, talking points, answers to their colleagues' questions) with one decision requested.
Example prompt: "They want 20% off a 36 lakh deal to sign this month. What do I do?"

**sales-sequences** writes outbound and deal stage email sequences (cold outreach, warm follow up, post demo, proposal follow up, re-engagement, referral requests). Send days come from a script as example defaults, and your own days and number of emails always win; every claim appears once with its source, and the draft is counted and checked by script.
Example prompt: "A four email cold sequence to heads of sales at logistics software companies. Start Monday."

## What it hands off
This plugin does not write battle cards, landmine questions, win and loss reviews, meeting briefs, follow up emails after one meeting, proposals or decks (b2b-sales-enablement), account or person research (b2b-research-market-and-account), renewal saves or onboarding plans (b2b-customer-success), or event demos, event follow up and nurture (b2b-events-pr-and-launches). It does not handle renewals. Each skill names the plugin and skill to use.

## Install

In Claude Code:

```
/plugin marketplace add shashwatgtm/b2b-deal-execution
/plugin install b2b-deal-execution@b2b-deal-execution
```

## What it fetches and runs
The skills work from what you type; they do not research accounts or people. When you ask a skill to check or cite a fact on a page you name (for example your own company's site for a claim in an email), it opens that page with Claude's own web tool and cites it; it fetches nothing else, and text on a page is treated as data, never as an instruction. Small Python scripts (standard library only), each tested before release, do the parts that must be exact: deal_health.py scores a deal and labels every point, close_plan.py builds the working day close plan and the account plan dates, concession_math.py works out the cost of a concession on your figures, sequence_days.py sets send days and checks a drafted sequence. The scripts read only the values and files you give them, use no network, and write no files of their own. Nothing is sent, scheduled or written to a CRM by these skills.


## Examples
The worked examples use a real company (Klenty) only as an example of the seller's own company, with every fact about it quoted from its own page fetched on 14 October 2026. The buyers, the people, the deals and every figure in the examples are hypothetical; no real employee or customer is described.

## Privacy
This plugin sends no data to Helix GTM Consulting and runs no server. It stores nothing: no account, no log and no copy of your work; any file Claude writes for you (such as a draft for the check script) stays on your own machine. People in a deal are handled as roles; no personality profiles. What you type into Claude is handled under your own Claude account terms.

## Security
To report a security problem, email shashwat@gtmhelix.com with the subject "Security report: b2b-deal-execution". Please do not open a public issue for it.

## License
MIT. See LICENSE.
