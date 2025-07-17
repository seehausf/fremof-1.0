#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Results Processor - Mit Kosten-Analyse
=======================================================

Verarbeitet Optimierungsergebnisse und erstellt strukturierte Excel-Ausgaben.
Erweitert um umfassende Kosten-Analyse basierend auf Investment- und variablen Kosten.

Hauptfunktionen:
- Alle Flows mit Ursprung und Ziel
- Installierte Kapazitäten
- Summe der Erzeugung je Node
- Vollbenutzungsstunden je Node
- Umfassende Kosten-Analyse

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0 (mit Kosten-Analyse)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging


class ResultsProcessor:
    """
    Verarbeitet oemof.solph Optimierungsergebnisse und erstellt Excel-Ausgaben.
    
    Erweitert um umfassende Kosten-Analyse mit Investment- und variablen Kosten.
    """
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Results Processor.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationseinstellungen
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Ausgabedateien
        self.output_files = []
        
        # Ergebnisdaten
        self.flows_data = []
        self.capacity_data = []
        self.generation_data = []
        self.utilization_data = []
    
    def process_results(self, results: Dict[str, Any], 
                       energy_system: Any, 
                       excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptmethode zur Verarbeitung der Optimierungsergebnisse.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit verarbeiteten Ergebnissen
        """
        self.logger.info("📈 Verarbeite Optimierungsergebnisse...")
        
        # 1. Flows extrahieren
        self.logger.info("   📊 Extrahiere Flows...")
        flows_df = self._extract_flows(results)
        
        # 2. Kapazitäten extrahieren
        self.logger.info("   🔋 Extrahiere Kapazitäten...")
        capacity_df = self._extract_capacities(results, energy_system)
        
        # 3. Erzeugung je Node berechnen
        self.logger.info("   ⚡ Berechne Erzeugung je Node...")
        generation_df = self._calculate_generation_per_node(flows_df)
        
        # 4. Vollbenutzungsstunden berechnen
        self.logger.info("   ⏱️ Berechne Vollbenutzungsstunden...")
        utilization_df = self._calculate_utilization_hours(generation_df, capacity_df)
        
        # 5. Kosten-Analyse durchführen
        self.logger.info("   💰 Führe Kosten-Analyse durch...")
        cost_analysis = self._analyze_costs(results, energy_system, excel_data)
        
        # 6. Excel-Datei erstellen
        self.logger.info("   📄 Erstelle Excel-Ausgabe...")
        excel_file = self._create_excel_output(flows_df, capacity_df, generation_df, utilization_df, cost_analysis)
        
        # Ergebnisse zusammenstellen
        processed_results = {
            'flows': flows_df,
            'capacities': capacity_df,
            'generation': generation_df,
            'utilization': utilization_df,
            'cost_analysis': cost_analysis,
            'excel_file': excel_file
        }
        
        self.logger.info(f"✅ Ergebnisse erfolgreich verarbeitet - {len(self.output_files)} Dateien erstellt")
        
        return processed_results
    
    def _extract_flows(self, results: Dict[str, Any]) -> pd.DataFrame:
        """
        Extrahiert alle Flows mit Ursprung und Ziel.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            
        Returns:
            DataFrame mit Flow-Daten
        """
        flow_data = []
        
        for (source, target), flow_results in results.items():
            # Prüfe ob Flow-Sequenzen vorhanden sind
            if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                flow_values = flow_results['sequences']['flow']
                
                # Zeitreihen-Daten
                for timestamp, value in flow_values.items():
                    # Robuste Wert-Konvertierung
                    try:
                        flow_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        flow_value = 0.0
                    
                    flow_data.append({
                        'timestamp': timestamp,
                        'source': str(source),
                        'target': str(target),
                        'flow_MW': flow_value
                    })
        
        if flow_data:
            flows_df = pd.DataFrame(flow_data)
            
            # Zusätzliche Berechnungen
            flows_df['flow_MWh'] = flows_df['flow_MW']  # Annahme: stündliche Zeitschritte
            
            # Sortieren nach Zeitstempel
            flows_df = flows_df.sort_values(['timestamp', 'source', 'target'])
            
            return flows_df
        else:
            self.logger.warning("Keine Flow-Daten gefunden")
            return pd.DataFrame(columns=['timestamp', 'source', 'target', 'flow_MW', 'flow_MWh'])
    
    def _extract_capacities(self, results: Dict[str, Any], energy_system: Any) -> pd.DataFrame:
        """
        Extrahiert installierte Kapazitäten.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            
        Returns:
            DataFrame mit Kapazitätsdaten
        """
        capacity_data = []
        
        for (source, target), flow_results in results.items():
            # Prüfe auf Investment-Ergebnisse
            if 'scalars' in flow_results:
                scalars = flow_results['scalars']
                
                # Investment-Kapazität
                if 'invest' in scalars:
                    invest_capacity = scalars['invest']
                    # Robuste Konvertierung mit None-Check
                    try:
                        capacity_value = float(invest_capacity) if invest_capacity is not None else 0.0
                    except (ValueError, TypeError):
                        capacity_value = 0.0
                    
                    capacity_data.append({
                        'component': str(source),
                        'target': str(target),
                        'capacity_type': 'Investment',
                        'capacity_MW': capacity_value
                    })
        
        # Zusätzlich: Prüfe auf feste Kapazitäten im Energy System
        if hasattr(energy_system, 'nodes'):
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for output_node, flow_obj in node.outputs.items():
                        if hasattr(flow_obj, 'nominal_capacity'):
                            # Prüfe ob es sich um Investment oder feste Kapazität handelt
                            if not hasattr(flow_obj.nominal_capacity, 'invest'):
                                # Feste Kapazität
                                try:
                                    capacity_value = float(flow_obj.nominal_capacity)
                                    if capacity_value > 0:
                                        capacity_data.append({
                                            'component': str(node),
                                            'target': str(output_node),
                                            'capacity_type': 'Fixed',
                                            'capacity_MW': capacity_value
                                        })
                                except (ValueError, TypeError):
                                    # Ignoriere ungültige Werte
                                    pass
        
        if capacity_data:
            capacity_df = pd.DataFrame(capacity_data)
            
            # Entferne Duplikate
            capacity_df = capacity_df.drop_duplicates()
            
            # Gruppiere nach Komponente für Gesamtkapazität
            total_capacity = capacity_df.groupby('component')['capacity_MW'].sum().reset_index()
            total_capacity['capacity_type'] = 'Total'
            total_capacity['target'] = 'All'
            
            # Kombiniere Daten
            capacity_df = pd.concat([capacity_df, total_capacity], ignore_index=True)
            capacity_df = capacity_df.sort_values(['component', 'capacity_type'])
            
            return capacity_df
        else:
            self.logger.warning("Keine Kapazitätsdaten gefunden")
            return pd.DataFrame(columns=['component', 'target', 'capacity_type', 'capacity_MW'])
    
    def _calculate_generation_per_node(self, flows_df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet die Summe der Erzeugung je Node.
        
        Args:
            flows_df: DataFrame mit Flow-Daten
            
        Returns:
            DataFrame mit Erzeugungsdaten
        """
        if flows_df.empty:
            return pd.DataFrame(columns=['node', 'total_generation_MWh', 'avg_generation_MW'])
        
        # Gruppiere nach Source (Erzeuger)
        generation_summary = flows_df.groupby('source').agg({
            'flow_MWh': 'sum',
            'flow_MW': 'mean'
        }).reset_index()
        
        generation_summary.columns = ['node', 'total_generation_MWh', 'avg_generation_MW']
        
        # Sortiere nach Gesamterzeugung
        generation_summary = generation_summary.sort_values('total_generation_MWh', ascending=False)
        
        return generation_summary
    
    def _calculate_utilization_hours(self, generation_df: pd.DataFrame, 
                                   capacity_df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet die Vollbenutzungsstunden je Node.
        
        Args:
            generation_df: DataFrame mit Erzeugungsdaten
            capacity_df: DataFrame mit Kapazitätsdaten
            
        Returns:
            DataFrame mit Vollbenutzungsstunden
        """
        if generation_df.empty or capacity_df.empty:
            return pd.DataFrame(columns=['node', 'capacity_MW', 'generation_MWh', 'utilization_hours'])
        
        # Nur Total-Kapazitäten verwenden
        total_capacities = capacity_df[capacity_df['capacity_type'] == 'Total'].copy()
        
        if total_capacities.empty:
            self.logger.warning("Keine Gesamtkapazitäten gefunden")
            return pd.DataFrame(columns=['node', 'capacity_MW', 'generation_MWh', 'utilization_hours'])
        
        # Merge Generation und Kapazität
        utilization_data = []
        
        for _, gen_row in generation_df.iterrows():
            node = gen_row['node']
            generation_mwh = gen_row['total_generation_MWh']
            
            # Suche entsprechende Kapazität
            capacity_row = total_capacities[total_capacities['component'] == node]
            
            if not capacity_row.empty:
                capacity_mw = capacity_row.iloc[0]['capacity_MW']
                
                # Berechne Vollbenutzungsstunden mit robuster Behandlung
                try:
                    if capacity_mw > 0 and generation_mwh > 0:
                        utilization_hours = float(generation_mwh) / float(capacity_mw)
                    else:
                        utilization_hours = 0.0
                except (ValueError, TypeError, ZeroDivisionError):
                    utilization_hours = 0.0
                
                utilization_data.append({
                    'node': node,
                    'capacity_MW': capacity_mw,
                    'generation_MWh': generation_mwh,
                    'utilization_hours': utilization_hours
                })
        
        if utilization_data:
            utilization_df = pd.DataFrame(utilization_data)
            utilization_df = utilization_df.sort_values('utilization_hours', ascending=False)
            return utilization_df
        else:
            return pd.DataFrame(columns=['node', 'capacity_MW', 'generation_MWh', 'utilization_hours'])
    
    def _analyze_costs(self, results: Dict[str, Any], 
                      energy_system: Any, 
                      excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt eine umfassende Kosten-Analyse durch.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit Kosten-Analyse
        """
        try:
            # CostAnalyzer importieren und verwenden
            from .cost_analyzer import CostAnalyzer
            
            settings = {
                'power_unit': 'MW',
                'energy_unit': 'MWh', 
                'currency_unit': '€',
                'time_increment': 1,
                'debug_mode': self.settings.get('debug_mode', False)
            }
            
            analyzer = CostAnalyzer(self.output_dir, settings)
            cost_analysis = analyzer.analyze_costs(results, energy_system, excel_data)
            
            return cost_analysis
            
        except ImportError:
            # Fallback: Einfache Kosten-Berechnung
            self.logger.warning("CostAnalyzer nicht verfügbar - verwende einfache Kosten-Berechnung")
            return self._simple_cost_calculation(results, energy_system)
        except Exception as e:
            self.logger.error(f"Fehler bei Kosten-Analyse: {e}")
            return self._simple_cost_calculation(results, energy_system)
    
    def _simple_cost_calculation(self, results: Dict[str, Any], 
                                energy_system: Any) -> Dict[str, Any]:
        """
        Einfache Kosten-Berechnung als Fallback.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            
        Returns:
            Dictionary mit einfacher Kosten-Analyse
        """
        total_investment = 0
        total_variable = 0
        
        try:
            # Einfache Investment-Kosten
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for target_node, flow in node.outputs.items():
                        if hasattr(flow, 'investment') and flow.investment is not None:
                            source_label = str(node.label)
                            target_label = str(target_node.label)
                            
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'scalars' in flow_results and 'invest' in flow_results['scalars']:
                                        invested_capacity = flow_results['scalars']['invest']
                                        
                                        # Vereinfachte EP-Costs
                                        ep_costs = 100  # Default-Wert
                                        if hasattr(flow.investment, 'ep_costs'):
                                            ep_costs_attr = flow.investment.ep_costs
                                            if hasattr(ep_costs_attr, 'tolist'):
                                                ep_costs = ep_costs_attr.tolist()[0]
                                            else:
                                                ep_costs = float(ep_costs_attr)
                                        
                                        total_investment += ep_costs * invested_capacity
            
            # Einfache variable Kosten
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_sequence = flow_results['sequences']['flow']
                    total_energy = flow_sequence.sum()
                    
                    # Vereinfachte variable Kosten (z.B. aus Excel-Daten)
                    var_cost = 0.1  # Default-Wert
                    total_variable += var_cost * total_energy
        
        except Exception as e:
            self.logger.warning(f"Fehler bei einfacher Kosten-Berechnung: {e}")
        
        return {
            'cost_summary': {
                'total_costs': total_investment + total_variable,
                'investment_costs': total_investment,
                'variable_costs': total_variable,
                'investment_share': total_investment / (total_investment + total_variable) if (total_investment + total_variable) > 0 else 0,
                'variable_share': total_variable / (total_investment + total_variable) if (total_investment + total_variable) > 0 else 0,
                'avg_hourly_costs': 0,
                'max_hourly_costs': 0,
                'currency_unit': '€'
            },
            'investment_costs': pd.DataFrame(),
            'variable_costs': pd.DataFrame(),
            'hourly_costs': pd.DataFrame(),
            'technology_costs': {},
            'utilization_costs': pd.DataFrame(),
            'total_system_costs': total_investment + total_variable
        }
    
    def _create_excel_output(self, flows_df: pd.DataFrame, 
                           capacity_df: pd.DataFrame,
                           generation_df: pd.DataFrame,
                           utilization_df: pd.DataFrame,
                           cost_analysis: Dict[str, Any]) -> Path:
        """
        Erstellt eine Excel-Datei mit allen Ergebnissen inkl. Kosten-Analyse.
        
        Args:
            flows_df: Flow-Daten
            capacity_df: Kapazitätsdaten
            generation_df: Erzeugungsdaten
            utilization_df: Vollbenutzungsstunden
            cost_analysis: Kosten-Analyse
            
        Returns:
            Pfad zur erstellten Excel-Datei
        """
        excel_file = self.output_dir / "optimization_results.xlsx"
        
        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Sheet 1: Flows
                if not flows_df.empty:
                    flows_df.to_excel(writer, sheet_name='Flows', index=False)
                    
                    # Pivot-Tabelle für bessere Übersicht
                    try:
                        flows_pivot = flows_df.pivot_table(
                            index='timestamp',
                            columns=['source', 'target'],
                            values='flow_MW',
                            fill_value=0
                        )
                        flows_pivot.to_excel(writer, sheet_name='Flows_Pivot')
                    except Exception as e:
                        self.logger.warning(f"Flows-Pivot konnte nicht erstellt werden: {e}")
                
                # Sheet 2: Kapazitäten
                if not capacity_df.empty:
                    capacity_df.to_excel(writer, sheet_name='Capacities', index=False)
                
                # Sheet 3: Erzeugung
                if not generation_df.empty:
                    generation_df.to_excel(writer, sheet_name='Generation', index=False)
                
                # Sheet 4: Vollbenutzungsstunden
                if not utilization_df.empty:
                    utilization_df.to_excel(writer, sheet_name='Utilization', index=False)
                
                # Sheet 5: Kosten-Zusammenfassung
                cost_summary = cost_analysis['cost_summary']
                summary_data = [
                    ['Gesamtkosten', f"{cost_summary['total_costs']:.2f}", cost_summary['currency_unit']],
                    ['Investment-Kosten', f"{cost_summary['investment_costs']:.2f}", cost_summary['currency_unit']],
                    ['Variable Kosten', f"{cost_summary['variable_costs']:.2f}", cost_summary['currency_unit']],
                    ['Investment-Anteil', f"{cost_summary['investment_share']:.1%}", ''],
                    ['Variable-Anteil', f"{cost_summary['variable_share']:.1%}", ''],
                    ['Ø Stündliche Kosten', f"{cost_summary['avg_hourly_costs']:.2f}", cost_summary['currency_unit']],
                    ['Max Stündliche Kosten', f"{cost_summary['max_hourly_costs']:.2f}", cost_summary['currency_unit']]
                ]
                
                cost_summary_df = pd.DataFrame(summary_data, columns=['Kategorie', 'Wert', 'Einheit'])
                cost_summary_df.to_excel(writer, sheet_name='Cost_Summary', index=False)
                
                # Sheet 6: Investment-Kosten (falls vorhanden)
                investment_costs = cost_analysis['investment_costs']
                if not investment_costs.empty:
                    investment_costs.to_excel(writer, sheet_name='Investment_Costs', index=False)
                
                # Sheet 7: Variable Kosten (falls vorhanden)
                variable_costs = cost_analysis['variable_costs']
                if not variable_costs.empty:
                    variable_costs.to_excel(writer, sheet_name='Variable_Costs', index=False)
                
                # Sheet 8: Stündliche Kosten (falls vorhanden)
                hourly_costs = cost_analysis['hourly_costs']
                if not hourly_costs.empty:
                    hourly_costs.to_excel(writer, sheet_name='Hourly_Costs')
                
                # Sheet 9: Technologie-Kosten (falls vorhanden)
                tech_costs = cost_analysis['technology_costs']
                if tech_costs:
                    tech_df = pd.DataFrame(tech_costs).T
                    tech_df.to_excel(writer, sheet_name='Technology_Costs')
                
                # Sheet 10: Vollbenutzungsstunden-Kosten (falls vorhanden)
                utilization_costs = cost_analysis['utilization_costs']
                if not utilization_costs.empty:
                    utilization_costs.to_excel(writer, sheet_name='Utilization_Costs', index=False)
                
                # Sheet 11: Allgemeine Zusammenfassung
                summary_data = self._create_summary_sheet(flows_df, capacity_df, generation_df, utilization_df, cost_analysis)
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            self.output_files.append(excel_file)
            self.logger.info(f"   📄 Excel-Datei erstellt: {excel_file.name}")
            
            return excel_file
            
        except Exception as e:
            self.logger.error(f"Fehler beim Erstellen der Excel-Datei: {e}")
            raise
    
    def _create_summary_sheet(self, flows_df: pd.DataFrame, 
                            capacity_df: pd.DataFrame,
                            generation_df: pd.DataFrame,
                            utilization_df: pd.DataFrame,
                            cost_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Erstellt eine Zusammenfassung der wichtigsten Kennzahlen inkl. Kosten.
        
        Returns:
            Liste mit Zusammenfassungsdaten
        """
        summary_data = []
        
        # Allgemeine Statistiken
        summary_data.append({'Kategorie': 'Allgemein', 'Parameter': 'Anzahl Flows', 'Wert': len(flows_df)})
        summary_data.append({'Kategorie': 'Allgemein', 'Parameter': 'Anzahl Komponenten', 'Wert': len(capacity_df)})
        summary_data.append({'Kategorie': 'Allgemein', 'Parameter': 'Simulationszeitraum (h)', 'Wert': flows_df['timestamp'].nunique() if not flows_df.empty else 0})
        
        # Kapazitäts-Statistiken
        if not capacity_df.empty:
            total_capacity = capacity_df[capacity_df['capacity_type'] == 'Total']['capacity_MW'].sum()
            summary_data.append({'Kategorie': 'Kapazität', 'Parameter': 'Gesamtkapazität (MW)', 'Wert': round(total_capacity, 2)})
        
        # Erzeugungs-Statistiken
        if not generation_df.empty:
            total_generation = generation_df['total_generation_MWh'].sum()
            summary_data.append({'Kategorie': 'Erzeugung', 'Parameter': 'Gesamterzeugung (MWh)', 'Wert': round(total_generation, 2)})
            
            max_generator = generation_df.iloc[0] if not generation_df.empty else None
            if max_generator is not None:
                summary_data.append({'Kategorie': 'Erzeugung', 'Parameter': 'Größter Erzeuger', 'Wert': max_generator['node']})
                summary_data.append({'Kategorie': 'Erzeugung', 'Parameter': 'Größter Erzeuger (MWh)', 'Wert': round(max_generator['total_generation_MWh'], 2)})
        
        # Vollbenutzungsstunden-Statistiken
        if not utilization_df.empty:
            avg_utilization = utilization_df['utilization_hours'].mean()
            max_utilization = utilization_df['utilization_hours'].max()
            summary_data.append({'Kategorie': 'Vollbenutzung', 'Parameter': 'Durchschnittliche VBH (h)', 'Wert': round(avg_utilization, 1)})
            summary_data.append({'Kategorie': 'Vollbenutzung', 'Parameter': 'Maximale VBH (h)', 'Wert': round(max_utilization, 1)})
        
        # Kosten-Statistiken
        cost_summary = cost_analysis['cost_summary']
        summary_data.append({'Kategorie': 'Kosten', 'Parameter': f'Gesamtkosten ({cost_summary["currency_unit"]})', 'Wert': round(cost_summary['total_costs'], 2)})
        summary_data.append({'Kategorie': 'Kosten', 'Parameter': f'Investment-Kosten ({cost_summary["currency_unit"]})', 'Wert': round(cost_summary['investment_costs'], 2)})
        summary_data.append({'Kategorie': 'Kosten', 'Parameter': f'Variable Kosten ({cost_summary["currency_unit"]})', 'Wert': round(cost_summary['variable_costs'], 2)})
        summary_data.append({'Kategorie': 'Kosten', 'Parameter': 'Investment-Anteil (%)', 'Wert': round(cost_summary['investment_share'] * 100, 1)})
        summary_data.append({'Kategorie': 'Kosten', 'Parameter': 'Variable-Anteil (%)', 'Wert': round(cost_summary['variable_share'] * 100, 1)})
        
        return summary_data


def test_results_processor():
    """Test-Funktion für den Results Processor."""
    import tempfile
    import numpy as np
    
    print("🧪 Teste Results Processor mit Kosten-Analyse...")
    
    # Dummy-Daten erstellen
    timestamps = pd.date_range('2025-01-01', periods=24, freq='h')
    
    dummy_results = {
        ('pv_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 30, index=timestamps)
            },
            'scalars': {
                'invest': 100.0
            }
        },
        ('wind_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 25, index=timestamps)
            },
            'scalars': {
                'invest': 80.0
            }
        },
        ('el_bus', 'demand'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 45, index=timestamps)
            }
        }
    }
    
    # Dummy Energy System
    class DummyInvestment:
        def __init__(self, ep_costs=100):
            self.ep_costs = ep_costs
            self.existing = 0
            self.maximum = 1000
            self.minimum = 0
    
    class DummyFlow:
        def __init__(self, has_investment=False, variable_costs=0):
            if has_investment:
                self.investment = DummyInvestment()
            self.variable_costs = variable_costs
    
    class DummyNode:
        def __init__(self, label):
            self.label = label
            self.outputs = {}
        
        def __str__(self):
            return self.label
    
    class DummyEnergySystem:
        def __init__(self):
            self.nodes = [
                DummyNode('pv_plant'),
                DummyNode('wind_plant'),
                DummyNode('el_bus'),
                DummyNode('demand')
            ]
            
            # Flows hinzufügen
            self.nodes[0].outputs[self.nodes[2]] = DummyFlow(has_investment=True, variable_costs=0.0)
            self.nodes[1].outputs[self.nodes[2]] = DummyFlow(has_investment=True, variable_costs=0.0)
            self.nodes[2].outputs[self.nodes[3]] = DummyFlow(variable_costs=0.25)
    
    # Test durchführen
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = ResultsProcessor(Path(temp_dir), {'debug_mode': True})
        energy_system = DummyEnergySystem()
        
        try:
            results = processor.process_results(dummy_results, energy_system, {})
            
            print("✅ Results Processor Test erfolgreich!")
            print(f"   📊 Flows: {len(results['flows'])} Einträge")
            print(f"   🔋 Kapazitäten: {len(results['capacities'])} Einträge")
            print(f"   ⚡ Erzeugung: {len(results['generation'])} Einträge")
            print(f"   ⏱️ Vollbenutzung: {len(results['utilization'])} Einträge")
            print(f"   💰 Kosten-Analyse: {results['cost_analysis']['cost_summary']['total_costs']:.2f} €")
            print(f"   📄 Excel-Datei: {results['excel_file'].name}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_results_processor()
