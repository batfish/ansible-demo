# ansible-demo
This repo contains the files and instructions necessary to reproduce our [Ansible demo presentation](https://www.ansible.com/resources/webinars-training/validating-pre-commit-network-configuration-changes-at-scale-with-batfish-ansible), which uses [Pybatfish](https://github.com/batfish/pybatfish) and [Batfish](https://github.com/batfish/batfish) to validate pre-commit network configuration changes.  

Automation without pre-commit validation is risky. Use Batfish in your automated workflow for comprehensive correctness guarantees before pushing to production.


## Prereqs

* Run [Batfish](https://github.com/batfish/batfish).  If you don't already have it set up and running, run this to set up and start the [docker container](https://github.com/batfish/docker/blob/master/batfish.md):

  `mkdir -p data && docker run -d -v $(pwd)/data:/data -p 9997:9997 -p 9996:9996 batfish/allinone:sha_736c753_e840243`
* Install the [Pybatfish](https://github.com/batfish/pybatfish) version used for the demo (to guarantee compatibility):

  `pip install git+git://github.com/batfish/pybatfish.git@386d0379e0b16985cee9c6cd12c0e7d8d8c8d6cc`
* Install Ansible (see [installation guide](https://docs.ansible.com/ansible/2.7/installation_guide/intro_installation.html) for details):

  `pip install ansible`

## Setup
* Clone this demo repo:

  `git clone git@github.com:batfish/ansible-demo.git`
* Edit the group vars in `playbooks/inventory` file to reflect your setup.
* Run the setup script to create the base snapshot and policies:

  `python python/demo-setup.py -p snapshots/snapshot0/ -a "DC Fabric Policy" checks/fabric/ -a "DC Base Policy" checks/base/`

### Optional Setup for Integrations

#### Git Integration
This Git integration allows Ansible to create a branch in the GitHub repository with your network configurations, and commit each change you validate to that branch.
* Clone your network repo e.g.
  `git clone git@github.com:YOUR_ORG_NAME/YOUR_NETWORK_REPO.git`

  Note: The network repo should be formatted the same way as [snapshots/snapshot0/](https://github.com/batfish/ansible-demo/blob/master/snapshots/snapshot0/), with config files in a `configs/` dir at the root of the repo.
* Generate a [GitHub token with access to this repo](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/), then supply the token to the `playbooks/inventory` file

#### S3 Integration
This S3 integration is for posting Batfish validation logs to your S3 bucket. Logs are also stored locally whether or not S3 is used.
* [Create an S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/gsg/CreatingABucket.html) to store your logs
* Install required Python modules:

  `pip install botocore`
  `pip install boto3`

#### Slack Integration
* Follow [these instructions](https://get.slack.help/hc/en-us/articles/115005265063-Incoming-WebHooks-for-Slack) to create a Slack service that accepts incoming webhooks.

## Running the Demo

Both scenarios can optionally be run with extra tags `s3`, `slack`, and/or `git` to enable different integrations.

Note: logs for each playbook run are written to `s3_logs/`.

### Add Leaf Scenario
This scenario adds a new leaf router to an existing datacenter and confirms the changes made adhere to the defined network policies.

#### Run 1 - Fail Policy
This run fails due to duplicate BGP ASNs between leaf 2 and leaf 3.

* Run the playbook `ansible-playbook -i playbooks/inventory playbooks/master.yml --tags "always"`
* Fill in the prompts:
  * Hostname: `lhr-leaf-03`
  * POD: `1`
  * BGP ASN: `65002`

#### Run 2 - Pass Policy
This run passes our predefined policies.

* Run the playbook `ansible-playbook -i playbooks/inventory playbooks/master.yml --tags "always"`
* Fill in the prompts:
  * Hostname: `lhr-leaf-03`
  * POD: `1`
  * BGP ASN: `65003`


### Update ACL Scenario
This scenario is derived from our `Provably Safe ACL and Firewall Changes` [Python notebook](https://github.com/batfish/pybatfish/blob/master/jupyter_notebooks/Provably%20Safe%20ACL%20and%20Firewall%20Changes.ipynb).  It updates our firewalls to allow access to a new HTTP service (TCP port 80 on subnet 10.1.5.0/27) and confirms the changes:
1) Are necessary (i.e. firewalls do not currently permit the new traffic)
2) Allow the new traffic
3) Don't allow anything other than the new traffic (i.e. confirm no collateral damage)

#### Run 1 - Fail ACL Validation
This run creates a bigger hole in the firewall than we intended, thus fails collateral damage check.

* Edit the file `inputs/acls.json` to reflect the desired ACL changes, adding this line just before the deny all line: `"permit tcp any 10.1.5.0 0.0.0.63 eq 80",`
* Run the ACL playbook: `ansible-playbook -i playbooks/inventory playbooks/master_acl.yml --tags "create"`
* Fill in the prompts:
  * Firewall hostnames: `lhr-fw-01|lhr-fw-02`
  * POD: `1`
  * Source IPs of new traffic to allow: `0.0.0.0/0`
  * Destination IPs of new traffic to allow: `10.1.5.0/27`
  * IP protocol for new traffic to allow: `tcp`
  * Destination ports: `80`

#### Run 2 - Pass ACL Validation
This run passes our ACL validation checks.

* Edit the file `inputs/acls.json` to reflect the desired ACL changes, replacing the line added above with this line: `"permit tcp any 10.1.5.0 0.0.0.31 eq 80",`
* Run the ACL playbook: `ansible-playbook -i playbooks/inventory playbooks/master_acl.yml --tags "create"`
* Fill in the prompts, same as the previous run:
  * Firewall hostnames: `lhr-fw-01|lhr-fw-02`
  * POD: `1`
  * Source IPs of new traffic to allow: `0.0.0.0/0`
  * Destination IPs of new traffic to allow: `10.1.5.0/27`
  * IP protocol for new traffic to allow: `tcp`
  * Destination ports: `80`

**Got questions, feedback, or feature requests? Join our community on [Slack!](https://join.slack.com/t/batfish-org/shared_invite/enQtMzA0Nzg2OTAzNzQ1LTUxOTJlY2YyNTVlNGQ3MTJkOTIwZTU2YjY3YzRjZWFiYzE4ODE5ODZiNjA4NGI5NTJhZmU2ZTllOTMwZDhjMzA)**
