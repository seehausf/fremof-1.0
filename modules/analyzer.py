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
        self.logger.info("🔍 Führe vertiefende Analysen durch...")
        
        # KPI-Analyse
        kpis = self._calculate_kpis(results, energy_system, excel_data)
        self.analysis_results['kpis'] = kpis
        
        # Autarkie-Analyse
        autarky = self._analyze_autarky(results)
        self.analysis_results['autarky'] = autarky
        
        # Lastdeckungs-Analyse
        load_coverage = self._analyze_load_coverage(results)
        self.analysis_results['load_coverage'] = load_coverage
        
        # Auslastungs-Analyse
        utilization = self._analyze_utilization(results)
        self.analysis_results['utilization'] = utilization
        
        # Emissions-Analyse (falls Daten verfügbar)
        if self._has_emission_data(excel_data):
            emissions = self._analyze_emissions(results, excel_data)
            self.analysis_results['emissions'] = emissions
        
        # Wirtschaftlichkeits-Analyse
        economics = self._analyze_economics(results)
        self.analysis_results['economics'] = economics
        
        # Ergebnisse speichern
        self._save_analysis_results()
        
        self.logger.info(f"✅ {len(self.analysis_results)} Analysen abgeschlossen")
        
        return self.analysis_results
    
    def _calculate_kpis(self, results: Dict[str, Any], energy_system: Any,
                       excel_data: Dict[str, Any]) -> Dict[str, float]:
        """Berechnet Key Performance Indicators."""
        kpis = {}
        
        try:
            # Gesamtenergie-Flows
            total_energy = 0
            peak_power = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    total_energy += flow_values.sum()
                    peak_power = max(peak_power, flow_values.max())
            
            kpis['total_energy_kwh'] = total_energy
            kpis['peak_power_kw'] = peak_power
            
            # Zeitbasierte KPIs
            if hasattr(energy_system, 'timeindex'):
                simulation_hours = len(energy_system.timeindex)
                kpis['simulation_duration_h'] = simulation_hours
                
                if simulation_hours > 0:
                    kpis['average_power_kw'] = total_energy / simulation_hours
                    kpis['load_factor'] = (total_energy / simulation_hours) / peak_power if peak_power > 0 else 0
            
            # Renewable Energy Share (vereinfacht)
            renewable_energy = 0
            total_generation = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    energy = flow_values.sum()
                    
                    # Vereinfachte Erkennung erneuerbarer Quellen
                    if any(keyword in str(source).lower() for keyword in ['pv', 'wind', 'solar', 'hydro']):
                        renewable_energy += energy
                    
                    # Nur Generatoren zählen (nicht interne Flows)
                    if 'bus' in str(target).lower():
                        total_generation += energy
            
            if total_generation > 0:
                kpis['renewable_share'] = renewable_energy / total_generation
            else:
                kpis['renewable_share'] = 0
            
            # Anzahl aktiver Zeitstunden
            active_hours = 0
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    active_hours = max(active_hours, (flow_values > 0).sum())
            
            kpis['active_hours'] = active_hours
            
        except Exception as e:
            self.logger.warning(f"KPI-Berechnung fehlgeschlagen: {e}")
        
        return kpis
    
    def _analyze_autarky(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Analysiert den Autarkiegrad des Systems."""
        autarky = {}
        
        try:
            # Grid-Import und Export identifizieren
            grid_import = 0
            grid_export = 0
            total_demand = 0
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    energy = flow_values.sum()
                    
                    # Grid-Flows identifizieren
                    if 'grid' in str(source).lower() and 'import' in str(source).lower():
                        grid_import += energy
                    elif 'grid' in str(target).lower() and 'export' in str(target).lower():
                        grid_export += energy
                    
                    # Demand identifizieren
                    if any(keyword in str(target).lower() for keyword in ['load', 'demand', 'sink']):
                        if 'grid' not in str(target).lower():
                            total_demand += energy
            
            # Autarkiegrad berechnen
            if total_demand > 0:
                autarky['autarky_rate'] = max(0, (total_demand - grid_import) / total_demand)
            else:
                autarky['autarky_rate'] = 0
            
            # Eigenverbrauchsrate
            own_generation = total_demand + grid_export - grid_import
            if own_generation > 0:
                autarky['self_consumption_rate'] = (total_demand - grid_import) / own_generation
            else:
                autarky['self_consumption_rate'] = 0
            
            autarky['grid_import_kwh'] = grid_import
            autarky['grid_export_kwh'] = grid_export
            autarky['total_demand_kwh'] = total_demand
            
        except Exception as e:
            self.logger.warning(f"Autarkie-Analyse fehlgeschlagen: {e}")
        
        return autarky
    
    def _analyze_load_coverage(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert die Lastdeckung durch verschiedene Quellen."""
        load_coverage = {}
        
        try:
            # Alle Flows zu Lasten sammeln
            load_flows = {}
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    # Load/Demand/Sink als Ziel identifizieren
                    if any(keyword in str(target).lower() for keyword in ['load', 'demand', 'sink']):
                        if 'grid' not in str(target).lower():  # Grid-Export ausschließen
                            flow_values = flow_results['sequences']['flow']
                            load_flows[str(source)] = flow_values.sum()
            
            if load_flows:
                total_load = sum(load_flows.values())
                
                # Prozentuale Anteile berechnen
                load_shares = {}
                for source, energy in load_flows.items():
                    share = (energy / total_load) if total_load > 0 else 0
                    load_shares[source] = {
                        'energy_kwh': energy,
                        'share_percent': share * 100
                    }
                
                load_coverage['total_load_kwh'] = total_load
                load_coverage['source_shares'] = load_shares
                
                # Top-3 Quellen
                sorted_sources = sorted(load_shares.items(), 
                                      key=lambda x: x[1]['energy_kwh'], 
                                      reverse=True)
                load_coverage['top_sources'] = dict(sorted_sources[:3])
            
        except Exception as e:
            self.logger.warning(f"Lastdeckungs-Analyse fehlgeschlagen: {e}")
        
        return load_coverage
    
    def _analyze_utilization(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert die Auslastung von Komponenten."""
        utilization = {}
        
        try:
            component_utilization = {}
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    
                    if len(flow_values) > 0:
                        max_flow = flow_values.max()
                        avg_flow = flow_values.mean()
                        
                        # Auslastung berechnen
                        if max_flow > 0:
                            avg_utilization = avg_flow / max_flow
                            
                            # Volllaststunden
                            full_load_hours = flow_values.sum() / max_flow if max_flow > 0 else 0
                            
                            component_utilization[f"{source} → {target}"] = {
                                'max_flow_kw': max_flow,
                                'avg_flow_kw': avg_flow,
                                'avg_utilization': avg_utilization,
                                'full_load_hours': full_load_hours,
                                'operating_hours': (flow_values > 0).sum()
                            }
            
            # Nach Auslastung sortieren
            sorted_utilization = dict(sorted(component_utilization.items(),
                                           key=lambda x: x[1]['avg_utilization'],
                                           reverse=True))
            
            utilization['component_utilization'] = sorted_utilization
            
            # Durchschnittliche Systemauslastung
            if component_utilization:
                avg_system_utilization = np.mean([
                    comp['avg_utilization'] for comp in component_utilization.values()
                ])
                utilization['average_system_utilization'] = avg_system_utilization
            
        except Exception as e:
            self.logger.warning(f"Auslastungs-Analyse fehlgeschlagen: {e}")
        
        return utilization
    
    def _has_emission_data(self, excel_data: Dict[str, Any]) -> bool:
        """Prüft ob Emissionsdaten verfügbar sind."""
        # Vereinfachte Prüfung auf Emissions-Spalten
        for sheet_name, df in excel_data.items():
            if isinstance(df, pd.DataFrame):
                if any('emission' in str(col).lower() for col in df.columns):
                    return True
        return False
    
    def _analyze_emissions(self, results: Dict[str, Any], excel_data: Dict[str, Any]) -> Dict[str, float]:
        """Analysiert CO2-Emissionen (vereinfacht)."""
        emissions = {}
        
        try:
            # Standard-Emissionsfaktoren (kg CO2/kWh)
            emission_factors = {
                'grid': 0.4,      # Netz-Strommix
                'gas': 0.2,       # Erdgas
                'coal': 0.8,      # Kohle
                'oil': 0.7,       # Öl
                'pv': 0.05,       # PV (Lifecycle)
                'wind': 0.02,     # Wind (Lifecycle)
                'hydro': 0.01     # Wasserkraft
            }
            
            total_emissions = 0
            source_emissions = {}
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    energy = flow_values.sum()
                    
                    # Emissionsfaktor bestimmen
                    emission_factor = 0
                    source_str = str(source).lower()
                    
                    for fuel_type, factor in emission_factors.items():
                        if fuel_type in source_str:
                            emission_factor = factor
                            break
                    
                    # Emissionen berechnen
                    component_emissions = energy * emission_factor
                    total_emissions += component_emissions
                    
                    if component_emissions > 0:
                        source_emissions[str(source)] = {
                            'energy_kwh': energy,
                            'emission_factor_kg_per_kwh': emission_factor,
                            'emissions_kg_co2': component_emissions
                        }
            
            emissions['total_emissions_kg_co2'] = total_emissions
            emissions['source_emissions'] = source_emissions
            
            # Spezifische Emissionen
            total_energy = sum([data['energy_kwh'] for data in source_emissions.values()])
            if total_energy > 0:
                emissions['specific_emissions_kg_co2_per_kwh'] = total_emissions / total_energy
            
        except Exception as e:
            self.logger.warning(f"Emissions-Analyse fehlgeschlagen: {e}")
        
        return emissions
    
    def _analyze_economics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert wirtschaftliche Kennzahlen."""
        economics = {}
        
        try:
            total_costs = 0
            cost_breakdown = {}
            
            for (source, target), flow_results in results.items():
                if 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Variable Kosten
                    var_costs = scalars.get('variable_costs', 0)
                    if var_costs > 0 and 'sequences' in flow_results:
                        if 'flow' in flow_results['sequences']:
                            total_flow = flow_results['sequences']['flow'].sum()
                            total_var_costs = var_costs * total_flow
                            
                            cost_breakdown[f"{source}_variable"] = total_var_costs
                            total_costs += total_var_costs
                    
                    # Investment-Kosten
                    inv_costs = scalars.get('investment_costs', 0)
                    if inv_costs > 0:
                        cost_breakdown[f"{source}_investment"] = inv_costs
                        total_costs += inv_costs
            
            economics['total_costs_euro'] = total_costs
            economics['cost_breakdown'] = cost_breakdown
            
            # Kosten pro kWh (vereinfacht)
            total_energy = sum([
                flow_results['sequences']['flow'].sum()
                for flow_results in results.values()
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']
            ])
            
            if total_energy > 0:
                economics['lcoe_euro_per_kwh'] = total_costs / total_energy
            
        except Exception as e:
            self.logger.warning(f"Wirtschaftlichkeits-Analyse fehlgeschlagen: {e}")
        
        return economics
    
    def _save_analysis_results(self):
        """Speichert alle Analyse-Ergebnisse."""
        try:
            # JSON-Export
            import json
            
            json_file = self.output_dir / "analysis_results.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            
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


# Test-Funktion
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
            results = analyzer.perform_analysis(dummy_results, energy_system, excel_data)
            print("✅ Analyzer Test erfolgreich!")
            print(f"Durchgeführte Analysen: {list(results.keys())}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")


if __name__ == "__main__":
    test_analyzer()
