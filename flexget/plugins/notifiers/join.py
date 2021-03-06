from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

import logging

from flexget import plugin
from flexget.event import event
from flexget.plugin import PluginWarning
from flexget.config_schema import one_or_more
from flexget.utils.requests import Session as RequestSession, TimedLimiter
from requests.exceptions import RequestException

__name__ = 'join'
log = logging.getLogger(__name__)

requests = RequestSession(max_retries=3)
requests.add_domain_limiter(TimedLimiter('appspot.com', '5 seconds'))

JOIN_URL = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush'


class JoinNotifier(object):
    """
    Example::

      join:
        [api_key: <API_KEY> (your join api key. Only required for 'group' notifications)]
        [group: <GROUP_NAME> (name of group of join devices to notify. 'all', 'android', etc.)
        [device: <DEVICE_ID> (can also be a list of device ids)]
        [url: <NOTIFICATION_URL>]
        [sms_number: <NOTIFICATION_SMS_NUMBER>]
        [icon: <NOTIFICATION_ICON>]
    """
    schema = {
        'type': 'object',
        'properties': {
            'api_key': {'type': 'string'},
            'group': {
                'type': 'string',
                'enum': ['all', 'android', 'chrome', 'windows10', 'phone', 'tablet', 'pc']
            },
            'device': one_or_more({'type': 'string'}),
            'url': {'type': 'string'},
            'icon': {'type': 'string'},
            'sms_number': {'type': 'string'},
            'priority': {'type': 'integer', 'minimum': -2, 'maximum': 2}
        },
        'dependencies': {
            'group': ['api_key']
        },
        'error_dependencies': '`api_key` is required to use Join `group` notifications',
        'oneOf': [
            {'required': ['device']},
            {'required': ['api_key']},
        ],
        'error_oneOf': 'Either a `device` to notify, or an `api_key` must be specified, and not both',
        'additionalProperties': False
    }

    def notify(self, title, message, config):
        """
        Send Join notifications.
        """
        notification = {'title': title, 'text': message, 'url': config.get('url'),
                        'icon': config.get('icon'), 'priority': config.get('priority')}
        if config.get('api_key'):
            config.setdefault('group', 'all')
            notification['apikey'] = config['api_key']
            notification['deviceId'] = 'group.' + config['group']
        else:
            if isinstance(config['device'], list):
                notification['deviceIds'] = ','.join(config['device'])
            else:
                notification['deviceId'] = config['device']

        if config.get('sms_number'):
            notification['smsnumber'] = config['sms_number']
            notification['smstext'] = message

        try:
            response = requests.get(JOIN_URL, params=notification)
        except RequestException as e:
            raise PluginWarning(e.args[0])
        else:
            error = response.json().get('errorMessage')
            if error:
                raise PluginWarning(error)


@event('plugin.register')
def register_plugin():
    plugin.register(JoinNotifier, __name__, api_ver=2, interfaces=['notifiers'])
