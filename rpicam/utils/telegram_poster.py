#!/usr/bin/env python3

import os
from typing import Union
from pathlib import Path

import requests

from rpicam.utils.logging_utils import get_logger


class TelegramPoster:
    """
    Bare-bones class to post videos to a Telegram chat.
    Uses per default credentials stored in environment.
    """

    API_URL = 'https://api.telegram.org'
    API_TOKEN_ENV_VAR = 'RPICAM_TG_API_TOKEN'
    CHAT_ID_ENV_VAR = 'RPICAM_TG_CHAT_ID'

    def __init__(self, api_token: str = None, chat_id: str = None):
        if api_token is not None and chat_id is not None:
            self.api_token = api_token
            self.chat_id = chat_id
        else:
            self.api_token = os.getenv(self.API_TOKEN_ENV_VAR, None)
            self.chat_id = os.getenv(self.CHAT_ID_ENV_VAR, None)
        self._logger = get_logger(self.__class__.__name__, verb=True)
        if self.api_token is None or self.chat_id is None:
            raise RuntimeError('Could not find Telegram credentials in environment.')

    def send_video(self, p: Union[Path, str]):
        """Post the given video to Telegram using stored credentials."""
        p = Path(str(p)).resolve()
        if not p.is_file():
            raise RuntimeError(f'file not found: {p}')
        url = f'{self.API_URL}/bot{self.api_token}/sendVideo'
        files = {
            'chat_id': (None, self.chat_id),
            'video': (str(p), open(p, 'rb'))
        }
        r = requests.post(url, files=files)
        if r.status_code != 200:
            self._logger.error(f'Could not upload file. Exit code was {r.status_code}: "{r.text}"')
        else:
            self._logger.info(f'Successfully uploaded file to Telegram.')

    def send_text(self, text: str):
        """Post the given text to Telegram using stored credentials."""
        url = f'{self.API_URL}/bot{self.api_token}/sendMessage'
        data = {
            'chat_id': self.chat_id,
            'text': text
        }
        r = requests.post(url, data=data)
        if r.status_code != 200:
            self._logger.error(f'Could not send text. Exit code was {r.status_code}: "{r.text}"')
        else:
            self._logger.info(f'Successfully sent text to Telegram.')
