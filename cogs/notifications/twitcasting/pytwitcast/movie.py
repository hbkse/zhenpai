from .models import Model


class Movie(Model):

    @classmethod
    def parse(cls, api, json):
        movie = cls(api)
        setattr(movie, '_json', json)

        for k, v in json.items():
            setattr(movie, k, v)

        return movie