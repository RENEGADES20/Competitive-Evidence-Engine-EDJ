"""Transcripts are chunked by speaker turn (#107). Fixtures are shrunk from the stored transcripts."""
from cee.config import entity_by_id
from cee.ingest.chunk import SegmentTagger, chunk_sections, pack_paragraphs
from cee.ingest.transcript import split_turns

CFO = "Alastair M. Borthwick Executive VP & CFO"
ANALYST = "Gerard Sean Cassidy RBC Capital Markets, Research Division"


def bac_tagger():
    bac = entity_by_id("BAC")
    return SegmentTagger(bac["segment_aliases"], bac["segment_stops"], (), bac["segment_mentions"],
                         bac["mention_stops"], bac["mention_excludes"], bac["mention_signals"])


def sp_transcript(*call: str) -> str:
    """S&P layout: header, participant list, then the call paragraphs."""
    return "\n\n".join([
        "Bank of America - Q2 2026 earnings call - 2026-07-14\n"
        "Transcript source: S&P Global Market Intelligence. Speaker names as in the source.",
        "Call Participants", "EXECUTIVES", CFO, "Brian Thomas Moynihan Chairman & CEO",
        "ANALYSTS", ANALYST, "Presentation", *call])


def chunks_of(text: str, tagger=None):
    return chunk_sections("BAC-TR-TEST", "BAC", "transcript", "2026-06-30", [("Document", text, None)],
                          segment_for=tagger or (lambda s, t, p=None: None))


# Shrunk from BAC-TR-2026Q2 (the issue's #38): the analyst asks, the CFO answers about Merrill, then
# moves on to commercial loans in the same turn.
MERRILL_1 = ("First, I think you were referring to the Merrill 5% guide, where we said we are aiming for 5% "
             "over the course of the next 3 to 5 years. Merrill added net new households and the advisers "
             "keep growing assets. " * 2).strip()
MERRILL_2 = ("We will keep growing the sales force, and adviser attrition is now at near historic lows, so "
             "the Merrill advisers and the Private Bank keep adding households. " * 2).strip()
COMMERCIAL = ("On the commercial loan growth, Global Banking loans grew in commercial and middle market, "
              "and the Global Markets and Consumer Banking segments grew deposits and card balances. " * 3).strip()
QA = sp_transcript(
    "Operator", "Welcome to the call.", CFO, "Thank you. Revenue grew.",
    "Question and Answer", "Operator", "We'll now move on to Gerard Cassidy with RBC.",
    ANALYST, "Alastair, can you update us on the Merrill 5% guide?",
    CFO, MERRILL_1, MERRILL_2, COMMERCIAL)


def test_question_and_answer_are_separate_chunks():
    texts = [c.text for c in chunks_of(QA)]
    question = next(t for t in texts if "update us on the Merrill" in t)
    assert question.startswith("Question and Answer\n\nOperator\n\nWe'll now move on")  # hand-off rides along
    assert f"\n\n{ANALYST}\n\n" in question and CFO not in question
    answers = [t for t in texts if MERRILL_1[:40] in t or COMMERCIAL[:40] in t]
    assert answers and all(t.startswith(CFO + "\n\n") for t in answers)
    assert all(ANALYST not in t for t in answers)


def test_merrill_part_of_an_answer_is_gwim_and_the_commercial_part_is_not():
    chunks = chunks_of(QA, bac_tagger())
    merrill = next(c for c in chunks if MERRILL_1[:40] in c.text)
    commercial = next(c for c in chunks if COMMERCIAL[:40] in c.text)
    assert merrill is not commercial
    assert merrill.segment == "GWIM" and commercial.segment is None
    assert merrill.prefix == "[BAC|GWIM|transcript|2026-06-30]"


def test_at_the_old_cap_the_answer_stays_one_untagged_chunk():
    # Why transcripts use 1,200: at 1,500 the whole answer (Merrill + commercial) fits one chunk,
    # the tagger sees both businesses and leaves it untagged, as with BAC-TR-2026Q2#38 before #107.
    from cee.ingest.transcript import turn_pieces
    pieces = [p for p in turn_pieces(QA, pack_paragraphs, 1500) if MERRILL_1[:40] in p[0]]
    assert len(pieces) == 1 and COMMERCIAL[:40] in pieces[0][0]
    assert bac_tagger()("Document", pieces[0][1]) is None


def test_long_answer_splits_into_chunks_of_the_same_turn():
    long_answer = [("Sentence about net interest income and deposits. " * 12).strip() for _ in range(5)]
    chunks = chunks_of(sp_transcript(ANALYST, "A question?", CFO, *long_answer, ANALYST, "Next question?"))
    answer = [c.text for c in chunks if "net interest income" in c.text]
    assert len(answer) >= 3
    assert all(t.startswith(CFO + "\n\n") and len(t) <= 1200 for t in answer)
    assert "\n\n".join(t.split("\n\n", 1)[1] for t in answer) == "\n\n".join(long_answer)


# Shrunk from BAC-TR-2026Q1: the CFO names GWIM once, then keeps talking about it past the cap.
GWIM_OPEN = ("On Slide 14, we turn to Global Wealth and Investment Management, which delivered a strong quarter "
             "on solid client flows and disciplined expenses. " * 4).strip()
