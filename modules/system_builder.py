#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Energiesystem-Aufbau Modul - Multi-Input/Output Version
========================================================================

Erweiterte Version mit Unterstützung für Multi-Input/Output-Transformers.
Unterstützt BHKW (Gas → Strom + Wärme), Wärmepumpen (Strom + Umwelt → Wärme), etc.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0 (Multi-IO)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
import logging

# oemof.solph 0.6.0 Imports
try:
    import oemof.solph as solph
    from oemof.solph import buses, components
    from oemof.solph._options import Investment, NonConvex
    Flow = solph.Flow
except ImportError as e:
    print(f"❌ oemof.solph nicht verfügbar: {e}")
    print("Installieren Sie oemof.solph: pip install oemof.solph>=0.6.0")
    raise


class MultiIOSystemBuilder:
    """
    Erweiterte SystemBuilder-Klasse mit Multi-Input/Output-Unterstützung.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Multi-IO System-Builder.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Konfiguration
        self.bus_separator = settings.get('bus_separator', '|')
        self.factor_separator = settings.get('factor_separator', '|')
        
        # Komponenten-Container
        self.bus_objects = {}
        self.component_objects = {}
        self.energy_system = None
        
        # Statistiken
        self.build_stats = {
            'buses': 0,
            'sources': 0,
            'sinks': 0,
            'transformers': 0,
            'multi_input_transformers': 0,
            'multi_output_transformers': 0,
            'investments': 0,
            'timeseries': 0
        }
    
    def build_energy_system(self, excel_data: Dict[str, Any]) -> solph.EnergySystem:
        """
        Baut das komplette Energiesystem mit Multi-IO-Unterstützung auf.
        
        Args:
            excel_data: Dictionary mit Excel-Daten
            
        Returns:
            Vollständiges oemof.solph EnergySystem
        """
        self.logger.info("🏗️ Beginne Energiesystem-Aufbau (Multi-IO)")
        
        # Zeitindex erstellen
        timeindex = self._create_timeindex(excel_data.get('settings', {}))
        
        # EnergySystem erstellen
        self.energy_system = solph.EnergySystem(timeindex=timeindex)
        
        # Komponenten in korrekter Reihenfolge erstellen
        self._build_buses(excel_data)
        self._build_sources(excel_data)
        self._build_sinks(excel_data)
        self._build_multi_transformers(excel_data)  # Neue Multi-IO-Transformer
        
        # Alle Objekte zum EnergySystem hinzufügen
        all_objects = list(self.bus_objects.values()) + list(self.component_objects.values())
        self.energy_system.add(*all_objects)
        
        # Statistiken ausgeben
        self._log_build_statistics()
        
        self.logger.info("✅ Energiesystem-Aufbau abgeschlossen")
        return self.energy_system
    
    def _create_timeindex(self, settings: Dict[str, Any]) -> pd.DatetimeIndex:
        """Erstellt den Zeitindex aus den Settings."""
        start = settings.get('timeindex_start', '2025-01-01')
        periods = int(settings.get('timeindex_periods', 8760))
        freq = settings.get('timeindex_freq', 'h')
        
        timeindex = pd.date_range(start=start, periods=periods, freq=freq)
        self.logger.info(f"⏰ Zeitindex: {timeindex[0]} bis {timeindex[-1]} ({len(timeindex)} Perioden)")
        
        return timeindex
    
    def _build_buses(self, excel_data: Dict[str, Any]):
        """Erstellt alle Bus-Objekte."""
        if 'buses' not in excel_data:
            self.logger.warning("⚠️ Keine Buses definiert")
            return
        
        buses_df = excel_data['buses']
        self.logger.info(f"🚌 Erstelle {len(buses_df)} Buses...")
        
        for _, bus_data in buses_df.iterrows():
            if bus_data.get('include', 0) != 1:
                continue
                
            label = bus_data['label']
            
            try:
                bus = solph.buses.Bus(label=label)
                self.bus_objects[label] = bus
                self.build_stats['buses'] += 1
                
                self.logger.debug(f"      ✓ Bus: {label}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Bus '{label}': {e}")
                raise
    
    def _build_sources(self, excel_data: Dict[str, Any]):
        """Erstellt alle Source-Objekte."""
        if 'sources' not in excel_data:
            self.logger.info("   ⏭️ Keine Sources definiert")
            return
        
        sources_df = excel_data['sources']
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   ⚡ Erstelle {len(sources_df)} Sources...")
        
        for _, source_data in sources_df.iterrows():
            if source_data.get('include', 0) != 1:
                continue
                
            label = source_data['label']
            
            try:
                # Multi-Output-Unterstützung für Sources
                output_buses = self._parse_bus_list(source_data.get('output_bus', source_data.get('bus', '')))
                
                if not output_buses:
                    self.logger.warning(f"Source '{label}': Keine Output-Busse definiert")
                    continue
                
                # Multi-Output-Flows erstellen
                output_flows = self._create_multi_flows(
                    source_data, output_buses, timeseries_data, 'output'
                )
                
                # Source erstellen
                source = solph.components.Source(
                    label=label,
                    outputs=output_flows
                )
                
                self.component_objects[label] = source
                self.build_stats['sources'] += 1
                
                # Investment-Statistik
                if source_data.get('investment', 0) == 1:
                    self.build_stats['investments'] += 1
                    
                if len(output_buses) > 1:
                    self.logger.debug(f"      ✓ Multi-Output Source: {label} → {output_buses}")
                else:
                    self.logger.debug(f"      ✓ Source: {label} → {output_buses[0]}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Source '{label}': {e}")
                raise
    
    def _build_sinks(self, excel_data: Dict[str, Any]):
        """Erstellt alle Sink-Objekte."""
        if 'sinks' not in excel_data:
            self.logger.info("   ⏭️ Keine Sinks definiert")
            return
        
        sinks_df = excel_data['sinks']
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   🔽 Erstelle {len(sinks_df)} Sinks...")
        
        for _, sink_data in sinks_df.iterrows():
            if sink_data.get('include', 0) != 1:
                continue
                
            label = sink_data['label']
            
            try:
                # Multi-Input-Unterstützung für Sinks
                input_buses = self._parse_bus_list(sink_data.get('input_bus', sink_data.get('bus', '')))
                
                if not input_buses:
                    self.logger.warning(f"Sink '{label}': Keine Input-Busse definiert")
                    continue
                
                # Multi-Input-Flows erstellen
                input_flows = self._create_multi_flows(
                    sink_data, input_buses, timeseries_data, 'input'
                )
                
                # Sink erstellen
                sink = solph.components.Sink(
                    label=label,
                    inputs=input_flows
                )
                
                self.component_objects[label] = sink
                self.build_stats['sinks'] += 1
                
                # Investment-Statistik
                if sink_data.get('investment', 0) == 1:
                    self.build_stats['investments'] += 1
                    
                if len(input_buses) > 1:
                    self.logger.debug(f"      ✓ Multi-Input Sink: {input_buses} → {label}")
                else:
                    self.logger.debug(f"      ✓ Sink: {input_buses[0]} → {label}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Sink '{label}': {e}")
                raise
    
    def _build_multi_transformers(self, excel_data: Dict[str, Any]):
        """Erstellt alle Multi-Input/Output-Transformer-Objekte."""
        if 'simple_transformers' not in excel_data:
            self.logger.info("   ⏭️ Keine Transformers definiert")
            return
        
        transformers_df = excel_data['simple_transformers']
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   🔄 Erstelle {len(transformers_df)} Multi-IO-Transformers...")
        
        for _, transformer_data in transformers_df.iterrows():
            if transformer_data.get('include', 0) != 1:
                continue
                
            label = transformer_data['label']
            
            try:
                # Input- und Output-Busse parsen
                input_buses = self._parse_bus_list(transformer_data.get('input_bus', ''))
                output_buses = self._parse_bus_list(transformer_data.get('output_bus', ''))
                
                if not input_buses or not output_buses:
                    self.logger.warning(f"Transformer '{label}': Keine Input- oder Output-Busse definiert")
                    continue
                
                # Validierung
                if not self._validate_multi_transformer(transformer_data, input_buses, output_buses):
                    continue
                
                # Flows erstellen
                input_flows = self._create_multi_flows(
                    transformer_data, input_buses, timeseries_data, 'input'
                )
                output_flows = self._create_multi_flows(
                    transformer_data, output_buses, timeseries_data, 'output'
                )
                
                # Conversion-Faktoren erstellen
                conversion_factors = self._create_conversion_factors(
                    transformer_data, output_buses, output_flows
                )
                
                # Converter erstellen
                converter = solph.components.Converter(
                    label=label,
                    inputs=input_flows,
                    outputs=output_flows,
                    conversion_factors=conversion_factors
                )
                
                self.component_objects[label] = converter
                self.build_stats['transformers'] += 1
                
                # Investment-Statistik
                if transformer_data.get('investment', 0) == 1:
                    self.build_stats['investments'] += 1
                
                # Multi-IO-Statistiken
                if len(input_buses) > 1:
                    self.build_stats['multi_input_transformers'] += 1
                if len(output_buses) > 1:
                    self.build_stats['multi_output_transformers'] += 1
                
                # Logging
                input_str = " + ".join(input_buses) if len(input_buses) > 1 else input_buses[0]
                output_str = " + ".join(output_buses) if len(output_buses) > 1 else output_buses[0]
                self.logger.debug(f"      ✓ Transformer: {input_str} → {output_str}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Transformer '{label}': {e}")
                raise
    
    def _parse_bus_list(self, bus_string: str) -> List[str]:
        """
        Parst Bus-String mit Trennzeichen.
        
        Args:
            bus_string: "el_bus|heat_bus|co2_bus" oder "el_bus"
            
        Returns:
            Liste der Bus-Namen
        """
        if not bus_string or pd.isna(bus_string):
            return []
        
        bus_str = str(bus_string).strip()
        
        if self.bus_separator in bus_str:
            bus_list = [bus.strip() for bus in bus_str.split(self.bus_separator)]
            return [bus for bus in bus_list if bus]  # Leere entfernen
        else:
            return [bus_str] if bus_str else []
    
    def _parse_conversion_factors(self, factor_string: str, expected_count: int) -> List[float]:
        """
        Parst Conversion-Factors für Multi-Outputs.
        
        Args:
            factor_string: "0.35|0.50" oder "3.5"
            expected_count: Erwartete Anzahl Faktoren
            
        Returns:
            Liste der Conversion-Faktoren
        """
        if not factor_string or pd.isna(factor_string):
            return [1.0] * expected_count
        
        factor_str = str(factor_string).strip()
        
        if self.factor_separator in factor_str:
            factors = [float(f.strip()) for f in factor_str.split(self.factor_separator)]
        else:
            factors = [float(factor_str)]
        
        # Länge anpassen
        if len(factors) == 1 and expected_count > 1:
            # Ersten Faktor für alle verwenden
            factors = factors * expected_count
        elif len(factors) != expected_count:
            raise ValueError(f"Anzahl Conversion-Faktoren ({len(factors)}) ≠ Erwartete Anzahl ({expected_count})")
        
        return factors
    
    def _create_multi_flows(self, component_data: pd.Series, bus_list: List[str], 
                           timeseries_data: pd.DataFrame, flow_type: str) -> Dict[Any, Any]:
        """
        Erstellt mehrere Flows für Multi-Input/Output-Komponenten.
        
        Args:
            component_data: Komponenten-Daten
            bus_list: Liste der verbundenen Busse
            timeseries_data: Zeitreihendaten
            flow_type: 'input' oder 'output'
            
        Returns:
            Dictionary {bus_object: flow_object}
        """
        flows = {}
        
        for i, bus_name in enumerate(bus_list):
            # Bus-Objekt auflösen
            if bus_name not in self.bus_objects:
                raise ValueError(f"Bus '{bus_name}' nicht gefunden")
            
            bus_obj = self.bus_objects[bus_name]
            
            # Investment nur für ersten Flow (Index 0)
            if i == 0:
                # Erster Flow: mit Investment-Möglichkeit
                flow = self._create_investment_flow(component_data, timeseries_data, flow_type)
            else:
                # Weitere Flows: ohne Investment
                flow = self._create_standard_flow(component_data, timeseries_data, flow_type)
            
            flows[bus_obj] = flow
        
        return flows
    
    def _create_investment_flow(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                               flow_type: str) -> Flow:
        """
        Erstellt einen Flow mit Investment-Möglichkeit.
        
        Args:
            component_data: Komponenten-Daten
            timeseries_data: Zeitreihendaten
            flow_type: 'input' oder 'output'
            
        Returns:
            Flow-Objekt
        """
        flow_params = {}
        
        # Investment-Kapazität verarbeiten
        capacity = self._process_investment_capacity(component_data)
        if capacity is not None:
            flow_params['nominal_capacity'] = capacity
        
        # Variable Kosten
        if 'variable_costs' in component_data and pd.notna(component_data['variable_costs']):
            try:
                var_costs = float(component_data['variable_costs'])
                flow_params['variable_costs'] = var_costs
            except (ValueError, TypeError):
                pass
        
        # Profile verarbeiten
        profile = self._process_profiles(component_data, timeseries_data, flow_type)
        if profile is not None:
            if flow_type == 'input':
                # Für Inputs: fix profile
                flow_params['fix'] = profile
                # Auto-Kapazität wenn nicht gesetzt
                if 'nominal_capacity' not in flow_params:
                    flow_params['nominal_capacity'] = max(profile) * 1.2
            else:
                # Für Outputs: max profile
                flow_params['max'] = profile
        
        # Flow erstellen
        try:
            return Flow(**flow_params)
        except Exception as e:
            self.logger.warning(f"Fehler beim Erstellen des Investment-Flows: {e}")
            return Flow()
    
    def _create_standard_flow(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                             flow_type: str) -> Flow:
        """
        Erstellt einen Standard-Flow ohne Investment.
        
        Args:
            component_data: Komponenten-Daten
            timeseries_data: Zeitreihendaten
            flow_type: 'input' oder 'output'
            
        Returns:
            Flow-Objekt
        """
        flow_params = {}
        
        # Nur Standard-Kapazität (existing)
        if 'existing' in component_data and pd.notna(component_data['existing']):
            try:
                existing = float(component_data['existing'])
                if existing > 0:
                    flow_params['nominal_capacity'] = existing
            except (ValueError, TypeError):
                pass
        
        # Variable Kosten
        if 'variable_costs' in component_data and pd.notna(component_data['variable_costs']):
            try:
                var_costs = float(component_data['variable_costs'])
                flow_params['variable_costs'] = var_costs
            except (ValueError, TypeError):
                pass
        
        # Profile verarbeiten (vereinfacht)
        profile = self._process_profiles(component_data, timeseries_data, flow_type)
        if profile is not None:
            if flow_type == 'input':
                flow_params['fix'] = profile
            else:
                flow_params['max'] = profile
        
        # Flow erstellen
        try:
            return Flow(**flow_params)
        except Exception as e:
            self.logger.warning(f"Fehler beim Erstellen des Standard-Flows: {e}")
            return Flow()
    
    def _process_investment_capacity(self, component_data: pd.Series) -> Optional[Union[float, Investment]]:
        """
        Verarbeitet Investment-Kapazität mit Annuity-Berechnung.
        
        Args:
            component_data: Komponenten-Daten
            
        Returns:
            Float-Wert oder Investment-Objekt
        """
        # Prüfe ob Investment aktiviert
        if component_data.get('investment', 0) != 1:
            # Kein Investment: existing als nominal_capacity verwenden
            if 'existing' in component_data and pd.notna(component_data['existing']):
                try:
                    existing = float(component_data['existing'])
                    return existing if existing > 0 else None
                except (ValueError, TypeError):
                    pass
            return None
        
        # Investment aktiviert: Investment-Objekt erstellen
        try:
            investment_costs = float(component_data.get('investment_costs', 0))
            existing = float(component_data.get('existing', 0))
            invest_min = float(component_data.get('invest_min', 0))
            invest_max = float(component_data.get('invest_max', 500))  # Fallback
            
            # EP-Costs berechnen
            ep_costs = self._calculate_ep_costs(component_data, investment_costs)
            
            # Investment-Objekt erstellen
            investment = Investment(
                ep_costs=ep_costs,
                existing=existing,
                minimum=invest_min,
                maximum=invest_max
            )
            
            return investment
            
        except Exception as e:
            self.logger.warning(f"Fehler bei Investment-Verarbeitung: {e}")
            return None
    
    def _calculate_ep_costs(self, component_data: pd.Series, investment_costs: float) -> float:
        """
        Berechnet EP-Costs mit Annuity-Formel.
        
        Args:
            component_data: Komponenten-Daten
            investment_costs: Investitionskosten
            
        Returns:
            EP-Costs-Wert
        """
        lifetime = component_data.get('lifetime', None)
        interest_rate = component_data.get('interest_rate', None)
        
        if lifetime and interest_rate is not None:
            try:
                lifetime = float(lifetime)
                interest_rate = float(interest_rate)
                
                if interest_rate == 0:
                    # Zinssatz = 0: Einfache Division
                    return investment_costs / lifetime
                else:
                    # Annuity-Formel
                    q = 1 + interest_rate
                    annuity_factor = (interest_rate * q**lifetime) / (q**lifetime - 1)
                    return investment_costs * annuity_factor
                    
            except (ValueError, TypeError):
                pass
        
        # Fallback: Direkte Kosten
        return investment_costs
    
    def _process_profiles(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                         flow_type: str) -> Optional[List[float]]:
        """
        Verarbeitet Profile aus Zeitreihendaten.
        
        Args:
            component_data: Komponenten-Daten
            timeseries_data: Zeitreihendaten
            flow_type: 'input' oder 'output'
            
        Returns:
            Liste der Profil-Werte
        """
        profile_column = component_data.get('profile_column', '')
        
        if not profile_column or pd.isna(profile_column):
            return None
        
        if profile_column not in timeseries_data.columns:
            self.logger.warning(f"Profil-Spalte '{profile_column}' nicht in Zeitreihendaten gefunden")
            return None
        
        profile_values = timeseries_data[profile_column].values
        
        if len(profile_values) == 0:
            return None
        
        # Für Sources: Normalisierung auf max=1.0
        if flow_type == 'output' and max(profile_values) > 1.0:
            profile_values = profile_values / max(profile_values)
        
        return profile_values.tolist()
    
    def _create_conversion_factors(self, transformer_data: pd.Series, output_buses: List[str], 
                                  output_flows: Dict[Any, Any]) -> Dict[Any, float]:
        """
        Erstellt Conversion-Faktoren-Dictionary für Multi-Output-Transformer.
        
        Args:
            transformer_data: Transformer-Daten
            output_buses: Liste der Output-Bus-Namen
            output_flows: Dictionary der Output-Flows
            
        Returns:
            Dictionary {bus_object: conversion_factor}
        """
        conversion_factors = {}
        
        if len(output_buses) == 1:
            # Single-Output: conversion_factor verwenden
            factor = float(transformer_data.get('conversion_factor', 1.0))
            bus_obj = list(output_flows.keys())[0]
            conversion_factors[bus_obj] = factor
        else:
            # Multi-Output: output_conversion_factors verwenden
            factors_str = transformer_data.get('output_conversion_factors', 
                                              transformer_data.get('conversion_factor', '1.0'))
            factors = self._parse_conversion_factors(factors_str, len(output_buses))
            
            for i, (bus_obj, flow) in enumerate(output_flows.items()):
                conversion_factors[bus_obj] = factors[i]
        
        return conversion_factors
    
    def _validate_multi_transformer(self, transformer_data: pd.Series, 
                                   input_buses: List[str], output_buses: List[str]) -> bool:
        """
        Validiert Multi-Input/Output-Transformer-Konfiguration.
        
        Args:
            transformer_data: Transformer-Daten
            input_buses: Liste der Input-Busse
            output_buses: Liste der Output-Busse
            
        Returns:
            True wenn gültig
        """
        label = transformer_data.get('label', 'unknown')
        
        # Mindestens ein Input und ein Output
        if not input_buses or not output_buses:
            self.logger.error(f"Transformer '{label}': Mindestens ein Input und Output erforderlich")
            return False
        
        # Alle Busse existieren?
        for bus_name in input_buses + output_buses:
            if bus_name not in self.bus_objects:
                self.logger.error(f"Transformer '{label}': Bus '{bus_name}' nicht gefunden")
                return False
        
        # Conversion-Faktoren prüfen
        if len(output_buses) > 1:
            factors_str = transformer_data.get('output_conversion_factors', 
                                              transformer_data.get('conversion_factor', '1.0'))
            try:
                factors = self._parse_conversion_factors(factors_str, len(output_buses))
                if len(factors) != len(output_buses):
                    self.logger.error(f"Transformer '{label}': Anzahl Conversion-Faktoren stimmt nicht")
                    return False
            except ValueError as e:
                self.logger.error(f"Transformer '{label}': {e}")
                return False
        
        return True
    
    def _log_build_statistics(self):
        """Gibt Aufbau-Statistiken aus."""
        self.logger.info("📊 Multi-IO Aufbau-Statistiken:")
        for component_type, count in self.build_stats.items():
            if count > 0:
                self.logger.info(f"   {component_type.replace('_', ' ').title()}: {count}")
    
    def get_system_summary(self, energy_system: solph.EnergySystem) -> Dict[str, str]:
        """
        Erstellt eine Zusammenfassung des Multi-IO-Energiesystems.
        
        Args:
            energy_system: Das oemof.solph EnergySystem
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        summary = {}
        
        # Zeitindex-Informationen
        timeindex = energy_system.timeindex
        summary['Zeitraum'] = f"{timeindex[0].strftime('%Y-%m-%d')} bis {timeindex[-1].strftime('%Y-%m-%d')}"
        summary['Zeitschritte'] = f"{len(timeindex)} ({pd.infer_freq(timeindex) or 'variabel'})"
        
        # Komponenten-Statistiken
        nodes = energy_system.nodes
        
        # Nach Typen klassifizieren
        buses = [n for n in nodes if isinstance(n, solph.buses.Bus)]
        sources = [n for n in nodes if isinstance(n, solph.components.Source)]
        sinks = [n for n in nodes if isinstance(n, solph.components.Sink)]
        converters = [n for n in nodes if isinstance(n, solph.components.Converter)]
        
        summary['Buses'] = str(len(buses))
        summary['Sources'] = str(len(sources))
        summary['Sinks'] = str(len(sinks))
        summary['Converter'] = str(len(converters))
        
        # Multi-IO-Statistiken
        summary['Multi-Input-Transformer'] = str(self.build_stats.get('multi_input_transformers', 0))
        summary['Multi-Output-Transformer'] = str(self.build_stats.get('multi_output_transformers', 0))
        
        # Investment-Komponenten zählen
        investment_count = 0
        for node in nodes:
            if hasattr(node, 'inputs'):
                for flow in node.inputs.values():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_count += 1
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_count += 1
        
        if investment_count > 0:
            summary['Investment-Flows'] = str(investment_count)
        
        summary['Gesamt-Knoten'] = str(len(nodes))
        
        return summary


