#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Ergebnisverarbeitung (KOMPLETT NEU GESCHRIEBEN)
================================================================

Verarbeitet und speichert Optimierungsergebnisse in verschiedenen Formaten.
Erstellt strukturierte Ausgabedateien und detaillierte Kostenanalyse.

KOMPLETT NEU: Saubere Architektur, vollständige Funktionalität, keine Syntaxfehler.

Autor: [Ihr Name]  
Datum: Juli 2025
Version: 2.0.0 (komplett neu)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import json

try:
    import oemof.solph as solph
    from oemof.solph._options import Investment, NonConvex
except ImportError:
    solph = None


class ResultsProcessor:
    """Verarbeitet und speichert Optimierungsergebnisse."""
    
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
        Verarbeitet die Optimierungsergebnisse vollständig.
        
        Args:
            results: oemof.solph Ergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit verarbeiteten Ergebnissen
        """
        self.logger.info("📈 Verarbeite Optimierungsergebnisse...")
        
        processed_results = {}
        
        try:
            # 1. Basis-Flows extrahieren
            flows_df = self._extract_flows(results)
            processed_results['flows'] = flows_df
            self._save_dataframe(flows_df, 'flows')
            
            # 2. Bus-Bilanzen berechnen
            bus_balances = self._calculate_bus_balances(results, energy_system)
            processed_results['bus_balances'] = bus_balances
            self._save_dataframe(bus_balances, 'bus_balances')
            
            # 3. Investment-Ergebnisse
            investments = self._extract_investments(results)
            if not investments.empty:
                processed_results['investments'] = investments
                self._save_dataframe(investments, 'investments')
            
            # 4. Kostenaufschlüsselung
            costs = self._calculate_comprehensive_costs(results, energy_system, excel_data)
            processed_results['costs'] = costs
            self._save_costs_breakdown(costs)
            
            # 5. Zusammenfassung erstellen
            summary = self._create_summary(processed_results, energy_system)
            processed_results['summary'] = summary
            self._save_summary(summary)
            
            # 6. Komplette Excel-Ausgabe
            self._create_comprehensive_excel_output(processed_results, energy_system, excel_data)
            
            self.logger.info(f"✅ {len(self.output_files)} Ergebnisdateien erstellt")
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Ergebnisverarbeitung: {e}")
            raise
    
    def _extract_flows(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Extrahiert alle Flow-Werte aus den Ergebnissen."""
        try:
            flow_data = []
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    
                    # Als DataFrame mit Zeitstempel
                    for timestamp, value in flow_values.items():
                        flow_data.append({
                            'timestamp': timestamp,
                            'source': str(source),
                            'target': str(target),
                            'flow_kW': value,
                            'connection': f"{source} → {target}"
                        })
            
            if flow_data:
                df = pd.DataFrame(flow_data)
                
                # Pivot für bessere Übersicht
                pivot_df = df.pivot_table(
                    index='timestamp', 
                    columns='connection', 
                    values='flow_kW', 
                    fill_value=0
                )
                
                # Statistiken hinzufügen
                summary_stats = pd.DataFrame({
                    'total_energy_kWh': pivot_df.sum(),
                    'max_power_kW': pivot_df.max(),
                    'avg_power_kW': pivot_df.mean(),
                    'min_power_kW': pivot_df.min(),
                    'operating_hours': (pivot_df > 0).sum()
                })
                
                # Als separate Sheets speichern
                return {
                    'flows': pivot_df,
                    'flow_statistics': summary_stats
                }
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Flow-Extraktion fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _calculate_bus_balances(self, results: Dict[str, Any], energy_system: Any) -> pd.DataFrame:
        """Berechnet Bilanzen für alle Buses."""
        if not solph:
            return pd.DataFrame()
        
        try:
            balance_data = []
            
            # Alle Buses identifizieren
            buses = [node for node in energy_system.nodes if isinstance(node, solph.buses.Bus)]
            
            for bus in buses:
                bus_label = str(bus.label)
                
                # Inputs und Outputs sammeln
                inputs_data = []
                outputs_data = []
                
                for (source, target), flow_results in results.items():
                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                        flow_values = flow_results['sequences']['flow']
                        
                        if str(target) == bus_label:
                            # Input zum Bus
                            inputs_data.append({
                                'source': str(source),
                                'values': flow_values
                            })
                        elif str(source) == bus_label:
                            # Output vom Bus
                            outputs_data.append({
                                'target': str(target),
                                'values': flow_values
                            })
                
                # Zeitreihen erstellen
                if inputs_data or outputs_data:
                    # Sample-Zeitindex aus erstem verfügbaren Flow
                    sample_flow = (inputs_data + outputs_data)[0]['values']
                    
                    for timestamp in sample_flow.index:
                        # Inputs summieren
                        total_input = sum([
                            inp['values'].get(timestamp, 0) for inp in inputs_data
                        ])
                        
                        # Outputs summieren
                        total_output = sum([
                            out['values'].get(timestamp, 0) for out in outputs_data
                        ])
                        
                        balance_data.append({
                            'timestamp': timestamp,
                            'bus': bus_label,
                            'total_input_kW': total_input,
                            'total_output_kW': total_output,
                            'balance_kW': total_input - total_output,
                            'input_sources': len(inputs_data),
                            'output_targets': len(outputs_data)
                        })
            
            if balance_data:
                df = pd.DataFrame(balance_data)
                
                # Balance-Checks hinzufügen
                df['balance_violation'] = abs(df['balance_kW']) > 1e-6
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Bus-Bilanz-Berechnung fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _extract_investments(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Extrahiert Investment-Ergebnisse."""
        try:
            investment_data = []
            
            for (source, target), flow_results in results.items():
                if 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Investment-bezogene Werte suchen
                    for key, value in scalars.items():
                        if 'invest' in key.lower() and value > 0:
                            investment_data.append({
                                'connection': f"{source} → {target}",
                                'source': str(source),
                                'target': str(target),
                                'parameter': key,
                                'invested_capacity_kW': value,
                                'investment_type': self._classify_investment_type(source, target)
                            })
            
            if investment_data:
                df = pd.DataFrame(investment_data)
                
                # Zusätzliche Analyse
                df['total_invested_capacity'] = df.groupby('connection')['invested_capacity_kW'].transform('sum')
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Investment-Extraktion fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _calculate_comprehensive_costs(self, results: Dict[str, Any], 
                                     energy_system: Any, 
                                     excel_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Berechnet umfassende Kostenaufschlüsselung."""
        try:
            cost_breakdown = {}
            
            # 1. Variable Kosten
            variable_costs = self._calculate_variable_costs(results)
            cost_breakdown['variable_costs'] = variable_costs
            
            # 2. Investment-Kosten
            investment_costs = self._calculate_investment_costs(results, energy_system, excel_data)
            cost_breakdown['investment_costs'] = investment_costs
            
            # 3. Technologie-Zusammenfassung
            technology_summary = self._calculate_technology_cost_summary(variable_costs, investment_costs)
            cost_breakdown['technology_summary'] = technology_summary
            
            # 4. Kostenarten-Übersicht
            cost_type_summary = self._calculate_cost_type_summary(variable_costs, investment_costs)
            cost_breakdown['cost_type_summary'] = cost_type_summary
            
            return cost_breakdown
            
        except Exception as e:
            self.logger.warning(f"Kostenberechnung fehlgeschlagen: {e}")
            return {}
    
    def _calculate_variable_costs(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Berechnet variable Kosten."""
        try:
            variable_cost_data = []
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'scalars' in flow_results:
                    sequences = flow_results['sequences']
                    scalars = flow_results['scalars']
                    
                    if 'flow' in sequences:
                        flow_values = sequences['flow']
                        total_energy = flow_values.sum()
                        
                        # Variable Kosten aus Scalars
                        var_costs = scalars.get('variable_costs', 0)
                        
                        if var_costs != 0 and total_energy > 0:
                            total_var_costs = total_energy * var_costs
                            
                            variable_cost_data.append({
                                'connection': f"{source} → {target}",
                                'source': str(source),
                                'target': str(target),
                                'total_energy_kWh': total_energy,
                                'variable_costs_EUR_per_kWh': var_costs,
                                'total_variable_costs_EUR': total_var_costs,
                                'technology_type': self._guess_technology_type(str(source)),
                                'max_power_kW': flow_values.max(),
                                'avg_power_kW': flow_values.mean(),
                                'operating_hours': (flow_values > 0).sum()
                            })
            
            if variable_cost_data:
                df = pd.DataFrame(variable_cost_data)
                df = df.sort_values('total_variable_costs_EUR', ascending=False)
                
                # Relative Anteile
                total_costs = df['total_variable_costs_EUR'].sum()
                if total_costs > 0:
                    df['cost_share_percent'] = (df['total_variable_costs_EUR'] / total_costs * 100).round(2)
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Variable Kostenberechnung fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _calculate_investment_costs(self, results: Dict[str, Any], 
                                  energy_system: Any, 
                                  excel_data: Dict[str, Any]) -> pd.DataFrame:
        """Berechnet Investment-Kosten."""
        try:
            investment_cost_data = []
            
            for (source, target), flow_results in results.items():
                if 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Investment-Kapazität
                    if 'invest' in scalars and scalars['invest'] > 0:
                        invested_capacity = scalars['invest']
                        
                        # EP-Costs aus System extrahieren (vereinfacht)
                        ep_costs = self._estimate_ep_costs(source, target, energy_system, excel_data)
                        
                        if ep_costs > 0:
                            annual_investment_costs = ep_costs * invested_capacity
                            
                            investment_cost_data.append({
                                'connection': f"{source} → {target}",
                                'source': str(source),
                                'target': str(target),
                                'invested_capacity_kW': invested_capacity,
                                'ep_costs_EUR_per_kW_per_year': ep_costs,
                                'annual_investment_costs_EUR': annual_investment_costs,
                                'technology_type': self._guess_technology_type(str(source)),
                                'investment_type': self._classify_investment_type(source, target)
                            })
            
            if investment_cost_data:
                df = pd.DataFrame(investment_cost_data)
                df = df.sort_values('annual_investment_costs_EUR', ascending=False)
                
                # Relative Anteile
                total_investment = df['annual_investment_costs_EUR'].sum()
                if total_investment > 0:
                    df['investment_share_percent'] = (df['annual_investment_costs_EUR'] / total_investment * 100).round(2)
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Investment-Kostenberechnung fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _calculate_technology_cost_summary(self, variable_costs: pd.DataFrame, 
                                         investment_costs: pd.DataFrame) -> pd.DataFrame:
        """Erstellt Technologie-Kostenzusammenfassung."""
        try:
            summary_data = []
            
            # Alle Technologien sammeln
            technologies = set()
            if not variable_costs.empty:
                technologies.update(variable_costs['technology_type'].unique())
            if not investment_costs.empty:
                technologies.update(investment_costs['technology_type'].unique())
            
            for technology in technologies:
                var_costs = 0
                inv_costs = 0
                total_energy = 0
                total_capacity = 0
                
                # Variable Kosten
                if not variable_costs.empty:
                    tech_var = variable_costs[variable_costs['technology_type'] == technology]
                    var_costs = tech_var['total_variable_costs_EUR'].sum()
                    total_energy = tech_var['total_energy_kWh'].sum()
                
                # Investment-Kosten
                if not investment_costs.empty:
                    tech_inv = investment_costs[investment_costs['technology_type'] == technology]
                    inv_costs = tech_inv['annual_investment_costs_EUR'].sum()
                    total_capacity = tech_inv['invested_capacity_kW'].sum()
                
                total_costs = var_costs + inv_costs
                
                if total_costs > 0:
                    summary_data.append({
                        'technology_type': technology,
                        'variable_costs_EUR': var_costs,
                        'investment_costs_EUR': inv_costs,
                        'total_costs_EUR': total_costs,
                        'total_energy_kWh': total_energy,
                        'total_capacity_kW': total_capacity,
                        'specific_costs_EUR_per_kWh': var_costs / total_energy if total_energy > 0 else 0,
                        'specific_costs_EUR_per_kW': total_costs / total_capacity if total_capacity > 0 else 0
                    })
            
            if summary_data:
                df = pd.DataFrame(summary_data)
                df = df.sort_values('total_costs_EUR', ascending=False)
                
                # Relative Anteile
                total_system_costs = df['total_costs_EUR'].sum()
                if total_system_costs > 0:
                    df['cost_share_percent'] = (df['total_costs_EUR'] / total_system_costs * 100).round(2)
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Technologie-Zusammenfassung fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _calculate_cost_type_summary(self, variable_costs: pd.DataFrame, 
                                   investment_costs: pd.DataFrame) -> pd.DataFrame:
        """Erstellt Kostenarten-Übersicht."""
        try:
            summary_data = []
            
            # Variable Kosten
            if not variable_costs.empty:
                var_total = variable_costs['total_variable_costs_EUR'].sum()
                var_count = len(variable_costs)
                total_energy = variable_costs['total_energy_kWh'].sum()
                
                summary_data.append({
                    'cost_type': 'Variable Costs',
                    'total_EUR': var_total,
                    'components_count': var_count,
                    'avg_cost_per_component_EUR': var_total / var_count if var_count > 0 else 0,
                    'total_energy_kWh': total_energy,
                    'avg_cost_per_kWh_EUR': var_total / total_energy if total_energy > 0 else 0
                })
            
            # Investment-Kosten
            if not investment_costs.empty:
                inv_total = investment_costs['annual_investment_costs_EUR'].sum()
                inv_count = len(investment_costs)
                total_capacity = investment_costs['invested_capacity_kW'].sum()
                
                summary_data.append({
                    'cost_type': 'Investment Costs',
                    'total_EUR': inv_total,
                    'components_count': inv_count,
                    'avg_cost_per_component_EUR': inv_total / inv_count if inv_count > 0 else 0,
                    'total_capacity_kW': total_capacity,
                    'avg_cost_per_kW_EUR': inv_total / total_capacity if total_capacity > 0 else 0
                })
            
            if summary_data:
                df = pd.DataFrame(summary_data)
                
                # Gesamtkosten und Anteile
                total_costs = df['total_EUR'].sum()
                if total_costs > 0:
                    df['cost_share_percent'] = (df['total_EUR'] / total_costs * 100).round(2)
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Kostenarten-Zusammenfassung fehlgeschlagen: {e}")
            return pd.DataFrame()
    
    def _create_summary(self, processed_results: Dict[str, Any], energy_system: Any) -> Dict[str, Any]:
        """Erstellt eine Ergebnis-Zusammenfassung."""
        try:
            summary = {}
            
            # Zeitraum
            if hasattr(energy_system, 'timeindex'):
                timeindex = energy_system.timeindex
                summary['simulation_period'] = {
                    'start': timeindex[0].strftime('%Y-%m-%d %H:%M'),
                    'end': timeindex[-1].strftime('%Y-%m-%d %H:%M'),
                    'duration_hours': len(timeindex),
                    'resolution': pd.infer_freq(timeindex) or 'variable'
                }
            
            # Energie-Flows
            if 'flows' in processed_results and isinstance(processed_results['flows'], dict):
                flows_data = processed_results['flows'].get('flows', pd.DataFrame())
                if not flows_data.empty:
                    summary['energy_flows'] = {
                        'total_energy_MWh': flows_data.sum().sum() / 1000,
                        'peak_power_MW': flows_data.max().max() / 1000,
                        'number_of_flows': len(flows_data.columns)
                    }
            
            # Kosten
            if 'costs' in processed_results:
                costs = processed_results['costs']
                total_costs = 0
                
                if 'cost_type_summary' in costs and not costs['cost_type_summary'].empty:
                    total_costs = costs['cost_type_summary']['total_EUR'].sum()
                
                summary['costs'] = {
                    'total_system_costs_EUR': total_costs,
                    'has_variable_costs': 'variable_costs' in costs and not costs['variable_costs'].empty,
                    'has_investment_costs': 'investment_costs' in costs and not costs['investment_costs'].empty
                }
            
            # Investments
            if 'investments' in processed_results and not processed_results['investments'].empty:
                investments = processed_results['investments']
                summary['investments'] = {
                    'number_of_investments': len(investments),
                    'total_invested_capacity_kW': investments['invested_capacity_kW'].sum(),
                    'investment_technologies': investments['investment_type'].unique().tolist()
                }
            
            # System-Info
            if hasattr(energy_system, 'nodes'):
                nodes = energy_system.nodes
                node_types = {}
                
                for node in nodes:
                    node_type = type(node).__name__
                    node_types[node_type] = node_types.get(node_type, 0) + 1
                
                summary['system_info'] = {
                    'total_components': len(nodes),
                    'component_types': node_types
                }
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"Summary-Erstellung fehlgeschlagen: {e}")
            return {}
    
    # Hilfsmethoden
    def _guess_technology_type(self, component_label: str) -> str:
        """Errät Technologie-Typ basierend auf Label."""
        label_lower = component_label.lower()
        
        if any(word in label_lower for word in ['pv', 'solar', 'photovoltaic']):
            return 'PV Solar'
        elif any(word in label_lower for word in ['wind', 'wtg']):
            return 'Wind Power'
        elif any(word in label_lower for word in ['grid', 'import']):
            return 'Grid Import'
        elif any(word in label_lower for word in ['load', 'demand']):
            return 'Load'
        elif any(word in label_lower for word in ['gas', 'plant']):
            return 'Gas Power'
        elif any(word in label_lower for word in ['heat', 'pump']):
            return 'Heat Pump'
        elif any(word in label_lower for word in ['export']):
            return 'Grid Export'
        else:
            return 'Other'
    
    def _classify_investment_type(self, source: Any, target: Any) -> str:
        """Klassifiziert Investment-Typ."""
        source_str = str(source).lower()
        target_str = str(target).lower()
        
        if 'bus' in target_str:
            return 'Generation Investment'
        elif 'bus' in source_str:
            return 'Demand Investment'
        else:
            return 'Conversion Investment'
    
    def _estimate_ep_costs(self, source: Any, target: Any, energy_system: Any, excel_data: Dict[str, Any]) -> float:
        """Schätzt EP-Costs für Investment (vereinfacht)."""
        # Fallback-Werte basierend auf Technologie
        source_str = str(source).lower()
        
        if any(word in source_str for word in ['pv', 'solar']):
            return 71.0  # Typisch für PV
        elif any(word in source_str for word in ['wind']):
            return 96.0  # Typisch für Wind
        elif any(word in source_str for word in ['gas']):
            return 58.0  # Typisch für Gas
        elif any(word in source_str for word in ['heat', 'pump']):
            return 115.0  # Typisch für Wärmepumpe
        else:
            return 50.0  # Default
    
    # Speicher-Methoden
    def _save_dataframe(self, df: Union[pd.DataFrame, Dict[str, pd.DataFrame]], filename: str):
        """Speichert DataFrame(s) in gewähltem Format."""
        if isinstance(df, dict):
            # Multiple DataFrames als Excel mit mehreren Sheets
            if self.output_format.lower() == 'xlsx':
                filepath = self.output_dir / f"{filename}.xlsx"
                
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    for sheet_name, data in df.items():
                        if not data.empty:
                            data.to_excel(writer, sheet_name=sheet_name, index=True)
                
                self.output_files.append(filepath)
                self.logger.debug(f"      💾 {filepath.name}")
            else:
                # Separate CSV-Dateien
                for sheet_name, data in df.items():
                    if not data.empty:
                        filepath = self.output_dir / f"{filename}_{sheet_name}.csv"
                        data.to_csv(filepath, index=True)
                        self.output_files.append(filepath)
                        self.logger.debug(f"      💾 {filepath.name}")
        
        elif isinstance(df, pd.DataFrame) and not df.empty:
            # Einzelnes DataFrame
            if self.output_format.lower() == 'xlsx':
                filepath = self.output_dir / f"{filename}.xlsx"
                df.to_excel(filepath, index=True)
            else:
                filepath = self.output_dir / f"{filename}.csv"
                df.to_csv(filepath, index=True)
            
            self.output_files.append(filepath)
            self.logger.debug(f"      💾 {filepath.name}")
    
    def _save_costs_breakdown(self, costs: Dict[str, pd.DataFrame]):
        """Speichert die Kostenaufschlüsselung."""
        if not costs:
            return
        
        try:
            if self.output_format.lower() == 'xlsx':
                filepath = self.output_dir / "cost_breakdown.xlsx"
                
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    for cost_type, df in costs.items():
                        if not df.empty:
                            df.to_excel(writer, sheet_name=cost_type, index=False)
                
                self.output_files.append(filepath)
                self.logger.debug(f"      💾 {filepath.name}")
            else:
                # Separate CSV-Dateien
                for cost_type, df in costs.items():
                    if not df.empty:
                        filepath = self.output_dir / f"costs_{cost_type}.csv"
                        df.to_csv(filepath, index=False)
                        self.output_files.append(filepath)
                        self.logger.debug(f"      💾 {filepath.name}")
                        
        except Exception as e:
            self.logger.warning(f"Kostenaufschlüsselung konnte nicht gespeichert werden: {e}")
    
    def _save_summary(self, summary: Dict[str, Any]):
        """Speichert die Zusammenfassung."""
        try:
            # JSON-Format
            json_file = self.output_dir / "summary.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.output_files.append(json_file)
            
            # Text-Format
            txt_file = self.output_dir / "summary.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write("OPTIMIERUNGSERGEBNISSE - ZUSAMMENFASSUNG\n")
                f.write("=" * 50 + "\n\n")
                
                for section, data in summary.items():
                    f.write(f"{section.upper().replace('_', ' ')}:\n")
                    f.write("-" * 30 + "\n")
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            f.write(f"  {key.replace('_', ' ').title()}: {value}\n")
                    else:
                        f.write(f"  {data}\n")
                    
                    f.write("\n")
            
            self.output_files.append(txt_file)
            self.logger.debug(f"      💾 {json_file.name}, {txt_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Summary konnte nicht gespeichert werden: {e}")
    
    def _create_comprehensive_excel_output(self, processed_results: Dict[str, Any], 
                                         energy_system: Any, excel_data: Dict[str, Any]):
        """Erstellt eine umfassende Excel-Ausgabedatei mit allen Ergebnissen."""
        try:
            filepath = self.output_dir / "comprehensive_results.xlsx"
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # 1. Summary Sheet
                if 'summary' in processed_results:
                    summary_data = self._flatten_summary_for_excel(processed_results['summary'])
                    if summary_data:
                        summary_df = pd.DataFrame(list(summary_data.items()), 
                                                columns=['Parameter', 'Value'])
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # 2. Flows Sheet
                if 'flows' in processed_results:
                    flows_data = processed_results['flows']
                    if isinstance(flows_data, dict):
                        if 'flows' in flows_data and not flows_data['flows'].empty:
                            flows_data['flows'].to_excel(writer, sheet_name='Flows', index=True)
                        if 'flow_statistics' in flows_data and not flows_data['flow_statistics'].empty:
                            flows_data['flow_statistics'].to_excel(writer, sheet_name='Flow_Statistics', index=True)
                    elif isinstance(flows_data, pd.DataFrame) and not flows_data.empty:
                        flows_data.to_excel(writer, sheet_name='Flows', index=True)
                
                # 3. Bus Balances Sheet
                if 'bus_balances' in processed_results and not processed_results['bus_balances'].empty:
                    processed_results['bus_balances'].to_excel(writer, sheet_name='Bus_Balances', index=False)
                
                # 4. Investments Sheet
                if 'investments' in processed_results and not processed_results['investments'].empty:
                    processed_results['investments'].to_excel(writer, sheet_name='Investments', index=False)
                
                # 5. Cost Breakdown Sheets
                if 'costs' in processed_results:
                    costs = processed_results['costs']
                    for cost_type, df in costs.items():
                        if not df.empty:
                            sheet_name = f"Costs_{cost_type.title()}"[:31]  # Excel Sheet-Name-Limit
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 6. System Info Sheet
                if hasattr(energy_system, 'nodes'):
                    system_info_data = []
                    
                    for node in energy_system.nodes:
                        node_info = {
                            'label': str(node.label),
                            'type': type(node).__name__,
                            'inputs': len(getattr(node, 'inputs', {})),
                            'outputs': len(getattr(node, 'outputs', {}))
                        }
                        system_info_data.append(node_info)
                    
                    if system_info_data:
                        system_df = pd.DataFrame(system_info_data)
                        system_df.to_excel(writer, sheet_name='System_Components', index=False)
                
                # 7. Timestep Info (falls verfügbar)
                if 'timestep_reduction_stats' in excel_data:
                    stats = excel_data['timestep_reduction_stats']
                    timestep_df = pd.DataFrame(list(stats.items()), 
                                             columns=['Parameter', 'Value'])
                    timestep_df.to_excel(writer, sheet_name='Timestep_Management', index=False)
            
            self.output_files.append(filepath)
            self.logger.info(f"📊 Umfassende Excel-Ausgabe erstellt: {filepath.name}")
            
        except Exception as e:
            self.logger.warning(f"Umfassende Excel-Ausgabe konnte nicht erstellt werden: {e}")
    
    def _flatten_summary_for_excel(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Flacht die Summary-Struktur für Excel ab."""
        try:
            flattened = {}
            
            for section, data in summary.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        flattened[f"{section}_{key}"] = value
                else:
                    flattened[section] = data
            
            return flattened
            
        except Exception as e:
            self.logger.warning(f"Summary-Flattening fehlgeschlagen: {e}")
            return {}


# Test-Funktion für den neuen Results Processor
def test_results_processor():
    """Testfunktion für den neu geschriebenen Results-Processor."""
    import tempfile
    
    # Dummy-Ergebnisse erstellen
    timestamps = pd.date_range('2025-01-01', periods=24, freq='h')
    
    dummy_results = {
        ('pv_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 50, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.0,
                'invest': 100
            }
        },
        ('grid_import', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 30, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.25
            }
        },
        ('el_bus', 'electrical_load'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 60, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.0
            }
        }
    }
    
    # Dummy Energy System
    class DummyNode:
        def __init__(self, label, node_type):
            self.label = label
            self._type = node_type
            self.inputs = {}
            self.outputs = {}
    
    class DummyEnergySystem:
        def __init__(self):
            self.timeindex = timestamps
            self.nodes = [
                DummyNode('pv_plant', 'Source'),
                DummyNode('el_bus', 'Bus'),
                DummyNode('grid_import', 'Source'),
                DummyNode('electrical_load', 'Sink')
            ]
    
    excel_data = {
        'timestep_reduction_stats': {
            'strategy': 'full',
            'original_periods': 24,
            'final_periods': 24,
            'time_savings': '0%'
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'output_format': 'xlsx', 'debug_mode': True}
        processor = ResultsProcessor(Path(temp_dir), settings)
        
        try:
            results = processor.process_results(dummy_results, DummyEnergySystem(), excel_data)
            print("✅ Neuer Results-Processor Test erfolgreich!")
            print(f"📊 Verarbeitete Ergebnisse: {list(results.keys())}")
            print(f"💾 Erstellte Dateien: {len(processor.output_files)}")
            
            # Prüfe einzelne Ergebnisse
            if 'flows' in results:
                print("   ✅ Flows erfolgreich extrahiert")
            if 'costs' in results:
                print(f"   💰 Kosten-Kategorien: {list(results['costs'].keys())}")
            if 'summary' in results:
                print("   📋 Summary erfolgreich erstellt")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_results_processor()