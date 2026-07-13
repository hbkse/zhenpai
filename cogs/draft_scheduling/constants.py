import datetime
import pytz

# Timezone used to interpret candidate days and displayed times.
# (Repo convention elsewhere is US/Central; change this if your group is elsewhere.)
# Absolute moments (deadline, locked-in time) render in each viewer's local time
# via Discord timestamps; only hour *labels* (picker options, status) use this.
DRAFT_TIMEZONE = pytz.timezone('US/Central')
TIMEZONE_LABEL = 'US Central'  # keep in sync with DRAFT_TIMEZONE

# A draft doesn't fire with fewer than this many players. Auto-pick requires it;
# below it the organizer gets pinged to decide.
MIN_PLAYERS = 6

DEFAULT_DEADLINE_HOURS = 72
DEFAULT_HOUR_START = 12   # noon
DEFAULT_HOUR_END = 22     # 10 PM (last selectable *start* time)
MAX_CANDIDATE_DAYS = 4    # discord caps messages at 5 component rows; 4 selects + 1 button row

# Reminder cadence
FIRST_DM_HOURS = 24                   # DM non-responders this long after kickoff
SECOND_DM_HOURS = 48                  # second DM
LAST_CALL_HOURS_BEFORE_DEADLINE = 12  # public @mention when this close to deadline
DAY_OF_REMINDER_HOURS_BEFORE = 2      # ping attendees this long before the draft

DRAFT_LENGTH_HOURS = 4  # used for the scheduled event's end time

WEEKDAYS = {
    'mon': 0, 'monday': 0,
    'tue': 1, 'tues': 1, 'tuesday': 1,
    'wed': 2, 'weds': 2, 'wednesday': 2,
    'thu': 3, 'thur': 3, 'thurs': 3, 'thursday': 3,
    'fri': 4, 'friday': 4,
    'sat': 5, 'saturday': 5,
    'sun': 6, 'sunday': 6,
}

DEFAULT_SESSION_NAME = 'Draft'


def fmt_hour(hour: int) -> str:
    """ 18 -> '6 PM', 0 -> '12 AM', 12 -> '12 PM' """
    suffix = 'AM' if hour < 12 else 'PM'
    display = hour % 12
    if display == 0:
        display = 12
    return f"{display} {suffix}"


def fmt_day(d: datetime.date) -> str:
    """ 2026-07-17 -> 'Fri Jul 17' """
    return f"{d:%a %b} {d.day}"


def describe_hours(hours, hour_start: int, hour_end: int) -> str:
    """ Stored start hours -> the coarse label the user picked.
        [12..22] -> 'anytime', [15..22] -> 'after 3 PM', [] -> "can't" """
    if not hours:
        return "can't"
    hs = sorted(hours)
    if hs == list(range(hs[0], hour_end + 1)):
        return 'anytime' if hs[0] <= hour_start else f'after {fmt_hour(hs[0])}'
    return ', '.join(fmt_hour(h) for h in hs)


def local_slot_to_utc(day: datetime.date, hour: int) -> datetime.datetime:
    """ Local (day, start hour) -> naive UTC datetime, for storage. """
    local = DRAFT_TIMEZONE.localize(datetime.datetime.combine(day, datetime.time(hour=hour)))
    return local.astimezone(pytz.utc).replace(tzinfo=None)


def utc_to_local(dt_naive_utc: datetime.datetime) -> datetime.datetime:
    """ Naive UTC datetime -> aware local datetime. """
    return pytz.utc.localize(dt_naive_utc).astimezone(DRAFT_TIMEZONE)


def discord_timestamp(dt_naive_utc: datetime.datetime, style: str = 'F') -> str:
    epoch = int(pytz.utc.localize(dt_naive_utc).timestamp())
    return f"<t:{epoch}:{style}>"
