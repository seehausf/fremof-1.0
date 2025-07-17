#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Kosten-Analyse - Vollständige Implementation
=============================================================

Moderne Kosten-Analyse für oemof.solph 0.6.0 basierend auf der ursprünglichen 
Implementierung, angepasst für die neue Architektur.

Hauptfunktionen:
- Investment-Kosten aus Energy System und Results
- Variable Kosten aus Flows und Erzeugung
- Gesamtkosten-Aufschlüsselung
- Stündliche Kosten-Zeitreihen
- Kosten nach Technologie gruppiert

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0 (für oemof 0.6.0)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import logging


class CostAnalyzer:
    """
    Moderne Kosten-Analyse für oemof.solph 0.6.0 Ergebnisse.
    
    Berechnet Investment-Kosten, variable Kosten und Gesamtkosten
    basierend auf Energy System Definition und Optimierungsergebnissen.
    """
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Cost Analyzer.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationseinstellungen
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Einheiten (können aus Settings überschrieben werden)
        self.power_unit = settings.get('power_unit', 'MW')
        self.energy_unit = settings.get('energy_unit', 'MWh')
        self.currency_unit = settings.get('currency_unit', '€')
        
        # Zeitschritt-Faktor (1 für stündliche Schritte)
        self.time_increment = settings.get('time_increment', 1)
        
        # Ausgabedateien
        self.output_files = []
    
    def analyze_costs(self, results: Dict[str, Any], 
                     energy_system: Any, 
                     excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptmethode für die komplette Kosten-Analyse.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit detaillierter Kosten-Analyse
        """
        self.logger.info("💰 Starte umfassende Kosten-Analyse...")
        
        try:
            # 1. Investment-Kosten analysieren
            self.logger.info("   💳 Berechne Investment-Kosten...")
            investment_costs = self._calculate_investment_costs(results, energy_system)
            
            # 2. Variable Kosten analysieren
            self.logger.info("   📊 Berechne variable Kosten...")
            variable_costs = self._calculate_variable_costs(results, energy_system)
            
            # 3. Stündliche Kosten berechnen
            self.logger.info("   ⏱️ Berechne stündliche Kosten...")
            hourly_costs = self._calculate_hourly_costs(results, energy_system)
            
            # 4. Kosten nach Technologie gruppieren
            self.logger.info("   🏭 Gruppiere Kosten nach Technologie...")
            technology_costs = self._group_costs_by_technology(investment_costs, variable_costs)
            
            # 5. Gesamtkosten-Zusammenfassung
            self.logger.info("   📋 Erstelle Kosten-Zusammenfassung...")
            cost_summary = self._create_cost_summary(investment_costs, variable_costs, hourly_costs)
            
            # 6. Vollbenutzungsstunden-basierte Kosten
            self.logger.info("   ⚡ Berechne Kosten pro Vollbenutzungsstunde...")
            utilization_costs = self._calculate_utilization_costs(investment_costs, variable_costs)
            
            cost_analysis = {
                'investment_costs': investment_costs,
                'variable_costs': variable_costs,
                'hourly_costs': hourly_costs,
                'technology_costs': technology_costs,
                'cost_summary': cost_summary,
                'utilization_costs': utilization_costs,
                'total_system_costs': cost_summary['total_costs']
            }
            
            self.logger.info(f"✅ Kosten-Analyse abgeschlossen: {cost_summary['total_costs']:.2f} {self.currency_unit}")
            
            return cost_analysis
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Kosten-Analyse: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
            
            # Fallback: Leere Ergebnisse
            return self._create_empty_cost_analysis()
    
    def _calculate_investment_costs(self, results: Dict[str, Any], 
                                  energy_system: Any) -> pd.DataFrame:
        """
        Berechnet Investment-Kosten basierend auf tatsächlichen Investitionen.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            
        Returns:
            DataFrame mit Investment-Kosten-Details
        """
        investment_data = []
        
        try:
            # Durchsuche alle Nodes nach Investment-Flows
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for target_node, flow in node.outputs.items():
                        # Prüfe auf Investment-Flow
                        if hasattr(flow, 'investment') and flow.investment is not None:
                            investment = flow.investment
                            source_label = str(node.label)
                            target_label = str(target_node.label)
                            
                            # Suche entsprechende Results
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'scalars' in flow_results and 'invest' in flow_results['scalars']:
                                        invested_capacity = flow_results['scalars']['invest']
                                        
                                        if invested_capacity > 0:
                                            # EP-Costs extrahieren
                                            ep_costs = self._extract_ep_costs(investment)
                                            
                                            # Existing und Maximum extrahieren
                                            existing = self._extract_investment_param(investment, 'existing', 0)
                                            maximum = self._extract_investment_param(investment, 'maximum', float('inf'))
                                            minimum = self._extract_investment_param(investment, 'minimum', 0)
                                            
                                            # Jährliche Investment-Kosten berechnen
                                            annual_investment_cost = ep_costs * invested_capacity
                                            
                                            # Technologie-Typ bestimmen
                                            tech_type = self._determine_technology_type(source_label)
                                            
                                            investment_data.append({
                                                'component': source_label,
                                                'target': target_label,
                                                'connection': f"{source_label} → {target_label}",
                                                'technology': tech_type,
                                                'invested_capacity_MW': float(invested_capacity),
                                                'existing_capacity_MW': float(existing),
                                                'minimum_capacity_MW': float(minimum) if minimum != float('inf') else 0,
                                                'maximum_capacity_MW': float(maximum) if maximum != float('inf') else 999999,
                                                'total_capacity_MW': float(invested_capacity + existing),
                                                'ep_costs_EUR_per_MW_per_year': float(ep_costs),
                                                'annual_investment_costs_EUR': float(annual_investment_cost)
                                            })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Investment-Kosten-Berechnung: {e}")
        
        if investment_data:
            return pd.DataFrame(investment_data)
        else:
            return pd.DataFrame(columns=[
                'component', 'target', 'connection', 'technology', 'invested_capacity_MW',
                'existing_capacity_MW', 'minimum_capacity_MW', 'maximum_capacity_MW', 
                'total_capacity_MW', 'ep_costs_EUR_per_MW_per_year', 'annual_investment_costs_EUR'
            ])
    
    def _calculate_variable_costs(self, results: Dict[str, Any], 
                                energy_system: Any) -> pd.DataFrame:
        """
        Berechnet variable Kosten basierend auf tatsächlichen Flows.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            
        Returns:
            DataFrame mit variablen Kosten-Details
        """
        variable_data = []
        
        try:
            # Durchsuche alle Nodes nach Flows mit variablen Kosten
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for target_node, flow in node.outputs.items():
                        # Prüfe auf variable Kosten
                        if hasattr(flow, 'variable_costs') and flow.variable_costs is not None:
                            source_label = str(node.label)
                            target_label = str(target_node.label)
                            
                            # Variable Kosten extrahieren
                            var_costs = self._extract_variable_costs(flow)
                            
                            # Suche entsprechende Results
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                                        flow_sequence = flow_results['sequences']['flow']
                                        
                                        # Energie-Statistiken berechnen
                                        total_energy = float(flow_sequence.sum() * self.time_increment)
                                        max_flow = float(flow_sequence.max()) if len(flow_sequence) > 0 else 0
                                        mean_flow = float(flow_sequence.mean()) if len(flow_sequence) > 0 else 0
                                        operating_hours = int((flow_sequence > 0).sum())
                                        
                                        if total_energy > 0:
                                            # Gesamte variable Kosten
                                            if isinstance(var_costs, (list, np.ndarray)):
                                                # Zeitvariable Kosten
                                                var_costs_series = pd.Series(var_costs, index=flow_sequence.index)
                                                total_var_cost = float((flow_sequence * var_costs_series).sum())
                                                avg_var_cost = float(var_costs_series.mean())
                                            else:
                                                # Konstante Kosten
                                                total_var_cost = float(var_costs * total_energy)
                                                avg_var_cost = float(var_costs)
                                            
                                            # Technologie-Typ bestimmen
                                            tech_type = self._determine_technology_type(source_label)
                                            
                                            variable_data.append({
                                                'component': source_label,
                                                'target': target_label,
                                                'connection': f"{source_label} → {target_label}",
                                                'technology': tech_type,
                                                'total_energy_MWh': total_energy,
                                                'max_flow_MW': max_flow,
                                                'mean_flow_MW': mean_flow,
                                                'operating_hours': operating_hours,
                                                'capacity_factor': float(mean_flow / max_flow) if max_flow > 0 else 0,
                                                'avg_variable_costs_EUR_per_MWh': avg_var_cost,
                                                'total_variable_costs_EUR': total_var_cost
                                            })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Variable-Kosten-Berechnung: {e}")
        
        if variable_data:
            return pd.DataFrame(variable_data)
        else:
            return pd.DataFrame(columns=[
                'component', 'target', 'connection', 'technology', 'total_energy_MWh',
                'max_flow_MW', 'mean_flow_MW', 'operating_hours', 'capacity_factor',
                'avg_variable_costs_EUR_per_MWh', 'total_variable_costs_EUR'
            ])
    
    def _calculate_hourly_costs(self, results: Dict[str, Any], 
                              energy_system: Any) -> pd.DataFrame:
        """
        Berechnet stündliche Kosten für alle Flows.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            
        Returns:
            DataFrame mit stündlichen Kosten
        """
        hourly_data = []
        
        try:
            # Sammle alle Flows mit variablen Kosten
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for target_node, flow in node.outputs.items():
                        if hasattr(flow, 'variable_costs') and flow.variable_costs is not None:
                            source_label = str(node.label)
                            target_label = str(target_node.label)
                            
                            var_costs = self._extract_variable_costs(flow)
                            
                            # Suche entsprechende Results
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                                        flow_sequence = flow_results['sequences']['flow']
                                        
                                        # Stündliche Kosten berechnen
                                        if isinstance(var_costs, (list, np.ndarray)):
                                            var_costs_series = pd.Series(var_costs, index=flow_sequence.index)
                                            hourly_costs = flow_sequence * var_costs_series
                                        else:
                                            hourly_costs = flow_sequence * var_costs
                                        
                                        # Daten für DataFrame vorbereiten
                                        for timestamp, cost in hourly_costs.items():
                                            hourly_data.append({
                                                'timestamp': timestamp,
                                                'component': source_label,
                                                'target': target_label,
                                                'connection': f"{source_label} → {target_label}",
                                                'flow_MW': float(flow_sequence[timestamp]),
                                                'variable_cost_EUR_per_MWh': float(var_costs if not isinstance(var_costs, (list, np.ndarray)) else var_costs_series[timestamp]),
                                                'hourly_cost_EUR': float(cost)
                                            })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Stündliche-Kosten-Berechnung: {e}")
        
        if hourly_data:
            hourly_df = pd.DataFrame(hourly_data)
            
            # Pivot für bessere Übersicht
            try:
                hourly_pivot = hourly_df.pivot_table(
                    index='timestamp',
                    columns='connection',
                    values='hourly_cost_EUR',
                    fill_value=0
                )
                
                # Gesamtkosten pro Stunde
                hourly_pivot['total_hourly_costs'] = hourly_pivot.sum(axis=1)
                
                return hourly_pivot
            except Exception as e:
                self.logger.warning(f"Fehler bei Pivot-Erstellung: {e}")
                return hourly_df
        else:
            return pd.DataFrame()
    
    def _group_costs_by_technology(self, investment_costs: pd.DataFrame, 
                                 variable_costs: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Gruppiert Kosten nach Technologie-Typen.
        
        Args:
            investment_costs: DataFrame mit Investment-Kosten
            variable_costs: DataFrame mit variablen Kosten
            
        Returns:
            Dictionary mit Kosten nach Technologie
        """
        tech_costs = {}
        
        try:
            # Investment-Kosten nach Technologie
            if not investment_costs.empty:
                for _, row in investment_costs.iterrows():
                    tech = row['technology']
                    if tech not in tech_costs:
                        tech_costs[tech] = {'investment': 0, 'variable': 0, 'total': 0}
                    tech_costs[tech]['investment'] += float(row['annual_investment_costs_EUR'])
            
            # Variable Kosten nach Technologie
            if not variable_costs.empty:
                for _, row in variable_costs.iterrows():
                    tech = row['technology']
                    if tech not in tech_costs:
                        tech_costs[tech] = {'investment': 0, 'variable': 0, 'total': 0}
                    tech_costs[tech]['variable'] += float(row['total_variable_costs_EUR'])
            
            # Gesamtkosten berechnen
            for tech in tech_costs:
                tech_costs[tech]['total'] = (
                    tech_costs[tech]['investment'] + 
                    tech_costs[tech]['variable']
                )
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Technologie-Kosten-Gruppierung: {e}")
        
        return tech_costs
    
    def _create_cost_summary(self, investment_costs: pd.DataFrame, 
                           variable_costs: pd.DataFrame,
                           hourly_costs: pd.DataFrame) -> Dict[str, float]:
        """
        Erstellt eine Kosten-Zusammenfassung.
        
        Args:
            investment_costs: DataFrame mit Investment-Kosten
            variable_costs: DataFrame mit variablen Kosten
            hourly_costs: DataFrame mit stündlichen Kosten
            
        Returns:
            Dictionary mit Kosten-Zusammenfassung
        """
        try:
            total_investment = float(investment_costs['annual_investment_costs_EUR'].sum()) if not investment_costs.empty else 0
            total_variable = float(variable_costs['total_variable_costs_EUR'].sum()) if not variable_costs.empty else 0
            total_costs = total_investment + total_variable
            
            # Anteile berechnen
            investment_share = total_investment / total_costs if total_costs > 0 else 0
            variable_share = total_variable / total_costs if total_costs > 0 else 0
            
            # Durchschnittliche stündliche Kosten
            avg_hourly_costs = 0
            max_hourly_costs = 0
            
            if not hourly_costs.empty and 'total_hourly_costs' in hourly_costs.columns:
                avg_hourly_costs = float(hourly_costs['total_hourly_costs'].mean())
                max_hourly_costs = float(hourly_costs['total_hourly_costs'].max())
            
            return {
                'total_costs': total_costs,
                'investment_costs': total_investment,
                'variable_costs': total_variable,
                'investment_share': investment_share,
                'variable_share': variable_share,
                'avg_hourly_costs': avg_hourly_costs,
                'max_hourly_costs': max_hourly_costs,
                'currency_unit': self.currency_unit
            }
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Kosten-Zusammenfassung: {e}")
            return {
                'total_costs': 0,
                'investment_costs': 0,
                'variable_costs': 0,
                'investment_share': 0,
                'variable_share': 0,
                'avg_hourly_costs': 0,
                'max_hourly_costs': 0,
                'currency_unit': self.currency_unit
            }
    
    def _calculate_utilization_costs(self, investment_costs: pd.DataFrame, 
                                   variable_costs: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet Kosten pro Vollbenutzungsstunde.
        
        Args:
            investment_costs: DataFrame mit Investment-Kosten
            variable_costs: DataFrame mit variablen Kosten
            
        Returns:
            DataFrame mit Kosten pro Vollbenutzungsstunde
        """
        utilization_data = []
        
        try:
            # Kombiniere Investment- und Variable Kosten
            for _, inv_row in investment_costs.iterrows():
                component = inv_row['component']
                
                # Suche entsprechende variable Kosten
                var_row = variable_costs[variable_costs['component'] == component]
                
                if not var_row.empty:
                    var_row = var_row.iloc[0]
                    
                    # Vollbenutzungsstunden berechnen
                    if inv_row['total_capacity_MW'] > 0:
                        full_load_hours = float(var_row['total_energy_MWh'] / inv_row['total_capacity_MW'])
                    else:
                        full_load_hours = 0
                    
                    # Kosten pro VBH
                    investment_cost_per_flh = float(inv_row['annual_investment_costs_EUR'] / full_load_hours) if full_load_hours > 0 else 0
                    variable_cost_per_flh = float(var_row['avg_variable_costs_EUR_per_MWh'])
                    total_cost_per_flh = investment_cost_per_flh + variable_cost_per_flh
                    
                    utilization_data.append({
                        'component': component,
                        'technology': inv_row['technology'],
                        'capacity_MW': float(inv_row['total_capacity_MW']),
                        'full_load_hours': full_load_hours,
                        'investment_cost_per_FLH': investment_cost_per_flh,
                        'variable_cost_per_FLH': variable_cost_per_flh,
                        'total_cost_per_FLH': total_cost_per_flh
                    })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Vollbenutzungsstunden-Kosten: {e}")
        
        if utilization_data:
            return pd.DataFrame(utilization_data)
        else:
            return pd.DataFrame(columns=[
                'component', 'technology', 'capacity_MW', 'full_load_hours',
                'investment_cost_per_FLH', 'variable_cost_per_FLH', 'total_cost_per_FLH'
            ])
    
    def _extract_ep_costs(self, investment) -> float:
        """Extrahiert EP-Costs aus Investment-Objekt."""
        try:
            if hasattr(investment, 'ep_costs'):
                ep_costs = investment.ep_costs
                if hasattr(ep_costs, 'tolist'):
                    ep_costs_list = ep_costs.tolist()
                    return float(ep_costs_list[0]) if ep_costs_list else 0
                else:
                    return float(ep_costs)
        except Exception as e:
            self.logger.warning(f"Fehler bei EP-Costs-Extraktion: {e}")
        return 0
    
    def _extract_investment_param(self, investment, param_name: str, default_value) -> float:
        """Extrahiert Investment-Parameter."""
        try:
            if hasattr(investment, param_name):
                param_value = getattr(investment, param_name)
                if hasattr(param_value, 'tolist'):
                    param_list = param_value.tolist()
                    return float(param_list[0]) if param_list else default_value
                else:
                    return float(param_value)
        except Exception as e:
            self.logger.warning(f"Fehler bei {param_name}-Extraktion: {e}")
        return default_value
    
    def _extract_variable_costs(self, flow) -> float:
        """Extrahiert variable Kosten aus Flow-Objekt."""
        try:
            if hasattr(flow, 'variable_costs'):
                var_costs = flow.variable_costs
                if hasattr(var_costs, 'tolist'):
                    return var_costs.tolist()
                else:
                    return float(var_costs)
        except Exception as e:
            self.logger.warning(f"Fehler bei Variable-Kosten-Extraktion: {e}")
        return 0
    
    def _determine_technology_type(self, component_name: str) -> str:
        """
        Bestimmt den Technologie-Typ basierend auf dem Komponenten-Namen.
        
        Args:
            component_name: Name der Komponente
            
        Returns:
            Technologie-Typ als String
        """
        component_lower = component_name.lower()
        
        if any(term in component_lower for term in ['pv', 'solar', 'photovoltaic']):
            return 'Solar PV'
        elif any(term in component_lower for term in ['wind', 'wka', 'windkraft']):
            return 'Wind'
        elif any(term in component_lower for term in ['grid', 'netz', 'import']):
            return 'Grid Import'
        elif any(term in component_lower for term in ['battery', 'storage', 'speicher']):
            return 'Storage'
        elif any(term in component_lower for term in ['gas', 'biogas', 'erdgas']):
            return 'Gas'
        elif any(term in component_lower for term in ['chp', 'bhkw', 'kwk']):
            return 'CHP'
        elif any(term in component_lower for term in ['heat', 'wärme', 'heizung']):
            return 'Heat'
        elif any(term in component_lower for term in ['pump', 'wärmepumpe']):
            return 'Heat Pump'
        else:
            return 'Other'
    
    def _create_empty_cost_analysis(self) -> Dict[str, Any]:
        """Erstellt eine leere Kosten-Analyse als Fallback."""
        return {
            'investment_costs': pd.DataFrame(),
            'variable_costs': pd.DataFrame(),
            'hourly_costs': pd.DataFrame(),
            'technology_costs': {},
            'cost_summary': {
                'total_costs': 0,
                'investment_costs': 0,
                'variable_costs': 0,
                'investment_share': 0,
                'variable_share': 0,
                'avg_hourly_costs': 0,
                'max_hourly_costs': 0,
                'currency_unit': self.currency_unit
            },
            'utilization_costs': pd.DataFrame(),
            'total_system_costs': 0
        }


def test_cost_analyzer():
    """Test-Funktion für den Cost Analyzer."""
    import tempfile
    
    print("🧪 Teste Cost Analyzer...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {
            'power_unit': 'MW',
            'energy_unit': 'MWh',
            'currency_unit': '€',
            'time_increment': 1,
            'debug_mode': True
        }
        
        analyzer = CostAnalyzer(Path(temp_dir), settings)
        
        print("✅ Cost Analyzer erfolgreich initialisiert!")
        print("💡 Verwende analyzer.analyze_costs(results, energy_system, excel_data)")
        print("📊 Für vollständige Kosten-Analyse mit Excel-Export")
        
        # Test der Technologie-Erkennung
        test_components = ['pv_plant', 'wind_plant', 'grid_import', 'battery_storage', 'gas_turbine']
        print("\n🔍 Teste Technologie-Erkennung:")
        for component in test_components:
            tech_type = analyzer._determine_technology_type(component)
            print(f"   {component} → {tech_type}")


if __name__ == "__main__":
    test_cost_analyzer()
