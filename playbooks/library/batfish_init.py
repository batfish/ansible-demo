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
module: batfish_init

short_description: Initializes new network snapshot in Batfish

version_added: "2.7"

description:
    - "Initializes new network snapshot in Batfish, using Pybatfish"

options:
    base_name:
        description:
            - Name of the base snapshot to fork from.  If no name is provided, a new snapshot is created from scratch.
        required: false
    host:
        description:
            - Host running the C(Batfish) service.
        required: false
    name:
        description:
            - Name of the new snapshot to create.
        required: true
    network:
        description:
            - Name of the network to create the new snapshot in.
        required: true
    path:
        description:
            - Path to the directory containing snapshot files.
        required: true

author:
    - Spencer Fraint (`@sfraint <https://github.com/sfraint>`_)

requirements:
    - "pybatfish"
'''

EXAMPLES = '''
# Initialize a new snapshot
- name: Init new snapshot
  batfish_init:
    name: base_snapshot
    network: test_network
    path: /path/to/snapshot_dir/

# Fork a new snapshot from an existing one
- name: Fork from base snapshot
  batfish_init:
    base_name: base_snapshot
    name: new_snapshot
    network: test_network
    path: /path/to/additional_files/
'''

RETURN = '''
name:
    description: Name of the snapshot created
    type: str
network:
    description: Name of the network containing the new snapshot
    type: str
result:
    description: Result of the action performed
    type: str
'''

from ansible.module_utils.basic import AnsibleModule

try:
    import logging
    from pybatfish.client.commands import (bf_fork_snapshot, bf_init_snapshot,
                                           bf_session, bf_set_network)
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
        base_name=dict(type='str', required=False, default=None),
        host=dict(type='str', required=False, default='localhost'),
        name=dict(type='str', required=True),
        network=dict(type='str', required=True),
        path=dict(type='str', required=True)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        name='',
        network='',
        result='',
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not pybatfish_found:
        module.fail_json(msg='Python module Pybatfish is required')

    if module.check_mode:
        return result

    base_name = module.params['base_name']
    name = module.params['name']
    path = module.params['path']

    try:
        bf_session.coordinatorHost = module.params['host']
        network = bf_set_network(module.params['network'])
    except Exception as e:
        module.fail_json(msg='Failed to set network: {}'.format(e), **result)
    result['network'] = network

    try:
        if base_name is not None:
            name = bf_fork_snapshot(add_files=path, base_name=base_name, name=name, overwrite=True)
            result['result'] = "Forked snapshot '{}' from '{}' adding files at '{}'".format(name, base_name, path)
        else:
            name = bf_init_snapshot(path, name, overwrite=True)
            result['result'] = "Created snapshot '{}' from files at '{}'".format(name, path)
    except Exception as e:
        module.fail_json(msg='Failed to init snapshot: {}'.format(e), **result)
    result['name'] = name

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    result['changed'] = True

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
