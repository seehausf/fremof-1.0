#!/usr/bin/env python3
"""
Energy System Exporter Module - VOLLSTÄNDIG KORRIGIERTE VERSION

Dieses Modul exportiert alle Attribute und Parameter eines aufgebauten Energy Systems
in computer- und menschenlesbare Formate.

KORRIGIERT: Investment-Parameter werden jetzt korrekt aus flow.investment extrahiert
statt aus flow.nominal_capacity (basierend auf echter oemof.solph Struktur).

Datei: modules/energy_system_exporter.py
Erstellt von: Energy System Export Integration
Version: 1.1 (Investment-Korrektur)
Datum: Juli 2025
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import oemof.solph as solph
from oemof.solph import Investment, NonConvex
import logging


class EnergySystemExporter:
    """
    Exportiert Energy System Attribute und Parameter in verschiedene Formate.
    
    Unterstützte Formate:
    - JSON (computer-lesbar)
    - YAML (computer- und menschenlesbar)
    - TXT (menschenlesbar, strukturiert)
    
    KORRIGIERT: Korrekte Investment-Parameter-Erkennung via flow.investment
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Energy System Exporter.
        
        Args:
            settings: Dictionary mit Konfigurationseinstellungen
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Export-Metadaten
        self.export_metadata = {
            'export_timestamp': datetime.now().isoformat(),
            'exporter_version': '1.1',
            'oemof_version': solph.__version__ if hasattr(solph, '__version__') else 'unknown',
            'investment_detection': 'corrected_flow_investment'
        }
    
    def export_system(self, 
                     energy_system: solph.EnergySystem,
                     excel_data: Dict[str, Any],
                     output_dir: Path,
                     formats: List[str] = ['json', 'yaml', 'txt']) -> Dict[str, Path]:
        """
        Exportiert das Energy System in die gewünschten Formate.
        
        Args:
            energy_system: Das zu exportierende EnergySystem
            excel_data: Original Excel-Daten für Vergleiche
            output_dir: Zielverzeichnis für Export-Dateien
            formats: Liste der gewünschten Export-Formate
            
        Returns:
            Dictionary mit Format -> Dateipfad Mapping
        """
        self.logger.info("📤 Starte Energy System Export...")
        
        # Output-Verzeichnis erstellen
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Vollständige System-Daten sammeln
        system_data = self._collect_system_data(energy_system, excel_data)
        
        # Export-Dateien erstellen
        export_files = {}
        
        for fmt in formats:
            try:
                if fmt.lower() == 'json':
                    filepath = self._export_json(system_data, output_dir)
                    export_files['json'] = filepath
                    
                elif fmt.lower() == 'yaml':
                    filepath = self._export_yaml(system_data, output_dir)
                    export_files['yaml'] = filepath
                    
                elif fmt.lower() == 'txt':
                    filepath = self._export_txt(system_data, output_dir)
                    export_files['txt'] = filepath
                    
                else:
                    self.logger.warning(f"⚠️  Unbekanntes Export-Format: {fmt}")
                    
            except Exception as e:
                self.logger.error(f"❌ Fehler beim {fmt.upper()}-Export: {e}")
                if self.settings.get('debug_mode', False):
                    import traceback
                    traceback.print_exc()
        
        self.logger.info(f"✅ System-Export abgeschlossen: {len(export_files)} Dateien erstellt")
        
        # Optional: Debug-Analyse erstellen
        if self.settings.get('debug_mode', False):
            debug_file = self._create_debug_analysis(energy_system, excel_data, output_dir)
            export_files['debug'] = debug_file
        
        return export_files
    
    def _collect_system_data(self, energy_system: solph.EnergySystem, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sammelt alle System-Daten für den Export."""
        self.logger.info("🔍 Sammle System-Daten...")
        
        return {
            'metadata': self.export_metadata,
            'system_statistics': self._get_system_statistics(energy_system),
            'timeindex': self._export_timeindex(energy_system),
            'components': self._export_all_components(energy_system),
            'flows': self._export_all_flows(energy_system),
            'investment_definitions': self._export_investment_definitions(energy_system),
            'nonconvex_definitions': self._export_nonconvex_definitions(energy_system),
            'excel_summary': self._get_excel_summary(excel_data) if excel_data else {}
        }
    
    def _get_system_statistics(self, energy_system: Any) -> Dict[str, Any]:
        """Erstellt Systemstatistiken - KORRIGIERT für Investment-Erkennung."""
        nodes = energy_system.nodes
        
        # Komponenten nach Typen klassifizieren
        buses = [n for n in nodes if isinstance(n, solph.buses.Bus)]
        sources = [n for n in nodes if isinstance(n, solph.components.Source)]
        sinks = [n for n in nodes if isinstance(n, solph.components.Sink)]
        converters = [n for n in nodes if isinstance(n, solph.components.Converter)]
        
        # KORRIGIERT: Investment-Komponenten detailliert analysieren
        investment_flows = 0
        investment_components = []
        investment_details = {}
        
        for node in nodes:
            node_label = str(node.label)
            node_investments = []
            
            # Input-Flows prüfen - KORRIGIERT: flow.investment statt flow.nominal_capacity
            if hasattr(node, 'inputs'):
                for connected_node, flow in node.inputs.items():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_flows += 1
                        flow_info = {
                            'direction': 'input',
                            'connected_to': str(connected_node.label),
                            'investment_details': self._get_investment_properties(flow.investment)
                        }
                        node_investments.append(flow_info)
            
            # Output-Flows prüfen - KORRIGIERT: flow.investment statt flow.nominal_capacity  
            if hasattr(node, 'outputs'):
                for connected_node, flow in node.outputs.items():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_flows += 1
                        flow_info = {
                            'direction': 'output',
                            'connected_to': str(connected_node.label),
                            'investment_details': self._get_investment_properties(flow.investment)
                        }
                        node_investments.append(flow_info)
            
            # Node zu Investment-Komponenten hinzufügen falls Investments vorhanden
            if node_investments:
                investment_components.append(node_label)
                investment_details[node_label] = {
                    'component_type': type(node).__name__,
                    'flows': node_investments
                }
        
        # NonConvex-Flows zählen
        nonconvex_flows = 0
        for node in nodes:
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_flows += 1
            if hasattr(node, 'inputs'):
                for flow in node.inputs.values():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_flows += 1
        
        # Kosten-relevante Flows zählen
        cost_relevant_flows = 0
        for node in nodes:
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if (hasattr(flow, 'variable_costs') and flow.variable_costs is not None) or \
                       (hasattr(flow, 'investment') and flow.investment is not None):
                        cost_relevant_flows += 1
        
        return {
            'total_nodes': len(nodes),
            'buses': len(buses),
            'sources': len(sources),
            'sinks': len(sinks),
            'converters': len(converters),
            'total_flows': sum(len(getattr(n, 'outputs', {})) for n in nodes),
            'investment_flows': investment_flows,
            'investment_components': investment_components,
            'investment_details': investment_details,
            'nonconvex_flows': nonconvex_flows,
            'cost_relevant_flows': cost_relevant_flows,
            'has_investments': investment_flows > 0,
            'has_nonconvex': nonconvex_flows > 0
        }
    
    def _export_timeindex(self, energy_system: Any) -> Dict[str, Any]:
        """Exportiert Zeitindex-Informationen."""
        if not hasattr(energy_system, 'timeindex'):
            return {}
        
        timeindex = energy_system.timeindex
        
        return {
            'start_time': timeindex[0].isoformat() if len(timeindex) > 0 else None,
            'end_time': timeindex[-1].isoformat() if len(timeindex) > 0 else None,
            'timesteps': len(timeindex),
            'frequency': pd.infer_freq(timeindex),
            'first_timestamp': timeindex[0].isoformat() if len(timeindex) > 0 else None,
            'last_timestamp': timeindex[-1].isoformat() if len(timeindex) > 0 else None,
            'sample_timestamps': [ts.isoformat() for ts in timeindex[:5]] if len(timeindex) > 5 else [ts.isoformat() for ts in timeindex]
        }
    
    def _export_all_components(self, energy_system: Any) -> Dict[str, Dict[str, Any]]:
        """Exportiert alle Komponenten mit ihren Eigenschaften."""
        components = {}
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            component_info = {
                'type': type(node).__name__,
                'module': type(node).__module__,
                'attributes': self._get_component_attributes(node),
                'inputs': {},
                'outputs': {}
            }
            
            # Input-Flows
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    flow_key = f"from_{input_node.label}"
                    component_info['inputs'][flow_key] = self._get_flow_properties(flow)
            
            # Output-Flows
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    flow_key = f"to_{output_node.label}"
                    component_info['outputs'][flow_key] = self._get_flow_properties(flow)
            
            components[node_label] = component_info
        
        return components
    
    def _get_component_attributes(self, node: Any) -> Dict[str, Any]:
        """Extrahiert alle relevanten Komponenten-Attribute."""
        attributes = {}
        
        # Standard-Attribute für alle Komponenten
        standard_attrs = ['label', 'constraint_group', 'custom_properties']
        
        # Bus-spezifische Attribute
        if hasattr(node, 'balanced'):
            standard_attrs.append('balanced')
        
        for attr in standard_attrs:
            if hasattr(node, attr):
                value = getattr(node, attr)
                if value is not None:
                    attributes[attr] = value
        
        return attributes
    
    def _get_flow_properties(self, flow) -> Dict[str, Any]:
        """Extrahiert alle Flow-Eigenschaften - KORRIGIERT für oemof.solph Investment-Struktur."""
        properties = {}
        
        # Standard Flow-Attribute
        flow_attrs = [
            'variable_costs', 'min', 'max', 'fix', 'summed_max', 'summed_min',
            'positive_gradient_limit', 'negative_gradient_limit'
        ]
        
        for attr in flow_attrs:
            if hasattr(flow, attr):
                value = getattr(flow, attr)
                if value is not None:
                    # Pandas Series/Arrays in Listen umwandeln - YAML-sicher
                    if hasattr(value, 'tolist'):
                        value_list = value.tolist()
                        # YAML-Fix: None-Werte in Listen durch "null" String ersetzen
                        if any(v is None for v in value_list):
                            value_list = ["null" if v is None else v for v in value_list]
                        properties[attr] = value_list
                    else:
                        properties[attr] = value
        
        # KORRIGIERT: Nominal Capacity (einfacher Float/Wert)
        if hasattr(flow, 'nominal_capacity') and flow.nominal_capacity is not None:
            properties['nominal_capacity'] = flow.nominal_capacity
            properties['has_fixed_capacity'] = True
        else:
            properties['has_fixed_capacity'] = False
        
        # KORRIGIERT: Investment-Parameter (separates Attribut!)
        if hasattr(flow, 'investment') and flow.investment is not None:
            properties['investment'] = self._get_investment_properties(flow.investment)
            properties['is_investment_flow'] = True
        else:
            properties['is_investment_flow'] = False
        
        # NonConvex-Parameter
        if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
            properties['nonconvex'] = self._get_nonconvex_properties(flow.nonconvex)
            properties['has_nonconvex'] = True
        else:
            properties['has_nonconvex'] = False
        
        return properties
    
    def _get_investment_properties(self, investment: Investment) -> Dict[str, Any]:
        """Extrahiert Investment-Parameter - KORRIGIERT für echte oemof.solph Struktur."""
        inv_props = {'is_investment': True}
        
        # Investment-Attribute (basierend auf echten oemof.solph Investment-Objekten)
        inv_attrs = [
            'existing', 'maximum', 'minimum', 'ep_costs', 'offset', 
            'nonconvex', 'lifetime', 'interest_rate', 'age', 'fixed_costs',
            'overall_maximum', 'overall_minimum'
        ]
        
        for attr in inv_attrs:
            if hasattr(investment, attr):
                value = getattr(investment, attr)
                if value is not None:
                    # Listen/Arrays zu Python-Listen konvertieren für JSON/YAML-Kompatibilität
                    if hasattr(value, 'tolist'):
                        try:
                            value_list = value.tolist()
                            # Für bessere Lesbarkeit: Falls alle Werte gleich sind, nur einen Wert speichern
                            if len(set(value_list)) == 1:
                                inv_props[attr] = value_list[0]
                                inv_props[f'{attr}_is_constant'] = True
                            else:
                                inv_props[attr] = value_list
                                inv_props[f'{attr}_is_constant'] = False
                        except:
                            inv_props[attr] = str(value)
                    else:
                        inv_props[attr] = value
        
        return inv_props
    
    def _get_nonconvex_properties(self, nonconvex: NonConvex) -> Dict[str, Any]:
        """Extrahiert NonConvex-Parameter."""
        nonconvex_props = {'is_nonconvex': True}
        
        # NonConvex-Attribute
        nonconvex_attrs = [
            'minimum_uptime', 'minimum_downtime', 'startup_costs', 'shutdown_costs',
            'maximum_startups', 'maximum_shutdowns', 'initial_status'
        ]
        
        for attr in nonconvex_attrs:
            if hasattr(nonconvex, attr):
                value = getattr(nonconvex, attr)
                if value is not None:
                    nonconvex_props[attr] = value
        
        return nonconvex_props
    
    def _export_all_flows(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle Flows als Liste."""
        flows = []
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Output-Flows
            if hasattr(node, 'outputs'):
                for connected_node, flow in node.outputs.items():
                    flow_data = {
                        'id': f"{node_label}_to_{connected_node.label}",
                        'from': node_label,
                        'to': str(connected_node.label),
                        'direction': 'output',
                        'properties': self._get_flow_properties(flow)
                    }
                    flows.append(flow_data)
        
        return flows
    
    def _export_investment_definitions(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle Investment-Definitionen - KORRIGIERT."""
        investments = []
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Input-Flows prüfen - KORRIGIERT
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_def = {
                            'component': node_label,
                            'flow_direction': 'input',
                            'connection': f"{input_node.label} → {node_label}",
                            'investment_parameters': self._get_investment_properties(flow.investment)
                        }
                        investments.append(investment_def)
            
            # Output-Flows prüfen - KORRIGIERT
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'investment') and flow.investment is not None:
                        investment_def = {
                            'component': node_label,
                            'flow_direction': 'output',
                            'connection': f"{node_label} → {output_node.label}",
                            'investment_parameters': self._get_investment_properties(flow.investment)
                        }
                        investments.append(investment_def)
        
        return investments
    
    def _export_nonconvex_definitions(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle NonConvex-Definitionen."""
        nonconvex_flows = []
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Output-Flows prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_def = {
                            'component': node_label,
                            'flow_direction': 'output',
                            'connection': f"{node_label} → {output_node.label}",
                            'nonconvex_parameters': self._get_nonconvex_properties(flow.nonconvex)
                        }
                        nonconvex_flows.append(nonconvex_def)
        
        return nonconvex_flows
    
    def _get_excel_summary(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Erstellt eine Zusammenfassung der ursprünglichen Excel-Daten."""
        summary = {'available_sheets': list(excel_data.keys())}
        
        # Komponenten-Counts
        for sheet_name in ['buses', 'sources', 'sinks', 'simple_transformers']:
            if sheet_name in excel_data and hasattr(excel_data[sheet_name], '__len__'):
                summary[f'{sheet_name}_count'] = len(excel_data[sheet_name])
        
        # Zeitreihen-Info
        if 'timeseries' in excel_data and hasattr(excel_data['timeseries'], '__len__'):
            summary['timeseries_count'] = len(excel_data['timeseries'])
        
        # Settings-Info
        if 'settings' in excel_data and hasattr(excel_data['settings'], '__len__'):
            summary['settings_count'] = len(excel_data['settings'])
        
        return summary
    
    def _export_json(self, data: Dict[str, Any], output_dir: Path) -> Path:
        """Exportiert Daten als JSON."""
        filepath = output_dir / "energy_system_export.json"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"JSON Export Fehler: {e}")
            # Fallback: Vereinfachte Version ohne problematische Werte
            simplified_data = self._simplify_for_json(data)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(simplified_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.debug(f"JSON Export: {filepath}")
        return filepath
    
    def _create_debug_analysis(self, energy_system: Any, excel_data: Dict[str, Any], output_dir: Path) -> Path:
        """Erstellt detaillierte Debug-Analyse - KORRIGIERT für Investment-Struktur."""
        debug_info = {
            'export_metadata': self.export_metadata.copy(),
            'analysis_focus': 'Investment-Parameter Validierung (KORRIGIERT)',
            'excel_analysis': {},
            'system_analysis': {},
            'investment_analysis': {},
            'investment_objects_found': [],
            'discrepancies': []
        }
        
        # Excel-Daten analysieren
        if 'sources' in excel_data and not excel_data['sources'].empty:
            debug_info['excel_analysis']['sources'] = []
            for _, row in excel_data['sources'].iterrows():
                source_info = {
                    'label': row.get('label', 'unknown'),
                    'investment_flag': row.get('investment_flag', 0),
                    'is_investment_flag': bool(row.get('investment_flag', 0) == 1),
                    'ep_costs': row.get('ep_costs', None),
                    'existing': row.get('existing', None),
                    'maximum': row.get('maximum', None),
                    'raw_row': dict(row)
                }
                debug_info['excel_analysis']['sources'].append(source_info)
        
        # KORRIGIERT: System-Objekte analysieren mit flow.investment
        debug_info['system_analysis']['components'] = {}
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            node_info = {
                'type': type(node).__name__,
                'flows': {}
            }
            
            # Output-Flows analysieren - KORRIGIERT
            if hasattr(node, 'outputs'):
                for connected_node, flow in node.outputs.items():
                    flow_info = {
                        'to': str(connected_node.label),
                        'has_nominal_capacity': hasattr(flow, 'nominal_capacity'),
                        'nominal_capacity_value': getattr(flow, 'nominal_capacity', None),
                        'has_investment': hasattr(flow, 'investment'),
                        'investment_object': getattr(flow, 'investment', None),
                        'is_investment_flow': hasattr(flow, 'investment') and flow.investment is not None,
                        'flow_attributes': {}
                    }
                    
                    # Investment-spezifische Analyse
                    if flow_info['is_investment_flow']:
                        investment_obj = flow.investment
                        flow_id = f"{node_label}_output_to_{connected_node.label}"
                        debug_info['investment_objects_found'].append(flow_id)
                        
                        # Investment-Parameter sammeln
                        investment_analysis = {
                            'has_ep_costs': hasattr(investment_obj, 'ep_costs'),
                            'ep_costs_value': getattr(investment_obj, 'ep_costs', None),
                            'has_existing': hasattr(investment_obj, 'existing'),
                            'existing_value': getattr(investment_obj, 'existing', None),
                            'has_maximum': hasattr(investment_obj, 'maximum'),
                            'maximum_value': getattr(investment_obj, 'maximum', None),
                            'object_type': str(type(investment_obj)),
                            'all_attributes': [attr for attr in dir(investment_obj) if not attr.startswith('_')]
                        }
                        debug_info['investment_analysis'][flow_id] = investment_analysis
                    
                    node_info['flows'][f'output_to_{connected_node.label}'] = flow_info
            
            debug_info['system_analysis']['components'][node_label] = node_info
        
        # Debug-Datei speichern
        debug_filepath = output_dir / "energy_system_debug_analysis.json"
        with open(debug_filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"🔍 Debug-Analyse erstellt: {debug_filepath}")
        return debug_filepath


def create_export_module(settings: Dict[str, Any]) -> EnergySystemExporter:
    """
    Factory-Funktion zum Erstellen des Export-Moduls.
    
    Args:
        settings: Dictionary mit Konfigurationseinstellungen
        
    Returns:
        EnergySystemExporter Instanz
    """
    return EnergySystemExporter(settings)


def test_export_module():
    """Test-Funktion für das Export-Modul."""
    print("🧪 Teste Energy System Export-Modul...")
    
    # Dummy-Settings
    settings = {'debug_mode': True}
    
    # Export-Modul erstellen
    exporter = create_export_module(settings)
    
    print("✅ Export-Modul erfolgreich erstellt!")
    print(f"   Version: {exporter.export_metadata['exporter_version']}")
    print(f"   Timestamp: {exporter.export_metadata['export_timestamp']}")


if __name__ == "__main__":
    test_export_module()
    
    def _export_yaml(self, data: Dict[str, Any], output_dir: Path) -> Path:
        """Exportiert Daten als YAML mit Fallback-Strategie."""
        filepath = output_dir / "energy_system_export.yaml"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            self.logger.warning(f"YAML Export Fehler: {e} - verwende Fallback-Strategie")
            # Fallback: Vereinfachte YAML-Version
            simplified_data = self._simplify_for_yaml(data)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(simplified_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            except Exception as e2:
                self.logger.error(f"YAML Fallback fehlgeschlagen: {e2} - erstelle Text-Version")
                # Letzter Fallback: Als Text
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("# YAML Export fehlgeschlagen - Text-Fallback\n")
                    f.write(f"# Fehler: {e}\n\n")
                    f.write(str(data))
        
        self.logger.debug(f"YAML Export: {filepath}")
        return filepath
    
    def _export_txt(self, data: Dict[str, Any], output_dir: Path) -> Path:
        """Exportiert Daten als strukturierte Textdatei."""
        filepath = output_dir / "energy_system_export.txt"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("OEMOF.SOLPH ENERGY SYSTEM EXPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Metadaten
            f.write("📋 METADATEN\n")
            f.write("-" * 40 + "\n")
            metadata = data['metadata']
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # System-Statistiken
            f.write("📊 SYSTEM-STATISTIKEN\n")
            f.write("-" * 40 + "\n")
            stats = data['system_statistics']
            for key, value in stats.items():
                if key not in ['investment_details']:  # Details separat
                    if isinstance(value, list):
                        f.write(f"{key}: {', '.join(map(str, value))}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Investment-Details
            if stats.get('has_investments', False):
                f.write("💰 INVESTMENT-DETAILS\n")
                f.write("-" * 40 + "\n")
                inv_details = stats.get('investment_details', {})
                for comp_name, comp_data in inv_details.items():
                    f.write(f"\n{comp_data['component_type']}: {comp_name}\n")
                    for flow_info in comp_data['flows']:
                        direction = flow_info['direction']
                        connected_to = flow_info['connected_to']
                        inv_details = flow_info['investment_details']
                        f.write(f"  {direction} → {connected_to}:\n")
                        
                        # Wichtigste Investment-Parameter
                        if 'existing' in inv_details:
                            f.write(f"    Bestehend: {inv_details['existing']} kW\n")
                        if 'maximum' in inv_details:
                            f.write(f"    Maximum: {inv_details['maximum']} kW\n")
                        if 'ep_costs' in inv_details:
                            f.write(f"    EP-Costs: {inv_details['ep_costs']} €/kW/a\n")
                f.write("\n")
            
            # Zeitindex
            f.write("⏰ ZEITINDEX\n")
            f.write("-" * 40 + "\n")
            timeindex = data['timeindex']
            f.write(f"Start: {timeindex.get('start_time', 'N/A')}\n")
            f.write(f"Ende: {timeindex.get('end_time', 'N/A')}\n")
            f.write(f"Zeitschritte: {timeindex.get('timesteps', 'N/A')}\n")
            f.write(f"Frequenz: {timeindex.get('frequency', 'N/A')}\n")
            f.write("\n")
            
            # Komponenten-Übersicht
            f.write("🔧 KOMPONENTEN-ÜBERSICHT\n")
            f.write("-" * 40 + "\n")
            components = data['components']
            
            for comp_name, comp_data in components.items():
                f.write(f"\n{comp_data['type']}: {comp_name}\n")
                
                # Investment-Flows hervorheben
                has_investments = False
                for direction in ['inputs', 'outputs']:
                    for flow_name, flow_props in comp_data.get(direction, {}).items():
                        if flow_props.get('is_investment_flow', False):
                            has_investments = True
                            break
                
                if has_investments:
                    f.write("  💰 INVESTMENT-KOMPONENTE\n")
                
                # Wichtigste Eigenschaften
                if comp_data.get('inputs'):
                    f.write(f"  Inputs: {len(comp_data['inputs'])}\n")
                if comp_data.get('outputs'):
                    f.write(f"  Outputs: {len(comp_data['outputs'])}\n")
        
        self.logger.debug(f"TXT Export: {filepath}")
        return filepath
    
    def _simplify_for_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Vereinfacht Daten für JSON-Export."""
        import copy
        simplified = copy.deepcopy(data)
        
        # Problematische Werte ersetzen
        def clean_dict(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, (list, tuple)):
                        try:
                            # Teste ob Liste JSON-serialisierbar ist
                            json.dumps(value)
                        except:
                            d[key] = f"[Liste mit {len(value)} Elementen - nicht JSON-serialisierbar]"
                    elif isinstance(value, dict):
                        clean_dict(value)
                    elif hasattr(value, 'tolist'):
                        try:
                            d[key] = value.tolist()
                        except:
                            d[key] = str(value)
            return d
        
        return clean_dict(simplified)
    
    def _simplify_for_yaml(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Vereinfacht Daten für YAML-Export."""
        import copy
        simplified = copy.deepcopy(data)
        
        # Problematische Werte für YAML ersetzen
        def clean_for_yaml(obj):
            if isinstance(obj, dict):
                return {k: clean_for_yaml(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                # Problematische Listen vereinfachen
                if len(obj) > 100:  # Sehr lange Listen kürzen
                    return f"[Zeitreihe mit {len(obj)} Werten]"
                try:
                    # Teste YAML-Serialisierung
                    yaml.dump(obj)
                    return obj
                except:
                    return f"[Liste mit {len(obj)} Elementen]"
            elif hasattr(obj, 'tolist'):
                try:
                    return obj.tolist()
                except:
                    return str(obj)
            else:
                return obj
        
        return clean_for_yaml(simplified)