# Copyright 2015-2016 Yelp Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import mock
import pytest
from mock import patch

import paasta_tools.chronos_tools
from paasta_tools.cli.cmds.validate import check_service_path
from paasta_tools.cli.cmds.validate import get_schema
from paasta_tools.cli.cmds.validate import get_service_path
from paasta_tools.cli.cmds.validate import invalid_chronos_instance
from paasta_tools.cli.cmds.validate import paasta_validate
from paasta_tools.cli.cmds.validate import paasta_validate_soa_configs
from paasta_tools.cli.cmds.validate import SCHEMA_INVALID
from paasta_tools.cli.cmds.validate import SCHEMA_VALID
from paasta_tools.cli.cmds.validate import UNKNOWN_SERVICE
from paasta_tools.cli.cmds.validate import valid_chronos_instance
from paasta_tools.cli.cmds.validate import validate_chronos
from paasta_tools.cli.cmds.validate import validate_schema
from paasta_tools.cli.cmds.validate import validate_tron


@patch('paasta_tools.cli.cmds.validate.validate_all_schemas', autospec=True)
@patch('paasta_tools.cli.cmds.validate.validate_chronos', autospec=True)
@patch('paasta_tools.cli.cmds.validate.validate_tron', autospec=True)
@patch('paasta_tools.cli.cmds.validate.get_service_path', autospec=True)
@patch('paasta_tools.cli.cmds.validate.check_service_path', autospec=True)
def test_paasta_validate_calls_everything(
    mock_check_service_path,
    mock_get_service_path,
    mock_validate_tron,
    mock_validate_chronos,
    mock_validate_all_schemas,
):
    # Ensure each check in 'paasta_validate' is called

    mock_check_service_path.return_value = True
    mock_get_service_path.return_value = 'unused_path'
    mock_validate_all_schemas.return_value = True
    mock_validate_chronos.return_value = True
    mock_validate_tron.return_value = True

    args = mock.MagicMock()
    args.service = None
    args.soa_dir = None

    paasta_validate(args)

    assert mock_validate_all_schemas.called
    assert mock_validate_chronos.called
    assert mock_validate_tron.called


def test_get_service_path_unknown(capfd):
    service = None
    soa_dir = 'unused'

    assert get_service_path(service, soa_dir) is None

    output, _ = capfd.readouterr()
    assert UNKNOWN_SERVICE in output


def test_validate_unknown_service():
    args = mock.MagicMock()
    args.service = None
    args.yelpsoa_config_root = 'unused'
    paasta_validate(args) == 1


def test_validate_unknown_service_service_path():
    service_path = 'unused/path'

    assert not paasta_validate_soa_configs(service_path)


@patch('paasta_tools.cli.cmds.validate.os.path.isdir', autospec=True)
@patch('paasta_tools.cli.cmds.validate.glob', autospec=True)
def test_get_service_path_cwd(
    mock_glob,
    mock_isdir,
):
    mock_isdir.return_value = True
    mock_glob.return_value = ['something.yaml']

    service = None
    soa_dir = os.getcwd()

    service_path = get_service_path(service, soa_dir)

    assert service_path == os.getcwd()


@patch('paasta_tools.cli.cmds.validate.os.path.isdir', autospec=True)
@patch('paasta_tools.cli.cmds.validate.glob', autospec=True)
def test_get_service_path_soa_dir(
    mock_glob,
    mock_isdir,
):
    mock_isdir.return_value = True
    mock_glob.return_value = ['something.yaml']

    service = 'some_service'
    soa_dir = 'some/path'

    service_path = get_service_path(service, soa_dir)

    assert service_path == f'{soa_dir}/{service}'


def is_schema(schema):
    assert schema is not None
    assert isinstance(schema, dict)
    assert '$schema' in schema


def test_get_schema_marathon_found():
    schema = get_schema('marathon')
    is_schema(schema)


def test_get_schema_chronos_found():
    schema = get_schema('chronos')
    is_schema(schema)


def test_get_schema_tron_found():
    schema = get_schema('tron')
    is_schema(schema)


