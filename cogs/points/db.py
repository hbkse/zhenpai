from asyncpg import Pool
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

log: logging.Logger = logging.getLogger(__name__)

class PointsDb:
    # table names
    POINTS = 'points'
    POINT_BALANCE = 'point_balances'
    PROCESSED_EVENTS = 'processed_events'

    def __init__(self, pool: Pool):
        self.pool = pool
    