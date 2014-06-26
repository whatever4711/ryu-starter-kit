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

import logging

import json
from webob import Response
import os
import mimetypes

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import dpset
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_0
from ryu.lib import ofctl_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication
from ryu.app.sdnhub_apps import stateless_lb, learning_switch
from ryu.ofproto import inet

LOG = logging.getLogger('ryu.app.sdnhub_apps.stateless_lb_rest')

# REST API
#
############# Configure loadbalancer
#
# create loadbalancer filter
# POST /v1.0/loadbalancer/create
#
# delete loadbalancer filter
# DELETE /v1.0/loadbalancer/delete
#

import re, socket

def is_mac_valid(x):
    if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", x.lower()):
        return True
    else:
        return False

def is_ip_valid(x):
    y = x.split('/')
    if len(y) > 2:
        return False
    try:
        socket.inet_aton(y[0])
        return True
    except socket.error:
       return False

class StatelessLBController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(StatelessLBController, self).__init__(req, link, data, **config)
        self.stateless_lb = data['stateless_lb']
        self.stateless_lb.set_learning_switch(data['learning_switch'])

    def is_config_data_valid(self, lb_config):
        if not is_ip_valid(lb_config['virtual_ip']):
            return False
        for server in lb_config['servers']:
            if not is_ip_valid(server['ip']) or not is_mac_valid(server['mac']):
                return False
        return True

    def create_loadbalancer(self, req, **_kwargs):
        try:
            lb_config = eval(req.body)
            if not self.is_config_data_valid(lb_config):
                return Response(status=400)

            self.stateless_lb.set_virtual_ip(lb_config['virtual_ip'])
            self.stateless_lb.set_server_pool(lb_config['servers'])
            self.stateless_lb.set_rewrite_ip_flag(lb_config['rewrite_ip'])

        except SyntaxError:
            LOG.error('Invalid syntax %s', req.body)
            return Response(status=400)

        return Response(status=200,content_type='application/json',
                    body=json.dumps({'status':'success'}))

    def delete_loadbalancer(self, req, **_kwargs):
        try:
            lb_config = eval(req.body)
            print lb_config
            if not self.is_config_data_valid(lb_config):
                return Response(status=400)

            self.stateless_lb.set_virtual_ip()
            self.stateless_lb.set_server_pool()

        except SyntaxError:
            LOG.error('Invalid syntax %s', req.body)
            return Response(status=400)

        return Response(status=200,content_type='application/json',
                    body=json.dumps({'status':'success'}))


class StatelessLBRestApi(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,
                    ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'stateless_lb': stateless_lb.StatelessLB,
        'learning_switch': learning_switch.L2LearningSwitch
    }

    def __init__(self, *args, **kwargs):
        super(StatelessLBRestApi, self).__init__(*args, **kwargs)
        stateless_lb = kwargs['stateless_lb']
        learning_switch = kwargs['learning_switch']
        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {}
        self.data['waiters'] = self.waiters
        self.data['stateless_lb'] = stateless_lb
        self.data['learning_switch'] = learning_switch

        wsgi.registory['StatelessLBController'] = self.data
        mapper = wsgi.mapper

        mapper.connect('loadbalancer', '/v1.0/loadbalancer/create',
                       controller=StatelessLBController, action='create_loadbalancer',
                       conditions=dict(method=['POST']))

        mapper.connect('loadbalancer', '/v1.0/loadbalancer/delete',
                       controller=StatelessLBController, action='delete_loadbalancer',
                       conditions=dict(method=['POST']))


