#!/bin/sh

export PYTHONPATH=$PYTHONPATH:.

./bin/ryu-manager --observe-links ryu.app.sdnhub_apps.fileserver ryu.app.sdnhub_apps.host_tracker_rest  ryu.app.rest_topology ryu.app.sdnhub_apps.stateless_lb_rest ryu.app.sdnhub_apps.tap_rest ryu.app.ofctl_rest
