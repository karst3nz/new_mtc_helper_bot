from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    user_id: int
    tg_username: Optional[str]
    group_id: Optional[int]
    rasp_data: Optional[str]
    mng_time: Optional[str]
    mng_send_state: Optional[str]
    sec_group_id: Optional[int]
    msg_max_length: Optional[str]
    format_rasp: Optional[str]
    missed_hours: Optional[int]
    show_missed_hours_mode: Optional[str]
    smena: Optional[int]


@dataclass
class TGgroup:
    id: int
    user_id: int
    group: int
    pin_new_rasp: bool