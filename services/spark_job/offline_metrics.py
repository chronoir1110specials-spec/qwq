import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    count,
    lead,
    lit,
    sum as fsum,
    to_timestamp,
    unix_timestamp,
)
from pyspark.sql.window import Window


def run_job(input_path: str, output_dir: str):
    spark = (
        SparkSession.builder.appName("douyin-live-offline-metrics")
        .master("local[*]")
        .getOrCreate()
    )

    raw = spark.read.json(input_path).withColumn("event_ts", to_timestamp(col("event_time")))

    interaction = (
        raw.groupBy("live_id")
        .agg(
            count(lit(1)).alias("event_count"),
            fsum(col("gift_value")).alias("gift_value_sum"),
        )
        .orderBy("live_id")
    )
    interaction.write.mode("overwrite").json(f"{output_dir}/interaction_summary")

    watch_events = raw.filter(col("event_type").isin(["enter", "leave"]))
    window_spec = Window.partitionBy("live_id", "user_id").orderBy("event_ts")

    paired = (
        watch_events.withColumn("next_event", lead("event_type").over(window_spec))
        .withColumn("next_ts", lead("event_ts").over(window_spec))
        .filter((col("event_type") == "enter") & (col("next_event") == "leave"))
        .withColumn("watch_seconds", unix_timestamp("next_ts") - unix_timestamp("event_ts"))
        .filter(col("watch_seconds") > 0)
    )

    watch_duration = (
        paired.groupBy("live_id", "user_id")
        .agg(fsum("watch_seconds").alias("watch_seconds"))
        .orderBy("live_id", "watch_seconds", ascending=False)
    )
    watch_duration.write.mode("overwrite").json(f"{output_dir}/user_watch_duration")

    spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Spark offline metrics")
    parser.add_argument("--input", default="data/raw_events.jsonl")
    parser.add_argument("--output", default="data/dws")
    args = parser.parse_args()
    run_job(args.input, args.output)


if __name__ == "__main__":
    main()
