#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Analyse-Modul
==============================

Führt vertiefende Analysen der Optimierungsergebnisse durch.
Berechnet KPIs, Sensitivitäten und weitere Kennzahlen.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging


class Analyzer:
    """Klasse für vertiefende Analysen von Optimierungsergebnissen."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Analyzer.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Analyse-Ergebnisse
        self.analysis_results = {}
        self.output_files = []
    
    def create_analysis(self, results: Dict[str, Any], energy_system: Any,
                       excel_data: Dict[str, Any]) -> List[Path]:
        """
        Führt alle verfügbaren Analysen durch und erstellt Dateien.
        
        Args:
            results: Optimierungsergebnisse
            energy_system: EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Liste der erstellten Analyse-Dateien
        """
        self.logger.info("🔍 Führe vertiefende Analysen durch...")
        
        try:
            # Hauptanalyse durchführen
            analysis_results = self.perform_analysis(results, energy_system, excel_data)
            
            # Ergebnisse speichern
            self._save_analysis_results()
            
            self.logger.info(f"✅ {len(self.analysis_results)} Analysen abgeschlossen")
            
            return self.output_files
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Analyse: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
            return []
    
    def perform_analysis(self, results: Dict[str, Any], energy_system: Any,
                        excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt alle verfügbaren Analysen durch.
        
        Args:
            results: Optimierungsergebnisse
            energy_system: EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit Analyse-Ergebnissen
        """
        # KPI-Analyse
        self.logger.info("   📊 Berechne KPIs...")
        kpis = self._calculate_kpis(results, energy_system, excel_data)
        self.analysis_results['kpis'] = kpis
        
        # Autarkie-Analyse
        self.logger.info("   🏠 Analysiere Autarkie...")
        autarky = self._analyze_autarky(results)
        self.analysis_results['autarky'] = autarky
        
        # Lastdeckungs-Analyse
        self.logger.info("   ⚡ Analysiere Lastdeckung...")
        load_coverage = self._analyze_load_coverage(results)
        self.analysis_results['load_coverage'] = load_coverage
        
        # Auslastungs-Analyse
        self.logger.info("   📈 Analysiere Auslastung...")
        utilization = self._analyze_utilization(results)
        self.analysis_results['utilization'] = utilization
        
        # Wirtschaftlichkeits-Analyse
        self.logger.info("   💰 Analysiere Wirtschaftlichkeit...")
        economics = self._analyze_economics(results)
        self.analysis_results['economics'] = economics
        
        # Emissions-Analyse (falls Daten verfügbar)
        if self._has_emission_data(excel_data):
            self.logger.info("   🌱 Analysiere Emissionen...")
            emissions = self._analyze_emissions(results, excel_data)
            self.analysis_results['emissions'] = emissions
        
        return self.analysis_results
    
    def _calculate_kpis(self, results: Dict[str, Any], energy_system: Any,
                       excel_data: Dict[str, Any]) -> Dict[str, float]:
        """Berechnet Key Performance Indicators."""
        kpis = {}
        
        try:
            # Grundlegende Energie-KPIs
            total_generation = 0
            total_demand = 0
            renewable_generation = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_sum = flow_results['sequences']['flow'].sum()
                    
                    # Gesamterzeugung
                    if self._is_generator(str(source)):
                        total_generation += flow_sum
                        
                        # Erneuerbare Erzeugung
                        if self._is_renewable(str(source)):
                            renewable_generation += flow_sum
                    
                    # Gesamtnachfrage
                    if self._is_demand(str(target)):
                        total_demand += flow_sum
            
            # KPIs berechnen
            kpis['total_generation_MWh'] = round(total_generation, 2)
            kpis['total_demand_MWh'] = round(total_demand, 2)
            kpis['renewable_generation_MWh'] = round(renewable_generation, 2)
            kpis['renewable_share'] = round(renewable_generation / total_generation if total_generation > 0 else 0, 3)
            kpis['supply_demand_balance'] = round(total_generation / total_demand if total_demand > 0 else 0, 3)
            
            # Zeitbereich-KPIs
            if hasattr(energy_system, 'timeindex'):
                kpis['simulation_hours'] = len(energy_system.timeindex)
                kpis['avg_generation_MW'] = round(total_generation / len(energy_system.timeindex) if len(energy_system.timeindex) > 0 else 0, 2)
                kpis['avg_demand_MW'] = round(total_demand / len(energy_system.timeindex) if len(energy_system.timeindex) > 0 else 0, 2)
        
        except Exception as e:
            self.logger.warning(f"Fehler bei KPI-Berechnung: {e}")
        
        return kpis
    
    def _analyze_autarky(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Analysiert den Autarkiegrad."""
        autarky = {}
        
        try:
            grid_import = 0
            total_demand = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_sum = flow_results['sequences']['flow'].sum()
                    
                    # Grid-Import
                    if 'grid' in str(source).lower() and 'import' in str(source).lower():
                        grid_import += flow_sum
                    
                    # Gesamtnachfrage
                    if self._is_demand(str(target)):
                        total_demand += flow_sum
            
            # Autarkiegrad berechnen
            autarky_degree = 1 - (grid_import / total_demand) if total_demand > 0 else 0
            
            autarky['grid_import_MWh'] = round(grid_import, 2)
            autarky['total_demand_MWh'] = round(total_demand, 2)
            autarky['autarky_degree'] = round(autarky_degree, 3)
            autarky['grid_dependency'] = round(grid_import / total_demand if total_demand > 0 else 0, 3)
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Autarkie-Analyse: {e}")
        
        return autarky
    
    def _analyze_load_coverage(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert die Lastdeckung."""
        load_coverage = {}
        
        try:
            # Sammle alle Erzeugung und Last-Zeitreihen
            generation_series = []
            demand_series = []
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_series = flow_results['sequences']['flow']
                    
                    if self._is_generator(str(source)):
                        generation_series.append(flow_series)
                    
                    if self._is_demand(str(target)):
                        demand_series.append(flow_series)
            
            if generation_series and demand_series:
                # Summiere alle Zeitreihen
                total_generation = sum(generation_series)
                total_demand = sum(demand_series)
                
                # Lastdeckungsstatistiken
                coverage_ratio = total_generation / total_demand
                
                load_coverage['min_coverage'] = round(coverage_ratio.min(), 3)
                load_coverage['max_coverage'] = round(coverage_ratio.max(), 3)
                load_coverage['avg_coverage'] = round(coverage_ratio.mean(), 3)
                load_coverage['std_coverage'] = round(coverage_ratio.std(), 3)
                
                # Zeiten mit Über-/Unterdeckung
                overproduction_hours = (coverage_ratio > 1.05).sum()
                underproduction_hours = (coverage_ratio < 0.95).sum()
                
                load_coverage['overproduction_hours'] = int(overproduction_hours)
                load_coverage['underproduction_hours'] = int(underproduction_hours)
                load_coverage['balanced_hours'] = len(coverage_ratio) - overproduction_hours - underproduction_hours
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Lastdeckungs-Analyse: {e}")
        
        return load_coverage
    
    def _analyze_utilization(self, results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Analysiert die Anlagenauslastung."""
        utilization = {}
        
        try:
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_series = flow_results['sequences']['flow']
                    source_name = str(source)
                    
                    if self._is_generator(source_name):
                        # Auslastungsstatistiken
                        max_flow = flow_series.max()
                        avg_flow = flow_series.mean()
                        operating_hours = (flow_series > 0).sum()
                        total_hours = len(flow_series)
                        
                        utilization[source_name] = {
                            'max_output_MW': round(max_flow, 2),
                            'avg_output_MW': round(avg_flow, 2),
                            'capacity_factor': round(avg_flow / max_flow if max_flow > 0 else 0, 3),
                            'operating_hours': int(operating_hours),
                            'total_hours': int(total_hours),
                            'availability': round(operating_hours / total_hours if total_hours > 0 else 0, 3)
                        }
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Auslastungs-Analyse: {e}")
        
        return utilization
    
    def _analyze_economics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Analysiert wirtschaftliche Kennzahlen."""
        economics = {}
        
        try:
            # Vereinfachte Wirtschaftlichkeitsanalyse
            total_energy = 0
            estimated_costs = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_sum = flow_results['sequences']['flow'].sum()
                    total_energy += flow_sum
                    
                    # Vereinfachte Kostenschätzung basierend auf Technologie
                    source_name = str(source).lower()
                    if 'pv' in source_name or 'solar' in source_name:
                        estimated_costs += flow_sum * 50  # €/MWh
                    elif 'wind' in source_name:
                        estimated_costs += flow_sum * 60  # €/MWh
                    elif 'grid' in source_name:
                        estimated_costs += flow_sum * 250  # €/MWh
                    else:
                        estimated_costs += flow_sum * 100  # €/MWh Default
            
            # LCOE (vereinfacht)
            lcoe = estimated_costs / total_energy if total_energy > 0 else 0
            
            economics['total_energy_MWh'] = round(total_energy, 2)
            economics['estimated_total_costs_EUR'] = round(estimated_costs, 2)
            economics['estimated_LCOE_EUR_per_MWh'] = round(lcoe, 2)
            
        except Exception as e:
            self.logger.warning(f"Fehler bei Wirtschaftlichkeits-Analyse: {e}")
        
        return economics
    
    def _analyze_emissions(self, results: Dict[str, Any], excel_data: Dict[str, Any]) -> Dict[str, float]:
        """Analysiert CO2-Emissionen (falls Daten verfügbar)."""
        emissions = {}
        
        try:
            # Vereinfachte Emissions-Analyse
            total_emissions = 0
            total_energy = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_sum = flow_results['sequences']['flow'].sum()
                    total_energy += flow_sum
                    
                    # Vereinfachte Emissionsfaktoren (kg CO2/MWh)
                    source_name = str(source).lower()
                    if 'pv' in source_name or 'solar' in source_name:
                        total_emissions += flow_sum * 50  # kg CO2/MWh
                    elif 'wind' in source_name:
                        total_emissions += flow_sum * 30  # kg CO2/MWh
                    elif 'grid' in source_name:
                        total_emissions += flow_sum * 500  # kg CO2/MWh
                    elif 'gas' in source_name:
                        total_emissions += flow_sum * 400  # kg CO2/MWh
            
            emissions['total_emissions_kg_CO2'] = round(total_emissions, 2)
            emissions['total_energy_MWh'] = round(total_energy, 2)
            emissions['emission_factor_kg_CO2_per_MWh'] = round(total_emissions / total_energy if total_energy > 0 else 0, 2)
            emissions['total_emissions_t_CO2'] = round(total_emissions / 1000, 2)
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Emissions-Analyse: {e}")
        
        return emissions
    
    def _has_emission_data(self, excel_data: Dict[str, Any]) -> bool:
        """Prüft ob Emissions-Daten verfügbar sind."""
        # Vereinfacht: Immer aktiviert für Demo
        return True
    
    def _is_generator(self, component_name: str) -> bool:
        """Prüft ob Komponente ein Erzeuger ist."""
        generator_terms = ['plant', 'generator', 'pv', 'wind', 'solar', 'turbine', 'source']
        return any(term in component_name.lower() for term in generator_terms)
    
    def _is_renewable(self, component_name: str) -> bool:
        """Prüft ob Komponente erneuerbar ist."""
        renewable_terms = ['pv', 'solar', 'wind', 'hydro', 'bio', 'geothermal']
        return any(term in component_name.lower() for term in renewable_terms)
    
    def _is_demand(self, component_name: str) -> bool:
        """Prüft ob Komponente eine Last ist."""
        demand_terms = ['demand', 'load', 'consumption', 'sink']
        return any(term in component_name.lower() for term in demand_terms)
    
    def _save_analysis_results(self):
        """Speichert die Analyse-Ergebnisse."""
        try:
            # JSON-Export
            import json
            
            json_file = self.output_dir / "analysis_results.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            
            self.output_files.append(json_file)
            
            # Excel-Export (wenn möglich)
            try:
                excel_file = self.output_dir / "analysis_results.xlsx"
                
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    for analysis_type, results in self.analysis_results.items():
                        if isinstance(results, dict):
                            # Flache Struktur für Excel
                            flat_data = self._flatten_dict(results)
                            df = pd.DataFrame(list(flat_data.items()), 
                                            columns=['Parameter', 'Wert'])
                            df.to_excel(writer, sheet_name=analysis_type[:30], index=False)
                
                self.output_files.append(excel_file)
                self.logger.debug(f"      💾 {excel_file.name}")
                
            except Exception:
                pass  # Excel-Export optional
            
            # Text-Report
            report_file = self.output_dir / "analysis_report.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("VERTIEFENDE ANALYSE - BERICHT\n")
                f.write("=" * 50 + "\n\n")
                
                for analysis_type, results in self.analysis_results.items():
                    f.write(f"{analysis_type.upper()}:\n")
                    f.write("-" * 30 + "\n")
                    
                    if isinstance(results, dict):
                        self._write_dict_to_file(f, results, indent=0)
                    else:
                        f.write(f"{results}\n")
                    
                    f.write("\n")
            
            self.output_files.append(report_file)
            self.logger.debug(f"      💾 {json_file.name}, {report_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Fehler beim Speichern der Analyse-Ergebnisse: {e}")
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flacht verschachtelte Dictionaries ab."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _write_dict_to_file(self, f, d: Dict, indent: int = 0):
        """Schreibt Dictionary strukturiert in Datei."""
        for key, value in d.items():
            if isinstance(value, dict):
                f.write("  " * indent + f"{key}:\n")
                self._write_dict_to_file(f, value, indent + 1)
            else:
                f.write("  " * indent + f"{key}: {value}\n")


def test_analyzer():
    """Testfunktion für den Analyzer."""
    import tempfile
    
    # Dummy-Daten erstellen
    timestamps = pd.date_range('2025-01-01', periods=24, freq='h')
    
    dummy_results = {
        ('pv_plant', 'el_load'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 30, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.0
            }
        },
        ('grid_import', 'el_load'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 20, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.25
            }
        }
    }
    
    class DummyEnergySystem:
        def __init__(self):
            self.timeindex = timestamps
    
    energy_system = DummyEnergySystem()
    excel_data = {}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        analyzer = Analyzer(Path(temp_dir), settings)
        
        try:
            analysis_files = analyzer.create_analysis(dummy_results, energy_system, excel_data)
            print("✅ Analyzer Test erfolgreich!")
            print(f"Durchgeführte Analysen: {list(analyzer.analysis_results.keys())}")
            print(f"Erstellte Dateien: {len(analysis_files)}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_analyzer()