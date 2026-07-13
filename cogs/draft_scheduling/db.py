import json
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional

from asyncpg import Pool

log: logging.Logger = logging.getLogger(__name__)


@dataclass
class DraftSession:
    id: int
    guild_id: int
    channel_id: int
    announcement_message_id: Optional[int]
    organizer_id: int
    role_id: int
    name: str
    candidate_days: List[date]
    hour_start: int
    hour_end: int
    deadline: datetime  # naive UTC
    status: str
    reminder_stage: int
    day_of_reminder_sent: bool
    picked_slot: Optional[datetime]  # naive UTC
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> 'DraftSession':
        return cls(
            id=row['id'],
            guild_id=row['guild_id'],
            channel_id=row['channel_id'],
            announcement_message_id=row['announcement_message_id'],
            organizer_id=row['organizer_id'],
            role_id=row['role_id'],
            name=row['name'],
            candidate_days=[date.fromisoformat(s) for s in row['candidate_days'].split(',') if s],
            hour_start=row['hour_start'],
            hour_end=row['hour_end'],
            deadline=row['deadline'],
            status=row['status'],
            reminder_stage=row['reminder_stage'],
            day_of_reminder_sent=row['day_of_reminder_sent'],
            picked_slot=row['picked_slot'],
            created_at=row['created_at'],
        )


@dataclass
class DraftResponse:
    id: int
    session_id: int
    user_id: int
    is_out: bool
    availability: Dict[str, List[int]]  # {"2026-07-17": [18, 19], ...}
    note: Optional[str]
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> 'DraftResponse':
        return cls(
            id=row['id'],
            session_id=row['session_id'],
            user_id=row['user_id'],
            is_out=row['is_out'],
            availability=json.loads(row['availability'] or '{}'),
            note=row['note'],
            updated_at=row['updated_at'],
        )


class DraftSchedulingDb:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def create_session(self, guild_id: int, channel_id: int, organizer_id: int, role_id: int,
                             name: str, candidate_days: List[date], hour_start: int,
                             hour_end: int, deadline: datetime) -> int:
        query = """
            INSERT INTO draft_sessions
                (guild_id, channel_id, organizer_id, role_id, name, candidate_days, hour_start, hour_end, deadline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        days_str = ','.join(d.isoformat() for d in candidate_days)
        return await self.pool.fetchval(query, guild_id, channel_id, organizer_id, role_id,
                                        name, days_str, hour_start, hour_end, deadline)

    async def set_announcement_message(self, session_id: int, message_id: int):
        await self.pool.execute(
            "UPDATE draft_sessions SET announcement_message_id = $2 WHERE id = $1",
            session_id, message_id)

    async def get_session(self, session_id: int) -> Optional[DraftSession]:
        row = await self.pool.fetchrow("SELECT * FROM draft_sessions WHERE id = $1", session_id)
        return DraftSession.from_row(row) if row else None

    async def get_sessions_by_status(self, statuses: List[str]) -> List[DraftSession]:
        rows = await self.pool.fetch(
            "SELECT * FROM draft_sessions WHERE status = ANY($1::text[]) ORDER BY id", statuses)
        return [DraftSession.from_row(r) for r in rows]

    async def get_sessions_in_channel(self, guild_id: int, channel_id: int,
                                      statuses: List[str]) -> List[DraftSession]:
        rows = await self.pool.fetch(
            """SELECT * FROM draft_sessions
               WHERE guild_id = $1 AND channel_id = $2 AND status = ANY($3::text[])
               ORDER BY id DESC""",
            guild_id, channel_id, statuses)
        return [DraftSession.from_row(r) for r in rows]

    async def set_status(self, session_id: int, status: str):
        await self.pool.execute("UPDATE draft_sessions SET status = $2 WHERE id = $1", session_id, status)

    async def set_reminder_stage(self, session_id: int, stage: int):
        await self.pool.execute("UPDATE draft_sessions SET reminder_stage = $2 WHERE id = $1", session_id, stage)

    async def set_picked(self, session_id: int, picked_slot_utc: datetime):
        await self.pool.execute(
            "UPDATE draft_sessions SET status = 'decided', picked_slot = $2 WHERE id = $1",
            session_id, picked_slot_utc)

    async def set_day_of_reminder_sent(self, session_id: int):
        await self.pool.execute(
            "UPDATE draft_sessions SET day_of_reminder_sent = TRUE WHERE id = $1", session_id)

    async def get_response(self, session_id: int, user_id: int) -> Optional[DraftResponse]:
        row = await self.pool.fetchrow(
            "SELECT * FROM draft_responses WHERE session_id = $1 AND user_id = $2",
            session_id, user_id)
        return DraftResponse.from_row(row) if row else None

    async def get_responses(self, session_id: int) -> List[DraftResponse]:
        rows = await self.pool.fetch(
            "SELECT * FROM draft_responses WHERE session_id = $1 ORDER BY updated_at", session_id)
        return [DraftResponse.from_row(r) for r in rows]

    async def upsert_availability(self, session_id: int, user_id: int,
                                  availability: Dict[str, List[int]], note: Optional[str]):
        query = """
            INSERT INTO draft_responses (session_id, user_id, is_out, availability, note, updated_at)
            VALUES ($1, $2, FALSE, $3, $4, NOW())
            ON CONFLICT (session_id, user_id) DO UPDATE
            SET is_out = FALSE, availability = $3, note = $4, updated_at = NOW()
        """
        await self.pool.execute(query, session_id, user_id, json.dumps(availability), note)

    async def upsert_out(self, session_id: int, user_id: int):
        query = """
            INSERT INTO draft_responses (session_id, user_id, is_out, availability, updated_at)
            VALUES ($1, $2, TRUE, '{}', NOW())
            ON CONFLICT (session_id, user_id) DO UPDATE
            SET is_out = TRUE, availability = '{}', updated_at = NOW()
        """
        await self.pool.execute(query, session_id, user_id)
