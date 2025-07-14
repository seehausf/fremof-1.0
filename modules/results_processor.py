#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Ergebnisverarbeitung
=====================================

Verarbeitet und speichert Optimierungsergebnisse in verschiedenen Formaten.
Erstellt strukturierte Ausgabedateien und Zusammenfassungen.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

try:
    import oemof.solph as solph
except ImportError:
    solph = None


class ResultsProcessor:
    """Klasse für die Verarbeitung und Speicherung von Optimierungsergebnissen."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Results-Processor.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Output-Format
        self.output_format = settings.get('output_format', 'xlsx')
        
        # Erstellte Dateien
        self.output_files = []
    
    def process_results(self, results: Dict[str, Any], energy_system: Any, 
                       excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Optimierungsergebnisse komplett.
        
        Args:
            results: oemof.solph Ergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit verarbeiteten Ergebnissen
        """
        self.logger.info("📈 Verarbeite Optimierungsergebnisse...")
        
        processed_results = {}
        
        # Flows extrahieren und speichern
        flows_df = self._extract_flows(results)
        processed_results['flows'] = flows_df
        self._save_dataframe(flows_df, 'flows')
        
        # Bus-Bilanzen berechnen
        bus_balances = self._calculate_bus_balances(results, energy_system)
        processed_results['bus_balances'] = bus_balances
        self._save_dataframe(bus_balances, 'bus_balances')
        
        # Investment-Ergebnisse (falls vorhanden)
        investments = self._extract_investments(results)
        if not investments.empty:
            processed_results['investments'] = investments
            self._save_dataframe(investments, 'investments')
        
        # Kosten-Aufschlüsselung
        costs = self._calculate_costs(results, energy_system)
        processed_results['costs'] = costs
        self._save_dataframe(costs, 'costs')
        
        # Zusammenfassung erstellen
        summary = self._create_summary(processed_results, energy_system)
        processed_results['summary'] = summary
        self._save_summary(summary)
        
        self.logger.info(f"✅ {len(self.output_files)} Ergebnisdateien erstellt")
        
        return processed_results
    
    def _extract_flows(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Extrahiert alle Flow-Werte aus den Ergebnissen."""
        flow_data = []
        
        for (source, target), flow_results in results.items():
            if 'sequences' in flow_results:
                flow_values = flow_results['sequences']['flow']
                
                for timestamp, value in flow_values.items():
                    flow_data.append({
                        'timestamp': timestamp,
                        'source': str(source),
                        'target': str(target),
                        'flow': value
                    })
        
        if flow_data:
            df = pd.DataFrame(flow_data)
            # Pivot für bessere Übersicht
            pivot_df = df.pivot_table(
                index='timestamp', 
                columns=['source', 'target'], 
                values='flow', 
                fill_value=0
            )
            return pivot_df
        else:
            return pd.DataFrame()
    
    def _calculate_bus_balances(self, results: Dict[str, Any], energy_system: Any) -> pd.DataFrame:
        """Berechnet Bilanzen für alle Buses."""
        if not solph:
            return pd.DataFrame()
        
        balance_data = []
        
        # Alle Buses identifizieren
        buses = [node for node in energy_system.nodes if isinstance(node, solph.buses.Bus)]
        
        for bus in buses:
            bus_label = bus.label
            
            # Inputs (Zuflüsse zum Bus)
            inputs = []
            for (source, target), flow_results in results.items():
                if str(target) == bus_label and 'sequences' in flow_results:
                    flow_values = flow_results['sequences']['flow']
                    inputs.append(flow_values)
            
            # Outputs (Abflüsse vom Bus)
            outputs = []
            for (source, target), flow_results in results.items():
                if str(source) == bus_label and 'sequences' in flow_results:
                    flow_values = flow_results['sequences']['flow']
                    outputs.append(flow_values)
            
            # Summieren
            if inputs or outputs:
                if inputs:
                    total_input = sum(inputs)
                else:
                    total_input = pd.Series(0, index=flow_values.index)
                
                if outputs:
                    total_output = sum(outputs)
                else:
                    total_output = pd.Series(0, index=flow_values.index)
                
                balance = total_input - total_output
                
                for timestamp in total_input.index:
                    balance_data.append({
                        'timestamp': timestamp,
                        'bus': bus_label,
                        'input': total_input[timestamp],
                        'output': total_output[timestamp],
                        'balance': balance[timestamp]
                    })
        
        if balance_data:
            return pd.DataFrame(balance_data)
        else:
            return pd.DataFrame()
    
    def _extract_investments(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Extrahiert Investment-Ergebnisse."""
        investment_data = []
        
        for (source, target), flow_results in results.items():
            if 'scalars' in flow_results:
                scalars = flow_results['scalars']
                
                # Investment-bezogene Werte suchen
                for key, value in scalars.items():
                    if 'invest' in key.lower():
                        investment_data.append({
                            'source': str(source),
                            'target': str(target),
                            'parameter': key,
                            'value': value
                        })
        
        return pd.DataFrame(investment_data)
    
    def _calculate_costs(self, results: Dict[str, Any], energy_system: Any) -> pd.DataFrame:
        """Berechnet Kostenaufschlüsselung."""
        cost_data = []
        
        for (source, target), flow_results in results.items():
            if 'sequences' in flow_results and 'scalars' in flow_results:
                sequences = flow_results['sequences']
                scalars = flow_results['scalars']
                
                # Variable Kosten
                if 'flow' in sequences:
                    flow_values = sequences['flow']
                    
                    # Variable Kosten aus Flow-Eigenschaften extrahieren (vereinfacht)
                    variable_costs = scalars.get('variable_costs', 0)
                    if variable_costs != 0:
                        total_variable_costs = flow_values.sum() * variable_costs
                        
                        cost_data.append({
                            'source': str(source),
                            'target': str(target),
                            'cost_type': 'variable',
                            'total_cost': total_variable_costs,
                            'unit': '€'
                        })
                
                # Investment-Kosten
                investment_costs = scalars.get('investment_costs', 0)
                if investment_costs != 0:
                    cost_data.append({
                        'source': str(source),
                        'target': str(target),
                        'cost_type': 'investment',
                        'total_cost': investment_costs,
                        'unit': '€'
                    })
        
        return pd.DataFrame(cost_data)
    
    def _create_summary(self, processed_results: Dict[str, Any], energy_system: Any) -> Dict[str, Any]:
        """Erstellt eine Ergebnis-Zusammenfassung."""
        summary = {
            'simulation_period': {},
            'energy_flows': {},
            'costs': {},
            'investments': {},
            'system_info': {}
        }
        
        # Zeitraum
        if hasattr(energy_system, 'timeindex'):
            timeindex = energy_system.timeindex
            summary['simulation_period'] = {
                'start': timeindex[0].strftime('%Y-%m-%d %H:%M'),
                'end': timeindex[-1].strftime('%Y-%m-%d %H:%M'),
                'duration_hours': len(timeindex),
                'resolution': pd.infer_freq(timeindex) or 'variable'
            }
        
        # Energie-Flüsse
        if 'flows' in processed_results and not processed_results['flows'].empty:
            flows_df = processed_results['flows']
            
            summary['energy_flows'] = {
                'total_energy_MWh': flows_df.sum().sum() / 1000,  # Annahme: Werte in kWh
                'peak_power_MW': flows_df.max().max() / 1000,
                'number_of_flows': len(flows_df.columns)
            }
        
        # Kosten
        if 'costs' in processed_results and not processed_results['costs'].empty:
            costs_df = processed_results['costs']
            
            total_costs = costs_df['total_cost'].sum()
            variable_costs = costs_df[costs_df['cost_type'] == 'variable']['total_cost'].sum()
            investment_costs = costs_df[costs_df['cost_type'] == 'investment']['total_cost'].sum()
            
            summary['costs'] = {
                'total_costs_euro': total_costs,
                'variable_costs_euro': variable_costs,
                'investment_costs_euro': investment_costs
            }
        
        # Investments
        if 'investments' in processed_results and not processed_results['investments'].empty:
            investments_df = processed_results['investments']
            
            summary['investments'] = {
                'number_of_investments': len(investments_df),
                'total_invested_capacity': investments_df[
                    investments_df['parameter'].str.contains('capacity', case=False)
                ]['value'].sum()
            }
        
        # System-Info
        if solph and hasattr(energy_system, 'nodes'):
            nodes = energy_system.nodes
            summary['system_info'] = {
                'total_components': len(nodes),
                'buses': len([n for n in nodes if isinstance(n, solph.buses.Bus)]),
                'sources': len([n for n in nodes if isinstance(n, solph.components.Source)]),
                'sinks': len([n for n in nodes if isinstance(n, solph.components.Sink)]),
                'converters': len([n for n in nodes if isinstance(n, solph.components.Converter)])
            }
        
        return summary
    
    def _save_dataframe(self, df: pd.DataFrame, filename: str):
        """Speichert DataFrame in gewähltem Format."""
        if df.empty:
            return
        
        if self.output_format.lower() == 'xlsx':
            filepath = self.output_dir / f"{filename}.xlsx"
            df.to_excel(filepath, index=True)
        else:  # CSV
            filepath = self.output_dir / f"{filename}.csv"
            df.to_csv(filepath, index=True)
        
        self.output_files.append(filepath)
        self.logger.debug(f"      💾 {filepath.name}")
    
    def _save_summary(self, summary: Dict[str, Any]):
        """Speichert die Zusammenfassung."""
        # JSON-Format für maschinenlesbare Zusammenfassung
        import json
        
        json_file = self.output_dir / "summary.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.output_files.append(json_file)
        
        # Textformat für menschenlesbare Zusammenfassung
        txt_file = self.output_dir / "summary.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("OPTIMIERUNGSERGEBNISSE - ZUSAMMENFASSUNG\n")
            f.write("=" * 50 + "\n\n")
            
            for section, data in summary.items():
                f.write(f"{section.upper().replace('_', ' ')}:\n")
                f.write("-" * 30 + "\n")
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        f.write(f"  {key}: {value}\n")
                else:
                    f.write(f"  {data}\n")
                
                f.write("\n")
        
        self.output_files.append(txt_file)
        self.logger.debug(f"      💾 {json_file.name}, {txt_file.name}")


# Test-Funktion
def test_results_processor():
    """Testfunktion für den Results-Processor."""
    import tempfile
    
    # Dummy-Ergebnisse erstellen
    dummy_results = {
        ('source1', 'bus1'): {
            'sequences': {
                'flow': pd.Series([10, 20, 15], index=pd.date_range('2025-01-01', periods=3, freq='h'))
            },
            'scalars': {
                'variable_costs': 0.1
            }
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'output_format': 'csv', 'debug_mode': True}
        processor = ResultsProcessor(Path(temp_dir), settings)
        
        # Dummy Energy System
        class DummyEnergySystem:
            def __init__(self):
                self.timeindex = pd.date_range('2025-01-01', periods=3, freq='h')
                self.nodes = []
        
        energy_system = DummyEnergySystem()
        excel_data = {}
        
        try:
            results = processor.process_results(dummy_results, energy_system, excel_data)
            print("✅ Results-Processor Test erfolgreich!")
            print(f"Erstellte Dateien: {len(processor.output_files)}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")


if __name__ == "__main__":
    test_results_processor()
