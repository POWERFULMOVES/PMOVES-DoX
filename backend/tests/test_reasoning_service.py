"""Tests for ReasoningService."""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.reasoning_service import (
    ReasoningService,
    ReasoningStatus,
    Evidence,
    ReasoningStep,
    ReasoningTrace,
)


class TestReasoningServiceInit:
    """Tests for ReasoningService initialization."""

    def test_init_creates_empty_state(self):
        """New ReasoningService should have empty traces and evidence pool."""
        service = ReasoningService()
        assert service._traces == {}
        assert service._evidence_pool == {}


class TestStartReasoning:
    """Tests for starting reasoning traces."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_start_reasoning_success(self, service):
        """Starting a new reasoning trace should succeed."""
        trace = service.start_reasoning(
            question="What is the answer?",
            context="Some background context"
        )

        assert trace is not None
        assert trace.trace_id is not None
        assert trace.question == "What is the answer?"
        assert trace.context == "Some background context"
        assert trace.status == ReasoningStatus.ACTIVE
        assert trace.steps == []

    def test_start_reasoning_without_context(self, service):
        """Starting reasoning without context should work."""
        trace = service.start_reasoning(question="Simple question")

        assert trace.question == "Simple question"
        assert trace.context is None

    def test_start_reasoning_stores_trace(self, service):
        """Started trace should be stored internally."""
        trace = service.start_reasoning(question="Test")

        assert trace.trace_id in service._traces


class TestAddStep:
    """Tests for adding reasoning steps."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    @pytest.fixture
    def trace(self, service):
        """Create a trace for testing."""
        return service.start_reasoning(question="Test question")

    def test_add_step_success(self, service, trace):
        """Adding a step to an active trace should succeed."""
        step = service.add_step(
            trace_id=trace.trace_id,
            thought="First analysis step",
            confidence=0.8,
            agent_id="test-agent"
        )

        assert step is not None
        assert step.step_number == 1
        assert step.thought == "First analysis step"
        assert step.confidence == 0.8
        assert step.agent_id == "test-agent"

    def test_add_step_increments_number(self, service, trace):
        """Each step should have incrementing step numbers."""
        step1 = service.add_step(trace.trace_id, "Step 1", 0.7)
        step2 = service.add_step(trace.trace_id, "Step 2", 0.8)
        step3 = service.add_step(trace.trace_id, "Step 3", 0.9)

        assert step1.step_number == 1
        assert step2.step_number == 2
        assert step3.step_number == 3

    def test_add_step_nonexistent_trace(self, service):
        """Adding step to non-existent trace should return None."""
        step = service.add_step("fake-trace-id", "thought", 0.5)
        assert step is None

    def test_add_step_to_concluded_trace(self, service, trace):
        """Adding step to concluded trace should return None."""
        service.conclude(trace.trace_id, "Conclusion", 0.9)

        step = service.add_step(trace.trace_id, "Late step", 0.5)
        assert step is None


class TestAddEvidence:
    """Tests for adding evidence to steps."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    @pytest.fixture
    def trace_with_step(self, service):
        """Create a trace with one step."""
        trace = service.start_reasoning(question="Test")
        step = service.add_step(trace.trace_id, "Analysis", 0.7)
        return trace, step

    def test_add_evidence_success(self, service, trace_with_step):
        """Adding evidence to a step should succeed."""
        trace, step = trace_with_step

        evidence = service.add_evidence(
            trace_id=trace.trace_id,
            step_id=step.step_id,
            source="document-123",
            content="Relevant text from document",
            relevance_score=0.85
        )

        assert evidence is not None
        assert evidence.source == "document-123"
        assert evidence.content == "Relevant text from document"
        assert evidence.relevance_score == 0.85

    def test_add_evidence_to_pool(self, service, trace_with_step):
        """Added evidence should be stored in the pool."""
        trace, step = trace_with_step

        evidence = service.add_evidence(
            trace.trace_id, step.step_id,
            "source", "content", 0.8
        )

        assert evidence.evidence_id in service._evidence_pool

    def test_add_evidence_invalid_trace(self, service):
        """Adding evidence to invalid trace should return None."""
        evidence = service.add_evidence(
            "fake-trace", "fake-step",
            "source", "content", 0.5
        )
        assert evidence is None


class TestConclude:
    """Tests for concluding reasoning traces."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_conclude_success(self, service):
        """Concluding an active trace should succeed."""
        trace = service.start_reasoning(question="Test")
        service.add_step(trace.trace_id, "Analysis", 0.8)

        result = service.conclude(
            trace_id=trace.trace_id,
            conclusion="Final answer",
            final_confidence=0.9
        )

        assert result is True
        concluded_trace = service.get_trace(trace.trace_id)
        assert concluded_trace.status == ReasoningStatus.CONCLUDED
        assert concluded_trace.conclusion == "Final answer"
        assert concluded_trace.final_confidence == 0.9
        assert concluded_trace.concluded_at is not None

    def test_conclude_nonexistent_trace(self, service):
        """Concluding non-existent trace should return False."""
        result = service.conclude("fake-id", "conclusion", 0.5)
        assert result is False

    def test_conclude_already_concluded(self, service):
        """Concluding already concluded trace should return False."""
        trace = service.start_reasoning(question="Test")
        service.conclude(trace.trace_id, "First conclusion", 0.9)

        result = service.conclude(trace.trace_id, "Second conclusion", 0.8)
        assert result is False


