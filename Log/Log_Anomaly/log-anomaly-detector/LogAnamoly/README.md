# Log_Anomaly
Monitoring systems need to identify abnormal behavior quickly before it becomes a major issue. Log streams can contain increasing error rates or unusual activity that needs to be detected and reported immediately.

## Log ingestion

The `log_ingestion` package generates synthetic request logs, follows an append-only log file, parses lines into `LogEvent` objects, and emits populated 60-second windows every 10 seconds. It does not implement anomaly detection.

Run the generator from this directory:

```powershell
python -m log_generator --rate 10 --scenario normal --path app.log
```

Available scenarios are `normal`, `error_spike`, `latency_spike`, `traffic_spike`, and `database_failure`. The generator can also change scenarios while running through `LogGenerator.set_scenario()`.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

The anomaly-engine package and its `LogWindow` model are not present in this repository. `SlidingWindow` lazily imports `anomaly_engine.models.LogWindow` when it emits a populated window, using the keyword fields specified in the integration contract. The constructor can be injected in tests or adapted at integration time if the engine's actual constructor differs.
