"""
Shared execution state for managing agent cancellation.
"""
from typing import Set

# Track cancelled projects for runner interruption
cancelled_projects: Set[str] = set()
