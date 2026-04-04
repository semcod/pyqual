"""Callback protocols for pipeline events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pyqual.pipeline_results import StageResult, IterationResult


@runtime_checkable
class OnStageStart(Protocol):
    def __call__(self, name: str) -> None: ...


@runtime_checkable
class OnIterationStart(Protocol):
    def __call__(self, iteration: int) -> None: ...


@runtime_checkable
class OnStageError(Protocol):
    def __call__(self, failure: Any) -> None: ...


@runtime_checkable
class OnStageDone(Protocol):
    """Called after each stage completes. Receives the full StageResult."""

    def __call__(self, result: StageResult) -> None: ...


@runtime_checkable
class OnStageOutput(Protocol):
    """Called with each line of streaming output from a stage."""

    def __call__(self, stage_name: str, stream: str, line: str) -> None: ...


@runtime_checkable
class OnIterationDone(Protocol):
    """Called after each iteration completes. Receives the full IterationResult."""

    def __call__(self, result: IterationResult) -> None: ...
