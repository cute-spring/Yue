#!/usr/bin/env python3
import argparse
import os
from datetime import datetime
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed chat sessions for timezone-boundary real E2E test."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="YUE_DATA_DIR used by backend server and this seed script.",
    )
    parser.add_argument(
        "--scenario",
        default="cross_midnight",
        choices=[
            "cross_midnight",
            "new_chat_base",
            "append_today_new_chat",
            "expand_collapse",
            "date_presets",
            "tag_filter_search",
        ],
        help="Seed scenario name.",
    )
    return parser.parse_args()


def _clear_all(db, session_model, message_model) -> None:
    db.query(message_model).delete()
    db.query(session_model).delete()
    db.commit()


def _seed_sessions(
    *,
    service,
    SessionLocal,
    SessionModel,
    seeds: List[Dict[str, object]],
) -> None:
    for seed in seeds:
        session = service.create_chat(agent_id="default")
        service.add_message(session.id, "user", f"Seed message for {seed['title']}")
        with SessionLocal() as db:
            row = db.query(SessionModel).filter(SessionModel.id == session.id).first()
            if row is None:
                raise RuntimeError(f"Cannot find seeded session: {session.id}")
            row.title = str(seed["title"])
            row.summary = "Real E2E timezone seed"
            row.created_at = seed["updated_at"]
            row.updated_at = seed["updated_at"]
            row.tags_json = seed.get("tags_json", "[]")
            db.commit()


def main() -> int:
    args = parse_args()
    os.environ["YUE_DATA_DIR"] = args.data_dir

    from app.core.database import SessionLocal
    from app.models.chat import Message as MessageModel
    from app.models.chat import Session as SessionModel
    from app.services.chat_service import ChatService

    service = ChatService()

    if args.scenario != "append_today_new_chat":
        with SessionLocal() as db:
            _clear_all(db, SessionModel, MessageModel)

    if args.scenario == "cross_midnight":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {
                    "title": "Timezone Today Session",
                    # Naive UTC; in Asia/Shanghai this is 2026-04-11 00:30.
                    "updated_at": datetime(2026, 4, 10, 16, 30, 0),
                },
                {
                    "title": "Timezone Yesterday Session",
                    # Naive UTC; in Asia/Shanghai this is 2026-04-10 23:30.
                    "updated_at": datetime(2026, 4, 10, 15, 30, 0),
                },
            ],
        )
    elif args.scenario == "new_chat_base":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {
                    "title": "Existing Yesterday Session",
                    # Local 2026-04-10 20:00 @ Asia/Shanghai
                    "updated_at": datetime(2026, 4, 10, 12, 0, 0),
                }
            ],
        )
    elif args.scenario == "append_today_new_chat":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {
                    "title": "Fresh Today Session",
                    # Local 2026-04-11 00:20 @ Asia/Shanghai
                    "updated_at": datetime(2026, 4, 10, 16, 20, 0),
                }
            ],
        )
    elif args.scenario == "expand_collapse":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {
                    "title": "Today Expanded Session",
                    "updated_at": datetime(2026, 4, 11, 1, 0, 0),  # local 4/11
                },
                {
                    "title": "Yesterday A",
                    "updated_at": datetime(2026, 4, 10, 3, 0, 0),  # local 4/10
                },
                {
                    "title": "Yesterday B",
                    "updated_at": datetime(2026, 4, 10, 4, 0, 0),  # local 4/10
                },
                {
                    "title": "TwoDaysAgo",
                    "updated_at": datetime(2026, 4, 9, 4, 0, 0),  # local 4/9
                },
            ],
        )
    elif args.scenario == "date_presets":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {"title": "Preset Today", "updated_at": datetime(2026, 4, 11, 1, 0, 0)},  # local 4/11
                {"title": "Preset D-6", "updated_at": datetime(2026, 4, 5, 4, 0, 0)},   # local 4/5
                {"title": "Preset D-7", "updated_at": datetime(2026, 4, 4, 4, 0, 0)},   # local 4/4
                {"title": "Preset D-29", "updated_at": datetime(2026, 3, 13, 4, 0, 0)}, # local 3/13
                {"title": "Preset D-30", "updated_at": datetime(2026, 3, 12, 4, 0, 0)}, # local 3/12
            ],
        )
    elif args.scenario == "tag_filter_search":
        _seed_sessions(
            service=service,
            SessionLocal=SessionLocal,
            SessionModel=SessionModel,
            seeds=[
                {
                    "title": "Tag Today API",
                    "updated_at": datetime(2026, 4, 11, 1, 0, 0),  # local 4/11
                    "tags_json": '["api","urgent"]',
                },
                {
                    "title": "Tag Yesterday API",
                    "updated_at": datetime(2026, 4, 10, 3, 0, 0),  # local 4/10
                    "tags_json": '["api","backend"]',
                },
                {
                    "title": "Tag Yesterday Design",
                    "updated_at": datetime(2026, 4, 10, 4, 0, 0),  # local 4/10
                    "tags_json": '["design","frontend"]',
                },
            ],
        )
    else:
        raise ValueError(f"Unsupported scenario: {args.scenario}")

    print(f"Seeded timezone E2E data into: {args.data_dir} (scenario={args.scenario})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
