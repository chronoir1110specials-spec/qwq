# System Architecture Notes

## Data Flow

1. Collector captures public live data events.
2. Events are published to Kafka topic `live_events`.
3. Flink consumes Kafka stream and computes near real-time indicators:
   - online users
   - gift frequency
   - interaction frequency
4. Spark runs periodic offline jobs:
   - user watch duration
   - conversion-related aggregates
5. Hive stores layered warehouse data:
   - ODS raw events
   - DWD cleaned detail
   - DWS aggregated subject metrics
6. Flask API serves business indicators to frontend dashboard.

## Core Modules

- Data collection: `services/collector`
- Stream compute: `services/flink_job`
- Batch compute: `services/spark_job`
- API service: `apps/backend`
- Visualization: `apps/frontend`
