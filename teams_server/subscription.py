from datetime import datetime
from typing import Optional, TypedDict

from aiohttp.client import request

from graph import Auth, TokensResponse


class GraphError(RuntimeError):
    def __init__(self, msg: str, *args):
        self.msg = msg
        super().__init__(*args)


class GraphSubscriptionBase(TypedDict, total=True):
    id: str
    resource: str
    applicationId: str
    changeType: str
    clientState: str
    notificationUrl: str
    expirationDateTime: str
    includeResourceData: bool


class GraphSubscription(GraphSubscriptionBase, total=False):
    lifecycleNotificationUrl: str


class LifecycleNotification(TypedDict):
    subscriptionId: str
    subscriptionExpirationDateTime: str
    tenantId: str
    clientState: str
    lifecycleEvent: str


def format_datetime(time: datetime) -> str:
    if time.tzinfo is not None:
        offset = time.utcoffset()
        assert offset
        time = (time - offset).replace(tzinfo=None)
    return time.isoformat() + 'Z'


class GraphSubscriptions:
    def __init__(
        self, client_state: str, auth: Auth
    ) -> None:
        self.client_state = client_state
        self.auth = auth

    async def _get_token(self, auth: TokensResponse) -> str:
        tokens = await self.auth.get_tokens(auth)
        if 'error' in tokens:
            raise GraphError(f'Error refreshing tokens: {tokens}')
        return 'Bearer ' + tokens['access_token']

    async def get_subscription(
        self, auth: TokensResponse, id: str
    ) -> GraphSubscription:
        async with request(
            'GET',
            f'https://graph.microsoft.com/v1.0/subscriptions/{id}',
            headers={'Authorization': await self._get_token(auth)},
        ) as resp:
            return await resp.json()

    async def remove_subscription(self, auth: TokensResponse, id: str) -> bool:
        async with request(
            'DELETE',
            f'https://graph.microsoft.com/v1.0/subscriptions/{id}',
            headers={'Authorization': await self._get_token(auth)},
        ) as resp:
            return resp.status == 204

    async def add_subscription(
        self,
        auth: TokensResponse,
        notification_url: str,
        resource: str,
        expiration: datetime,
        client_state: str,
        lifecycle_notification_url: Optional[str] = None,
        change_type: str = 'created',
    ) -> GraphSubscription:
        data = {
            'changeType': change_type,
            'notificationUrl': notification_url,
            'resource': resource,
            'expirationDateTime': format_datetime(expiration),
            'clientState': client_state,
        }
        if lifecycle_notification_url is not None:
            data.update(lifecycleNotificationUrl=lifecycle_notification_url)
        async with request(
            'POST',
            f'https://graph.microsoft.com/v1.0/subscriptions',
            headers={'Authorization': await self._get_token(auth)},
            json=data,
        ) as resp:
            return await resp.json()

    async def renew_subscription(
        self, auth: TokensResponse, id: str, expiration: datetime
    ) -> GraphSubscription:
        async with request(
            'PATCH',
            f'https://graph.microsoft.com/v1.0/subscriptions/{id}',
            headers={'Authorization': await self._get_token(auth)},
            json={'expirationDateTime': format_datetime(expiration)},
        ) as resp:
            return await resp.json()

    async def parse_lifecycle_notification(
        self,
        auth: TokensResponse,
        notification: LifecycleNotification,
        notification_url: str,
        resource: str,
        expiration: datetime,
        client_state: str,
        lifecycle_notification_url: Optional[str] = None,
        change_type: str = 'created',
    ):
        event = notification['lifecycleEvent']
        if event == 'reauthorizationRequired':
            subscription = await self.renew_subscription(
                auth, notification['subscriptionId'], expiration
            )
            if subscription.get('id') != notification['subscriptionId']:
                raise GraphError(f'Weird renew response: {subscription}')
        elif event == 'subscriptionRemoved':
            subscription = await self.add_subscription(
                auth,
                notification_url=notification_url,
                resource=resource,
                expiration=expiration,
                client_state=client_state,
                lifecycle_notification_url=lifecycle_notification_url,
                change_type=change_type,
            )
            if 'id' not in subscription:
                raise GraphError(f'Weird recreate response: {subscription}')
            return subscription['id']
