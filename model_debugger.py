#!/usr/bin/env python3
"""
model_debugger.py - Debugging-Tools für oemof-solph Modelle

Tools für Infeasible Model Debugging:
1. LP-File Export (Solver-Nebenbedingungen)
2. EnergySystem Analyse (Builder-Validation)
3. Investment-Parameter Debugging
4. Flow-Constraint Analyse
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ModelDebugger:
    """Debugging-Tools für oemof-solph Modelle"""
    
    def __init__(self, energy_system, model=None, data=None):
        """
        Initialisiert den Model Debugger
        
        Args:
            energy_system: oemof EnergySystem
            model: oemof Model (optional)
            data: Original Excel-Daten (optional)
        """
        self.energy_system = energy_system
        self.model = model
        self.data = data
        
        # Output-Verzeichnis
        self.debug_dir = Path('debug')
        self.debug_dir.mkdir(exist_ok=True)
        
        # Timestamp für Dateien
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def export_lp_file(self, filename=None):
        """
        Exportiert LP-Datei für Solver-Debugging
        
        Args:
            filename: Name der LP-Datei (optional)
            
        Returns:
            Pfad zur erstellten LP-Datei
        """
        if self.model is None:
            logger.error("Kein Model verfügbar für LP-Export")
            return None
        
        if filename is None:
            filename = f"model_debug_{self.timestamp}.lp"
        
        lp_path = self.debug_dir / filename
        
        try:
            logger.info("Exportiere LP-Datei für Solver-Debugging...")
            
            # LP-Datei schreiben
            self.model.write(str(lp_path), io_options={'symbolic_solver_labels': True})
            
            logger.info(f"LP-Datei erstellt: {lp_path}")
            
            # LP-Datei analysieren
            self._analyze_lp_file(lp_path)
            
            return lp_path
            
        except Exception as e:
            logger.error(f"Fehler beim LP-Export: {e}")
            return None
    
    def _analyze_lp_file(self, lp_path):
        """Analysiert LP-Datei und gibt Statistiken aus"""
        try:
            with open(lp_path, 'r') as f:
                content = f.read()
            
            # Grundlegende Statistiken
            lines = content.split('\n')
            
            # Zähle verschiedene Abschnitte
            obj_lines = [l for l in lines if l.strip().startswith('obj:') or 'Minimize' in l or 'Maximize' in l]
            constraint_lines = [l for l in lines if 'c_e_' in l or 'c_u_' in l or 'c_l_' in l]
            bounds_lines = [l for l in lines if 'Bounds' in l or ' <= ' in l or ' >= ' in l]
            binary_lines = [l for l in lines if 'Binary' in l or 'Binaries' in l]
            
            logger.info(f"LP-Datei Analyse:")
            logger.info(f"  Zeilen gesamt: {len(lines)}")
            logger.info(f"  Objektiv-Funktionen: {len(obj_lines)}")
            logger.info(f"  Constraints: {len(constraint_lines)}")
            logger.info(f"  Bounds: {len(bounds_lines)}")
            logger.info(f"  Binäre Variablen: {len(binary_lines)}")
            
            # Suche nach Investment-Variablen
            investment_vars = [l for l in lines if 'invest' in l.lower()]
            if investment_vars:
                logger.info(f"  Investment-Variablen gefunden: {len(investment_vars)}")
                for var_line in investment_vars[:5]:  # Erste 5 anzeigen
                    logger.info(f"    {var_line.strip()}")
            else:
                logger.warning("  Keine Investment-Variablen gefunden!")
            
        except Exception as e:
            logger.warning(f"LP-Datei-Analyse fehlgeschlagen: {e}")
    
    def analyze_energy_system(self):
        """
        Analysiert das EnergySystem und gibt detaillierte Informationen aus
        
        Returns:
            Dictionary mit EnergySystem-Analyse
        """
        logger.info("Analysiere EnergySystem...")
        
        analysis = {
            'summary': {},
            'nodes': [],
            'flows': [],
            'investments': [],
            'constraints': [],
            'potential_issues': []
        }
        
        # Basis-Informationen
        nodes = list(self.energy_system.nodes)
        analysis['summary'] = {
            'total_nodes': len(nodes),
            'timeindex_length': len(self.energy_system.timeindex) if hasattr(self.energy_system, 'timeindex') else 0,
            'timeframe': f"{self.energy_system.timeindex[0]} - {self.energy_system.timeindex[-1]}" if hasattr(self.energy_system, 'timeindex') and self.energy_system.timeindex else "Unbekannt"
        }
        
        # Node-Analyse
        for node in nodes:
            node_info = self._analyze_node(node)
            analysis['nodes'].append(node_info)
            
            # Flows analysieren
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    flow_info = self._analyze_flow(input_node, node, flow, 'input')
                    analysis['flows'].append(flow_info)
                    
                    # Investment-Flows sammeln
                    if hasattr(flow, 'investment') and flow.investment:
                        analysis['investments'].append(flow_info)
            
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    flow_info = self._analyze_flow(node, output_node, flow, 'output')
                    analysis['flows'].append(flow_info)
                    
                    # Investment-Flows sammeln
                    if hasattr(flow, 'investment') and flow.investment:
                        analysis['investments'].append(flow_info)
        
        # Potential Issues identifizieren
        analysis['potential_issues'] = self._identify_potential_issues(analysis)
        
        # Analyseergebnisse speichern
        self._save_analysis_report(analysis)
        
        return analysis
    
    def _analyze_node(self, node):
        """Analysiert einen einzelnen Node"""
        node_info = {
            'label': getattr(node, 'label', str(node)),
            'type': type(node).__name__,
            'module': type(node).__module__,
            'inputs_count': len(getattr(node, 'inputs', {})),
            'outputs_count': len(getattr(node, 'outputs', {})),
            'attributes': {}
        }
        
        # Wichtige Attribute sammeln
        important_attrs = ['balanced', 'investment', 'existing', 'nominal_capacity']
        for attr in important_attrs:
            if hasattr(node, attr):
                value = getattr(node, attr)
                node_info['attributes'][attr] = str(value)
        
        return node_info
    
    def _analyze_flow(self, from_node, to_node, flow, direction):
        """Analysiert einen einzelnen Flow"""
        flow_info = {
            'from_node': getattr(from_node, 'label', str(from_node)),
            'to_node': getattr(to_node, 'label', str(to_node)),
            'direction': direction,
            'flow_type': type(flow).__name__,
            'attributes': {}
        }
        
        # Flow-Attribute analysieren
        important_flow_attrs = [
            'nominal_capacity', 'max', 'min', 'fix', 'variable_costs',
            'investment', 'existing', 'availability', 'full_load_time_max', 'full_load_time_min'
        ]
        
        for attr in important_flow_attrs:
            if hasattr(flow, attr):
                value = getattr(flow, attr)
                if value is not None:
                    # Für Investment-Objekte
                    if attr == 'investment' and value:
                        flow_info['attributes']['investment'] = self._analyze_investment(value)
                    # Für Listen/Arrays (Zeitreihen)
                    elif isinstance(value, (list, tuple, np.ndarray)):
                        flow_info['attributes'][attr] = f"Zeitreihe (Länge: {len(value)})"
                    else:
                        flow_info['attributes'][attr] = str(value)
        
        return flow_info
    
    def _analyze_investment(self, investment):
        """Analysiert Investment-Objekt"""
        investment_info = {}
        
        investment_attrs = ['maximum', 'minimum', 'existing', 'ep_costs', 'offset']
        for attr in investment_attrs:
            if hasattr(investment, attr):
                value = getattr(investment, attr)
                investment_info[attr] = str(value)
        
        return investment_info
    
    def _identify_potential_issues(self, analysis):
        """Identifiziert potentielle Probleme die zu Infeasibility führen könnten"""
        issues = []
        
        # 1. Keine Investment-Kapazitäten
        if not analysis['investments']:
            issues.append("KRITISCH: Keine Investment-Flows gefunden - möglicherweise keine Erzeugungskapazität")
        
        # 2. Sources ohne Output-Kapazität
        sources = [n for n in analysis['nodes'] if 'Source' in n['type']]
        for source in sources:
            source_flows = [f for f in analysis['flows'] if f['from_node'] == source['label']]
            if not source_flows:
                issues.append(f"WARNUNG: Source '{source['label']}' hat keine Output-Flows")
        
        # 3. Sinks ohne Input-Kapazität
        sinks = [n for n in analysis['nodes'] if 'Sink' in n['type']]
        for sink in sinks:
            sink_flows = [f for f in analysis['flows'] if f['to_node'] == sink['label']]
            if not sink_flows:
                issues.append(f"WARNUNG: Sink '{sink['label']}' hat keine Input-Flows")
        
        # 4. Isolierte Buses
        buses = [n for n in analysis['nodes'] if 'Bus' in n['type']]
        for bus in buses:
            bus_flows = [f for f in analysis['flows'] if f['from_node'] == bus['label'] or f['to_node'] == bus['label']]
            if not bus_flows:
                issues.append(f"KRITISCH: Bus '{bus['label']}' ist isoliert (keine Flows)")
        
        # 5. Investment ohne maximale Kapazität
        for inv_flow in analysis['investments']:
            inv_attrs = inv_flow['attributes'].get('investment', {})
            if isinstance(inv_attrs, dict):
                if 'maximum' not in inv_attrs or inv_attrs.get('maximum') == '0':
                    issues.append(f"KRITISCH: Investment-Flow {inv_flow['from_node']}→{inv_flow['to_node']} hat keine maximale Kapazität")
        
        # 6. Converter-spezifische Probleme
        converters = [n for n in analysis['nodes'] if 'Transform' in n['type'] or 'Convert' in n['type']]
        for converter in converters:
            conv_inputs = [f for f in analysis['flows'] if f['to_node'] == converter['label']]
            conv_outputs = [f for f in analysis['flows'] if f['from_node'] == converter['label']]
            
            if not conv_inputs:
                issues.append(f"KRITISCH: Converter '{converter['label']}' hat keine Inputs")
            if not conv_outputs:
                issues.append(f"KRITISCH: Converter '{converter['label']}' hat keine Outputs")
        
        return issues
    
    def _save_analysis_report(self, analysis):
        """Speichert detaillierten Analyse-Report"""
        report_path = self.debug_dir / f"energy_system_analysis_{self.timestamp}.txt"
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("OEMOF-SOLPH ENERGYSYSTEM ANALYSE\n")
                f.write("=" * 50 + "\n\n")
                
                # Summary
                f.write("ZUSAMMENFASSUNG:\n")
                f.write("-" * 20 + "\n")
                for key, value in analysis['summary'].items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # Potential Issues
                if analysis['potential_issues']:
                    f.write("POTENTIELLE PROBLEME:\n")
                    f.write("-" * 30 + "\n")
                    for issue in analysis['potential_issues']:
                        f.write(f"⚠️  {issue}\n")
                    f.write("\n")
                
                # Nodes
                f.write("NODES:\n")
                f.write("-" * 10 + "\n")
                for node in analysis['nodes']:
                    f.write(f"Node: {node['label']} ({node['type']})\n")
                    f.write(f"  Inputs: {node['inputs_count']}, Outputs: {node['outputs_count']}\n")
                    if node['attributes']:
                        f.write(f"  Attributes: {node['attributes']}\n")
                    f.write("\n")
                
                # Investment Flows
                if analysis['investments']:
                    f.write("INVESTMENT FLOWS:\n")
                    f.write("-" * 20 + "\n")
                    for inv_flow in analysis['investments']:
                        f.write(f"Investment: {inv_flow['from_node']} → {inv_flow['to_node']}\n")
                        if 'investment' in inv_flow['attributes']:
                            f.write(f"  Parameter: {inv_flow['attributes']['investment']}\n")
                        f.write("\n")
                
                # Alle Flows
                f.write("ALLE FLOWS:\n")
                f.write("-" * 15 + "\n")
                for flow in analysis['flows']:
                    f.write(f"Flow: {flow['from_node']} → {flow['to_node']} ({flow['direction']})\n")
                    if flow['attributes']:
                        for attr, value in flow['attributes'].items():
                            f.write(f"  {attr}: {value}\n")
                    f.write("\n")
            
            logger.info(f"Analyse-Report gespeichert: {report_path}")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Analyse-Reports: {e}")
    
    def debug_converter_implementation(self):
        """
        Spezielle Debugging-Funktion für Converter-Implementierung
        
        Returns:
            Dictionary mit Converter-spezifischer Analyse
        """
        logger.info("Analysiere Converter-Implementierung...")
        
        converter_debug = {
            'converters_found': [],
            'converter_flows': [],
            'conversion_factors': [],
            'issues': []
        }
        
        # Finde alle Converter-artigen Nodes
        for node in self.energy_system.nodes:
            node_type = type(node).__name__
            if 'Transform' in node_type or 'Convert' in node_type:
                converter_info = {
                    'label': getattr(node, 'label', str(node)),
                    'type': node_type,
                    'inputs': {},
                    'outputs': {}
                }
                
                # Input-Flows analysieren
                if hasattr(node, 'inputs'):
                    for input_node, flow in node.inputs.items():
                        converter_info['inputs'][getattr(input_node, 'label', str(input_node))] = {
                            'nominal_capacity': getattr(flow, 'nominal_capacity', None),
                            'investment': bool(getattr(flow, 'investment', False))
                        }
                
                # Output-Flows analysieren
                if hasattr(node, 'outputs'):
                    for output_node, flow in node.outputs.items():
                        converter_info['outputs'][getattr(output_node, 'label', str(output_node))] = {
                            'nominal_capacity': getattr(flow, 'nominal_capacity', None),
                            'investment': bool(getattr(flow, 'investment', False))
                        }
                
                converter_debug['converters_found'].append(converter_info)
        
        # Issues identifizieren
        if not converter_debug['converters_found']:
            converter_debug['issues'].append("Keine Converter-Komponenten im EnergySystem gefunden")
        
        for converter in converter_debug['converters_found']:
            if not converter['inputs']:
                converter_debug['issues'].append(f"Converter '{converter['label']}' hat keine Inputs")
            if not converter['outputs']:
                converter_debug['issues'].append(f"Converter '{converter['label']}' hat keine Outputs")
        
        # Report speichern
        self._save_converter_debug_report(converter_debug)
        
        return converter_debug
    
    def _save_converter_debug_report(self, converter_debug):
        """Speichert Converter-Debug-Report"""
        report_path = self.debug_dir / f"converter_debug_{self.timestamp}.txt"
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("CONVERTER IMPLEMENTIERUNG DEBUG\n")
                f.write("=" * 40 + "\n\n")
                
                if converter_debug['issues']:
                    f.write("PROBLEME:\n")
                    f.write("-" * 15 + "\n")
                    for issue in converter_debug['issues']:
                        f.write(f"❌ {issue}\n")
                    f.write("\n")
                
                f.write("GEFUNDENE CONVERTER:\n")
                f.write("-" * 25 + "\n")
                for converter in converter_debug['converters_found']:
                    f.write(f"Converter: {converter['label']} ({converter['type']})\n")
                    f.write(f"  Inputs: {converter['inputs']}\n")
                    f.write(f"  Outputs: {converter['outputs']}\n")
                    f.write("\n")
            
            logger.info(f"Converter-Debug-Report gespeichert: {report_path}")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Converter-Debug-Reports: {e}")
    
    def run_full_debug(self):
        """
        Führt vollständige Debug-Analyse durch
        
        Returns:
            Dictionary mit allen Debug-Informationen
        """
        logger.info("Starte vollständige Debug-Analyse...")
        
        debug_results = {
            'lp_file': None,
            'energy_system_analysis': None,
            'converter_debug': None,
            'debug_timestamp': self.timestamp,
            'debug_directory': str(self.debug_dir)
        }
        
        # 1. LP-Export
        debug_results['lp_file'] = self.export_lp_file()
        
        # 2. EnergySystem-Analyse
        debug_results['energy_system_analysis'] = self.analyze_energy_system()
        
        # 3. Converter-Debug
        debug_results['converter_debug'] = self.debug_converter_implementation()
        
        # 4. Zusammenfassung ausgeben
        self._print_debug_summary(debug_results)
        
        return debug_results
    
    def _print_debug_summary(self, debug_results):
        """Gibt Debug-Zusammenfassung aus"""
        print("\n" + "="*60)
        print("🔍 MODEL DEBUG ZUSAMMENFASSUNG")
        print("="*60)
        
        # EnergySystem Info
        if debug_results['energy_system_analysis']:
            analysis = debug_results['energy_system_analysis']
            print(f"📊 EnergySystem: {analysis['summary']['total_nodes']} Nodes, {len(analysis['flows'])} Flows")
            print(f"💰 Investments: {len(analysis['investments'])} Investment-Flows")
            
            # Potentielle Probleme
            if analysis['potential_issues']:
                print(f"\n⚠️  POTENTIELLE PROBLEME ({len(analysis['potential_issues'])}):")
                for issue in analysis['potential_issues'][:5]:  # Erste 5 anzeigen
                    print(f"   • {issue}")
                if len(analysis['potential_issues']) > 5:
                    print(f"   ... und {len(analysis['potential_issues']) - 5} weitere")
        
        # Converter Info
        if debug_results['converter_debug']:
            conv_debug = debug_results['converter_debug']
            print(f"\n🔄 Converter: {len(conv_debug['converters_found'])} gefunden")
            if conv_debug['issues']:
                print(f"   Converter-Probleme: {len(conv_debug['issues'])}")
        
        # Dateien
        print(f"\n📁 Debug-Dateien erstellt in: {debug_results['debug_directory']}")
        if debug_results['lp_file']:
            print(f"   📄 LP-Datei: {Path(debug_results['lp_file']).name}")
        
        print("\n💡 NÄCHSTE SCHRITTE:")
        print("   1. LP-Datei mit Solver analysieren")
        print("   2. Investment-Parameter in Excel prüfen")
        print("   3. Converter-Konfiguration überprüfen")
        print("="*60)

# Beispiel-Verwendung
def debug_infeasible_model(energy_system, model=None, data=None):
    """
    Hauptfunktion für Model-Debugging
    
    Args:
        energy_system: oemof EnergySystem
        model: oemof Model (optional)
        data: Original Excel-Daten (optional)
        
    Returns:
        Debug-Ergebnisse
    """
    debugger = ModelDebugger(energy_system, model, data)
    return debugger.run_full_debug()
