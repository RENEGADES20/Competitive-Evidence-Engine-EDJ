# Brief (distilled)

Source: the project brief and the Thirty Questions document from the project lead.
Ground rules are not restated here: see [CLAUDE.md, Ground rules](../CLAUDE.md#ground-rules).

## Purpose

A searchable, cited corpus of public evidence about a small set of wealth-management
competitors and Edward Jones itself, plus a front end where someone asks a plain-language
question and gets an answer in which every claim links to a document the system stored.

- Built for Edward Jones's Chief Strategy Officer (CSO). The project lead stands in for him
  and runs every evaluation.
- The corpus is built **ahead** of the questions, not fetched at question time: fast,
  reproducible, auditable. Same question twice -> same answer, same sources.
- When evidence is missing, the system says so and names the source that would answer it.
  Built in week 1, not patched in week 11.
- It assembles what is known and where it was said. It does not recommend or forecast.

## Eight use cases

| Use case | Example | Returns | Stops at |
|---|---|---|---|
| Entity brief | What is Morgan Stanley's strategy to increase NNA? | Synthesized brief, every claim linked; direct quotes where wording matters | What the firm will do next, or what Edward Jones should do |
| Head to head | How do Schwab, LPL and Ameriprise approach advisor recruiting? | Same dimensions per firm side by side; undisclosed cells shown as gaps | Declaring a winner; filling empty cells with guesses |
| Mechanism | How does Schwab use scale to acquire clients cheaply? | Mechanism end to end: economics, channels, management claims, what disclosure misses; Edward Jones filings alongside | "...and how Edward Jones could replicate it" |
| Theme scan | What will receiving advice look like in future? | Range of positions and who holds them, organized by position | A forecast; picking one view |
| Segment evidence | What do we know about younger investors' preferences? | Survey data, competitor moves, management statements, each sourced and dated | "...and so Edward Jones should" |
| Benchmark | NNA by quarter across the peer set | Table of value, period, source, and each firm's own metric definition | Normalizing definitions behind the scenes |
| Recency | What's new on Raymond James in the last 90 days? | What entered the corpus, newest first, one line on why it matters | Pushing / alerting |
| Honest miss | Anything on Vanguard's advisor compensation? | "No", what the corpus does hold, and which source would answer | Guessing |

## Coverage

Core five this term (chosen for structural variety):

| Firm | How it reports | Why it is in the five |
|---|---|---|
| Morgan Stanley (MS) | Wealth Management is a reported segment | Named in seed questions; rich segment disclosure |
| Charles Schwab (SCHW) | Pure-play | Strongest disclosure; monthly activity reports incl. NNA |
| Edward Jones (EDJ) | The Jones Financial Companies, L.L.L.P., files 10-K, CIK 815917 | Our side of every comparison |
| Merrill (MER) | Segment of BAC: Global Wealth & Investment Management (GWIM) | Deliberate hard case: segment attribution |
| Raymond James (RJF) | Private Client Group segment | Closest structural peer (employee advisors, branches) |

Expansion eleven (earned, not scheduled; only after gates 1-3 pass cleanly):

| Group | Firms | Cost once the five work |
|---|---|---|
| Pure-play public | Ameriprise (AMP), LPL (LPLA), Stifel (SF), Robinhood (HOOD) | Nearly free |
| Bank segments | J.P. Morgan WM (JPM), Wells Fargo Advisors (WFC), Goldman (GS) | Nearly free (reuses Merrill solution) |
| Foreign filers | UBS (20-F), RBC (40-F) | Real work: new doc types and calendars |
| Private | Fidelity, Vanguard | Real work: Form ADV and research only; thinness must be visible |

Design test: adding a sixth firm must be configuration and a source list, not new code.

## Source tiers

| Tier | Label | Contents |
|---|---|---|
| 1 | licensed | Capital IQ, Bloomberg (financials, segments, transcripts). Blocked on ADR-000 |
| 2 | filing | SEC EDGAR (10-K, 10-Q, 8-K, DEF 14A, 20-F, 40-F), Form ADV / IAPD bulk, FINRA BrokerCheck |
| 3 | IR | Investor-day decks, quarterly supplements, press releases, monthly metrics |
| 4 | trade press | InvestmentNews, Financial Planning, ThinkAdvisor, RIABiz, AdvisorHub, WealthManagement.com, Barron's Advisor, Citywire RIA. Expect feed rot; re-check monthly |
| 5 | research | Cerulli (library), consultancies, FINRA Foundation, CFP Board, free investor surveys, SEC/DOL direction. Indexed by theme; start week 3 |
| 6 | signal (stretch) | Job postings, app-store reviews. Only after tiers 1-5 and the bar are done |

## Acceptance bar

The project lead sits down cold and asks **10 questions** from the bank. For **at least 7**
he gets an answer with working citations he would forward to the CSO with his name on it.
For the **other 3**, the system says honestly what it does not have.

Floor if the bar is missed: a deep, correctly cited, searchable corpus of the five firms.
Work is ordered so the floor arrives first.

## Boundaries (binding)

Not building this term: alerts and notifications; autonomous web-browsing agents;
recommendations or advice; forecasts and predictions; any Edward Jones internal data;
any client or advisor data; production security / SSO; multi-user accounts; mobile;
slide decks; written reports. The only shipped document is a page on how to run it.

## Gates

A gate that fails means scope comes out, never that the gate moves.

| Gate | Weeks | Pass criteria |
|---|---|---|
| 1 | W1-2 | 30 questions; 5 entities locked, 11 mapped; source feasibility matrix; written licensing answer; skeleton runs end to end on all 7 machines |
| 2 | W3-5 (check W5) | 10 bank questions: a human finds the answer in the database by hand in < 10 min each. And: adding a sixth firm is not as costly as the first |
| 3 | W6-8 (check W8) | >= 60% of the bank (18/30) at acting quality, citations resolve |
| 4 | W9-11 (check W11) | >= 70% (21/30) at acting quality, and the project lead used it unsupervised at least once |

W12: harden and hand off, no new capability. Project lead evaluation sessions: W7, W10, W12.

## Risks

| Risk | Mitigation |
|---|---|
| Corpus breadth is the long pole and feels boring | Gate 2; three of seven on corpus |
| Licensing comes back restrictive | Resolve in writing in W1 (ADR-000); tiers 2-5 alone must clear the bar |
| Thematic questions need a corpus nobody built | Tier 5 starts W3, owned by C3 |
| Segment attribution quietly corrupts answers (BAC news as Merrill) | Three trap questions (Q4, Q27, Q30) scored weekly all term; segment hard filter |
| A pod stalls because work is outside its skillset | Tech lead unblocks; everyone starts from a running skeleton |
