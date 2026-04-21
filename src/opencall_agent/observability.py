"""OpenTelemetry tracing + PII scrubbing for the agent layer.

- `configure_tracing` wires a global TracerProvider with a ConsoleSpanExporter
  by default. Tests swap in an `InMemorySpanExporter` to assert shape.
- `scrub` masks CPF / email / phone before emission; applied to any span
  attribute that carries user or document text.

Kept minimal on purpose: one span per node plus one span for each external
call (embed/search/complete). Hosted exporters (Langfuse, Jaeger) are a
configuration change, not a code change.
"""

from __future__ import annotations

import re
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)

_TRACER_NAME = "opencall_agent"

_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(
    r"(?:\+?55[\s-]?)?(?:\(\d{2}\)|\d{2})[\s-]?9?\d{4}[-\s]?\d{4}"
)


def scrub(text: str) -> str:
    """Mask CPF / email / phone. Safe to call on any string."""
    if not text:
        return text
    text = _CPF_RE.sub("[CPF]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    return text


def configure_tracing(exporter: SpanExporter | None = None) -> TracerProvider:
    """Ensure the global TracerProvider exists and attach an exporter.

    OTEL ignores repeated `set_tracer_provider` calls, so we install once and
    then just hang additional SpanProcessors off the existing provider. That
    lets tests inject an `InMemorySpanExporter` without fighting the global.
    """
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        provider = current
    else:
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter or ConsoleSpanExporter()))
    return provider


def get_tracer() -> trace.Tracer:
    current = trace.get_tracer_provider()
    if not isinstance(current, TracerProvider):
        configure_tracing()
    return trace.get_tracer(_TRACER_NAME)


def set_attr(span: trace.Span, key: str, value: Any) -> None:
    """Set a span attribute, scrubbing strings before emission."""
    if isinstance(value, str):
        value = scrub(value)
    span.set_attribute(key, value)
