from datetime import datetime, timezone

from backend.event_generator import _analysis_payload, _event_payload
from backend.aws_services import AwsPublisher
from anomaly_engine.models import AnalysisResult, LogWindow, Severity, Signal
from log_ingestion.models import LogEvent


def test_raw_event_keeps_dashboard_contract() -> None:
    payload = _event_payload(
        LogEvent(datetime.now(timezone.utc), "ERROR", 500, 120.0, "api", "Database timeout")
    )
    assert payload["type"] == "event"
    assert {"timestamp", "level", "service", "message", "error_rate", "baseline", "deviation", "severity", "is_anomaly"} <= payload.keys()


def test_analysis_payload_contains_engine_result_and_metrics() -> None:
    window = LogWindow(total_requests=100, error_count=20, server_error_count=10, avg_latency_ms=250.0)
    result = AnalysisResult(
        anomaly=True,
        score=0.9,
        severity=Severity.CRITICAL,
        signals=[Signal.ERROR_RATE_SPIKE],
        statistical_score=0.95,
        ml_score=0.82,
    )
    payload = _analysis_payload(window, result)
    assert payload["type"] == "analysis"
    assert payload["analysis"]["severity"] == "CRITICAL"
    assert payload["metrics"]["five_xx_rate"] == 0.1


def test_aws_without_clients_is_a_noop() -> None:
    publisher = AwsPublisher("ap-south-1", "/group", "stream", "SignalWatch", None)
    publisher.logs = None
    publisher.cloudwatch = None
    publisher.sns = None
    window = LogWindow(total_requests=1, error_count=0, avg_latency_ms=1.0)
    result = AnalysisResult(anomaly=False, score=0.0, severity=Severity.NORMAL)
    publisher.publish(result, window)
