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

from ansys.result_explorer.core.client import Client

rx = Client.connect_with_token(
    "eyJob3N0IjoibG9jYWxob3N0IiwiaHR0cFBvcnQiOjgwMDAsImdycGNQb3J0Ijo1MDAwMCwic2Vzc2lvbklkIjoiN2FkNGE2YjQtYzc4ZC00MWFlLWI2MmMtMTc5NDc2MzU4Mzc3In0="
)

session_path = r"D:\tmp\my_session.rxs"
rx.save_session(session_path)

# save each workspace as a template
for workspace in rx.list_workspaces():
    template_path = rf"D:\tmp\{workspace.name}.rxwt"
    workspace.export_as_template(template_path)
