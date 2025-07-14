#!/usr/bin/env python3
"""
src/core/utilities.py - Gemeinsame Hilfsfunktionen

VOLLSTÄNDIGE VERSION mit Converter-Funktionen
Zentrale Sammlung aller wiederverwendbaren Funktionen:
- Parameter-Extraktion (numeric, boolean, flow parameters) - ARRAY-SICHER
- Converter-spezifische Funktionen (NEU)
- Validierungs-Funktionen
- Zeitreihen-Keyword-Auflösung
- Logging-Utilities
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional, Union, List, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# PARAMETER-EXTRAKTION - ARRAY-SICHER
# =============================================================================

def get_numeric_value(component_data: pd.Series, param: str, default: float = 0) -> float:
    """
    Extrahiert numerischen Wert aus Komponenten-Daten
    ARRAY-SICHER: Behandelt Zeitreihen-Keywords korrekt
    
    Args:
        component_data: pandas Series mit Komponenten-Daten
        param: Parameter-Name
        default: Standard-Wert falls Parameter fehlt
        
    Returns:
        Numerischer Wert
    """
    if param not in component_data:
        return default
    
    value = component_data[param]
    
    # Sichere NaN-Prüfung für Arrays und Skalare
    if value is None:
        return default
    
    # Für Arrays/Listen (aufgelöste Zeitreihen-Keywords)
    if isinstance(value, (list, tuple, np.ndarray)):
        # Arrays können nicht direkt als Zahlenwert verwendet werden
        logger.warning(f"Parameter {param} ist Zeitreihe/Array, kann nicht als numerischer Wert verwendet werden")
        return default
    
    # Für skalare Werte
    try:
        if pd.isna(value):
            return default
    except (ValueError, TypeError):
        # Falls pd.isna() mit dem Wert nicht umgehen kann
        pass
    
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Konnte {param} nicht als Zahl interpretieren: {value}, verwende {default}")
        return default

def get_boolean_value(component_data: pd.Series, param: str, default: bool = False) -> bool:
    """
    Extrahiert Boolean-Wert aus Komponenten-Daten
    ARRAY-SICHER: Behandelt Zeitreihen-Keywords korrekt
    
    Args:
        component_data: pandas Series mit Komponenten-Daten
        param: Parameter-Name
        default: Standard-Wert falls Parameter fehlt
        
    Returns:
        Boolean-Wert
    """
    if param not in component_data:
        return default
    
    value = component_data[param]
    
    # Sichere NaN-Prüfung für Arrays und Skalare
    if value is None:
        return default
    
    # Für Arrays/Listen (sollten nicht als Boolean interpretiert werden)
    if isinstance(value, (list, tuple, np.ndarray)):
        logger.warning(f"Parameter {param} ist Zeitreihe/Array, kann nicht als Boolean verwendet werden")
        return default
    
    # Für skalare Werte
    try:
        if pd.isna(value):
            return default
    except (ValueError, TypeError):
        # Falls pd.isna() mit dem Wert nicht umgehen kann
        pass
    
    # Verschiedene Boolean-Darstellungen handhaben
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower() in ['true', 'yes', '1', 'on', 'enabled']
    elif isinstance(value, (int, float)):
        return bool(value)
    else:
        return default

def get_flow_parameter(component_data: pd.Series, param: str) -> Optional[Union[float, List[float]]]:
    """
    Extrahiert Flow-Parameter (kann Zeitreihe oder skalarer Wert sein)
    ARRAY-SICHER: Erkennt und behandelt Arrays korrekt
    
    Args:
        component_data: pandas Series mit Komponenten-Daten
        param: Parameter-Name ('min', 'max', 'fix', etc.)
        
    Returns:
        Flow-Parameter als Wert oder Zeitreihe
    """
    # Parameter existiert nicht
    if param not in component_data:
        return None
        
    value = component_data[param]
    
    # Wert ist None
    if value is None:
        return None
    
    # Bereits aufgelöste Zeitreihe (Liste/Array)
    if isinstance(value, (list, tuple, np.ndarray)):
        if isinstance(value, np.ndarray):
            return value.tolist()
        return list(value)
    
    # Für skalare Werte
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        # Falls pd.isna() mit dem Wert nicht umgehen kann
        pass
    
    # Numerischer Wert
    try:
        numeric_value = float(value)
        return numeric_value
    except (ValueError, TypeError):
        return None

def get_flow_extensions(component_data: pd.Series) -> Dict[str, Any]:
    """
    Extrahiert erweiterte Flow-Parameter (Phase 2.1)
    ARRAY-SICHER: Sichere Behandlung für Zeitreihen-Keywords
    
    Args:
        component_data: pandas Series mit Komponenten-Daten
        
    Returns:
        Dictionary mit erweiterten Flow-Parametern
    """
    extensions = {}
    
    # Full load time minimum
    full_load_time_min = component_data.get('full_load_time_min')
    if full_load_time_min is not None and not isinstance(full_load_time_min, (list, tuple, np.ndarray)):
        try:
            if not pd.isna(full_load_time_min):
                value = float(full_load_time_min)
                if value > 0:
                    extensions['full_load_time_min'] = value
                    logger.debug(f"Full load time min: {value} h")
        except (ValueError, TypeError):
            logger.warning(f"Invalid full_load_time_min: {full_load_time_min}")
    
    # Full load time maximum
    full_load_time_max = component_data.get('full_load_time_max')
    if full_load_time_max is not None and not isinstance(full_load_time_max, (list, tuple, np.ndarray)):
        try:
            if not pd.isna(full_load_time_max):
                value = float(full_load_time_max)
                if value > 0:
                    extensions['full_load_time_max'] = value
                    logger.debug(f"Full load time max: {value} h")
        except (ValueError, TypeError):
            logger.warning(f"Invalid full_load_time_max: {full_load_time_max}")
    
    return extensions

def get_investment_extensions(component_data: pd.Series) -> Dict[str, Any]:
    """
    Extrahiert Investment-Erweiterungs-Parameter (Phase 2.1)
    ARRAY-SICHER: Sichere Behandlung für Zeitreihen-Keywords
    
    Args:
        component_data: pandas Series mit Komponenten-Daten
        
    Returns:
        Dictionary mit Investment-Parametern
    """
    investment_params = {}
    
    # Investment minimum
    investment_min = component_data.get('investment_min')
    if investment_min is not None and not isinstance(investment_min, (list, tuple, np.ndarray)):
        try:
            if not pd.isna(investment_min):
                value = float(investment_min)
                if value > 0:
                    investment_params['minimum'] = value
        except (ValueError, TypeError):
            logger.warning(f"Invalid investment_min: {investment_min}")
    
    return investment_params

# =============================================================================
# CONVERTER-SPEZIFISCHE FUNKTIONEN (NEU - KOMPLETT IMPLEMENTIERT)
# =============================================================================

def parse_bus_list(bus_string: Any) -> List[str]:
    """
    Parst Bus-Liste aus String (für Converter Multi-Input/Output)
    
    Args:
        bus_string: String mit Bus-Namen getrennt durch ';' oder einzelner Bus
        
    Returns:
        Liste von Bus-Namen
    """
    if pd.isna(bus_string) or bus_string is None:
        return []
    
    bus_str = str(bus_string).strip()
    if not bus_str:
        return []
    
    # Mehrere Buses durch ';' getrennt
    if ';' in bus_str:
        buses = [bus.strip() for bus in bus_str.split(';') if bus.strip()]
        return buses
    else:
        # Einzelner Bus
        return [bus_str]

def parse_conversion_factors(conversion_string: Any, expected_count: int = None) -> List[float]:
    """
    Parst Conversion-Faktoren aus String
    
    Args:
        conversion_string: String mit Faktoren getrennt durch ';' oder einzelner Faktor
        expected_count: Erwartete Anzahl Faktoren (optional)
        
    Returns:
        Liste von Conversion-Faktoren
    """
    if pd.isna(conversion_string) or conversion_string is None:
        # Standard-Faktoren (1.0)
        return [1.0] * (expected_count or 1)
    
    # Einzelner numerischer Wert
    if isinstance(conversion_string, (int, float)):
        factor = float(conversion_string)
        return [factor] * (expected_count or 1)
    
    # String-Verarbeitung
    conv_str = str(conversion_string).strip()
    if not conv_str:
        return [1.0] * (expected_count or 1)
    
    # Mehrere Faktoren durch ';' getrennt
    if ';' in conv_str:
        factors = []
        for factor_str in conv_str.split(';'):
            if factor_str.strip():
                try:
                    factors.append(float(factor_str.strip()))
                except ValueError:
                    logger.warning(f"Ungültiger Conversion-Faktor: {factor_str}, verwende 1.0")
                    factors.append(1.0)
        
        # Falls weniger Faktoren als erwartet, mit 1.0 auffüllen
        if expected_count and len(factors) < expected_count:
            factors.extend([1.0] * (expected_count - len(factors)))
        
        return factors
    else:
        # Einzelner Faktor
        try:
            factor = float(conv_str)
            return [factor] * (expected_count or 1)
        except ValueError:
            logger.warning(f"Ungültiger Conversion-Faktor: {conv_str}, verwende 1.0")
            return [1.0] * (expected_count or 1)

def validate_converter_flows(component_data: pd.Series) -> None:
    """
    Validiert Converter-Flow-Konfiguration
    
    Args:
        component_data: Converter-Daten
        
    Raises:
        ValueError: Bei Validierungs-Fehlern
    """
    label = component_data.get('label', 'unknown')
    
    # Input-Buses prüfen
    inputs = component_data.get('inputs', '')
    if pd.isna(inputs) or not str(inputs).strip():
        raise ValueError(f"Converter '{label}': Keine Input-Buses definiert")
    
    # Output-Buses prüfen
    outputs = component_data.get('outputs', '')
    if pd.isna(outputs) or not str(outputs).strip():
        raise ValueError(f"Converter '{label}': Keine Output-Buses definiert")
    
    # Parse Bus-Listen
    input_buses = parse_bus_list(inputs)
    output_buses = parse_bus_list(outputs)
    
    # Conversion-Faktoren prüfen
    input_conversions = parse_conversion_factors(
        component_data.get('input_conversions', '1.0'), 
        len(input_buses)
    )
    output_conversions = parse_conversion_factors(
        component_data.get('output_conversions', '1.0'), 
        len(output_buses)
    )
    
    # Anzahl prüfen
    if len(input_conversions) != len(input_buses):
        logger.warning(f"Converter '{label}': Anzahl Input-Conversions ({len(input_conversions)}) != Input-Buses ({len(input_buses)})")
    
    if len(output_conversions) != len(output_buses):
        logger.warning(f"Converter '{label}': Anzahl Output-Conversions ({len(output_conversions)}) != Output-Buses ({len(output_buses)})")

def get_converter_bus_references(data: Dict[str, pd.DataFrame]) -> Set[str]:
    """
    Sammelt alle Bus-Referenzen aus Converter-Komponenten
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        
    Returns:
        Set mit Bus-Namen aus Converters
    """
    bus_refs = set()
    
    converters_df = data.get('converters', pd.DataFrame())
    if converters_df.empty:
        return bus_refs
    
    for _, converter in converters_df.iterrows():
        # Input-Buses
        inputs = converter.get('inputs', '')
        if not pd.isna(inputs):
            input_buses = parse_bus_list(inputs)
            bus_refs.update(input_buses)
        
        # Output-Buses
        outputs = converter.get('outputs', '')
        if not pd.isna(outputs):
            output_buses = parse_bus_list(outputs)
            bus_refs.update(output_buses)
    
    return bus_refs

def validate_converter_data(data: Dict[str, pd.DataFrame]) -> None:
    """
    Validiert alle Converter-Daten
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        
    Raises:
        ValueError: Bei kritischen Validierungs-Fehlern
    """
    converters_df = data.get('converters', pd.DataFrame())
    if converters_df.empty:
        return
    
    logger.info("Validiere Converter-Daten...")
    
    for _, converter in converters_df.iterrows():
        validate_converter_flows(converter)
    
    logger.info("Converter-Validierung abgeschlossen")

def get_converter_summary(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Erstellt Zusammenfassung aller Converter-Komponenten
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        
    Returns:
        Dictionary mit Converter-Zusammenfassung
    """
    converters_df = data.get('converters', pd.DataFrame())
    
    if converters_df.empty:
        return {'total_converters': 0, 'converters': []}
    
    converter_list = []
    
    for _, converter in converters_df.iterrows():
        converter_info = {
            'label': converter.get('label', 'unknown'),
            'technology': converter.get('technology', 'unknown'),
            'inputs': parse_bus_list(converter.get('inputs', '')),
            'outputs': parse_bus_list(converter.get('outputs', '')),
            'investment': get_boolean_value(converter, 'investment', False),
            'existing_capacity': get_numeric_value(converter, 'existing', 0),
            'include': get_boolean_value(converter, 'include', True)
        }
        converter_list.append(converter_info)
    
    return {
        'total_converters': len(converter_list),
        'converters': converter_list
    }

