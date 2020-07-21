from .user import User


class _DatabaseUsers:
    def get_user(self, user_id: int) -> User:
        return self.session.query(User)\
                .filter(User.user_id == user_id)\
                .first()

    def get_or_add_user(self, user_id: int) -> User:
        user = self.session.query(User)\
                .filter(User.user_id == user_id)\
                .first()
        if not user:
            user = User(user_id)
            self.session.add(user)
        return user
    
    def delete_user(self, user: User):
        self.session.delete(user)
