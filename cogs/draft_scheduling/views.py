from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Dict, List, Optional

import discord
from discord import ui

from .constants import fmt_day, fmt_hour
from .db import DraftResponse, DraftSession

if TYPE_CHECKING:
    from .draft_scheduling import DraftScheduling

log: logging.Logger = logging.getLogger(__name__)


class AnnouncementView(ui.View):
    """ Persistent view attached to the public announcement message.
        Re-registered in cog_load after restarts for active sessions. """

    def __init__(self, cog: 'DraftScheduling', session_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.session_id = session_id

        avail_button = ui.Button(
            label='Set availability',
            style=discord.ButtonStyle.primary,
            custom_id=f'draftsched:avail:{session_id}',
        )
        avail_button.callback = self.on_set_availability
        self.add_item(avail_button)

        out_button = ui.Button(
            label='Out this week',
            style=discord.ButtonStyle.secondary,
            custom_id=f'draftsched:out:{session_id}',
        )
        out_button.callback = self.on_out
        self.add_item(out_button)

    async def _get_open_session(self, interaction: discord.Interaction) -> Optional[DraftSession]:
        session = await self.cog.db.get_session(self.session_id)
        if not session or session.status != 'collecting':
            await interaction.response.send_message(
                "Scheduling for this draft is closed.", ephemeral=True)
            return None
        return session

    async def on_set_availability(self, interaction: discord.Interaction):
        session = await self._get_open_session(interaction)
        if not session:
            return
        existing = await self.cog.db.get_response(session.id, interaction.user.id)
        picker = AvailabilityPicker(self.cog, session, existing)
        await interaction.response.send_message(
            content=picker.instructions(), view=picker, ephemeral=True)

    async def on_out(self, interaction: discord.Interaction):
        session = await self._get_open_session(interaction)
        if not session:
            return
        await self.cog.db.upsert_out(session.id, interaction.user.id)
        await interaction.response.send_message(
            "Got it, you're marked as out this week. Click **Set availability** if that changes.",
            ephemeral=True)
        await self.cog.update_announcement(session.id)


class DaySelect(ui.Select):
    """ One multi-select per candidate day. Options are start times. """

    def __init__(self, picker: 'AvailabilityPicker', day: date, row: int):
        self.picker = picker
        self.day_iso = day.isoformat()
        selected = set(picker.selections.get(self.day_iso, []))
        options = [
            discord.SelectOption(label=fmt_hour(h), value=str(h), default=(h in selected))
            for h in range(picker.session.hour_start, picker.session.hour_end + 1)
        ]
        super().__init__(
            placeholder=f"{fmt_day(day)} — pick every start time that works",
            min_values=0,
            max_values=len(options),
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        self.picker.selections[self.day_iso] = sorted(int(v) for v in self.values)
        await interaction.response.defer()


class NoteModal(ui.Modal, title='Note for the organizer'):
    note = ui.TextInput(
        label='Anything the organizer should know?',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
        placeholder='e.g. "Saturday works but only if we wrap by 6"',
    )

    def __init__(self, picker: 'AvailabilityPicker'):
        super().__init__()
        self.picker = picker
        self.note.default = picker.note

    async def on_submit(self, interaction: discord.Interaction):
        self.picker.note = self.note.value.strip() or None
        try:
            suffix = " *(note attached ✏️)*" if self.picker.note else ""
            await interaction.response.edit_message(
                content=self.picker.instructions() + suffix, view=self.picker)
        except discord.HTTPException:
            await interaction.response.defer()


class AvailabilityPicker(ui.View):
    """ Ephemeral, per-user picker. One select per day + submit/note buttons. """

    def __init__(self, cog: 'DraftScheduling', session: DraftSession,
                 existing: Optional[DraftResponse]):
        super().__init__(timeout=15 * 60)
        self.cog = cog
        self.session = session
        self.selections: Dict[str, List[int]] = {}
        self.note: Optional[str] = None
        if existing and not existing.is_out:
            self.selections = dict(existing.availability)
            self.note = existing.note

        for i, day in enumerate(session.candidate_days):
            self.add_item(DaySelect(self, day, row=i))

    def instructions(self) -> str:
        return ("Pick every start time you could make, per day. "
                "Leave a day empty if it doesn't work. Hit **Submit** when done.")

    def _summary(self) -> str:
        lines = []
        for day in self.session.candidate_days:
            hours = self.selections.get(day.isoformat(), [])
            if hours:
                lines.append(f"**{fmt_day(day)}**: {', '.join(fmt_hour(h) for h in hours)}")
        if not lines:
            return "no times selected"
        return '\n'.join(lines)

    @ui.button(label='Submit', style=discord.ButtonStyle.success, row=4)
    async def submit(self, interaction: discord.Interaction, button: ui.Button):
        session = await self.cog.db.get_session(self.session.id)
        if not session or session.status != 'collecting':
            await interaction.response.edit_message(
                content="Scheduling for this draft has closed in the meantime, sorry!", view=None)
            return

        availability = {d: hours for d, hours in self.selections.items() if hours}
        if not availability:
            await interaction.response.send_message(
                "You didn't select any times — if none work, use **Out this week** instead.",
                ephemeral=True)
            return

        await self.cog.db.upsert_availability(
            self.session.id, interaction.user.id, availability, self.note)
        note_line = f"\n📝 Note: *{self.note}*" if self.note else ""
        await interaction.response.edit_message(
            content=f"✅ Availability saved:\n{self._summary()}{note_line}\n\n"
                    f"You can click **Set availability** again any time before the deadline to change it.",
            view=None)
        self.stop()
        await self.cog.update_announcement(self.session.id)

    @ui.button(label='Add note', style=discord.ButtonStyle.secondary, row=4)
    async def add_note(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(NoteModal(self))


class SlotSelect(ui.Select):
    def __init__(self, view: 'OrganizerDecisionView', slot_options: List[discord.SelectOption]):
        self.decision_view = view
        super().__init__(placeholder='Pick a slot to lock in', min_values=1, max_values=1,
                         options=slot_options, row=0)

    async def callback(self, interaction: discord.Interaction):
        day_iso, hour_str = self.values[0].split('|')
        await self.decision_view.resolve(interaction, day_iso, int(hour_str))


class OrganizerDecisionView(ui.View):
    """ DMed to the organizer when the bot can't auto-pick.
        Not persistent across restarts — /draft pick is the fallback. """

    def __init__(self, cog: 'DraftScheduling', session_id: int,
                 slot_options: List[discord.SelectOption]):
        super().__init__(timeout=None)
        self.cog = cog
        self.session_id = session_id
        if slot_options:
            self.add_item(SlotSelect(self, slot_options))

    async def _get_pending_session(self, interaction: discord.Interaction) -> Optional[DraftSession]:
        session = await self.cog.db.get_session(self.session_id)
        if not session or session.status != 'needs_organizer':
            await interaction.response.send_message(
                "This session was already resolved.", ephemeral=True)
            return None
        return session

    async def resolve(self, interaction: discord.Interaction, day_iso: str, hour: int):
        session = await self._get_pending_session(interaction)
        if not session:
            return
        await interaction.response.edit_message(
            content=f"Locked in **{fmt_day(date.fromisoformat(day_iso))} {fmt_hour(hour)}** — announcing it now.",
            view=None)
        await self.cog.finalize(session, day_iso, hour, auto=False)
        self.stop()

    @ui.button(label='Cancel this week', style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        session = await self._get_pending_session(interaction)
        if not session:
            return
        await interaction.response.edit_message(
            content="Cancelled — I'll let the channel know there's no draft this week.", view=None)
        await self.cog.cancel_session(session, announce=True)
        self.stop()
