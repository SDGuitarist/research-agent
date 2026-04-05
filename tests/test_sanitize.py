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

    def test_already_escaped_input_is_idempotent(self):
        """Pre-escaped entities normalize back, then re-escape once."""
        result = sanitize_content("&lt;script&gt;")
        assert result == "&lt;script&gt;"


class TestSanitizeIdempotency:
    """Idempotency invariant: sanitize(sanitize(x)) == sanitize(x)."""

    def _assert_idempotent(self, text: str) -> None:
        once = sanitize_content(text)
        twice = sanitize_content(once)
        assert twice == once, f"Not idempotent for {text!r}: {once!r} → {twice!r}"

    def test_plain_text(self):
        self._assert_idempotent("hello world")

    def test_ampersand(self):
        self._assert_idempotent("a & b")

    def test_angle_brackets(self):
        self._assert_idempotent("<script>alert('xss')</script>")

    def test_pre_escaped_amp(self):
        self._assert_idempotent("&amp;")

    def test_pre_escaped_lt(self):
        self._assert_idempotent("&lt;")

    def test_pre_escaped_gt(self):
        self._assert_idempotent("&gt;")

    def test_mixed_raw_and_escaped(self):
        self._assert_idempotent("a & <b> &lt;c&gt;")

    def test_unicode(self):
        self._assert_idempotent("émoji 🎉 & stuff")

    def test_empty_string(self):
        self._assert_idempotent("")

    def test_html_entity_nbsp(self):
        self._assert_idempotent("&nbsp;")

    def test_html_entity_euro(self):
        self._assert_idempotent("&euro;")

    def test_numeric_entity(self):
        self._assert_idempotent("&#x27;")

    def test_nested_tags_with_ampersand(self):
        self._assert_idempotent("</source>&<injected>")
