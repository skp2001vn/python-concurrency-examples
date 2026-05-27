"""Coordinate deployment workers before switching traffic.

Use `threading.Barrier` to release all prepared deployment workers together.
"""

from python_concurrency_examples.examples.barrierdeployment.deployment import (
    DeploymentGate,
)

__all__ = ["DeploymentGate"]
