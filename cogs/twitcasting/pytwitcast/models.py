class Model:
    """
    Base representation of JSON data entities in the official Twitcasting API.
    Implement this class to create Python-native representations of Twitcasting data objects.
    """

    def __init__(self, api=None):
        self._api = api

    @classmethod
    def parse(cls, api, json):
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        results = list()
        for json in json_list:
            if json:
                results.append(cls.parse(api=api, json=json))
        return results

