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
