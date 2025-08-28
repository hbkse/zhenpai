# These are their Origin UIDs. Just be mindful of rate limits if we have
# a lot of players on this list
DEFAULT_PLAYERS = [
    "2411561527",  # Kanav
    "2264348150",  # Zaporteza
    "2310441224",   # B1LL
    "76561197984898546",  # firechuong
    "1007843832232",  # sam100
    "1003694528166",  # ImARailgun
    "1009818857089",  # NotHeartbreaker
    "2411660248",  # Real_Life_Decoy
    "1011551048572",  # genzbossandamini
    "1013320161195"  # ratgodx
]


import logging
from typing import Dict, Optional
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

PLAYER_STATUS_URL = (
    "https://api.mozambiquehe.re/bridge?version=5&platform=PC&uid={uid}"
)


async def fetch_player_data(
    bot: Zhenpai, api_key: str, player_uid: str
) -> Optional[Dict]:
    url = PLAYER_STATUS_URL.format(uid=player_uid)

    try:
        async with bot.http_client.get(
            url, headers={"Authorization": api_key}
        ) as resp:
            if resp.status == 404:
                log.info("Player UID %s not found", player_uid)
                return None
            elif resp.status != 200:
                log.warning(
                    "Failed to fetch data for player UID %s (status %s)",
                    player_uid,
                    resp.status,
                )
                return None

            data = await resp.json()
            return data
    except Exception as e:
        log.exception(
            "Error fetching player data for UID %s: %s", player_uid, e
        )
        return None


def parse_player_info(data: Dict, player_name: str) -> Dict:
    global_info = data.get("global", {})
    realtime_info = data.get("realtime", {})
    legends_info = data.get("legends", {})

    # Build player name
    name = global_info.get("name", player_name)
    tag = global_info.get("tag", "")
    player_name_with_tag = f"{name}#{tag}" if tag else name

    # Build rank info
    rank_info = global_info.get("rank", {})
    rank_name = rank_info.get("rankName", "Unranked")
    rank_div = rank_info.get("rankDiv", 0)
    rank_label = f"{rank_name} {rank_div}" if rank_div > 0 else rank_name
    rank_score = rank_info.get("rankScore", 0)

    # Build legend info
    selected_legend = realtime_info.get("selectedLegend")
    if not selected_legend:
        selected_legend_data = legends_info.get("selected", {})
        selected_legend = selected_legend_data.get("LegendName")

    # Build status
    is_in_game = realtime_info.get("isInGame", 0) == 1
    is_online = realtime_info.get("isOnline", 0) == 1
    lobby_state = realtime_info.get("lobbyState", "offline")

    if is_in_game:
        status = "in_game"
    elif is_online:
        status = lobby_state if lobby_state else "online"
    else:
        status = "offline"

    return {
        "playerName": player_name_with_tag,
        "rankLabel": rank_label,
        "rankScore": rank_score,
        "legend": selected_legend,
        "status": status
    }
