# Gate 4 results: 30 questions on the final snapshot

**Score: 21/30 at acting quality** (tier 1: 12/18), scored by the TL agent (Claude) on 2026-11-18. Gate 4 target: at least 21/30 (docs/BRIEF.md).

## How this was run

- Snapshot `corpus-2026-11-17` (219 documents), time windows as of 2026-11-17.
- Code: `main` e02b1c9 (retrieval #203/PR #206, prompt v3 #204/PR #207, firm scope #205/PR #208), run from branch `tl/121-gate4` at 40fe462 (no product change on the branch).
- Model `claude-sonnet-5-5`, prompt v3, one model call per question. Every answer was produced by `scripts/eval_run.py --real`; 19 answers were made in the R2 check run and reused unchanged (same prompt, same retrieved passages), 11 were made in the final run.
- Scoring: each answer read against its `passes_if` line in `evals/questions.yaml`: would the project lead forward it with his name on it? One verdict per question, no half credit. This is one agent's judgement; borderline questions are named.
- Citations: 382 in total; every cited passage was in the retrieved set and exists in the database. The code's number check flagged 4 claims (Q4, Q9, Q20, Q22); each figure was checked against its passage and is present (checker false positives).

## Scores

Classes for failures: r = retrieval missed a passage the corpus holds; s = answer shape or a required part missing; b = behavior choice differs from the expected one; c = corpus gap.

| Q | Tier | Expected -> got | Gate 3 | R1 (11-18, before fixes) | Gate 4 | Class |
|---|---|---|---|---|---|---|
| Q1 | 1 | answer -> answer | PASS | PASS | **PASS** |  |
| Q2 | 1 | answer -> answer | PASS | FAIL | **PASS** |  |
| Q3 | 1 | answer -> answer | FAIL | FAIL | **FAIL** | s |
| Q4 (trap) | 1 | answer -> answer | PASS | PASS | **PASS** |  |
| Q5 | 1 | answer -> answer | PASS | PASS | **PASS** |  |
| Q6 | 1 | answer -> answer | PASS | FAIL | **PASS** |  |
| Q7 | 2 | answer -> answer | FAIL | FAIL | **FAIL** | s |
| Q8 | 2 | answer -> answer | PASS | PASS | **PASS** |  |
| Q9 | 3 | answer -> answer | PASS | PASS | **PASS** |  |
| Q10 | 3 | answer -> answer | PASS | PASS | **PASS** |  |
| Q11 | 1 | answer -> gap_with_adjacent | FAIL | FAIL | **FAIL** | c, b |
| Q12 | 3 | answer_with_boundary -> answer_with_boundary | FAIL | FAIL | **FAIL** | s |
| Q13 | 1 | answer -> answer | FAIL | FAIL | **PASS** |  |
| Q14 | 3 | answer -> answer | PASS | PASS | **PASS** |  |
| Q15 | 3 | answer -> answer | FAIL | FAIL | **FAIL** | r, s |
| Q16 | 3 | answer -> answer | FAIL | FAIL | **PASS** |  |
| Q17 | 1 | answer -> answer | FAIL | FAIL | **PASS** |  |
| Q18 | 3 | answer -> answer | PASS | PASS | **PASS** |  |
| Q19 | 3 | answer_with_boundary -> answer_with_boundary | FAIL | FAIL | **PASS** |  |
| Q20 | 1 | answer -> answer | FAIL | FAIL | **FAIL** | r |
| Q21 | 2 | answer -> answer | PASS | PASS | **PASS** |  |
| Q22 | 1 | answer -> answer | FAIL | FAIL | **PASS** |  |
| Q23 | 1 | answer -> gap_with_adjacent | FAIL | FAIL | **FAIL** | c, b |
| Q24 | 3 | gap_with_adjacent -> gap_with_adjacent | PASS | PASS | **PASS** |  |
| Q25 | 1 | gap_with_adjacent -> gap_with_adjacent | FAIL | FAIL | **FAIL** | r |
| Q26 | 1 | answer -> answer | FAIL | PASS | **PASS** |  |
| Q27 (trap) | 1 | answer -> answer | PASS | PASS | **PASS** |  |
| Q28 | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | PASS | **FAIL** | s |
| Q29 | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | PASS | **PASS** |  |
| Q30 (trap) | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | PASS | **PASS** |  |

Gate 3 (corpus-2026-11-16): 16/30. R1 (corpus-2026-11-17, before the three fixes): 15/30. Gate 4 (same corpus, after the fixes): 21/30.

Borderline on the pass side: Q17, Q19, Q22, Q26. On the fail side: Q15, Q25, Q28. Another scorer could move the total by one or two either way.

## Known gaps

- **Advisor headcount for Morgan Stanley, Schwab and Merrill is not in the corpus** (no stored filing, supplement, deck or release gives a count). Q11 and Q23 cannot pass on this corpus; Q24 cannot compute a ratio for those firms.
- **Retrieval still misses passages the corpus holds:** Morgan Stanley's formulaic payout for Q25 and Q7, Raymond James's full payout ranges for Q25, Schwab's revenue composition for Q15, the Fidelity next-generation study and UBS sample for Q20, Merrill's AI-tools remark for Q17, Edward Jones's next-generation platform for Q19.
- **Answer shape:** a comparison grid uses the dimensions the evidence offers, not all the dimensions the question implies (Q7); a part of the question with no evidence is sometimes neither answered nor named as a gap (Q3 concessions, Q12 Edward Jones cost structure, Q28 net headcount vs attrition).
- **Behavior on corpus gaps:** with prompt v3, Q11 and Q23 choose `gap_with_adjacent` when most firms lack the figure. This is honest on this corpus, but the bank expects `answer`.
- **Uncited empty cells:** Q7's grid states three empty cells as claims without a citation; code flags them (`no_citation`). They belong in `gaps`.
- **Trade press only for recency:** Q26's 90-day window holds no Raymond James primary document, so every item is trade press (labelled indicative).
- Q18 is scored without fee-schedule documents beyond the Form ADV brochures.

Next steps are in [docs/NEXT.md](../NEXT.md). How to reproduce this run: [docs/RUN.md](../RUN.md) section 7.

## The 30 answers

Each answer as the system returned it: claims with the passages they cite (document type, publication date, opening of the stored passage), adjacent evidence, the gaps the answer names and the caveats inserted by code. Raw outputs: `report.json` next to this file.

### Q1: What is Morgan Stanley's strategy to increase their net new assets?

**Verdict: PASS**. Channels in management's words (Workplace funnel, IPO flows, integrated firm, advisor-led fee-based flows), each dated 3Q25-3Q26, with the quarterly NNA series.

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It names the channels management itself credits for net new asset growth, in management's framing, with the emphasis each is given -- and it is dated. Strategy stated in 2024 is not strategy stated today, and an answer that blurs the two has failed.

**Claims**

1. On the 3Q25 earnings call (October 2025), CFO Sharon Yeshaya said NNA is "just the beginning". She described workplace and IPOs as ways to build out the integrated firm. She said the firm has people to "shepherd individuals across the entire firm", including institutional securities and underwriting. She also said there is "a lot more to go" in working with companies and their founders and serving them throughout the corporate lifecycle.
   - `MS-TR-2025Q3#45` (transcript, 2025-10-15): "Sharon Yeshaya CFO at Morgan Stanley I think that goes back, I think it was Abraham. I can't remember. It may have been Dan Fannon. The first question that we answered about NNA. It's just the beginning. I mean, I don't ..."
2. On the 4Q25 call (January 2026), management called 2025 "consistent execution of our strategy". It cited full-year net new assets of $356 billion and fee-based flows of $160 billion as demonstrating "industry-leading growth". It said Workplace and E-Trade relationships "continue to seek out advice". The 2025 10-K (published February 2026) reports the same $356 billion NNA and $160 billion fee-based flows.
   - `MS-TR-2025Q4#19` (transcript, 2026-01-15): "Company Representative at Morgan Stanley Fixed income revenues were $8.7 billion for the full year. Importantly, investing in our lending businesses has contributed to increased consistency and stability of our franchise..."
   - `MS-10K-2025#127` (10-K, 2026-02-19): "• The Firm reported net revenues of $70.6 billion and net income applicable to Morgan Stanley of $16.9 billion reflecting strong results across our business segments and demonstrating the strength of our Integrated Firm...."
3. The January 2026 strategic update deck presents a Wealth Management slide titled "Driving Growth and Strong Performance". It has panels headed "Attracting Net New Assets" and "Momentum in Fee-Based Flows", comparing 2016-2020 with 2021-2025. The deck's end notes define Core Client Relationships as Advisor-Led Households, Self-Directed Households and Workplace Participants, measured at 4Q 2020 and 4Q 2025.
   - `MS-DECK-2026-strategic-update#8` (deck, 2026-01-15): "~330 ~735 2016 - 2020 2021 - 2025 ~580 ~1,640 2016 - 2020 2021 - 2025 Momentum in Fee-Based Flows Fee-Based Flows ($Bn) (2) Attracting Net New Assets Net New Assets ($Bn) (1) Expanding Performance 19 32 2020 2025 Net Rev..."
   - `MS-DECK-2026-strategic-update#31` (deck, 2026-01-15): "These notes refer to the financial metrics and/or defined terms presented on Slide 8 Fee-Based Flows represent net new fee-based assets (including asset acquisitions), net account transfers, dividends, interest, and clie..."
4. On the 2Q26 call (July 2026), the CFO reported record NNA of $148 billion, with stock plan IPO flows just over half of it. She described Workplace as "a strong contributor to the top of the funnel" and said the "client acquisition funnel is becoming increasingly evident". She said Workplace "brings relationships and assets onto the platform" and that the firm is positioned to support them. She said the firm continues to deliver advice and solutions to new and existing relationships, "supporting the build in our fee-based assets", and that its investments are "extending our runway for growth".
   - `MS-TR-2026Q2#16` (transcript, 2026-07-15): "Sharon Yeshaya Executive VP & CFO Lastly, net new assets were a record of $148 billion. Stock plan IPO flows represented just over half of the overall NNA this quarter, more than offsetting seasonal taxes, illustrating t..."
   - `MS-PR-2026-07-15-01#5` (press, 2026-07-15): "Wealth Management reported net revenues of $8.9 billion compared with $7.8 billion a year ago. Pre-tax income of $2.7 billion resulted in a pre-tax margin of 30.5%. 4,15 Strong net new assets for the quarter were $148 bi..."
5. On the 3Q26 call (October 2026), the CFO attributed record NNA of $232 billion to "the strength of our core business and the differentiated growth opportunities created by Workplace and the integrated firm". IPO-related flows were just over half of that. She said an active IPO calendar accelerates the funnel and increases client interest in advice. She said the firm's "pipeline and our connectivity across channels" let it "build relationships early and deepen them over time". The 3Q26 press release adds that fee-based flows were $80 billion, "demonstrating continued strength in our Advisor-led channel", and included a new corporate retirement mandate.
   - `MS-TR-2026Q3#15` (transcript, 2026-10-14): "Sharon Yeshaya Executive VP & CFO Net interest income was $2.2 billion, down modestly as deposits grew and the mix shifted. Looking ahead, we expect a modest increase in the fourth quarter, subject to rates and client be..."
   - `MS-PR-2026-10-14-01#5` (press, 2026-10-14): "Wealth Management reported record net revenues of $9.1 billion compared with $8.2 billion a year ago. Record pre-tax income of $2.8 billion resulted in a pre-tax margin of 30.4%. 4,14 Record net new assets were $232 bill..."
6. The Wealth Management supplement shows quarterly NNA of $118.4 billion at 1Q26, $148.1 billion at 2Q26 and $232.4 billion at 3Q26. The 3Q26 figure compares with $81.0 billion in 3Q25. Fee-based asset flows were $80.5 billion in 3Q26, and self-directed households were 8.8 million.
   - `MS-SUPP-2026Q1#14` (supplement, 2026-04-15): "(unaudited, dollars in billions) / / Quarter Ended - Mar 31, 2026 / Quarter Ended - Dec 31, 2025 / Quarter Ended - Mar 31, 2025 / Percentage Change From: - Dec 31, 2025 / Percentage Change From: - Mar 31, 2025 / /---/---..."
   - `MS-SUPP-2026Q2#16` (supplement, 2026-07-15): "(unaudited, dollars in billions) / / Quarter Ended - Jun 30, 2026 / Quarter Ended - Mar 31, 2026 / Quarter Ended - Jun 30, 2025 / Percentage Change From: - Mar 31, 2026 / Percentage Change From: - Jun 30, 2025 / /---/---..."
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."
7. The firm names risks to NNA growth. The 2Q26 10-Q (August 2026) says NNA is influenced by client investment and spending behaviors, seasonality, the ability to attract and retain financial advisors and clients, capital market and corporate activities, and large idiosyncratic flows. It says the growth rate of NNA "may be impacted" if these factors continue. It notes just over half of 2Q26 NNA was IPO-related inflows from Workplace clients. On the 3Q26 call, the CFO said flows "will fluctuate as lockups expire, funds make distributions and individuals use assets for consumption".
   - `MS-10Q-2026Q2#58` (10-Q, 2026-08-04): "4. Annualized weighted average represents the total annualized weighted average cost of the various deposit products. Amounts include the effect of related hedging derivatives. The period end cost of deposits is based up..."
   - `MS-TR-2026Q3#15` (transcript, 2026-10-14): "Sharon Yeshaya Executive VP & CFO Net interest income was $2.2 billion, down modestly as deposits grew and the mix shifted. Looking ahead, we expect a modest increase in the fourth quarter, subject to rates and client be..."

**Adjacent evidence (a related but different quantity)**

1. WealthManagement.com (2026-10-14) reported that 3Q26 NNA of $232 billion "doubled analysts' expectations", up 57% quarter-over-quarter and 187% year-over-year.
   - *Differs because:* Trade-press reporting is indicative, not authoritative, and describes results rather than Morgan Stanley's strategy.
   - `MS-TRADE-2026-10-14-WM-01#0` (trade, 2026-10-14): "Wealth Revenues Climb at Morgan Stanley, Merrill Lynch WealthManagement.com trade press - 2026-10-14 (tier 4, indicative only) Source: https://www.wealthmanagement.com/wirehouse-news/wealth-revenues-climb-at-morgan-stanl..."

**Gaps (named by the answer)**

- No explicit NNA target, or detailed plan for advisor recruiting or channel-specific NNA goals, appears in the evidence. The strategic update deck text provided is mostly chart labels and end notes. *Would fill it:* Full January 2026 strategic update presentation and transcript; Morgan Stanley 10-K Wealth Management business description

### Q2: How is Raymond James positioning itself to recruit advisors away from the wirehouses?

**Verdict: PASS**. Affiliation choice (five AdvisorChoice options), payout (higher rate on production for Advisor Select), autonomy (book ownership, run your own branch), platform, and recruiting results ($393M T12 production, $56B assets in nine months).

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It gives Raymond James's own recruiting pitch -- affiliation choice, payout, autonomy, platform -- sourced to management statements rather than inferred, plus recruiting results where the firm discloses them.

**Claims**

1. The trade press item (published 2026-11-04) reports that a team joining Raymond James cited culture and leadership stability as the deciding factors. A team member is quoted saying "Raymond James stands out for its reputation and longstanding stability." The item says the Ohio hire "extends a consistent run of Raymond James & Associates recruiting from UBS throughout 2026." This is trade-press reporting, not a firm disclosure.
   - `RJF-TRADE-2026-11-04-IN-01#2` (trade, 2026-11-04): "Culture and leadership stability were the deciding factors in the team's decision to move. "Raymond James stands out for its reputation and longstanding stability," Massey said. "Its strong leadership team and client-fir..."
2. On the fiscal 3Q26 earnings call (July 2026), CEO Paul Shoukry said that through the first 9 months of the fiscal year the firm recruited advisors with trailing 12-month production totaling $393 million and more than $56 billion of client assets at their previous firms. He said the recruiting source and pipeline "remains diverse across our affiliation options." He credited a "differentiated value proposition": advisors "do not have to choose between culture and capabilities," because the firm offers an advisor- and client-focused culture together with leading technology, products and solutions.
   - `RJF-TR-2026Q2#6` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director Through the first 9 months of the fiscal year, we recruited advisers with trailing 12-month production totaling $393 million and more than $56 billion of client assets at their previous..."
3. On the fiscal 2Q26 call (April 2026), Shoukry said advisors who are newer to the firm sometimes appreciate its technology even more "because they're coming from a firm where they saw what the alternatives are." He said newer advisors are, in his words, "blown away" by the culture and technology. In the press release of the same date he said the firm continues to develop "industry-leading technology solutions, including increasing AI integration," and that advisor recruiting activity "across all our affiliation options remains robust."
   - `RJF-TR-2026Q1#54` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director No, not really. I mean it just depends on where we're recruiting from and what affiliation option. So it varies. There's nothing noticeably different. I would say the advisers that were..."
   - `RJF-PR-2026-04-22-01#1` (press, 2026-04-22): "ST. PETERSBURG, Fla. - Raymond James Financial, Inc. (NYSE: RJF) today reported net revenues of $3.86 billion and net income available to common shareholders of $542 million, or $2.72 per diluted share, for the fiscal se..."
4. Raymond James's recruiting pages (content as of 2026-04-21 and 2026-03-11) present AdvisorChoice®, a set of five affiliation options: Traditional Employee, Advisor Select, Independent Contractor, Bank & Credit Union, and Corporate RIA. The page describes the employee option as offering "book ownership." Advisor Select is described as letting established advisors lead their own branch and "run your branch's P&L to earn a higher rate on production." The 2025 10-K likewise describes multiple affiliation options under AdvisorChoice®.
   - `RJF-PR-web-affiliation-options#0` (press, 2026-04-21): "Raymond James Affiliation options Raymond James advisor recruiting page - content as of 2026-04-21 Source: https://web.archive.org/web/20260421065839/https://www.raymondjames.com/advisor-opportunities/affiliation-options..."
   - `RJF-PR-web-advisor-select#0` (press, 2026-03-11): "Raymond James Advisor Select® Raymond James advisor recruiting page - content as of 2026-03-11 Source: https://web.archive.org/web/20260311101214/https://www.raymondjames.com/advisor-opportunities/affiliation-options/adv..."
   - `RJF-10K-2025#10` (10-K, 2025-11-25): "We offer multiple affiliation options, which we refer to as AdvisorChoice®. Financial advisors primarily affiliate with us directly as either employees or independent contractors or as employees of third-party Registered..."
5. At its June 2025 investor day, the firm's materials listed "Multiple Affiliation Options," "Best of Both Worlds," "Advisor and Book Ownership" and "Stability." They also listed recruiting, retention and advisor productivity as Private Client Group strategic initiatives.
   - `RJF-DECK-2025-investor-day#49` (deck, 2025-06-05): "Multiple Affiliation Options Best of Both Worlds Advisor and B ook Ownership R J F Stability Inspire and empower the world's best financial professionals."
   - `RJF-DECK-2025-investor-day#40` (deck, 2025-06-05): "RETENTION ADVISOR PRODUCTIVITY RECRUIT ING"
6. The firm invests financially in recruiting. On the fiscal 4Q25 call (October 2025), the CFO said adjusted compensation expense in fiscal 2025 included amortization of transition assistance to recruited advisors and retention awards to existing advisors totaling $355 million, up approximately 11% from fiscal 2024. In the segment supplement for the quarter ended December 31, 2025, PCG recruiting and retention-related compensation was $107 million, up 22% from December 31, 2024. The firm says these awards are expensed over the requisite service period, typically between 5 and 10 years.
   - `RJF-TR-2025Q3#20` (transcript, 2025-10-22): "Butch Oorlog CFO at Raymond James Keep in mind, there are many variables which could influence actual results, including any interest rate actions during the upcoming quarter and factors affecting our balance sheet, incl..."
   - `RJF-SUPP-2025Q4#12` (supplement, 2026-01-28): "/ $ in millions / Three months ended - December 31, 2024 / Three months ended - March 31, 2025 / Three months ended - June 30, 2025 / Three months ended - September 30, 2025 / Three months ended - December 31, 2025 / % c..."
   - `RJF-SUPP-2026Q2#45` (supplement, 2026-07-22): "PCG recruiting and retention-related compensation includes expenses related to cash and equity awards issued in conjunction with recruiting activities, as retention for existing advisors, or in conjunction with our acqui..."
7. On the fiscal 1Q26 call (January 2026), Shoukry said the firm would "much rather recruit one by one," where advisors are a good cultural fit and 100% of transition assistance goes to retention rather than to a seller. He compared its recruiting volume to "a pretty decent size acquisition." The firm's 10-Qs (filed February, May and August 2026) cite higher business development expenses tied to financial advisor recruiting.
   - `RJF-TR-2025Q4#44` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial Yeah, I mean, there's a lot of investment that goes into recruiting. The reason we broke out the retention and transition assistance-related expense for the first time this qua..."
   - `RJF-10Q-2025Q4#199` (10-Q, 2026-02-06): "Compensation, commissions and benefits expense increased 8%, primarily due to an increase in compensable revenues in the PCG segment, and an increase in compensation costs to support our growth, including financial advis..."
   - `RJF-10Q-2026Q1#239` (10-Q, 2026-05-06): "Compensation, commissions and benefits expense increased 15%, primarily due to an increase in commissions expense resulting from higher asset management and related administrative fees and brokerage revenues in the PCG s..."
   - `RJF-10Q-2026Q2#252` (10-Q, 2026-08-05): "Non-compensation expenses increased 4%, primarily due to an increase in expenses related to our growth, including higher communications and information processing expenses resulting from continued investments in technolo..."
8. Risk the firm names: the 2025 10-K says it participates, with limited exceptions, in the Protocol for Broker Recruiting, a voluntary agreement that governs the client information advisors may take and their ability to solicit prior-firm clients. The firm notes that competitors may withdraw from it. It also says it has been subject to claims of unfair hiring practices, which could result in material litigation and discourage potential recruits.
   - `RJF-10K-2025#91` (10-K, 2025-11-25): "Moreover, companies in our industry whose employees or independent contractors accept positions with competitors frequently claim that those competitors have engaged in unfair hiring practices. We have been subject to se..."

**Gaps (named by the answer)**

- A breakdown of Raymond James recruits by prior firm type (wirehouse versus other) is not found in the evidence provided. The firm's statements refer to previous firms and affiliation options generally, not to wirehouses specifically. The only wirehouse-specific reference is trade-press reporting on UBS. *Would fill it:* Raymond James earnings call Q&A or investor presentations on recruit sources; advisor recruiting trade press

### Q3: What is Schwab's strategy for its RIA custody business?

**Verdict: FAIL** (s). Framing and priorities, but nothing on ground management concedes and no gap naming that part.

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It describes how Schwab frames the advisor-services business, its stated priorities, and the competitive pressure management acknowledges -- including where they concede ground.

**Claims**

1. The 2025 10-K (published 2026-02-25) describes the Advisor Services segment as providing custodial, trading, banking and trust, and support services to independent RIAs, independent retirement advisors, and recordkeepers.
   - `SCHW-10K-2025#11` (10-K, 2026-02-25): "Schwab provides financial services to individuals and institutional clients through two segments - Investor Services and Advisor Services. The Investor Services segment provides retail brokerage, investment advisory, and..."
2. The 2025 10-K states that RIAs and their clients have access to Schwab's broad range of wealth services (individual securities, mutual funds, ETFs, alternative investments, fixed income, managed accounts, cash products, bank lending, trust services). As custodian, Schwab earns revenue tied to the underlying client assets, predominantly net interest revenue and asset management and administration fees, and does not charge the RIA or end client a custody fee.
   - `SCHW-10K-2025#26` (10-K, 2026-02-25): "Schwab provides extensive educational materials, programs, and events to RIAs seeking to expand their knowledge of industry issues and trends, as well as sharpen their individual expertise and practice management skills...."
3. The 2025 10-K describes Schwab's educational and event support for RIAs, including industry research, practice-management programs and the annual IMPACT conference.
   - `SCHW-10K-2025#26` (10-K, 2026-02-25): "Schwab provides extensive educational materials, programs, and events to RIAs seeking to expand their knowledge of industry issues and trends, as well as sharpen their individual expertise and practice management skills...."
4. The 2025 10-K names competitors in Advisor Services: institutional custodians, wirehouses, regional and independent broker-dealers, fintech custodians, banks, and trust companies. It says the firm's overall strategy rests on the principle that trusted relationships bring more assets from new and existing clients, which drives revenue. Management lists scale as a key competitive advantage across both segments.
   - `SCHW-10K-2025#13` (10-K, 2026-02-25): "Management estimates that investable wealth in the United States (U.S.) (consisting of assets in defined contribution, retail wealth management and brokerage, and registered investment advisor channels, along with bank d..."
5. On the 1Q25 earnings call (April 2025), CEO Rick Wurster said Schwab is a leader in two of the fastest-growing segments of financial services, self-directed investors and registered investment advisors. He cited being number one in RIA custodial assets.
   - `SCHW-TR-2025Q1#9` (transcript, 2025-04-17): "Rick Wurster President and CEO at Charles Schwab In the first quarter, total revenue increased 18% year-over-year to $5.6 billion, and adjusted earnings per share increased 41% over the first quarter of 2024. We are off ..."
6. On the 3Q25 earnings call (October 2025), Wurster said Schwab is deepening relationships with the 16,000 RIA firms it serves by building "a broader support ecosystem that extends beyond custody alone." He cited more lending support, more alternatives capability, an institutional no-transaction-fee mutual fund platform expanded to funds from nearly 60 managers, and the launch of Advisor ProDirect for breakaway advisors.
   - `SCHW-TR-2025Q3#13` (transcript, 2025-10-16): "Rick Wurster President and CEO at Schwab Finally, we remain committed to our four strategic focus areas to meet the evolving needs of our clients. At the start of the year, I laid out our priorities: growth, scale and ef..."
7. In the 2Q26 results release (July 2026), Schwab noted that long/short strategy interest remained strong among RIA clients. Margin loan debits were $42.1 billion and short cash credits were $43.7 billion as of June 30, 2026.
   - `SCHW-PR-2026-07-21-01#2` (press, 2026-07-21): "ults across a range of environments. During the second quarter, strong client engagement helped drive year-over-year revenue growth of 21% to a record $7.1 billion.” 2Q26 Revenue CFO Mike Verdeschi Growth vs. 2Q25 Strong..."
8. The 2Q26 deck (July 2026) says Schwab "remains the trusted platform of choice for investors & RIAs" and shows it ranked #1 in RIA custodial assets. On the 3Q26 call (October 2026), Wurster repeated that Schwab is #1 by RIA custodial assets.
   - `SCHW-DECK-2026Q2#14` (deck, 2026-07-21): "Schwab remains the trusted platform of choice for investors & RIAs. Ranked #1 $13.1T 11.9M $5.7T Total Client Assets in RIA Custodial Assets Daily Average Trades"
   - `SCHW-TR-2026Q3#4` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director We remain the trusted platform of choice for investors and registered investment advisers. We are #1 by total client assets, #1 by RIA custodial assets and #1 in daily ave..."
   - `SCHW-DECK-2026Q3#11` (deck, 2026-10-15): "#1 Total Client Assets 1.8B Total Client Interactions 1 #1 RIA Custodial Assets #1 Daily Average Trades ~1.8x TOA Ratio 2 ~$3.8T Monthly Money Movement 3"
9. Trade press (WealthManagement.com, 2026-10-28, indicative only) reports Wurster told advisors at Schwab Impact that Schwab will continue to focus on custody for RIAs with under $100 million AUM. It quotes him saying Schwab's role is "to provide a platform and a support ecosystem that helps you support your clients and helps your firm thrive." The article links this to Fidelity's move to require firms under $100 million to leave its platform by June 30, 2027.
   - `SCHW-TRADE-2026-10-28-WM-01#0` (trade, 2026-10-28): "Schwab CEO Wurster Commits to Small RIAs WealthManagement.com trade press - 2026-10-28 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ria-news/schwab-ceo-wurster-commits-to-rias-with-client-assets-und..."

**Gaps (named by the answer)**

- The evidence has no dedicated, detailed statement of Advisor Services strategy such as targets, pricing or investment plans for RIA custody. It also lacks segment financials for Advisor Services. *Would fill it:* Schwab Advisor Services segment discussion in the 10-K/10-Q MD&A, and the Investor Day or Spring Business Update presentation on Advisor Services

### Q4 (trap): What is Merrill's advisor growth strategy, and how has it changed?

**Verdict: PASS**. Trap held: every claim Merrill-specific or labelled GWIM; training pipeline, sourcing shift (experienced recruiting 'not an enormous part'), 5% guide; headcount marked as a gap.

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* Every claim is about Merrill specifically -- the advisor development pipeline, headcount trajectory, the stated shift in how advisors are sourced -- and nothing about Bank of America's consumer bank or BAC-wide hiring is presented as Merrill's strategy.

**Claims**

1. On the 1Q25 earnings call (April 2025), the CFO said GWIM expense growth of 9% supported technology investment and "the cost of hiring to add experienced advisors to the platform in Merrill and the private bank." This statement covers Merrill and the Private Bank together (GWIM segment).
   - `BAC-TR-2025Q1#28` (transcript, 2025-04-15): "Alastair Borthwick CFO at Bank of America The number of clients that have banking products with us continues to grow also and is now approaching two-thirds of the client base. Importantly, about 30% of our revenue remain..."
2. On the 2Q25 earnings call (July 2025), the CFO said the firm "continued to add financial advisors to the sales force in Merrill and the Private Bank through our extensive training program and experienced hiring of advisors." He said approximately one-third of net new households in Q2 were added by newly trained advisors. He again cited the cost of hiring experienced advisors in Merrill and the Private Bank as an expense driver.
   - `BAC-TR-2025Q2#34` (transcript, 2025-07-16): "Alastair Borthwick CFO at Bank of America Merrill and the Private Bank now manage nearly $4.4 trillion in client balances and continue to see organic growth that produced strong AUM flows of $82 billion in the past year,..."
   - `BAC-TR-2025Q2#35` (transcript, 2025-07-16): "Alastair Borthwick CFO at Bank of America We're not only growing relationships, but we're also deepening as the number of clients that have banking products with us grew to nearly 63%. While this is primarily a fee-based..."
3. The GWIM Foundational Beliefs slide from the November 2025 investor day says management believes "having the best advisors enables us to deliver exceptional client outcomes". It also says growth of fully advised client relationships "drives financial outcomes".
   - `BAC-DECK-2025-investor-day#8` (deck, 2025-11-05): "We believe… …growth of our fully advised client relationships drives financial outcomes …the Wealth Continuum allows us to deliver as one company and is our engine for lasting growth …having the best advisors enables us ..."
4. On the 4Q25 earnings call (January 2026), the CFO said Merrill financial advisors see the value of the franchise and "we're picking up the recruiting of experienced advisors." He said that "isn't an enormous part of our strategy" and described a training program for people in wealth management, Bank of America and Merrill. He said management believes it can keep driving that program to improve net new flows.
   - `BAC-TR-2025Q4#106` (transcript, 2026-01-14): "Alastair Borthwick CFO at Bank of America I think the Merrill FA see the value of our franchise and how they can help their own clients over a long period of time, and we're picking up the recruiting of experienced advis..."
5. On the 1Q26 earnings call (April 2026), the CFO said management is focused on "adviser productivity" and is "driving productivity higher on both newer and existing members of our financial advisers team." He said the firm continues "to attract talent across both new and experienced advisers."
   - `BAC-TR-2026Q1#26` (transcript, 2026-04-15): "Alastair Borthwick Chief Financial Officer Pretax margin was 26%, reflecting the operating leverage achieved through disciplined expense management. Client balances increased to $4.6 trillion, up 10% year-over-year suppo..."
6. On the 2Q26 earnings call (July 2026), the CFO said both Merrill and the Private Bank "continued to attract talented advisers who are drawn to the breadth of our platform." He said strong adviser productivity, digital engagement and new AI-enabled tools help advisers prepare for client conversations and deliver personalized advice at scale.
   - `BAC-TR-2026Q2#20` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO Turning to Slide 14. GWIM delivered another outstanding quarter, highlighted by record revenue and pretax income, expanded profit margins, and continued client growth. Clients con..."
   - `BAC-TR-2026Q2#21` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO Franchise continued to benefit from strong adviser productivity, growing digital engagement and new AI-enabled tools that help advisers prepare for client conversations, identify ..."
7. On the 2Q26 call (July 2026), the CFO referred to the Merrill 5% guide, aiming for 5% over the next 3 to 5 years, and said the firm is "off to a good start". He said the goal for Merrill leadership is to "just keep growing the sales force." He also said "adviser attrition is now at near historic lows" and that "we've got more to do."
   - `BAC-TR-2026Q2#63` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO First, I think you were referring to the Merrill 5% guide, where we said we are aiming for 5% over the course of the next 3 to 5 years. It's been 7 months, and I think we're off t..."
8. On the 3Q26 call (October 2026), the CFO said Merrill added about 4,200 net new households with at least $500,000 in assets, up 17%. He said the results reflect demand for advice and "our ability to attract clients and experienced advisers to the platform." He cited advisor productivity, digital engagement and AI tools as expanding capacity to deliver personalized advice at scale.
   - `BAC-TR-2026Q3#19` (transcript, 2026-10-14): "Alastair Borthwick Client balances climbed above $5 trillion for the first time, up 9%, while AUM rose 12% to about $2.4 trillion. Quarterly net client flows were about $38 billion, including approximately $20 billion of..."
9. A Merrill press release (15 September 2026) announced the Tax Efficient Transition Service and Dollar Cost Averaging Service. The head of Managed Account Advisors at Merrill said they reflect "a continued focus on making it easier for advisors to implement personalized investment strategies at scale."
   - *Flagged by code:* number_not_found
   - `MER-PR-2026-09-15-01#0` (press, 2026-09-15): "Merrill Launches New Services to Support Portfolio Transitions and Systematic Cash Investing Merrill press release - 2026-09-15 Source: Bank of America Newsroom, Global Wealth and Investment Management category. Key poin..."
   - `MER-PR-2026-09-15-01#2` (press, 2026-09-15): "Both services are optional and available to clients, with no additional IAP Program Fees charged. They are available through IAP and are implemented by Managed Account Advisors LLC (MAA), Merrill’s centralized team that ..."
10. Merrill's advisor recruiting pages (page content as of 2026-11-03) pitch experienced advisors on the brand and on infrastructure supporting lead generation through Bank of America's bank and trust division. They also pitch access to Merrill's wealth management platform and Bank of America's banking and trust capabilities. A separate Advisor Development Program page describes roles meant to help new advisors "build your book of high-net worth clients."
   - `MER-PR-web-becoming-a-merrill-lynch-advisor#0` (press, 2026-11-03): "Accelerate your business growth at Merrill Merrill advisor recruiting page - content as of 2026-11-03 Source: https://careers.bankofamerica.com/en-us/becoming-a-merrill-lynch-advisor (fetched 2026-11-03) Content as of: 2..."
   - `MER-PR-web-advisor-development-program#0` (press, 2026-11-03): "Advisor Development Program Merrill advisor recruiting page - content as of 2026-11-03 Source: https://careers.bankofamerica.com/en-us/career-development/advisor-development-program (fetched 2026-11-03) Content as of: 20..."

**Adjacent evidence (a related but different quantity)**

1. The 2025 10-K (published 2026-02-25) reports GWIM net income up $407 million to $4.7 billion, with an operating margin of 25 percent in both 2025 and 2024.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-10K-2025#246` (10-K, 2026-02-25): "Merrill Wealth Management’s advisory business provides a high-touch client experience through a network of financial advisors focused on clients with over $250,000 in total investable assets. Merrill Wealth Management pr..."
2. WealthManagement.com (2026-11-03) and InvestmentNews (2026-11-12 and 2026-10-14) report individual advisors leaving Merrill for JPMorgan, an RIA and LPL.
   - *Differs because:* Trade-press reporting is indicative, not authoritative.
   - `MER-TRADE-2026-11-03-WM-01#0` (trade, 2026-11-03): "JPMorgan Adds Merrill Alums To Boost California, Southeast Business WealthManagement.com trade press - 2026-11-03 (tier 4, indicative only) Source: https://www.wealthmanagement.com/wirehouse-news/jpmorgan-lures-940-milli..."
   - `MER-TRADE-2026-11-12-IN-01#0` (trade, 2026-11-12): "Merrill veteran Jonathan Stogsdill joins Trinity Wealth Advisors in St. Louis InvestmentNews trade press - 2026-11-12 (tier 4, indicative only) Source: https://www.investmentnews.com/wirehouses/merrill-veteran-jonathan-s..."
   - `MER-TRADE-2026-10-14-IN-02#2` (trade, 2026-10-14): "On the West Coast, Economos Private Wealth launched from Danville, Calif., outside San Francisco. Nick Economos brings more than 25 years of industry experience serving corporate executives, business owners and multigene..."

**Gaps (named by the answer)**

- Merrill does not report standalone results. *Would fill it:* Bank of America earnings supplement or 10-K GWIM disclosures (segment level only)
- The evidence does not state a numeric advisor headcount target, advisor attrition rate or hiring volume for Merrill. It also does not say what the "5%" guide measures. *Would fill it:* Bank of America investor day transcript or slides (November 2025) and management commentary defining the Merrill 5% guide

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q5: Where is Morgan Stanley investing in technology for its advisors?

**Verdict: PASS**. Named platform with purpose (LeadIQ), non-advisor tools labelled as such; spend only where disclosed, firmwide figures labelled.

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It names actual platforms and initiatives with management's stated purpose for each. Spend figures appear only where disclosed -- never estimated, never rounded from a trade-press characterisation.

**Claims**

1. On the 1Q25 earnings call (April 2025), CEO Ted Pick said the financial advisor sees the integrated firm offering "unique access to intellectual capital, world-class technology, compensation that is viewed to be fair and motivating." This is general positioning, not a named advisor tool.
   - `MS-TR-2025Q1#54` (transcript, 2025-04-11): "Ted Pick Chairman and CEO at Morgan Stanley People are coming toward the platform. Jed Finn and Vince Lumia's lights are blinking, as in their phone lights, nonstop. Folks want to come onto this platform. That is in part..."
2. On the 3Q25 earnings call (October 2025), CFO Sharon Yeshaya named early AI use cases, some live and some in pilot. The advisor-facing one is LeadIQ, which she described as an "AI-powered lead distribution platform, focusing on matching workplace and self-directed relationships and facilitating engagement with our financial advisors." The other two, DevGen AI (developer efficiency, code modernization) and Parable (data analysis and summarization), are not described as advisor tools.
   - `MS-TR-2025Q3#8` (transcript, 2025-10-15): "Sharon Yeshaya CFO at Morgan Stanley Thank you and good morning. The firm delivered exceptional results in the third quarter, underscoring the power of our global integrated firm and the scale of $8.9 trillion in total c..."
3. The 3Q25 10-Q (November 2025) says Wealth Management non-compensation expenses increased primarily from higher marketing and business development costs and increased technology spend.
   - `MS-10Q-2025Q3#63` (10-Q, 2025-11-03): "The Provision for credit losses on loans and lending commitments of $71 million in the current year period was primarily related to certain specific loans in our tailored lending and residential real estate portfolios, a..."
4. On the 4Q25 call (January 2026), Ted Pick said the firm continues to invest in each of its three segments, including Wealth, "via human capital and technology." He said growth plans embed increasing adoption of AI tools across the enterprise and the client base.
   - `MS-TR-2025Q4#8` (transcript, 2026-01-15): "Ted Pick Chairman and CEO at Morgan Stanley We continue to invest in each of our three business segments: Wealth, Institutional Securities, and Investment Management via human capital and technology. Our growth plans emb..."
5. On the same 4Q25 call (January 2026), Pick referred to "ongoing investments we're making" in AI in core technology and in AI efficiency and effectiveness tools. He expects continued operating leverage if markets are constructive and the firm executes.
   - `MS-TR-2025Q4#65` (transcript, 2026-01-15): "Ted Pick Chairman and CEO at Morgan Stanley That was very clever. I did read your report.You are trying to get at moving the goals without moving the goals. Yeah.I mean, Sharon put some meat on the bone, but of course, w..."
6. On the 1Q26 call (April 2026), Pick described the firm's technology as "world-class technology, world-class cyber defense" and said it is additive to "the best trusted advisers sitting with the client." He called the adviser relationship "the key." His AI examples there were in equities and core infrastructure, not advisor tools.
   - `MS-TR-2026Q1#44` (transcript, 2026-04-15): "Edward N. Pick CEO & Chairman of the Board I'd also say that this phenomenon is taking place inside of our equities business, where, as you know, we have a leadership business where we are able to take some of the comple..."
7. The 2Q26 10-Q (August 2026) attributes the firmwide increase in non-compensation expenses of 19% for the quarter and 14% for the year-to-date period partly to increased technology spend. This is not broken out for advisors.
   - `MS-10Q-2026Q2#20` (10-Q, 2026-08-04): "• Compensation and benefits expenses of $8,187 million in the current quarter and $16,729 million in the current year period increased 14% compared with the prior year periods, primarily due to an increase in the formula..."
8. On the 3Q26 call (October 2026), Yeshaya said the firm continues to invest across its technology stack, "embracing AI tools to support our infrastructure, business growth and people." She also said the firm's scale "supports continued investment in future technology, including AI and digital tools."
   - `MS-TR-2026Q3#8` (transcript, 2026-10-14): "Sharon Yeshaya Executive VP & CFO Thank you, and good morning. In the third quarter, the firm delivered strong results, revenues of $20.3 billion, EPS of $3.03 and an ROTCE of 22.6%. Growth momentum from the second quart..."
   - `MS-TR-2026Q3#16` (transcript, 2026-10-14): "Sharon Yeshaya Executive VP & CFO Since acquiring E*TRADE and expanding our workplace offering 6 years ago, we have added over $2 trillion of net new assets. Our multiyear track record demonstrates our differentiated cli..."
9. On the 3Q26 call (October 2026), Pick said that if the technology is world-class, clients make decisions with their financial advisers. He said technology "can help do a lot of the early work" on clients' needs, and that the firm will keep investing "whatever it takes" to protect clients.
   - `MS-TR-2026Q3#35` (transcript, 2026-10-14): "Edward N. Pick CEO & Chairman of the Board Third, and this is critical, is the ability to protect client assets. We're one of a very few number of firms that can continue to invest whatever it takes to protect our client..."
10. The 3Q26 press release (October 2026) says Wealth Management non-compensation expenses increased from a year ago primarily from higher technology spend and marketing and business development expenses.
   - `MS-PR-2026-10-14-01#5` (press, 2026-10-14): "Wealth Management reported record net revenues of $9.1 billion compared with $8.2 billion a year ago. Record pre-tax income of $2.8 billion resulted in a pre-tax margin of 30.4%. 4,14 Record net new assets were $232 bill..."

**Gaps (named by the answer)**

- Specific advisor-facing technology investments beyond LeadIQ (for example advisor desktop, planning or AI assistant tools) and the dollar amount of technology spend for Wealth Management advisors are not found in the evidence provided. *Would fill it:* Morgan Stanley Wealth Management investor-day or strategic-update decks, 10-K technology discussion, and earnings-call Q&A on advisor AI tools

### Q6: What has Raymond James said about its affiliation models, and has the mix shifted?

**Verdict: PASS**. Options as the firm describes them (10-K, Advisor Select, five options, Corporate RIA); mix movement quoted from management oldest first, incl. the employee-option uptick; no quantified mix, said so.

Tier 1, use case `entity_brief`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It lays out the affiliation options as the firm describes them and reports any disclosed movement in the mix, with the disclosure quoted rather than characterised.

**Claims**

1. What the firm says it offers - the FY2025 10-K (period ended 2025-09-30, published 2025-11-25) states that Raymond James offers multiple affiliation options, which it calls AdvisorChoice®. Advisors primarily affiliate directly as employees or independent contractors, or as employees of third-party RIAs and broker-dealers served through its RIA and Custody Services (RCS) division.
   - `RJF-10K-2025#10` (10-K, 2025-11-25): "We offer multiple affiliation options, which we refer to as AdvisorChoice®. Financial advisors primarily affiliate with us directly as either employees or independent contractors or as employees of third-party Registered..."
2. What the firm says it offers - Raymond James's investor day deck (published 2025-06-05) lists "Multiple Affiliation Options" as a theme in its recap.
   - `RJF-DECK-2025-investor-day#49` (deck, 2025-06-05): "Multiple Affiliation Options Best of Both Worlds Advisor and B ook Ownership R J F Stability Inspire and empower the world's best financial professionals."
3. What the firm says it offers - Raymond James's recruiting page (page content as of 2026-03-11) describes Advisor Select® as an employee affiliation option. It gives established advisors the full benefits of the employee channel with the independence to create their own branches, and lets them run the branch's P&L to earn a higher rate on production.
   - `RJF-PR-web-advisor-select#0` (press, 2026-03-11): "Raymond James Advisor Select® Raymond James advisor recruiting page - content as of 2026-03-11 Source: https://web.archive.org/web/20260311101214/https://www.raymondjames.com/advisor-opportunities/affiliation-options/adv..."
4. What the firm says it offers - Raymond James's affiliation-options page (content as of 2026-04-21) lists five AdvisorChoice® options: Traditional Employee, Advisor Select, Independent Contractor, Bank & Credit Union, and Corporate RIA.
   - `RJF-PR-web-affiliation-options#0` (press, 2026-04-21): "Raymond James Affiliation options Raymond James advisor recruiting page - content as of 2026-04-21 Source: https://web.archive.org/web/20260421065839/https://www.raymondjames.com/advisor-opportunities/affiliation-options..."
5. What the firm says it offers - Raymond James's independent-advisor web page (page content as of 2026-05-19) describes a Corporate RIA affiliation model. The firm says it lets fee-based advisors get the RIA experience while streamlining many of its burdens.
   - `RJF-PR-web-independent-advisor#1` (press, 2026-05-19): "Succession and acquisition: Make career-critical decisions with specialized guidance Business consulting Unlock the power of independence with the support of consultants dedicated to helping advisors navigate business ow..."
6. Mix over time (oldest first) - On the call for the quarter ended 2024-09-30 (published October 2024), then-CEO Paul Reilly said RCS had by far the highest percentage growth. In total dollars, he said independent led a couple of years earlier, but that year the employee channel "really led the way". He said the firm no longer sees the old pattern of independents growing faster in up markets. He said he expected some cyclical improvement in the independent contractor model, and that the employee side and RCS had good backlogs.
   - `RJF-TR-2024Q3#66` (transcript, 2024-10-23): "Paul Reilly Chair and CEO at Raymond James Financial You know, it depends on how you want to look at it. In our RIA part, RCS, it is by far the highest percentage growth. And, you know, as consistent with industry trends..."
7. Mix over time - On the call for the quarter ended 2025-06-30 (published July 2025), CEO Paul Shoukry said the advisor recruiting pipeline was "growing significantly across all of our affiliation options".
   - `RJF-TR-2025Q2#21` (transcript, 2025-07-23): "Paul Shoukry CEO at Raymond James Financial As we enter the fourth quarter, we are encouraged by the strong tailwinds arising from fee-based assets up 8%. Net loans higher by 3%, and strong pipelines for growth across ou..."
8. Mix over time - On the call for the quarter ended 2025-12-31 (published January 2026), Shoukry said advisors are coming from wires, regionals and other independents. He said Raymond James has the largest addressable market across its affiliation options (employee, independent contractor and RIA custody), with critical mass and decades of experience in all of them.
   - `RJF-TR-2025Q4#50` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial Yeah, I mean, I hate to speak on any specific M&A or transactions. We have a lot of friendly competitors, and they're doing, you know, good jobs keeping the advisors, you know,..."
9. Mix over time - In the earnings release for the quarter ended 2026-03-31 (published 2026-04-22), Shoukry said advisor recruiting activity "across all our affiliation options remains robust".
   - `RJF-PR-2026-04-22-01#1` (press, 2026-04-22): "ST. PETERSBURG, Fla. - Raymond James Financial, Inc. (NYSE: RJF) today reported net revenues of $3.86 billion and net income available to common shareholders of $542 million, or $2.72 per diluted share, for the fiscal se..."
10. Mix over time - On the call for the quarter ended 2026-03-31 (published April 2026), an analyst asked whether the mix-shift headwind would persist, given expected momentum in the independent channel. Shoukry said the firm is seeing a good uptick in the employee option too. He said the mix shift he had referred to concerned the comp ratio more than the margin, because of the payout difference between the independent and employee channels. He said momentum is good across all options and that employee-side success "continues to tick up".
   - `RJF-TR-2026Q1#45` (transcript, 2026-04-22): "Operator Your next question comes from the line of Steven Chubak with Wolfe Research. Steven Joseph Chubak Wolfe Research, LLC Paul, Butch, hope you're well. Yes. So maybe just to double-click on Brennan's line of questi..."
   - `RJF-TR-2026Q1#46` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director Yes. No, we're actually seeing pretty good uptick in the employee affiliation option as well. And the mix shift is really what I was referring to more about the comp ratio than the marg..."
11. Mix over time - On the call for the quarter ended 2026-06-30 (published July 2026), Shoukry described the pipeline as "still strong and robust across the different affiliation options". He called the momentum "broad-based strength" across the options and said recruited teams are weighing the pros and cons of each option.
   - `RJF-TR-2026Q2#31` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director Yes. I mean the pipeline is still strong and robust across the different affiliation options. There's a team yesterday with $5 million of production that came, and they're actually inte..."

**Adjacent evidence (a related but different quantity)**

1. WealthManagement.com (published 2026-10-29) reported that Shoukry said, on the fiscal fourth-quarter call, that recruiting success is spread across all affiliation channels. It reported that the independent contractor channel is seeing the most interest in dollar volume, while RIA custody is growing at a high percentage rate on a smaller base.
   - *Differs because:* Trade-press reporting is indicative, not authoritative.
   - `RJF-TRADE-2026-10-29-WM-01#0` (trade, 2026-10-29): "Raymond James Recruiting Across Affiliation Models WealthManagement.com trade press - 2026-10-29 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ibd-news/raymond-james-recruiting-surges-assets-hit-187-..."
2. The 10-Q for the quarter ended 2026-06-30 (published 2026-08-05) says the year-to-date rise in the total compensation ratio reflected a shift in revenue mix toward revenues with higher direct compensation, including asset management and related administrative fees and brokerage revenues.
   - *Differs because:* This is a revenue-mix shift, not a shift in the mix of advisors across affiliation models.
   - `RJF-10Q-2026Q2#251` (10-Q, 2026-08-05): "Compensation, commissions and benefits expense increased 13%, primarily due to higher commissions expense resulting from an increase in asset management and related administrative fees and brokerage revenues in the PCG s..."

**Gaps (named by the answer)**

- No quantified mix of advisors, assets or production by affiliation model (employee, independent contractor, RCS) over time was found. The evidence is qualitative management commentary only, so whether the mix has shifted cannot be measured from it. *Would fill it:* Raymond James 10-K or 10-Q PCG financial advisor headcount by channel, monthly operating metrics, or investor-day disclosures

### Q7: How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

**Verdict: FAIL** (s). A grid now, but only two dimensions (recruiting, retention); payout philosophy and training pipeline missing; Morgan Stanley cells empty although its formulaic payout is in the corpus; three empty-cell statements carry no citation (flagged by code).

Tier 2, use case `head_to_head`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity+theme`.

*Passes if:* The same dimensions are applied to all three -- recruiting posture, payout philosophy, training pipeline, disclosed retention results -- every cell cited, and empty cells left visibly empty rather than filled with something reasonable.

**Claims**

1. Recruiting - Morgan Stanley: no advisor-recruiting statement from Morgan Stanley is in the evidence provided (see gaps).
   - *Flagged by code:* no_citation
2. Recruiting - Merrill: On the 1Q25 Bank of America earnings call (April 2025), the CFO said GWIM expense growth of 9% supported, among other things, the cost of hiring to add experienced advisors to the platform in Merrill and the private bank.
   - `BAC-TR-2025Q1#28` (transcript, 2025-04-15): "Alastair Borthwick CFO at Bank of America The number of clients that have banking products with us continues to grow also and is now approaching two-thirds of the client base. Importantly, about 30% of our revenue remain..."
3. Recruiting - Merrill: Merrill's Advisor Development Program recruiting page (page content as of 2026-11-03) describes roles designed to help advisors meet clients, identify financial goals, align banking and investing solutions and build a book of high-net-worth clients. It pitches a career in wealth management with 'unlimited growth and earning potential'.
   - `MER-PR-web-advisor-development-program#0` (press, 2026-11-03): "Advisor Development Program Merrill advisor recruiting page - content as of 2026-11-03 Source: https://careers.bankofamerica.com/en-us/career-development/advisor-development-program (fetched 2026-11-03) Content as of: 20..."
4. Recruiting - Merrill: Trade press (published 2026-11-16) reports that Merrill executives in October touted recruited assets to the wealth unit doubling year over year as the firm returned to veteran broker recruiting. It says Merrill largely pulled back from veteran recruiting at the end of 2017, and that Co-Presidents Lindsay Hans and Eric Schimpf, who took over in 2023, restored a focus on hiring and a more aggressive offer. It also lists recent hires from UBS, Morgan Stanley and Edward Jones. This is trade-press reporting, not a firm filing.
   - `MER-TRADE-2026-11-16-AH-01#1` (trade, 2026-11-16): "The move came the same day as another UBS broker, Franklin J. Laden, joined Merrill in Denver. He managed $375 million in assets and joined an existing team, the LDSO Group, at Merrill, according to the spokesperson. Lad..."
5. Recruiting - Raymond James: On the fiscal 4Q25 call (October 2025), CEO Paul Shoukry said the firm ended the fiscal year with a record number of financial advisors, 2% higher than the prior year. He cited a robust recruiting pipeline and strong commitments to join in coming quarters, and said the 'best-of-both-worlds' value proposition resonates across all affiliation options. He also named the firm's balance sheet and commitment to independence as differentiators.
   - `RJF-TR-2025Q3#8` (transcript, 2025-10-22): "Paul Shoukry CEO at Raymond James Quarterly domestic net new assets were nearly $18 billion this quarter, representing a 5% annualized growth rate. We ended the fiscal year with a record number of financial advisors, 2% ..."
6. Recruiting - Raymond James: In its fiscal 2Q26 earnings release (April 22, 2026), the CEO said financial advisor recruiting activity across all affiliation options 'remains robust'.
   - `RJF-PR-2026-04-22-01#1` (press, 2026-04-22): "ST. PETERSBURG, Fla. - Raymond James Financial, Inc. (NYSE: RJF) today reported net revenues of $3.86 billion and net income available to common shareholders of $542 million, or $2.72 per diluted share, for the fiscal se..."
7. Recruiting - Raymond James: The 10-Q for the period ended June 30, 2026 (published August 2026) cites compensation costs tied to growth, including financial advisor recruiting and retention-related compensation expenses. It also cites financial advisor recruiting-related expenses in non-compensation costs. It attributes net new assets to financial advisor recruiting and retention.
   - `RJF-10Q-2026Q2#316` (10-Q, 2026-08-05): "Compensation-related expenses increased $321 million, or 18%, primarily due to higher commissions expense resulting from higher asset management and related administrative fees and brokerage revenues, as well as an incre..."
8. Retention - Morgan Stanley: no advisor-retention statement from Morgan Stanley is in the evidence provided (see gaps).
   - *Flagged by code:* no_citation
9. Retention - Merrill: no Merrill advisor-retention statement is in the evidence provided (see gaps).
   - *Flagged by code:* no_citation
10. Retention - Raymond James: On the fiscal 4Q25 call (October 2025), the CEO described the record advisor count as reflecting 'solid advisor retention' as well as strong recruiting. He said the firm continues to invest in its platform and offerings to retain and attract advisors.
   - `RJF-TR-2025Q3#8` (transcript, 2025-10-22): "Paul Shoukry CEO at Raymond James Quarterly domestic net new assets were nearly $18 billion this quarter, representing a 5% annualized growth rate. We ended the fiscal year with a record number of financial advisors, 2% ..."
11. Retention - Raymond James: The fiscal 2025 10-K (published November 2025) names advisor departures as a risk, including to independent RIAs, some backed by private equity, which has produced a 'highly competitive recruiting environment'. It says reported AUA may be negatively affected if the firm fails to retain or recruit advisors. The firm says it seeks to mitigate this through financial advisor succession planning and a broad range of services and resources to support advisors' practices.
   - `RJF-10K-2025#90` (10-K, 2025-11-25): "Our PCG business is subject to risks arising from the continued industry-wide trend in which financial advisors are departing traditional firms, including to form independent RIAs or to join existing third-party RIAs, so..."

**Adjacent evidence (a related but different quantity)**

1. The Morgan Stanley 2025 10-K (published 2026-02-19) says its talent development programs are designed to help employees achieve career goals, and that the firm believes supporting employee development and growth contributes to long-term retention.
   - *Differs because:* It describes talent development for all employees, not advisor recruiting or retention specifically.
   - `MS-10K-2025#51` (10-K, 2026-02-19): "Our clearly defined and long-standing core values guide decision-making aligned with the expectations of our employees, clients, shareholders, regulators, directors and the communities in which we operate. Our Code of Co..."
2. On the 1Q26 call (April 2026), Morgan Stanley's CFO described greater retention of vested Workplace assets and migration of those assets to advice.
   - *Differs because:* It concerns retention of client assets from the Workplace channel, not retention of advisors.
   - `MS-TR-2026Q1#24` (transcript, 2026-04-15): "Sharon Yeshaya Executive VP & CFO Specifically, with this quarter, you'll see that often and not surprisingly that in the first quarter, you'll see unvested assets vest. And what we saw in Workplace this quarter is great..."

**Gaps (named by the answer)**

- Morgan Stanley - recruiting: not found in the evidence provided. The only advisor-related item is an analyst's question about advisor retention, recruitment and backlogs, with no management answer included. *Would fill it:* Morgan Stanley earnings call transcripts (Wealth Management Q&A), investor presentations, and the 10-K Wealth Management discussion
- Morgan Stanley - retention: not found in the evidence provided as an advisor-specific statement. *Would fill it:* Morgan Stanley earnings call transcripts and 10-K/10-Q Wealth Management sections on financial advisor headcount and attrition
- Merrill - retention: not found in the evidence provided. Merrill does not report standalone results; Bank of America reports GWIM, which includes Merrill and the Private Bank. *Would fill it:* Bank of America earnings calls and GWIM investor day materials covering advisor retention; Merrill advisor recruiting materials

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q8: Compare how Schwab and Raymond James describe their value proposition to independent advisors.

**Verdict: PASS**. Each firm's own language; custody (Schwab) and affiliation (Raymond James) kept distinct.

Tier 2, use case `head_to_head`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It uses each firm's own language and keeps custody and affiliation distinct rather than flattening two different business models into one comparison.

**Claims**

1. Core pitch - Schwab: On the 1Q26 call (published April 2026), CEO Rick Wurster said advisers continue to win because "the fiduciary model works" and independent advisers "have a great model", and that as Schwab supports their growth, "we win as well."
   - `SCHW-TR-2026Q1#49` (transcript, 2026-04-16): "Richard Andrew Wurster CEO, President & Director And importantly, the advisers continue to win in the marketplace because the fiduciary model works, because there's a bull market for advice and convenience and the indepe..."
2. Core pitch - Schwab: On the 3Q26 call (published October 2026), Wurster said Schwab has "built our adviser business around helping independent advisers grow, compete and succeed," and that the business requires scale, trust, operational excellence, outstanding service and breadth as advisers' and clients' needs become more complex.
   - `SCHW-TR-2026Q3#10` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director We have built our adviser business around helping independent advisers grow, compete and succeed. Today, we serve more than 16,000 firms representing $5.8 trillion in asse..."
3. Core pitch - Raymond James: On the 4Q25 call (published January 2026), CEO Paul Shoukry pointed to the "value proposition, the cultural fit, the platform" and "multiple affiliation options". He said Raymond James has the largest addressable market across employee, independent contractor and RIA custody options, with critical mass and decades of experience in each.
   - `RJF-TR-2025Q4#50` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial Yeah, I mean, I hate to speak on any specific M&A or transactions. We have a lot of friendly competitors, and they're doing, you know, good jobs keeping the advisors, you know,..."
4. Core pitch - Raymond James: Its independent-advisor recruiting page (page content as of 2026-05-19) is headed "A partnership in independence." It says "Standing apart doesn't mean you need to stand alone" and that an independent contractor can access Raymond James's full capabilities "at a level that's right for your business."
   - `RJF-PR-web-independent-advisor#0` (press, 2026-05-19): "Independent Advisor Raymond James advisor recruiting page - content as of 2026-05-19 Source: https://web.archive.org/web/20260519072648/https://www.raymondjames.com/advisor-opportunities/affiliation-options/independent-a..."
5. Core pitch - Raymond James: On the 2Q FY26 call (published July 2026), Shoukry said the strong balance sheet, long-term focus and commitment to independence "continues to set Raymond James apart for advisers evaluating alternatives."
   - `RJF-TR-2026Q2#7` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director Together with our strong balance sheet, long-term focus and commitment to independence, that combination continues to set Raymond James apart for advisers evaluating alternatives. Our a..."
6. Capabilities offered - Schwab: Wurster described (3Q26 call, October 2026) a platform that "brings together custody, trading, banking and lending capabilities, technology and dedicated service and support." Schwab's 2Q26 10-Q (published August 2026) says its Advisor Services segment provides custodial, trading, banking and trust, and support services to independent RIAs, independent retirement advisors and recordkeepers.
   - `SCHW-TR-2026Q3#10` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director We have built our adviser business around helping independent advisers grow, compete and succeed. Today, we serve more than 16,000 firms representing $5.8 trillion in asse..."
   - `SCHW-10Q-2026Q2#7` (10-Q, 2026-08-07): "Schwab provides financial services to individuals and institutional clients through two segments - Investor Services and Advisor Services. The Investor Services segment provides retail brokerage, investment advisory, and..."
7. Capabilities offered - Raymond James: The recruiting page (as of 2026-05-19) describes a "full-service, self-clearing New York Stock Exchange-member broker/dealer" covering investing, planning, private wealth, marketing and technology. It lists private wealth concierge support, advisor-shaped technology and customized branding as resources.
   - `RJF-PR-web-independent-advisor#0` (press, 2026-05-19): "Independent Advisor Raymond James advisor recruiting page - content as of 2026-05-19 Source: https://web.archive.org/web/20260519072648/https://www.raymondjames.com/advisor-opportunities/affiliation-options/independent-a..."
8. Capabilities offered - Raymond James: On the 2Q FY26 call (July 2026), Shoukry said the firm is investing in private wealth tools and resources, and in automation, process improvement and AI, as part of "more than $1.1 billion annual technology spend."
   - `RJF-TR-2026Q2#7` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director Together with our strong balance sheet, long-term focus and commitment to independence, that combination continues to set Raymond James apart for advisers evaluating alternatives. Our a..."
9. Traction cited by management - Schwab: On the 3Q26 call (October 2026), Wurster said Schwab serves more than 16,000 firms representing $5.8 trillion in assets. He said more than 1,100 advisory firms added Schwab as a custodian last year, "more than 3x the number of the next closest provider."
   - `SCHW-TR-2026Q3#10` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director We have built our adviser business around helping independent advisers grow, compete and succeed. Today, we serve more than 16,000 firms representing $5.8 trillion in asse..."
10. Traction cited by management - Raymond James: On the 4Q25 call (January 2026), Shoukry said advisors are coming "from wires, regionals, other independents." On the 2Q FY26 call (July 2026), he cited "near record levels of adviser satisfaction." The FY2025 10-K (published November 2025) reports 5,065 independent advisors as of September 30, 2025.
   - `RJF-TR-2025Q4#50` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial Yeah, I mean, I hate to speak on any specific M&A or transactions. We have a lot of friendly competitors, and they're doing, you know, good jobs keeping the advisors, you know,..."
   - `RJF-TR-2026Q2#7` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director Together with our strong balance sheet, long-term focus and commitment to independence, that combination continues to set Raymond James apart for advisers evaluating alternatives. Our a..."
   - `RJF-10K-2025#24` (10-K, 2025-11-25): "As of September 30, 2025, we had approximately 19,500 associates (including 3,878 employee financial advisors) and 5,065 independent advisors. This reflects an increase of approximately 500 associates compared to the pri..."
11. Independence as a stated value - Raymond James: The FY2025 10-K (published November 2025) lists "we value independence" among the pledges to clients, advisors and associates in its culture "blueprint."
   - `RJF-10K-2025#24` (10-K, 2025-11-25): "As of September 30, 2025, we had approximately 19,500 associates (including 3,878 employee financial advisors) and 5,065 independent advisors. This reflects an increase of approximately 500 associates compared to the pri..."

**Adjacent evidence (a related but different quantity)**

1. WealthManagement.com (published 2026-10-29) reports that Wurster said Schwab wants RIAs to have access to banking services such as lending, private market investing and long-short strategies equal to or better than wirehouse advisors. It quotes him: "We are increasingly trying to play a role of being their bank."
   - *Differs because:* Trade-press reporting is indicative, not authoritative; it is a journalist's account of CEO remarks, not a Schwab filing or call transcript.
   - `SCHW-TRADE-2026-10-29-WM-01#0` (trade, 2026-10-29): "Schwab to Push Bank Capabilities for RIAs to Compete With Wirehouses WealthManagement.com trade press - 2026-10-29 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ria-news/schwab-to-push-on-bank-capabi..."

### Q9: How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

**Verdict: PASS**. Merrill thresholds ($250K advisory, GWIM bands, $3MM+ Private Bank metric) and Morgan Stanley's 'no dollar thresholds' said plainly.

Tier 3, use case `head_to_head`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It reports each firm's disclosed segmentation and any stated thresholds, and says plainly where a firm does not disclose thresholds instead of inferring them from marketing language.

**Claims**

1. Dollar thresholds by tier - Merrill: The 2025 10-K (published 2026-02-25) says Merrill Wealth Management's advisory business serves clients with over $250,000 in total investable assets.
   - `BAC-10K-2025#246` (10-K, 2026-02-25): "Merrill Wealth Management’s advisory business provides a high-touch client experience through a network of financial advisors focused on clients with over $250,000 in total investable assets. Merrill Wealth Management pr..."
2. Dollar thresholds by tier - Merrill: A Bank of America investor-day deck (published 2025-11-05) shows a "Wealth Continuum" with Mass Affluent ($500K - $1MM) and High Net Worth ($1MM - $10MM). The evidence does not say how this continuum relates to the $250,000 advisory threshold in the 10-K.
   - *Flagged by code:* number_not_found
   - `BAC-DECK-2025-investor-day#12` (deck, 2025-11-05): "Wealth Continuum Mass Affluent ($500K - $1MM) High Net Worth ($1MM - $10MM)"
3. Dollar thresholds by tier - Merrill: A Bank of America press release (published 2026-01-14) defines digitally active Private Bank core relationships as those with $3MM+ in total balances. This is stated for that metric.
   - `BAC-PR-2026-01-14-01#12` (press, 2026-01-14): "6 Percentage of digitally active Private Bank core relationships across the enterprise ($3MM+ in total balances) as of November 2025. Includes third-party activities and excludes Irrevocable Trust-only relationships, Ins..."
4. Top-tier (HNW/UHNW) positioning - Morgan Stanley: The 2025 10-K (published 2026-02-19) describes its U.S. Bank Subsidiaries as lending to "high to ultra-high net worth individuals". It says Wealth Management lending includes securities-based lending and "tailored lending to ultra-high net worth clients".
   - `MS-10K-2025#190` (10-K, 2026-02-19): "Liquidity and Overlay Services. Includes liquidity products, as well as overlay services, which represent investment strategies that use passive exposure instruments to obtain, offset or substitute specific portfolio exp..."
5. Top-tier (HNW/UHNW) positioning - Morgan Stanley: The 2Q26 10-Q (published 2026-08-04) says commercial real estate loans in Wealth Management are originated through its private banking platform and often have guarantees from "high or ultra-high net worth clients". It gives no dollar cut-offs for these terms.
   - `MS-10Q-2026Q2#186` (10-Q, 2026-08-04): "Total $ 6,961 $ 133 $ 7,094 $ 7,276 $ 198 $ 7,474 LC - Lending Commitments 1. Amounts include HFI loans and lending commitments. HFI loans are presented net of ACL. As of June 30, 2026 and December 31, 2025, our direct l..."
6. Top-tier (HNW/UHNW) positioning - Morgan Stanley: The 1Q26 10-Q (published 2026-05-05) describes Institutional Securities as serving corporations, governments, financial institutions and ultra-high net worth clients. So ultra-high net worth clients appear in both the Institutional Securities and Wealth Management segment descriptions.
   - `MS-10Q-2026Q1#208` (10-Q, 2026-05-05): "A description of the clients and principal products and services of each of the Firm’s business segments is below. Through the Integrated Firm some of our clients may use the products and services of more than one of our..."
   - `MS-10K-2025#190` (10-K, 2026-02-19): "Liquidity and Overlay Services. Includes liquidity products, as well as overlay services, which represent investment strategies that use passive exposure instruments to obtain, offset or substitute specific portfolio exp..."
7. Top-tier (HNW/UHNW) positioning - Morgan Stanley: On the 3Q26 earnings call (published 2026-10-14), CEO Edward Pick cited "ultra-high net worth family office infrastructure solutions" among the capabilities available to Morgan Stanley clients.
   - `MS-TR-2026Q3#33` (transcript, 2026-10-14): "Edward N. Pick CEO & Chairman of the Board I'd highlight 4. The first is we all bear in mind that we've got a unique set of products and capabilities as the largest distributor in the world. We're the most important weal..."
8. Top-tier (HNW/UHNW) positioning - Merrill: The 2025 10-K (published 2026-02-25) says Bank of America Private Bank, together with Merrill Wealth Management's Private Wealth Management business, serves high net worth and ultra high net worth clients. It describes wealth structuring, investment management, trust and banking solutions. Merrill's advisory business is described separately, by the $250,000 investable-assets focus.
   - `BAC-10K-2025#246` (10-K, 2026-02-25): "Merrill Wealth Management’s advisory business provides a high-touch client experience through a network of financial advisors focused on clients with over $250,000 in total investable assets. Merrill Wealth Management pr..."
9. Top-tier (HNW/UHNW) positioning - Merrill: Merrill's advisor recruiting page (page content as of 2026-11-03) lists "robust solutions for ultra-high-net-worth clients, including alternative investments and sustainable and impact investing strategies".
   - `MER-PR-web-becoming-a-merrill-lynch-advisor#0` (press, 2026-11-03): "Accelerate your business growth at Merrill Merrill advisor recruiting page - content as of 2026-11-03 Source: https://careers.bankofamerica.com/en-us/becoming-a-merrill-lynch-advisor (fetched 2026-11-03) Content as of: 2..."

**Adjacent evidence (a related but different quantity)**

1. Trade press (WealthManagement.com, 2026-09-08) reports a team joining Merrill Private Wealth Management from Morgan Stanley Private Wealth Management. It says the team serves high-net-worth and ultra-high-net-worth clients and is aligned with Merrill's Southeast private wealth division.
   - *Differs because:* Trade-press reporting is indicative, not authoritative. It shows that both firms have 'Private Wealth' units but gives no tier definitions.
   - `MER-TRADE-2026-09-08-WM-01#0` (trade, 2026-09-08): "Merrill Lynch Poaches Morgan Stanley, Truist, Wells Advisors with Combined $1.8B WealthManagement.com trade press - 2026-09-08 (tier 4, indicative only) Source: https://www.wealthmanagement.com/wirehouse-news/merrill-poa..."

**Gaps (named by the answer)**

- Morgan Stanley - dollar thresholds by tier: not found in the evidence provided. The chunks use 'high net worth' and 'ultra-high net worth' without asset cut-offs, and give no tier ladder for Wealth Management. *Would fill it:* Morgan Stanley Wealth Management investor presentations or the 10-K business section, plus the firm's client-segment or minimum-asset disclosures (e.g., Private Wealth Management and Workplace segment descriptions).
- Merrill does not report standalone results. The evidence on tiers comes from Bank of America's GWIM segment disclosures (Merrill Wealth Management plus the Private Bank), so tier labels are not matched to Merrill-only financials. *Would fill it:* Bank of America investor-day materials and 10-K Item 7 GWIM discussion.

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q10: Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

**Verdict: PASS**. Only GWIM names a 'Mass Affluent' tier (dated slide); basis visible; the other four marked as no explicit statement.

Tier 3, use case `head_to_head`. Expected behavior `answer`, got `answer`. Retrieval: 30 passages, mode `entity+theme`.

*Passes if:* It shows its work rather than asserting a ranking -- the actual statements, dated, with the basis for calling one firm more explicit than another made visible so the reader can disagree.

**Claims**

1. Of the firms in the evidence, Bank of America's GWIM segment (Merrill plus the Private Bank) is the only one whose own materials name a "Mass Affluent" tier. The question doesn't list the five firms, so I take them to be Edward Jones, Morgan Stanley, Raymond James, Schwab and Bank of America/Merrill. In its investor day deck (published 2025-11-05), the GWIM "Wealth Continuum" slide labels "Mass Affluent ($500K - $1MM)" next to "High Net Worth ($1MM - $10MM)". This is a label on a slide. The chunk contains no accompanying commentary.
   - `BAC-DECK-2025-investor-day#12` (deck, 2025-11-05): "Wealth Continuum Mass Affluent ($500K - $1MM) High Net Worth ($1MM - $10MM)"
2. In the same investor day deck (published 2025-11-05), GWIM states its foundational beliefs. It says "the Wealth Continuum allows us to deliver as one company and is our engine for lasting growth". It also says "we have the capabilities to deliver for every client in the way they want to be served". The chunk does not single out mass-affluent clients in these statements.
   - `BAC-DECK-2025-investor-day#8` (deck, 2025-11-05): "We believe… …growth of our fully advised client relationships drives financial outcomes …the Wealth Continuum allows us to deliver as one company and is our engine for lasting growth …having the best advisors enables us ..."
3. The deck's GWIM overview slide (published 2025-11-05) describes "Serving the wealth continuum of clients". It cites 2MM client relationships, $4.6T in client balances, more than 15K wealth advisors and $23B in revenue.
   - `BAC-DECK-2025-investor-day#9` (deck, 2025-11-05): "Merrill / Private Bank 2MM $4.6T Client Relationships Serving the wealth continuum of clients Client Balances 2 nd largest traditional wealth manager 2 >15K Wealth Advisors $23B Revenue 1 Industry leading advisor force H..."
4. On the 2Q26 earnings call (published 2026-07-14), CFO Alastair Borthwick said GWIM "added another 6,000 net new affluent households to serve". He tied this to growth in banking relationships and lending balances, which he said shows "the power of our integrated wealth and banking model". He used the word "affluent", not "mass affluent".
   - `BAC-TR-2026Q2#20` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO Turning to Slide 14. GWIM delivered another outstanding quarter, highlighted by record revenue and pretax income, expanded profit margins, and continued client growth. Clients con..."

**Adjacent evidence (a related but different quantity)**

1. Schwab's 2Q26 deck (published 2026-07-21) cites "61%" of affluent clients who prefer to consolidate wealth and banking relationships. It also says 62% of U.S. adults own stock.
   - *Differs because:* This is a market statistic about affluent clients. It is not a Schwab statement about serving mass-affluent clients, and it does not use that term.
   - `SCHW-DECK-2026Q2#16` (deck, 2026-07-21): "…at a time when investing is playing an increasingly central role in individual's financial lives. 62% of U.S. adults own stock - highest level since 2007 1 More people invest Increase in holdings of equities & mutual fu..."
2. Cerulli research (published 2026-03-25) sizes middle-market and mass-affluent households ($100,000 to $2 million in financial assets) at $25 trillion across 46.9 million households.
   - *Differs because:* This is third-party research on the segment. It is not a statement by any of the five firms.
   - `CERULLI-MASS-AFFLUENT-2026#0` (research, 2026-03-25): "Mass-Affluent Households Represent a $25 Trillion Market Opportunity March 25, 2026 — Boston As U.S. household financial assets surpass $100 trillion, the mass-affluent segment is primed for earlier advisor engagement Ce..."
   - `CERULLI-MASS-AFFLUENT-2026#1` (research, 2026-03-25): "“Though this strategy has proven effective, it faces increased pressure as competitors seek additional options to connect with prospects earlier in the financial lifecycle.” Acting earlier matters. According to Cerulli, ..."
3. A trade article (published 2026-10-21) cites a June 2025 Cerulli report that 52% of mass-affluent participants without an advisor say their retirement savings account provider is their primary source of retirement planning guidance. The article is about a Morgan Stanley survey.
   - *Differs because:* The mass-affluent figure comes from Cerulli, reported in trade press. It is not a Morgan Stanley statement, and trade-press reporting is indicative, not authoritative.
   - `MS-TRADE-2026-10-21-IN-01#3` (trade, 2026-10-21): "A June 2025 Cerulli Associates report found that 63% of active 401(k) participants do not have a financial advisor , while 52% of mass-affluent participants without an advisor say their retirement savings account provide..."
4. A trade article (published 2026-09-29) says Raymond James's Private Wealth Advisor designation is for advisors serving high-net-worth clients, generally those with at least $5 million in investable assets.
   - *Differs because:* This covers high-net-worth clients, not mass-affluent ones. It is also trade press, which is indicative, not authoritative.
   - `RJF-TRADE-2026-09-29-IN-01#3` (trade, 2026-09-29): "That effort includes estate and charitable planning capabilities, lending and cash management solutions, risk management services, and intergenerational wealth strategies, all positioned as tools that advisors can draw o..."

**Gaps (named by the answer)**

- Edward Jones: no explicit firm statement about serving mass-affluent clients found in the evidence provided. *Would fill it:* Edward Jones 10-K business section, investor materials or earnings commentary
- Morgan Stanley: no explicit firm statement about serving mass-affluent clients found in the evidence provided. *Would fill it:* Morgan Stanley earnings call transcripts, investor day decks, Wealth Management segment disclosures
- Raymond James: no explicit firm statement about serving mass-affluent clients found in the evidence provided. *Would fill it:* Raymond James investor day deck, earnings call transcripts, 10-K Private Client Group description
- Schwab: no explicit firm statement about serving mass-affluent clients found in the evidence provided. *Would fill it:* Schwab earnings call transcripts, investor materials, 10-K
- Merrill does not report standalone results. The Bank of America deck and call figures are GWIM, which includes both Merrill and the Private Bank. *Would fill it:* Bank of America GWIM segment disclosures; Merrill-specific materials

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q11: How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

**Verdict: FAIL** (c, b). EDJ and RJF definitions only; no advisor count for Morgan Stanley, Schwab or Merrill exists in any stored document, so five definitions cannot be given; prompt v3 now chooses gap_with_adjacent (expected answer).

Tier 1, use case `head_to_head`. Expected behavior `answer`, got `gap_with_adjacent`. Retrieval: 30 passages, mode `entity`.

*Passes if:* Five definitions, quoted from the filings, with the differences between them named explicitly.

**Claims**

1. Edward Jones - the 10-Q for the quarter ended 2025-09-26 (published November 2025) defines its attrition metric by reference to advisor headcount. Attrition % is "the annualized number of financial advisors that left or retired from the Partnership during the period compared to the total number of financial advisors as of period end." Departures are counted as advisors who left or retired, and the denominator is period-end headcount.
   - `EDJ-10Q-2025Q3#69` (10-Q, 2025-11-07): "100 102 -2% Average 99 100 -1% 98 98 — (1) Income before allocations margin is income before allocations expressed as a percentage of total revenue. (2) Client dollars invested for trade revenue represents the principal ..."
2. Edward Jones - the 2025 10-K (published March 2026) reports "Financial advisors (actual)" on two bases: at year end (20,425) and average (20,331). The excerpt does not define "actual" or say which roles it includes or excludes.
   - `EDJ-10K-2025#130` (10-K, 2026-03-13): "$ 973 $ 815 $ 674 19% Client households at year end 6.7 6.6 6.3 2% Net new assets for the year ($ billions)(2) $ 74 $ 74 $ 97 — Financial advisors (actual): At year end 20,425 20,125 19,232 1% Average 20,331 19,650 18,94..."
3. Edward Jones - the 10-Q for the quarter ended 2026-06-26 (published August 2026) again reports "Financial advisors (actual)" at period end (20,514 vs. 20,309) and as an average (20,537 vs. 20,316). The excerpt gives no inclusion or exclusion definition.
   - `EDJ-10Q-2026Q2#60` (10-Q, 2026-08-07): "2% Net new assets for the period ($ billions)(3) $ 18 $ 17 6% $ 36 $ 34 6% Financial advisors (actual): At period end 20,514 20,309 1% 20,514 20,309 1% Average 20,537 20,316 1% 20,517 20,265 1% (1) Income before allocati..."
4. Raymond James - the fiscal 2025 10-K (published November 2025) states that financial advisors associated with firms in its RCS division (third-party RIAs and broker-dealers that use its custody and support services) "are not included in our financial advisor counts," although their client assets are included in AUA. AUA for RCS firms totaled $217.3 billion at September 30, 2025. This is an explicit exclusion from the count.
   - `RJF-10K-2025#12` (10-K, 2025-11-25): "Through our domestic RCS division, we offer third-party RIAs and broker-dealers a range of products and services including custodial services, trade execution, research, and other support and services (including access t..."
5. Raymond James - on the fiscal fourth-quarter 2025 call (published October 2025), CEO Paul Shoukry cited "a record number of financial advisors of 8,943." The excerpt does not say what the count includes beyond the RCS exclusion above.
   - `RJF-TR-2025Q3#4` (transcript, 2025-10-22): "Paul Shoukry CEO at Raymond James As we look ahead, many of our key business drivers also ended the year at record levels, including record client assets of $1.73 trillion, a record number of financial advisors of 8,943,..."

**Adjacent evidence (a related but different quantity)**

1. Morgan Stanley's January 2026 strategic-update deck defines Advisor-Led Households as households with at least one account holding Advisor-Led Client Assets. It defines Advisor-Led Client Assets as assets in accounts that have a WM representative assigned. Morgan Stanley's 10-Q (June 2026) defines self-directed client assets as active accounts that are not advisor led.
   - *Differs because:* These definitions cover households and client assets, not the count of advisors or representatives.
   - `MS-DECK-2026-strategic-update#31` (deck, 2026-01-15): "These notes refer to the financial metrics and/or defined terms presented on Slide 8 Fee-Based Flows represent net new fee-based assets (including asset acquisitions), net account transfers, dividends, interest, and clie..."
   - `MS-10Q-2026Q2#60` (10-Q, 2026-08-04): "3. Fee-based asset flows include net new fee-based assets (including asset acquisitions), net account transfers, dividends, interest and client fees, and exclude institutional cash management related activity. For a desc..."
2. Schwab's 2Q26 10-Q (published August 2026) says compensation and benefits rose partly because of "growth in headcount, including growth in financial consultants and wealth advisors."
   - *Differs because:* This is a qualitative expense driver. It gives no advisor count and no definition of who is counted as a financial consultant or wealth advisor.
   - `SCHW-10Q-2026Q2#71` (10-Q, 2026-08-07): "The Company’s second quarter and first six months of 2026 results include expenses related to Forge subsequent to our March 2, 2026 acquisition (see also Item 1 - Note 3). Acquisition and integration-related costs relate..."
3. On the Bank of America 3Q26 call (October 2026), management said Merrill added about 4,200 net new households with at least $500,000 in assets. It also referred to attracting "experienced advisers to the platform." The segment filing describes GWIM as two businesses, Merrill Wealth Management and Bank of America Private Bank.
   - *Differs because:* These are household and relationship metrics for GWIM or Merrill, not an advisor headcount. GWIM includes both Merrill and Bank of America Private Bank, so its figures are not Merrill's.
   - `BAC-TR-2026Q3#19` (transcript, 2026-10-14): "Alastair Borthwick Client balances climbed above $5 trillion for the first time, up 9%, while AUM rose 12% to about $2.4 trillion. Quarterly net client flows were about $38 billion, including approximately $20 billion of..."
   - `BAC-10Q-2026Q2#88` (10-Q, 2026-07-31): "GWIM consists of two primary businesses: Merrill Wealth Management and Bank of America Private Bank. For more information on GWIM, see Business Segment Operations in the MD&A of the Corporation’s 2025 Annual Report on Fo..."

**Gaps (named by the answer)**

- Edward Jones: the meaning of "Financial advisors (actual)" is not stated in the excerpts. They do not say whether it covers only fully registered advisors or whether trainees and Canada are included or excluded. *Would fill it:* Edward Jones 10-K Item 1 or MD&A definitions and glossary, or investor-relations metric definitions
- Raymond James: only the RCS exclusion is stated. The excerpts do not say whether employee advisors and independent contractor advisors are both included, or whether other affiliation channels are counted. *Would fill it:* Raymond James 10-K PCG segment description or financial supplement footnotes on advisor counts
- Morgan Stanley: advisor headcount and its definition are not found in the evidence provided. *Would fill it:* Morgan Stanley 10-K or 10-Q Wealth Management metrics, or the financial supplement (financial advisor and representative counts with footnotes)
- Schwab: advisor headcount and its definition are not found in the evidence provided. The excerpts mention only growth in financial consultants and wealth advisors. *Would fill it:* Schwab 10-K or 10-Q business overview, or the investor presentation and Monthly Activity Report
- Bank of America / Merrill: advisor headcount and its definition are not found in the evidence provided. Merrill does not report standalone results. *Would fill it:* Bank of America GWIM supplemental disclosures or earnings-release key-indicator tables (financial advisor counts)
- The question says "the five" without naming them. I assumed Edward Jones, Raymond James, Morgan Stanley, Schwab and Bank of America (Merrill), the firms in the evidence. A definition is disclosed for only two of them, and only in part. *Would fill it:* Confirm the intended peer set

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q12: How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

**Verdict: FAIL** (s). Boundary held, Schwab's scale economics given, but Edward Jones's cost structure is not set alongside and the gap does not name it.

Tier 3, use case `mechanism`. Expected behavior `answer_with_boundary`, got `answer_with_boundary`. Retrieval: 20 passages, mode `entity+theme`.

*Passes if:* It delivers the evidence half completely -- Schwab's disclosed acquisition channels and economics, what management has claimed about cost of acquisition, and Edward Jones's own disclosed cost structure set alongside -- then explicitly hands off the replication question rather than attempting it.

**Claims**

1. Schwab's 2025 10-K (published 2026-02-25) lists "Scale and Size of the Business" as a key competitive advantage. It says the firm can "spread operating costs and amortize new investments over a large base of clients." Management estimates U.S. investable wealth exceeds $80 trillion against the firm's $11.90 trillion in client assets. It says its strategy rests on trusted relationships bringing in more assets from both new and existing clients.
   - `SCHW-10K-2025#13` (10-K, 2026-02-25): "Management estimates that investable wealth in the United States (U.S.) (consisting of assets in defined contribution, retail wealth management and brokerage, and registered investment advisor channels, along with bank d..."
2. Schwab's 2Q26 10-Q (published 2026-08-07) says management works to couple Schwab's scale and resources with ongoing expense discipline "to keep costs low" so products are affordable. The filing calls this part of its "no trade-offs" approach.
   - `SCHW-10Q-2026Q2#8` (10-Q, 2026-08-07): "This strategy emphasizes placing clients’ perspectives, needs, and desires at the forefront. Because investing plays a fundamental role in building financial security, we strive to deliver a better investing experience f..."
3. On the 4Q25 earnings call (published 2026-01-21), CEO Rick Wurster said Gen Z investors were nearly a third of new retail client accounts opened in 2025. He said nearly 60% of new accounts are under age 40 and about one-third of new clients are affluent. He also said that at Schwab's scale the firm has an opportunity to do more for existing clients "at a magnitude that can't be easily replicated."
   - `SCHW-TR-2025Q4#11` (transcript, 2026-01-21): "Rick Wurster President and CEO at Charles Schwab Corp Gen Z investors comprise nearly a third of new retail client accounts opened in 2025, and nearly 60% are under the age of 40. About one-third of new clients are afflu..."
4. Schwab's 2Q26 earnings release (published 2026-07-21) reports 1.4 million new brokerage account openings in the quarter, which brought total client accounts to 48.0 million. Core net new assets were $119.8 billion, up 49% versus 2Q25.
   - `SCHW-PR-2026-07-21-01#2` (press, 2026-07-21): "ults across a range of environments. During the second quarter, strong client engagement helped drive year-over-year revenue growth of 21% to a record $7.1 billion.” 2Q26 Revenue CFO Mike Verdeschi Growth vs. 2Q25 Strong..."
5. On the 2Q26 call (published 2026-07-21), Wurster said management believes AI "will help us attract new clients." He said developer team productivity improved by 15% to 20% over the past year. He described AI as combining people with AI-powered capabilities.
   - `SCHW-TR-2026Q2#19` (transcript, 2026-07-21): "Richard Andrew Wurster CEO, President & Director We've talked about AI as part of our omnichannel experience, and it is becoming more embedded in all we do, accelerating our strategy and amplifying our competitive advant..."
6. On the 3Q26 call (published 2026-10-15), Wurster said developer productivity had increased by about 25% from internal AI use. He described Schwab's combination of people, technology, scale and value as a powerful advantage "very difficult to replicate."
   - `SCHW-TR-2026Q3#8` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director We're using AI internally to help our developers and professionals work more effectively and efficiently. We've already seen developer productivity increase by about 25%. ..."
7. Edward Jones's 2025 10-K (published 2026-03-13) states the Partnership's strategic ambition is to help tens of millions of investors achieve financial fulfillment through personalized, comprehensive planning and trusted advice. It says the Partnership aspires to continue investing in technology to scale its ability to provide financial planning, anticipate clients' needs, and attract and serve new client segments.
   - `EDJ-10K-2025#8` (10-K, 2026-03-13): "None of the Partnership's securities is listed on a securities exchange and therefore some governance requirements that generally apply to listed companies that file periodic reports with the Securities and Exchange Comm..."
8. Edward Jones's 2025 10-K risk factors (published 2026-03-13) say the increased cost of its digital initiatives "may continue to adversely impact the Partnership's profitability." They also say major digital initiatives or system replacements bring adjustment periods for branch and home office associates. They say that using AI may expose the Partnership to additional information security, legal and regulatory risk.
   - `EDJ-10K-2025#75` (10-K, 2026-03-13): "The Partnership's increased cost from these digital initiatives may continue to adversely impact the Partnership's profitability. Furthermore, with any major digital initiative or system replacement, there will be a peri..."
9. Edward Jones's 2Q26 10-Q (published 2026-08-07) describes the Partnership as primarily serving individual investors in the U.S. and Canada. It says revenues come mainly from advisory and account-service fees, fees on client assets, and commissions.
   - `EDJ-10Q-2026Q2#28` (10-Q, 2026-08-07): "Through these retail brokerage entities, the Partnership primarily serves individual investors in the U.S. and Canada and primarily derives revenues from fees for providing investment advisory and other account services ..."
10. The evidence above only provides objective context for the strategic question asked. Whether or how Edward Jones should act is a judgment for the strategy team to make, beyond the scope of this evidence engine.
   - `SCHW-10K-2025#13` (10-K, 2026-02-25): "Management estimates that investable wealth in the United States (U.S.) (consisting of assets in defined contribution, retail wealth management and brokerage, and registered investment advisor channels, along with bank d..."
   - `SCHW-10Q-2026Q2#8` (10-Q, 2026-08-07): "This strategy emphasizes placing clients’ perspectives, needs, and desires at the forefront. Because investing plays a fundamental role in building financial security, we strive to deliver a better investing experience f..."
   - `EDJ-10K-2025#8` (10-K, 2026-03-13): "None of the Partnership's securities is listed on a securities exchange and therefore some governance requirements that generally apply to listed companies that file periodic reports with the Securities and Exchange Comm..."
   - `EDJ-10K-2025#75` (10-K, 2026-03-13): "The Partnership's increased cost from these digital initiatives may continue to adversely impact the Partnership's profitability. Furthermore, with any major digital initiative or system replacement, there will be a peri..."

**Gaps (named by the answer)**

- Schwab does not disclose a per-client acquisition cost or marketing spend per new account in the evidence provided. The evidence shows scale-based cost spreading and new-account volumes, but not that new clients are acquired "cheaply." *Would fill it:* Schwab 10-K or investor day materials on marketing and acquisition spend; management commentary on cost to acquire
- Edward Jones new-client figures (net new households, new-client counts) on the same dimension as Schwab's 1.4 million new brokerage accounts are not in the evidence provided. The 2Q25 10-Q chunk defines the metric but shows no values. *Would fill it:* Edward Jones 10-Q/10-K MD&A key-metrics table (net new households, net new assets)

### Q13: How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

**Verdict: PASS**. Channel end to end in management's framing (participants, funnel, vesting retention, channel migration), with the $99B FY2025 advisor-led flows from workplace/E*TRADE attached to its period.

Tier 1, use case `mechanism`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* The channel is described end to end in management's own framing, with any disclosed conversion or funded-account figures attached to the period they were stated in.

**Claims**

1. The 2025 10-K (published 2026-02-19) describes Wealth Management as supporting clients through three channels: Advisor-Led, Self-Directed and Workplace. It says workplace services include stock plan administration, and defines the workplace channel as equity compensation solutions for companies, their executives and employees.
   - `MS-10K-2025#125` (10-K, 2026-02-19): "Wealth Management provides a comprehensive array of financial services and solutions to individual investors, including high and ultra-high net worth individuals, and businesses and institutions. Wealth Management suppor..."
   - `MS-10K-2025#168` (10-K, 2026-02-19): "1. Self-directed client assets represent active accounts which are not advisor led. Active accounts are defined as having at least $25 in assets. 2. Self-directed households represent the total number of households that ..."
2. The 2025 10-K reports 6.5 million stock plan participants and $534 billion of stock plan unvested assets at December 31, 2025. It counts participants as total accounts with vested and/or unvested stock plan assets, and individuals in multiple plans count in each plan.
   - `MS-10K-2025#168` (10-K, 2026-02-19): "1. Self-directed client assets represent active accounts which are not advisor led. Active accounts are defined as having at least $25 in assets. 2. Self-directed households represent the total number of households that ..."
3. The January 2026 strategic update deck (published 2026-01-15) defines "Advisor-Led Flows from Workplace and E*TRADE" as assets brought into advisor-led relationships where the initial account was workplace or self-directed. It averaged these across 2020-2024. It also defines Core Client Relationships as advisor-led households, self-directed households and workplace participants, excluding overlap.
   - `MS-DECK-2026-strategic-update#32` (deck, 2026-01-15): "Self-Directed Households represent the total number of households that include at least one active account with Self-Directed Client Assets. Self-Directed Client Assets represent active accounts which are not advisor-led..."
   - `MS-DECK-2026-strategic-update#31` (deck, 2026-01-15): "These notes refer to the financial metrics and/or defined terms presented on Slide 8 Fee-Based Flows represent net new fee-based assets (including asset acquisitions), net account transfers, dividends, interest, and clie..."
4. On the 4Q25 earnings call (2026-01-15), management said advisor-led assets originating from workplace and E*TRADE relationships accelerated to a record $99 billion for the full year, compared with historical averages of around $60 billion per year.
   - `MS-TR-2025Q4#20` (transcript, 2026-01-15): "Company Representative at Morgan Stanley Advisor-led assets originating from workplace and E*TRADE relationships accelerated, growing to a record $99 billion for the full year, compared to historical averages of around $..."
5. On the 1Q26 earnings call (2026-04-15), CFO Sharon Yeshaya described a workplace "funnel". The first step is retaining assets as unvested assets vest; in the quarter the firm saw greater retention of vested workplace assets, which translated into net new assets. Over time, she said, workplace assets are "seeking advice" through channel migration, supported by technology and investment. She said this migration helped contribute to over $1 trillion of total assets in the advisor-led strategy.
   - `MS-TR-2026Q1#24` (transcript, 2026-04-15): "Sharon Yeshaya Executive VP & CFO Specifically, with this quarter, you'll see that often and not surprisingly that in the first quarter, you'll see unvested assets vest. And what we saw in Workplace this quarter is great..."
6. On the 2Q26 earnings call (2026-07-15), the CFO said stock plan IPO flows were just over half of record net new assets of $148 billion. She called workplace a strong contributor to the "top of the funnel" and said "Workplace brings relationships and assets onto the platform." She said the firm is well positioned to support these new relationships and to build fee-based assets. The 2Q26 press release likewise says just over half of the $148 billion represented inflows related to IPOs of certain clients in the Workplace channel.
   - `MS-TR-2026Q2#16` (transcript, 2026-07-15): "Sharon Yeshaya Executive VP & CFO Lastly, net new assets were a record of $148 billion. Stock plan IPO flows represented just over half of the overall NNA this quarter, more than offsetting seasonal taxes, illustrating t..."
   - `MS-PR-2026-07-15-01#5` (press, 2026-07-15): "Wealth Management reported net revenues of $8.9 billion compared with $7.8 billion a year ago. Pre-tax income of $2.7 billion resulted in a pre-tax margin of 30.5%. 4,15 Strong net new assets for the quarter were $148 bi..."
7. The 2Q26 10-Q (published 2026-08-04) reports 6.6 million stock plan participants and $658 billion of stock plan unvested public assets at June 30, 2026. It states that unvested assets are not included in client assets.
   - `MS-10Q-2026Q2#61` (10-Q, 2026-08-04): "2. Self-directed households represent the total number of households that include at least one active account with self-directed assets. Individual households or participants that are engaged in one or more of our Wealth..."
8. On the 3Q26 earnings call (2026-10-14), CEO Edward Pick described "attachment points" that bring clients to E*TRADE and keep the firm close to them in the corporate stock plan (workplace) context. Where appropriate, he said, these lead to fee-based flows that make their way to advisers. He called the $80 billion fee-based flows figure an important statistic. The 3Q26 supplement shows fee-based asset flows of $80.5 billion for the quarter and stock plan unvested public assets of $638 billion.
   - `MS-TR-2026Q3#23` (transcript, 2026-10-14): "Edward N. Pick CEO & Chairman of the Board And then the last 3 years, we drew in another $1 trillion. So $1 trillion over 3 years, 2-, 3-year sets running shows not only our ability to make the proposition the case that ..."
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."

**Gaps (named by the answer)**

- A quantified conversion rate from workplace or stock plan participants into advisor-led clients, and the 2026 advisor-led flows originating from workplace, are not disclosed in the evidence. The $99 billion figure covers full-year 2025 and combines workplace and E*TRADE. *Would fill it:* Morgan Stanley investor day or earnings-call disclosures on advisor-led flows from workplace, and Form 10-K Wealth Management channel discussion

### Q14: How does Raymond James's affiliation-choice model work commercially?

**Verdict: PASS**. Each option's economics from Raymond James's own page and 10-K (payout, benefits, entry minimums, compliance, loans), firm side via NNA attribution and recruiting figures.

Tier 3, use case `mechanism`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* It explains what each affiliation option means economically for both the advisor and the firm, sourced to Raymond James's own description rather than to industry commentary about it.

**Claims**

1. The fiscal 2025 10-K (published November 2025) says Raymond James offers multiple affiliation options, which it calls AdvisorChoice®. Financial advisors primarily affiliate directly as employees or independent contractors. They can also affiliate as employees of third-party RIAs and broker-dealers that the firm serves through its RIA and Custody Services (RCS) division.
   - `RJF-10K-2025#10` (10-K, 2025-11-25): "We offer multiple affiliation options, which we refer to as AdvisorChoice®. Financial advisors primarily affiliate with us directly as either employees or independent contractors or as employees of third-party Registered..."
2. The fiscal 2025 10-K (November 2025) describes the employee model as a traditional branch supported by local management and administrative staff, serving predominantly retail clients. Employee advisors' compensation primarily includes a payout on revenues they generate, and they also participate in the firm's employee benefit plans.
   - `RJF-10K-2025#10` (10-K, 2025-11-25): "We offer multiple affiliation options, which we refer to as AdvisorChoice®. Financial advisors primarily affiliate with us directly as either employees or independent contractors or as employees of third-party Registered..."
3. Raymond James's recruiting page (page content as of 2026-04-21) lists five AdvisorChoice® options: Traditional Employee, Advisor Select, Independent Contractor, Bank & Credit Union and Corporate RIA. It also lists RIA & Custody Services. The page describes each as a different mix of support, freedom and flexibility. It describes Traditional Employee as offering book ownership and Advisor Select as leading your own branch with administrative support and full corporate benefits.
   - `RJF-PR-web-affiliation-options#0` (press, 2026-04-21): "Raymond James Affiliation options Raymond James advisor recruiting page - content as of 2026-04-21 Source: https://web.archive.org/web/20260421065839/https://www.raymondjames.com/advisor-opportunities/affiliation-options..."
   - `RJF-PR-web-affiliation-options#1` (press, 2026-04-21): "RIA & Custody Services: Take strategic, financial and administrative control of your practice with a full-service partner at the ready. Compare your options Dig into the details of our affiliation spectrum and find the a..."
4. Raymond James's recruiting page (as of 2026-04-21) gives these entry qualifications and payouts for the employee-type models. Traditional Employee: minimum 5 years of experience, up to 50% payout, and full employee benefits. Advisor Select: minimum 3 years and $3.5 million or higher in annual branch fees and commission revenue, with a 70-80% gross payout and full employee benefits.
   - `RJF-PR-web-affiliation-options#1` (press, 2026-04-21): "RIA & Custody Services: Take strategic, financial and administrative control of your practice with a full-service partner at the ready. Compare your options Dig into the details of our affiliation spectrum and find the a..."
5. Raymond James's recruiting page (as of 2026-04-21) gives these qualifications and payouts for the independent-type models. Independent Contractor: minimum 3 years, and a minimum T12 of $150,000 to join an existing branch or $400,000 to open a new branch. Its payout is 81% to 90%, and advisors build their own benefits package through third-party partnerships. Corporate RIA: minimum 3 years and $50 million in assets under advisement, also an 81% to 90% payout.
   - `RJF-PR-web-affiliation-options#1` (press, 2026-04-21): "RIA & Custody Services: Take strategic, financial and administrative control of your practice with a full-service partner at the ready. Compare your options Dig into the details of our affiliation spectrum and find the a..."
   - `RJF-PR-web-affiliation-options#2` (press, 2026-04-21): "Model: Bank & Credit Union Qualifications*: Minimum 3 years of experience and $250,000 in production. Payout + Benefits: Get the support you need during your transition by receiving a competitive compensation package fro..."
6. Raymond James's recruiting page (as of 2026-04-21) describes the Bank & Credit Union model as requiring a minimum of 3 years of experience and $250,000 in production. Advisors receive a competitive compensation package from the financial institution in partnership with Raymond James. For RIA & Custody Services, the page lists $100 million or more in assets to establish a new RIA, a minimum of $30 million to plug in an existing RIA, and $1 billion or more in assets under management for introducing broker/dealers. Compensation is determined with the advisor's RIA or broker/dealer, which also creates its own benefits package.
   - `RJF-PR-web-affiliation-options#2` (press, 2026-04-21): "Model: Bank & Credit Union Qualifications*: Minimum 3 years of experience and $250,000 in production. Payout + Benefits: Get the support you need during your transition by receiving a competitive compensation package fro..."
7. Raymond James's recruiting page (as of 2026-04-21) splits compliance responsibility by model. For Traditional Employee, Advisor Select and Bank & Credit Union, compliance support comes from the branch manager and home office. For Independent Contractor and Corporate RIA, it comes from the divisional team and home office. In RIA & Custody Services, "You'll be responsible for compliance."
   - `RJF-PR-web-affiliation-options#1` (press, 2026-04-21): "RIA & Custody Services: Take strategic, financial and administrative control of your practice with a full-service partner at the ready. Compare your options Dig into the details of our affiliation spectrum and find the a..."
   - `RJF-PR-web-affiliation-options#2` (press, 2026-04-21): "Model: Bank & Credit Union Qualifications*: Minimum 3 years of experience and $250,000 in production. Payout + Benefits: Get the support you need during your transition by receiving a competitive compensation package fro..."
8. Raymond James's independent-advisor page (page content as of 2026-05-19) describes Corporate RIA as letting fee-based advisors get the RIA experience while streamlining many of its burdens. It also lists optional business consulting and solutions for independent advisors, including real estate, insurance, business operations, business structure, talent sourcing, paraplanning and admin extension. It says independent advisors are supported by dedicated divisional management and corporate leadership.
   - `RJF-PR-web-independent-advisor#1` (press, 2026-05-19): "Succession and acquisition: Make career-critical decisions with specialized guidance Business consulting Unlock the power of independence with the support of consultants dedicated to helping advisors navigate business ow..."
9. On the call published July 2026, CEO Paul Shoukry described the firm as "agnostic" about how an advisor affiliates. He said the firm wants advisors to fall in love with its culture, values, platform and capabilities, and that how they affiliate is something it is "indifferent to." He said the firm has "the largest addressable market in the industry" because it has all the affiliation options. He also cited a 97% advisor satisfaction rate from its surveys and called retention "the foundation for the growth."
   - `RJF-TR-2026Q2#26` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director And we have 97% adviser satisfaction rate, 97% adviser satisfaction rate with our surveys, which is the best I know of in the industry when I speak to other CEOs and other firms. And so..."
10. On the call published January 2026, Shoukry said the firm has the largest addressable market across its affiliation options, from employee to independent contractor to RIA custody. He said it has critical mass and decades of experience in all of them, and that it is not a new venture or a test. He said advisors are coming from wirehouses, regionals and other independents.
   - `RJF-TR-2025Q4#50` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial Yeah, I mean, I hate to speak on any specific M&A or transactions. We have a lot of friendly competitors, and they're doing, you know, good jobs keeping the advisors, you know,..."
11. In October 2024, then-CEO Paul Reilly said RCS had by far the highest percentage growth. He said that in dollar terms the lead had alternated between channels: independent a couple of years earlier, and the employee channel that year. He said the firm no longer sees independents growing faster in up markets and employees in slow markets. In his words, it is "really just where we can meet the teams that like an affiliation option."
   - `RJF-TR-2024Q3#66` (transcript, 2024-10-23): "Paul Reilly Chair and CEO at Raymond James Financial You know, it depends on how you want to look at it. In our RIA part, RCS, it is by far the highest percentage growth. And, you know, as consistent with industry trends..."
12. On the call published April 2026, Shoukry said that across all affiliation options, which the firm calls adviser choice, the firm's approach is what has driven 7% annualized net new assets for the first half of its fiscal year. He credited both recruiting and strong retention. In the fiscal second quarter, domestic net new assets were $23 billion, a 5.8% annualized growth rate. Recruits to the domestic independent contractor and employee channels had trailing 12-month production of $141 million and nearly $21 billion of client assets at their previous firms.
   - `RJF-TR-2026Q1#23` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director And so I think the valuation -- there'll be close eyes on the valuation in that space to see what the ongoing commitment and value prices that they'll be willing to pay will be going fo..."
   - `RJF-TR-2026Q1#4` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director In the Private Client Group, we ended the quarter with $1.7 trillion of client assets under administration down slightly compared to the preceding quarter, but representing year-over-ye..."
13. On the call published July 2026, management reported domestic net new assets of $21.7 billion in the fiscal third quarter, a 5.5% annualized growth rate. Recruits to the domestic independent contractor and employee channels had trailing 12-month production of $156 million and nearly $23 billion of client assets at their previous firms. Management said strong retention and recruiting momentum show Raymond James remains a destination of choice for advisers across its affiliation options.
   - `RJF-TR-2026Q2#5` (transcript, 2026-07-22): "Paul Marone Shoukry CEO & Director In the Private Client Group, we ended the quarter with a record $1.86 trillion of client assets under administration, up 9% from the preceding quarter and 18% year-over-year. Our growth..."
14. The 10-Q for the period ended December 2025 (published February 2026) states that the firm offers loans to prospective financial advisors for recruiting and retention purposes. The offers are contingent on events including the individuals joining or continuing their affiliation, and on meeting other conditions in their offer. The fiscal 2025 10-K says the allowance for credit losses on loans to financial advisors takes into account the advisor's affiliation status, meaning whether the advisor is actively affiliated or has terminated affiliation.
   - `RJF-10Q-2025Q4#142` (10-Q, 2026-02-06): "Because many of our lending commitments expire without being funded in whole or in part, the contractual amounts are not estimates of our actual future credit exposure or future liquidity requirements. The allowance for ..."
   - `RJF-10K-2025#462` (10-K, 2025-11-25): "We estimate credit losses on unfunded lending commitments using a methodology consistent with that used in the corresponding bank loan portfolio segment and also based on the expected funding probabilities for fully bind..."
15. The fiscal 2025 10-K (November 2025) names recruiting-related risks. The firm has been subject to claims of unfair hiring practices and may face more. It participates, with limited exceptions, in the voluntary Protocol for Broker Recruiting, which governs the client information advisors may take and their ability to solicit prior clients. The 10-K says this ability makes clients of a moving advisor more likely to open accounts at the new firm, and that competitors could withdraw from the Protocol.
   - `RJF-10K-2025#91` (10-K, 2025-11-25): "Moreover, companies in our industry whose employees or independent contractors accept positions with competitors frequently claim that those competitors have engaged in unfair hiring practices. We have been subject to se..."

**Gaps (named by the answer)**

- Raymond James: Headline payout ranges are published (company recruiting page, as of 2026-04-21); the full payout grid is not public. The payout percentage for Bank & Credit Union is not stated; the page says only that compensation comes from the financial institution. *Would fill it:* Raymond James advisor recruiting materials or divisional recruiting teams (payout grid and footnotes)
- Revenue, margin or profitability by affiliation channel (employee, independent contractor, RCS, Bank & Credit Union) was not found. Neither was the firm's cost of supporting each model, so the commercial economics to the firm per channel cannot be shown. *Would fill it:* 10-K Private Client Group segment disclosure and investor-day deck, or a management answer on channel economics
- The page footnotes (** and ***) that qualify the payout figures were not included in the evidence. *Would fill it:* Full text of the Raymond James affiliation options web page

### Q15: What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

**Verdict: FAIL** (r, s). Advisor-led side now present (EDJ revenue split, MS fee-based share), but Schwab's own revenue composition is missing and the answer declines to state the mechanism. Borderline.

Tier 3, use case `mechanism`. Expected behavior `answer`, got `answer`. Retrieval: 30 passages, mode `entity`.

*Passes if:* It uses disclosed revenue composition for each model and explains the structural difference as a mechanism, not as a ratio. Where the comparison breaks down, it says so.

**Claims**

1. Schwab, 2Q25 earnings call (published July 2025): CEO Rick Wurster pointed to client activity and balance-sheet products as business fundamentals, citing margin loans up 16%, Pledged Asset Line balances at a record $21 billion, and record managed investing flows that helped assets in its wealth and asset management businesses reach all-time highs.
   - `SCHW-TR-2025Q2#8` (transcript, 2025-07-18): "Rick Wurster President and CEO at Schwab As we look to the future, we remain confident we'll continue to drive growth across a range of environments. Our competitive position remains unmatched. We are number one in the i..."
2. Edward Jones, 10-Q for 2Q25 (published August 2025): the firm attributed net revenue growth of 9% to $8,402 primarily to fee revenue. It credited higher average market levels and continued investment of client dollars into advisory programs. It said interest and dividends revenue decreased, mainly because of lower interest earned on short-term investments and government and agency obligations.
   - `EDJ-10Q-2025Q2#69` (10-Q, 2025-08-08): "Average client AUC increased 11% during the first half of 2025 compared to the same period in 2024, reflecting increases in the market value of client assets as well as the cumulative impact of net new assets gathered. A..."
3. Edward Jones, 10-Q for 3Q25 (published November 2025): asset-based fee revenue rose 15% to $3,667 in the quarter, primarily from advisory program fees, on higher average market levels and continued investment of client dollars into advisory programs. Trade revenue (commissions and principal transactions) rose only 1% to $448.
   - `EDJ-10Q-2025Q3#78` (10-Q, 2025-11-07): "client asset values ($ billions)(1): Advisory programs $ 982.3 $ 819.7 20% $ 924.1 $ 782.6 18% Mutual fund assets held outside of $ 704.5 $ 643.5 9% $ 678.2 $ 620.3 9% advisory programs (1) Assets on which the Partnershi..."
4. Schwab, 2025 10-K (published February 2026): management says its strategy is based on the principle that trusted relationships will translate into more assets from new and existing clients, ultimately driving more revenue. It cites scale as a key competitive advantage, which lets it spread operating costs and amortize new investments over a large base of clients.
   - `SCHW-10K-2025#13` (10-K, 2026-02-25): "Management estimates that investable wealth in the United States (U.S.) (consisting of assets in defined contribution, retail wealth management and brokerage, and registered investment advisor channels, along with bank d..."
5. Edward Jones, 2025 10-K (published March 2026): the firm describes earning revenue on clients' assets through service fees and revenue sharing from mutual fund and insurance companies. It also earns cash solutions revenue from its Insured Bank Deposit Program, asset-based fees from trust and investment management services, and fees tied to its Money Market Fund. In Advisory Solutions, clients can elect a research model, in which the firm assumes full investment discretion, or a custom model built with their financial advisor.
   - `EDJ-10K-2025#23` (10-K, 2026-03-13): "Service Fees and Other Asset-Based Fees. The Partnership earns revenue on clients’ assets through service fees and revenue sharing received under agreements with certain mutual fund and insurance companies. Cash solution..."
   - `EDJ-10K-2025#20` (10-K, 2026-03-13): "and bonds. When investing in Advisory Solutions, the client may elect either a research or custom model. If the client elects a research model, the Partnership assumes full investment discretion on the account and the cl..."
6. Morgan Stanley, 2025 10-K (published February 2026): Wealth Management states that any revenues it earns on client assets vary depending on the services and products provided. It reports advisor-led client assets of $5,715 billion at December 31, 2025, of which fee-based client assets were $2,753 billion, or 48%.
   - `MS-10K-2025#166` (10-K, 2026-02-19): "NNA represent client asset inflows, including interest, dividends and asset acquisitions, less client asset outflows, and excluding the impact of business combinations/divestitures and the impact of fees and commissions...."
7. Schwab, April 2026 monthly activity report (published May 2026): Schwab earns a fixed net yield on client margin loans and short credits tied to certain long/short strategies. It excludes those balances from average interest-earning assets starting in December 2025. It reports transactional sweep cash held on the balance sheet, including bank sweep deposits and broker-dealer cash balances.
   - `SCHW-MONTHLY-2026-04#9` (monthly, 2026-05-14): "(4) Balances include margin loans and short credits related to certain long/short strategies from which the Company earns a fixed net yield. For the month of April 2026, margin loans totaled $29.6 billion and short credi..."
8. Edward Jones, 2Q26 10-Q (published August 2026): the firm splits net revenue into fee revenue, trade revenue, net interest and dividends revenue, and other revenue. Advisory program fees are based on the average daily market value of client assets, so they move with market values and with client dollars invested or divested. Account and activity fees depend on the number of client accounts and the variety of services. Trade revenue depends on trading volume, product mix, trade size and margins earned, all of which can be affected by market volatility.
   - `EDJ-10Q-2026Q2#55` (10-Q, 2026-08-07): "The Partnership broadly categorizes its net revenues into four categories: fee revenue, trade revenue, net interest and dividends revenue (net of interest expense) and other revenue, net. In the Partnership’s Consolidate..."
9. Schwab, 3Q26 earnings release (published October 2026): management describes a 'diversified business model' and says deeper client engagement across the platform is broadening its revenue model. Third-quarter revenue rose 17% year-over-year to a record $7.2 billion.
   - `SCHW-PR-2026-10-15-01#2` (press, 2026-10-15): "3Q25 grew to $37.3 billion, up 59% year-over-year, while net flows into Schwab Wealth AdvisoryTM increased 55%.” President & CEO Rick Wurster Diversified Revenue Growth 17% “Deeper client engagement across Schwab's platf..."
10. Morgan Stanley Wealth Management supplement for 3Q26 (published October 2026): advisor-led client assets were $6,631 billion, of which fee-based client assets were $3,155 billion, or 48%. Fee-based asset flows were $80.5 billion. Deposits were $465 billion, with an annualized weighted average cost of deposits of 2.72% for the period average. The firm separately reports a self-directed channel of $1,802 billion in client assets.
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."

**Adjacent evidence (a related but different quantity)**

1. On the 3Q25 call (October 2025), Morgan Stanley CEO Ted Pick described the firm's business model as 'activity-based'.
   - *Differs because:* It describes Morgan Stanley's overall firm model, not Schwab or an advisor-led wealth revenue breakdown.
   - `MS-TR-2025Q3#3` (transcript, 2025-10-15): "Ted Pick Chairman and CEO at Morgan Stanley Our business model is activity-based, and while we cannot control the broader economic and market backdrop, the heart of the Morgan Stanley investment thesis remains our delive..."
2. Bank of America GWIM, 1Q26 call (April 2026): management cited average loans up 13% led by custom lending and securities-based lending, and said it is focused on pricing discipline and adviser productivity.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-TR-2026Q1#26` (transcript, 2026-04-15): "Alastair Borthwick Chief Financial Officer Pretax margin was 26%, reflecting the operating leverage achieved through disciplined expense management. Client balances increased to $4.6 trillion, up 10% year-over-year suppo..."

**Gaps (named by the answer)**

- Schwab's revenue mix (net interest revenue, asset management and administration fees, trading revenue) and its net interest margin or yield on client assets are not shown in the evidence provided. The comparison therefore rests on each firm's described drivers, not on a revenue-per-asset figure. *Would fill it:* Schwab 10-K or 10-Q net revenue and net interest revenue tables, and Schwab earnings supplement
- A revenue-to-client-asset yield for an advisor-led firm (for example Edward Jones or Morgan Stanley Wealth Management) on the same basis is not in the evidence provided. *Would fill it:* Edward Jones 10-K or 10-Q net revenue by category and average client assets; Morgan Stanley Wealth Management segment disclosure
- No source in the evidence states why the two models differ. The chunks describe each firm's revenue sources separately, and a causal comparison would be inference. *Would fill it:* Management commentary or investor-day materials that compare advisor-led and self-directed or custody-led economics

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q16: What will receiving financial advice in the future look like for clients?

**Verdict: PASS**. Organised by position, each attributed and dated, no forecast of its own.

Tier 3, use case `theme_scan`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `theme`.

*Passes if:* It presents the spread of positions organised by position rather than by firm, each attributed and dated, and offers no single forecast of its own.

**Claims**

1. More holistic, bespoke advice supported by technology and AI: on the 1Q26 earnings call (published April 2026), Raymond James CEO Paul Shoukry said advisers "have been expected and will continue to be expected to provide more holistic and bespoke financial advice to their clients over time." He said this requires the firm to provide technology, and that "AI can actually help." He cited $1.1 billion spent on technology and AI, covering adviser tools and client tools, plus lending (SBL and mortgage) and insurance.
   - `RJF-TR-2026Q1#51` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director But you also have to have competitive technology -- that's why we spent $1.1 billion on technology and AI and all the components of technologies from the adviser tools to the client too..."
2. Wider planning and new client segments and channels: the Edward Jones 2025 10-K (published March 2026) says the Partnership is investing in initiatives to meet clients' planning, investing, saving, spending, borrowing and comprehensive needs. These include Financial Planning Services, where clients "receive a more personalized experience with additional planning capabilities." They also include High Net Worth, Workplace, and a new digital platform for Next Generation investors. The filing says the Partnership "cannot reliably predict the timing or outcome of the initiatives."
   - `EDJ-10K-2025#88` (10-K, 2026-03-13): "The Partnership has been actively pursuing and making substantial investments in additional strategies, solutions, products, structures and third-party relationships (collectively, "initiatives") to meet clients' plannin..."
3. Team-based, one-stop-shop service for wealthier households: Cerulli's Global Wealth Transfer research (published October 2025) says that in the HNW space, practices across all intermediary channels are increasingly creating team-based structures. They are also receiving enhanced home-office service and product support, "allowing advisors to be clients' one-stop shop for all their needs." Cerulli also finds a significant uptake in advice consumption and reliance on advisors as investors move into their 50s.
   - `CERULLI-GWT-2025#19` (research, 2025-10-29): "Those who expect to receive substantial wealth will be receiving it at a pivotal time. These households are in their 'Sandwich Generation' years-financially tied to their children while also worried about responsibility ..."
4. Earlier engagement and a defined premium experience for mass-affluent prospects: Cerulli (published March 2026) says future prospects are likely to hold several financial-services provider relationships (banking, retirement plans, insurance, mortgages, tax preparation) before reaching wealth-management minimums. Its analyst says providers will need to engage prospects earlier or find better ways to displace incumbents. He also says providers must define what a premium experience entails. Cerulli reports that 32% of affluent respondents prefer the same provider for investing and banking and have already chosen to do so. Opportunities to engage new clients fall from 44% among the affluent under 30 to 24% among those in their 50s.
   - `CERULLI-MASS-AFFLUENT-2026#1` (research, 2026-03-25): "“Though this strategy has proven effective, it faces increased pressure as competitors seek additional options to connect with prospects earlier in the financial lifecycle.” Acting earlier matters. According to Cerulli, ..."
5. Platform infrastructure that follows client choice of technology: on the 2Q26 call (published July 2026), Schwab CEO Rick Wurster said Schwab is building a technology platform to support the industry "well into the future." He said the firm is "actively building infrastructure to support client activity on the technology of clients' choice," including possible digital markets infrastructure and tokenized securities. He said it is unclear how much the tokenization market will take off. He also pointed to Schwab's combination of "people in AI" and scale.
   - `SCHW-TR-2026Q2#13` (transcript, 2026-07-21): "Richard Andrew Wurster CEO, President & Director Finally, we're building towards a technology platform that will support the industry well into the future. Whether that looks like it does today, where if the industry mov..."
6. Advice valued more under uncertainty: on the 1Q25 call (published April 2025), Morgan Stanley's CFO said clients "continue to entrust us with more of their assets, reinforcing the value they place on advice." She also said "uncertainty has increased the value of advice."
   - `MS-TR-2025Q1#15` (transcript, 2025-04-11): "Sharon Yeshaya CFO at Morgan Stanley However, over the course of the recent two weeks, we have seen a notable increase in sweep balances, exceeding our internal forecasts. While this is likely associated with recent mark..."
7. Alternatives and AI tools for advisors (trade press, indicative only): InvestmentNews (published 2026-10-14) reports that Merrill Lynch, Morgan Stanley and Wells Fargo continue to boost sales of alternative investments and to develop AI functions for financial advisors in 2026. It says advisors sell alternatives to clients seeking higher yields and diversification.
   - `MER-TRADE-2026-10-14-IN-01#0` (trade, 2026-10-14): "Alternatives and AI in focus for advisors at wirehouses in Q3 InvestmentNews trade press - 2026-10-14 (tier 4, indicative only) Source: https://www.investmentnews.com/alternatives/alternatives-and-ai-in-focus-for-advisor..."

**Adjacent evidence (a related but different quantity)**

1. Bank of America's 3Q26 press release (published 2026-10-14) reports 80% of households actively using digital platforms, 2.3 million digitally-enabled sales (71% of total sales), and 24.2 million active Erica users, up 18%.
   - *Differs because:* These are consumer-banking digital usage figures, not a statement about how clients will receive financial advice in future.
   - `BAC-PR-2026-10-14-01#9` (press, 2026-10-14): "$113 million(H) - Net charge-offs of $1.1 billion were relatively flat • Noninterest expense of $5.8 billion increased 5%, driven by investments in technology and brand - Efficiency ratio of 50% • Return on average alloc..."

**Gaps (named by the answer)**

- No source in the evidence gives a single forecast of what the client advice experience will look like. The views above come from individual firm statements and Cerulli research, and they are not reconciled. Details of client-facing AI (how clients will interact with it) are not described. *Would fill it:* Firm investor-day decks or product announcements on client-facing AI and digital advice; Cerulli or other industry research on client advice preferences.

### Q17: What are these firms saying about AI in advice delivery, and who is claiming the most?

**Verdict: PASS**. Named advisor tools (RJF list, MS LeadIQ, Schwab Portfolio Insights) kept apart from volume claims (BAC counts) and aspirations; the 'who claims most' basis is visible. Borderline: Merrill's AI-tools remark not retrieved.

Tier 1, use case `theme_scan`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `theme`.

*Passes if:* It separates specificity from volume: a named tool actually deployed to advisors is a different claim from an aspiration on an earnings call, and the answer distinguishes them rather than treating both as "investing in AI."

**Claims**

1. Raymond James's investor day deck (June 2025), in its Financial Advisors section, lists advisor-facing tools including RJnet & Advisor Access GenAI Search, Zoom AI Meeting Summaries and Microsoft CoPilot. The slide gives no usage or outcome figures.
   - `RJF-DECK-2025-investor-day#121` (deck, 2025-06-05): "RJnet & Advisor Access GenAI Search Zoom AI Meeting Summaries Advisor Access Recommended Apps GenAI Search Microsoft CoPilot NASH Platform"
2. On the 3Q25 earnings call (October 2025), Morgan Stanley's CFO said early AI use cases, some live and some in pilot, are showing progress. She named DevGen AI (developer efficiency), Parable (data analysis and summaries) and LeadIQ, an AI-powered lead distribution platform that matches workplace and self-directed relationships and facilitates engagement with financial advisors. The named tools are about developers, data analysis and lead routing. None is described as delivering advice.
   - `MS-TR-2025Q3#8` (transcript, 2025-10-15): "Sharon Yeshaya CFO at Morgan Stanley Thank you and good morning. The firm delivered exceptional results in the third quarter, underscoring the power of our global integrated firm and the scale of $8.9 trillion in total c..."
3. Raymond James's 2025 10-K (published November 2025) says it uses and incorporates AI, including generative AI, in its technology platform. In Item 1A it names risks: inaccurate or biased output, security and privacy exposure that it seeks to mitigate with proprietary 'walled-garden' environments, and compliance costs from new AI rules.
   - `RJF-10K-2025#112` (10-K, 2025-11-25): "We use, develop, and incorporate within our technology platform and services, systems and tools that incorporate AI and machine learning, including generative AI. Although we strive to establish and maintain appropriate ..."
4. On the 4Q25 call (January 2026), Raymond James's CEO said the firm's suite of AI-based tools is focused on empowering financial advisors and professionals by applying AI to enhance service models in secure, scalable applications. No metrics were given in this passage.
   - `RJF-TR-2025Q4#6` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial The firm's suite of AI-based tools and technologies is focused on empowering financial advisors and professionals across the firm by applying artificial intelligence to enhance..."
5. Edward Jones's 2025 10-K (published March 2026) mentions AI only as a competitive factor. It says the industry is evolving technologically, with firms of all sizes providing enhanced digital experiences, including the use of artificial intelligence technologies and lower-cost computer-based 'robo-advice'. The chunk contains no Edward Jones AI deployment claims.
   - `EDJ-10K-2025#26` (10-K, 2026-03-13): "The Partnership is subject to intense competition in all phases of its business from broker-dealers, registered investment advisors, banks, insurance companies and other financial services firms, some of which are larger..."
6. On the 1Q26 call (April 2026), Schwab's CEO said Schwab is 'already an AI-enabled company' and that AI will accelerate its strategy. In his words, AI opens up new distribution channels and lets Schwab create personalized relationships with clients it has not been able to serve with a person-to-person relationship. This is a strategic claim without figures in this passage.
   - `SCHW-TR-2026Q1#12` (transcript, 2026-04-16): "Richard Andrew Wurster CEO, President & Director Finally, I want to spend a few minutes diving into how artificial intelligence is accelerating our strategy and the fast pace at which we are launching impactful AI capabi..."
7. On the 2Q26 call (July 2026), Bank of America's CEO said over 200,000 teammates use AI-enabled capabilities and generate more than 400,000 prompts a day. He said over 300 AI use cases were approved, 'all of which have good economics', of which 114 are live generative AI use cases and 34 are fully implemented. He said the tools are designed to help customer relationship managers prepare more thoroughly for client meetings and to improve productivity, consistency and client service. The 2Q26 deck (slide 20) shows the same counts: >300 approved AI/machine learning use cases, 114 live generative AI use cases, 34 fully deployed.
   - `BAC-TR-2026Q2#6` (transcript, 2026-07-14): "Brian Thomas Moynihan Chairman & CEO Before I turn it over to Alastair, I want to bring your attention to a couple slides. First, we have our digital slides in the appendix. In addition, we added a slide on AI at Slide 2..."
   - `BAC-DECK-2026Q2#29` (deck, 2026-07-14): ">300 AI / machine learning use cases approved / 114 live generative AI use cases with 34 fully deployed"
8. Schwab's 2Q26 deck (July 2026) lists 'AI-enabled Workflows & Capabilities' among the ongoing investments next to its managed investing net flows (Schwab Advisor Network and Schwab Wealth Advisory combined $28B in 1H25 versus $41B in 1H26, +50%). The slide lists AI as an investment and does not attribute the flows to it. Schwab's 2Q26 release describes Portfolio Insights as a generative AI feature giving clients a narrative snapshot of portfolio day change, news recaps and Schwab research snippets. Schwab states that it is not investment advice and that generative AI output may be inaccurate.
   - `SCHW-DECK-2026Q2#22` (deck, 2026-07-21): "Schwab Advisor Network TM Schwab Wealth Advisory TM 1H25 1H26 $28B $41B +50% Other MI  Expanded FC & WA Coverage  Discretionary Portfolios  Digital Enhancements  AI-enabled Workflows & Capabilities Note: T = Trillion..."
   - `SCHW-PR-2026-07-21-01#8` (press, 2026-07-21): "(2) Client margin loans and short credits related to certain long/short strategies utilized by RIAs are excluded from interest-earning assets and company funding sources. (3) Portfolio Insights (Insights) is a generative..."
9. Bank of America's 3Q26 earnings release (October 2026) repeats the figures of more than 200,000 teammates using AI tools and 300-plus approved use cases across the company. The firm says it is 'turning our scale into a competitive advantage'.
   - `BAC-PR-2026-10-14-01#2` (press, 2026-10-14): "With more than 200,000 teammates using AI tools and 300-plus approved use cases across the company, we are turning our scale into a competitive advantage. Bank of America Reports 3Q26 Net Income of $6.9 Billion; EPS of $..."
10. Trade press (InvestmentNews, October 2026, indicative only) quotes Wells Fargo's CEO saying the firm just launched an AI-powered tool for financial advisors that 'streamlines routine work and helps them access the information they need to better serve clients'. He called it 'the first of several capabilities planned as part of our broader AI strategy in wealth and investment management'. The same article says the Merrill executive did not mention new AI tools, though the message was that the firm would continue to invest in AI and digital capabilities.
   - `MER-TRADE-2026-10-14-IN-01#2` (trade, 2026-10-14): "At Merrill Lynch, client sales of alternative investments increased 19% in the quarter, said Eric Schimpf, president and co-head of Merrill Wealth Management, this morning during a conference call with reporters. While t..."
11. Who is claiming the most: on the evidence provided, Bank of America makes the most quantified AI claims (more than 200,000 users, more than 400,000 prompts a day, more than 300 approved use cases, 114 live generative AI use cases, 34 fully implemented). These counts cover the whole company and are not specific to advice delivery. Its only advice-related statement is that tools help relationship managers prepare for client meetings. Schwab makes the broadest strategic claim (AI as an accelerator of distribution and personalized relationships) without figures. Wells Fargo and Raymond James describe advisor-facing tools without metrics. Morgan Stanley's named AI examples are mostly not advice tools. Edward Jones makes no AI claims of its own in the evidence.
   - `BAC-TR-2026Q2#6` (transcript, 2026-07-14): "Brian Thomas Moynihan Chairman & CEO Before I turn it over to Alastair, I want to bring your attention to a couple slides. First, we have our digital slides in the appendix. In addition, we added a slide on AI at Slide 2..."
   - `BAC-DECK-2026Q2#29` (deck, 2026-07-14): ">300 AI / machine learning use cases approved / 114 live generative AI use cases with 34 fully deployed"
   - `BAC-PR-2026-10-14-01#2` (press, 2026-10-14): "With more than 200,000 teammates using AI tools and 300-plus approved use cases across the company, we are turning our scale into a competitive advantage. Bank of America Reports 3Q26 Net Income of $6.9 Billion; EPS of $..."
   - `SCHW-TR-2026Q1#12` (transcript, 2026-04-16): "Richard Andrew Wurster CEO, President & Director Finally, I want to spend a few minutes diving into how artificial intelligence is accelerating our strategy and the fast pace at which we are launching impactful AI capabi..."
   - `MER-TRADE-2026-10-14-IN-01#2` (trade, 2026-10-14): "At Merrill Lynch, client sales of alternative investments increased 19% in the quarter, said Eric Schimpf, president and co-head of Merrill Wealth Management, this morning during a conference call with reporters. While t..."
   - `RJF-TR-2025Q4#6` (transcript, 2026-01-28): "Paul Shoukry CEO at Raymond James Financial The firm's suite of AI-based tools and technologies is focused on empowering financial advisors and professionals across the firm by applying artificial intelligence to enhance..."
   - `MS-TR-2025Q3#8` (transcript, 2025-10-15): "Sharon Yeshaya CFO at Morgan Stanley Thank you and good morning. The firm delivered exceptional results in the third quarter, underscoring the power of our global integrated firm and the scale of $8.9 trillion in total c..."
   - `EDJ-10K-2025#26` (10-K, 2026-03-13): "The Partnership is subject to intense competition in all phases of its business from broker-dealers, registered investment advisors, banks, insurance companies and other financial services firms, some of which are larger..."

**Adjacent evidence (a related but different quantity)**

1. Deloitte Center for Financial Services (20 May 2026) predicts adviser productivity uplift from AI, especially agentic execution, could reach roughly 30% to 100% by 2032. It says advisers spend nearly 70% of their time on behind-the-scenes work.
   - *Differs because:* This is third-party research and a prediction about the industry, not a statement by any of the firms about their own advice delivery.
   - `DELOITTE-AGENTIC-2026#0` (research, 2026-05-20): "The agentic AI productivity wave is heading for wealth management Agentic AI capabilities could help firms lower cost-to-serve, enhance advice quality and delivery, improve adviser and client experience, and drive compet..."
2. Capgemini's World Wealth Report research (published 2026-06-03) describes a three-horizon roadmap that runs from AI-driven productivity tools, through to autonomous portfolio delivery and AI-enabled estate and tax planning embedded in client journeys.
   - *Differs because:* This is a research firm's recommended roadmap for the industry, not a claim by any firm about what it has delivered.
   - `CAPGEMINI-WWR-2026#17` (research, 2026-06-03): "The wealth management landscape is shifting from selling products to offering personalized, empathetic advice: future success will be defined by how well firms understand clients' lifestyles and aspirations, rather than ..."

**Gaps (named by the answer)**

- Merrill Lynch: no firm-sourced statement on AI in advice delivery. The only evidence is trade press saying its executive did not mention new AI tools. *Would fill it:* Bank of America earnings call and deck commentary on Merrill Wealth Management, or Merrill product releases
- Morgan Stanley: no statement in the evidence on AI tools that directly deliver advice to clients or support advisor-client conversations. Only the LeadIQ lead-distribution tool touches advisors. *Would fill it:* Morgan Stanley wealth management investor presentations and later earnings calls
- Edward Jones: no statement of its own AI deployment or claims. The 10-K cited covers only competition from AI and robo-advice. *Would fill it:* Edward Jones earnings commentary, investor materials or partnership communications
- No firm discloses outcome metrics (such as advisor productivity or client results) tied specifically to AI in advice delivery. Bank of America's figures count usage and use cases company-wide. *Would fill it:* Firm investor days, earnings decks or 10-K MD&A sections that quantify AI impact on advisors

### Q18: Where is the industry heading on fee structures and pricing transparency?

**Verdict: PASS**. Organised by position; research, survey, filings, trade press and ADV fee disclosures each labelled for what they are.

Tier 3, use case `theme_scan`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `theme`.

*Passes if:* Disclosed pricing changes, regulatory direction and published research are kept distinct from commentary and opinion, each labelled for what it is.

**Claims**

1. Position: pressure shows up as transparency and unbundling, not blanket cuts. A research piece published 2026-04-08 ("Can advisory fees survive the collapse of planning costs?", citing McKinsey) says it expects repricing of services where clients see no differentiation, such as basic tax projections. It calls the fear of an immediate industry-wide fee freefall "likely overstated". It says fee rates for relationships of more than $1 million have stayed at about 104 basis points since 2019, and that fee pressure will be uneven, "manifesting as demands for transparency and unbundled pricing rather than a blanket reduction in basis points."
   - `MCK-SIGNAL-SELLOFF-2026#9` (research, 2026-04-08): "While we anticipate a repricing of those services where clients perceive no differentiation, such as basic tax projections, the fear of an immediate, industry-wide fee freefall is likely overstated. In most models, plann..."
2. Position: client demand for fee transparency is strong. A Wealthtender study (published 2025-08-13) reports that 73% of people consider fee transparency the most important trust factor. It also reports that 38% of survey participants identified lack of fee transparency as a red flag. Pricing was the top factor (48%) in final advisor selection, though the source says the cheapest option is not necessarily best.
   - `WEALTHTENDER-ADVISOR-SEARCH-2025#57` (research, 2025-08-13): "Always ask for a clear, written explanation of all costs before engaging an advisor. Our study shows 73% of people consider fee transparency the most important trust factor. Q: Should I be suspicious if an advisor won’t ..."
3. Position: fees are drifting lower through passive products and mutual-fund fee changes. The Raymond James 10-K (period ended 2025-09-30, published 2025-11-25) says asset management fees may decline over time because of competition and contract renegotiation. It says the shift to passive products generates lower fees than active products, and that a continued trend toward passive investments or changes in the fee structure of asset management accounts would hurt revenues. The Edward Jones 2025 10-K (published 2026-03-13) says clients' mutual fund holdings have been affected by industry changes in fee structures, and that the firm has seen and may continue to see decreased margins on mutual funds. Bank of America's Q1 2026 10-Q (published 2026-05-01) cites "lower AUM pricing" as a partial offset to higher investment and brokerage services income.
   - `RJF-10K-2025#100` (10-K, 2025-11-25): "Our asset management fees may also decline over time due to factors such as increased competition and the renegotiation of contracts. Additionally, most of our clients may withdraw funds from under our management at thei..."
   - `EDJ-10K-2025#55` (10-K, 2026-03-13): "High inflation rates and market expectations of rising or prolonged inflation in the future can negatively influence net new assets, securities prices and activity levels in the securities markets. The Partnership has an..."
   - `BAC-10Q-2026Q1#31` (10-Q, 2026-05-01): "Noninterest income increased $723 million to $14.5 billion for the three months ended March 31, 2026 compared to the same period in 2025. The following highlights the significant changes. ● Service charges increased $113..."
4. Position: the research view (fee rates steady, pressure uneven) and the firms' risk-factor language (fees may decline) point in different directions on overall fee levels. The research says fees above $1 million have held at about 104 bps and rejects a blanket reduction. Raymond James and Edward Jones name fee decline or margin compression as risks.
   - `MCK-SIGNAL-SELLOFF-2026#9` (research, 2026-04-08): "While we anticipate a repricing of those services where clients perceive no differentiation, such as basic tax projections, the fear of an immediate, industry-wide fee freefall is likely overstated. In most models, plann..."
   - `RJF-10K-2025#100` (10-K, 2025-11-25): "Our asset management fees may also decline over time due to factors such as increased competition and the renegotiation of contracts. Additionally, most of our clients may withdraw funds from under our management at thei..."
   - `EDJ-10K-2025#55` (10-K, 2026-03-13): "High inflation rates and market expectations of rising or prolonged inflation in the future can negatively influence net new assets, securities prices and activity levels in the securities markets. The Partnership has an..."
5. Position: firms say they will adapt pricing to competition and client preferences. On the Raymond James fiscal Q2 2026 call (period ended 2026-03-31, published 2026-04-22), the CEO said the firm wants a "profitable and competitive and fair pricing structure". He said it would be flexible and open to evolving if the industry moves based on competitive pressures and client preferences, and that it reviews pricing, fees and payout on an ongoing basis.
   - `RJF-TR-2026Q1#48` (transcript, 2026-04-22): "Paul Marone Shoukry CEO & Director I mean, ultimately, we want to have a profitable and competitive and fair pricing structure. Fair for most importantly for the clients, also the financial professionals and the firm. An..."
6. Position: some firms present transparency and low cost as part of their model. Schwab's Q2 2026 10-Q (published 2026-08-07) describes its strategy as offering a broad range of products "with a focus on transparency, value, and trust". It says management couples scale with expense discipline to keep costs low and products affordable. Schwab's 2025 10-K (published 2026-02-25) says its operating efficiency lets it price products and services competitively.
   - `SCHW-10Q-2026Q2#8` (10-Q, 2026-08-07): "This strategy emphasizes placing clients’ perspectives, needs, and desires at the forefront. Because investing plays a fundamental role in building financial security, we strive to deliver a better investing experience f..."
   - `SCHW-10K-2025#14` (10-K, 2026-02-25): "• Operating Efficiency - Coupled with scale, our operating efficiency and sharing of infrastructure across different businesses creates a cost advantage that enables us to competitively price products and services while ..."
7. Position: distributors are adding platform charges. Trade press (published 2026-09-29) reports that Merrill's new "support fee" caps out at 10 basis points. It says Merrill's fee-based program pricing is, per sources, typically 1.00% to 1.40% and as high as 1.75%. It also says sources trace platform tolls at large distributors to the zeroing out of commissions, and that Schwab introduced data fees over seven years ago. This is trade-press reporting, not a firm disclosure.
   - `MER-TRADE-2026-09-29-RB-01#7` (trade, 2026-09-29): "Larger asset managers are likely to take a bigger hit too, in real terms, than the middle-market, due to Merrill's new “support fee," that made news in July. In absolute terms, the support fees, which cap out at 10 basis..."
8. Context, firm disclosures on current fee structures. Morgan Stanley's ADV brochure (published 2026-11-04) describes a wrap fee with a maximum annual asset-based Morgan Stanley Advisory Fee of 2.0%, plus a Sub-Manager Fee that generally ranges from 0.20% to 0.75% for SMAs. Raymond James's ADV (published 2026-09-14) describes Wealth Advisory Services fees as hourly (up to $400 per hour), flat-dollar, or a percentage of assets under advisement not to exceed 2.25% annually. It also says some legacy relationships pay under older fee schedules.
   - `MS-ADV-2026#127` (adv, 2026-11-04): "You pay an asset-based fee to MSWM ("Morgan Stanley Advisory Fee") for our investment advisory services, portfolio implementation services, custody of account assets with MSWM, trade execution with or through MSWM or its..."
   - `RJF-ADV-2026#33` (adv, 2026-09-14): "Under our Wealth Advisory Services Program, Fees for planning services can be structured as an hourly rate or fixed (flat) dollar Fee, while investment consulting services may be assessed as an hourly rate, a fixed (flat..."

**Gaps (named by the answer)**

- No industry-wide data or forecast on future fee levels or regulatory direction on pricing disclosure was found. The evidence is a research note, one consumer study, firm filings and one trade article. *Would fill it:* Industry fee-benchmarking studies (for example advisory fee surveys), regulatory releases on fee disclosure, and trade press tracking pricing changes

### Q19: How should the preferences of younger investors shape Edward Jones's offerings?

**Verdict: PASS**. Cohort preferences (Cerulli, BofA studies, dated, samples named as HNW) and competitor moves aimed at the cohort (Schwab Gen Z/millennial share, two dates); stops at 'should'. Borderline: EDJ's own next-gen platform not retrieved.

Tier 3, use case `segment_evidence`. Expected behavior `answer_with_boundary`, got `answer_with_boundary`. Retrieval: 28 passages, mode `entity+theme`.

*Passes if:* It assembles published evidence on the cohort's preferences and competitor moves aimed at it, each dated and sourced -- then stops at the word "should" and says so.

**Claims**

1. The Edward Jones 2025 10-K (published 2026-03-13) lists competition for clients and personnel amid generational wealth transfer, "changing client demographics, preferences and values," technology and artificial intelligence among the Partnership's strategic risks. It says it addresses them through initiatives to deliver enhanced value and impact for current and potential clients.
   - `EDJ-10K-2025#304` (10-K, 2026-03-13): "The Partnership seeks to address its strategic risks, most notably competition for clients and personnel in light of the evolving financial services industry and generational wealth transfer, changing client demographics..."
2. The Edward Jones 2025 10-K (published 2026-03-13) says its ability to compete and adapt its business model may be adversely affected by generational wealth transfer, "changing client expectations for expanded product offerings and technology needs," and changing client demographics, preferences and values. It also says competitors increasingly offer personalized services and enhanced digital experiences, including AI and lower-cost "robo-advice". The Partnership expects this to keep requiring significant investment in financial advisors, technology infrastructure, digital initiatives and data-powered tools.
   - `EDJ-10K-2025#56` (10-K, 2026-03-13): "All aspects of the Partnership’s business are highly competitive. The financial services industry continues to innovate and evolve technologically, with an increasing number of firms of all sizes providing personalized s..."
3. Cerulli (published 2025-10-29) estimates Millennials will inherit $46 trillion over the next 25 years, more than Generation X households. Gen X stands to inherit the most in the next 10 years, $14 trillion against Millennials' $8 trillion. Cerulli also notes that while older investors tend to be more advisor-reliant, younger investors prefer to retain a greater degree of control of at least part of their investing lives.
   - `CERULLI-GWT-2025#1` (research, 2025-10-29): "Millennials will be inheriting more over the course of the next 25 years ($46 trillion) than Generation X households. However, Gen X stands to inherit the greatest portion of assets in the next 10 years, totaling $14 tri..."
4. The 2024 Bank of America Private Bank Study of Wealthy Americans (published 2024-06-18) reports that Millennials and Gen Z allocate three times more of their portfolios to alternative investments than older generations. For respondents aged 21-43 it lists the greatest growth opportunities as real estate investments (31 percent), crypto/digital assets (28 percent) and private equity (26 percent). This is a high-net-worth sample, not Edward Jones clients.
   - `BOFA-PB-STUDY-2024#0` (research, 2024-06-18): "June 18, 2024 at 9:00 AM Eastern B of A BofA Private Bank Study of Wealthy Americans Finds Generational Divide in Investing, Giving and Preserving Wealth Millennials and Gen Z Allocate Three Times More of Their Investmen..."
5. The 2026 Bank of America Private Bank study (published 2026-06-17) reports that 47% of young investors use AI to research companies or markets and 87% are comfortable with advisors using AI to help manage portfolios. It also reports that 65% still prefer to receive investment advice from a human advisor.
   - `BOFA-PB-STUDY-2026#15` (research, 2026-06-17): "forty seven percent 47% of young investors use AI to research companies or markets, and eighty seven percent 87% are comfortable with advisors using AI to help manage portfolios, yet sixty five percent 65% still prefer t..."
6. On Schwab's 3Q25 call (October 2025), CEO Rick Wurster said nearly one-third of new-to-firm retail households this year are Gen Zers. He said they are being met in the channels where they look for investing information, and that they learn about finances primarily through social media and family. This is a peer's statement, not Edward Jones's.
   - `SCHW-TR-2025Q3#11` (transcript, 2025-10-16): "Rick Wurster President and CEO at Schwab We're continuing to attract and serve RIAs of all sizes, and our advisor services business is thriving. In our retail business, we are attracting and serving investors of all ages..."
7. On Schwab's 3Q26 call (October 2026), CEO Rick Wurster said approximately 70% of new-to-firm retail households are Gen Z and millennials. He also said Schwab's retention rate around wealth transfers is "extremely high". This is a peer's statement, not Edward Jones's.
   - `SCHW-TR-2026Q3#11` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director Turning to our retail business. We are serving individual investors who span the investor spectrum. Our retail business is built to win across generations, wealth tiers, i..."
8. The evidence above only provides objective context for the strategic question asked. Whether or how Edward Jones should act is a judgment for the strategy team to make, beyond the scope of this evidence engine.
   - `EDJ-10K-2025#304` (10-K, 2026-03-13): "The Partnership seeks to address its strategic risks, most notably competition for clients and personnel in light of the evolving financial services industry and generational wealth transfer, changing client demographics..."
   - `EDJ-10K-2025#56` (10-K, 2026-03-13): "All aspects of the Partnership’s business are highly competitive. The financial services industry continues to innovate and evolve technologically, with an increasing number of firms of all sizes providing personalized s..."
   - `CERULLI-GWT-2025#1` (research, 2025-10-29): "Millennials will be inheriting more over the course of the next 25 years ($46 trillion) than Generation X households. However, Gen X stands to inherit the greatest portion of assets in the next 10 years, totaling $14 tri..."
   - `BOFA-PB-STUDY-2026#15` (research, 2026-06-17): "forty seven percent 47% of young investors use AI to research companies or markets, and eighty seven percent 87% are comfortable with advisors using AI to help manage portfolios, yet sixty five percent 65% still prefer t..."

**Adjacent evidence (a related but different quantity)**

1. A Kitces.com commentary reprinted 2026-08-18 discusses Edward Jones's deal with Quicken. The author describes Edward Jones as having 20,000 advisors and nearly 10 million clients. He questions the choice of Quicken over other personal-financial-management platforms and says the deal may spur broader advisor offerings.
   - *Differs because:* Trade-press reporting is indicative, not authoritative. It is the author's commentary on Edward Jones's technology and does not link the deal to the preferences of younger investors.
   - `EDJ-TRADE-2026-08-18-IN-01#4` (trade, 2026-08-18): "In turn, it's also striking that Edward Jones chose Quicken… a PFM software that originated in the DOS era more than 40 years ago, still runs an active desktop version for consumers (how exactly will that integrate to… a..."
   - `EDJ-TRADE-2026-08-18-IN-01#5` (trade, 2026-08-18): "Ultimately, though, Edward Jones' deal with Quicken is still likely to make waves, if only for the sheer size of Edward Jones itself… with 20,000 advisors and nearly 10 million clients they serve (compared to the only-2-..."

**Gaps (named by the answer)**

- Edward Jones's own disclosure of the age mix of its clients or new clients, or of younger investors' preferences. The 10-K cites changing demographics and preferences only in general terms. *Would fill it:* Edward Jones earnings materials or investor presentations, or internal client-demographics and survey data
- Edward Jones's specific product or technology responses aimed at younger investors (for example alternatives, digital self-direction or AI tools) are not described in the evidence provided. *Would fill it:* Edward Jones annual report business discussion, press releases and product announcements

### Q20: What evidence is there about how clients under 40 choose a financial advisor?

**Verdict: FAIL** (r). Behavior fixed, but no finding is about under-40 advisor choice with its sample: UBS and BofA give no age cut-off or sample size; the Fidelity study is not retrieved.

Tier 1, use case `segment_evidence`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `theme`.

*Passes if:* It returns actual survey findings with their source, sample and date -- not a generalisation about a generation. Two surveys that disagree are reported as disagreeing.

**Claims**

1. The Bank of America Private Bank 2026 Study of Wealthy Americans (published 2026-06-17) reports that 65% of young investors still prefer to receive investment advice from a human advisor. The same study reports 47% of young investors use AI to research companies or markets, and 87% are comfortable with advisors using AI to help manage portfolios. The chunk does not define "young investors" by age.
   - `BOFA-PB-STUDY-2026#15` (research, 2026-06-17): "forty seven percent 47% of young investors use AI to research companies or markets, and eighty seven percent 87% are comfortable with advisors using AI to help manage portfolios, yet sixty five percent 65% still prefer t..."
2. The UBS research "What does the next generation look for in a wealth manager?" (published 2026-04-22) reports that experience and expertise top the next generation's wish list when choosing a wealth manager (79%). It also reports that 56% want advisors who can build trusted relationships across generations, and 41% want an advisor who fully understands the next generation's needs. The chunk's own wording refers to the "next generation" and does not state an under-40 age cut-off.
   - `UBS-NEXTGEN-2026#83` (research, 2026-04-22): "When choosing a wealth manager, experience and expertise sit at the top of the next generation's wish list (79%). As a second generation entrepreneur explained, "We want wealth planning expertise. An expert should defini..."
3. The same UBS research reports that priorities vary by gender. Women emphasize experience (90%), frequent engagement (35%) and early commitment to the next generation (40%). Men are more likely to prioritize advisors with a deep understanding of their financial goals (49%).
   - `UBS-NEXTGEN-2026#83` (research, 2026-04-22): "When choosing a wealth manager, experience and expertise sit at the top of the next generation's wish list (79%). As a second generation entrepreneur explained, "We want wealth planning expertise. An expert should defini..."
4. Cerulli's wealth-transfer research (published 2025-10-29) states that older investors tend to be more advisor-reliant, while younger investors prefer to retain a greater degree of control of at least part of their investing lives. Cerulli defines Millennials as ages 27-42 and Gen Z and younger as under 27, as of 2023.
   - `CERULLI-GWT-2025#1` (research, 2025-10-29): "Millennials will be inheriting more over the course of the next 25 years ($46 trillion) than Generation X households. However, Gen X stands to inherit the greatest portion of assets in the next 10 years, totaling $14 tri..."
5. Schwab's CEO said on the 3Q26 earnings call (October 2026) that the firm is attracting younger clients, with approximately 70% of new-to-firm retail households being Gen Z and millennials. This shows which firm younger clients are joining. It does not state their selection criteria.
   - `SCHW-TR-2026Q3#11` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director Turning to our retail business. We are serving individual investors who span the investor spectrum. Our retail business is built to win across generations, wealth tiers, i..."
6. A Schwab investor day deck (published 2026-05-14) shows Gen Z and Millennial investors at 61% of new clients. The same slide shows new-to-firm retail households up 14% and new-to-firm retail net new assets up 25% over 2024-2025. The 61% figure differs from the roughly 70% household figure from the 3Q26 call. The two figures come from different sources and the chunks do not reconcile them.
   - *Flagged by code:* number_not_found
   - `SCHW-DECK-2026-investor-day#131` (deck, 2026-05-14): "Marketing is foundational to enterprise growth. +14% New-to-Firm Retail HHs 2024 - 2025 Fuels consistent, high-quality enterprise growth while attracting new clients. +25% New-to-Firm Retail NNA 2024 - 2025 61% Gen Z & M..."

**Adjacent evidence (a related but different quantity)**

1. Merrill's materials (a 2026 Bank of America Q2 deck and a recruiting web page as of 2026-11-03) cite advisor recognitions aimed at younger advisors. These include 24 Merrill advisors on Financial Planning's 2026 Top 40 Brokers Under 40 and 446 advisors on Forbes' 2025 Top Next-Generation Wealth Advisors Best-in-State list.
   - `BAC-DECK-2026Q2#36` (deck, 2026-07-14): "Merrill earned the most recognitions on Forbes' 2026 Top Wealth Advisors Best-inState and Best-in-State Wealth Management Teams lists 23 Merrill advisors on Forbes' 2026 Top 100 Women Wealth Advisors >300 Merrill advisor..."
   - `MER-PR-web-becoming-a-merrill-lynch-advisor#1` (press, 2026-11-03): "Suite of state-of-the-art, user-friendly tools and resources designed to streamline your practice A client-focused and advisor-centric culture of collaboration A client-first planning process, powered by Merrill exclusiv..."
2. Bank of America's GWIM press release (published 2026-01-14) lists No. 1 on Financial Planning's Top 40 Advisors Under 40 List (2025).
   - `BAC-PR-2026-01-14-01#12` (press, 2026-01-14): "6 Percentage of digitally active Private Bank core relationships across the enterprise ($3MM+ in total balances) as of November 2025. Includes third-party activities and excludes Irrevocable Trust-only relationships, Ins..."

**Gaps (named by the answer)**

- No source in the evidence directly surveys clients under 40 on how they choose an advisor, such as referral, fees, digital experience or advisor age. Two sources use age-neutral labels: UBS's "next generation" and BofA's "young investors". UBS's sample is wealthy next-generation respondents, and its chunk gives no age cut-off. *Would fill it:* Investor-demographic survey research (for example Cerulli, or a firm's Gen Z/millennial client study) with age-banded advisor-selection questions
- The evidence does not state whether clients under 40 choose between advisor-led and self-directed channels differently from older clients. Cerulli's statement on control preferences is qualitative only. *Would fill it:* Firm client-demographic disclosures by channel, or the full Cerulli report

