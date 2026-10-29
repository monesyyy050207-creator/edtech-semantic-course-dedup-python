from src.course_deduplication import CourseRecord, choose_record, delivery_text


def test_checkout_course_reuses_a_close_existing_record():
    record = CourseRecord("checkout-101", "Checkout basics", "2026-11-15", "Mina", "weekly")
    assert "Checkout basics" in delivery_text(record)
    result = choose_record([{"id": "catalog-7", "score": 0.93, "metadata": {"title": "Checkout fundamentals"}}])
    assert result["decision"] == "reuse"
    assert result["match"]["id"] == "catalog-7"


def test_a_different_deadline_creates_a_new_record():
    result = choose_record([{"id": "catalog-7", "score": 0.71}])
    assert result == {"decision": "create", "match": None}
