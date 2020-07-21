from .guild import Guild


class _DatabaseGuilds:
    def get_guild(self, guild_id: int) -> Guild:
        return self.session.query(Guild) \
            .filter(Guild.guild_id == guild_id) \
            .first()

    def get_or_add_guild(self, guild_id: int) -> Guild:
        guild = self.session.query(Guild) \
            .filter(Guild.guild_id == guild_id) \
            .first()
        if not guild:
            guild = Guild(guild_id)
            self.session.add(guild)
        return guild

    def delete_guild(self, guild: Guild):
        self.session.delete(guild)
