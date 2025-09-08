from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    user_id: int
    tg_username: str
    group_id: int
    sec_group_id: int
    missed_hours: int
    show_missed_hours_mode: Optional[str]  # может быть None, если в БД NULL


@dataclass
class TGgroup:
    id: int
    user_id: int
    group: int
    pin_new_rasp: bool