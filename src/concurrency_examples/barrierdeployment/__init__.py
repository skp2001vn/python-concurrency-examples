"""Coordinate deployment workers before switching traffic.

Use `threading.Barrier` to release all prepared deployment workers together.
"""

from concurrency_examples.barrierdeployment.deployment import (
    DeploymentGate,
)

__all__ = ["DeploymentGate"]
