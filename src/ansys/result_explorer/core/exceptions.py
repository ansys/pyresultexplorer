# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
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

"""Exceptions for Result Explorer client."""

import grpc


class ResultExplorerError(RuntimeError):
    """Custom exception for Result Explorer client errors."""

    @classmethod
    def from_grpc_error(cls, grpc_error: grpc.RpcError) -> "ResultExplorerError":
        """Create a ResultExplorerError from a grpc.RpcError."""
        details = grpc_error.details()
        if grpc_error.code() == grpc.StatusCode.NOT_FOUND:
            return cls(f"Resource not found: {details}")
        return cls(f"{details}")


class UnsecureConnectionWarning(Warning):
    """Warning for unencrypted gRPC connections."""

    pass
