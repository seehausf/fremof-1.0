"""
Energy System Exporter Module - PRODUKTIONSVERSION

Dieses Modul exportiert alle Attribute und Parameter eines aufgebauten Energy Systems
in computer- und menschenlesbare Formate.

Datei: modules/energy_system_exporter.py
Erstellt von: Energy System Export Integration
Version: 1.0
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
            'exporter_version': '1.0',
            'oemof_version': solph.__version__ if hasattr(solph, '__version__') else 'unknown'
        }
    
    def export_system(self, 
                     energy_system: solph.EnergySystem,
                     excel_data: Dict[str, Any],
                     output_dir: Path,
                     formats: List[str] = ['json', 'yaml', 'txt']) -> Dict[str, Path]:
        """
        Exportiert das Energy System in die gewünschten Formate.
        
        Args:
            energy_system: Das aufgebaute oemof.solph EnergySystem
            excel_data: Original Excel-Daten
            output_dir: Ausgabe-Verzeichnis
            formats: Liste der gewünschten Export-Formate
            
        Returns:
            Dictionary mit Format -> Dateipfad Zuordnung
        """
        self.logger.info("📤 Exportiere Energy System...")
        
        # System-Daten sammeln
        system_export = self._collect_system_data(energy_system, excel_data)
        
        # Export-Verzeichnis erstellen
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp für Dateinamen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"energy_system_export_{timestamp}"
        
        exported_files = {}
        
        # JSON Export
        if 'json' in formats:
            json_file = output_dir / f"{base_filename}.json"
            self._export_json(system_export, json_file)
            exported_files['json'] = json_file
            
        # YAML Export
        if 'yaml' in formats:
            yaml_file = output_dir / f"{base_filename}.yaml"
            self._export_yaml(system_export, yaml_file)
            exported_files['yaml'] = yaml_file
            
        # TXT Export (menschenlesbar)
        if 'txt' in formats:
            txt_file = output_dir / f"{base_filename}.txt"
            self._export_txt(system_export, txt_file)
            exported_files['txt'] = txt_file
        
        self.logger.info(f"✅ Export abgeschlossen. {len(exported_files)} Dateien erstellt.")
        for fmt, filepath in exported_files.items():
            self.logger.info(f"   📄 {fmt.upper()}: {filepath.name}")
        
        return exported_files
    
    def _collect_system_data(self, 
                           energy_system: solph.EnergySystem, 
                           excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sammelt alle relevanten System-Daten für den Export.
        
        Args:
            energy_system: Das oemof.solph EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit allen Export-Daten
        """
        system_export = {
            'metadata': self.export_metadata.copy(),
            'system_info': self._get_system_info(energy_system),
            'timeindex': self._get_timeindex_info(energy_system),
            'components': self._get_components_info(energy_system),
            'original_excel_data': self._get_excel_summary(excel_data)
        }
        
        return system_export
    
    def _get_system_info(self, energy_system: solph.EnergySystem) -> Dict[str, Any]:
        """Sammelt allgemeine System-Informationen."""
        nodes = energy_system.nodes
        
        # Komponenten nach Typen klassifizieren
        buses = [n for n in nodes if isinstance(n, solph.buses.Bus)]
        sources = [n for n in nodes if isinstance(n, solph.components.Source)]
        sinks = [n for n in nodes if isinstance(n, solph.components.Sink)]
        converters = [n for n in nodes if isinstance(n, solph.components.Converter)]
        
        # Investment-Komponenten zählen - VERBESSERT
        investment_flows = 0
        investment_components = []
        
        for node in nodes:
            node_has_investment = False
            
            # Input-Flows prüfen
            if hasattr(node, 'inputs'):
                for connected_node, flow in node.inputs.items():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_flows += 1
                        node_has_investment = True
            
            # Output-Flows prüfen
            if hasattr(node, 'outputs'):
                for connected_node, flow in node.outputs.items():
                    if isinstance(getattr(flow, 'nominal_capacity', None), Investment):
                        investment_flows += 1
                        node_has_investment = True
            
            # Komponente zur Investment-Liste hinzufügen
            if node_has_investment:
                investment_components.append(str(node.label))
        
        return {
            'total_nodes': len(nodes),
            'buses_count': len(buses),
            'sources_count': len(sources),
            'sinks_count': len(sinks),
            'converters_count': len(converters),
            'investment_flows_count': investment_flows,
            'investment_components': investment_components,  # NEU: Liste der Investment-Komponenten
            'has_nonconvex': self._has_nonconvex_flows(nodes)
        }
    
    def _get_timeindex_info(self, energy_system: solph.EnergySystem) -> Dict[str, Any]:
        """Sammelt Zeitindex-Informationen."""
        timeindex = energy_system.timeindex
        
        return {
            'start_time': timeindex[0].isoformat(),
            'end_time': timeindex[-1].isoformat(),
            'timesteps': len(timeindex),
            'frequency': pd.infer_freq(timeindex),
            'duration_hours': len(timeindex),
            'infer_last_interval': getattr(energy_system, 'infer_last_interval', None)
        }
    
    def _get_components_info(self, energy_system: solph.EnergySystem) -> Dict[str, Dict[str, Any]]:
        """Sammelt detaillierte Informationen zu allen Komponenten."""
        components = {}
        
        for node in energy_system.nodes:
            component_info = {
                'type': type(node).__name__,
                'module': type(node).__module__,
                'attributes': self._get_node_attributes(node),
                'flows': self._get_node_flows(node)
            }
            
            components[str(node.label)] = component_info
        
        return components
    
    def _get_node_attributes(self, node: Any) -> Dict[str, Any]:
        """Extrahiert alle relevanten Attribute eines Nodes."""
        attributes = {'label': str(node.label)}
        
        # Basis-Attribute je nach Node-Typ
        if isinstance(node, solph.buses.Bus):
            attributes['component_type'] = 'Bus'
            
        elif isinstance(node, solph.components.Source):
            attributes['component_type'] = 'Source'
            
        elif isinstance(node, solph.components.Sink):
            attributes['component_type'] = 'Sink'
            
        elif isinstance(node, solph.components.Converter):
            attributes['component_type'] = 'Converter'
            # Conversion factors
            if hasattr(node, 'conversion_factors'):
                attributes['conversion_factors'] = {
                    str(k.label): v for k, v in node.conversion_factors.items()
                }
        
        return attributes
    
    def _get_node_flows(self, node: Any) -> Dict[str, Dict[str, Any]]:
        """Extrahiert alle Flow-Informationen eines Nodes."""
        flows = {}
        
        # Input-Flows
        if hasattr(node, 'inputs'):
            for connected_node, flow in node.inputs.items():
                flow_key = f"input_from_{connected_node.label}"
                flows[flow_key] = self._get_flow_properties(flow)
        
        # Output-Flows
        if hasattr(node, 'outputs'):
            for connected_node, flow in node.outputs.items():
                flow_key = f"output_to_{connected_node.label}"
                flows[flow_key] = self._get_flow_properties(flow)
        
        return flows
    
    def _get_flow_properties(self, flow: Any) -> Dict[str, Any]:
        """Extrahiert alle Eigenschaften eines Flows."""
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
                        # YAML-Fix: None-Werte in Listen durch 0 ersetzen oder Liste kürzen
                        if any(v is None for v in value_list):
                            # Option 1: None durch "null" String ersetzen für bessere Lesbarkeit
                            value_list = ["null" if v is None else v for v in value_list]
                        properties[attr] = value_list
                    else:
                        properties[attr] = value
        
        # Nominal Capacity (kann Investment-Objekt sein)
        if hasattr(flow, 'nominal_capacity'):
            nominal_cap = flow.nominal_capacity
            if isinstance(nominal_cap, Investment):
                properties['investment'] = self._get_investment_properties(nominal_cap)
            elif nominal_cap is not None:
                properties['nominal_capacity'] = nominal_cap
        
        # NonConvex-Parameter
        if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
            properties['nonconvex'] = self._get_nonconvex_properties(flow.nonconvex)
        
        return properties
    
    def _get_investment_properties(self, investment: Investment) -> Dict[str, Any]:
        """Extrahiert Investment-Parameter."""
        inv_props = {'is_investment': True}
        
        # Investment-Attribute
        inv_attrs = [
            'existing', 'maximum', 'minimum', 'ep_costs', 'offset', 
            'nonconvex', 'lifetime', 'interest_rate', 'age'
        ]
        
        for attr in inv_attrs:
            if hasattr(investment, attr):
                value = getattr(investment, attr)
                if value is not None:
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
    
    def _get_excel_summary(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Erstellt eine Zusammenfassung der ursprünglichen Excel-Daten."""
        summary = {}
        
        # Verfügbare Sheets
        for sheet_name, sheet_data in excel_data.items():
            if isinstance(sheet_data, pd.DataFrame):
                summary[sheet_name] = {
                    'rows': len(sheet_data),
                    'columns': list(sheet_data.columns),
                    'data_types': {k: str(v) for k, v in sheet_data.dtypes.to_dict().items()}
                }
        
        return summary
    
    def _has_nonconvex_flows(self, nodes: List[Any]) -> bool:
        """Prüft ob NonConvex-Flows im System vorhanden sind."""
        for node in nodes:
            if hasattr(node, 'inputs'):
                for flow in node.inputs.values():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        return True
            if hasattr(node, 'outputs'):
                for flow in node.outputs.values():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        return True
        return False
    
    def _export_json(self, data: Dict[str, Any], filepath: Path):
        """Exportiert Daten als JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        self.logger.debug(f"JSON Export: {filepath}")
    
    def _export_yaml(self, data: Dict[str, Any], filepath: Path):
        """Exportiert Daten als YAML - mit Error Handling."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, 
                             default=self._yaml_representer)
            self.logger.debug(f"YAML Export: {filepath}")
        except Exception as e:
            self.logger.warning(f"YAML Export fehlgeschlagen: {e}")
            # Fallback: Vereinfachte YAML ohne problematische Werte
            try:
                simplified_data = self._simplify_for_yaml(data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(simplified_data, f, default_flow_style=False, 
                                 allow_unicode=True)
                self.logger.info(f"YAML Export (vereinfacht): {filepath}")
            except Exception as e2:
                self.logger.error(f"Auch vereinfachter YAML Export fehlgeschlagen: {e2}")
                # Als letzter Ausweg: YAML-Datei mit Fehlermeldung erstellen
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# YAML Export fehlgeschlagen\n")
                    f.write(f"# Fehler: {e}\n")
                    f.write(f"# Vereinfachter Export ebenfalls fehlgeschlagen: {e2}\n")
                    f.write(f"# Verwenden Sie stattdessen die JSON- oder TXT-Datei\n")
    
    def _yaml_representer(self, data):
        """Custom YAML Representer für problematische Datentypen."""
        if data is None:
            return "null"
        return str(data)
    
    def _simplify_for_yaml(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Vereinfacht Daten für YAML-Export."""
        if isinstance(data, dict):
            return {k: self._simplify_for_yaml(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Listen mit None-Werten vereinfachen
            if any(v is None for v in data):
                return f"[Liste mit {len(data)} Werten, davon {data.count(None)} None-Werte]"
            return [self._simplify_for_yaml(v) for v in data]
        elif data is None:
            return "null"
        else:
            return data
    
    def _export_txt(self, data: Dict[str, Any], filepath: Path):
        """Exportiert Daten als strukturierte Textdatei."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ENERGY SYSTEM EXPORT - MENSCHENLESBAR\n")
            f.write("=" * 80 + "\n\n")
            
            # Metadaten
            f.write("📋 EXPORT-INFORMATIONEN\n")
            f.write("-" * 40 + "\n")
            for key, value in data['metadata'].items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # System-Übersicht
            f.write("🏗️  SYSTEM-ÜBERSICHT\n")
            f.write("-" * 40 + "\n")
            system_info = data['system_info']
            f.write(f"Gesamt-Knoten: {system_info['total_nodes']}\n")
            f.write(f"Buses: {system_info['buses_count']}\n")
            f.write(f"Sources: {system_info['sources_count']}\n")
            f.write(f"Sinks: {system_info['sinks_count']}\n")
            f.write(f"Converter: {system_info['converters_count']}\n")
            f.write(f"Investment-Flows: {system_info['investment_flows_count']}\n")
            
            # Investment-Komponenten auflisten falls vorhanden
            if system_info.get('investment_components'):
                f.write(f"Investment-Komponenten: {', '.join(system_info['investment_components'])}\n")
            
            f.write(f"NonConvex-Flows: {'Ja' if system_info['has_nonconvex'] else 'Nein'}\n")
            f.write("\n")
            
            # Zeitindex
            f.write("⏰ ZEITINDEX\n")
            f.write("-" * 40 + "\n")
            timeindex = data['timeindex']
            f.write(f"Start: {timeindex['start_time']}\n")
            f.write(f"Ende: {timeindex['end_time']}\n")
            f.write(f"Zeitschritte: {timeindex['timesteps']}\n")
            f.write(f"Frequenz: {timeindex['frequency']}\n")
            f.write("\n")
            
            # Komponenten-Details
            f.write("🔧 KOMPONENTEN-DETAILS\n")
            f.write("-" * 40 + "\n")
            components = data['components']
            
            for comp_name, comp_data in components.items():
                f.write(f"\n{comp_data['type']}: {comp_name}\n")
                f.write("  " + "-" * 35 + "\n")
                
                # Attribute
                if comp_data['attributes']:
                    f.write("  Attribute:\n")
                    for attr, value in comp_data['attributes'].items():
                        if attr != 'label':  # Label schon im Header
                            f.write(f"    {attr}: {value}\n")
                
                # Flows
                if comp_data['flows']:
                    f.write("  Flows:\n")
                    for flow_name, flow_props in comp_data['flows'].items():
                        f.write(f"    {flow_name}:\n")
                        for prop, value in flow_props.items():
                            if isinstance(value, dict):
                                f.write(f"      {prop}:\n")
                                for sub_prop, sub_value in value.items():
                                    f.write(f"        {sub_prop}: {sub_value}\n")
                            else:
                                # Lange Listen kürzen
                                if isinstance(value, list) and len(value) > 5:
                                    f.write(f"      {prop}: [Zeitreihe mit {len(value)} Werten]\n")
                                else:
                                    f.write(f"      {prop}: {value}\n")
        
        self.logger.debug(f"TXT Export: {filepath}")


def create_export_module(settings: Dict[str, Any]) -> EnergySystemExporter:
    """
    Factory-Funktion zum Erstellen des Export-Moduls.
    
    Args:
        settings: Dictionary mit Konfigurationseinstellungen
        
    Returns:
        EnergySystemExporter Instanz
    """
    return EnergySystemExporter(settings)


# Test-Funktion
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
