from .tag import Tag
from typing import List


class _DatabaseTags:
    def get_tag_by_guild_id_and_tag(self, guild_id: str, tag: str) -> Tag:
        return self.session.query(Tag) \
            .filter(Tag.guild_id == guild_id) \
            .filter(Tag.tag == tag) \
            .first()

    def get_tags_by_guild_id(self, guild_id: str) -> List[Tag]:
        return self.session.query(Tag) \
            .filter(Tag.guild_id == guild_id) \
            .all()

    def get_tags_by_guild_id_and_creator_id(self, guild_id: str, creator_id: str) -> List[Tag]:
        return self.session.query(Tag) \
            .filter(Tag.guild_id == guild_id) \
            .filter(Tag.creator_id == creator_id) \
            .all()

    def add_tag(self, tag: Tag):
        self.session.add(tag)

    def remove_tag(self, tag: Tag):
        self.session.delete(tag)
