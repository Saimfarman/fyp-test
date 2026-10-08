from backend.app.audits import (
    ContactRule,
    HeadingRule,
    PageFacts,
    TitleRule,
    ViewportRule,
    _score,
    _severity,
)


def page(html: str, url: str = "https://example.com") -> PageFacts:
    return PageFacts(url=url, status_code=200, html=html, headers={})


def test_rules_accept_complete_page():
    complete = page(
        """
        <html><head><title>Example</title>
        <meta name="description" content="A local business">
        <meta name="viewport" content="width=device-width"></head>
        <body><h1>Example</h1><a href="tel:+923001234567">Call</a></body></html>
        """
    )

    assert TitleRule().evaluate(complete) is None
    assert HeadingRule().evaluate(complete) is None
    assert ViewportRule().evaluate(complete) is None
    assert ContactRule().evaluate(complete) is None


def test_score_penalizes_each_issue_category():
    issue = TitleRule().evaluate(page("<html><body><h1>Example</h1></body></html>"))
    assert issue is not None

    overall, categories = _score([issue])

    assert categories["On-page"] == 82
    assert overall < 100


def test_severity_respects_status_and_score_thresholds():
    assert _severity(80, "HAS_WEBSITE")[0] == "LOW"
    assert _severity(60, "HAS_WEBSITE")[0] == "MEDIUM"
    assert _severity(40, "HAS_WEBSITE")[0] == "HIGH"
    assert _severity(20, "HAS_WEBSITE")[0] == "CRITICAL"
    assert _severity(100, "DEAD_SITE")[0] == "CRITICAL"