GWIM_MORE = ("Client balances increased, and we remain focused on adviser productivity; we continue to attract "
             "talent across both new and experienced advisers. " * 4).strip()
BANKING = ("Global Banking delivered solid results, with commercial loans and deposits growing and "
           "investment banking fees up. " * 6).strip()


def test_continuation_of_a_gwim_turn_keeps_the_tag():
    chunks = chunks_of(sp_transcript(CFO, GWIM_OPEN, GWIM_MORE), bac_tagger())
    opening = next(c for c in chunks if GWIM_OPEN[:40] in c.text)
    more = next(c for c in chunks if GWIM_MORE[:40] in c.text)
    assert opening is not more and opening.segment == "GWIM" and more.segment == "GWIM"


def test_continuation_that_moves_to_another_business_is_untagged():
    chunks = chunks_of(sp_transcript(CFO, GWIM_OPEN, BANKING), bac_tagger())
    opening = next(c for c in chunks if GWIM_OPEN[:40] in c.text)
    banking = next(c for c in chunks if BANKING[:40] in c.text)
    assert opening is not banking and opening.segment == "GWIM" and banking.segment is None


def test_a_new_speaker_does_not_inherit_the_tag():
    chunks = chunks_of(sp_transcript(CFO, GWIM_OPEN, ANALYST, GWIM_MORE), bac_tagger())
    assert next(c for c in chunks if GWIM_MORE[:40] in c.text).segment is None


def test_speaker_label_is_not_counted_by_the_tagger():
    # "RBC Capital Markets" in the analyst's label is a firm, not BAC's Global Markets.
    chunks = chunks_of(sp_transcript(ANALYST, "How are Merrill advisers and households growing at Merrill?"),
                       bac_tagger())
    assert next(c for c in chunks if "Merrill advisers" in c.text).segment == "GWIM"


def test_acquisition_of_merrill_is_history_not_gwim():
    # BAC-TR-2025Q1: the 2009 balance sheet "after the acquisition of Merrill".
    text = sp_transcript(CFO, "I'm on slide 22. It shows the company in the fourth quarter of 2009, after the "
                              "acquisition of Merrill, and the company today.")
    assert all(c.segment is None for c in chunks_of(text, bac_tagger()))


def test_marketbeat_label_with_firm():
    text = "\n\n".join([
        "Morgan Stanley - Q2 2025 earnings call - 2025-07-16\n"
        "Transcript source: MarketBeat (transcript provided by Quartr). Speaker names as in the source.",
        "Call Participants", "EXECUTIVES", "Ted Pick Chairman and CEO", "ANALYSTS",
        "Mike Mayo Analyst at Wells Fargo", "Presentation",
        "Ted Pick Chairman and CEO at Morgan Stanley", "Thank you, and good morning.",
        "Mike Mayo Analyst at Wells Fargo", "Hi. A question on wealth?"])
    speakers = [t.speaker for t in split_turns(text)[1:]]
    assert speakers == ["Ted Pick Chairman and CEO at Morgan Stanley", "Mike Mayo Analyst at Wells Fargo"]


def test_bloomberg_names_and_q_a_labels():
    text = "\n\n".join([
        "Bank of America - Q3 2026 earnings call - 2026-10-14\n"
        "Transcript source: Bloomberg. Speaker names as in the source.",
        "Company Participants", "Alastair Borthwick Brian T. Moynihan",
        "Other Participants", "Gerard Cassidy Mike Mayo", "Presentation",
        "Alastair Borthwick", "Thank you, and good morning.",
        "Q - Gerard Cassidy", "A question on Merrill?", "A - Alastair Borthwick", "An answer."])
    speakers = [t.speaker for t in split_turns(text)[1:]]
    assert speakers == ["Alastair Borthwick", "Q - Gerard Cassidy", "A - Alastair Borthwick"]


def test_roic_bare_names_without_a_list():
    text = "\n\n".join([
        "Charles Schwab - Q4 2024 earnings call - 2025-01-21\n"
        "Transcript source: Roic.ai. Speaker names as in the source.",
        "Jeff Edwards", "Good morning, everyone.", "Rick Wurster", "Thanks, Jeff."])
    assert [t.speaker for t in split_turns(text)[1:]] == ["Jeff Edwards", "Rick Wurster"]


def test_label_split_over_two_paragraphs_and_page_header_leftover():
    text = sp_transcript(
        "Alastair M. Borthwick", "Executive VP & CFO", "Revenue grew.",
        "BANK OF AMERICA CORPORATION FQ2 2026 EARNINGS CALL - PRELIMINARY COPY JUL 14, 2026",
        "Deposits grew too.")
    turns = split_turns(text)[1:]
    assert [t.speaker for t in turns] == [CFO]
    assert turns[0].paras == ["Revenue grew.", "Deposits grew too."]


def test_preamble_keeps_the_header_and_participant_list():
    first = chunks_of(QA)[0].text
    assert first.startswith("Bank of America - Q2 2026 earnings call") and "ANALYSTS" in first


def test_other_document_types_chunk_as_before():
    body = "\n\n".join(("Paragraph %d about deposits. " % i) * 30 for i in range(4))
    chunks = chunk_sections("BAC-PR-TEST", "BAC", "press", "2026-06-30", [("Document", body, None)])
    assert [c.text for c in chunks] == pack_paragraphs(body)
