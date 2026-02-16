"""Tests for sanitize_content() — single canonical location."""

from research_agent.sanitize import sanitize_content


class TestSanitizeContent:
    """Tests for sanitize_content() function."""

    def test_escapes_angle_brackets(self):
        result = sanitize_content("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_handles_empty_string(self):
        assert sanitize_content("") == ""

    def test_preserves_normal_text(self):
        text = "This is normal text without any special characters."
        assert sanitize_content(text) == text

    def test_escapes_nested_tags(self):
        result = sanitize_content("</source><injected>malicious</injected>")
        assert "&lt;/source&gt;" in result
        assert "&lt;injected&gt;" in result

    def test_handles_multiple_tags(self):
        result = sanitize_content("<div><p>text</p></div>")
        assert result == "&lt;div&gt;&lt;p&gt;text&lt;/p&gt;&lt;/div&gt;"

    def test_escapes_ampersands(self):
        result = sanitize_content("Tom & Jerry")
        assert result == "Tom &amp; Jerry"

    def test_ampersand_before_angle_brackets(self):
        result = sanitize_content("&lt;script&gt;")
        assert result == "&amp;lt;script&amp;gt;"
