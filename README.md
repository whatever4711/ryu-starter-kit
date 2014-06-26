SDN Starter Kit 
===============

This software package is offered to promote SDN trial and adoption in
smaller proof-of-concept deployments. The applications are built over
the [Ryu](http://osrg.github.io/ryu/) controller platform.
The current code base offers simple implementations of the applications /
modules like topology visualization, monitoring tap management, server
load-balancing. More features will be coming in soon.

If you are interested in a trial of a full solution suite that is
production ready, please
[Sign-up](http://sdnhub.org/releases/trial-signup/).

# Installation and Running
* Download VM with pre-installed software that will autostart

* Alternatively, you can setup from scratch using these commands:

        $ git clone https://github.com/osrg/ryu
        $ cd ryu/ryu/app
        $ git clone https://bitbucket.org/sdnhub/ryu-starter-kit sdnhub_apps

* It is recommended to install the following packages if you do not already
have it in your Python environment:

        $ sudo apt-get install -y libxslt1-dev msgpack-python python-setuptools python-nose python-pip
        $ sudo pip install ipaddr networkx bitarray netaddr oslo.config routes webob paramiko mock eventlet xml_compare pyflakes pylint

* You can now run the controller and the applications as follows:

        $ cd ~/ryu
        $ export PYTHONPATH=$PYTHONPATH:.
        $ ./ryu/app/sdnhub_apps/run_sdnhub_apps.sh

* Access the configuration page by visiting
http://ip-address-of-controller:8080/

# Solution release notes
* Current implementation works with OpenFlow 1.3 physical and virtual
switches.

* **Web GUI**: The GUI is sourced from the application directory and
served over the WSGI server already implemented by Ryu for the REST API
calls. All solutions expose a north-bound API that is used by
Javascript modules embedded in the HTML page to make the output dynamic. 

* **Host tracker** : The host tracker module tracks all the hosts in the
system based on the PacketIn messages received at the controller. The
entries in the cache expired after 300 seconds of not hearing from a
host.

* **Topology** : Displays the switches and hosts. The hosts are pulled
from the host tracker application, while the switches and links are
pulled from the standard topology discovery module. Presently, the
topology does not auto-refresh.

* **Tap manager** : The simple tap manager inserts custom rules in the
switch based on the filter criteria specified in the UI. In the current
implementation, the source and sink need to be on the same switch.
The implementation is stateless and leaves it to the user to remember
what taps have already been created.

* **Load balancer**: This simple load balancer application creates a
single pool of servers and assigns incoming requests to different
servers in the pool on a round-robin basis. The current implementation
is stateless, does not perform a L7 termination, and only load-balances
TCP requests.

# Maintainers
This code base is maintained by [SDN Hub](http://sdnhub.org). The author
is Srini Seetharaman (srini.seetharaman@gmail.com)

# Support/discussion forum

(http://sdnhub.org/forums/forum/solution-suite/ryu-sdn-starter-kit/)

