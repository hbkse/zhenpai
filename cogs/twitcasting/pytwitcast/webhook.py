from .models import Model


class Webhook(Model):

    @classmethod
    def parse(cls, api, json):
        webhook = cls(api)
        setattr(webhook, '_json', json)

        for k, v in json.items():
            setattr(webhook, k, v)

        return webhook
