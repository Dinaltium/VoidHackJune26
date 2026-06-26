"""SQLite persistence for receipts, events, and per-session token usage.

Synchronous SQLAlchemy 2.0 core/ORM; calls are cheap (local file) and wrapped
in a threadpool by the async layer where needed.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .schemas import Event, Receipt


class Base(DeclarativeBase):
    pass


class ReceiptRow(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)
    data: Mapped[str] = mapped_column(Text)  # full Receipt JSON


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)
    data: Mapped[str] = mapped_column(Text)


class UsageRow(Base):
    __tablename__ = "usage"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tokens: Mapped[int] = mapped_column(default=0)


class Store:
    def __init__(self, db_path: str | Path) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(self.engine)

    # ---- receipts ----
    def save_receipt(self, receipt: Receipt) -> None:
        with Session(self.engine) as s:
            s.merge(
                ReceiptRow(
                    id=receipt.id,
                    ts=receipt.ts,
                    session_id=receipt.session_id,
                    action=receipt.decision.action.value,
                    data=receipt.model_dump_json(),
                )
            )
            s.commit()

    def get_receipt(self, receipt_id: str) -> Receipt | None:
        with Session(self.engine) as s:
            row = s.get(ReceiptRow, receipt_id)
            return Receipt.model_validate_json(row.data) if row else None

    def list_receipts(self, limit: int = 50) -> list[Receipt]:
        with Session(self.engine) as s:
            rows = s.scalars(
                select(ReceiptRow).order_by(ReceiptRow.ts.desc()).limit(limit)
            ).all()
            return [Receipt.model_validate_json(r.data) for r in rows]

    # ---- events ----
    def save_event(self, event: Event) -> None:
        with Session(self.engine) as s:
            s.merge(
                EventRow(
                    id=event.id,
                    ts=event.ts,
                    session_id=event.session_id,
                    action=event.action.value,
                    data=event.model_dump_json(),
                )
            )
            s.commit()

    def list_events(self, limit: int = 100) -> list[Event]:
        with Session(self.engine) as s:
            rows = s.scalars(
                select(EventRow).order_by(EventRow.ts.desc()).limit(limit)
            ).all()
            return [Event.model_validate_json(r.data) for r in rows]

    # ---- stats ----
    def stats(self) -> dict[str, int]:
        with Session(self.engine) as s:
            rows = s.execute(
                select(ReceiptRow.action, func.count()).group_by(ReceiptRow.action)
            ).all()
            out = {"allow": 0, "redact": 0, "block": 0}
            for action, count in rows:
                out[action] = int(count)
            out["total"] = sum(out.values())
            return out

    # ---- per-session token usage ----
    def add_usage(self, session_id: str, tokens: int) -> int:
        with Session(self.engine) as s:
            row = s.get(UsageRow, session_id)
            if row is None:
                row = UsageRow(session_id=session_id, tokens=0)
                s.add(row)
            row.tokens += tokens
            total = row.tokens
            s.commit()
            return total

    def get_usage(self, session_id: str) -> int:
        with Session(self.engine) as s:
            row = s.get(UsageRow, session_id)
            return row.tokens if row else 0

    def reset(self) -> None:
        """Wipe all tables (used by tests and the demo reset endpoint)."""
        with Session(self.engine) as s:
            for tbl in (ReceiptRow, EventRow, UsageRow):
                s.query(tbl).delete()
            s.commit()


def summarize_request(payload: dict) -> dict:
    """Compact, secret-free summary of a request for the receipt."""
    messages = payload.get("messages", []) or []
    tools = payload.get("tools", []) or []
    roles = [m.get("role") for m in messages]
    return {
        "model": payload.get("model"),
        "n_messages": len(messages),
        "roles": roles,
        "n_tools": len(tools),
        "tool_names": [t.get("function", {}).get("name") for t in tools][:20],
    }
