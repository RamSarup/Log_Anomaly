from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.models import LogWindow

engine = AnomalyEngine.default()

normal = LogWindow(total_requests=1000, error_count=10,
                   server_error_count=2, avg_latency_ms=200)
incident = LogWindow(total_requests=1000, error_count=120,
                     server_error_count=80, avg_latency_ms=2200)

print("NORMAL  :", engine.analyze(normal).model_dump(mode="json"))
print("INCIDENT:", engine.analyze(incident).model_dump(mode="json"))