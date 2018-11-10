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
module: batfish_policy

short_description: Runs policy in Batfish

version_added: "2.7"

description:
    - "Runs (and optionally initializes) policy in Batfish, using Pybatfish"

options:
    policy_name:
        description:
            - Name of the policy to run.  If not specified, all analyses will be run.
        required: false
    host:
        description:
            - Host running the C(Batfish) service.
        required: false
    name:
        description:
            - Name of the snapshot to run the policy on.
        required: true
    network:
        description:
            - Name of the network containing the specified snapshot.
        required: true
    new:
        description:
            - If C(yes), a new policy is created with the supplied path.  Otherwise an existing policy is run.
        required: false
    path:
        description:
            - Path to the checks to add to the new policy.
        required: if new is C(yes)

author:
    - Spencer Fraint (`@sfraint <https://github.com/sfraint>`_)

requirements:
    - "pybatfish"
'''

EXAMPLES = '''
# Create and run a new policy
- name: Create and run new policy
  batfish_policy:
    name: base_snapshot
    network: test_network
    new: yes
    policy_name: policy_name
    path: /path/to/policy_dir/

# Run an existing policy
- name: Run existing policy
    name: base_snapshot
    network: test_network
    policy_name: policy_name
'''

RETURN = '''
result:
    description: Pass/Fail result of each check in the policy
    type: str
result_verbose:
    description: Detailed result of each check in the policy
    type: str
summary:
    description: Pass/Fail result of the policy overall
    type: str
'''

PASS = 'PASS'
FAIL = 'FAIL'

from ansible.module_utils.basic import AnsibleModule

try:
    import json
    from pybatfish.client.commands import (bf_get_analysis_answers, bf_init_analysis,
                                           bf_list_analyses, bf_run_analysis,
                                           bf_set_network, bf_session)
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
        policy_name=dict(type='str', required=False, default=None),
        host=dict(type='str', required=False, default='localhost'),
        name=dict(type='str', required=True),
        network=dict(type='str', required=True),
        new=dict(type='bool', required=False, default=False),
        path=dict(type='str', required=False)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        result='',
        result_verbose='',
        summary=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            [ "new", True, [ "path", "policy_name" ] ] # path and name are required if adding a new policy
        ]
    )

    if not pybatfish_found:
        module.fail_json(msg='Python module Pybatfish is required')

    if module.check_mode:
        return result

    snapshot_name = module.params['name']
    policy_name = module.params['policy_name']

    try:
        bf_session.coordinatorHost = module.params['host']
        network = bf_set_network(module.params['network'])
    except Exception as e:
        module.fail_json(msg='Failed to set network: {}'.format(e), **result)

    try:
        if module.params['new']:
            bf_init_analysis(policy_name, module.params['path'])
    except Exception as e:
        module.fail_json(msg='Failed to initialize policy: {}'.format(e), **result)

    try:
        if policy_name is not None:
            policy_results = {policy_name: _run_policy(policy_name, snapshot_name)}
        else:
            policy_results = {a: _run_policy(a, snapshot_name) for a in bf_list_analyses()}
    except Exception as e:
        module.fail_json(msg='Failed to answer policy: {}'.format(e), **result)

    result['result'] = {}
    result['result_verbose'] = {}
    failure = False
    # If a check's summary.numFailed is 0, we assume the check PASSed
    for policy in policy_results:
        policy_result = policy_results[policy]
        result['result'][policy] = {
            k: PASS if policy_result[k]['summary']['numFailed'] == 0 else FAIL for k in policy_result
        }
        failure |= FAIL in result['result'][policy].values()

        result['result_verbose'][policy] = {
            k: policy_result[k]['answerElements'][0]['rows'] if 'rows' in policy_result[k]['answerElements'][0] else [] for k in policy_result
        }

    result['summary'] = FAIL if failure else PASS

    module.exit_json(**result)


def _run_policy(name, snapshot):
    """
    Run a policy and return a dictionary containing its checks and their results.
    Converts check results from strings into dictionaries.
    """
    return {k: json.loads(v) for k, v in bf_run_analysis(name=name, snapshot=snapshot).items()}

def main():
    run_module()

if __name__ == '__main__':
    main()
