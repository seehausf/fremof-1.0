#!/usr/bin/env python3
"""
src/builder/component_builder.py - KOMPLETT ÜBERARBEITET

FIXED VERSION: Folgt exakt den oemof-Beispielen
- Keine Default-Werte für leere Felder
- Klare Investment vs. Normal-Modus Trennung  
- Nur zwingend notwendige Parameter
- Korrekte Converter-Investment-Logic
"""

import pandas as pd
from typing import Dict, Any, Optional, List
import logging
from .base_builder import BaseModelBuilder
from ..core import (
    setup_component_logger, get_numeric_value, get_boolean_value,
    get_flow_parameter, get_flow_extensions, parse_bus_list, parse_conversion_factors
)

logger = setup_component_logger('builder.component')

class ComponentBuilder(BaseModelBuilder):
    """
    KOMPLETT ÜBERARBEITETE Klasse für Komponenten-Erstellung
    Folgt exakt den oemof-Beispielen - keine Default-Werte!
    """
    
    def create_sources(self):
        """Erstellt alle Source-Komponenten"""
        if self.data['sources'].empty:
            logger.info("Keine Sources zu erstellen")
            return
            
        logger.info("Erstelle Sources (FIXED)...")
        
        for _, source_data in self.data['sources'].iterrows():
            try:
                # FIXED: Validierung vor Erstellung
                self._validate_source_parameters(source_data)
                source = self._build_source_fixed(source_data)
                self.nodes.append(source)
                logger.debug(f"Source erstellt: {source_data['label']}")
            except Exception as e:
                logger.error(f"Fehler bei Source '{source_data['label']}': {e}")
                raise
        
        logger.info(f"Sources erstellt: {len(self.data['sources'])}")
    
    def create_sinks(self):
        """Erstellt alle Sink-Komponenten"""
        if self.data['sinks'].empty:
            logger.info("Keine Sinks zu erstellen")
            return
            
        logger.info("Erstelle Sinks (FIXED)...")
        
        for _, sink_data in self.data['sinks'].iterrows():
            try:
                # FIXED: Validierung vor Erstellung
                self._validate_sink_parameters(sink_data)
                sink = self._build_sink_fixed(sink_data)
                self.nodes.append(sink)
                logger.debug(f"Sink erstellt: {sink_data['label']}")
            except Exception as e:
                logger.error(f"Fehler bei Sink '{sink_data['label']}': {e}")
                raise
        
        logger.info(f"Sinks erstellt: {len(self.data['sinks'])}")
    
    def create_converters(self):
        """Erstellt alle Converter-Komponenten (KOMPLETT ÜBERARBEITET)"""
        if 'converters' not in self.data or self.data['converters'].empty:
            logger.info("Keine Converters zu erstellen")
            return
            
        logger.info("Erstelle Converters (KOMPLETT ÜBERARBEITET)...")
        
        for _, converter_data in self.data['converters'].iterrows():
            try:
                # FIXED: Validierung vor Erstellung
                self._validate_converter_parameters(converter_data)
                converter = self._build_converter_fixed(converter_data)
                self.nodes.append(converter)
                logger.debug(f"Converter erstellt: {converter_data['label']}")
            except Exception as e:
                logger.error(f"Fehler bei Converter '{converter_data['label']}': {e}")
                raise
        
        logger.info(f"Converters erstellt: {len(self.data['converters'])}")
    
    def create_storages(self):
        """Erstellt alle Storage-Komponenten"""
        if 'storages' not in self.data or self.data['storages'].empty:
            logger.info("Keine Storages zu erstellen")
            return
            
        logger.info("Erstelle Storages (FIXED)...")
        
        for _, storage_data in self.data['storages'].iterrows():
            try:
                # FIXED: Validierung vor Erstellung
                self._validate_storage_parameters(storage_data)
                storage = self._build_storage_fixed(storage_data)
                self.nodes.append(storage)
                logger.debug(f"Storage erstellt: {storage_data['label']}")
            except Exception as e:
                logger.error(f"Fehler bei Storage '{storage_data['label']}': {e}")
                raise
        
        logger.info(f"Storages erstellt: {len(self.data['storages'])}")
    
    # =============================================================================
    # PARAMETER-VALIDIERUNG (NEU)
    # =============================================================================
    
    def _validate_source_parameters(self, source_data: pd.Series):
        """
        FIXED: Validiert Source-Parameter - existing erforderlich für Output-Flow
        
        Args:
            source_data: Source-Daten
            
        Raises:
            ValueError: Bei fehlenden zwingend notwendigen Parametern
        """
        label = source_data.get('label', 'unknown')
        
        # Output-Bus erforderlich
        if 'output' not in source_data or pd.isna(source_data['output']):
            raise ValueError(f"Source '{label}': 'output' Bus erforderlich")
        
        # existing erforderlich für Output-Flow nominal_capacity
        existing = get_numeric_value(source_data, 'existing', 0)
        has_investment = get_boolean_value(source_data, 'investment', False)
        
        if existing <= 0 and not has_investment:
            raise ValueError(f"Source '{label}': 'existing > 0' erforderlich (für Output-Flow nominal_capacity)")
        
        # Investment-Parameter prüfen
        if has_investment:
            investment_max = get_numeric_value(source_data, 'investment_max', 0)
            if investment_max <= 0:
                raise ValueError(f"Source '{label}': 'investment_max > 0' erforderlich wenn investment=True")
            
            capex = get_numeric_value(source_data, 'capex', 0)
            if capex <= 0:
                logger.warning(f"Source '{label}': capex=0 - kostenlose Investment")
    
    def _validate_sink_parameters(self, sink_data: pd.Series):
        """FIXED: Validiert Sink-Parameter - existing ODER fix erforderlich für Input-Flow!"""
        label = sink_data.get('label', 'unknown')
        
        # Input-Bus erforderlich
        if 'input' not in sink_data or pd.isna(sink_data['input']):
            raise ValueError(f"Sink '{label}': 'input' Bus erforderlich")
        
        # existing ODER fix erforderlich für Input-Flow nominal_capacity
        existing = get_numeric_value(sink_data, 'existing', 0)
        has_investment = get_boolean_value(sink_data, 'investment', False)
        has_fix = get_flow_parameter(sink_data, 'fix') is not None
        
        if existing <= 0 and not has_investment and not has_fix:
            raise ValueError(f"Sink '{label}': 'existing > 0' oder 'investment=True' oder 'fix' erforderlich (für Input-Flow nominal_capacity)")
        
        # Investment-Parameter prüfen
        if has_investment:
            investment_max = get_numeric_value(sink_data, 'investment_max', 0)
            if investment_max <= 0:
                raise ValueError(f"Sink '{label}': 'investment_max > 0' erforderlich wenn investment=True")
    
    def _validate_converter_parameters(self, converter_data: pd.Series):
        """FIXED: Validiert Converter-Parameter - existing erforderlich für Main-Output"""
        label = converter_data.get('label', 'unknown')
        
        # Input-Buses erforderlich
        inputs = converter_data.get('inputs', '')
        if pd.isna(inputs) or not str(inputs).strip():
            raise ValueError(f"Converter '{label}': 'inputs' Buses erforderlich")
        
        # Output-Buses erforderlich
        outputs = converter_data.get('outputs', '')
        if pd.isna(outputs) or not str(outputs).strip():
            raise ValueError(f"Converter '{label}': 'outputs' Buses erforderlich")
        
        # Conversion-Faktoren erforderlich
        input_conversions = converter_data.get('input_conversions', '')
        output_conversions = converter_data.get('output_conversions', '')
        
        if pd.isna(input_conversions):
            raise ValueError(f"Converter '{label}': 'input_conversions' erforderlich")
        
        if pd.isna(output_conversions):
            raise ValueError(f"Converter '{label}': 'output_conversions' erforderlich")
        
        # existing erforderlich für Main-Output (erster Output)
        existing = get_numeric_value(converter_data, 'existing', 0)
        has_investment = get_boolean_value(converter_data, 'investment', False)
        
        if existing <= 0 and not has_investment:
            raise ValueError(f"Converter '{label}': 'existing > 0' erforderlich (für nominal_capacity des ersten Outputs)")
        
        # Investment-Parameter prüfen
        if has_investment:
            investment_max = get_numeric_value(converter_data, 'investment_max', 0)
            if investment_max <= 0:
                raise ValueError(f"Converter '{label}': 'investment_max > 0' erforderlich wenn investment=True")
    
    def _validate_storage_parameters(self, storage_data: pd.Series):
        """FIXED: Validiert Storage-Parameter - existing ist IMMER erforderlich!"""
        label = storage_data.get('label', 'unknown')
        
        # Bus erforderlich
        if 'bus' not in storage_data or pd.isna(storage_data['bus']):
            raise ValueError(f"Storage '{label}': 'bus' erforderlich")
        
        # existing ist IMMER erforderlich (für nominal_storage_capacity)
        existing = get_numeric_value(storage_data, 'existing', 0)
        has_investment = get_boolean_value(storage_data, 'investment', False)
        
        if existing <= 0 and not has_investment:
            raise ValueError(f"Storage '{label}': 'existing > 0' erforderlich (für nominal_storage_capacity)")
    
    # =============================================================================
    # KOMPONENTEN-ERSTELLUNG (KOMPLETT NEU)
    # =============================================================================
    
    def _build_source_fixed(self, source_data: pd.Series):
        """
        FIXED: Erstellt Source nach oemof-Beispielen
        Keine Default-Werte!
        """
        self._load_oemof_modules()
        
        # Output-Bus ermitteln
        output_buses = [bus.strip() for bus in str(source_data['output']).split(';')]
        if len(output_buses) != 1:
            raise ValueError(f"Source '{source_data['label']}' muss genau einen Output-Bus haben")
        
        output_bus = self.buses_dict[output_buses[0]]
        
        # FIXED: Flow-Parameter ohne Default-Werte
        flow_params = self._build_flow_parameters_fixed(source_data, 'source')
        
        # Flow erstellen
        flow = self.flows.Flow(**flow_params)
        
        # Source erstellen
        source = self.components.Source(
            label=source_data['label'],
            outputs={output_bus: flow}
        )
        
        return source
    
    def _build_sink_fixed(self, sink_data: pd.Series):
        """
        FIXED: Erstellt Sink - Input-Flow bekommt nominal_capacity!
        
        Bei Sinks ist der Input-Flow der Main-Flow mit nominal_capacity
        """
        self._load_oemof_modules()
        
        # Input-Bus ermitteln
        input_buses = [bus.strip() for bus in str(sink_data['input']).split(';')]
        if len(input_buses) != 1:
            raise ValueError(f"Sink '{sink_data['label']}' muss genau einen Input-Bus haben")
        
        input_bus = self.buses_dict[input_buses[0]]
        
        # FIXED: Sink Input-Flow bekommt nominal_capacity
        flow_params = self._build_flow_parameters_fixed(sink_data, 'sink')
        
        # Flow erstellen
        flow = self.flows.Flow(**flow_params)
        
        # Sink erstellen
        sink = self.components.Sink(
            label=sink_data['label'],
            inputs={input_bus: flow}
        )
        
        return sink
    
    def _build_converter_fixed(self, converter_data: pd.Series):
        """
        FIXED: Erstellt Converter nach oemof-Beispielen
        Korrekte Investment-Logic!
        """
        self._load_oemof_modules()
        
        # Input/Output-Buses ermitteln
        input_buses = parse_bus_list(converter_data.get('inputs', ''))
        output_buses = parse_bus_list(converter_data.get('outputs', ''))
        
        # Conversion-Faktoren parsen
        input_conversions = parse_conversion_factors(
            converter_data.get('input_conversions', '1.0'), 
            len(input_buses)
        )
        output_conversions = parse_conversion_factors(
            converter_data.get('output_conversions', '1.0'), 
            len(output_buses)
        )
        
        # Flows erstellen
        inputs_dict = {}
        outputs_dict = {}
        conversion_factors = {}
        
        # Input-Flows (FIXED: KEIN nominal_capacity - automatische Skalierung)
        for i, bus_label in enumerate(input_buses):
            bus = self.buses_dict[bus_label]
            
            # Input-Flows bekommen KEINE nominal_capacity - werden automatisch skaliert!
            flow_params = self._build_input_flow_parameters_fixed(converter_data)
            flow = self.flows.Flow(**flow_params)
            
            inputs_dict[bus] = flow
            conversion_factors[bus] = input_conversions[i] if i < len(input_conversions) else 1.0
        
        # Output-Flows (FIXED: NUR der ERSTE bekommt nominal_capacity!)
        for i, bus_label in enumerate(output_buses):
            bus = self.buses_dict[bus_label]
            
            if i == 0:  # FIXED: Nur der ERSTE Output bekommt nominal_capacity!
                # Main-Output mit nominal_capacity (Investment oder existing)
                flow_params = self._build_flow_parameters_fixed(converter_data, 'converter_main_output')
                logger.debug(f"Converter '{converter_data['label']}' Main-Output ({bus_label}): MIT nominal_capacity")
            else:
                # Secondary-Outputs: KEIN nominal_capacity - automatische Skalierung!
                flow_params = self._build_secondary_output_flow_fixed(converter_data)
                logger.debug(f"Converter '{converter_data['label']}' Secondary-Output ({bus_label}): OHNE nominal_capacity")
            
            flow = self.flows.Flow(**flow_params)
            outputs_dict[bus] = flow
            conversion_factors[bus] = output_conversions[i] if i < len(output_conversions) else 1.0
        
        # Converter erstellen
        converter = self.components.Converter(
            label=converter_data['label'],
            inputs=inputs_dict,
            outputs=outputs_dict,
            conversion_factors=conversion_factors
        )
        
        logger.debug(f"Converter '{converter_data['label']}': {len(inputs_dict)} inputs, {len(outputs_dict)} outputs")
        return converter
    
    def _build_storage_fixed(self, storage_data: pd.Series):
        """
        FIXED: Erstellt Storage nach oemof-Beispielen
        Keine Default-Werte!
        """
        self._load_oemof_modules()
        
        # Bus ermitteln
        storage_bus = self.buses_dict[str(storage_data['bus']).strip()]
        
        # FIXED: Storage-Parameter ohne Default-Werte
        storage_params = self._build_storage_parameters_fixed(storage_data)
        
        # Input/Output Flows (einfach, kein Investment auf Flows)
        input_flow = self.flows.Flow()
        output_flow = self.flows.Flow()
        
        # Storage erstellen
        storage = self.components.GenericStorage(
            label=storage_data['label'],
            inputs={storage_bus: input_flow},
            outputs={storage_bus: output_flow},
            **storage_params
        )
        
        return storage
    
    # =============================================================================
    # FLOW-PARAMETER ERSTELLUNG (KOMPLETT NEU - FOLGT OEMOF-BEISPIELEN)
    # =============================================================================
    
    def _build_flow_parameters_fixed(self, component_data: pd.Series, flow_type: str) -> Dict[str, Any]:
        """
        FIXED: Erstellt Flow-Parameter - nominal_capacity nur für bestimmte Flows!
        
        GRUNDREGEL: 
        - Sources: Output-Flow bekommt nominal_capacity
        - Sinks: Input-Flow bekommt nominal_capacity  
        - Converters: Erster Output-Flow bekommt nominal_capacity
        - Andere Flows: KEIN nominal_capacity (automatische Skalierung über conversion_factors)
        
        Args:
            component_data: Komponenten-Daten
            flow_type: 'source', 'sink', 'converter_main_output'
            
        Returns:
            Dictionary mit Flow-Parametern
        """
        flow_params = {}
        
        # SCHRITT 1: nominal_capacity nur für Main-Flows!
        if flow_type in ['source', 'sink', 'converter_main_output']:
            has_investment = get_boolean_value(component_data, 'investment', False)
            existing = get_numeric_value(component_data, 'existing', 0)
            
            if has_investment:
                # INVESTMENT-MODUS: Investment-Objekt erstellen
                # existing wird Attribut des Investment-Objekts
                investment = self._build_investment_object_fixed(component_data)
                if investment:
                    flow_params['nominal_capacity'] = investment
                    logger.debug(f"Investment-Flow für {flow_type}: {component_data['label']} (existing={existing} wird Investment-Attribut)")
                else:
                    raise ValueError(f"Investment aktiviert aber Investment-Objekt konnte nicht erstellt werden: {component_data['label']}")
            else:
                # NORMAL-MODUS: nominal_capacity = existing
                flow_params['nominal_capacity'] = existing
                logger.debug(f"Normal-Flow nominal_capacity={existing} für {flow_type}: {component_data['label']}")
        else:
            # Andere Flow-Typen bekommen KEIN nominal_capacity (automatische Skalierung)
            logger.debug(f"Flow OHNE nominal_capacity für {flow_type}: {component_data['label']} (automatische Skalierung)")
        
        # SCHRITT 2: Basis Flow-Parameter (NUR wenn explizit gesetzt!)
        for param in ['min', 'max', 'fix']:
            value = get_flow_parameter(component_data, param)
            if value is not None:
                flow_params[param] = value
                logger.debug(f"Flow-Parameter {param}={value} für {component_data['label']}")
        
        # SCHRITT 3: Variable Kosten (NUR wenn explizit gesetzt!)
        var_costs = get_flow_parameter(component_data, 'variable_costs')
        if var_costs is not None:
            flow_params['variable_costs'] = var_costs
            logger.debug(f"Variable costs={var_costs} für {component_data['label']}")
        
        # SCHRITT 4: Erweiterte Flow-Parameter (NUR bei Investment!)
        has_investment = get_boolean_value(component_data, 'investment', False)
        if has_investment and flow_type in ['source', 'sink', 'converter_main_output']:
            flow_extensions = get_flow_extensions(component_data)
            if flow_extensions:
                flow_params.update(flow_extensions)
                logger.debug(f"Flow-Extensions {flow_extensions} für {component_data['label']}")
        
        return flow_params
    
    def _build_input_flow_parameters_fixed(self, converter_data: pd.Series) -> Dict[str, Any]:
        """
        FIXED: Input-Flows für Converter - KEIN nominal_capacity!
        
        Input-Flows werden automatisch über conversion_factors skaliert
        
        Args:
            converter_data: Converter-Daten
            
        Returns:
            Dictionary mit Input-Flow-Parametern (OHNE nominal_capacity)
        """
        flow_params = {}
        
        # WICHTIG: Input-Flows bekommen KEIN nominal_capacity!
        # Sie werden automatisch über conversion_factors vom ersten Output skaliert
        
        # Variable Kosten für Input (z.B. Brennstoffkosten)
        var_costs = get_flow_parameter(converter_data, 'variable_costs')
        if var_costs is not None:
            flow_params['variable_costs'] = var_costs
        
        # Min/Max Parameter (falls gesetzt - aber ohne nominal_capacity problematisch)
        # Besser: Keine min/max für Input-Flows oder nur bei Investment
        logger.debug(f"Input-Flow-Parameter für {converter_data['label']}: {flow_params} (KEIN nominal_capacity)")
        return flow_params
    
    def _build_secondary_output_flow_fixed(self, converter_data: pd.Series) -> Dict[str, Any]:
        """
        FIXED: Secondary-Output-Flows für Converter - KEIN nominal_capacity!
        
        Secondary-Outputs werden automatisch über conversion_factors skaliert
        
        Args:
            converter_data: Converter-Daten
            
        Returns:
            Dictionary mit Secondary-Output-Flow-Parametern (OHNE nominal_capacity)
        """
        flow_params = {}
        
        # WICHTIG: Secondary-Outputs bekommen KEIN nominal_capacity!
        # Sie werden automatisch über conversion_factors vom ersten Output skaliert
        
        # Min/Max Parameter (falls gesetzt - aber ohne nominal_capacity problematisch)
        # Besser: Keine min/max für Secondary-Outputs oder nur bei speziellen Fällen
        
        logger.debug(f"Secondary-Output-Flow-Parameter für {converter_data['label']}: {flow_params} (KEIN nominal_capacity)")
        return flow_params
    
    def _build_investment_object_fixed(self, component_data: pd.Series):
        """
        FIXED: Erstellt Investment-Objekt nach oemof-Beispielen
        
        Args:
            component_data: Komponenten-Daten
            
        Returns:
            oemof.solph Investment-Objekt
        """
        # Investment-Builder verwenden (der ist bereits korrekt!)
        from .investment_builder import InvestmentBuilder
        investment_builder = InvestmentBuilder(self.data)
        investment_builder._load_oemof_modules = self._load_oemof_modules
        investment_builder.Investment = self.Investment
        
        return investment_builder.build_investment(component_data)
    
    def _build_storage_parameters_fixed(self, storage_data: pd.Series) -> Dict[str, Any]:
        """
        FIXED: Erstellt Storage-Parameter ohne Default-Werte
        
        Args:
            storage_data: Storage-Daten
            
        Returns:
            Dictionary mit Storage-Parametern (NUR gesetzte Werte!)
        """
        storage_params = {}
        
        # Investment für Storage-Kapazität
        has_investment = get_boolean_value(storage_data, 'investment', False)
        
        if has_investment:
            investment = self._build_investment_object_fixed(storage_data)
            if investment:
                storage_params['nominal_storage_capacity'] = investment
        else:
            # Bestehende Storage-Kapazität (NUR wenn > 0!)
            existing_capacity = get_numeric_value(storage_data, 'existing', 0)
            if existing_capacity > 0:
                storage_params['nominal_storage_capacity'] = existing_capacity
        
        # Storage-spezifische Parameter (NUR wenn explizit gesetzt!)
        storage_param_mapping = {
            'max_storage_level': 'max_storage_level',
            'min_storage_level': 'min_storage_level', 
            'inflow_conversion_factor': 'inflow_conversion_factor',
            'outflow_conversion_factor': 'outflow_conversion_factor',
            'loss_rate': 'loss_rate',
            'initial_storage_level': 'initial_storage_level'
        }
        
        for excel_param, oemof_param in storage_param_mapping.items():
            if excel_param in storage_data and pd.notna(storage_data[excel_param]):
                value = float(storage_data[excel_param])
                storage_params[oemof_param] = value
                logger.debug(f"Storage-Parameter {oemof_param}={value} für {storage_data['label']}")
        
        return storage_params
    
    # =============================================================================
    # KOMPONENTEN-ZUSAMMENFASSUNG (ERWEITERT)
    # =============================================================================
    
    def get_component_summary(self) -> Dict[str, Any]:
        """
        Erstellt detaillierte Zusammenfassung aller Komponenten
        
        Returns:
            Dictionary mit Komponenten-Zusammenfassung
        """
        summary = {
            'sources': [],
            'sinks': [],
            'converters': [],
            'storages': [],
            'validation_status': 'OK'
        }
        
        try:
            # Sources analysieren
            for _, source in self.data['sources'].iterrows():
                source_info = {
                    'label': source['label'],
                    'output': source.get('output', 'unbekannt'),
                    'investment': get_boolean_value(source, 'investment', False),
                    'existing_capacity': get_numeric_value(source, 'existing', 0),
                    'investment_max': get_numeric_value(source, 'investment_max', 0)
                }
                summary['sources'].append(source_info)
            
            # Sinks analysieren  
            for _, sink in self.data['sinks'].iterrows():
                sink_info = {
                    'label': sink['label'],
                    'input': sink.get('input', 'unbekannt'),
                    'investment': get_boolean_value(sink, 'investment', False),
                    'existing_capacity': get_numeric_value(sink, 'existing', 0),
                    'has_fix': get_flow_parameter(sink, 'fix') is not None
                }
                summary['sinks'].append(sink_info)
            
            # Converters analysieren
            if 'converters' in self.data and not self.data['converters'].empty:
                for _, converter in self.data['converters'].iterrows():
                    converter_info = {
                        'label': converter['label'],
                        'inputs': parse_bus_list(converter.get('inputs', '')),
                        'outputs': parse_bus_list(converter.get('outputs', '')),
                        'technology': converter.get('technology', 'unknown'),
                        'investment': get_boolean_value(converter, 'investment', False),
                        'existing_capacity': get_numeric_value(converter, 'existing', 0),
                        'investment_max': get_numeric_value(converter, 'investment_max', 0)
                    }
                    summary['converters'].append(converter_info)
            
            # Storages analysieren
            if 'storages' in self.data and not self.data['storages'].empty:
                for _, storage in self.data['storages'].iterrows():
                    storage_info = {
                        'label': storage['label'],
                        'bus': storage.get('bus', 'unbekannt'),
                        'investment': get_boolean_value(storage, 'investment', False),
                        'existing_capacity': get_numeric_value(storage, 'existing', 0)
                    }
                    summary['storages'].append(storage_info)
        
        except Exception as e:
            summary['validation_status'] = f'ERROR: {e}'
            logger.error(f"Fehler bei Component-Summary: {e}")
        
        return summary

# Export der Klasse für Import
__all__ = ['ComponentBuilder']