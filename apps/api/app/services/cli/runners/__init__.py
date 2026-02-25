"""
Model runners — dispatch to different SDKs based on provider protocol.
"""
from .router import ProviderRouter

__all__ = ["ProviderRouter"]
