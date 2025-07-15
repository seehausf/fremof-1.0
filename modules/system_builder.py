#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Energiesystem-Aufbau Modul
===========================================

Baut oemof.solph Energiesysteme aus Excel-Daten auf.
Unterstützt Buses, Sources, Sinks, Simple Transformers und Investment-Optionen.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
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
    # In 0.6.0: Flow ist direkt verfügbar
    Flow = solph.Flow
except ImportError as e:
    print(f"❌ oemof.solph nicht verfügbar: {e}")
    print("Installieren Sie oemof.solph: pip install oemof.solph>=0.6.0")
    raise


class SystemBuilder:
    """Klasse für den Aufbau von oemof.solph Energiesystemen aus Excel-Daten."""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den System-Builder.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
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
            'investments': 0,
            'timeseries': 0
        }
    
    def build_energy_system(self, excel_data: Dict[str, Any]) -> solph.EnergySystem:
        """
        Baut das komplette Energiesystem aus Excel-Daten auf.
        
        Args:
            excel_data: Dictionary mit Excel-Daten vom ExcelReader
            
        Returns:
            oemof.solph.EnergySystem Objekt
        """
        self.logger.info("🏗️  Baue Energiesystem auf...")
        
        # Zeitindex aus Excel-Daten
        timeindex = excel_data.get('timeindex')
        if timeindex is None:
            raise ValueError("Kein Zeitindex in Excel-Daten gefunden")
        
        # Debug: Zeitindex-Informationen loggen
        self.logger.debug(f"Zeitindex-Typ: {type(timeindex)}")
        self.logger.debug(f"Zeitindex-Länge: {len(timeindex)}")
        self.logger.debug(f"Erste 3 Werte: {timeindex[:3].tolist()}")
        
        # EnergySystem erstellen
        try:
            # Prüfen ob der Zeitindex eine gültige Frequenz hat
            timeindex_info = excel_data.get('timeindex_info', {})
            has_freq = timeindex_info.get('has_freq', False)
            
            if has_freq:
                # Für Zeitreihen mit N-1 Werten bei N Zeitpunkten: infer_last_interval=True
                infer_last = True
                self.logger.debug("Zeitindex hat gültige Frequenz - verwende infer_last_interval=True")
            else:
                # Keine gültige Frequenz: infer_last_interval=False
                infer_last = False
                self.logger.debug("Zeitindex hat keine gültige Frequenz - verwende infer_last_interval=False")
            
            self.energy_system = solph.EnergySystem(
                timeindex=timeindex,
                infer_last_interval=infer_last
            )
            self.logger.debug("✅ EnergySystem erfolgreich erstellt")
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen des EnergySystem: {e}")
            raise
        
        # Komponenten in der richtigen Reihenfolge erstellen
        try:
            self._build_buses(excel_data)
            self._build_sources(excel_data)
            self._build_sinks(excel_data)
            self._build_simple_transformers(excel_data)
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen der Komponenten: {e}")
            raise
        
        # Alle Komponenten zum Energiesystem hinzufügen
        try:
            all_components = list(self.bus_objects.values()) + list(self.component_objects.values())
            self.energy_system.add(*all_components)
            self.logger.debug(f"✅ {len(all_components)} Komponenten hinzugefügt")
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Hinzufügen der Komponenten: {e}")
            raise
        
        self.logger.info("✅ Energiesystem erfolgreich aufgebaut")
        self._log_build_statistics()
        
        return self.energy_system
    
    def _build_buses(self, excel_data: Dict[str, Any]):
        """Erstellt alle Bus-Objekte."""
        if 'buses' not in excel_data:
            raise ValueError("Keine Bus-Definitionen gefunden")
        
        buses_df = excel_data['buses']
        self.logger.info(f"   🚌 Erstelle {len(buses_df)} Buses...")
        
        for _, bus_data in buses_df.iterrows():
            label = bus_data['label']
            
            try:
                # Bus erstellen (in 0.6.0 ist Bus in solph.buses)
                bus = solph.buses.Bus(label=label)
                
                self.bus_objects[label] = bus
                self.build_stats['buses'] += 1
                
                self.logger.debug(f"      ✓ Bus: {label}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Bus '{label}': {e}")
                raise
    
    def _build_sources(self, excel_data: Dict[str, Any]):
        """Erstellt alle Source-Objekte mit neuer Investment-Logik."""
        if 'sources' not in excel_data:
            self.logger.info("   ⏭️  Keine Sources definiert")
            return
        
        sources_df = excel_data['sources']
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   ⚡ Erstelle {len(sources_df)} Sources...")
        
        for _, source_data in sources_df.iterrows():
            label = source_data['label']
            bus_label = source_data['bus']
            
            try:
                # Bus-Referenz auflösen
                if bus_label not in self.bus_objects:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden")
                
                bus = self.bus_objects[bus_label]
                
                # NEUE Investment-Logik: Flow erstellen
                flow = self._create_investment_flow(source_data, timeseries_data, 'source')
                
                # Source erstellen
                source = solph.components.Source(
                    label=label,
                    outputs={bus: flow}  # Immer der erste (und einzige) Output-Flow
                )
                
                self.component_objects[label] = source
                self.build_stats['sources'] += 1
                
                # Investment-Statistik
                if source_data.get('is_investment', False):
                    self.build_stats['investments'] += 1
                    self.logger.debug(f"      ✓ Source (Investment): {label} -> {bus_label}")
                else:
                    self.logger.debug(f"      ✓ Source: {label} -> {bus_label}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Source '{label}': {e}")
                raise
    
    def _build_sinks(self, excel_data: Dict[str, Any]):
        """Erstellt alle Sink-Objekte mit neuer Investment-Logik."""
        if 'sinks' not in excel_data:
            self.logger.info("   ⏭️  Keine Sinks definiert")
            return
        
        sinks_df = excel_data['sinks']
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   🔽 Erstelle {len(sinks_df)} Sinks...")
        
        for _, sink_data in sinks_df.iterrows():
            label = sink_data['label']
            bus_label = sink_data['bus']
            
            try:
                # Bus-Referenz auflösen
                if bus_label not in self.bus_objects:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden")
                
                bus = self.bus_objects[bus_label]
                
                # NEUE Investment-Logik: Flow erstellen
                flow = self._create_investment_flow(sink_data, timeseries_data, 'sink')
                
                # Sink erstellen
                sink = solph.components.Sink(
                    label=label,
                    inputs={bus: flow}  # Immer der erste (und einzige) Input-Flow
                )
                
                self.component_objects[label] = sink
                self.build_stats['sinks'] += 1
                
                # Investment-Statistik
                if sink_data.get('is_investment', False):
                    self.build_stats['investments'] += 1
                    self.logger.debug(f"      ✓ Sink (Investment): {bus_label} -> {label}")
                else:
                    self.logger.debug(f"      ✓ Sink: {bus_label} -> {label}")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Sink '{label}': {e}")
                raise
    
    def _build_simple_transformers(self, excel_data: Dict[str, Any]):
        """Erstellt alle Simple Transformer-Objekte mit neuer Investment-Logik."""
        if 'simple_transformers' not in excel_data:
            self.logger.info("   ⏭️  Keine Simple Transformers definiert")
            return
        
        transformers_df = excel_data['simple_transformers']
        
        if len(transformers_df) == 0:
            self.logger.info("   ⏭️  Simple Transformers Sheet leer")
            return
        
        timeseries_data = excel_data.get('timeseries', pd.DataFrame())
        
        self.logger.info(f"   🔄 Erstelle {len(transformers_df)} Simple Transformers...")
        
        for _, transformer_data in transformers_df.iterrows():
            label = transformer_data['label']
            input_bus_label = transformer_data['input_bus']
            output_bus_label = transformer_data['output_bus']
            conversion_factor = float(transformer_data['conversion_factor'])
            
            try:
                # Bus-Referenzen auflösen
                if input_bus_label not in self.bus_objects:
                    raise ValueError(f"Input Bus '{input_bus_label}' nicht gefunden")
                if output_bus_label not in self.bus_objects:
                    raise ValueError(f"Output Bus '{output_bus_label}' nicht gefunden")
                
                input_bus = self.bus_objects[input_bus_label]
                output_bus = self.bus_objects[output_bus_label]
                
                # NEUE Investment-Logik: Input Flow erstellen (Investment-Flow)
                input_flow = self._create_investment_flow(transformer_data, timeseries_data, 'transformer_input')
                
                # Output Flow erstellen (normaler Flow ohne Investment)
                output_flow_data = transformer_data.copy()
                output_flow_data['is_investment'] = False  # Output-Flow nie Investment
                output_flow_data['existing'] = None  # Kapazität wird über Input bestimmt
                output_flow = self._create_investment_flow(output_flow_data, timeseries_data, 'transformer_output')
                
                # Converter erstellen
                converter = solph.components.Converter(
                    label=label,
                    inputs={input_bus: input_flow},   # Investment-Flow am Input
                    outputs={output_bus: output_flow},
                    conversion_factors={output_bus: conversion_factor}
                )
                
                self.component_objects[label] = converter
                self.build_stats['transformers'] += 1
                
                # Investment-Statistik
                if transformer_data.get('is_investment', False):
                    self.build_stats['investments'] += 1
                    self.logger.debug(f"      ✓ Converter (Investment): {input_bus_label} -> {output_bus_label} (η={conversion_factor})")
                else:
                    self.logger.debug(f"      ✓ Converter: {input_bus_label} -> {output_bus_label} (η={conversion_factor})")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler beim Erstellen von Converter '{label}': {e}")
                raise
    
    def _create_investment_flow(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                               flow_type: str) -> Flow:
        """
        NEUE METHODE: Erstellt ein Flow-Objekt mit neuer Investment-Logik.
        
        Args:
            component_data: Pandas Series mit Komponentendaten
            timeseries_data: DataFrame mit Zeitreihendaten
            flow_type: Art des Flows ('source', 'sink', 'transformer_input', 'transformer_output')
            
        Returns:
            oemof.solph.Flow Objekt
        """
        flow_params = {}
        
        # NEUE Investment-Logik anwenden
        nominal_capacity = self._process_new_investment_capacity(component_data)
        if nominal_capacity is not None:
            flow_params['nominal_capacity'] = nominal_capacity
        
        # Variable Costs (unverändert)
        if 'variable_costs' in component_data and pd.notna(component_data['variable_costs']):
            try:
                var_costs = float(component_data['variable_costs'])
                flow_params['variable_costs'] = var_costs
            except (ValueError, TypeError):
                pass
        
        # Profile verarbeiten (unverändert)
        profile = self._process_profiles(component_data, timeseries_data, flow_type)
        if profile is not None:
            if flow_type == 'sink':
                # Für Sinks: fix profile
                flow_params['fix'] = profile
                # Wenn kein nominal_capacity gesetzt ist, verwende das Maximum des Profils
                if 'nominal_capacity' not in flow_params:
                    max_profile_value = max(profile) if profile else 1.0
                    flow_params['nominal_capacity'] = max_profile_value * 1.2  # 20% Puffer
                    self.logger.debug(f"Automatische nominal_capacity für Sink mit fix Profile: {flow_params['nominal_capacity']:.2f}")
            else:
                # Für Sources: max profile
                flow_params['max'] = profile
        
        # Min/Max Constraints (TODO: implementieren)
        if 'min' in component_data and pd.notna(component_data['min']):
            try:
                min_val = float(component_data['min'])
                flow_params['min'] = min_val
            except (ValueError, TypeError):
                pass
        
        if 'max' in component_data and pd.notna(component_data['max']):
            try:
                max_val = float(component_data['max'])
                flow_params['max'] = max_val
            except (ValueError, TypeError):
                pass
        
        # NonConvex Parameter (unverändert)
        nonconvex_obj = self._create_nonconvex(component_data)
        if nonconvex_obj is not None:
            flow_params['nonconvex'] = nonconvex_obj
        
        # Flow erstellen
        try:
            return Flow(**flow_params)
        except Exception as e:
            self.logger.warning(f"Fehler beim Erstellen des Investment-Flows: {e}")
            self.logger.warning(f"Flow-Parameter: {flow_params}")
            # Fallback: Minimaler Flow
            return Flow()
    
    def _process_new_investment_capacity(self, component_data: pd.Series) -> Optional[Union[float, Any]]:
        """
        ERWEITERT: Verarbeitet Investment-Kapazität mit Annuity-Berechnung.
        
        Neue Logik für ep_costs:
        1. Nur investment_costs → ep_costs = investment_costs
        2. investment_costs + lifetime + interest_rate → ep_costs = Annuity
        """
        is_investment = component_data.get('is_investment', False)
        existing_value = component_data.get('existing')
        
        if is_investment:
            # Investment-Fall: Erstelle Investment-Objekt
            investment_params = {}
            
            # NEUE ANNUITY-BERECHNUNG FÜR EP_COSTS
            ep_costs = self._calculate_ep_costs(component_data)
            if ep_costs is not None:
                investment_params['ep_costs'] = ep_costs
            
            # Investment-Grenzen (unverändert)
            if 'invest_min' in component_data and pd.notna(component_data['invest_min']):
                investment_params['minimum'] = float(component_data['invest_min'])
            
            if 'invest_max' in component_data and pd.notna(component_data['invest_max']):
                investment_params['maximum'] = float(component_data['invest_max'])
            
            # Existing capacity als bestehende Kapazität (unverändert)
            if existing_value is not None and pd.notna(existing_value):
                try:
                    existing_cap = float(existing_value)
                    if existing_cap >= 0:
                        investment_params['existing'] = existing_cap
                except (ValueError, TypeError):
                    self.logger.warning(f"Ungültiger existing-Wert für Investment: {existing_value}")
            
            # Investment-Objekt erstellen
            if investment_params:
                return Investment(**investment_params)
            else:
                self.logger.warning("Investment aktiviert, aber keine Investment-Parameter gefunden")
                return None
        
        else:
            # Normaler Fall: existing → nominal_capacity (unverändert)
            if existing_value is not None and pd.notna(existing_value):
                try:
                    existing_cap = float(existing_value)
                    if existing_cap > 0:
                        return existing_cap
                    else:
                        self.logger.warning(f"existing-Wert <= 0: {existing_cap}")
                        return None
                except (ValueError, TypeError):
                    self.logger.warning(f"Ungültiger existing-Wert: {existing_value}")
                    return None
            else:
                return None
            
    def get_investment_summary(self, energy_system: solph.EnergySystem) -> Dict[str, Any]:
        """
        NEUE METHODE: Erstellt eine Zusammenfassung aller Investment-Komponenten.
        
        Args:
            energy_system: Das oemof.solph EnergySystem
            
        Returns:
            Dictionary mit Investment-Zusammenfassung
        """
        investment_summary = {
            'total_investments': 0,
            'sources_with_investment': [],
            'sinks_with_investment': [],
            'transformers_with_investment': [],
            'total_potential_capacity': 0,
            'total_investment_costs_max': 0
        }
        
        nodes = energy_system.nodes
        
        for node in nodes:
            node_label = str(node.label)
            
            # Investment-Flows finden
            investment_flows = []
            
            # Inputs prüfen
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_flows.append({
                            'direction': 'input',
                            'connection': f"{input_node.label} → {node.label}",
                            'investment': flow.nominal_capacity
                        })
            
            # Outputs prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_flows.append({
                            'direction': 'output',
                            'connection': f"{node.label} → {output_node.label}",
                            'investment': flow.nominal_capacity
                        })
            
            # Investment-Komponenten kategorisieren
            if investment_flows:
                investment_summary['total_investments'] += 1
                
                # Komponententyp bestimmen
                if isinstance(node, solph.components.Source):
                    investment_summary['sources_with_investment'].append({
                        'label': node_label,
                        'flows': investment_flows
                    })
                elif isinstance(node, solph.components.Sink):
                    investment_summary['sinks_with_investment'].append({
                        'label': node_label,
                        'flows': investment_flows
                    })
                elif isinstance(node, solph.components.Converter):
                    investment_summary['transformers_with_investment'].append({
                        'label': node_label,
                        'flows': investment_flows
                    })
                
                # Potentiale und Kosten summieren
                for flow_info in investment_flows:
                    investment = flow_info['investment']
                    
                    if hasattr(investment, 'maximum') and investment.maximum:
                        investment_summary['total_potential_capacity'] += investment.maximum
                    
                    if hasattr(investment, 'ep_costs') and investment.ep_costs:
                        if hasattr(investment, 'maximum') and investment.maximum:
                            max_costs = investment.ep_costs * investment.maximum
                            investment_summary['total_investment_costs_max'] += max_costs
        
        return investment_summary    
    
    def _create_flow(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                     flow_type: str) -> Flow:
        """
        Erstellt ein Flow-Objekt basierend auf Komponentendaten.
        
        Args:
            component_data: Pandas Series mit Komponentendaten
            timeseries_data: DataFrame mit Zeitreihendaten
            flow_type: Art des Flows ('source', 'sink', 'transformer_input', 'transformer_output')
            
        Returns:
            oemof.solph.Flow Objekt
        """
        flow_params = {}
        
        # Nominal Capacity verarbeiten
        nominal_capacity = self._process_nominal_capacity(component_data)
        if nominal_capacity is not None:
            flow_params['nominal_capacity'] = nominal_capacity
        
        # Variable Costs
        if 'variable_costs' in component_data and pd.notna(component_data['variable_costs']):
            try:
                var_costs = float(component_data['variable_costs'])
                flow_params['variable_costs'] = var_costs
            except (ValueError, TypeError):
                pass
        
        # Profile verarbeiten
        profile = self._process_profiles(component_data, timeseries_data, flow_type)
        if profile is not None:
            if flow_type == 'sink':
                # Für Sinks: fix profile - WICHTIG: nominal_capacity muss auch gesetzt sein!
                flow_params['fix'] = profile
                # Wenn kein nominal_capacity gesetzt ist, verwende das Maximum des Profils
                if 'nominal_capacity' not in flow_params:
                    max_profile_value = max(profile) if profile else 1.0
                    flow_params['nominal_capacity'] = max_profile_value * 1.2  # 20% Puffer
                    self.logger.debug(f"Automatische nominal_capacity für Sink mit fix Profile: {flow_params['nominal_capacity']:.2f}")
            else:
                # Für Sources: max profile
                flow_params['max'] = profile
        
        # Min/Max Constraints
        if 'min' in component_data and pd.notna(component_data['min']):
            try:
                min_val = float(component_data['min'])
                flow_params['min'] = min_val
            except (ValueError, TypeError):
                pass
        
        if 'max' in component_data and pd.notna(component_data['max']):
            try:
                max_val = float(component_data['max'])
                flow_params['max'] = max_val
            except (ValueError, TypeError):
                pass
        
        # NonConvex Parameter (falls implementiert)
        nonconvex_obj = self._create_nonconvex(component_data)
        if nonconvex_obj is not None:
            flow_params['nonconvex'] = nonconvex_obj
        
        # Flow erstellen - mit expliziter Fehlerbehandlung
        try:
            return Flow(**flow_params)
        except Exception as e:
            self.logger.warning(f"Fehler beim Erstellen des Flows: {e}")
            self.logger.warning(f"Flow-Parameter: {flow_params}")
            # Fallback: Minimaler Flow
            return Flow()
    
    def _process_nominal_capacity(self, component_data: pd.Series) -> Optional[float]:
        """Verarbeitet nominal_capacity Parameter, inklusive Investment."""
        if 'nominal_capacity' not in component_data:
            return None
        
        nominal_capacity = component_data['nominal_capacity']
        
        # Investment-Fall
        if component_data.get('is_investment', False):
            investment_params = {}
            
            # Investment-Parameter sammeln
            if 'investment_costs' in component_data and pd.notna(component_data['investment_costs']):
                investment_params['ep_costs'] = float(component_data['investment_costs'])
            
            if 'invest_min' in component_data and pd.notna(component_data['invest_min']):
                investment_params['minimum'] = float(component_data['invest_min'])
            
            if 'invest_max' in component_data and pd.notna(component_data['invest_max']):
                investment_params['maximum'] = float(component_data['invest_max'])
            
            # Existing capacity
            if 'existing_capacity' in component_data and pd.notna(component_data['existing_capacity']):
                investment_params['existing'] = float(component_data['existing_capacity'])
            
            # Investment-Objekt erstellen
            return Investment(**investment_params)
        
        # Normale Kapazität
        elif pd.notna(nominal_capacity) and str(nominal_capacity).upper() != 'INVEST':
            try:
                return float(nominal_capacity)
            except (ValueError, TypeError):
                return None
        
        return None
    
    def _process_profiles(self, component_data: pd.Series, timeseries_data: pd.DataFrame, 
                         flow_type: str) -> Optional[List[float]]:
        """Verarbeitet Zeitreihen-Profile."""
        if timeseries_data.empty:
            return None
        
        # Profile-Spalte bestimmen
        profile_column = None
        
        if flow_type == 'source':
            # Für Sources: profile_column oder max_profile
            if 'profile_column' in component_data and pd.notna(component_data['profile_column']):
                profile_column = component_data['profile_column']
            elif 'max_profile' in component_data and pd.notna(component_data['max_profile']):
                profile_column = component_data['max_profile']
        
        elif flow_type == 'sink':
            # Für Sinks: profile_column oder fix_profile
            if 'profile_column' in component_data and pd.notna(component_data['profile_column']):
                profile_column = component_data['profile_column']
            elif 'fix_profile' in component_data and pd.notna(component_data['fix_profile']):
                profile_column = component_data['fix_profile']
        
        # Profil extrahieren
        if profile_column and profile_column in timeseries_data.columns:
            try:
                profile = timeseries_data[profile_column].values
                
                # NaN-Werte behandeln
                if np.isnan(profile).any():
                    self.logger.warning(f"NaN-Werte in Profil '{profile_column}' durch 0 ersetzt")
                    profile = np.nan_to_num(profile, nan=0.0)
                
                # Negative Werte prüfen
                if (profile < 0).any() and flow_type == 'source':
                    self.logger.warning(f"Negative Werte in Source-Profil '{profile_column}' durch 0 ersetzt")
                    profile = np.maximum(profile, 0)
                
                # Sicherstellen, dass alle Werte numerisch und endlich sind
                profile = np.asarray(profile, dtype=float)
                profile = np.where(np.isfinite(profile), profile, 0.0)
                
                self.build_stats['timeseries'] += 1
                return profile.tolist()
                
            except Exception as e:
                self.logger.warning(f"Fehler beim Verarbeiten von Profil '{profile_column}': {e}")
                return None
        
        return None
    
    def _create_nonconvex(self, component_data: pd.Series) -> Optional[NonConvex]:
        """Erstellt NonConvex-Objekt falls entsprechende Parameter vorhanden."""
        nonconvex_params = {}
        
        # NonConvex-Parameter sammeln
        param_mapping = {
            'minimum_uptime': 'minimum_uptime',
            'minimum_downtime': 'minimum_downtime',
            'startup_costs': 'startup_costs',
            'shutdown_costs': 'shutdown_costs',
            'maximum_startups': 'maximum_startups',
            'maximum_shutdowns': 'maximum_shutdowns',
            'initial_status': 'initial_status'
        }
        
        for excel_param, solph_param in param_mapping.items():
            if excel_param in component_data and pd.notna(component_data[excel_param]):
                try:
                    value = component_data[excel_param]
                    if excel_param in ['startup_costs', 'shutdown_costs']:
                        nonconvex_params[solph_param] = float(value)
                    else:
                        nonconvex_params[solph_param] = int(value)
                except (ValueError, TypeError):
                    self.logger.warning(f"Ungültiger NonConvex-Parameter {excel_param}: {value}")
        
        # NonConvex-Objekt nur erstellen wenn Parameter vorhanden
        if nonconvex_params:
            return NonConvex(**nonconvex_params)
        
        return None
    
    def _log_build_statistics(self):
        """Loggt Statistiken zum Aufbau des Energiesystems."""
        self.logger.info("📊 Aufbau-Statistiken:")
        for component_type, count in self.build_stats.items():
            if count > 0:
                self.logger.info(f"   {component_type.title()}: {count}")
    
    def get_system_summary(self, energy_system: solph.EnergySystem) -> Dict[str, str]:
        """
        Erstellt eine Zusammenfassung des aufgebauten Energiesystems.
        
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
        
        # Investment-Komponenten zählen
        investment_count = 0
        for node in nodes:
            if hasattr(node, 'inputs'):
                for flow in node.inputs.values():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_count += 1
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_count += 1
        
        if investment_count > 0:
            summary['Investment-Flows'] = str(investment_count)
        
        # Gesamt-Knoten
        summary['Gesamt-Knoten'] = str(len(nodes))
        
        return summary
    
    def validate_system(self, energy_system: solph.EnergySystem) -> Tuple[bool, List[str]]:
        """
        Validiert das aufgebaute Energiesystem.
        
        Args:
            energy_system: Das zu validierende EnergySystem
            
        Returns:
            Tuple (is_valid, error_messages)
        """
        errors = []
        
        # Basis-Validierung
        if len(energy_system.nodes) == 0:
            errors.append("Energiesystem ist leer")
            return False, errors
        
        # Buses prüfen
        buses = [n for n in energy_system.nodes if isinstance(n, solph.buses.Bus)]
        if len(buses) == 0:
            errors.append("Keine Buses gefunden")
        
        # Isolierte Buses prüfen
        for bus in buses:
            has_input = any(bus in node.outputs for node in energy_system.nodes if hasattr(node, 'outputs'))
            has_output = any(bus in node.inputs for node in energy_system.nodes if hasattr(node, 'inputs'))
            
            if not has_input and not has_output:
                errors.append(f"Bus '{bus.label}' ist isoliert (keine Verbindungen)")
            elif not has_input:
                errors.append(f"Bus '{bus.label}' hat keine Inputs")
            elif not has_output:
                errors.append(f"Bus '{bus.label}' hat keine Outputs")
        
        # Investment-Parameter prüfen
        for node in energy_system.nodes:
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment = flow.nominal_capacity
                        if hasattr(investment, 'ep_costs') and investment.ep_costs <= 0:
                            errors.append(f"Investment ohne positive Kosten: {node.label}")
        
        is_valid = len(errors) == 0
        return is_valid, errors

def test_system_builder():
    """Testfunktion für den System-Builder."""
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    try:
        from modules.excel_reader import ExcelReader
        
        # Test mit Beispieldatei
        example_file = Path("examples/example_1.xlsx")
        
        if example_file.exists():
            # Excel-Daten einlesen
            settings = {'debug_mode': True}
            reader = ExcelReader(settings)
            excel_data = reader.read_project_file(example_file)
            
            # System aufbauen
            builder = SystemBuilder(settings)
            energy_system = builder.build_energy_system(excel_data)
            
            # Validieren
            is_valid, errors = builder.validate_system(energy_system)
            
            if is_valid:
                print("✅ Test erfolgreich!")
                summary = builder.get_system_summary(energy_system)
                print("System-Zusammenfassung:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ Validierungsfehler:")
                for error in errors:
                    print(f"  - {error}")
                    
        else:
            print(f"❌ Beispieldatei nicht gefunden: {example_file}")
            
    except ImportError as e:
        print(f"❌ Import-Fehler: {e}")
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")


if __name__ == "__main__":
    test_system_builder()