class TestAbandon:
    """Tests for abandoning reasoning traces."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_abandon_success(self, service):
        """Abandoning an active trace should succeed."""
        trace = service.start_reasoning(question="Test")

        result = service.abandon(trace.trace_id)

        assert result is True
        abandoned_trace = service.get_trace(trace.trace_id)
        assert abandoned_trace.status == ReasoningStatus.ABANDONED

    def test_abandon_nonexistent_trace(self, service):
        """Abandoning non-existent trace should return False."""
        result = service.abandon("fake-id")
        assert result is False


class TestGetTrace:
    """Tests for retrieving traces."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_get_trace_success(self, service):
        """Getting existing trace should return it."""
        trace = service.start_reasoning(question="Test")
        service.add_step(trace.trace_id, "Step 1", 0.7)

        retrieved = service.get_trace(trace.trace_id)

        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id
        assert len(retrieved.steps) == 1

    def test_get_trace_nonexistent(self, service):
        """Getting non-existent trace should return None."""
        retrieved = service.get_trace("fake-id")
        assert retrieved is None


class TestGetEvidence:
    """Tests for retrieving evidence."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_get_evidence_success(self, service):
        """Getting existing evidence should return it."""
        trace = service.start_reasoning(question="Test")
        step = service.add_step(trace.trace_id, "Analysis", 0.7)
        evidence = service.add_evidence(
            trace.trace_id, step.step_id,
            "source", "content", 0.8
        )

        retrieved = service.get_evidence(evidence.evidence_id)

        assert retrieved is not None
        assert retrieved.evidence_id == evidence.evidence_id
        assert retrieved.source == "source"

    def test_get_evidence_nonexistent(self, service):
        """Getting non-existent evidence should return None."""
        retrieved = service.get_evidence("fake-id")
        assert retrieved is None


class TestListActiveTraces:
    """Tests for listing active traces."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_list_active_traces(self, service):
        """Listing should return only active traces."""
        trace1 = service.start_reasoning(question="Active 1")
        trace2 = service.start_reasoning(question="Active 2")
        trace3 = service.start_reasoning(question="Concluded")
        service.conclude(trace3.trace_id, "Done", 0.9)

        active = service.list_active_traces()

        assert len(active) == 2
        trace_ids = [t.trace_id for t in active]
        assert trace1.trace_id in trace_ids
        assert trace2.trace_id in trace_ids
        assert trace3.trace_id not in trace_ids

    def test_list_active_traces_empty(self, service):
        """Listing with no traces should return empty list."""
        active = service.list_active_traces()
        assert active == []


class TestEvidenceModel:
    """Tests for Evidence model validation."""

    def test_evidence_defaults(self):
        """Evidence should have default values."""
        evidence = Evidence(
            source="test",
            content="test content",
            relevance_score=0.5
        )

        assert evidence.evidence_id is not None
        assert evidence.metadata == {}

    def test_evidence_with_metadata(self):
        """Evidence should accept metadata."""
        evidence = Evidence(
            source="doc",
            content="text",
            relevance_score=0.8,
            metadata={"page": 5, "paragraph": 2}
        )

        assert evidence.metadata["page"] == 5


class TestReasoningStepModel:
    """Tests for ReasoningStep model."""

    def test_step_defaults(self):
        """ReasoningStep should have default values."""
        step = ReasoningStep(
            step_number=1,
            thought="Test thought",
            confidence=0.7
        )

        assert step.step_id is not None
        assert step.evidence == []
        assert step.agent_id is None
        assert step.created_at is not None


class TestReasoningTraceModel:
    """Tests for ReasoningTrace model."""

    def test_trace_defaults(self):
        """ReasoningTrace should have default values."""
        trace = ReasoningTrace(
            question="Test question"
        )

        assert trace.trace_id is not None
        assert trace.status == ReasoningStatus.ACTIVE
        assert trace.steps == []
        assert trace.conclusion is None
        assert trace.concluded_at is None


class TestReasoningServiceIntegration:
    """Integration tests for complete reasoning workflows."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReasoningService."""
        return ReasoningService()

    def test_complete_reasoning_workflow(self, service):
        """Test a complete reasoning workflow from start to conclusion."""
        # Start reasoning
        trace = service.start_reasoning(
            question="What is the capital of France?",
            context="Geographic question"
        )

        # Add first step with evidence
        step1 = service.add_step(
            trace.trace_id,
            "Looking for information about France",
            confidence=0.6,
            agent_id="search-agent"
        )
        service.add_evidence(
            trace.trace_id, step1.step_id,
            source="encyclopedia",
            content="France is a country in Western Europe",
            relevance_score=0.7
        )

        # Add second step with more evidence
        step2 = service.add_step(
            trace.trace_id,
            "Found capital information",
            confidence=0.95,
            agent_id="qa-agent"
        )
        service.add_evidence(
            trace.trace_id, step2.step_id,
            source="geography-db",
            content="Paris is the capital of France",
            relevance_score=0.99
        )

        # Conclude
        service.conclude(
            trace.trace_id,
            conclusion="The capital of France is Paris",
            final_confidence=0.98
        )

        # Verify final state
        final_trace = service.get_trace(trace.trace_id)
        assert final_trace.status == ReasoningStatus.CONCLUDED
        assert len(final_trace.steps) == 2
        assert final_trace.conclusion == "The capital of France is Paris"
        assert final_trace.final_confidence == 0.98
