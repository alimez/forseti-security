# Copyright 2017 The Forseti Security Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

"""
Flatten the following attributes in firewall rules.
IPProtocol, ports,

Example:
"allowed": [{"IPProtocol": "tcp,udp", "ports": ["1","50051"]}]
This will generate 4 Firewall rule objects
- action: allowed, IPProtocol: tcp, ports: 1
- action: allowed, IPProtocol: tcp, ports: 1
- action: allowed, IPProtocol: udp, ports: 50051
- action: allowed, IPProtocol: udp, ports: 50051

Source or destination
You specify either a source or a destination, but not both, depending 
on the direction of the firewall you create:

For ingress (inbound) rules, the target parameter specifies the destination 
VMs for traffic; you cannot use the destination parameter. You specify 
the source by using the source parameter.

For egress (outbound) rules, the target parameter specifies the source VMs 
for traffic; you cannot use the source parameter. You specify the destination 
by using the destination parameter.

You cannot mix and match service accounts and network tags in any firewall rule:

You cannot use target service accounts and target tags together in any firewall 
rule (ingress or egress).

{
"allowed": [{"IPProtocol": "tcp", "ports": ["50051"]}],
"creationTimestamp": "2018-02-28T21:49:07.739-08:00",
"description": "",
"direction": "INGRESS", 
"disabled": false, 
"id": "1002375335368075964", 
"kind": "compute#firewall", 
"name": "forseti-server-allow-grpc-20180228211432", 
"network": "https://www.googleapis.com/compute/beta/projects/joe-project-p2/global/networks/default", 
"priority": 0, 
"selfLink": "https://www.googleapis.com/compute/beta/projects/joe-project-p2/global/firewalls/forseti-server-allow-grpc-20180228211432", 
"sourceRanges": ["10.128.0.0/9"], 
"targetServiceAccounts": ["forseti-gcp-server-1432@joe-project-p2.iam.gserviceaccount.com"]
}

"""


class FirewallRule(object):
    """Flattened firewall rule."""
    def __init__(self,
                 creation_timestamp,
                 priority,
                 ip_addr,
                 ip_bits,
                 identifier,
                 action,
                 ip_protocol,
                 ports,
                 direction,
                 disabled):
        self.creation_timestamp = creation_timestamp
        self.priority = priority
        self.ip_addr = ip_addr
        self.ip_bits = ip_bits
        self.identifier = identifier
        self.action = action
        self.ip_protocol = ip_protocol
        self.ports = ports
        self.direction = direction
        self.disabled = disabled

    @classmethod
    def from_json(cls, firewall_rule_data):
        """Generate a list of flattened firewall rule objects based
         on the given firewall resource data in string format.

         Args:
            firewall_rule_data (str): Firewall rule resource data,
                in JSON string format.

        Returns:
             list: A list of flattened firewall rule objects.
         """
        json_dict = json.loads(firewall_rule_data)

        action = 'allowed'

        if action not in json_dict:
            action = 'denied'

        identifiers = []

        if 'targetServiceAccounts' in json_dict:
            identifiers = json_dict.get('targetServiceAccounts', [])
        elif 'targetTags' in json_dict:
            identifiers = json_dict.get('targetTags', [])

        direction = json_dict.get('direction')  # INGREE OR EGRESS

        if direction.upper() == 'INGRESS':
            ip_addrs_cidr = json_dict.get('sourceRanges')
        else:
            ip_addrs_cidr = json_dict.get('destinationRanges')

        ip_addr_bits_list = [ip_addr_cidr.split('/') for ip_addr_cidr in ip_addrs_cidr]

        protocol_mappings = json_dict.get(action, [])

        flattened_firewall_rules = []

        creation_timestamp = json_dict.get('creationTimestamp')
        priority = json_dict.get('priority')
        disabled = False if json_dict.get('disabled') == 'false' else True

        for identifier in identifiers:
            for (ip_addr, ip_bits) in ip_addr_bits_list:
                for protocol_mapping in protocol_mappings:
                    ip_protocols = protocol_mapping.get('IPProtocol', [])
                    corresponding_ports = protocol_mapping.get('ports', [])

                    flattened_ports = cls._flatten_ports(corresponding_ports)
                    for ip_protocol in ip_protocols:
                        flattened_firewall_rules.append(
                            FirewallRule(
                                creation_timestamp,
                                priority,
                                ip_addr,
                                ip_bits,
                                identifier,
                                action,
                                ip_protocol,
                                flattened_ports,
                                direction,
                                disabled
                            ))
        return flattened_firewall_rules

    @classmethod
    def _flatten_ports(cls, ports):
        """Flatten the list of ports.

        Example:
            Input: ["1-5", "50051"]
            Output: ["1", "2", "3", "4", "5", "50051"]

        Args:
            corresponding_ports (list): List of corresponding ports.

        Returns:
            list: Flattened ports.
        """

        flattened_ports = []

        # Type of representation that can be in the ports
        # Range - e.g. "0-5"
        # Single port - e.g. "50051"
        # Empty - e.g. [] - this represents all ports.

        for port in ports:
            if '-' in port:
                # This is port range, flatten the range.
                port_range = port.split('-')
                start = int(port_range[0])
                end = int(port_range[1])
                flattened = [i for i in range(start, end+1)]
                flattened_ports += flattened
            else:
                # Single port.
                flattened_ports.append(int(port))

        # Cast the list to set to remove duplicates,
        # and cast it back to list.
        flattened_ports = list(set(flattened_ports))

        # Max port is 65535.
        # if not flattened_ports:
        #    flattened_ports = [i for i in range(0, 65536)]

        return flattened_ports
