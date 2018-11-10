#   Copyright 2018 Intentionet
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

import logging
from pybatfish.client.commands import *
from pybatfish.datamodel.flow import HeaderConstraints
# noinspection PyUnresolvedReferences
from pybatfish.question import bfq, list_questions, load_questions  # noqa F401
from pybatfish.datamodel.referencelibrary import *
from pybatfish.datamodel.primitives import *

from os import makedirs, path
import argparse



parser = argparse.ArgumentParser(description='Setup for Ansible-Batfish demo.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-a', '--analysis',
                    help='Name of and path to the analysis directory.',
                    default=None,
                    action='append',
                    nargs=2)
parser.add_argument('-n', '--network-name',
                    help='Name of the network for base snapshot.',
                    default='Ansible-Demo')
parser.add_argument('-p', '--snapshot-path',
                    help='Path to base snapshot configs.',
                    required=True)
parser.add_argument('-s', '--snapshot-name',
                    help='Name of the base snapshot.',
                    default='base_snapshot')
parser.add_argument('-l', '--log-level', default='INFO',
                    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Determines what level of logs to display')
args = parser.parse_args()

log_level = logging.getLevelName(args.log_level)
logging.basicConfig(format='%(levelname)s %(message)s', level=log_level)

bf_set_network(args.network_name)
bf_init_snapshot(args.snapshot_path, args.snapshot_name, overwrite=True)

analyses = args.analysis

### short term hack to make Fabric playbook work correctly
host_interfaces = [
    Interface(hostname="lhr-leaf-01", interface="Ethernet1/6"),
    Interface(hostname="lhr-leaf-01", interface="Ethernet1/7"),
    Interface(hostname="lhr-leaf-02", interface="Ethernet1/6"),
    Interface(hostname="lhr-leaf-02", interface="Ethernet1/7"),
    Interface(hostname="lhr-leaf-03", interface="Ethernet1/6"),
    Interface(hostname="lhr-leaf-03", interface="Ethernet1/7"),
]

refbook = ReferenceBook(name="mybook", interfaceGroups=[InterfaceGroup(name="host_interfaces", interfaces=host_interfaces)])
try:
    bf_add_reference_book(refbook)
except Exception as e:
    logging.warning('Could not add reference book: {}'.format(e))
## end hack

if analyses is not None:
    for name, path in analyses:
        logging.info('Setting up analysis "{}" with checks at "{}"'.format(name, path))
        try:
            bf_init_analysis(name, path)
        except:
            bf_delete_analysis(name)
            bf_init_analysis(name, path)


