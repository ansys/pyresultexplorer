# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. _create_hps_solution_example:

Create an HPS solution
======================

This example demonstrates how to interactively create an HPS solution by selecting
from available projects, jobs, tasks, and files:

- **Connect to Result Explorer** using a token for HPS access.
- **Browse HPS providers** to find available result providers.
- **Navigate the HPS hierarchy** through projects, jobs, and tasks.
- **Create an HPS solution** from selected file resources.

This example requires a valid authentication token and HPS-enabled result provider.

.. note::

    This example requires user interaction for selecting items from the HPS hierarchy.
    Make sure to replace the TOKEN variable with a valid token before running.
"""

from ansys.result_explorer.core.client import Client

TOKEN = "<insert here>"  # noqa E501


def select_item(items, item_type):
    """Helper to select an item from a list, auto-selecting if only one choice."""
    print(f"Available {item_type}:")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item.name} (id: {item.id})")

    if len(items) == 1:
        print(f"Selected {item_type}: {items[0].name} (auto-selected)\n")
        return items[0]

    choice = input(f"\nSelect a {item_type} (enter number): ")
    selected = items[int(choice) - 1]
    print(f"Selected {item_type}: {selected.name}\n")
    return selected


rx = Client.connect_with_token(TOKEN)

# list result providers
rps = rx.list_result_providers()
print("Result providers:")
for rp in rps:
    print(f" - {rp.name} (HPS: {rp.HasField('hps_url')})")


# find providers with HPS access
hps_providers = [rp for rp in rps if rp.hps_url]
assert hps_providers, "No result provider with HPS access found"

# let user pick a provider
print("\nAvailable HPS providers:")
for i, rp in enumerate(hps_providers, 1):
    print(f"{i}. {rp.name}")

choice = input("\nSelect a provider (enter number): ")
rp = hps_providers[int(choice) - 1]
print(f"Selected provider: {rp.name}\n")

# ============ Select Project ============
print("\n" + "=" * 40 + " Select Project " + "=" * 40)
projects = rx.hps_ls("/", result_provider=rp)
project = select_item(projects, "project")

# ============ Select Job ============
print("=" * 40 + " Select Job " + "=" * 40)
jobs = rx.hps_ls(f"/{project.id}", result_provider=rp)
job = select_item(jobs, "job")

# ============ Select Task ============
print("=" * 40 + " Select Task " + "=" * 40)
tasks = rx.hps_ls(f"/{project.id}/{job.id}", result_provider=rp)
task = select_item(tasks, "task")

# ============ Select File ============
print("=" * 40 + " Select File " + "=" * 40)
files = rx.hps_ls(f"/{project.id}/{job.id}/{task.id}", result_provider=rp)
file = select_item(files, "file")


solution = rx.create_hps_solution(
    name="Example HPS Solution",
    result_provider=rp.name,
    project_id=project.id,
    task_id=task.id,
    file_id=file.id,
)

print(f"\nCreated solution: {solution}")
