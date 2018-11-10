#!/usr/bin/python
#   Copyright 2018 The Batfish Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: batfish_searchfilters

short_description: Runs searchfilters question in Batfish

version_added: "2.7"

description:
    - "Runs searchfilters question in Batfish, using Pybatfish"

options:
    action:
        description:
            - The behavior that you want evaluated. Only one option should be selected.
        required: if C(reference_snapshot) is not specified
        choices: [ "permit", "deny", "matchLine <line number>" ]
    destination_ips:
        description:
            - Evaluate flows destined for the specified IPs.
        required: false
    destination_ports:
        description:
            - Evaluate flows destined for the specified port.
        required: false
    filters:
        description:
            - Only evaluate filters that match this regex.
        required: false
    host:
        description:
            - Host running the C(Batfish) service.
        required: false
    invert_search:
        description:
            - Search for packet headers outside the specified headerspace, rather than inside the space.
        required: false
    ip_protocols:
        description:
            - Evaluate flows of the specified IP protocols.
        required: false
    network:
        description:
            - Name of the network containing the specified snapshot.
        required: true
    nodes:
        description:
            - Only evaluate filters present on nodes matching this regex.
        required: false
    reference_snapshot:
        description:
            - Name of the reference snapshot to run against, only needed if running differentially.
        required: if C(action) is not specified
    source_ips:
        description:
            - Evaluate flows starting at the specified source IPs.
        required: false
    source_ports:
        description:
            - Evaluate flows starting at the specified source ports.
        required: false
    name:
        description:
            - Name of snapshot to run the question on.
        required: true

author:
    - Spencer Fraint (`@sfraint <https://github.com/sfraint>`_)

requirements:
    - "pybatfish"
'''

EXAMPLES = '''
- name: Run searchfilters to see if intended traffic is permitted through C(acl_in) ACL on node C(rtr-with-acl)
  batfish_searchfilters:
    name: "base_snapshot"
    network: "test_network"
    action: "permit"
    filters: "acl_in"
    nodes: "rtr-with-acl"
    source_ips: "10.10.10.0/24"
    destination_ips: "18.18.18.0/27"
    ip_protocols: "tcp"
    destination_ports: "80,8080"

- name: Run searchfilters to see if there are differences between two snapshots' C(acl_in) ACL on nodes C(nodeA) or C(nodeB), other than for the specified traffic
  batfish_searchfilters:
    name: "base_snapshot"
    reference_snapshot: "candidate_snapshot"
    network: "test_network"
    filters: "acl_in"
    nodes: "nodeA|nodeB"
    source_ips: "10.10.10.0/24"
    destination_ips: "18.18.18.0/27"
    ip_protocols: "tcp"
    destination_ports: "80,8080"
    invert_search: yes
'''

RETURN = '''
result_verbose:
    description: Detailed result of searchfilters
    type: dictionary
'''

from ansible.module_utils.basic import AnsibleModule

try:
    import json
    from pybatfish.client.commands import (bf_get_analysis_answers, bf_get_answer, bf_init_analysis,
                                           bf_run_analysis, bf_set_network, bf_session)
    from pybatfish.datamodel.flow import HeaderConstraints
    # noinspection PyUnresolvedReferences
    from pybatfish.question import bfq, list_questions, load_questions  # noqa F401
except Exception as e:
    pybatfish_found = False
else:
    pybatfish_found = True


def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        action=dict(type='str', required=False, default='permit'),
        destination_ips=dict(type='str', required=False, default=None),
        destination_ports=dict(type='str', required=False, default=None),
        filters=dict(type='str', required=False, default=".*"),
        host=dict(type='str', required=False, default='localhost'),
        invert_search=dict(type='bool', required=False, default=False),
        ip_protocols=dict(type='list', required=False, default=None),
        network=dict(type='str', required=True),
        nodes=dict(type='str', required=False, default=".*"),
        reference_snapshot=dict(type='str', required=False, default=None),
        source_ips=dict(type='str', required=False, default=None),
        source_ports=dict(type='str', required=False, default=None),
        name=dict(type='str', required=True)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        result_verbose='',
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[
            ['action', 'reference_snapshot']
        ]
    )

    if not pybatfish_found:
        module.fail_json(msg='Python module Pybatfish is required')

    if module.check_mode:
        return result

    snapshot = module.params['name']
    reference_snapshot = module.params['reference_snapshot']

    try:
        bf_session.coordinatorHost = module.params['host']
        network = bf_set_network(module.params['network'])
    except Exception as e:
        module.fail_json(msg='Failed to set network: {}'.format(e), **result)

    try:
        load_questions()
    except Exception as e:
        module.fail_json(msg='Failed to load questions: {}'.format(e), **result)

    try:
        headers = HeaderConstraints(srcIps=module.params['source_ips'],
                                    dstIps=module.params['destination_ips'],
                                    ipProtocols=module.params['ip_protocols'],
                                    srcPorts=module.params['source_ports'],
                                    dstPorts=module.params['destination_ports'])
    except Exception as e:
        module.fail_json(msg='Failed to create header constraint: {}'.format(e), **result)

    try:
        filters = module.params['filters']
        nodes = module.params['nodes']
        action = module.params['action']
        invert_search = module.params['invert_search']
        q = bfq.searchfilters(headers=headers,
                              filters=filters,
                              nodes=nodes,
                              action=action,
                              invertSearch=invert_search)
        q_name = q.get_name()
        answer_obj = q.answer(snapshot=snapshot,
                              reference_snapshot=reference_snapshot)
        answer_dict = bf_get_answer(questionName=q_name,
                                    snapshot=snapshot,
                                    reference_snapshot=reference_snapshot)
    except Exception as e:
        module.fail_json(msg='Failed to answer question: {}'.format(e), **result)

    answer_element = answer_dict["answerElements"][0]
    result['result_verbose'] = answer_element["rows"] if "rows" in answer_element else []

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
