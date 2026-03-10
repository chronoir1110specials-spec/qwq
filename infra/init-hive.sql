CREATE DATABASE IF NOT EXISTS douyin_live;

USE douyin_live;

CREATE TABLE IF NOT EXISTS ods_live_events (
  event_time STRING,
  live_id STRING,
  user_id STRING,
  event_type STRING,
  online_users INT,
  like_count INT,
  gift_value DOUBLE,
  product_id STRING,
  product_action STRING,
  comment STRING
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS dwd_live_events_cleaned (
  event_time TIMESTAMP,
  live_id STRING,
  user_id STRING,
  event_type STRING,
  online_users INT,
  like_count INT,
  gift_value DOUBLE,
  product_id STRING,
  product_action STRING,
  comment STRING
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS dws_live_metrics (
  metric_time TIMESTAMP,
  live_id STRING,
  avg_online_users DOUBLE,
  total_likes BIGINT,
  total_gift_value DOUBLE,
  interaction_count BIGINT
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET;
