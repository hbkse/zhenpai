import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Set, Tuple

import discord
import pytz
from discord import app_commands
from discord.ext import commands, tasks

from bot import Zhenpai
from .constants import (
    DAY_OF_REMINDER_HOURS_BEFORE,
    DEFAULT_DEADLINE_HOURS,
    DEFAULT_HOUR_END,
    DEFAULT_HOUR_START,
    DRAFT_LENGTH_HOURS,
    DRAFT_TIMEZONE,
    DRAFT_TYPE_LABELS,
    FIRST_DM_HOURS,
    LAST_CALL_HOURS_BEFORE_DEADLINE,
    MAX_CANDIDATE_DAYS,
    MIN_PLAYERS,
    SECOND_DM_HOURS,
    WEEKDAYS,
    discord_timestamp,
    fmt_day,
    fmt_hour,
    local_slot_to_utc,
    utc_to_local,
)
from .db import DraftResponse, DraftSchedulingDb, DraftSession
from .views import AnnouncementView, OrganizerDecisionView

log: logging.Logger = logging.getLogger(__name__)

POLLING_INTERVAL_MINUTES = 5


class DraftScheduling(commands.Cog):
    """ Schedules weekly MTG drafts: collects availability, nags non-responders,
        auto-picks a slot when everyone who responded can make it, otherwise
        hands the decision to the organizer. """

    draft = app_commands.Group(name='draft', description='MTG draft scheduling')

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = DraftSchedulingDb(self.bot.db_pool)
        self.tick.start()

    async def cog_load(self):
        # Re-register persistent announcement buttons for sessions still collecting.
        sessions = await self.db.get_sessions_by_status(['collecting'])
        for session in sessions:
            if session.announcement_message_id:
                self.bot.add_view(AnnouncementView(self, session.id),
                                  message_id=session.announcement_message_id)
        if sessions:
            log.info('Re-registered announcement views for %d active draft sessions', len(sessions))

    def cog_unload(self):
        self.tick.cancel()

    # ---------- commands ----------

    @draft.command(name='schedule', description='Kick off scheduling for a draft')
    @app_commands.describe(
        role='Role to ping for this draft',
        days='Comma-separated days, e.g. fri,sat,sun (max 4). Uses the next upcoming occurrence of each.',
        draft_type='In person or online (default: in person)',
        deadline_hours='How long to collect availability before deciding (default 72h)',
        hour_start='Earliest selectable start time, 24h clock (default 12 = noon)',
        hour_end='Latest selectable start time, 24h clock (default 22 = 10 PM)',
    )
    @app_commands.choices(draft_type=[
        app_commands.Choice(name='In person', value='in_person'),
        app_commands.Choice(name='Online', value='online'),
    ])
    async def schedule(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        days: str,
        draft_type: Optional[app_commands.Choice[str]] = None,
        deadline_hours: Optional[app_commands.Range[int, 1, 336]] = None,
        hour_start: Optional[app_commands.Range[int, 0, 23]] = None,
        hour_end: Optional[app_commands.Range[int, 0, 23]] = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message('This only works in a server.', ephemeral=True)
            return

        candidate_days = self._parse_days(days)
        if candidate_days is None:
            await interaction.response.send_message(
                "I couldn't parse those days. Use comma-separated day names, e.g. `fri,sat,sun`.",
                ephemeral=True)
            return
        if len(candidate_days) > MAX_CANDIDATE_DAYS:
            await interaction.response.send_message(
                f'Max {MAX_CANDIDATE_DAYS} candidate days (Discord component limits).', ephemeral=True)
            return

        h_start = hour_start if hour_start is not None else DEFAULT_HOUR_START
        h_end = hour_end if hour_end is not None else DEFAULT_HOUR_END
        if h_end < h_start:
            await interaction.response.send_message('hour_end must be >= hour_start.', ephemeral=True)
            return

        dtype = draft_type.value if draft_type else 'in_person'

        now_utc = datetime.utcnow()
        deadline = now_utc + timedelta(hours=deadline_hours or DEFAULT_DEADLINE_HOURS)
        # Don't let the deadline land after the earliest possible draft slot.
        earliest_slot_utc = local_slot_to_utc(min(candidate_days), h_start)
        latest_sane_deadline = earliest_slot_utc - timedelta(hours=3)
        if deadline > latest_sane_deadline:
            deadline = max(latest_sane_deadline, now_utc + timedelta(hours=1))

        await interaction.response.defer(ephemeral=True)

        session_id = await self.db.create_session(
            interaction.guild.id, interaction.channel.id, interaction.user.id, role.id,
            dtype, candidate_days, h_start, h_end, deadline)
        session = await self.db.get_session(session_id)

        embed = self._announcement_embed(session, [])
        view = AnnouncementView(self, session_id)
        message = await interaction.channel.send(
            content=f'{role.mention} time to schedule a draft!',
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await self.db.set_announcement_message(session_id, message.id)
        self.bot.add_view(view, message_id=message.id)

        await interaction.followup.send(
            f'Draft scheduling kicked off (session #{session_id}). '
            f'Deciding {discord_timestamp(deadline, "R")}.', ephemeral=True)

    @draft.command(name='status', description='Show current availability for the latest draft in this channel')
    async def status(self, interaction: discord.Interaction):
        session = await self.db.get_latest_session_in_channel(
            interaction.guild.id, interaction.channel.id)
        if not session:
            await interaction.response.send_message('No draft sessions in this channel yet.', ephemeral=True)
            return
        responses = await self.db.get_responses(session.id)
        embed = self._grid_embed(session, responses)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @draft.command(name='pick', description='(Organizer) Manually lock in a slot for the latest draft in this channel')
    @app_commands.describe(day='One of the candidate days, e.g. fri', hour='Start hour, 24h clock, e.g. 20')
    async def pick(self, interaction: discord.Interaction, day: str,
                   hour: app_commands.Range[int, 0, 23]):
        session = await self.db.get_latest_session_in_channel(
            interaction.guild.id, interaction.channel.id, ['collecting', 'needs_organizer'])
        if not session:
            await interaction.response.send_message('No active draft session in this channel.', ephemeral=True)
            return
        if not self._can_manage(interaction, session):
            await interaction.response.send_message('Only the organizer (or a server manager) can do that.', ephemeral=True)
            return

        matched = self._match_candidate_day(session, day)
        if not matched:
            options = ', '.join(fmt_day(d) for d in session.candidate_days)
            await interaction.response.send_message(
                f"That doesn't match a candidate day. Options: {options}", ephemeral=True)
            return

        await interaction.response.send_message(
            f'Locking in **{fmt_day(matched)} {fmt_hour(hour)}**.', ephemeral=True)
        await self.finalize(session, matched.isoformat(), hour, auto=False)

    @draft.command(name='cancel', description='(Organizer) Cancel the latest active draft in this channel')
    async def cancel(self, interaction: discord.Interaction):
        session = await self.db.get_latest_session_in_channel(
            interaction.guild.id, interaction.channel.id, ['collecting', 'needs_organizer', 'decided'])
        if not session:
            await interaction.response.send_message('No active draft session in this channel.', ephemeral=True)
            return
        if not self._can_manage(interaction, session):
            await interaction.response.send_message('Only the organizer (or a server manager) can do that.', ephemeral=True)
            return
        await interaction.response.send_message(f'Cancelled session #{session.id}.', ephemeral=True)
        await self.cancel_session(session, announce=True)

    # ---------- decision + finalize ----------

    async def run_decision(self, session: DraftSession):
        """ Called at deadline. Auto-pick if a slot works for every responder and
            we have enough players; otherwise DM the organizer a summary. """
        responses = await self.db.get_responses(session.id)
        responders, grid = self._build_grid(responses)

        universal = [slot for slot, users in grid.items() if len(users) == len(responders)]
        if responders and len(responders) >= MIN_PLAYERS and universal:
            day_iso, hour = min(universal)  # earliest day, earliest hour
            log.info('Session %d: auto-picking %s %s', session.id, day_iso, hour)
            await self.finalize(session, day_iso, hour, auto=True)
            return

        log.info('Session %d: needs organizer (%d responders, %d universal slots)',
                 session.id, len(responders), len(universal))
        await self.db.set_status(session.id, 'needs_organizer')
        await self._send_organizer_summary(session, responses, grid, len(responders))

    async def finalize(self, session: DraftSession, day_iso: str, hour: int, auto: bool):
        responses = await self.db.get_responses(session.id)
        attendees = [r.user_id for r in responses
                     if not r.is_out and hour in r.availability.get(day_iso, [])]

        slot_utc = local_slot_to_utc(date.fromisoformat(day_iso), hour)
        await self.db.set_picked(session.id, slot_utc)
        await self._disable_announcement_buttons(session)

        type_label = DRAFT_TYPE_LABELS.get(session.draft_type, session.draft_type)
        mentions = ' '.join(f'<@{uid}>' for uid in attendees) or '(nobody?!)'
        how = 'Everyone who responded can make it' if auto else 'The organizer picked'
        channel = self.bot.get_channel(session.channel_id)
        if channel:
            await channel.send(
                f'🃏 **Draft locked in: {discord_timestamp(slot_utc)}** ({type_label})\n'
                f'{how} — see you there: {mentions}',
                allowed_mentions=discord.AllowedMentions(users=True))

        await self._create_scheduled_event(session, slot_utc, type_label)

    async def cancel_session(self, session: DraftSession, announce: bool):
        await self.db.set_status(session.id, 'cancelled')
        await self._disable_announcement_buttons(session)
        if announce:
            channel = self.bot.get_channel(session.channel_id)
            if channel:
                await channel.send('🃏 No draft this week — scheduling was cancelled. See you next time!')

    async def _send_organizer_summary(self, session: DraftSession, responses: List[DraftResponse],
                                      grid: Dict[Tuple[str, int], Set[int]], responder_count: int):
        organizer = self.bot.get_user(session.organizer_id)
        if not organizer:
            log.warning('Session %d: could not find organizer %d', session.id, session.organizer_id)
            return

        if responder_count < MIN_PLAYERS:
            reason = f'only **{responder_count}** people are in (need {MIN_PLAYERS})'
        else:
            reason = 'no single slot works for everyone who responded'
        embed = self._grid_embed(session, responses)

        # Top slots by attendance for the quick-pick dropdown.
        ranked = sorted(grid.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:25]
        options = [
            discord.SelectOption(
                label=f'{fmt_day(date.fromisoformat(d))} {fmt_hour(h)} — {len(users)} in',
                value=f'{d}|{h}')
            for (d, h), users in ranked
        ]
        view = OrganizerDecisionView(self, session.id, options)
        try:
            await organizer.send(
                content=f"I couldn't auto-pick for draft session #{session.id}: {reason}.\n"
                        f'Pick a slot below, cancel the week, or use `/draft pick` in the channel '
                        f'(that also works if this menu dies to a bot restart).',
                embed=embed, view=view)
        except discord.Forbidden:
            channel = self.bot.get_channel(session.channel_id)
            if channel:
                await channel.send(
                    f"<@{session.organizer_id}> I couldn't auto-pick ({reason}) and your DMs are closed — "
                    f'use `/draft status` and `/draft pick` here.',
                    allowed_mentions=discord.AllowedMentions(users=True))

    async def _create_scheduled_event(self, session: DraftSession, slot_utc: datetime, type_label: str):
        guild = self.bot.get_guild(session.guild_id)
        if not guild:
            return
        start = pytz.utc.localize(slot_utc)
        if start <= discord.utils.utcnow():
            return
        try:
            await guild.create_scheduled_event(
                name=f'MTG Draft ({type_label})',
                start_time=start,
                end_time=start + timedelta(hours=DRAFT_LENGTH_HOURS),
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location=type_label,
                description='Scheduled by zhenpai draft scheduling.',
            )
        except discord.Forbidden:
            log.warning('Session %d: missing Manage Events permission, skipping scheduled event', session.id)
        except discord.HTTPException as e:
            log.warning('Session %d: failed to create scheduled event: %s', session.id, e)

    # ---------- reminders / polling ----------

    @tasks.loop(minutes=POLLING_INTERVAL_MINUTES)
    async def tick(self):
        now = datetime.utcnow()
        try:
            for session in await self.db.get_sessions_by_status(['collecting']):
                if now >= session.deadline:
                    await self.run_decision(session)
                else:
                    await self._maybe_remind(session, now)
            for session in await self.db.get_sessions_by_status(['decided']):
                await self._maybe_day_of_reminder(session, now)
        except Exception:
            log.exception('Error in draft scheduling tick')

    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()
        log.info('Starting %s update loop', __name__)

    async def _maybe_remind(self, session: DraftSession, now: datetime):
        elapsed = now - session.created_at
        remaining = session.deadline - now

        if session.reminder_stage < 3 and remaining <= timedelta(hours=LAST_CALL_HOURS_BEFORE_DEADLINE):
            await self._send_last_call(session)
            await self.db.set_reminder_stage(session.id, 3)
        elif session.reminder_stage < 2 and elapsed >= timedelta(hours=SECOND_DM_HOURS):
            await self._send_dm_reminders(session)
            await self.db.set_reminder_stage(session.id, 2)
        elif session.reminder_stage < 1 and elapsed >= timedelta(hours=FIRST_DM_HOURS):
            await self._send_dm_reminders(session)
            await self.db.set_reminder_stage(session.id, 1)

    async def _non_responders(self, session: DraftSession) -> List[discord.Member]:
        guild = self.bot.get_guild(session.guild_id)
        if not guild:
            return []
        role = guild.get_role(session.role_id)
        if not role:
            return []
        responses = await self.db.get_responses(session.id)
        responded_ids = {r.user_id for r in responses}
        return [m for m in role.members if not m.bot and m.id not in responded_ids]

    def _jump_url(self, session: DraftSession) -> str:
        return (f'https://discord.com/channels/{session.guild_id}/'
                f'{session.channel_id}/{session.announcement_message_id}')

    async def _send_dm_reminders(self, session: DraftSession):
        members = await self._non_responders(session)
        log.info('Session %d: DM reminding %d non-responders', session.id, len(members))
        for member in members:
            try:
                await member.send(
                    f"👋 Friendly reminder to set your availability for this week's draft "
                    f'(deciding {discord_timestamp(session.deadline, "R")}): {self._jump_url(session)}')
            except discord.Forbidden:
                log.info('Session %d: cannot DM %d', session.id, member.id)
            except discord.HTTPException as e:
                log.warning('Session %d: DM to %d failed: %s', session.id, member.id, e)

    async def _send_last_call(self, session: DraftSession):
        members = await self._non_responders(session)
        if not members:
            return
        channel = self.bot.get_channel(session.channel_id)
        if not channel:
            return
        mentions = ' '.join(m.mention for m in members)
        await channel.send(
            f'⏰ Last call for draft availability — deciding {discord_timestamp(session.deadline, "R")}. '
            f'Still waiting on: {mentions}',
            allowed_mentions=discord.AllowedMentions(users=True))

    async def _maybe_day_of_reminder(self, session: DraftSession, now: datetime):
        if session.day_of_reminder_sent or not session.picked_slot:
            return
        if not (timedelta(0) < session.picked_slot - now <= timedelta(hours=DAY_OF_REMINDER_HOURS_BEFORE)):
            return
        responses = await self.db.get_responses(session.id)
        local = utc_to_local(session.picked_slot)
        day_iso, hour = local.date().isoformat(), local.hour
        attendees = [r.user_id for r in responses
                     if not r.is_out and hour in r.availability.get(day_iso, [])]
        channel = self.bot.get_channel(session.channel_id)
        if channel and attendees:
            mentions = ' '.join(f'<@{uid}>' for uid in attendees)
            await channel.send(
                f'🃏 Draft starts {discord_timestamp(session.picked_slot, "R")}! {mentions}',
                allowed_mentions=discord.AllowedMentions(users=True))
        await self.db.set_day_of_reminder_sent(session.id)

    # ---------- helpers ----------

    def _parse_days(self, days_input: str) -> Optional[List[date]]:
        """ 'fri,sat,sun' -> next upcoming occurrence of each (1-7 days out), sorted. """
        today = datetime.now(DRAFT_TIMEZONE).date()
        result = []
        for token in days_input.split(','):
            token = token.strip().lower()
            if token not in WEEKDAYS:
                return None
            target = WEEKDAYS[token]
            offset = (target - today.weekday() - 1) % 7 + 1  # 1..7 days out
            candidate = today + timedelta(days=offset)
            if candidate not in result:
                result.append(candidate)
        return sorted(result) if result else None

    def _match_candidate_day(self, session: DraftSession, day_input: str) -> Optional[date]:
        token = day_input.strip().lower()
        for d in session.candidate_days:
            if token in (d.isoformat(), f'{d:%a}'.lower(), f'{d:%A}'.lower()):
                return d
        if token in WEEKDAYS:
            for d in session.candidate_days:
                if d.weekday() == WEEKDAYS[token]:
                    return d
        return None

    def _can_manage(self, interaction: discord.Interaction, session: DraftSession) -> bool:
        if interaction.user.id in (session.organizer_id, self.bot.owner_id):
            return True
        member = interaction.guild.get_member(interaction.user.id)
        return bool(member and member.guild_permissions.manage_guild)

    @staticmethod
    def _build_grid(responses: List[DraftResponse]):
        """ Returns (responders, grid) where grid maps (day_iso, hour) -> set of user ids. """
        responders = [r for r in responses if not r.is_out and r.availability]
        grid: Dict[Tuple[str, int], Set[int]] = {}
        for r in responders:
            for day_iso, hours in r.availability.items():
                for h in hours:
                    grid.setdefault((day_iso, h), set()).add(r.user_id)
        return responders, grid

    def _announcement_embed(self, session: DraftSession, responses: List[DraftResponse]) -> discord.Embed:
        type_label = DRAFT_TYPE_LABELS.get(session.draft_type, session.draft_type)
        responders = [r for r in responses if not r.is_out and r.availability]
        outs = [r for r in responses if r.is_out]
        days_line = ', '.join(fmt_day(d) for d in session.candidate_days)
        embed = discord.Embed(
            title=f'🃏 Scheduling a draft — {type_label}',
            description=(
                f'**Candidate days:** {days_line}\n'
                f'**Deciding:** {discord_timestamp(session.deadline)} '
                f'({discord_timestamp(session.deadline, "R")})\n\n'
                f'Click **Set availability** and pick every start time you could make. '
                f"Can't make it at all? **Out this week** is one click."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name='Responded', value=str(len(responders)))
        embed.add_field(name='Out', value=str(len(outs)))
        embed.set_footer(text=f'Session #{session.id} • auto-picks if everyone who responded '
                              f'shares a slot and {MIN_PLAYERS}+ are in')
        return embed

    def _grid_embed(self, session: DraftSession, responses: List[DraftResponse]) -> discord.Embed:
        responders, grid = self._build_grid(responses)
        outs = [r for r in responses if r.is_out]
        guild = self.bot.get_guild(session.guild_id)

        def name(uid: int) -> str:
            member = guild.get_member(uid) if guild else None
            return member.display_name if member else f'<{uid}>'

        embed = discord.Embed(
            title=f'Draft session #{session.id} — {len(responders)} in, {len(outs)} out',
            color=discord.Color.blurple(),
        )
        for day in session.candidate_days:
            day_iso = day.isoformat()
            lines = []
            for hour in range(session.hour_start, session.hour_end + 1):
                users = grid.get((day_iso, hour))
                if users:
                    everyone = ' ✅' if len(users) == len(responders) and len(responders) >= MIN_PLAYERS else ''
                    lines.append(f'**{fmt_hour(hour)}** — {len(users)}{everyone}: '
                                 f'{", ".join(sorted(name(u) for u in users))}')
            embed.add_field(name=fmt_day(day), value='\n'.join(lines)[:1024] or '*nobody yet*', inline=False)

        notes = [f'**{name(r.user_id)}**: {r.note}' for r in responses if r.note]
        if notes:
            embed.add_field(name='📝 Notes', value='\n'.join(notes)[:1024], inline=False)
        if session.status == 'decided' and session.picked_slot:
            embed.add_field(name='Locked in', value=discord_timestamp(session.picked_slot), inline=False)
        return embed

    async def update_announcement(self, session_id: int):
        """ Best-effort refresh of the responded/out counts on the announcement embed. """
        session = await self.db.get_session(session_id)
        if not session or not session.announcement_message_id:
            return
        try:
            channel = self.bot.get_channel(session.channel_id)
            if not channel:
                return
            message = await channel.fetch_message(session.announcement_message_id)
            responses = await self.db.get_responses(session_id)
            await message.edit(embed=self._announcement_embed(session, responses))
        except discord.HTTPException as e:
            log.warning('Session %d: failed to update announcement: %s', session_id, e)

    async def _disable_announcement_buttons(self, session: DraftSession):
        if not session.announcement_message_id:
            return
        try:
            channel = self.bot.get_channel(session.channel_id)
            if not channel:
                return
            message = await channel.fetch_message(session.announcement_message_id)
            await message.edit(view=None)
        except discord.HTTPException as e:
            log.warning('Session %d: failed to disable announcement buttons: %s', session.id, e)
