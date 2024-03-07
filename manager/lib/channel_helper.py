
from enum import Enum
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChannelHelper:
    url: str
    original_group: str = '<NONE>'
    name: str = '<UNKNOWN>'
    group: Optional[str] = None
    logo: Optional[str] = None
    tvg_name: Optional[str] = None
    tvg_id: Optional[str] = None

    @classmethod
    def from_m3u_entry(cls, channel_data: dict):
        """
        [
        {'name': 'Yes Movies Drama HD',
        'logo': 'https://af-play.com/storage/images/channel_logos/8dd7310854aad0f69f2c9b87232839a6.png',
        'url': 'http://bethoven.af-stream.com:1600/s/ccbejm2q/yes-movies-drama-il-hd/video.m3u8',
        'category': 'Israel',
        'tvg': {'id': 'yes-movies-drama-il-hd', 'name': None, 'url': None, 'chno': None},
        'country': {'code': None, 'name': None},
        'language': {'code': None, 'name': None},
        'status': 'GOOD',
        'live': True},
        ]
        """
        return cls(
            url=channel_data["url"],
            name=channel_data["name"],
            logo=channel_data["logo"],
            original_group=channel_data["category"],
            group=channel_data["category"],
            tvg_name=channel_data.get("tvg", {}).get("name"),
            tvg_id=channel_data.get("tvg", {}).get("id"),
        )

"""
9 Канал
9 Канал HD
Kan 11 HD
Keshet 12 HD
Reshet 13 HD
Ch 14 HD
i24 HD
Yes Movies Action HD
Yes Movies Comedy HD
Yes Movies Drama HD
Yes Movies KIDS HD
Yes TV Action HD
Yes TV Comedy HD
Yes TV Drama HD
HOT Cinema 1 HD
HOT Cinema 2 HD
HOT Cinema 3 HD
HOT Cinema 4 HD
HBO HD IL
Zone HD
Viva IL
Viva Premium HD
Viva+
Viva Vintage
HOT 3 HD
HOT 8 HD
Yes Israeli HD
Channel 24 HD IL
Turkish Dramas Plus HD
Turkish Dramas 2 HD
Turkish Dramas 3 HD
Yam Tichoni HD
Yam Tichoni+ HD
Bollywood HD IL
BollyShow HD
Animal Planet HD IL
Nat Geo Wild HD IL
National Geographic HD IL
Discovery HD IL
History HD IL
Travel Channel HD IL
Docu HD IL
Home Plus IL
Design Channel HD
Entertainment HD IL
E! IL
Food Network HD IL
Foody HD
Health HD
Good Life
CBS Reality IL
HOT Real HD
Sport 1 HD IL
Sport 2 HD IL
Sport 3 HD IL
Sport 4 HD IL
Sport 5 HD IL
Sport 5+ HD IL
Sport 5 Live HD
Sport 5 Stars HD
Sport 5 Gold
One HD IL
One 2 HD IL
Ego Total
Humor Channel HD
HOT Comedy HD
Cinema Family HD
Disney HD IL
Disney Jr HD IL
Nickelodeon HD IL
Nick Jr HD IL
TeenNick HD IL
HOP
Luli
Baby HD IL
Zoom IL
KAN23 HD IL
Junior HD IL
Music HD
Yam Tichoni 2 HD
"""


class GroupCategory(Enum):
    MOVIES = "MOVIES",
    MUSIC = "MUSIC",
    SPORT = "SPORT",
    OTHER = "OTHER",


channel_name_to_group_category = {
    "Yes Movies Action HD": GroupCategory.MOVIES,
    "Sport 5 Gold": GroupCategory.SPORT,
    "Music HD": GroupCategory.MUSIC,
}


class ChannelFactory:
    @classmethod
    def default(cls):
        return cls(
            name_mapper=channel_name_to_group_category,
        )

    def __init__(self, name_mapper):
        self.name_mapper = name_mapper

    def from_m3u_entry(self, entry: dict) -> ChannelHelper:
        channel = ChannelHelper.from_m3u_entry(entry)
        channel.group = str(self.find_group_category(channel).name)
        return channel

    def find_group_category(self, channel: ChannelHelper) -> GroupCategory:
        if (category := self._match_by_name_exact(channel)) is not None:
            return category

        if (category := self._match_by_name_fuzzy(channel)) is not None:
            return category

        return GroupCategory.OTHER

    def _match_by_name_exact(self, channel):
        return self.name_mapper.get(channel.name)

    def _match_by_name_fuzzy(self, channel):
        name_upper = channel.name.upper()
        tvg_id_upper = channel.tvg_id.upper() if channel.tvg_id else ''

        def in_gc(gc: GroupCategory, val):
            for v in gc.value:
                if v in val:
                    return True
            return False

        for gc in GroupCategory:
            if in_gc(gc, name_upper) or in_gc(gc, tvg_id_upper):
                return gc
        return None
