#!/usr/bin/env python
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
import subprocess
import sys

from paasta_tools.cli.utils import get_container_name
from paasta_tools.cli.utils import get_subparser
from paasta_tools.cli.utils import get_task_from_instance
from paasta_tools.cli.utils import PaastaTaskNotFound


def add_subparser(subparsers):
    get_subparser(
        description="'paasta docker_stop' works by picking a container running your service "
                    "at random. It then runs docker stop <container_id> to stop the container. "
                    "You should expect marathon to then replace the dead container. "
                    "Note this doesn't do any draining of the connections to this container!",
        help_text="Docker stop a container running your service",
        command='docker_stop',
        function=paasta_docker_stop,
        subparsers=subparsers,
    )


def paasta_docker_stop(args):
    try:
        task = get_task_from_instance(
            cluster=args.cluster,
            service=args.service,
            instance=args.instance,
            slave_hostname=args.host,
            task_id=args.mesos_id,
        )
    except PaastaTaskNotFound:
        sys.exit(1)
    container = get_container_name(task)
    slave = task.slave['hostname']
    command = f"sudo docker stop {container}"
    subprocess.call(["ssh", "-o", "LogLevel=QUIET", "-tA", slave, command])