def test_get_schema_missing():
    assert get_schema('fake_schema') is None


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_list_hashes_good(
    mock_get_file_contents, capfd,
):
    marathon_content = """
---
main_worker:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
  healthcheck_mode: cmd
  healthcheck_cmd: '/bin/true'
_main_http:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  registrations: ['foo.bar', 'bar.baz']
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_healthcheck_non_cmd(
    mock_get_file_contents, capfd,
):
    marathon_content = """
---
main_worker:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
  healthcheck_mode: tcp
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output
    marathon_content = """
---
main_worker:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_id(
    mock_get_file_contents, capfd,
):
    marathon_content = """
---
valid:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output

    marathon_content = """
---
this_is_okay_too_1:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output

    marathon_content = """
---
dashes-are-okay-too:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output

    marathon_content = """
---
main_worker_CAPITALS_INVALID:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert not validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output

    marathon_content = """
---
$^&*()(&*^%&definitely_not_okay:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
"""
    mock_get_file_contents.return_value = marathon_content
    assert not validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_healthcheck_cmd_has_cmd(
    mock_get_file_contents, capfd,
):
    marathon_content = """
---
main_worker:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
  healthcheck_mode: cmd
"""
    mock_get_file_contents.return_value = marathon_content
    assert not validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output
    marathon_content = """
---
main_worker:
  cpus: 0.1
  instances: 2
  mem: 250
  disk: 512
  cmd: virtualenv_run/bin/python adindexer/adindex_worker.py
  healthcheck_mode: cmd
  healthcheck_cmd: '/bin/true'
"""
    mock_get_file_contents.return_value = marathon_content
    assert validate_schema('unused_service_path.yaml', 'marathon')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_keys_outside_instance_blocks_bad(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
{
    "main": {
        "instances": 5
    },
    "page": false
}
"""
    assert not validate_schema('unused_service_path.json', 'marathon')

    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_security_good(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
main:
    dependencies_reference: main
    security:
        outbound_firewall: block
"""
    assert validate_schema('unused_service_path.yaml', 'marathon')

    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_schema_security_bad(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
main:
    dependencies_reference: main
    security:
        outbound_firewall: bblock
"""
    assert not validate_schema('unused_service_path.yaml', 'marathon')

    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_marathon_validate_invalid_key_bad(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
{
    "main": {
        "fake_key": 5
    }
}
"""
    assert not validate_schema('unused_service_path.json', 'marathon')

    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_chronos_validate_schema_list_hashes_good(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
{
    "daily_job": {
        "schedule": "bar"
    },
    "wheekly": {
        "schedule": "baz"
    }
}
"""
    assert validate_schema('unused_service_path.json', 'chronos')

    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_chronos_validate_schema_keys_outside_instance_blocks_bad(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
{
    "daily_job": {
        "schedule": "bar"
    },
    "page": false
}
"""
    assert not validate_schema('unused_service_path.json', 'chronos')

    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_chronos_validate_schema_security_good(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
some_batch:
    schedule: foo
    dependencies_reference: main
    security:
        outbound_firewall: block
"""
    assert validate_schema('unused_service_path.yaml', 'chronos')

    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_chronos_validate_schema_security_bad(
    mock_get_file_contents, capfd,
):
    mock_get_file_contents.return_value = """
some_batch:
    schedule: foo
    dependencies_reference: main
    security:
        outbound_firewall: bblock
"""
    assert not validate_schema('unused_service_path.yaml', 'chronos')

    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_services_for_cluster', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_all_instances_for_service', autospec=True)
@patch('paasta_tools.cli.cmds.validate.load_chronos_job_config', autospec=True)
@patch('paasta_tools.cli.cmds.validate.path_to_soa_dir_service', autospec=True)
def test_failing_chronos_job_validate(
    mock_path_to_soa_dir_service,
    mock_load_chronos_job_config,
    mock_list_all_instances_for_service,
    mock_list_clusters,
    mock_get_services_for_cluster,
    capfd,
):
    fake_service = 'fake-service'
    fake_instance = 'fake-instance'
    fake_cluster = 'penguin'

    mock_chronos_job = mock.Mock(autospec=True)
    mock_chronos_job.get_parents.return_value = None
    mock_chronos_job.validate.return_value = (False, ['something is wrong with the config'])

    mock_path_to_soa_dir_service.return_value = ('fake_soa_dir', fake_service)
    mock_list_clusters.return_value = [fake_cluster]
    mock_list_all_instances_for_service.return_value = [fake_instance]
    mock_get_services_for_cluster.return_value = [(fake_service, fake_instance)]
    mock_load_chronos_job_config.return_value = mock_chronos_job

    assert not validate_chronos('fake_service_path')

    output, _ = capfd.readouterr()
    expected_output = 'something is wrong with the config'
    assert invalid_chronos_instance(fake_cluster, fake_instance, expected_output) in output


@patch('paasta_tools.cli.cmds.validate.get_services_for_cluster', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_all_instances_for_service', autospec=True)
@patch('paasta_tools.cli.cmds.validate.load_chronos_job_config', autospec=True)
@patch('paasta_tools.cli.cmds.validate.path_to_soa_dir_service', autospec=True)
def test_failing_chronos_job_self_dependent(
    mock_path_to_soa_dir_service,
    mock_load_chronos_job_config,
    mock_list_all_instances_for_service,
    mock_list_clusters,
    mock_get_services_for_cluster,
    capfd,
):
    fake_service = 'fake-service'
    fake_instance = 'fake-instance'
    fake_cluster = 'penguin'
    chronos_spacer = paasta_tools.chronos_tools.INTERNAL_SPACER

    mock_chronos_job = mock.Mock(autospec=True)
    mock_chronos_job.get_parents.return_value = [f"{fake_service}{chronos_spacer}{fake_instance}"]
    mock_chronos_job.validate.return_value = (True, [])

    mock_path_to_soa_dir_service.return_value = ('fake_soa_dir', fake_service)
    mock_list_clusters.return_value = [fake_cluster]
    mock_list_all_instances_for_service.return_value = [fake_instance]
    mock_get_services_for_cluster.return_value = [(fake_service, fake_instance)]
    mock_load_chronos_job_config.return_value = mock_chronos_job

    assert not validate_chronos('fake_service_path')

    output, _ = capfd.readouterr()
    expected_output = 'Job fake-service.fake-instance cannot depend on itself'
    assert invalid_chronos_instance(fake_cluster, fake_instance, expected_output) in output


@patch('paasta_tools.cli.cmds.validate.get_services_for_cluster', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_all_instances_for_service', autospec=True)
@patch('paasta_tools.cli.cmds.validate.load_chronos_job_config', autospec=True)
@patch('paasta_tools.cli.cmds.validate.path_to_soa_dir_service', autospec=True)
def test_failing_chronos_job_missing_parent(
    mock_path_to_soa_dir_service,
    mock_load_chronos_job_config,
    mock_list_all_instances_for_service,
    mock_list_clusters,
    mock_get_services_for_cluster,
    capfd,
):
    fake_service = 'fake-service'
    fake_instance = 'fake-instance'
    fake_cluster = 'penguin'
    chronos_spacer = paasta_tools.chronos_tools.INTERNAL_SPACER

    mock_chronos_job = mock.Mock(autospec=True)
    mock_chronos_job.get_parents.return_value = ["{}{}{}".format(fake_service, chronos_spacer, 'parent-1')]
    mock_chronos_job.validate.return_value = (True, [])

    mock_path_to_soa_dir_service.return_value = ('fake_soa_dir', fake_service)
    mock_list_clusters.return_value = [fake_cluster]
    mock_list_all_instances_for_service.return_value = [fake_instance]
    mock_get_services_for_cluster.return_value = [(fake_service, fake_instance)]
    mock_load_chronos_job_config.return_value = mock_chronos_job

    assert not validate_chronos('fake_service_path')

    output, _ = capfd.readouterr()
    expected_output = 'Parent job fake-service.parent-1 could not be found'
    assert invalid_chronos_instance(fake_cluster, fake_instance, expected_output) in output


@patch('paasta_tools.cli.cmds.validate.get_services_for_cluster', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.list_all_instances_for_service', autospec=True)
@patch('paasta_tools.cli.cmds.validate.load_chronos_job_config', autospec=True)
@patch('paasta_tools.cli.cmds.validate.path_to_soa_dir_service', autospec=True)
def test_validate_chronos_valid_instance(
    mock_path_to_soa_dir_service,
    mock_load_chronos_job_config,
    mock_list_all_instances_for_service,
    mock_list_clusters,
    mock_get_services_for_cluster,
    capfd,
):
    fake_service = 'fake-service'
    fake_instance = 'fake-instance'
    fake_cluster = 'penguin'

    mock_chronos_job = mock.Mock(autospec=True)
    mock_chronos_job.get_parents.return_value = None
    mock_chronos_job.validate.return_value = (True, [])

    mock_path_to_soa_dir_service.return_value = ('fake_soa_dir', fake_service)
    mock_list_clusters.return_value = [fake_cluster]
    mock_list_all_instances_for_service.return_value = [fake_instance]
    mock_get_services_for_cluster.return_value = [(fake_service, fake_instance)]
    mock_load_chronos_job_config.return_value = mock_chronos_job

    assert validate_chronos('fake_service_path')

    output, _ = capfd.readouterr()
    assert valid_chronos_instance(fake_cluster, fake_instance) in output


@patch("paasta_tools.chronos_tools.TMP_JOB_IDENTIFIER", 'tmp', autospec=None)
@patch('paasta_tools.cli.cmds.validate.path_to_soa_dir_service', autospec=True)
def test_validate_chronos_tmp_job(mock_path_to_soa_dir_service, capfd):
    mock_path_to_soa_dir_service.return_value = ('fake_soa_dir', 'tmp')
    assert validate_chronos('fake_path/tmp') is False
    assert (
        "Services using scheduled tasks cannot be named tmp, as it clashes"
        " with the identifier used for temporary jobs"
    ) in \
        capfd.readouterr()[0]


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_tron_validate_schema_good(
    mock_get_file_contents, capfd,
):
    tron_content = """
jobs:
    - name: test_job
      node: batch_box
      service: my_service
      deploy_group: prod
      allow_overlap: false
      monitoring:
        team: my_team
      schedule:
        type: cron
        value: "0 7 * * 5"
      actions:
        - name: first
          command: echo hello world
        - name: second
          command: sleep 10
          expected_runtime: 15 sec
          executor: paasta
          cluster: paasta-cluster-1
          cpus: 0.5
          mem: 100
          pool: custom
"""
    mock_get_file_contents.return_value = tron_content
    assert validate_schema('unused_service_path.yaml', 'tron')
    output, _ = capfd.readouterr()
    assert SCHEMA_VALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_tron_validate_schema_job_extra_properties_bad(
    mock_get_file_contents, capfd,
):
    tron_content = """
jobs:
    - name: test_job
      node: batch_box
      schedule: "daily 04:00:00"
      unexpected: 100
      actions:
        - name: first
          command: echo hello world
"""
    mock_get_file_contents.return_value = tron_content
    assert not validate_schema('unused_service_path.yaml', 'tron')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_tron_validate_schema_actions_extra_properties_bad(
    mock_get_file_contents, capfd,
):
    tron_content = """
jobs:
    - name: test_job
      node: batch_box
      schedule: "daily 04:00:00"
      actions:
        - name: first
          command: echo hello world
          something_else: true
"""
    mock_get_file_contents.return_value = tron_content
    assert not validate_schema('unused_service_path.yaml', 'tron')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.get_file_contents', autospec=True)
def test_tron_validate_schema_cleanup_action_extra_properties_bad(
    mock_get_file_contents, capfd,
):
    tron_content = """
jobs:
    - name: test_job
      node: batch_box
      schedule: "daily 04:00:00"
      actions:
        - name: first
          command: echo hello world
      cleanup_action:
        command: rm output
        other_key: value
"""
    mock_get_file_contents.return_value = tron_content
    assert not validate_schema('unused_service_path.yaml', 'tron')
    output, _ = capfd.readouterr()
    assert SCHEMA_INVALID in output


@patch('paasta_tools.cli.cmds.validate.validate_schema', autospec=True)
@patch('paasta_tools.cli.cmds.validate.validate_complete_config', autospec=True)
@patch('os.listdir', autospec=True)
@pytest.mark.parametrize(
    'schema_valid,config_msgs,expected_return', [
        (False, [], False),
        (True, ['something wrong'], False),
        (True, [], True),
    ],
)
def test_validate_tron_with_tron_dir(
    mock_ls,
    mock_validate_tron_config,
    mock_validate_schema,
    capfd,
    schema_valid,
    config_msgs,
    expected_return,
):
    mock_ls.return_value = ['foo.yaml']
    mock_validate_schema.return_value = schema_valid
    mock_validate_tron_config.return_value = config_msgs

    assert validate_tron('soa/tron/dev') == expected_return
    mock_ls.assert_called_once_with('soa/tron/dev')
    mock_validate_schema.assert_called_once_with('soa/tron/dev/foo.yaml', 'tron')
    mock_validate_tron_config.assert_called_once_with(
        'foo', 'dev', 'soa',
    )

    output, _ = capfd.readouterr()
    for error in config_msgs:
        assert error in output


@patch('paasta_tools.cli.cmds.validate.list_tron_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.validate_complete_config', autospec=True)
def test_validate_tron_with_service_invalid(
    mock_validate_tron_config,
    mock_list_clusters,
    capfd,
):
    mock_list_clusters.return_value = ['dev', 'stage', 'prod']
    mock_validate_tron_config.side_effect = [[], ['some error'], []]

    assert not validate_tron('soa/my_service')
    mock_list_clusters.assert_called_once_with('my_service', 'soa')
    expected_calls = [
        mock.call('my_service', cluster, 'soa')
        for cluster in mock_list_clusters.return_value
    ]
    assert mock_validate_tron_config.call_args_list == expected_calls

    output, _ = capfd.readouterr()
    assert 'some error' in output


@patch('paasta_tools.cli.cmds.validate.list_tron_clusters', autospec=True)
@patch('paasta_tools.cli.cmds.validate.validate_complete_config', autospec=True)
def test_validate_tron_with_service_valid(
    mock_validate_tron_config,
    mock_list_clusters,
    capfd,
):
    mock_list_clusters.return_value = ['dev', 'prod']
    mock_validate_tron_config.side_effect = [[], []]

    assert validate_tron('soa/my_service')
    mock_list_clusters.assert_called_once_with('my_service', 'soa')
    expected_calls = [
        mock.call('my_service', cluster, 'soa')
        for cluster in mock_list_clusters.return_value
    ]
    assert mock_validate_tron_config.call_args_list == expected_calls

    output, _ = capfd.readouterr()
    assert 'tron-dev.yaml is valid' in output


def test_check_service_path_none(capfd):
    service_path = None
    assert not check_service_path(service_path)

    output, _ = capfd.readouterr()
    assert "%s is not a directory" % service_path in output


@patch('paasta_tools.cli.cmds.validate.os.path.isdir', autospec=True)
def test_check_service_path_empty(mock_isdir, capfd):
    mock_isdir.return_value = True
    service_path = 'fake/path'
    assert not check_service_path(service_path)

    output, _ = capfd.readouterr()
    assert "%s does not contain any .yaml files" % service_path in output


@patch('paasta_tools.cli.cmds.validate.os.path.isdir', autospec=True)
@patch('paasta_tools.cli.cmds.validate.glob', autospec=True)
def test_check_service_path_good(
    mock_glob,
    mock_isdir,
):
    mock_isdir.return_value = True
    mock_glob.return_value = True
    service_path = 'fake/path'
    assert check_service_path(service_path)
