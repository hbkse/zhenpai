from .twitcast_user import TwitcastUser


class _DatabaseTwitcastUsers:
    def get_twitcast_user(self, twitcast_user_id: str):
        return self.session.query(TwitcastUser) \
            .filter(TwitcastUser.twitcast_user_id == twitcast_user_id) \
            .first()

    def get_or_add_twitcast_user(self, twitcast_user_id: str, twitcast_name: str) -> TwitcastUser:
        twitcast_user = self.session.query(TwitcastUser) \
            .filter(TwitcastUser.twitcast_user_id == twitcast_user_id) \
            .first()
        if not twitcast_user:
            twitcast_user = TwitcastUser(twitcast_user_id, twitcast_name)
            self.session.add(twitcast_user)
        return twitcast_user

    def delete_twitcast_user(self, twitcast_user):
        self.session.delete(twitcast_user)
