"""Collector entrypoint for simulated, official push, and web-live adapters."""

import argparse

from collector_common import EventPublisher
from collector_official_push import run_official_push_server
from collector_simulated import run_simulated
from collector_web_live import run_web_live


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Douyin live interaction event adapter (simulate + official-push + web-live)"
    )
    parser.add_argument(
        "--mode",
        choices=["simulate", "official-push", "web-live"],
        default="simulate",
        help="simulate: local demo events, official-push: webhook receiver skeleton, web-live: web websocket adapter",
    )
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="live_events")
    parser.add_argument("--live-id", default="live_001")
    parser.add_argument(
        "--web-rid",
        default="",
        help="Douyin web live room id from https://live.douyin.com/<web_rid>",
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--config",
        default="",
        help="Optional YAML config path for official push room bindings",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--webhook-path", default="/webhook/douyin/live")
    parser.add_argument(
        "--web-source-dir",
        default="",
        help="Optional path to the Tiktok-live source directory used by web-live mode",
    )
    parser.add_argument(
        "--verification-token",
        default="",
        help="Optional shared token expected in X-Collector-Token or ?token=",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    publisher = EventPublisher(args.bootstrap, args.topic)
    try:
        if args.mode == "simulate":
            run_simulated(
                publisher=publisher,
                live_id=args.live_id,
                interval=args.interval,
                seed=args.seed,
            )
            return

        if args.mode == "web-live":
            web_rid = args.web_rid or args.live_id
            run_web_live(
                publisher=publisher,
                live_id=args.live_id,
                web_rid=web_rid,
                source_dir=args.web_source_dir,
            )
            return

        run_official_push_server(
            publisher=publisher,
            config_path=args.config,
            fallback_live_id=args.live_id,
            host=args.host,
            port=args.port,
            webhook_path=args.webhook_path,
            verification_token=args.verification_token,
        )
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
