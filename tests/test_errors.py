"""Tests for the exception hierarchy in research_agent.errors."""

from research_agent.errors import (
    ResearchError,
    SchemaError,
    SearchError,
    SkepticError,
    StateError,
    SynthesisError,
)


class TestAllExceptionsSubclassResearchError:
    """SchemaError and StateError subclass ResearchError."""

    def test_schema_error(self):
        assert issubclass(SchemaError, ResearchError)

    def test_state_error(self):
        assert issubclass(StateError, ResearchError)


class TestSchemaErrorCarriesMultipleErrors:
    """SchemaError(errors=["err1", "err2"]) stores both errors."""

    def test_stores_errors_list(self):
        err = SchemaError("validation failed", errors=["err1", "err2"])
        assert err.errors == ["err1", "err2"]

    def test_empty_errors_by_default(self):
        err = SchemaError("parse failed")
        assert err.errors == []

    def test_errors_accessible_via_attribute(self):
        errors = ["missing field: name", "invalid type: age"]
        err = SchemaError("schema invalid", errors=errors)
        assert len(err.errors) == 2
        assert "missing field: name" in err.errors


class TestExceptionsCarryMessage:
    """All new exceptions accept and store a message string."""

    def test_schema_error_message(self):
        err = SchemaError("bad yaml")
        assert str(err) == "bad yaml"

    def test_state_error_message(self):
        err = StateError("corrupt file")
        assert str(err) == "corrupt file"


class TestExistingExceptionsUnchanged:
    """SearchError, SynthesisError, SkepticError still exist and subclass ResearchError."""

    def test_search_error(self):
        assert issubclass(SearchError, ResearchError)
        err = SearchError("no results")
        assert str(err) == "no results"

    def test_synthesis_error(self):
        assert issubclass(SynthesisError, ResearchError)
        err = SynthesisError("synthesis failed")
        assert str(err) == "synthesis failed"

    def test_skeptic_error(self):
        assert issubclass(SkepticError, ResearchError)
        err = SkepticError("skeptic failed")
        assert str(err) == "skeptic failed"
