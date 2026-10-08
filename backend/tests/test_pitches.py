from app.pitches import _build_content, _pdf_bytes
from app.models import Lead


def test_pitch_content_is_bilingual_and_fact_grounded():
    lead = Lead(name="Karachi Cafe", website_status="NO_WEBSITE")

    content = _build_content(lead, None, [], "both")

    assert content["language"] == "both"
    assert "Karachi Cafe" in content["english"]["opening"]
    assert content["urdu"]["body"]
    assert len(content["recommendations"]) == 3
    assert content["price"] is None


def test_proposal_pdf_has_pdf_signature():
    result = _pdf_bytes("Proposal", ["Website plan", "Timeline: 1-2 weeks"])

    assert result.startswith(b"%PDF-1.4")
    assert b"Website plan" in result
