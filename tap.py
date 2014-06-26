# Copyright (C) 2014 SDN Hub
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import struct
import random
import ryu.utils

from ryu.base import app_manager
from ryu.topology import event as topo_event
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import HANDSHAKE_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4

from ryu.ofproto import ether
from ryu.controller import dpset

import networkx as nx

LOG = logging.getLogger('ryu.app.sdnhub_apps.tap')

class StarterTap(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(StarterTap, self).__init__(*args, **kwargs)

        self.broadened_field = {'dl_host': ['dl_src', 'dl_dst'],
                                'nw_host': ['nw_src', 'nw_dst'],
                                'tp_port': ['tp_src', 'tp_dst']}


    @set_ev_cls(ofp_event.EventOFPErrorMsg, [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def error_msg_handler(self, ev):
        msg = ev.msg
      
        LOG.info('OFPErrorMsg received: type=0x%02x code=0x%02x message=%s',
                        msg.type, msg.code, ryu.utils.hex_array(msg.data))


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser

        # Delete all existing rules on the switch
        mod = ofproto_parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                             out_port=ofproto.OFPP_ANY,out_group=ofproto.OFPG_ANY)
        datapath.send_msg(mod)


    def change_field(self, old_attrs, original, new):
        new_attrs = {}
        for key, val in old_attrs.items():
            if (key == original):
                new_attrs[new] = val
            else:
                new_attrs[key] = val
        return new_attrs

    def create_tap(self, filter_data):
        LOG.debug("Creating tap with filter = %s", str(filter_data))

        # If dl_host, nw_host or tp_port are used, the recursively call the individual filters.
        # This causes the match to expand and more rules to be programmed.
        result = True
        filter_data.setdefault('fields', {})
        filter_fields = filter_data['fields']

        for key, val in self.broadened_field.iteritems():
            if key in filter_fields:
                for new_val in val:
                    filter_data['fields'] = self.change_field(filter_fields, key, new_val)
                    result = result and self.create_tap(filter_data)

                return result

        # If match fields are exact, then proceed programming switches

        # Iterate over all the sources and sinks, and collect the individual
        # hop information. It is possible that a switch is both a source,
        # a sink and an intermediate hop.
        for source in filter_data['sources']:
            for sink in filter_data['sinks']:

                # Handle error case
                if source == sink:
                    continue

                # In basic version, source and sink are same switch
                if source['dpid'] != sink['dpid']:
                    LOG.debug("Mismatching source and sink switch")
                    return False

                datapath = self.dpset.get(source['dpid'])

                # If dpid is invalid, return
                if datapath is None:
                    LOG.debug("Unable to get datapath for id = %s", str(source['dpid']))
                    return False

                ofproto = datapath.ofproto
                ofproto_parser = datapath.ofproto_parser

                in_port = source['port_no']
                out_port = sink['port_no']
                filter_fields = filter_data['fields'].copy()

                ######## Create action list
                actions = [ofproto_parser.OFPActionOutput(out_port)]

                ######## Create match
                if in_port != 'all':  # If not sniffing on all in_ports
                    filter_fields['in_port'] = in_port
                match = ofctl_v1_3.to_match(datapath, filter_fields)

                ######## Cookie might come handy
                cookie = random.randint(0, 0xffffffffffffffff)

                inst = [ofproto_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

                # install the flow in the switch
                mod = ofproto_parser.OFPFlowMod(
                            datapath=datapath, match=match, 
                            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                            instructions=inst, cookie=cookie)

                datapath.send_msg(mod)

                LOG.debug("Flow inserted to switch %x: cookie=%s, out_port=%d, match=%s",
                                  datapath.id, str(cookie), out_port, str(filter_fields))

        LOG.info("Created tap with filter = %s", str(filter_data))
        return True


    def delete_tap(self, filter_data):
        LOG.debug("Deleting tap with filter %s", str(filter_data))

        # If dl_host, nw_host or tp_port are used, the recursively call the individual filters.
        # This causes the match to expand and more rules to be programmed.
        filter_data.setdefault('fields', {})
        filter_fields = filter_data['fields']

        for key, val in self.broadened_field.iteritems():
            if key in filter_fields:

                for new_val in val:
                    filter_data['fields'] = self.change_field(filter_fields, key, new_val)
                    self.delete_tap(filter_data)

                return

        # If match fields are exact, then proceed programming switches
        for source in filter_data['sources']:
            in_port = source['port_no']
            filter_fields = filter_data['fields'].copy()
            if in_port != 'all':  # If not sniffing on all in_ports
                filter_fields['in_port'] = in_port

            datapath = self.dpset.get(source['dpid'])

            # If dpid is invalid, return
            if datapath is None:
                continue

            ofproto = datapath.ofproto
            ofproto_parser = datapath.ofproto_parser
                    
            match = ofctl_v1_3.to_match(datapath, filter_fields)

            mod = ofproto_parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                          match = match, out_port=ofproto.OFPP_ANY,out_group=ofproto.OFPG_ANY)

            datapath.send_msg(mod)

