# -*- coding: utf-8 -*-
# Copyright 2014, 2015 OpenMarket Ltd
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

from twisted.internet import defer

from ._base import BaseHandler

import logging


logger = logging.getLogger(__name__)


class AdminHandler(BaseHandler):

    def __init__(self, hs):
        super(AdminHandler, self).__init__(hs)

    @defer.inlineCallbacks
    def get_whois(self, user):
        res = yield self.store.get_user_ip_and_agents(user)

        d = {}
        for r in res:
            device = d.setdefault(r["device_id"], {})
            session = device.setdefault(r["access_token"], [])
            session.append({
                "ip": r["ip"],
                "user_agent": r["user_agent"],
                "last_seen": r["last_seen"],
            })

        ret = {
            "user_id": user.to_string(),
            "devices": [
                {
                    "device_id": k,
                    "sessions": [
                        {
                            # "access_token": x, TODO (erikj)
                            "connections": y,
                        }
                        for x, y in v.items()
                    ]
                }
                for k, v in d.items()
            ],
        }

        defer.returnValue(ret)
