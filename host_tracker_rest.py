# Copyright (C) 2014 SDN Hub
#
# Licensed under the GNU GENERAL PUBLIC LICENSE, Version 3.
# You may not use this file except in compliance with this License.
# You may obtain a copy of the License at
#
#    http://www.gnu.org/licenses/gpl-3.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.

# REST API
#
############# Host tracker ##############
#
# get all hosts
# GET /hosts
#
# get all hosts associated with a switch
# GET /hosts/{dpid}
#
#

import logging
import json
from webob import Response
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.app.wsgi import ControllerBase, WSGIApplication, route

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.ofproto import ether
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.app.sdnhub_apps import host_tracker
from ryu.lib import dpid as dpid_lib

class HostTrackerController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(HostTrackerController, self).__init__(req, link, data, **config)
        self.host_tracker = data['host_tracker']
        self.dpset = data['dpset']

    @route('hosts', '/v1.0/hosts', methods=['GET'])
    def get_all_hosts(self, req, **kwargs):
        return Response(status=200,content_type='application/json',
                body=json.dumps(self.host_tracker.hosts))

    @route('hosts', '/v1.0/hosts/{dpid}', methods=['GET'])
            #requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_hosts(self, req, dpid, **_kwargs):
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return Response(status=404)

        switch_hosts = {}
        for key,val in self.host_tracker.hosts.iteritems():
            if val['dpid']== dpid_lib.dpid_to_str(dp.id):
                switch_hosts[key] = val

        return Response(status=200,content_type='application/json',
                body=json.dumps(switch_hosts))


class HostTrackerRestApi(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,
            ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
            'dpset': dpset.DPSet,
            'wsgi': WSGIApplication,
            'host_tracker': host_tracker.HostTracker
            }

    def __init__(self, *args, **kwargs):
        super(HostTrackerRestApi, self).__init__(*args, **kwargs)
        dpset = kwargs['dpset']
        wsgi = kwargs['wsgi']
        host_tracker = kwargs['host_tracker']

        self.data = {}
        self.data['dpset'] = dpset
        self.data['waiters'] = {}
        self.data['host_tracker'] = host_tracker

        wsgi.register(HostTrackerController, self.data)
        #mapper = wsgi.mapper

        #mapper.connect('hosts', '/v1.0/hosts', controller=HostTrackerController, action='get_all_hosts',
        #        conditions=dict(method=['GET']))
        #mapper.connect('hosts', '/v1.0/hosts/{dpid}', controller=HostTrackerController, action='get_hosts',
        #        conditions=dict(method=['GET']), requirements={'dpid': dpid_lib.DPID_PATTERN})
