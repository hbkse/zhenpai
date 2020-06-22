import json
from enum import Enum
from typing import List
from typing import Dict
from typing import Union
import base64

from .user import User
from .webhook import Webhook
from .movie import Movie

import requests

BASE_API_URI = "https://apiv2.twitcasting.tv/"


class Auth(Enum):
    BASIC = 'Basic '
    OAUTH = 'Bearer '
    NONE = ''


class TwitcastAPI:
    """
    This is a small API wrapper over the official Twitcasting V2 API.
    """

    def __init__(self, client_id: str, client_secret: str, access_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._session = requests.Session()

    def _generate_auth(self, auth: Auth):
        if auth is Auth.BASIC:
            return {'Authorization': Auth.BASIC.value + base64.b64encode(f'{self._client_id}:{self._client_secret}'.encode("utf-8")).decode("utf-8")}
        elif auth is Auth.OAUTH:
            return {'Authorization': Auth.OAUTH.value + self._access_token}
        else:
            return {}

    def _api_call(self, method: str, url: str, payload: object = None, json_data: Dict[str, str] = None, auth: Auth = None, params: dict = None):
        _url = BASE_API_URI + url

        args = dict(params=params)
        if payload:
            args['data'] = json.dumps(payload)
        if json:
            args['json'] = json_data

        _headers = self._generate_auth(auth)
        _headers['X-Api-Version'] = '2.0'
        _headers['Accept'] = 'application/json'

        r = self._session.request(method, _url, headers=_headers, **args)

        # TODO: HTTP error handling

        if r.text and r.text != 'null':
            if r.headers['Content-Type'] in ['image/jpeg', 'image/png']:
                file_ext = r.headers['Content-Type'].replace('image/', '')
                ret = {'bytes_data': r.content,
                       'file_ext': file_ext}
                return ret
            else:
                return r.json()
        else:
            return None

    def _get(self, url: str, args: dict = None, payload: object = None, json_data: Dict[str, str] = None, auth: Auth = None, **kwargs):
        if args:
            kwargs.update(args)

        return self._api_call('GET', url, payload, json_data, auth, kwargs)

    def _post(self, url: str, args: dict = None, payload: object = None, json_data: Dict[str, str] = None, auth: Auth = None, **kwargs):
        if args:
            kwargs.update(args)

        return self._api_call('POST', url, payload, json_data, auth, kwargs)

    def _delete(self, url: str, args: dict = None, payload: object = None, json_data: Dict[str, str] = None, auth: Auth = None, **kwargs):
        if args:
            kwargs.update(args)

        return self._api_call('DELETE', url, payload, json_data, auth, kwargs)

    def search_users(self, words: Union[str, List[str]], limit: int = 10, lang: str = 'ja') -> List[User]:
        """
        Search users on Twitcasting API by using the provided list of words as the query parameter.
        :param words: search terms.
        :param limit: maximum number of users to look up.
        :param lang: the language of the response.
        :return:
        """
        if isinstance(words, list):
            w = ' '.join(words) if len(words) > 1 else words[0]
        else:
            w = words
        res = self._get(url='/search/users', auth=Auth.OAUTH, words=w, limit=limit, lang=lang)
        return User.parse_list(self, res['users'])

    def get_webhook_list(self, limit: int = 50, offset: int = 0, user_id: str = None):
        """
        Gets list of registered webhooks on the Twitcasting account.
        :param limit: maximum number of webhooks to retrieve.
        :param offset: offset in the list of webhooks.
        :param user_id: filters the list for matching user_id.
        :return: list of Webhook objects.
        """
        res = self._get(url='/webhooks', auth=Auth.BASIC, limit=limit, offset=offset, user_id=user_id)
        return Webhook.parse_list(self, res['webhooks'])

    def register_webhook(self, user_id: str = None, events: List[str] = ['livestart', 'liveend']):
        """
        Registers a Twitcasting user webhook to the Twitcasting account.
        :param user_id: the id of the Twitcasting user to receive webhook notifications from.
        :param events: the events that Twitcasting will push notifications for. Only 'livestream' and 'liveend'
        are valid.
        :return:
        """
        data = {'user_id': user_id, 'events': events}
        return self._post(url='/webhooks', auth=Auth.BASIC, json_data=data)

    def remove_webhook(self, user_id: str = None, events: List[str] = ['livestart', 'liveend']):
        """
        Deletes a Twitcasting user webhook to the Twitcasting account.
        :param user_id: the id of the Twitcasting user to stop receiving webhook notifications from.
        :param events: the events that Twitcasting will stop pushing notifications for. Only 'livestream' and 'liveend'
        are valid.
        :return:
        """
        params = {'user_id': user_id, 'events[]': events}
        return self._delete(url='/webhooks', auth=Auth.BASIC, args=params)

    def parse_incoming_webhook(self, res):
        """
        Parses an incoming webhook notification into a Movie object (the stream that went online or offline)
         and a User object (the Twitcasting user that started or ended the stream).
        :param res: the raw webhook notification received by the web server.
        :return: tuple containing the Movie object and User object.
        """
        movie = Movie.parse(self, res['movie'])
        user = User.parse(self, res['broadcaster'])
        return movie, user
