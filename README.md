# Douyin Live Data Analytics System (MVP)

This project provides:

- Collector -> Kafka raw events
- Flink real-time metrics -> Kafka topic `live_metrics`
- Flask backend APIs (including realtime snapshot/SSE)
- ECharts frontend dashboard (supports realtime mode)

## 1. Structure

```text
.
|- infra/
|- services/
|  |- collector/
|  |- flink_job/
|  |- spark_job/
|- apps/
|  |- backend/
|  |- frontend/
|- tests/
|- docs/
```

## 2. Quick Start

```powershell
cd D:\lzy毕设
py -3.11 -m venv .venv311
& ".\.venv311\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv311\Scripts\python.exe" -m pip install -r requirements-core.txt
```

Run backend:

```powershell
& ".\.venv311\Scripts\python.exe" ".\apps\backend\run.py"
```

Open: `http://127.0.0.1:5000`

## 3. Start Infra

```powershell
cd D:\lzy毕设\infra
docker compose up -d
```

## 4. Run Realtime Pipeline

Run collector:

```powershell
cd D:\lzy毕设
& ".\.venv311\Scripts\python.exe" ".\services\collector\collector.py" --bootstrap localhost:9092 --topic live_events --live-id live_001 --interval 1
```

Run Flink job:

```powershell
cd D:\lzy毕设
& ".\.venv311\Scripts\python.exe" ".\services\flink_job\realtime_metrics.py" --bootstrap localhost:9092 --topic live_events --metrics-topic live_metrics
```

Frontend realtime mode:

- Open dashboard
- Click `开启实时`

## 5. Optional: Spark Offline Job

```powershell
cd D:\lzy毕设
& ".\.venv311\Scripts\python.exe" ".\services\spark_job\offline_metrics.py" --input data\raw_events.jsonl --output data\dws
```
