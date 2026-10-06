"""Configurable mock REST API for API-client problems. See shared/README.md."""

from .api import MockRestAPI, RequestLog
from .config import (
    DEFAULT_ENVELOPES,
    PAGINATION_STYLES,
    AuthConfig,
    FaultConfig,
    FieldMess,
    RateLimitConfig,
    ResourceConfig,
)
from .dataset import scale_records, scale_resources
from .messy import VARIANTS, render

__all__ = [
    "DEFAULT_ENVELOPES", "PAGINATION_STYLES", "VARIANTS", "AuthConfig", "FaultConfig", "FieldMess", "MockRestAPI",
    "RateLimitConfig", "RequestLog", "ResourceConfig", "render", "scale_records", "scale_resources",
]
