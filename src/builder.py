#!/usr/bin/env python3
"""
src/builder.py - REPLACEMENT NOTICE

Diese Datei ist VERALTET und sollte durch die modularen Builder ersetzt werden.
Für Rückwärtskompatibilität leitet sie auf die neue modulare Implementierung um.
"""

# Direkte Umleitung auf modulare Implementation
from .builder import ModelBuilder

# Deprecation Warning
import warnings
warnings.warn(
    "src/builder.py ist veraltet. Diese Datei leitet auf src/builder/ um.",
    DeprecationWarning,
    stacklevel=2
)

# Export für Rückwärtskompatibilität
__all__ = ['ModelBuilder']
