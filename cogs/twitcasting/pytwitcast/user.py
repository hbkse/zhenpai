from .models import Model


class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        setattr(user, '_json', json)

        for k, v in json.items():
            setattr(user, k, v)

        return user

    def create_webhook(self):
        return self._api.register_webhook(user_id=self.id)

    def delete_webhook(self):
        return self._api.remove_webhook(user_id=self.id)
