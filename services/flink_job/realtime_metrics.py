import argparse
from pathlib import Path

from pyflink.table import EnvironmentSettings, TableEnvironment


def _configure_pipeline_jars(t_env: TableEnvironment, jars_arg: str):
    jar_uris = []

    if jars_arg:
        for raw in jars_arg.split(","):
            item = raw.strip()
            if not item:
                continue
            if item.startswith("file:/"):
                jar_uris.append(item)
            else:
                jar_uris.append(Path(item).resolve().as_uri())

    jar_dir = Path(__file__).resolve().parent / "jars"
    for name in [
        "flink-sql-connector-kafka-3.3.0-1.20.jar",
        "flink-json-1.20.3.jar",
    ]:
        p = jar_dir / name
        if p.exists():
            jar_uris.append(p.resolve().as_uri())

    if jar_uris:
        # Flink expects a semicolon-separated list.
        merged = ";".join(dict.fromkeys(jar_uris))
        t_env.get_config().set("pipeline.jars", merged)
        print(f"[flink] pipeline.jars={merged}")
    else:
        print("[flink] warning: no connector jars configured; kafka connector may be unavailable.")


def build_job(
    bootstrap: str,
    topic: str,
    metrics_topic: str,
    jars: str,
    window_seconds: int,
):
    settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(settings)
    _configure_pipeline_jars(t_env, jars)

    t_env.execute_sql(
        f"""
        CREATE TABLE live_events (
          event_time STRING,
          live_id STRING,
          user_id STRING,
          event_type STRING,
          online_users INT,
          like_count INT,
          gift_value DOUBLE,
          product_id STRING,
          product_action STRING,
          `comment` STRING,
          proc_time AS PROCTIME()
        ) WITH (
          'connector' = 'kafka',
          'topic' = '{topic}',
          'properties.bootstrap.servers' = '{bootstrap}',
          'properties.group.id' = 'douyin-live-flink',
          'scan.startup.mode' = 'earliest-offset',
          'format' = 'json',
          'json.ignore-parse-errors' = 'true'
        )
        """
    )

    t_env.execute_sql(
        f"""
        CREATE TABLE realtime_metrics (
          window_start STRING,
          window_end STRING,
          live_id STRING,
          avg_online_users DOUBLE,
          like_events BIGINT,
          gift_events BIGINT,
          gift_value_sum DOUBLE,
          interaction_events BIGINT
        ) WITH (
          'connector' = 'kafka',
          'topic' = '{metrics_topic}',
          'properties.bootstrap.servers' = '{bootstrap}',
          'format' = 'json'
        )
        """
    )

    stmt = f"""
    INSERT INTO realtime_metrics
    SELECT
      CAST(window_start AS STRING),
      CAST(window_end AS STRING),
      live_id,
      AVG(CAST(online_users AS DOUBLE)) AS avg_online_users,
      SUM(CASE WHEN event_type='like' THEN 1 ELSE 0 END) AS like_events,
      SUM(CASE WHEN event_type='gift' THEN 1 ELSE 0 END) AS gift_events,
      SUM(gift_value) AS gift_value_sum,
      COUNT(*) AS interaction_events
    FROM TABLE(
      TUMBLE(TABLE live_events, DESCRIPTOR(proc_time), INTERVAL '{window_seconds}' SECOND)
    )
    GROUP BY live_id, window_start, window_end
    """
    t_env.execute_sql(stmt).wait()


def main():
    parser = argparse.ArgumentParser(description="PyFlink realtime metrics job")
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="live_events")
    parser.add_argument("--metrics-topic", default="live_metrics")
    parser.add_argument(
        "--output",
        default="",
        help="Deprecated. Kept for backward compatibility; ignored.",
    )
    parser.add_argument(
        "--jars",
        default="",
        help="Comma-separated jar paths or file:// URIs for Flink connectors.",
    )
    parser.add_argument("--window-seconds", type=int, default=10)
    args = parser.parse_args()
    build_job(
        args.bootstrap,
        args.topic,
        args.metrics_topic,
        args.jars,
        max(5, args.window_seconds),
    )


if __name__ == "__main__":
    main()