# Backward-Kompatibilität: Alias für die alte SystemBuilder-Klasse
SystemBuilder = MultiIOSystemBuilder


# Test-Funktion
def test_multi_io_system_builder():
    """Test-Funktion für den Multi-IO-System-Builder."""
    # Test-Daten
    test_data = {
        'settings': {
            'timeindex_start': '2025-01-01',
            'timeindex_periods': 24,
            'timeindex_freq': 'h'
        },
        'buses': pd.DataFrame({
            'label': ['el_bus', 'heat_bus', 'gas_bus'],
            'include': [1, 1, 1],
            'description': ['Elektrischer Bus', 'Wärme-Bus', 'Gas-Bus']
        }),
        'simple_transformers': pd.DataFrame({
            'label': ['chp_plant'],
            'include': [1],
            'input_bus': ['gas_bus'],
            'output_bus': ['el_bus|heat_bus'],
            'output_conversion_factors': ['0.35|0.50'],
            'existing': [0],
            'investment': [1],
            'investment_costs': [2000],
            'lifetime': [15],
            'interest_rate': [0.04]
        })
    }
    
    # System-Builder testen
    settings = {'debug_mode': True}
    builder = MultiIOSystemBuilder(settings)
    
    try:
        energy_system = builder.build_energy_system(test_data)
        summary = builder.get_system_summary(energy_system)
        
        print("✅ Multi-IO-System-Builder Test erfolgreich!")
        print("Zusammenfassung:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_multi_io_system_builder()
