# -*- coding: utf-8 -*-
# Copyright 2014 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from synapse.push import Pusher, PusherConfigException
from synapse.http.client import SimpleHttpClient

from twisted.internet import defer

import logging

logger = logging.getLogger(__name__)


class HttpPusher(Pusher):
    def __init__(self, _hs, instance_handle, user_name, app_id,
                 app_display_name, device_display_name, pushkey, pushkey_ts,
                 data, last_token, last_success, failing_since):
        super(HttpPusher, self).__init__(
            _hs,
            instance_handle,
            user_name,
            app_id,
            app_display_name,
            device_display_name,
            pushkey,
            pushkey_ts,
            data,
            last_token,
            last_success,
            failing_since
        )
        if 'url' not in data:
            raise PusherConfigException(
                "'url' required in data for HTTP pusher"
            )
        self.url = data['url']
        self.httpCli = SimpleHttpClient(self.hs)
        self.data_minus_url = {}
        self.data_minus_url.update(self.data)
        del self.data_minus_url['url']

    @defer.inlineCallbacks
    def _build_notification_dict(self, event):
        # we probably do not want to push for every presence update
        # (we may want to be able to set up notifications when specific
        # people sign in, but we'd want to only deliver the pertinent ones)
        # Actually, presence events will not get this far now because we
        # need to filter them out in the main Pusher code.
        if 'event_id' not in event:
            defer.returnValue(None)

        ctx = yield self.get_context_for_event(event)

        d = {
            'notification': {
                'transition': 'new',
                # everything is new for now: we don't have read receipts
                'id': event['event_id'],
                'type': event['type'],
                'from': event['user_id'],
                # we may have to fetch this over federation and we
                # can't trust it anyway: is it worth it?
                #'from_display_name': 'Steve Stevington'
                #'counts': { -- we don't mark messages as read yet so
                # we have no way of knowing
                #    'unread': 1,
                #    'missed_calls': 2
                # },
                'devices': [
                    {
                        'app_id': self.app_id,
                        'pushkey': self.pushkey,
                        'pushkey_ts': long(self.pushkey_ts / 1000),
                        'data': self.data_minus_url
                    }
                ]
            }
        }

        if len(ctx['aliases']):
            d['notification']['roomAlias'] = ctx['aliases'][0]
        if 'name' in ctx:
            d['notification']['roomName'] = ctx['name']

        defer.returnValue(d)

    @defer.inlineCallbacks
    def dispatch_push(self, event):
        notification_dict = yield self._build_notification_dict(event)
        if not notification_dict:
            defer.returnValue([])
        try:
            resp = yield self.httpCli.post_json_get_json(self.url, notification_dict)
        except:
            logger.exception("Failed to push %s ", self.url)
            defer.returnValue(False)
        rejected = []
        if 'rejected' in resp:
            rejected = resp['rejected']
        defer.returnValue(rejected)