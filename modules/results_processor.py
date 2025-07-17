#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Results Processor
===================================

Verarbeitet Optimierungsergebnisse und erstellt strukturierte Excel-Ausgaben.
Fokussiert auf die wichtigsten Ergebnisse: Flows, Kapazitäten, Erzeugung, Vollbenutzungsstunden.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging


class ResultsProcessor:
    """
    Verarbeitet oemof.solph Optimierungsergebnisse und erstellt Excel-Ausgaben.
    
    Hauptfunktionen:
    - Alle Flows mit Ursprung und Ziel
    - Installierte Kapazitäten
    - Summe der Erzeugung je Node
    - Vollbenutzungsstunden je Node
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
        
        # 5. Excel-Datei erstellen
        self.logger.info("   📄 Erstelle Excel-Ausgabe...")
        excel_file = self._create_excel_output(flows_df, capacity_df, generation_df, utilization_df)
        
        # Ergebnisse zusammenstellen
        processed_results = {
            'flows': flows_df,
            'capacities': capacity_df,
            'generation': generation_df,
            'utilization': utilization_df,
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
    
    def _create_excel_output(self, flows_df: pd.DataFrame, 
                           capacity_df: pd.DataFrame,
                           generation_df: pd.DataFrame,
                           utilization_df: pd.DataFrame) -> Path:
        """
        Erstellt eine Excel-Datei mit allen Ergebnissen.
        
        Args:
            flows_df: Flow-Daten
            capacity_df: Kapazitätsdaten
            generation_df: Erzeugungsdaten
            utilization_df: Vollbenutzungsstunden
            
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
                    flows_pivot = flows_df.pivot_table(
                        index='timestamp',
                        columns=['source', 'target'],
                        values='flow_MW',
                        fill_value=0
                    )
                    flows_pivot.to_excel(writer, sheet_name='Flows_Pivot')
                
                # Sheet 2: Kapazitäten
                if not capacity_df.empty:
                    capacity_df.to_excel(writer, sheet_name='Capacities', index=False)
                
                # Sheet 3: Erzeugung
                if not generation_df.empty:
                    generation_df.to_excel(writer, sheet_name='Generation', index=False)
                
                # Sheet 4: Vollbenutzungsstunden
                if not utilization_df.empty:
                    utilization_df.to_excel(writer, sheet_name='Utilization', index=False)
                
                # Sheet 5: Zusammenfassung
                summary_data = self._create_summary_sheet(flows_df, capacity_df, generation_df, utilization_df)
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
                            utilization_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Erstellt eine Zusammenfassung der wichtigsten Kennzahlen.
        
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
        
        return summary_data


def test_results_processor():
    """Test-Funktion für den Results Processor."""
    import tempfile
    import numpy as np
    
    print("🧪 Teste Results Processor...")
    
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
            print(f"   📄 Excel-Datei: {results['excel_file'].name}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_results_processor()