# =============================================================================
# ZEITREIHEN-VERARBEITUNG
# =============================================================================

def resolve_keyword(value: Any, available_columns: list, timeseries: pd.DataFrame) -> Any:
    """
    Löst ein einzelnes Zeitreihen-Keyword auf
    
    Args:
        value: Wert der aufgelöst werden soll
        available_columns: Verfügbare Zeitreihen-Spalten
        timeseries: Zeitreihen-DataFrame
        
    Returns:
        Aufgelöster Wert (Zeitreihe als Liste oder ursprünglicher Wert)
    """
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        if value is None:
            return None
    
    # String-Wert prüfen
    str_value = str(value).strip()
    
    # Ist es ein Zeitreihen-Keyword?
    if str_value in available_columns:
        timeseries_data = timeseries[str_value].tolist()
        logger.debug(f"Keyword '{str_value}' aufgelöst zu Zeitreihe mit {len(timeseries_data)} Werten")
        return timeseries_data
    
    # Numerischen Wert versuchen
    try:
        numeric_value = float(str_value)
        return numeric_value
    except ValueError:
        # String zurückgeben falls nicht numerisch
        return str_value

def resolve_timeseries_keywords(data: Dict[str, pd.DataFrame], timeseries: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Löst Zeitreihen-Keywords in allen Komponenten auf
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        timeseries: Zeitreihen-DataFrame
        
    Returns:
        Aktualisierte data mit aufgelösten Keywords
    """
    logger.info("Löse Zeitreihen-Keywords auf...")
    
    timeseries_columns = timeseries.columns.tolist()
    timeseries_columns.remove('timestamp')  # timestamp ist kein Keyword
    
    for sheet_name in ['sources', 'sinks', 'transformers', 'converters']:
        if sheet_name not in data or data[sheet_name].empty:
            continue
            
        df = data[sheet_name].copy()
        
        # Spalten prüfen, die Zeitreihen-Keywords enthalten können
        timeseries_fields = [
            'min', 'max', 'fix', 'availability', 'variable_costs',
            'full_load_time_max', 'full_load_time_min'  # Phase 2.1
        ]
        
        for field in timeseries_fields:
            if field in df.columns:
                df[field] = df[field].apply(
                    lambda x: resolve_keyword(x, timeseries_columns, timeseries)
                )
        
        data[sheet_name] = df
    
    logger.info("Zeitreihen-Keywords aufgelöst")
    return data

# =============================================================================
# VALIDIERUNGS-FUNKTIONEN
# =============================================================================

def validate_flow_extensions(data: Dict[str, pd.DataFrame]) -> None:
    """
    Validiert Flow-Erweiterungen (Phase 2.1)
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        
    Raises:
        ValueError: Bei Validierungs-Fehlern
    """
    logger.info("Validiere Flow-Erweiterungen...")
    
    for sheet_name in ['sources', 'sinks', 'converters']:
        if sheet_name not in data or data[sheet_name].empty:
            continue
            
        df = data[sheet_name]
        
        for _, component in df.iterrows():
            component_label = component['label']
            
            # Investment minimum validation
            if 'investment_min' in component and pd.notna(component['investment_min']):
                investment_min = component['investment_min']
                investment_max = component.get('investment_max', float('inf'))
                
                if investment_min > investment_max:
                    raise ValueError(
                        f"{sheet_name} '{component_label}': "
                        f"investment_min ({investment_min}) > investment_max ({investment_max})"
                    )
                
                # Investment muss aktiviert sein wenn minimum gesetzt
                if not component.get('investment', False):
                    logger.warning(
                        f"{sheet_name} '{component_label}': "
                        f"investment_min gesetzt aber investment=False"
                    )
            
            # Full load time validation
            full_load_min = component.get('full_load_time_min')
            full_load_max = component.get('full_load_time_max')
            
            if (pd.notna(full_load_min) and pd.notna(full_load_max) and 
                full_load_min > full_load_max):
                raise ValueError(
                    f"{sheet_name} '{component_label}': "
                    f"full_load_time_min ({full_load_min}) > full_load_time_max ({full_load_max})"
                )
            
            # Warnung wenn full_load_time ohne nominal_capacity
            if (pd.notna(full_load_min) or pd.notna(full_load_max)):
                has_capacity = (
                    component.get('existing', 0) > 0 or 
                    component.get('investment', False)
                )
                if not has_capacity:
                    logger.warning(
                        f"{sheet_name} '{component_label}': "
                        f"full_load_time Parameter gesetzt aber keine Kapazität definiert"
                    )
    
    logger.info("Flow-Erweiterungen validiert")

def validate_bus_references(data: Dict[str, pd.DataFrame]) -> set:
    """
    Prüft Bus-Referenzen und sammelt alle referenzierten Buses
    
    Args:
        data: Dictionary mit Komponenten-DataFrames
        
    Returns:
        Set mit allen referenzierten Bus-Namen
    """
    # Alle verfügbaren Buses sammeln
    if not data['buses'].empty:
        available_buses = set(data['buses']['label'].tolist())
    else:
        available_buses = set()
    
    # Bus-Referenzen in Sources prüfen
    for _, source in data['sources'].iterrows():
        if 'output' in source and pd.notna(source['output']):
            buses = [bus.strip() for bus in str(source['output']).split(';')]
            for bus in buses:
                if bus not in available_buses:
                    logger.warning(f"Bus '{bus}' in Source '{source['label']}' nicht in buses definiert - wird automatisch erstellt")
                    available_buses.add(bus)
    
    # Bus-Referenzen in Sinks prüfen  
    for _, sink in data['sinks'].iterrows():
        if 'input' in sink and pd.notna(sink['input']):
            buses = [bus.strip() for bus in str(sink['input']).split(';')]
            for bus in buses:
                if bus not in available_buses:
                    logger.warning(f"Bus '{bus}' in Sink '{sink['label']}' nicht in buses definiert - wird automatisch erstellt")
                    available_buses.add(bus)
    
    # Bus-Referenzen in Converters prüfen (NEU)
    converter_buses = get_converter_bus_references(data)
    for bus in converter_buses:
        if bus not in available_buses:
            logger.warning(f"Bus '{bus}' in Converter nicht in buses definiert - wird automatisch erstellt")
            available_buses.add(bus)
    
    return available_buses

# =============================================================================
# RESULTS-VERARBEITUNG (für Phase 2.2.1 Fix)
# =============================================================================

def safe_get_scalars(flow_data: Dict[str, Any]) -> tuple:
    """
    Sichere Extraktion von scalars aus flow_data (oemof-solph v0.6.0 Fix)
    
    Args:
        flow_data: Flow-Daten aus Results
        
    Returns:
        Tuple (scalar_columns, scalar_data) oder (None, None)
    """
    if 'scalars' not in flow_data:
        return None, None
    
    scalars = flow_data['scalars']
    
    # FIX: Sichere Behandlung von Series vs DataFrame
    if isinstance(scalars, pd.Series):
        # Series zu DataFrame konvertieren für einheitliche Behandlung
        scalars_df = scalars.to_frame().T
        return scalars_df.columns, scalars_df
    elif isinstance(scalars, pd.DataFrame):
        return scalars.columns, scalars
    else:
        logger.warning(f"Unbekannter scalars Typ: {type(scalars)}")
        return None, None

def extract_investment_data(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrahiert Investment-Daten aus Results (robust für v0.6.0)
    
    Args:
        results: oemof-solph Results
        
    Returns:
        Liste mit Investment-Daten
    """
    investment_data = []
    
    for flow_key, flow_data in results.items():
        scalar_columns, scalar_values = safe_get_scalars(flow_data)
        
        if scalar_columns is None:
            continue
        
        # Flow-Informationen
        if len(flow_key) == 2:
            from_node, to_node = flow_key
            flow_name = f"{from_node}→{to_node}"
        else:
            from_node = str(flow_key)
            to_node = ""
            flow_name = from_node
        
        # Investment-Spalten suchen
        investment_cols = [col for col in scalar_columns if 'invest' in str(col).lower()]
        
        for col in investment_cols:
            if not scalar_values[col].empty and scalar_values[col].iloc[0] > 0:
                investment_data.append({
                    'flow_name': flow_name,
                    'from_node': from_node,
                    'to_node': to_node,
                    'investment_type': col,
                    'capacity_kW': scalar_values[col].iloc[0],
                    'capacity_MW': scalar_values[col].iloc[0] / 1000
                })
    
    return investment_data

# =============================================================================
# LOGGING-UTILITIES
# =============================================================================

def setup_component_logger(component_name: str) -> logging.Logger:
    """
    Erstellt Logger für Komponenten
    
    Args:
        component_name: Name der Komponente
        
    Returns:
        Konfigurierter Logger
    """
    return logging.getLogger(f"src.{component_name}")

def log_dataframe_info(df: pd.DataFrame, name: str) -> None:
    """
    Protokolliert DataFrame-Informationen
    
    Args:
        df: DataFrame zum Protokollieren
        name: Name für Logs
    """
    if df.empty:
        logger.info(f"{name}: Leer")
    else:
        logger.info(f"{name}: {len(df)} Einträge")
        if hasattr(df, 'columns'):
            logger.debug(f"{name} Spalten: {list(df.columns)}")

# =============================================================================
# KONSTANTEN
# =============================================================================

# Standard-Parameter für verschiedene Komponenten-Typen
DEFAULT_COMPONENT_PARAMS = {
    'sources': {
        'existing': 0,
        'investment': False,
        'investment_max': 0,
        'capex': 0,
        'lifetime': 20,
        'wacc': 0.05,
        'variable_costs': 0,
        'availability': 1.0
    },
    'sinks': {
        'existing': 1.0,  # Default für normierte Flows
        'investment': False,
        'investment_max': 0,
        'capex': 0,
        'lifetime': 20,
        'wacc': 0.05,
        'variable_costs': 0,
        'availability': 1.0
    },
    'converters': {  # NEU
        'existing': 0,
        'investment': False,
        'investment_max': 0,
        'capex': 0,
        'lifetime': 20,
        'wacc': 0.05,
        'variable_costs': 0,
        'availability': 1.0,
        'input_conversions': 1.0,
        'output_conversions': 1.0
    }
}

# Gültige Spalten für Zeitreihen-Keywords
TIMESERIES_FIELDS = [
    'min', 'max', 'fix', 'availability', 'variable_costs',
    'full_load_time_max', 'full_load_time_min'  # Phase 2.1
]

# Investment-Parameter Namen
INVESTMENT_PARAMS = [
    'investment', 'investment_min', 'investment_max', 'capex', 
    'lifetime', 'wacc', 'existing'
]

# Converter-Parameter Namen (NEU)
CONVERTER_PARAMS = [
    'inputs', 'outputs', 'input_conversions', 'output_conversions',
    'technology', 'startup_costs', 'shutdown_costs', 
    'maintenance_interval', 'part_load_efficiency'
]