#!/usr/bin/env python3
"""
src/core/__init__.py - Core Module für gemeinsame Funktionen

VOLLSTÄNDIGE VERSION - alle Funktionen inklusive Converter verfügbar
"""

try:
    from .utilities import (
        # Parameter-Extraktion
        get_numeric_value,
        get_boolean_value,
        get_flow_parameter,
        get_flow_extensions,
        get_investment_extensions,
        
        # Converter-Funktionen (NEU - vollständig implementiert)
        parse_bus_list,
        parse_conversion_factors,
        validate_converter_flows,
        get_converter_bus_references,
        validate_converter_data,
        get_converter_summary,
        
        # Zeitreihen-Verarbeitung
        resolve_keyword,
        resolve_timeseries_keywords,
        
        # Validierungs-Funktionen
        validate_flow_extensions,
        validate_bus_references,
        
        # Results-Verarbeitung
        safe_get_scalars,
        extract_investment_data,
        
        # Logging-Utilities
        setup_component_logger,
        log_dataframe_info,
        
        # Konstanten
        DEFAULT_COMPONENT_PARAMS,
        TIMESERIES_FIELDS,
        INVESTMENT_PARAMS,
        CONVERTER_PARAMS
    )
    
    CONVERTER_FUNCTIONS_AVAILABLE = True
    print("✅ Alle Core-Funktionen inklusive Converter verfügbar")

except ImportError as e:
    print(f"❌ Kritischer Core-Import-Fehler: {e}")
    print("💡 Stelle sicher, dass utilities.py alle Funktionen implementiert hat")
    raise

# Export alle verfügbaren Funktionen
__all__ = [
    # Parameter-Extraktion
    'get_numeric_value',
    'get_boolean_value', 
    'get_flow_parameter',
    'get_flow_extensions',
    'get_investment_extensions',
    
    # Converter-Funktionen
    'parse_bus_list',
    'parse_conversion_factors',
    'validate_converter_flows',
    'get_converter_bus_references',
    'validate_converter_data',
    'get_converter_summary',
    
    # Zeitreihen-Verarbeitung
    'resolve_keyword',
    'resolve_timeseries_keywords',
    
    # Validierungs-Funktionen
    'validate_flow_extensions',
    'validate_bus_references',
    
    # Results-Verarbeitung
    'safe_get_scalars',
    'extract_investment_data',
    
    # Logging-Utilities
    'setup_component_logger',
    'log_dataframe_info',
    
    # Konstanten
    'DEFAULT_COMPONENT_PARAMS',
    'TIMESERIES_FIELDS',
    'INVESTMENT_PARAMS',
    'CONVERTER_PARAMS'
]