### Q21: What do we know about the generational wealth transfer, and how are these five preparing for it?

**Verdict: PASS**. Estimates (Cerulli, UBS) with source and vintage kept separate from what each firm says it does; gaps per firm.

Tier 2, use case `segment_evidence`. Expected behavior `answer`, got `answer`. Retrieval: 30 passages, mode `entity+theme`.

*Passes if:* The two halves stay separate: published estimates of the transfer (with each estimate's source and vintage, because these figures get repeated far from their origin) and what each firm has actually said it is doing.

**Claims**

1. Market context - Cerulli report (published 2025-10-29): Cerulli projects households will transfer $123.7 trillion to heirs ($105 trillion) and charities ($18 trillion) between now and 2048. It puts inheritance at Generation Xers $39 trillion and Millennials $46 trillion. It expects women in the Baby Boomer and older generations to receive $40 trillion in 'horizontal' transfers, and women in younger generations to receive $47 trillion of the intergenerational transfer.
   - `CERULLI-GWT-2025#2` (research, 2025-10-29): "Wealth has been created and concentrated at a rapid pace in recent years and now is more likely to be held by older households. This dynamic has driven wealth transfer projections significantly higher-Cerulli projects ho..."
2. Market context - UBS next-generation report (published 2026-04-22): UBS estimates USD 83 trillion in private wealth will change hands globally over the next two to three decades. It attributes the shift to aging demographics, longer life expectancies and decades of rising asset prices. This is a global estimate with a different horizon from Cerulli's, so the two figures are not directly comparable.
   - `UBS-NEXTGEN-2026#6` (research, 2026-04-22): "The Great Wealth Transfer is no longer a distant forecast; it is a seismic shift already in motion. Over the next two to three decades, an estimated USD 83 trillion in private wealth will change hands globally, marking t..."
3. Market context - Cerulli (published 2025-10-29): Cerulli says women and next-generation clients differ in service preferences from current client demographics. It says these differences are likely to shift market share to the firms best prepared to meet the recipients' needs. It says home offices must supply the expertise, investment products and technology to win future high-net-worth clients.
   - `CERULLI-GWT-2025#24` (research, 2025-10-29): "With trillions of dollars already changing hands annually, the Great Wealth Transfer is in full swing. It is critical for advisors, their firms, asset managers, and other industry participants to enact best practices and..."
4. Stated exposure to wealth transfer - Edward Jones (oldest to newest): The 2Q25 10-Q (published 2025-08-08) says net new assets decreased by 10% versus 2Q24, with higher outflows. It lists 'an aging client base and generational wealth transfers outside the firm' among the factors. It also reports financial advisor attrition increased to 6.4%, primarily due to more retirements.
   - `EDJ-10Q-2025Q2#67` (10-Q, 2025-08-08): "The Partnership ended the second quarter of 2025 with a 12% increase in client assets under care ("AUC") to $2.3 trillion and a 9% increase in average client AUC, reflecting increases in the market value of client assets..."
5. Stated exposure to wealth transfer - Edward Jones: The 3Q25 10-Q (published 2025-11-07) says net new assets decreased 4% in the first nine months of 2025. It says the outflows 'continue an increasing downward trend' influenced by several factors, including an aging client base and generational wealth transfers outside the firm.
   - `EDJ-10Q-2025Q3#72` (10-Q, 2025-11-07): "Average client AUC increased 11% during the first nine months of 2025 compared to the same period in 2024, reflecting increases in the market value of client assets, as well as the cumulative impact of net new assets gat..."
6. Stated exposure to wealth transfer - Edward Jones: The 2025 10-K (published 2026-03-13) says the Partnership's ability to compete and adapt its business model may be adversely affected by the evolving industry and generational wealth transfer. It cites changing client expectations for products and technology, and changing client demographics, preferences and values.
   - `EDJ-10K-2025#56` (10-K, 2026-03-13): "All aspects of the Partnership’s business are highly competitive. The financial services industry continues to innovate and evolve technologically, with an increasing number of firms of all sizes providing personalized s..."
7. Stated exposure to wealth transfer - Schwab: On the 3Q26 call (published 2026-10-15), CEO Rick Wurster said roughly 80% of retail assets are held by ultra-high-net-worth and high-net-worth households. He said Schwab is 'well positioned to continue serving future generations when that wealth is passed on'. He also said its 'retention rate around wealth transfers is extremely high'.
   - `SCHW-TR-2026Q3#11` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director Turning to our retail business. We are serving individual investors who span the investor spectrum. Our retail business is built to win across generations, wealth tiers, i..."
8. Stated exposure to wealth transfer - Schwab: The 3Q26 deck (published 2026-10-15) shows 80% of retail assets held by U/HNW households and ~75% of assets retained in a wealth transfer event.
   - `SCHW-DECK-2026Q3#24` (deck, 2026-10-15): "ATTRACT ~70% NTF Retail HH are Gen Z & Millennials 1 SERVE 80% Retail Assets Held by U/HNW 2 HHs RETAIN ~75% Assets Retained in a Wealth Transfer Event 3"
9. Preparation - Edward Jones: The 2025 10-K (published 2026-03-13) names competition for clients and personnel amid the evolving industry and generational wealth transfer, changing client demographics, technology, AI and regulatory change as strategic risks. The firm says it addresses them through initiatives to deliver enhanced value and impact for clients. It says it continues to make significant investments to attract and retain qualified talent and offers a competitive compensation and benefits program for financial advisors.
   - `EDJ-10K-2025#304` (10-K, 2026-03-13): "The Partnership seeks to address its strategic risks, most notably competition for clients and personnel in light of the evolving financial services industry and generational wealth transfer, changing client demographics..."
10. Preparation - Edward Jones: The 2025 10-K says competitive forces have resulted, and are expected to continue to result, in significant investments in financial advisors and other human capital, technology infrastructure, digital initiatives, knowledge- and data-powered tools, and strategic relationships.
   - `EDJ-10K-2025#56` (10-K, 2026-03-13): "All aspects of the Partnership’s business are highly competitive. The financial services industry continues to innovate and evolve technologically, with an increasing number of firms of all sizes providing personalized s..."
11. Preparation - Schwab: The 3Q26 deck (published 2026-10-15) organizes its retail pitch as Attract, Serve and Retain. Under Attract, ~70% of new-to-firm retail households are Gen Z and Millennials. On the 3Q26 call, Wurster said Schwab is attracting younger clients, with approximately 70% of new-to-firm retail households Gen Z and millennials. He said Schwab is 'winning assets with all generations'.
   - `SCHW-DECK-2026Q3#24` (deck, 2026-10-15): "ATTRACT ~70% NTF Retail HH are Gen Z & Millennials 1 SERVE 80% Retail Assets Held by U/HNW 2 HHs RETAIN ~75% Assets Retained in a Wealth Transfer Event 3"
   - `SCHW-TR-2026Q3#11` (transcript, 2026-10-15): "Richard Andrew Wurster CEO, President & Director Turning to our retail business. We are serving individual investors who span the investor spectrum. Our retail business is built to win across generations, wealth tiers, i..."
12. Preparation - Morgan Stanley: The firm's strategic update deck (published 2026-01-15) lays out offerings across client growth cycles. Under 'Preserve Wealth' it lists full-service wealth advice and asset allocation and family office solutions, trust and estate planning. Under 'Invest for the Future' it lists financial wellness and employee benefits, and founders wealth strategies. The slide does not use the term wealth transfer.
   - `MS-DECK-2026-strategic-update#22` (deck, 2026-01-15): "Corporates Founders / Employees Early Stage Public Company Invest for the Future Financial Wellness and Employee Benefits Founders Wealth Strategies Preserve Wealth Full-Service Wealth Advice and Asset Allocation Family ..."
13. Preparation - Bank of America: A Bank of America Private Bank Q&A in the evidence (published 2026-06-17) says the Private Bank helps families plan for longevity and wealth transfer through trust and estate planning, business succession strategies and family education. It says advisors facilitate conversations across generations to help clients preserve wealth and prepare heirs. This is Private Bank content, not Merrill-specific.
   - `BOFA-PB-STUDY-2026#16` (research, 2026-06-17): "Advisors, support by award-winning digital platforms, work across disciplines, to help clients manage growth, liquidity, longevity, and legacy as their priorities evolve. Question: How does Bank of America Private Bank s..."
14. Preparation - Bank of America (GWIM segment, which combines Merrill and the Private Bank): The GWIM press release (published 2026-01-14, period 2025-12-31) lists No. 1 on Forbes' Top Next Generation Advisors (2025) and No. 1 on Financial Planning's Top 40 Advisors Under 40 List (2025). It also lists No. 1 in Managed Personal Trust AUM. These are rankings the segment cites, not a stated wealth-transfer program.
   - `BAC-PR-2026-01-14-01#12` (press, 2026-01-14): "6 Percentage of digitally active Private Bank core relationships across the enterprise ($3MM+ in total balances) as of November 2025. Includes third-party activities and excludes Irrevocable Trust-only relationships, Ins..."

**Gaps (named by the answer)**

- Stated exposure to wealth transfer - Morgan Stanley: not found in the evidence provided. *Would fill it:* Morgan Stanley 10-K risk factors, earnings call transcripts, or Wealth Management investor presentations
- Stated exposure to wealth transfer - Raymond James: not found in the evidence provided. *Would fill it:* Raymond James 10-K risk factors, earnings call transcripts, or investor day materials on next-generation clients
- Stated exposure to wealth transfer - Bank of America: not found in the evidence provided. The Private Bank Q&A and GWIM press release cover offerings and rankings, not exposure or retention figures. Merrill does not report standalone results. *Would fill it:* Bank of America 10-K or earnings call remarks on GWIM and Merrill client demographics, or the Merrill and Private Bank investor day deck
- Preparation - Raymond James: not found in the evidence provided. The Raymond James chunks cover associate development, AI productivity and an RIA custody recruiting page, none of which address wealth transfer. *Would fill it:* Raymond James Private Client Group investor day materials, earnings calls, or advisor-facing next-generation and succession programs
- The five firms are not named in the question. This answer assumes Edward Jones, Schwab, Morgan Stanley, Raymond James and Bank of America (Merrill and Private Bank), based on the firms covered in the evidence. *Would fill it:* Confirm the intended peer set with the requester

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q22: Net new assets by quarter for each of the five, with each firm's own definition of the metric.

**Verdict: PASS**. Value, period and source per cell for Schwab, EDJ, RJF and MS; MS and EDJ definitions quoted, RJF label and basis; Schwab definition and missing quarters marked as gaps; Merrill marked as not reporting, GWIM flows only as adjacent. Borderline: Schwab definition absent.

Tier 1, use case `benchmark`. Expected behavior `answer`, got `answer`. Retrieval: 30 passages, mode `entity`.

*Passes if:* Value, period and source document for every cell, with each firm's definition alongside. A firm that does not report net new assets on this basis is marked as not reporting -- never as zero, and never quietly substituted with a near-neighbour metric.

**Claims**

1. Quarterly NNA - Schwab (reports "core net new assets"): The 2025 10-K (published 2026-02-25) states core net new assets for the fourth quarter of 2024 were $114.8 billion.
   - `SCHW-10K-2025#136` (10-K, 2026-02-25): "Reflecting the strength of equity markets and organic asset gathering, total client assets rose to $10.10 trillion as of year-end 2024, up 19% from year-end 2023. Core net new assets totaled $366.9 billion in 2024, up 20..."
2. Quarterly NNA - Schwab: The 1Q26 press release (published 2026-04-16) reports core net new assets of $140.0 billion, including a $17.5 billion outflow from a planned mutual fund clearing client deconversion; excluding that planned item, $157.5 billion. On the 1Q26 call the CEO cited $158 billion excluding the one-time outflow.
   - `SCHW-PR-2026-04-16-01#3` (press, 2026-04-16): "These actions reflect Schwab’s strong capital position as well as the sustained performance of the firm’s through-the-cycle financial model.” 1Q26 Common CFO Mike Verdeschi Stock Repurchases 1Q26 Client and Business High..."
   - `SCHW-TR-2026Q1#3` (transcript, 2026-04-16): "Richard Andrew Wurster CEO, President & Director Clients remain highly engaged, and they continue to turn to Schwab through volatile and uncertain markets. Clients opened 1.3 million brokerage accounts, up 10% over last ..."
3. Quarterly NNA - Schwab: The 2Q26 10-Q (published 2026-08-07) reports core net new assets of $119.8 billion in the second quarter of 2026, up 49% from the same period in 2025, and $259.8 billion for the first half of 2026.
   - `SCHW-10Q-2026Q2#22` (10-Q, 2026-08-07): "Supported by equity market growth and strong asset gathering, total client assets increased to $13.08 trillion at June 30, up 10% from year-end 2025. Schwab attracted core net new assets of $119.8 billion in the second q..."
4. Quarterly NNA - Edward Jones: The 3Q25 10-Q (published 2025-11-07) shows net new assets for the period of $17 billion versus $16 billion a year earlier.
   - `EDJ-10Q-2025Q3#67` (10-Q, 2025-11-07): "51 $ 55 -7% $ 160 $ 173 -7% Advisory programs $ 20 $ 14 43% $ 55 $ 41 34% Client households at period end 6.7 6.5 3% 6.7 6.5 3% Net new households for the period(3) 24,000 53,000 -55% 101,000 177,000 -43% Net new assets ..."
5. Quarterly NNA - Edward Jones: The 1Q26 10-Q (published 2026-05-07) shows net new assets for the period of $18 billion versus $17 billion a year earlier.
   - `EDJ-10Q-2026Q1#51` (10-Q, 2026-05-07): "4,677 4,167 12% Operating expenses 4,136 3,654 13% Income before allocations $ 541 $ 513 5% Related metrics: Income before allocations margin(1) 11.5% 12.2% -6% Client assets under care ($ billions): Total: At period end..."
6. Quarterly NNA - Edward Jones: The 2Q26 10-Q (published 2026-08-07) shows net new assets for the period of $18 billion versus $17 billion a year earlier (six months: $36 billion versus $34 billion).
   - `EDJ-10Q-2026Q2#60` (10-Q, 2026-08-07): "2% Net new assets for the period ($ billions)(3) $ 18 $ 17 6% $ 36 $ 34 6% Financial advisors (actual): At period end 20,514 20,309 1% 20,514 20,309 1% Average 20,537 20,316 1% 20,517 20,265 1% (1) Income before allocati..."
7. Quarterly NNA - Raymond James (reports "domestic Private Client Group net new assets"): On the call for the quarter ended March 31, 2025 (published 2025-04-23), the CEO said quarterly domestic net new assets equaled $8.8 billion, a 2.6% annualized growth rate on beginning-of-period domestic PCG assets.
   - `RJF-TR-2025Q1#6` (transcript, 2025-04-23): "Paul Shoukry CEO at Raymond James In the Private Client Group, we ended the quarter with $1.54 trillion of client assets under administration, representing year-over-year growth of 6%. Over the past 12 months, we recruit..."
8. Quarterly NNA - Raymond James: The 2Q26 supplement (published 2026-07-22) lists domestic PCG net new assets in $ millions of 11,651 (quarter ended June 30, 2025), 17,930 (Sept 30, 2025), 30,828 (Dec 31, 2025), 22,954 (Mar 31, 2026) and 21,692 (June 30, 2026), with annualized growth of 3.4%, 5.0%, 8.0%, 5.8% and 5.5%.
   - *Flagged by code:* number_not_found
   - `RJF-SUPP-2026Q2#9` (supplement, 2026-07-22): "/ Client asset metrics ($ in billions) / As of - June 30, 2025 / As of - September 30, 2025 / As of - December 31, 2025 / As of - March 31, 2026 / As of - June 30, 2026 / % change from - June 30, 2025 / % change from - M..."
9. Quarterly NNA - Morgan Stanley (Wealth Management segment): The 3Q26 supplement (published 2026-10-14) shows net new assets of $232.4 billion for the quarter ended Sep 30, 2026, $148.1 billion for Jun 30, 2026 and $81.0 billion for Sep 30, 2025. The 2Q26 10-Q (published 2026-08-04) also gives $148 billion for that quarter, of which just over half was IPO-related inflows in the Workplace channel.
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."
   - `MS-10Q-2026Q2#58` (10-Q, 2026-08-04): "4. Annualized weighted average represents the total annualized weighted average cost of the various deposit products. Amounts include the effect of related hedging derivatives. The period end cost of deposits is based up..."
10. Quarterly NNA - Morgan Stanley: On the 3Q26 call (published 2026-10-14), the CFO said net new assets of $232 billion, with IPO-related flows contributing just over half of the total.
   - `MS-TR-2026Q3#15` (transcript, 2026-10-14): "Sharon Yeshaya Executive VP & CFO Net interest income was $2.2 billion, down modestly as deposits grew and the mix shifted. Looking ahead, we expect a modest increase in the fourth quarter, subject to rates and client be..."
11. Definition - Schwab: The chunks that report core net new assets do not state a formal definition. They show the firm presenting the figure both including and excluding a planned $17.5 billion mutual fund clearing client deconversion outflow (1Q26).
   - `SCHW-PR-2026-04-16-01#3` (press, 2026-04-16): "These actions reflect Schwab’s strong capital position as well as the sustained performance of the firm’s through-the-cycle financial model.” 1Q26 Common CFO Mike Verdeschi Stock Repurchases 1Q26 Client and Business High..."
12. Definition - Edward Jones: The 2Q26 10-Q (published 2026-08-07) states that net new assets represents cash and securities inflows and outflows, including fees and commissions and excluding mutual fund capital gain distributions received by U.S. clients.
   - `EDJ-10Q-2026Q2#60` (10-Q, 2026-08-07): "2% Net new assets for the period ($ billions)(3) $ 18 $ 17 6% $ 36 $ 34 6% Financial advisors (actual): At period end 20,514 20,309 1% 20,514 20,309 1% Average 20,537 20,316 1% 20,517 20,265 1% (1) Income before allocati..."
13. Definition - Raymond James: The metric is labelled domestic Private Client Group net new assets, with an annualized growth rate on beginning-of-period domestic PCG assets (per management on the quarter ended March 31, 2025 call). The retrieved chunks do not include a formal definition or footnote.
   - `RJF-TR-2025Q1#6` (transcript, 2025-04-23): "Paul Shoukry CEO at Raymond James In the Private Client Group, we ended the quarter with $1.54 trillion of client assets under administration, representing year-over-year growth of 6%. Over the past 12 months, we recruit..."
   - `RJF-SUPP-2026Q2#9` (supplement, 2026-07-22): "/ Client asset metrics ($ in billions) / As of - June 30, 2025 / As of - September 30, 2025 / As of - December 31, 2025 / As of - March 31, 2026 / As of - June 30, 2026 / % change from - June 30, 2025 / % change from - M..."
14. Definition - Morgan Stanley: The 2Q26 10-Q (published 2026-08-04) states that NNA represent client asset inflows, including interest, dividends and asset acquisitions, less client asset outflows, and excluding the impact of business combinations/divestitures and the impact of fees and commissions. The January 2026 strategic update deck gives the same definition.
   - `MS-10Q-2026Q2#58` (10-Q, 2026-08-04): "4. Annualized weighted average represents the total annualized weighted average cost of the various deposit products. Amounts include the effect of related hedging derivatives. The period end cost of deposits is based up..."
   - `MS-DECK-2026-strategic-update#30` (deck, 2026-01-15): "The attainment of these objectives assumes a normal market environment and may be impacted by external factors that cannot be predicted at this time, including geopolitical, macroeconomic and market conditions and future..."

**Adjacent evidence (a related but different quantity)**

1. Bank of America GWIM (published 2026-10-14): quarterly net client flows of about $38 billion in 3Q26, including approximately $20 billion of AUM flows. GWIM AUM-rollforward net client flows ($ millions): 3Q25 23,517; 4Q25 20,209; 1Q26 20,372; 2Q26 13,673; 3Q26 19,980.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's. AUM flows and net client flows are also not a net-new-assets metric defined by the firm.
   - `BAC-TR-2026Q3#19` (transcript, 2026-10-14): "Alastair Borthwick Client balances climbed above $5 trillion for the first time, up 9%, while AUM rose 12% to about $2.4 trillion. Quarterly net client flows were about $38 billion, including approximately $20 billion of..."
   - `BAC-SUPP-2026Q3#54` (supplement, 2026-10-14): "/ (Dollars in millions) / Nine Months Ended September 30 - 2026 / Nine Months Ended September 30 - 2025 / Third Quarter - 2026 / Second Quarter - 2026 / First Quarter - 2026 / Fourth Quarter - 2025 / Third Quarter - 2025..."
2. Schwab's February 2026 monthly report (published 2026-03-13): core net new assets of $32.5 billion for the month, or $50.0 billion excluding the $17.5 billion deconversion outflow.
   - *Differs because:* This is a monthly figure, not a quarterly one.
   - `SCHW-MONTHLY-2026-02#2` (monthly, 2026-03-13): "WESTLAKE, Texas, March 13, 2026 - The Charles Schwab Corporation released its Monthly Activity Report today. Company highlights for the month of February 2026 include: Core net new assets brought to the company in Februa..."
3. Edward Jones 2025 10-K (published 2026-03-13): annual net new assets of $71.8 billion (2025), $71.9 billion (2024) and $94.3 billion (2023) in the first column group.
   - *Differs because:* These are full-year figures, not quarterly.
   - `EDJ-10K-2025#148` (10-K, 2026-03-13): "12% $ 48.5 $ 43.3 $ 37.9 12% Total households (in thousands) 6,546 6,402 6,158 2% 196 193 192 2% Net new assets for the period ($ billions) $ 71.8 $ 71.9 $ 94.3 — $ 2.1 $ 2.0 $ 2.3 5% Financial advisors (actual): At year..."

**Gaps (named by the answer)**

- Merrill does not report standalone results. *Would fill it:* Bank of America quarterly earnings release and supplement (GWIM section); no Merrill-only NNA is published
- Merrill - definition of net new assets: not found in the evidence provided. *Would fill it:* Bank of America 10-K/10-Q GWIM key-indicator definitions and footnotes
- Schwab - formal definition of core net new assets: not found in the evidence provided. Schwab's 3Q26 core NNA is also not in the evidence. *Would fill it:* Schwab 10-K/10-Q MD&A glossary or footnotes; Schwab 3Q26 earnings release
- Raymond James - formal definition of net new assets (footnote 10 of the key-metrics table) is not in the retrieved text; the 3Q fiscal 2026 quarter is also absent. *Would fill it:* Raymond James 10-Q/10-K MD&A, Private Client Group net new assets discussion and supplement footnotes
- Edward Jones - 4Q25 and 3Q26 quarterly net new assets are not in the evidence; the quarters shown are 3Q25, 1Q26 and 2Q26 only. *Would fill it:* Edward Jones 10-K (Q4 derivable) and 3Q26 10-Q
- Morgan Stanley - 1Q26 and 4Q25 quarterly NNA are not in the evidence. *Would fill it:* Morgan Stanley 1Q26 earnings release / financial supplement and 4Q25 supplement

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q23: Advisor headcount over the last eight quarters across the five.

**Verdict: FAIL** (c, b). No Morgan Stanley, Schwab or Merrill advisor counts in the corpus, so the series cannot be complete; EDJ's other quarters (10-Qs) not used; gap_with_adjacent (expected answer).

Tier 1, use case `benchmark`. Expected behavior `answer`, got `gap_with_adjacent`. Retrieval: 30 passages, mode `entity`.

*Passes if:* The series is complete and each firm's definition travels with it (see question 11). Where a firm changed its definition mid-series, the break is flagged rather than smoothed.

**Adjacent evidence (a related but different quantity)**

1. Edward Jones 10-Q for the second quarter of 2026 (published 2026-08-07): financial advisors at period end were 20,514 versus 20,309 a year earlier (1%); the average was 20,537 versus 20,316 (1%).
   - *Differs because:* This gives only two quarter-end points (2Q26 and 2Q25). It is not an eight-quarter series. The 1Q26 chunk is cut off before the advisor figures.
   - `EDJ-10Q-2026Q2#60` (10-Q, 2026-08-07): "2% Net new assets for the period ($ billions)(3) $ 18 $ 17 6% $ 36 $ 34 6% Financial advisors (actual): At period end 20,514 20,309 1% 20,514 20,309 1% Average 20,537 20,316 1% 20,517 20,265 1% (1) Income before allocati..."
2. On the 3Q25 earnings call (published 2025-10-22), Raymond James CEO Paul Shoukry said the firm ended the fiscal year with a record number of financial advisors, 2% higher than the prior year.
   - *Differs because:* This is a management statement of a percentage change for one year-end. It gives no advisor count and no quarterly series.
   - `RJF-TR-2025Q3#8` (transcript, 2025-10-22): "Paul Shoukry CEO at Raymond James Quarterly domestic net new assets were nearly $18 billion this quarter, representing a 5% annualized growth rate. We ended the fiscal year with a record number of financial advisors, 2% ..."
3. Schwab's 10-Q for the second quarter of 2026 (published 2026-08-07) says higher compensation and benefits expenses reflected growth in headcount, including financial consultants and wealth advisors.
   - *Differs because:* This is a qualitative statement about total company headcount. It gives no financial consultant or wealth advisor count by quarter.
   - `SCHW-10Q-2026Q2#25` (10-Q, 2026-08-07): "Bank deposit account fee revenue was $333 million and $628 million in the second quarter and first six months of 2026, respectively, increasing 35% and 28% from the same periods in 2025, due primarily to higher net yield..."
4. On the 2Q26 earnings call (published 2026-07-14), Bank of America CFO Alastair Borthwick said that Merrill is aiming to keep growing the sales force and that adviser attrition is near historic lows.
   - *Differs because:* This is a qualitative remark about attrition and intent. It gives no advisor headcount. Net advisor headcount change is not attrition, and attrition is not headcount.
   - `BAC-TR-2026Q2#63` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO First, I think you were referring to the Merrill 5% guide, where we said we are aiming for 5% over the course of the next 3 to 5 years. It's been 7 months, and I think we're off t..."

**Gaps (named by the answer)**

- Morgan Stanley: advisor headcount for the last eight quarters not found in the evidence provided. *Would fill it:* Morgan Stanley quarterly earnings releases and financial supplements (Wealth Management financial advisor counts), plus 10-Q and 10-K filings
- Raymond James: quarter-by-quarter financial advisor counts not found in the evidence provided. Only a 2% year-over-year increase at fiscal year-end 2025 is stated. *Would fill it:* Raymond James quarterly earnings releases and financial supplements (Private Client Group advisor counts)
- Edward Jones: only the 2Q26 and 2Q25 period-end advisor counts are in the evidence. The other quarters are not found in the evidence provided. *Would fill it:* Edward Jones 10-Q and 10-K MD&A tables (financial advisors at period end) for each of the last eight quarters
- Schwab: financial consultant and wealth advisor counts by quarter not found in the evidence provided. *Would fill it:* Schwab quarterly earnings decks, 10-Q and 10-K filings, and Monthly Activity Reports
- Merrill does not report standalone results. Merrill advisor counts for eight quarters are not found in the evidence provided. *Would fill it:* Bank of America quarterly earnings supplements and investor day materials (Merrill Wealth Management advisor counts)

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q24: Client assets per advisor across the five -- and is that comparison even valid?

**Verdict: PASS**. Declines the ratio and names why (asset scopes, self-directed and RIA custody, GWIM, different dates); EDJ and RJF inputs shown.

Tier 3, use case `benchmark`. Expected behavior `gap_with_adjacent`, got `gap_with_adjacent`. Retrieval: 30 passages, mode `entity`.

*Passes if:* It computes the figure only where both inputs are disclosed on a consistent basis, and answers the second half directly -- naming where the comparison is invalid and why.

**Claims**

1. Edward Jones's 10-Q for the second quarter of 2026 (published 2026-08-07) states the Partnership ended the quarter with $2.6 trillion of assets under care (AUC), including $1.2 trillion of advisory programs AUC, and with 20,514 financial advisors. Both inputs are disclosed, but the filing does not state a per-advisor figure.
   - `EDJ-10Q-2026Q2#61` (10-Q, 2026-08-07): "The Partnership ended the second quarter of 2026 with $2.6 trillion of assets under care ("AUC"), including $1.2 trillion of advisory programs AUC. Average client AUC increased 17%, reflecting increases in the market val..."
2. Raymond James's FY2025 10-K (published 2025-11-25) states that total client assets under administration (AUA) in its Private Client Group segment were $1.67 trillion as of September 30, 2025, of which $1.01 trillion was fee-based AUA, with 8,943 employee and independent contractor financial advisors. The figures cover the PCG segment only, and the filing does not state a per-advisor figure.
   - `RJF-10K-2025#9` (10-K, 2025-11-25): "Among the keys to our historical and continued success, our emphasis on putting the client first is at the core of our corporate values. We also believe in maintaining a long-term focus on our decision making. We believe..."
3. The comparison is not like-for-like because each firm uses its own asset measure. Edward Jones reports "assets under care" (Q2 2026 10-Q). Raymond James reports PCG "assets under administration" (FY2025 10-K).
   - `EDJ-10Q-2026Q2#61` (10-Q, 2026-08-07): "The Partnership ended the second quarter of 2026 with $2.6 trillion of assets under care ("AUC"), including $1.2 trillion of advisory programs AUC. Average client AUC increased 17%, reflecting increases in the market val..."
   - `RJF-10K-2025#9` (10-K, 2025-11-25): "Among the keys to our historical and continued success, our emphasis on putting the client first is at the core of our corporate values. We also believe in maintaining a long-term focus on our decision making. We believe..."
4. Morgan Stanley's January 2026 deck defines Total Client Assets as Wealth Management client assets plus Investment Management AUM. Its Wealth Management client assets include advisor-led brokerage, self-directed brokerage, workplace and stock plan services, and retirement plan services. It notes that some WM assets are also counted in IM's AuM. Schwab's reported total client assets, by contrast, come from a model it describes as leading in self-directed investors and RIAs. A total-assets-to-advisors ratio would therefore mix advised and non-advised assets, and the firms differ in how much of each they hold.
   - `MS-DECK-2026-strategic-update#28` (deck, 2026-01-15): "These notes refer to the financial metrics and/or defined terms presented on Slide 4 Earnings per Share ('EPS') represents diluted earnings per share. Return on average tangible common equity ('ROTCE') represents net inc..."
   - `SCHW-TR-2025Q1#9` (transcript, 2025-04-17): "Rick Wurster President and CEO at Charles Schwab In the first quarter, total revenue increased 18% year-over-year to $5.6 billion, and adjusted earnings per share increased 41% over the first quarter of 2024. We are off ..."
5. The measurement dates differ across the evidence. Edward Jones is as of June 2026 (10-Q published 2026-08-07). Raymond James is as of September 30, 2025 (10-K). Morgan Stanley's Wealth Management figures are as of September 30, 2026 (supplement published 2026-10-14). Schwab's are as of August 31, 2026 (monthly report published 2026-09-15). Bank of America GWIM's are as of September 30, 2026. Asset levels moved materially between these dates, so ratios built from them would not be same-date.
   - `EDJ-10Q-2026Q2#61` (10-Q, 2026-08-07): "The Partnership ended the second quarter of 2026 with $2.6 trillion of assets under care ("AUC"), including $1.2 trillion of advisory programs AUC. Average client AUC increased 17%, reflecting increases in the market val..."
   - `RJF-10K-2025#9` (10-K, 2025-11-25): "Among the keys to our historical and continued success, our emphasis on putting the client first is at the core of our corporate values. We also believe in maintaining a long-term focus on our decision making. We believe..."
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."
   - `SCHW-MONTHLY-2026-08#4` (monthly, 2026-09-15): "/ Number of Trading Days / 2025 Aug 21.0 / Sep 21.0 / Oct 23.0 / Nov 18.5 / Dec 21.5 / 2026 Jan 20.0 / Feb 19.0 / Mar 22.0 / Apr 21.0 / May 20.0 / Jun 21.0 / Jul 22.0 / Aug 21.0 / Mo. Change / Yr. / /---/---/---/---/---/..."
   - `BAC-SUPP-2026Q3#54` (supplement, 2026-10-14): "/ (Dollars in millions) / Nine Months Ended September 30 - 2026 / Nine Months Ended September 30 - 2025 / Third Quarter - 2026 / Second Quarter - 2026 / First Quarter - 2026 / Fourth Quarter - 2025 / Third Quarter - 2025..."

**Adjacent evidence (a related but different quantity)**

1. Morgan Stanley's Wealth Management segment reported total client assets of $8,433 billion at September 30, 2026 (supplement published 2026-10-14), of which advisor-led client assets were $6,631 billion and self-directed client assets were $1,802 billion. The same table reports no advisor headcount.
   - *Differs because:* These are asset totals with no advisor count, so they cannot give assets per advisor. The advisor-led subset is the closer numerator, but it has no matching advisor denominator in the evidence.
   - `MS-SUPP-2026Q3#16` (supplement, 2026-10-14): "(unaudited, dollars in billions) / / Quarter Ended - Sep 30, 2026 / Quarter Ended - Jun 30, 2026 / Quarter Ended - Sep 30, 2025 / Percentage Change From: - Jun 30, 2026 / Percentage Change From: - Sep 30, 2025 / /---/---..."
2. Schwab reported total client assets of $13,410.0 billion at August 31, 2026 (monthly report published 2026-09-15). Of that, $5,903.0 billion in Advisor Services was receiving ongoing advisory services. The evidence gives no advisor count.
   - *Differs because:* This is firm-wide client assets that include self-directed and RIA-custodial assets. Schwab's own description, 'number one in RIA custodial assets', shows its advisor-related assets sit with independent RIAs rather than a captive advisor force, so the figure is not comparable to an employee or affiliated advisor base.
   - `SCHW-MONTHLY-2026-08#4` (monthly, 2026-09-15): "/ Number of Trading Days / 2025 Aug 21.0 / Sep 21.0 / Oct 23.0 / Nov 18.5 / Dec 21.5 / 2026 Jan 20.0 / Feb 19.0 / Mar 22.0 / Apr 21.0 / May 20.0 / Jun 21.0 / Jul 22.0 / Aug 21.0 / Mo. Change / Yr. / /---/---/---/---/---/..."
3. Bank of America's GWIM segment reported total client balances of $5,056,787 million (about $5.06 trillion) at September 30, 2026 (supplement published 2026-10-14). Management described client balances as above $5 trillion, and said Merrill added about 4,200 net new households with at least $500,000 in assets.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-SUPP-2026Q3#54` (supplement, 2026-10-14): "/ (Dollars in millions) / Nine Months Ended September 30 - 2026 / Nine Months Ended September 30 - 2025 / Third Quarter - 2026 / Second Quarter - 2026 / First Quarter - 2026 / Fourth Quarter - 2025 / Third Quarter - 2025..."
   - `BAC-TR-2026Q3#19` (transcript, 2026-10-14): "Alastair Borthwick Client balances climbed above $5 trillion for the first time, up 9%, while AUM rose 12% to about $2.4 trillion. Quarterly net client flows were about $38 billion, including approximately $20 billion of..."

**Gaps (named by the answer)**

- Client assets per advisor is not disclosed by any of the five firms, and the evidence has no consistently defined advisor count for Morgan Stanley, Schwab or Merrill. *Would fill it:* Each firm's 10-K or 10-Q advisor-count disclosures and recruiting-page statistics, paired with same-date advisor-led client assets.
- Morgan Stanley - advisor headcount: not found in the evidence provided. *Would fill it:* Morgan Stanley 10-K or quarterly supplement, Wealth Management financial advisor count.
- Schwab - advisor headcount comparable to the others: not found in the evidence provided. Schwab's model is self-directed plus RIA custody. *Would fill it:* Schwab 10-K business description and Schwab Advisor Services disclosures.
- Merrill does not report standalone results. No Merrill-only client assets or advisor count appears in the evidence. *Would fill it:* Bank of America 10-K or supplement disclosures of Merrill advisor counts and client balances.
- Edward Jones and Raymond James: their figures are on different bases and dates (June 2026 firm-wide AUC vs September 2025 PCG AUA), so no same-date, same-scope ratio can be built from the evidence. *Would fill it:* Same-date Edward Jones and Raymond James 10-Q filings, with Raymond James's PCG AUA and advisor count for the same quarter.

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q25: What has each of the five actually disclosed about advisor compensation structures?

**Verdict: FAIL** (r). Behavior fixed (gap_with_adjacent), but Morgan Stanley's disclosed formulaic payout (10-K) is marked 'not found' and Raymond James's other published payout ranges are missing.

Tier 1, use case `benchmark`. Expected behavior `gap_with_adjacent`, got `gap_with_adjacent`. Retrieval: 30 passages, mode `entity`.

*Passes if:* It reports what is genuinely disclosed -- which is far less than people assume -- and marks the rest as undisclosed rather than reaching for trade-press reconstructions of payout grids.

**Claims**

1. Published advisor payout percentages - Raymond James: Raymond James's recruiting page (page content as of 2026-04-21) lists a Corporate RIA model (minimum 3 years of experience and $50 million in assets under advisement) with an '81% to 90% payout'. For the Bank & Credit Union model it describes only 'a competitive compensation package from the financial institution in partnership with Raymond James', and for RIA & Custody Services it says to 'work with your RIA or broker/dealer to determine compensation'.
   - `RJF-PR-web-affiliation-options#2` (press, 2026-04-21): "Model: Bank & Credit Union Qualifications*: Minimum 3 years of experience and $250,000 in production. Payout + Benefits: Get the support you need during your transition by receiving a competitive compensation package fro..."
2. Published advisor payout percentages - Raymond James (referral fees): Raymond James's ADV brochure (published 2026-09-14) says its Institutional Account Participation Program pays financial advisors a referral fee 'as a percentage of the management fee earned' by Raymond James Investment Management and/or its subsidiary advisers. No percentage is stated in the chunk.
   - `RJF-ADV-2026#114` (adv, 2026-09-14): "From time to time, our Firm and our financial advisors may enter into other types of referral arrangements, including arrangements with our affiliates or among financial advisors within a singular division or entity. The..."
3. Reported advisor compensation expense - Edward Jones: The Partnership's 10-Q for the quarter ended March 27, 2026 (published 2026-05-07) reports 'Financial advisor' compensation and benefits of $1,875 million, against $1,653 million in the prior-year quarter, a 13% change. It reports variable compensation separately at $748 million, against $611 million, a 22% change.
   - `EDJ-10Q-2026Q1#60` (10-Q, 2026-05-07): "Three Months Ended March 27, 2026 March 28, 2025 % Change ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── Operating expenses: Compensat..."
4. Reported advisor compensation expense - Raymond James: On the fiscal 3Q25 call (published 2025-10-22), the CFO said fiscal 2025 adjusted compensation expense included amortization of transition assistance for recruited advisors and other retention awards to existing advisors totalling $355 million, an increase of approximately 11% from fiscal 2024.
   - `RJF-TR-2025Q3#20` (transcript, 2025-10-22): "Butch Oorlog CFO at Raymond James Keep in mind, there are many variables which could influence actual results, including any interest rate actions during the upcoming quarter and factors affecting our balance sheet, incl..."

**Adjacent evidence (a related but different quantity)**

1. Edward Jones' 2025 10-K (published 2026-03-13), Item 11, discusses the Managing Partner-to-median-employee pay ratio, using salary and benefits, variable compensation and allocations of Partnership net income.
   - *Differs because:* It describes pay for the Managing Partner and a median employee, not the compensation structure for financial advisors.
   - `EDJ-10K-2025#314` (10-K, 2026-03-13): "The Wall Street Reform and Consumer Protection Act and related regulations require the Partnership to disclose the ratio of the compensation of the Managing Partner and compensation of a median employee of the Partnershi..."
2. Edward Jones' 10-Q for the quarter ended March 27, 2026 reports total compensation and benefits of $3,279 million, against $2,890 million in the prior-year quarter.
   - *Differs because:* Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid.
   - `EDJ-10Q-2026Q1#60` (10-Q, 2026-05-07): "Three Months Ended March 27, 2026 March 28, 2025 % Change ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── Operating expenses: Compensat..."
3. On the fiscal 3Q25 call (published 2025-10-22), Raymond James reported a total compensation ratio of 64.2% and an adjusted ratio of 64.0%, against a 65% target.
   - *Differs because:* Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid.
   - `RJF-TR-2025Q3#20` (transcript, 2025-10-22): "Butch Oorlog CFO at Raymond James Keep in mind, there are many variables which could influence actual results, including any interest rate actions during the upcoming quarter and factors affecting our balance sheet, incl..."
4. Merrill's ADV brochure (published 2026-10-30) describes compensation Merrill receives from third parties: closed-end fund structuring fees of 0.50% to 2.00% of new issue proceeds, and brokered CD placement fees of 0.02% to 0.30% annualized.
   - *Differs because:* This is compensation received by the firm from product providers, not what advisors are paid.
   - `MER-ADV-2026#449` (adv, 2026-10-30): "For new issue closed-end fund offerings, in addition to underwriting compensation, the closed-end fund investment manager can pay Merrill a structuring fee that ranges from 0.50% to 2.00% of the new issue proceeds for ad..."
5. Morgan Stanley's ADV brochure (published 2026-11-04) describes conflicts of interest from MSWM or affiliates being paid for hedging services on structured notes.
   - *Differs because:* This is firm and affiliate compensation and conflicts, not advisor compensation structure.
   - `MS-ADV-2026#198` (adv, 2026-11-04): "MSWM and/or its affiliates have a variety of relationships with, and provide a variety of services to, issuers of securities recommended for client accounts, including investment banking, corporate advisory and services,..."
6. Schwab's ADV brochure (published 2026-10-15) says CS&Co. receives payments from third-party ETF providers of up to $4 million annually per provider, and does not receive these payments from Schwab-sponsored ETFs.
   - *Differs because:* This is platform compensation received by the firm, not advisor pay.
   - `SCHW-ADV-2026#45` (adv, 2026-10-15): "CS&Co. receives compensation from sponsors or issuers of third-party ETFs ("ETF providers"), for recordkeeping, shareholder, administrative services, and/or other platform services. ETFs, as defined by this compensation ..."
7. Edward Jones' ADV brochure (published 2026-03-27) says the firm and its financial advisors 'receive compensation for services and recommendations that may differ from advice given to you' in Advisory Solutions Fund Models. It says Edward Jones receives no revenue sharing on those assets.
   - *Differs because:* It is a general conflict disclosure and gives no structure, rates or payout figures for advisors.
   - `EDJ-ADV-2026#122` (adv, 2026-03-27): "For more information regarding revenue sharing, please visit www.edwardjones.com/disclosures or request a revenue sharing disclosure document from your Edward Jones financial advisor. Edward Jones does not receive revenu..."

**Gaps (named by the answer)**

- Published advisor payout percentages - Edward Jones: not found in the evidence provided. *Would fill it:* Edward Jones financial advisor recruiting materials or the Item 11 compensation discussion in the 10-K
- Published advisor payout percentages - Merrill: not found in the evidence provided. Payout grids are not public. *Would fill it:* Merrill or Bank of America recruiting materials; Form ADV Part 2A section on advisor compensation
- Published advisor payout percentages - Morgan Stanley: not found in the evidence provided. Payout grids are not public. *Would fill it:* Morgan Stanley Wealth Management Form ADV Part 2A compensation section; recruiting materials
- Raymond James: Headline payout ranges are published (company recruiting page, as of 2026-04-21); the full payout grid is not public. *Would fill it:* Raymond James divisional recruiting disclosures or advisor offer terms
- Published advisor payout percentages - Schwab: not found in the evidence provided. The evidence describes Schwab's custodial and platform relationships, not payout to advisors it employs. *Would fill it:* Schwab Form ADV Part 2A on how its own representatives are paid
- Reported advisor compensation expense - Merrill: Merrill does not report standalone results. *Would fill it:* Bank of America GWIM segment disclosures, noting they include the Private Bank
- Reported advisor compensation expense - Morgan Stanley: not found in the evidence provided. *Would fill it:* Morgan Stanley 10-K or 10-Q compensation and benefits notes, and Wealth Management segment disclosures
- Reported advisor compensation expense - Schwab: not found in the evidence provided. The 10-K says compensation and benefits are allocated to segments by an activity-based costing model, but gives no advisor compensation figure. *Would fill it:* Schwab 10-K segment note or Schwab Form ADV on its own advisor pay
- Reported advisor compensation expense - Raymond James, Private Client Group financial advisor compensation line: the supplement table is cut off at the 'Financial advisor compensation' header, so no figure is available. *Would fill it:* Raymond James quarterly financial supplement, Private Client Group segment results

### Q26: What's new on Raymond James in the last 90 days?

**Verdict: PASS**. Items inside the 90-day window, newest first, trade press labelled indicative, departures and products marked. Borderline: 'why it matters' implicit for most items.

Tier 1, use case `recency`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* Items newest first, each with one line on why it might matter and a link that resolves. Nothing older than the window sneaks in.

**Claims**

1. Newest first. All items below come from trade press (indicative, not authoritative), not from Raymond James filings. On 2026-11-06, trade press reported that a team of Killfoil, Koch and Morin, with PNC backgrounds, joined Raymond James & Associates (RJA) as managing directors. It also reported that RJA had announced a $700 million advisor team joined earlier that week, the second in as many weeks to join the firm managing that amount.
   - `RJF-TRADE-2026-11-06-IN-01#1` (trade, 2026-11-06): ""Raymond James provides the resources, technology and breadth of capabilities that position our team to address the unique needs of the individuals and families we serve," said Killfoil, managing director of wealth manag..."
2. On 2026-11-05, InvestmentNews reported that Samuel Mintz and Stephen Gow moved from Truist Investment Services to RJA in Richmond, Virginia, adding more than $1.2 billion in client assets to the employee advisor channel. The article says Raymond James ended its fiscal year with a record 8,943 advisors, a 2% increase year-over-year, and that the firm has signaled healthy pipelines of advisor commitments.
   - `RJF-TRADE-2026-11-05-IN-01#0` (trade, 2026-11-05): "Richmond duo with $1.2B in assets joins Raymond James from Truist InvestmentNews trade press - 2026-11-05 (tier 4, indicative only) Source: https://www.investmentnews.com/independent-broker-dealers/richmond-duo-with-12b-..."
3. On 2026-11-04, trade press described an Ohio team hire as extending a consistent run of RJA recruiting from UBS throughout 2026.
   - `RJF-TRADE-2026-11-04-IN-01#2` (trade, 2026-11-04): "Culture and leadership stability were the deciding factors in the team's decision to move. "Raymond James stands out for its reputation and longstanding stability," Massey said. "Its strong leadership team and client-fir..."
4. On 2026-10-29, WealthManagement.com reported the firm's quarterly results. It said Raymond James had record quarter-end client assets under administration of $1.87 trillion, up 1% sequentially and 12% year-over-year. Private Client Group net revenue was a record $3.06 billion, up 15% year-over-year, with pre-tax income of $458 million, up 10%. Domestic PCG net new assets rose 88% for the fiscal year to a record of more than $98 billion. Non-GAAP EPS was $3.59 on revenue of $4.74 billion, up 13%.
   - `RJF-TRADE-2026-10-29-WM-01#1` (trade, 2026-10-29): "Raymond James no longer reports advisor headcount, but it had about 8,900 advisors the last time headcount was officially broken out. Overall, the firm reported record quarter-end client assets under administration of $1..."
5. The same 2026-10-29 article says Raymond James no longer reports advisor headcount, and that it had about 8,900 advisors the last time headcount was officially broken out. On M&A, CEO Shoukry said the firm looks for wealth management acquisitions that are a good cultural and strategic fit. In his words: "We don't do acquisitions to slash costs."
   - `RJF-TRADE-2026-10-29-WM-01#1` (trade, 2026-10-29): "Raymond James no longer reports advisor headcount, but it had about 8,900 advisors the last time headcount was officially broken out. Overall, the firm reported record quarter-end client assets under administration of $1..."
6. Departures: on 2026-10-16, WealthManagement.com reported that Janney Montgomery Scott is opening a Houston office seeded by the Edward Fitzpatrick Group. The team had been with Raymond James for about 23 years and had amassed $3.3 billion in client assets under management, per BrokerCheck and the announcement. Advisor Lance Murphy, who oversaw more than $200 million at Raymond James, is also leaving to join the team.
   - `RJF-TRADE-2026-10-16-WM-01#0` (trade, 2026-10-16): "Janney Adds $3.5B Houston-Based Team From Raymond James WealthManagement.com trade press - 2026-10-16 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ibd-news/janney-launches-3-5b-houston-based-team-ma..."
7. Departures: on 2026-10-08, WealthManagement.com reported that four practices that had operated as a unified Raymond James branch since 2022 joined Ascentis Independent Advisors, an independent RIA platform, bringing more than $1 billion in client assets. They moved from Raymond James Financial Services and will continue to use Raymond James as their primary custodian.
   - `RJF-TRADE-2026-10-08-WM-01#0` (trade, 2026-10-08): "Four Practices Bring $1B to Ascentis Independent From Raymond James WealthManagement.com trade press - 2026-10-08 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ria-news/four-practices-bring-1b-to-asc..."
8. On 2026-09-29, trade press reported that Raymond James launched Private Wealth Guided Portfolios. These are risk-based model portfolios combining equity and fixed income with a dedicated alternatives sleeve covering private markets and hedged strategies, aimed at advisors serving high-net-worth and ultra-high-net-worth clients. Private Client Group President Tash Elwyn said the firm is "committed to being a destination for private wealth advisors and the clients they serve." The firm's asset management services group oversees portfolio construction for the models.
   - `RJF-TRADE-2026-09-29-IN-01#0` (trade, 2026-09-29): "Raymond James launches guided portfolios for high-net-worth advisor market InvestmentNews trade press - 2026-09-29 (tier 4, indicative only) Source: https://www.investmentnews.com/independent-broker-dealers/raymond-james..."
   - `RJF-TRADE-2026-09-29-WM-01#0` (trade, 2026-09-29): "Raymond James Launches Public/Private Model Portfolios for HNW Clients WealthManagement.com trade press - 2026-09-29 (tier 4, indicative only) Source: https://www.wealthmanagement.com/alternative-investments/raymond-jame..."
   - `RJF-TRADE-2026-09-29-WM-01#1` (trade, 2026-09-29): "The launch adds to a list of investment products aimed at advisors that blend public and private assets. Wellington Management, Vanguard and Blackstone partnered to launch the WVB All Markets Fund and the WVB Blackstone ..."
9. Also on 2026-09-29, the trade press reported that nearly 450 advisors have earned the Raymond James Private Wealth Advisor designation since it launched in 2022, per the firm. It said CEO Shoukry has emphasized building the advisory ranks through individualized recruitment rather than large-scale acquisitions. It also said the firm launched proprietary active ETFs in October 2025 and is piloting an AI-powered advisor assistant called Raimond.
   - `RJF-TRADE-2026-09-29-WM-01#1` (trade, 2026-09-29): "The launch adds to a list of investment products aimed at advisors that blend public and private assets. Wellington Management, Vanguard and Blackstone partnered to launch the WVB All Markets Fund and the WVB Blackstone ..."
   - `RJF-TRADE-2026-09-29-IN-01#4` (trade, 2026-09-29): "Executives have been telegraphing the expanded push all year. At the firm's annual conference in Las Vegas in May 2026, both Chief Executive Officer Paul Shoukry and Elwyn said the advisor, not the home office, is the cl..."
10. On 2026-09-24, InvestmentNews reported that Raymond James Financial Services welcomed a five-advisor team, Harris Wealth Partners of Rochester, New York, from Commonwealth Financial Network, adding approximately $500 million in client assets to its independent advisor channel.
   - `RJF-TRADE-2026-09-24-IN-01#0` (trade, 2026-09-24): "Advisor moves: Raymond James, Baird add significant teams in latest recruiting push InvestmentNews trade press - 2026-09-24 (tier 4, indicative only) Source: https://www.investmentnews.com/independent-broker-dealers/advi..."
11. On 2026-09-16, WealthManagement.com reported, citing an SEC filing and a spokesperson, that Raymond James launched a firm-wide SIMPLE IRA Employer Advisory and Consulting Services Program, partnered with Capital Group American Funds, for small businesses with up to 100 employees. It was made available to its roughly 8,900 advisors.
   - `RJF-TRADE-2026-09-16-WM-01#0` (trade, 2026-09-16): "Raymond James Adds Retirement Plan Option for Small Business Owners WealthManagement.com trade press - 2026-09-16 (tier 4, indicative only) Source: https://www.wealthmanagement.com/ibd-news/raymond-james-adds-retirement-..."
12. On 2026-08-26, trade press reported a recruit to Raymond James Financial Services, an advisor with more than 31 years of experience, and said the firm has been particularly active attracting practices with affluent and business-owner clientele.
   - `RJF-TRADE-2026-08-26-IN-01#2` (trade, 2026-08-26): "Stillwell brings more than 31 years of financial services experience to his new affiliation. A Michigan State University graduate, he holds the Raymond James Private Wealth Advisor and Chartered Life Underwriter professi..."

**Gaps (named by the answer)**

- No primary Raymond James sources (earnings release, 10-K/10-Q, 8-K or press releases) are in the evidence. Every item above comes from trade press, so figures and characterizations are indicative only. *Would fill it:* Raymond James earnings release and call transcript, SEC filings, and the firm's newsroom

### Q27 (trap): What has changed at Merrill since the start of the year?

**Verdict: PASS**. Trap held: Merrill items only; GWIM figures only as labelled adjacents.

Tier 1, use case `recency`. Expected behavior `answer`, got `answer`. Retrieval: 20 passages, mode `entity`.

*Passes if:* Merrill items only. Bank of America material appears solely where the disclosure is explicitly about GWIM or Merrill, and is labelled as such.

**Claims**

1. A trade report published 2026-11-16 says Franklin J. Laden, who managed $375 million, joined Merrill in Denver from UBS. It also says Merrill that month added an advisor managing $205 million at Morgan Stanley in California and another overseeing $150 million at Edward D. Jones & Co. in Texas, according to a Merrill spokesperson.
   - `MER-TRADE-2026-11-16-AH-01#1` (trade, 2026-11-16): "The move came the same day as another UBS broker, Franklin J. Laden, joined Merrill in Denver. He managed $375 million in assets and joined an existing team, the LDSO Group, at Merrill, according to the spokesperson. Lad..."
2. The same 2026-11-16 trade report says Merrill executives in October touted that recruited assets to the wealth unit doubled year-over-year as the firm returned to veteran broker recruiting. The report says the firm largely pulled back from veteran recruiting at the end of 2017, and that Co-Presidents Lindsay Hans and Eric Schimpf, who took over in 2023, restored a focus on hiring and a more aggressive offer.
   - `MER-TRADE-2026-11-16-AH-01#1` (trade, 2026-11-16): "The move came the same day as another UBS broker, Franklin J. Laden, joined Merrill in Denver. He managed $375 million in assets and joined an existing team, the LDSO Group, at Merrill, according to the spokesperson. Lad..."
3. On the 3Q26 media call (reported 2026-10-14), Eric Schimpf, president and co-head of Merrill Wealth Management, said client sales of alternative investments at Merrill Lynch increased 19% in the quarter. The trade report adds that he did not mention new AI tools, but that the message was clear the firm would continue to invest in AI and digital capabilities.
   - `MER-TRADE-2026-10-14-IN-01#2` (trade, 2026-10-14): "At Merrill Lynch, client sales of alternative investments increased 19% in the quarter, said Eric Schimpf, president and co-head of Merrill Wealth Management, this morning during a conference call with reporters. While t..."
4. Bank of America's 3Q26 earnings press release (2026-10-14) lists these Merrill Wealth Management highlights: $4.2 trillion in client balances, $1.9 trillion in AUM balances, ~4.2K net new $500K+ households added in 3Q26, and 70K digital appointments scheduled in the quarter. It also reports 87% of Merrill households digitally active, 67% active on mobile, and 81% of eligible brokerage and bank accounts opened through digital onboarding.
   - `BAC-PR-2026-10-14-01#12` (press, 2026-10-14): "The increase was driven by higher asset management fees, up 16% to $4.5 billion, reflecting higher market valuations, strong AUM flows and higher NII • Noninterest expense of $5.0 billion increased 9%, driven primarily b..."
5. On the 3Q26 call (2026-10-14), CFO Alastair Borthwick said Merrill added about 4,200 net new households with at least $500,000 in assets, up 17%, and that 67% of Merrill clients have banking relationships with the firm. He attributed the results to strong demand for advice and the ability to attract clients and experienced advisers to the platform.
   - `BAC-TR-2026Q3#19` (transcript, 2026-10-14): "Alastair Borthwick Client balances climbed above $5 trillion for the first time, up 9%, while AUM rose 12% to about $2.4 trillion. Quarterly net client flows were about $38 billion, including approximately $20 billion of..."
6. On 2026-09-15 Merrill announced two new services, the Tax Efficient Transition Service (TET) and the Dollar Cost Averaging Service (DCA). Both are available through the Merrill Lynch Investment Advisory Program and are implemented by Managed Account Advisors LLC. Merrill describes them as combining automation with professional portfolio oversight to help clients simplify asset transitions and cash deployment.
   - `MER-PR-2026-09-15-01#0` (press, 2026-09-15): "Merrill Launches New Services to Support Portfolio Transitions and Systematic Cash Investing Merrill press release - 2026-09-15 Source: Bank of America Newsroom, Global Wealth and Investment Management category. Key poin..."
7. Bank of America's 2Q26 press release (2026-07-14) lists these Merrill Wealth Management highlights: $4.1 trillion in client balances, $1.8 trillion in AUM balances, ~5.4K net new $500K+ households added in 2Q26, 62K digital appointments scheduled, and 87% of Merrill households digitally active.
   - `BAC-PR-2026-07-14-01#11` (press, 2026-07-14): "The increase was driven by higher asset management fees, up 19% to $4.4 billion, reflecting higher market valuations and solid AUM flows, as well as higher NII • Noninterest expense of $5.0 billion increased 8%, driven p..."

**Adjacent evidence (a related but different quantity)**

1. GWIM segment results (Merrill plus Private Bank): the 3Q26 supplement (2026-10-14) shows net income of $1,540 million in 3Q26 against $1,329 million in 1Q26. Nine-month 2026 net income was $4,282 million against $3,265 million a year earlier. The 3Q26 efficiency ratio was 70.91, against 73.58 in 1Q26.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-SUPP-2026Q3#51` (supplement, 2026-10-14): "/ / / / / / / / / /---/---/---/---/---/---/---/---/ / (Dollars in millions) / Nine Months September / Ended 30 / Third Quarter / Second Quarter / First Quarter / Fourth Quarter / Third Quarter / / / 2026 / 2025 / 2026 / ..."
2. GWIM, 2025 10-K (published 2026-02-25), the year-start baseline: net income rose $407 million to $4.7 billion, and client balances were $4.8 trillion at December 31, 2025. In 3Q26 GWIM client balances were $5.1 trillion, up 9%, and the 3Q26 release says average loans and leases of $279 billion increased 13%.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-10K-2025#246` (10-K, 2026-02-25): "Merrill Wealth Management’s advisory business provides a high-touch client experience through a network of financial advisors focused on clients with over $250,000 in total investable assets. Merrill Wealth Management pr..."
   - `BAC-10K-2025#249` (10-K, 2026-02-25): "ement, beginning of year $ 1,882,211 $ 1,617,740 Net client flows 81,997 79,227 Market valuation/other 213,500 185,244 Total assets under management, end of year $ 2,177,708 $ 1,882,211 (1) Includes margin receivables, w..."
   - `BAC-PR-2026-10-14-01#12` (press, 2026-10-14): "The increase was driven by higher asset management fees, up 16% to $4.5 billion, reflecting higher market valuations, strong AUM flows and higher NII • Noninterest expense of $5.0 billion increased 9%, driven primarily b..."
3. GWIM, 1Q26 (published 2026-04-15): the CFO said the firm continues to attract talent across both new and experienced advisers. The deck shows ~4K net new $500K+ relationships across Merrill and Private Bank in 1Q26 and 88% of GWIM households/relationships digitally active.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-TR-2026Q1#26` (transcript, 2026-04-15): "Alastair Borthwick Chief Financial Officer Pretax margin was 26%, reflecting the operating leverage achieved through disciplined expense management. Client balances increased to $4.6 trillion, up 10% year-over-year suppo..."
   - `BAC-DECK-2026Q1#27` (deck, 2026-04-15): "AUM flows of $20B in 1Q26; $78B since 1Q25 66% of clients have deposit or lending relationship Average deposits of $287B increased modestly from 1Q25 Average loans and leases of $262B increased $30B, or 13%, from 1Q25 Ad..."
4. A trade report (2026-11-16) says UBS's Americas advisor headcount was down almost 1% year-over-year to 5,601, and that a $3.6 billion-asset team left to start an RIA and a $480 million team joined LPL Financial.
   - *Differs because:* These items describe UBS and other firms' advisor movements, not Merrill's own changes.
   - `MER-TRADE-2026-11-16-AH-01#1` (trade, 2026-11-16): "The move came the same day as another UBS broker, Franklin J. Laden, joined Merrill in Denver. He managed $375 million in assets and joined an existing team, the LDSO Group, at Merrill, according to the spokesperson. Lad..."

**Gaps (named by the answer)**

- Merrill does not report standalone results. *Would fill it:* Bank of America quarterly earnings supplement and 10-Q/10-K (GWIM segment), which report only the combined GWIM segment.
- Merrill-specific start-of-year baselines (for example, client balances or household counts as of December 2025 or 1Q26) were not found, so a precise year-to-date change in the Merrill Wealth Management metrics cannot be computed from this evidence. *Would fill it:* Bank of America 4Q25 earnings press release and 1Q26 press release (Merrill Wealth Management highlights).

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q28: What is Edward Jones's advisor attrition rate compared to Merrill's?

**Verdict: FAIL** (s). EDJ rate with period and definition, Merrill qualitative only, 'not comparable' said; but the adjacent net headcount change and its difference from attrition are missing (R1 had them). Borderline.

Tier 1, use case `honest_miss`. Expected behavior `gap_with_adjacent`, got `gap_with_adjacent`. Retrieval: 20 passages, mode `entity+theme`.

*Passes if:* Edward Jones discloses an advisor attrition rate; Merrill does not, so there is no comparable pair. States EDJ's rate with its period and EDJ's own definition (annualized advisors who left or retired over advisors at period end), cited to the 10-Q; says Merrill gives no rate, only qualitative commentary ("near historic lows"). Then the adjacent net headcount change, with the difference between that and attrition stated plainly. The line "Neither firm discloses advisor attrition on a comparable basis." is acceptable if EDJ's rate is also reported.

**Claims**

1. The Edward Jones 2Q25 10-Q (published August 2025) states that financial advisor attrition increased to 6.4%, which it attributes primarily to an increase in retirements, consistent with industry trends. The Partnership ended that quarter with 20,309 financial advisors.
   - `EDJ-10Q-2025Q2#67` (10-Q, 2025-08-08): "The Partnership ended the second quarter of 2025 with a 12% increase in client assets under care ("AUC") to $2.3 trillion and a 9% increase in average client AUC, reflecting increases in the market value of client assets..."
2. The same 10-Q (August 2025) defines Attrition % as the annualized number of financial advisors that left or retired from the Partnership during the period, compared to the total number of financial advisors at period end.
   - `EDJ-10Q-2025Q2#66` (10-Q, 2025-08-08): "97 1% 98 97 1% (1) Income before allocations margin is income before allocations expressed as a percentage of total revenue. (2) Client dollars invested for trade revenue represents the principal amount of clients’ buy a..."
3. The Edward Jones 3Q25 10-Q (published November 2025) states that financial advisor attrition was 6.1%, with 20,429 financial advisors at quarter end. It cites a variety of factors, including a rise in departures of advisors with tenure of five years or less.
   - `EDJ-10Q-2025Q3#70` (10-Q, 2025-11-07): "The Partnership ended the third quarter of 2025 with $2.4 trillion of assets under care ("AUC"), including $1.0 trillion of advisory programs AUC. Average client AUC increased 12% due to higher average market levels, as ..."
4. The Edward Jones 2025 10-K (published March 2026) states that the Partnership believes its rate of attrition of financial advisors is in line with comparable firms. It does not name those firms or give their rates.
   - `EDJ-10K-2025#27` (10-K, 2026-03-13): "The Partnership experiences continued efforts by competing firms to hire away its financial advisors, although the Partnership believes its rate of attrition of financial advisors is in line with comparable firms. Human ..."

**Adjacent evidence (a related but different quantity)**

1. On the 2Q26 Bank of America earnings call (July 2026), CFO Alastair Borthwick said that adviser attrition is now at near historic lows. He made the remark while discussing Merrill's household and sales-force growth goals.
   - *Differs because:* It is a qualitative remark with no attrition percentage, from a GWIM-segment transcript, so it cannot be set against Edward Jones's 6.1% or 6.4% and is not a Merrill attrition rate.
   - `BAC-TR-2026Q2#63` (transcript, 2026-07-14): "Alastair M. Borthwick Executive VP & CFO First, I think you were referring to the Merrill 5% guide, where we said we are aiming for 5% over the course of the next 3 to 5 years. It's been 7 months, and I think we're off t..."

**Gaps (named by the answer)**

- Merrill's advisor attrition rate is not disclosed in the evidence provided; only a qualitative comment ("near historic lows") appears, so no numeric comparison with Edward Jones is possible. *Would fill it:* Bank of America 10-K or investor-day disclosures on Merrill advisor retention, or industry recruiter/consultant data on advisor turnover
- Neither firm discloses advisor attrition on a comparable basis. *Would fill it:* Bank of America/Merrill filings or investor materials stating an annualized attrition percentage on a definition matching Edward Jones's
- Merrill does not report standalone results. *Would fill it:* Bank of America 10-K or earnings supplement (GWIM segment)

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

### Q29: What does Morgan Stanley pay its financial advisors?

**Verdict: PASS**. 'Payout grids are not public', formulaic payout and aggregate compensation labelled as different quantities, sources named.

Tier 1, use case `honest_miss`. Expected behavior `gap_with_adjacent`, got `gap_with_adjacent`. Retrieval: 20 passages, mode `entity`.

*Passes if:* "Payout grids are not public." Then aggregate compensation expense from the 10-K, clearly labelled as a different quantity, and a named source that would answer it if acquired -- noting that trade-press reporting on grid changes is indicative, not authoritative.

**Claims**

1. The 2025 10-K (published 2026-02-19) states that for certain revenue-producing employees in the Wealth Management and Investment Management segments, compensation is largely paid on the basis of formulaic payouts that link employee compensation to revenues.
   - `MS-10K-2025#153` (10-K, 2026-02-19): "The factors that drive compensation for our employees vary from period to period, from segment to segment and within a segment. For certain revenue-producing employees in the Wealth Management and Investment Management b..."
2. The 2025 10-K (published 2026-02-19) says Wealth Management compensation and benefits expenses increased primarily due to an increase in the formulaic payout to Wealth Management advisors, driven by higher compensable revenue.
   - `MS-10K-2025#170` (10-K, 2026-02-19): "The level and pace of interest rate changes and other macroeconomic factors have impacted client preferences, including cash allocation to other products and client demand for loans. These factors, along with other devel..."
3. On the 4Q25 earnings call (published 2026-01-15), a company representative said that, as previously announced, Morgan Stanley will increase the cash component of its advisor compensation. Management said this supports its overall investment into financial advisors and will help simplify the compensation program. It also said there will be some transitional costs.
   - `MS-TR-2025Q4#22` (transcript, 2026-01-15): "Company Representative at Morgan Stanley As we look ahead to the remainder of 2026, assuming the current forward curve, incremental loan growth, and our projections for the deposit mix, we expect NII to continue to trend..."
4. On the 1Q25 earnings call (published 2025-04-11), CEO Ted Pick described the firm's offer to financial advisors as including "compensation that is viewed to be fair and motivating." This is management's characterization and gives no figures.
   - `MS-TR-2025Q1#54` (transcript, 2025-04-11): "Ted Pick Chairman and CEO at Morgan Stanley People are coming toward the platform. Jed Finn and Vince Lumia's lights are blinking, as in their phone lights, nonstop. Folks want to come onto this platform. That is in part..."

**Adjacent evidence (a related but different quantity)**

1. The 2025 10-K (published 2026-02-19) reports firmwide Compensation and benefits expenses of $29,216 million in 2025, up 12% from the prior year. It attributes the rise primarily to a higher formulaic payout to Wealth Management advisors and higher discretionary incentive compensation within Institutional Securities, plus higher salary expenses.
   - *Differs because:* Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid.
   - `MS-10K-2025#128` (10-K, 2026-02-19): "• We reported net revenues of $70.6 billion in 2025, which increased by 14% compared with $61.8 billion in 2024. Net income applicable to Morgan Stanley was $16.9 billion in 2025, which increased by 26% compared with $13..."
2. The 2Q26 10-Q (published 2026-08-04) reports firmwide Compensation and benefits expenses of $8,187 million in the quarter and $16,729 million year to date, up 14%. It attributes the rise primarily to a higher formulaic payout to Wealth Management advisors and higher Institutional Securities incentive compensation, both on higher revenues.
   - *Differs because:* Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid.
   - `MS-10Q-2026Q2#20` (10-Q, 2026-08-04): "• Compensation and benefits expenses of $8,187 million in the current quarter and $16,729 million in the current year period increased 14% compared with the prior year periods, primarily due to an increase in the formula..."

**Gaps (named by the answer)**

- Morgan Stanley: Payout grids are not public. The evidence gives no advisor payout percentages, grid tiers or average advisor pay figures. It says only that payouts are formulaic and tied to revenues. *Would fill it:* Morgan Stanley recruiting materials or advisor compensation plan documents; industry compensation surveys (indicative only)

### Q30 (trap): What is Merrill's standalone profitability?

**Verdict: PASS**. Trap held: 'Merrill does not report standalone results', GWIM figures with explicit 'GWIM is not Merrill'.

Tier 1, use case `honest_miss`. Expected behavior `gap_with_adjacent`, got `gap_with_adjacent`. Retrieval: 20 passages, mode `entity`.

*Passes if:* "Merrill does not report standalone results." Then Bank of America's GWIM segment figures, with an explicit statement that GWIM is not Merrill -- the segment includes the private bank -- so the number answers a related but different question.

**Adjacent evidence (a related but different quantity)**

1. 3Q26 (press release and deck published 2026-10-14): GWIM net income was $1,540 million on total revenue of $7,118 million, with pretax income of $2,053 million, a pretax margin of 29% and return on average allocated capital of 28%.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-PR-2026-10-14-01#11` (press, 2026-10-14): "4 Global Wealth and Investment Management1(C) Financial Results Three months ended ($ in millions) 9/30/2026 6/30/2026 9/30/2025 Total revenue2 $7,118 $6,871 $6,312 Provision for credit losses 17 11 4 Noninterest expense..."
   - `BAC-DECK-2026Q3#30` (deck, 2026-10-14): "Inc / (Dec) Summary Income Statement ($MM) 3Q26 2Q26 3Q25 Total revenue, net of interest expense $7,118 $247 $806 Provision for credit losses 17 6 13 Noninterest expense 5,048 72 426 Pretax income 2,053 169 367 Pretax, p..."
2. Nine months ended September 2026 (supplement published 2026-10-14): GWIM net income was $4,282 million, with a return on average allocated capital of 26% and an efficiency ratio of 72.27.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-SUPP-2026Q3#51` (supplement, 2026-10-14): "/ / / / / / / / / /---/---/---/---/---/---/---/---/ / (Dollars in millions) / Nine Months September / Ended 30 / Third Quarter / Second Quarter / First Quarter / Fourth Quarter / Third Quarter / / / 2026 / 2025 / 2026 / ..."
3. 2Q26 (deck published 2026-07-14): GWIM net income was $1,413 million (up from $993 million in 2Q25), with a pretax margin of 27% and ROAC of 26%.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-DECK-2026Q2#19` (deck, 2026-07-14): "Inc / (Dec) Summary Income Statement ($MM) 2Q26 1Q26 2Q25 Total revenue, net of interest expense $6,871 $159 $934 Provision for credit losses 11 9 (9) Noninterest expense 4,976 38 383 Pretax income 1,884 112 560 Pretax, ..."
   - `BAC-PR-2026-07-14-01#10` (press, 2026-07-14): "4 Global Wealth and Investment Management1(B) Financial Results Three months ended ($ in millions) 6/30/2026 3/31/2026 6/30/2025 Total revenue2 $6,871 $6,712 $5,937 Provision for credit losses 11 2 20 Noninterest expense..."
4. 1Q26 (deck published 2026-04-15): GWIM net income was $1,329 million, with a pretax margin of 26% and ROAC of 24%.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-DECK-2026Q1#26` (deck, 2026-04-15): "/ Summary Income Statement ($MM) / 1Q26 / Inc / (Dec) - 4Q25 / Inc / (Dec) - 1Q25 / /---/---/---/---/ / Total revenue, net of interest expense / $6,712 / $94 / $696 / / Provision (benefit) for credit losses / 2 / 5 / (12..."
   - `BAC-PR-2026-04-15-01#10` (press, 2026-04-15): "4 Global Wealth and Investment Management1(B) Financial Results Three months ended ($ in millions) 3/31/2026 12/31/2025 3/31/2025 Total revenue2 $6,712 $6,618 $6,016 Provision (benefit) for credit losses 2 (3) 14 Noninte..."
5. The 2025 10-K (published 2026-02-25) shows GWIM full-year 2025 net income of $4,670 million versus $4,263 million in 2024, an efficiency ratio of 74.84, and an operating margin of 25 percent in both 2025 and 2024. The 10-K describes Merrill Wealth Management as one of the businesses within GWIM alongside the Bank of America Private Bank.
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-10K-2025#244` (10-K, 2026-02-25): "(Dollars in millions) 2025 2024 % Change ──────────────────────────────────────────────────────────────────────────────────────────────────────── Net interest income $ 7,197 $ 6,969 3% Noninterest income: Investment and ..."
   - `BAC-10K-2025#246` (10-K, 2026-02-25): "Merrill Wealth Management’s advisory business provides a high-touch client experience through a network of financial advisors focused on clients with over $250,000 in total investable assets. Merrill Wealth Management pr..."
6. On the 3Q25 earnings call (October 2025), the CFO said that wealth management net income grew 19% year-over-year to nearly $1.3 billion, with a 26% return on allocated capital and a 27% pre-tax margin, and that "Together, Merrill and the private bank managed $4.6 trillion in client balances."
   - *Differs because:* GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's.
   - `BAC-TR-2025Q3#26` (transcript, 2025-10-15): "Alastair Borthwick CFO at Bank of America Finally, as shown on appendix slide 20, strong digital adoption and Erika engagement continues, and customer experience scores remain elevated, reflecting the impact of our ongoi..."

**Gaps (named by the answer)**

- Merrill does not report standalone results. *Would fill it:* Bank of America 10-K/10-Q segment disclosures or earnings supplement. These report only the combined GWIM segment, so a Merrill-only figure would need a new disclosure from Bank of America.

**Caveats (inserted by code)**

- GWIM is not Merrill: the segment also includes Bank of America Private Bank.

