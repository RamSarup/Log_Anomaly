"""Failure-isolated AWS outputs for completed anomaly analyses."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "detection"))
load_dotenv(PROJECT_ROOT / ".env")

from detection.anomaly_engine.models import AnalysisResult, LogWindow, Severity

logger = logging.getLogger(__name__)

try:
	import boto3
except ImportError:
	boto3 = None


class AwsPublisher:
	def __init__(self, region: str, log_group: str, log_stream: str, namespace: str, topic_arn: str | None) -> None:
		self.topic_arn = topic_arn
		self.logs = None
		self.cloudwatch = None
		self.sns = None
		self._log_sequence_token: str | None = None
		if boto3 is not None:
			try:
				self.logs = boto3.client("logs", region_name=region)
				self.cloudwatch = boto3.client("cloudwatch", region_name=region)
				self.sns = boto3.client("sns", region_name=region)
			except Exception:
				logger.exception("AWS clients could not be initialized; continuing locally")
		self.log_group = log_group
		self.log_stream = log_stream
		self.namespace = namespace

	@classmethod
	def from_environment(cls) -> "AwsPublisher":
		return cls(
			region=os.getenv("AWS_REGION", "ap-south-1"),
			log_group=os.getenv("CLOUDWATCH_LOG_GROUP", "/signalwatch/anomalies"),
			log_stream=os.getenv("CLOUDWATCH_LOG_STREAM", "local-development"),
			namespace=os.getenv("CLOUDWATCH_NAMESPACE", "SignalWatch"),
			topic_arn=os.getenv("SNS_TOPIC_ARN") or None,
		)

	def publish(self, result: AnalysisResult, window: LogWindow) -> None:
		payload = self._payload(result, window)
		self._publish_logs(payload)
		self._publish_metrics(window, result)
		if result.severity == Severity.CRITICAL:
			self._publish_sns(payload)

	def _payload(self, result: AnalysisResult, window: LogWindow) -> dict:
		return {
			"timestamp": (window.window_end or datetime.now(timezone.utc)).isoformat(),
			"anomaly": result.anomaly,
			"severity": result.severity.value,
			"score": result.score,
			"statistical_score": result.statistical_score,
			"ml_score": result.ml_score,
			"signals": [signal.value for signal in result.signals],
			"metrics": {
				"total_requests": window.total_requests,
				"error_count": window.error_count,
				"server_error_count": window.server_error_count,
				"error_rate": window.error_rate,
				"five_xx_rate": window.five_xx_rate,
				"avg_latency_ms": window.avg_latency_ms,
			},
		}

	def _publish_logs(self, payload: dict) -> None:
		if self.logs is None:
			return
		try:
			try:
				self.logs.create_log_group(logGroupName=self.log_group)
			except self.logs.exceptions.ResourceAlreadyExistsException:
				pass
			try:
				self.logs.create_log_stream(logGroupName=self.log_group, logStreamName=self.log_stream)
			except self.logs.exceptions.ResourceAlreadyExistsException:
				pass
			streams = self.logs.describe_log_streams(
				logGroupName=self.log_group,
				logStreamNamePrefix=self.log_stream,
			)
			if streams.get("logStreams"):
				self._log_sequence_token = streams["logStreams"][0].get("uploadSequenceToken")
			request = {
				"logGroupName": self.log_group,
				"logStreamName": self.log_stream,
				"logEvents": [{"timestamp": int(datetime.now(timezone.utc).timestamp() * 1000), "message": json.dumps(payload)}],
			}
			if self._log_sequence_token:
				request["sequenceToken"] = self._log_sequence_token
			response = self.logs.put_log_events(**request)
			self._log_sequence_token = response.get("nextSequenceToken")
		except Exception as error:
			if error.__class__.__name__ == "NoCredentialsError":
				self.logs = None
				logger.warning("CloudWatch Logs disabled: AWS credentials are unavailable")
			else:
				logger.exception("CloudWatch Logs publishing failed")

	def _publish_metrics(self, window: LogWindow, result: AnalysisResult) -> None:
		if self.cloudwatch is None:
			return
		metrics = {
			"ErrorRate": (window.error_rate, "Percent"),
			"FiveXXRate": (window.five_xx_rate, "Percent"),
			"AverageLatency": (window.avg_latency_ms, "Milliseconds"),
			"AnomalyScore": (result.score, "None"),
			"RequestVolume": (float(window.total_requests), "Count"),
			"CriticalAnomalies": (1.0 if result.severity == Severity.CRITICAL else 0.0, "Count"),
		}
		try:
			self.cloudwatch.put_metric_data(
				Namespace=self.namespace,
				MetricData=[{"MetricName": name, "Value": value, "Unit": unit} for name, (value, unit) in metrics.items()],
			)
		except Exception as error:
			if error.__class__.__name__ == "NoCredentialsError":
				self.cloudwatch = None
				logger.warning("CloudWatch Metrics disabled: AWS credentials are unavailable")
			else:
				logger.exception("CloudWatch Metrics publishing failed")

	def _publish_sns(self, payload: dict) -> None:
		if self.sns is None or not self.topic_arn:
			return
		try:
			self.sns.publish(TopicArn=self.topic_arn, Subject="SignalWatch CRITICAL anomaly", Message=json.dumps(payload, indent=2))
		except Exception as error:
			if error.__class__.__name__ == "NoCredentialsError":
				self.sns = None
				logger.warning("SNS notifications disabled: AWS credentials are unavailable")
			else:
				logger.exception("SNS notification failed")