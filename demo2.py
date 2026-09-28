from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.models import LogWindow
from anomaly_engine.persistence import PersistenceGate

engine = AnomalyEngine.default()
gate = PersistenceGate(required=3)

normal = LogWindow(total_requests=1000, error_count=10,
                   server_error_count=2, avg_latency_ms=200)
bad = LogWindow(total_requests=1000, error_count=120,
                server_error_count=80, avg_latency_ms=2200)

for name, w in [("normal", normal), ("bad", bad), ("bad", bad),
                ("bad", bad), ("normal", normal)]:
    r = engine.analyze(w)
    print(name, r.severity.value, "-> ALERT" if gate.update(r) else "-> quiet")