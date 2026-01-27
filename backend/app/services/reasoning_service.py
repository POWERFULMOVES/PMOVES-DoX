"""Reasoning service for multi-step reasoning with evidence tracking.

This module provides structured reasoning capabilities with:
- Reasoning trace management (start, add steps, conclude)
- Evidence circulation between reasoning steps
- Citation and confidence tracking

Note: Storage is currently in-memory only. Traces are NOT persisted across
service restarts. For persistent storage, integrate with CipherService.

The service supports multi-agent reasoning where different agents can contribute
steps to a shared reasoning trace, with evidence accumulated in a pool that
can be referenced across steps.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReasoningStatus(str, Enum):
    """Status of a reasoning trace.

    Attributes:
        ACTIVE: Reasoning is in progress, steps can be added.
        CONCLUDED: Reasoning completed with a final conclusion.
        ABANDONED: Reasoning was abandoned without conclusion.
    """

    ACTIVE = "active"
    CONCLUDED = "concluded"
    ABANDONED = "abandoned"


class Evidence(BaseModel):
    """A piece of evidence supporting reasoning.

    Attributes:
        evidence_id: Unique identifier for this evidence.
        source: Origin of evidence (Document ID, URL, or "agent:{agent_id}").
        content: The actual evidence content.
        relevance_score: How relevant this evidence is (0.0-1.0).
        metadata: Additional contextual information.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    content: str
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    """A single step in a reasoning trace.

    Attributes:
        step_id: Unique identifier for this step.
        step_number: Sequential position in the trace (1-indexed).
        thought: The reasoning thought for this step.
        evidence: List of evidence items supporting this step.
        confidence: Confidence level in this step (0.0-1.0).
        agent_id: ID of the agent that contributed this step.
        created_at: Timestamp when this step was created.
    """

    step_id: str = Field(default_factory=lambda: str(uuid4()))
    step_number: int
    thought: str
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    agent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReasoningTrace(BaseModel):
    """A complete reasoning trace from question to conclusion.

    Attributes:
        trace_id: Unique identifier for this trace.
        question: The question or problem being reasoned about.
        context: Optional context or constraints for reasoning.
        steps: List of reasoning steps taken.
        conclusion: Final answer or conclusion (if concluded).
        status: Current status of the trace.
        final_confidence: Overall confidence in the conclusion.
        max_steps: Maximum allowed steps for this trace.
        created_at: Timestamp when trace was created.
        concluded_at: Timestamp when trace was concluded.
    """

    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    context: Optional[str] = None
    steps: List[ReasoningStep] = Field(default_factory=list)
    conclusion: Optional[str] = None
    status: ReasoningStatus = ReasoningStatus.ACTIVE
    final_confidence: Optional[float] = None
    max_steps: int = Field(default=10, ge=1, le=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    concluded_at: Optional[datetime] = None

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class ReasoningService:
    """Service for managing multi-step reasoning traces.

    Provides methods to:
    - Start new reasoning traces with a question
    - Add steps with thoughts and evidence
    - Conclude reasoning with final answer
    - Query and retrieve traces
    - Manage evidence pools for cross-step reference

    Attributes:
        _traces: Dictionary of active reasoning traces by ID.
        _evidence_pool: Dictionary of evidence pools by trace ID.
    """

    def __init__(self) -> None:
        """Initialize the ReasoningService.

        Creates a new instance with empty trace and evidence pool registries.
        """
        self._traces: Dict[str, ReasoningTrace] = {}
        self._evidence_pool: Dict[str, List[Evidence]] = {}
        logger.info("ReasoningService initialized")

    async def start_reasoning(
        self,
        question: str,
        context: Optional[str] = None,
        max_steps: int = 10
    ) -> ReasoningTrace:
        """Start a new reasoning trace.

        Creates a new reasoning trace for the given question and initializes
        an empty evidence pool. The trace is marked as ACTIVE and ready to
        receive reasoning steps.

        Args:
            question: The question to reason about.
            context: Optional context or constraints.
            max_steps: Maximum allowed steps (stored in metadata).

        Returns:
            New ReasoningTrace with generated trace_id.

        Raises:
            ValueError: If question is empty or max_steps is invalid.
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if max_steps < 1 or max_steps > 100:
            raise ValueError("max_steps must be between 1 and 100")

        trace = ReasoningTrace(
            question=question.strip(),
            context=context.strip() if context else None,
            max_steps=max_steps,
            status=ReasoningStatus.ACTIVE,
        )

        self._traces[trace.trace_id] = trace
        self._evidence_pool[trace.trace_id] = []

        logger.info(
            f"Started reasoning trace {trace.trace_id[:8]}... "
            f"question='{question[:50]}...' max_steps={max_steps}"
        )

        return trace

    async def add_step(
        self,
        trace_id: str,
        thought: str,
        evidence: Optional[List[Evidence]] = None,
        confidence: float = 0.5,
        agent_id: Optional[str] = None
    ) -> ReasoningStep:
        """Add a reasoning step to an active trace.

        Creates a new step with the given thought and optional evidence,
        appending it to the trace's step list. Evidence items are also
        added to the trace's evidence pool for cross-step reference.

        Args:
            trace_id: Target trace ID.
            thought: The reasoning thought for this step.
            evidence: Supporting evidence (optional).
            confidence: Confidence in this step (0.0-1.0).
            agent_id: ID of agent contributing this step.

        Returns:
            The created ReasoningStep.

        Raises:
            ValueError: If trace not found, not active, or max steps reached.
        """
        trace = self._traces.get(trace_id)

        if not trace:
            raise ValueError(f"Reasoning trace not found: {trace_id}")

        if trace.status != ReasoningStatus.ACTIVE:
            raise ValueError(
                f"Cannot add step to {trace.status.value} trace: {trace_id}"
            )

        if len(trace.steps) >= trace.max_steps:
            raise ValueError(
                f"Maximum steps ({trace.max_steps}) reached for trace: {trace_id}"
            )

        if not thought or not thought.strip():
            raise ValueError("Thought cannot be empty")

        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))

        step_number = len(trace.steps) + 1
        step = ReasoningStep(
            step_number=step_number,
            thought=thought.strip(),
            evidence=evidence or [],
            confidence=confidence,
            agent_id=agent_id,
        )

        trace.steps.append(step)

        # Add evidence to the pool for cross-step reference
        if evidence:
            for ev in evidence:
                if ev not in self._evidence_pool[trace_id]:
                    self._evidence_pool[trace_id].append(ev)

        logger.info(
            f"Added step {step_number} to trace {trace_id[:8]}... "
            f"confidence={confidence:.2f} agent={agent_id or 'none'}"
        )

        return step

    async def conclude(
        self,
        trace_id: str,
        conclusion: str,
        final_confidence: Optional[float] = None
    ) -> ReasoningTrace:
        """Conclude a reasoning trace with final answer.

        Marks the trace as CONCLUDED and sets the final conclusion.
        If final_confidence is not provided, it is calculated as the
        weighted average of step confidences (weighted by step number).

        Args:
            trace_id: Trace to conclude.
            conclusion: Final answer/conclusion.
            final_confidence: Overall confidence (defaults to avg of steps).

        Returns:
            Updated ReasoningTrace with conclusion.

        Raises:
            ValueError: If trace not found or already concluded.
        """
        trace = self._traces.get(trace_id)

        if not trace:
            raise ValueError(f"Reasoning trace not found: {trace_id}")

        if trace.status == ReasoningStatus.CONCLUDED:
            raise ValueError(f"Trace already concluded: {trace_id}")

        if not conclusion or not conclusion.strip():
            raise ValueError("Conclusion cannot be empty")

        # Calculate final confidence if not provided
        if final_confidence is None:
            if trace.steps:
                # Weighted average: later steps weighted more heavily
                total_weight = 0.0
                weighted_sum = 0.0
                for step in trace.steps:
                    weight = step.step_number
                    weighted_sum += step.confidence * weight
                    total_weight += weight
                final_confidence = weighted_sum / total_weight if total_weight > 0 else 0.5
            else:
                final_confidence = 0.5
        else:
            # Clamp to valid range
            final_confidence = max(0.0, min(1.0, final_confidence))

        trace.conclusion = conclusion.strip()
        trace.status = ReasoningStatus.CONCLUDED
        trace.final_confidence = final_confidence
        trace.concluded_at = datetime.now(timezone.utc)

        logger.info(
            f"Concluded trace {trace_id[:8]}... "
            f"steps={len(trace.steps)} final_confidence={final_confidence:.2f}"
        )

        return trace

    async def abandon(self, trace_id: str, reason: Optional[str] = None) -> ReasoningTrace:
        """Abandon a reasoning trace without conclusion.

        Marks the trace as ABANDONED. This is useful when reasoning
        cannot proceed due to insufficient evidence or other blockers.

        Args:
            trace_id: Trace to abandon.
            reason: Optional reason for abandonment (stored in conclusion field).

        Returns:
            Updated ReasoningTrace with ABANDONED status.

        Raises:
            ValueError: If trace not found or already concluded/abandoned.
        """
        trace = self._traces.get(trace_id)

        if not trace:
            raise ValueError(f"Reasoning trace not found: {trace_id}")

        if trace.status != ReasoningStatus.ACTIVE:
            raise ValueError(
                f"Cannot abandon {trace.status.value} trace: {trace_id}"
            )

        trace.status = ReasoningStatus.ABANDONED
        trace.conclusion = reason
        trace.concluded_at = datetime.now(timezone.utc)

        logger.info(
            f"Abandoned trace {trace_id[:8]}... "
            f"reason='{reason[:50] if reason else 'none'}'"
        )

        return trace

    async def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a reasoning trace by ID.

        Args:
            trace_id: The trace identifier.

        Returns:
            ReasoningTrace if found, None otherwise.
        """
        trace = self._traces.get(trace_id)
        if trace:
            logger.debug(f"Retrieved trace {trace_id[:8]}...")
        else:
            logger.debug(f"Trace not found: {trace_id}")
        return trace

    async def add_evidence(
        self,
        trace_id: str,
        evidence: Evidence
    ) -> Evidence:
        """Add evidence to the pool for a trace.

        Adds evidence to the shared evidence pool without attaching it
        to a specific step. This allows evidence to be accumulated
        before deciding which steps to associate it with.

        Args:
            trace_id: Target trace ID.
            evidence: Evidence to add to the pool.

        Returns:
            The added Evidence object.

        Raises:
            ValueError: If trace not found.
        """
        if trace_id not in self._traces:
            raise ValueError(f"Reasoning trace not found: {trace_id}")

        if trace_id not in self._evidence_pool:
            self._evidence_pool[trace_id] = []

        # Check for duplicates by evidence_id
        existing_ids = {ev.evidence_id for ev in self._evidence_pool[trace_id]}
        if evidence.evidence_id not in existing_ids:
            self._evidence_pool[trace_id].append(evidence)
            logger.debug(
                f"Added evidence {evidence.evidence_id[:8]}... to trace {trace_id[:8]}..."
            )
        else:
            logger.debug(
                f"Evidence {evidence.evidence_id[:8]}... already in pool for trace {trace_id[:8]}..."
            )

        return evidence

    async def get_evidence_pool(self, trace_id: str) -> List[Evidence]:
        """Get all evidence accumulated for a trace.

        Returns all evidence items in the pool for the given trace,
        including evidence from individual steps and directly added evidence.

        Args:
            trace_id: Target trace ID.

        Returns:
            List of Evidence items in the pool.

        Raises:
            ValueError: If trace not found.
        """
        if trace_id not in self._traces:
            raise ValueError(f"Reasoning trace not found: {trace_id}")

        evidence_list = self._evidence_pool.get(trace_id, [])
        logger.debug(
            f"Retrieved {len(evidence_list)} evidence items for trace {trace_id[:8]}..."
        )
        return evidence_list

    def get_active_traces(self) -> List[ReasoningTrace]:
        """Get all active (non-concluded) traces.

        Returns:
            List of ReasoningTrace with ACTIVE status.
        """
        active = [
            trace for trace in self._traces.values()
            if trace.status == ReasoningStatus.ACTIVE
        ]
        logger.debug(f"Found {len(active)} active traces")
        return active

    def get_all_traces(self) -> List[ReasoningTrace]:
        """Get all traces regardless of status.

        Returns:
            List of all ReasoningTrace objects.
        """
        return list(self._traces.values())

    def cleanup_trace(self, trace_id: str) -> bool:
        """Remove a trace and its evidence pool from memory.

        This is useful for freeing memory after a trace is no longer needed.
        Only concluded or abandoned traces can be cleaned up.

        Args:
            trace_id: Trace to clean up.

        Returns:
            True if trace was removed, False if not found or still active.
        """
        trace = self._traces.get(trace_id)
        if not trace:
            logger.debug(f"Trace not found for cleanup: {trace_id}")
            return False

        if trace.status == ReasoningStatus.ACTIVE:
            logger.warning(f"Cannot cleanup active trace: {trace_id}")
            return False

        del self._traces[trace_id]
        if trace_id in self._evidence_pool:
            del self._evidence_pool[trace_id]

        logger.debug(f"Cleaned up trace {trace_id[:8]}...")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics.

        Returns:
            Dictionary with:
            - total_traces: Total number of traces
            - by_status: Count of traces by status
            - total_evidence: Total evidence items across all pools
            - avg_steps: Average number of steps per concluded trace
            - avg_confidence: Average final confidence of concluded traces
        """
        stats: Dict[str, Any] = {
            "total_traces": len(self._traces),
            "by_status": {},
            "total_evidence": sum(len(pool) for pool in self._evidence_pool.values()),
            "avg_steps": 0.0,
            "avg_confidence": 0.0,
        }

        # Count by status
        for trace in self._traces.values():
            status = trace.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # Calculate averages for concluded traces
        concluded_traces = [
            t for t in self._traces.values()
            if t.status == ReasoningStatus.CONCLUDED
        ]

        if concluded_traces:
            total_steps = sum(len(t.steps) for t in concluded_traces)
            stats["avg_steps"] = total_steps / len(concluded_traces)

            confidences = [
                t.final_confidence for t in concluded_traces
                if t.final_confidence is not None
            ]
            if confidences:
                stats["avg_confidence"] = sum(confidences) / len(confidences)

        logger.debug(f"Stats: {stats}")
        return stats


# Global singleton
reasoning_service = ReasoningService()
