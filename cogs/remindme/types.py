from enum import Enum

class ReminderType(Enum):
    """Enum for reminder types"""
    PRIVATE = "private"
    PUBLIC = "public"
    MENTION = "mention"
