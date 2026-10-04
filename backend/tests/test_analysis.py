import pytest

from backend.app.services.analysis import analyze_document, cross_check


@pytest.mark.asyncio
async def test_rejects_empty_upload():
    result = await analyze_document("id", "blank.pdf", "application/pdf", b"")
    assert result["status"] == "Rejected"
    assert "empty" in result["reason"].lower()


def test_no_upload_has_exact_rejection_message():
    issues, checks, health, status = cross_check({"name": "Aisha", "date_of_birth": "2004-02-01", "marks_percentage": "88%", "family_income": "240000"}, [])
    assert status == "Rejected"
    assert issues[0]["message"] == "Application rejected: no documents were uploaded. Please upload the required documents."
    assert health == 0


def test_missing_document_lists_exact_slot():
    issues, _, _, status = cross_check({"name": "Aisha", "date_of_birth": "2004-02-01", "marks_percentage": "88%", "family_income": "240000"}, [{"slot": "id", "status": "Verified", "confidence": .9, "fields": {}}])
    assert status == "Rejected"
    assert "Marksheet" in issues[0]["message"]
    assert "Income certificate" in issues[0]["message"]


def test_name_mismatch_becomes_needs_correction():
    issues, _, _, status = cross_check({"name": "Aisha Rahman", "date_of_birth": "2004-02-01", "marks_percentage": "88%", "family_income": "240000"}, [{"slot": "id", "status": "Verified", "confidence": .9, "fields": {"name": {"value": "Ayesha Khan", "confidence": .9}}}, {"slot": "marksheet", "status": "Verified", "confidence": .9, "fields": {"name": {"value": "Aisha Rahman", "confidence": .9}}}, {"slot": "income", "status": "Verified", "confidence": .9, "fields": {"name": {"value": "Aisha Rahman", "confidence": .9}}}])
    assert status in {"Needs Correction", "Manual Review"}
    assert any(issue["code"] == "name_mismatch" for issue in issues)
