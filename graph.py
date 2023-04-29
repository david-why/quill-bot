import asyncio
import time
from typing import List, Optional, TypedDict, Union

import aiohttp
import jwt


class LogInResponse(TypedDict):
    device_code: str
    user_code: str
    verification_uri: str
    expires: int
    interval: int
    message: str


class ErrorBase(TypedDict, total=False):
    error_description: str


class ErrorResponse(ErrorBase, total=True):
    error: str


class PollData(TypedDict):
    device_code: str
    interval: int


class TokensResponse(TypedDict):
    token_type: str
    scope: str
    expires: int
    access_token: str
    refresh_token: str
    id_token: str


class Auth:
    def __init__(self, client_id: str, tenant: str = 'common'):
        self.client_id = client_id
        self.tenant = tenant
        self.authority = f'https://login.microsoftonline.com/{tenant}'

    async def log_in(self, scopes: List[str]) -> Union[LogInResponse, ErrorResponse]:
        if any(x in scopes for x in ['offline_access', 'openid']):
            raise ValueError('Do not use offline_access, openid')
        scopes.extend(['offline_access', 'openid'])
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.authority}/oauth2/v2.0/devicecode',
                data={'client_id': self.client_id, 'scope': ' '.join(scopes)},
            ) as resp:
                data = await resp.json()
                if 'error' in data:
                    return data
                data['expires'] = int(time.time() + data['expires_in'])
                return data

    async def poll_log_in(self, data: PollData) -> Union[TokensResponse, ErrorResponse]:
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.authority}/oauth2/v2.0/token',
                    data={
                        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                        'tenant': self.tenant,
                        'client_id': self.client_id,
                        'device_code': data['device_code'],
                    },
                ) as resp:
                    resp = await resp.json()
                    if resp.get('error') == 'authorization_pending':
                        await asyncio.sleep(data['interval'])
                        continue
                    if resp.get('error') == 'bad_verification_code':
                        raise ValueError(data['device_code'])
                    if resp.get('error'):
                        return resp
                    resp['expires'] = int(time.time() + resp['expires_in'])
                    return resp

    async def get_tokens(
        self, data: TokensResponse
    ) -> Union[TokensResponse, ErrorResponse]:
        expires = data['expires']
        if time.time() + 10 < expires:
            return data
        refresh_token = data['refresh_token']
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.authority}/oauth2/v2.0/token',
                data={
                    'tenant': self.tenant,
                    'client_id': self.client_id,
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                },
            ) as resp:
                resp = await resp.json()
                if 'error' in resp:
                    return resp
                resp['expires'] = int(time.time() + resp['expires_in'])
                return resp

    def parse_id_token(self, id_token: str) -> dict:
        return jwt.decode(
            id_token, audience=self.client_id, options={'verify_signature': False}
        )
