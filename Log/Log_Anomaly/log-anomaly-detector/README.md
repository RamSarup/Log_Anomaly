# SignalWatch

Real-time log anomaly detection using the existing ingestion and anomaly-engine modules.

## Run

Install dependencies and start from the project root:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/dashboard`.

The FastAPI lifespan starts the existing synthetic generator, tails `logs/application.log`, parses new lines, emits raw events over `/ws`, and analyzes completed sliding windows. AWS output is optional and isolated from local processing.

## AWS configuration

Copy `.env.example` to `.env` and configure `AWS_REGION`, `CLOUDWATCH_LOG_GROUP`, `CLOUDWATCH_LOG_STREAM`, `CLOUDWATCH_NAMESPACE`, and optionally `SNS_TOPIC_ARN`. Do not place AWS access keys in source files. Boto3 uses its normal credential chain.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest detection/tests LogAnamoly/tests backend/tests -q
```
