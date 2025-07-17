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
from typing import Dict, List, Any, Tuple, Optional, Union
import logging


class FakeSequenceExtractor:
    """
    Optimierte Extraktion für oemof.solph._FakeSequence Objekte.
    Basierend auf Debug-Ergebnissen vom 17.07.2025.
    """
    
    @staticmethod
    def extract_value(obj: Any, default_value: float = 0.0) -> float:
        """
        Sichere Extraktion von Werten aus _FakeSequence und anderen oemof Objekten.
        
        Args:
            obj: Das zu extrahierende Objekt
            default_value: Standardwert bei Fehlern
            
        Returns:
            Extrahierter Wert als float
        """
        if obj is None:
            return default_value
        
        # Einfache Typen
        if isinstance(obj, (int, float)):
            return float(obj)
        
        # Listen und Arrays
        if isinstance(obj, (list, tuple, np.ndarray)):
            try:
                return float(obj[0]) if len(obj) > 0 else default_value
            except (ValueError, TypeError):
                return default_value
        
        # _FakeSequence und ähnliche Objekte
        if hasattr(obj, '_value') and hasattr(obj, '_length'):
            # Methode 1: Index-Zugriff (funktioniert laut Debug)
            try:
                return float(obj[0])
            except (IndexError, TypeError):
                pass
            
            # Methode 2: value-Attribut
            if hasattr(obj, 'value') and obj.value is not None:
                try:
                    return float(obj.value)
                except (ValueError, TypeError):
                    pass
            
            # Methode 3: _value-Attribut
            try:
                return float(obj._value)
            except (ValueError, TypeError):
                pass
        
        # Fallback für andere Objekte mit Index-Zugriff
        try:
            return float(obj[0])
        except (IndexError, TypeError, KeyError):
            pass
        
        # String-Konvertierung als letzter Ausweg
        try:
            return float(str(obj))
        except (ValueError, TypeError):
            pass
        
        logging.getLogger(__name__).warning(f"Konnte Wert nicht extrahieren aus {type(obj)}: {obj}")
        return default_value
    
    @staticmethod
    def extract_timeseries(obj: Any, expected_length: int = None) -> List[float]:
        """
        Extraktion einer kompletten Zeitreihe aus _FakeSequence.
        
        Args:
            obj: _FakeSequence Objekt
            expected_length: Erwartete Länge der Zeitreihe
            
        Returns:
            Liste mit Zeitreihenwerten
        """
        if obj is None:
            return []
        
        # Für normale Listen/Arrays
        if isinstance(obj, (list, tuple, np.ndarray)):
            try:
                return [float(x) for x in obj]
            except (ValueError, TypeError):
                return []
        
        # Für _FakeSequence Objekte
        if hasattr(obj, '_value') and hasattr(obj, '_length'):
            # Länge bestimmen
            length = expected_length
            if length is None:
                length = getattr(obj, '_length', 168)  # Default 168 Stunden
            
            # Werte extrahieren
            values = []
            try:
                for i in range(length):
                    try:
                        values.append(float(obj[i]))
                    except (IndexError, TypeError):
                        # Fallback: Ersten Wert für alle Zeitschritte
                        first_value = FakeSequenceExtractor.extract_value(obj)
                        values.append(first_value)
            except Exception:
                # Fallback: Konstante Zeitreihe
                first_value = FakeSequenceExtractor.extract_value(obj)
                values = [first_value] * length
            
            return values
        
        # Einzelwert zu Liste konvertieren
        try:
            single_value = FakeSequenceExtractor.extract_value(obj)
            if expected_length:
                return [single_value] * expected_length
            return [single_value]
        except:
            return []


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
        
        # Debug-Modus aktivieren für _FakeSequence Debugging
        if settings.get('debug_mode', False):
            self.logger.setLevel(logging.DEBUG)
        
        # Einheiten (können aus Settings überschrieben werden)
        self.power_unit = settings.get('power_unit', 'MW')
        self.energy_unit = settings.get('energy_unit', 'MWh')
        self.currency_unit = settings.get('currency_unit', '€')
        
        # Zeitschritt-Faktor (1 für stündliche Schritte)
        self.time_increment = settings.get('time_increment', 1)
        
        # FakeSequenceExtractor integrieren
        self.extractor = FakeSequenceExtractor()
        
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
            self.logger.info("   ⏰ Berechne stündliche Kosten...")
            hourly_costs = self._calculate_hourly_costs(results, energy_system)
            
            # 4. Kosten nach Technologie gruppieren
            self.logger.info("   🏭 Gruppiere Kosten nach Technologie...")
            technology_costs = self._group_costs_by_technology(investment_costs, variable_costs)
            
            # 5. Vollbenutzungsstunden-Kosten berechnen
            self.logger.info("   ⚡ Berechne Vollbenutzungsstunden-Kosten...")
            utilization_costs = self._calculate_utilization_costs(investment_costs, variable_costs)
            
            # 6. Kosten-Zusammenfassung erstellen
            self.logger.info("   📋 Erstelle Kosten-Zusammenfassung...")
            cost_summary = self._create_cost_summary(investment_costs, variable_costs, hourly_costs)
            
            # 7. Gesamtkosten berechnen
            total_system_costs = cost_summary['total_costs']
            
            # 8. Excel-Export vorbereiten
            self.logger.info("   📄 Exportiere Ergebnisse...")
            self._export_cost_analysis(
                investment_costs, variable_costs, hourly_costs, 
                technology_costs, cost_summary
            )
            
            self.logger.info("✅ Kosten-Analyse erfolgreich abgeschlossen!")
            
            return {
                'investment_costs': investment_costs,
                'variable_costs': variable_costs,
                'hourly_costs': hourly_costs,
                'technology_costs': technology_costs,
                'cost_summary': cost_summary,
                'utilization_costs': utilization_costs,
                'total_system_costs': total_system_costs,
                'output_files': self.output_files
            }
            
        except Exception as e:
            self.logger.error(f"Fehler bei Kosten-Analyse: {e}")
            return self._create_empty_cost_analysis()
    
    def _calculate_investment_costs(self, results: Dict[str, Any], 
                                  energy_system: Any) -> pd.DataFrame:
        """
        Berechnet Investment-Kosten aus Energy System und Results.
        
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
                            
                            # Nur weiter wenn var_costs > 0 (auch für Listen)
                            if var_costs == 0:
                                continue
                            
                            # Suche entsprechende Results
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                                        flow_sequence = flow_results['sequences']['flow']
                                        
                                        # Energie-Statistiken berechnen
                                        total_energy = float(flow_sequence.sum() * self.time_increment)
                                        max_flow = float(flow_sequence.max())
                                        avg_flow = float(flow_sequence.mean())
                                        
                                        # Variable Kosten berechnen
                                        if isinstance(var_costs, (list, np.ndarray)):
                                            # Zeitabhängige Kosten
                                            total_var_costs = sum(
                                                float(flow_sequence[i]) * var_costs[i] 
                                                for i in range(min(len(flow_sequence), len(var_costs)))
                                            )
                                            avg_var_costs = float(np.mean(var_costs))
                                        else:
                                            # Konstante Kosten
                                            total_var_costs = total_energy * var_costs
                                            avg_var_costs = float(var_costs)
                                        
                                        # Technologie-Typ bestimmen
                                        tech_type = self._determine_technology_type(source_label)
                                        
                                        variable_data.append({
                                            'component': source_label,
                                            'target': target_label,
                                            'connection': f"{source_label} → {target_label}",
                                            'technology': tech_type,
                                            'total_energy_MWh': total_energy,
                                            'max_flow_MW': max_flow,
                                            'avg_flow_MW': avg_flow,
                                            'avg_variable_costs_EUR_per_MWh': avg_var_costs,
                                            'total_variable_costs_EUR': total_var_costs
                                        })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei Variable-Kosten-Berechnung: {e}")
        
        if variable_data:
            return pd.DataFrame(variable_data)
        else:
            return pd.DataFrame(columns=[
                'component', 'target', 'connection', 'technology', 'total_energy_MWh',
                'max_flow_MW', 'avg_flow_MW', 'avg_variable_costs_EUR_per_MWh', 'total_variable_costs_EUR'
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
                            
                            # Nur weiter wenn var_costs > 0
                            if var_costs == 0:
                                continue
                            
                            # Suche entsprechende Results
                            for (result_source, result_target), flow_results in results.items():
                                if (str(result_source) == source_label and 
                                    str(result_target) == target_label):
                                    
                                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                                        flow_sequence = flow_results['sequences']['flow']
                                        
                                        # Stündliche Kosten berechnen
                                        if isinstance(var_costs, (list, np.ndarray)):
                                            try:
                                                for hour in range(len(flow_sequence)):
                                                    cost_index = min(hour, len(var_costs) - 1)
                                                    hourly_cost = float(flow_sequence.iloc[hour]) * var_costs[cost_index]
                                                    
                                                    hourly_data.append({
                                                        'hour': hour,
                                                        'component': source_label,
                                                        'target': target_label,
                                                        'flow_MWh': float(flow_sequence.iloc[hour]),
                                                        'variable_cost_EUR_per_MWh': var_costs[cost_index],
                                                        'hourly_cost_EUR': hourly_cost
                                                    })
                                            except (IndexError, TypeError) as e:
                                                self.logger.warning(f"Fehler bei stündlichen Kosten für {source_label}: {e}")
                                        else:
                                            # Konstante Kosten
                                            for hour in range(len(flow_sequence)):
                                                hourly_cost = float(flow_sequence.iloc[hour]) * var_costs
                                                
                                                hourly_data.append({
                                                    'hour': hour,
                                                    'component': source_label,
                                                    'target': target_label,
                                                    'flow_MWh': float(flow_sequence.iloc[hour]),
                                                    'variable_cost_EUR_per_MWh': var_costs,
                                                    'hourly_cost_EUR': hourly_cost
                                                })
        
        except Exception as e:
            self.logger.warning(f"Fehler bei stündlichen Kosten: {e}")
        
        if hourly_data:
            return pd.DataFrame(hourly_data)
        else:
            return pd.DataFrame(columns=[
                'hour', 'component', 'target', 'flow_MWh', 
                'variable_cost_EUR_per_MWh', 'hourly_cost_EUR'
            ])
    
    def _group_costs_by_technology(self, investment_costs: pd.DataFrame, 
                                  variable_costs: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Gruppiert Kosten nach Technologie.
        
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
            # Gesamtkosten berechnen
            total_investment = float(investment_costs['annual_investment_costs_EUR'].sum()) if not investment_costs.empty else 0
            total_variable = float(variable_costs['total_variable_costs_EUR'].sum()) if not variable_costs.empty else 0
            total_costs = total_investment + total_variable
            
            # Anteile berechnen
            investment_share = (total_investment / total_costs * 100) if total_costs > 0 else 0
            variable_share = (total_variable / total_costs * 100) if total_costs > 0 else 0
            
            # Stündliche Kosten-Statistiken
            if not hourly_costs.empty:
                avg_hourly_costs = float(hourly_costs['hourly_cost_EUR'].mean())
                max_hourly_costs = float(hourly_costs['hourly_cost_EUR'].max())
            else:
                avg_hourly_costs = 0
                max_hourly_costs = 0
            
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
    
    def _export_cost_analysis(self, investment_costs: pd.DataFrame, 
                             variable_costs: pd.DataFrame,
                             hourly_costs: pd.DataFrame,
                             technology_costs: Dict[str, Dict[str, float]],
                             cost_summary: Dict[str, float]):
        """
        Exportiert die Kosten-Analyse in Excel-Dateien.
        
        Args:
            investment_costs: DataFrame mit Investment-Kosten
            variable_costs: DataFrame mit variablen Kosten
            hourly_costs: DataFrame mit stündlichen Kosten
            technology_costs: Dictionary mit Technologie-Kosten
            cost_summary: Dictionary mit Kosten-Zusammenfassung
        """
        try:
            output_file = self.output_dir / 'cost_analysis.xlsx'
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Investment-Kosten
                if not investment_costs.empty:
                    investment_costs.to_excel(writer, sheet_name='Investment_Costs', index=False)
                
                # Variable Kosten
                if not variable_costs.empty:
                    variable_costs.to_excel(writer, sheet_name='Variable_Costs', index=False)
                
                # Stündliche Kosten (nur erste 1000 Zeilen)
                if not hourly_costs.empty:
                    hourly_costs.head(1000).to_excel(writer, sheet_name='Hourly_Costs', index=False)
                
                # Technologie-Kosten
                if technology_costs:
                    tech_df = pd.DataFrame(technology_costs).T
                    tech_df.to_excel(writer, sheet_name='Technology_Costs', index=True)
                
                # Kosten-Zusammenfassung
                summary_df = pd.DataFrame([cost_summary])
                summary_df.to_excel(writer, sheet_name='Cost_Summary', index=False)
            
            self.output_files.append(output_file)
            self.logger.info(f"📄 Kosten-Analyse exportiert: {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Fehler beim Excel-Export: {e}")
    
    # Optimierte Extraktions-Methoden mit FakeSequenceExtractor
    
    def _extract_ep_costs(self, investment) -> float:
        """Extrahiert EP-Costs mit FakeSequenceExtractor."""
        try:
            if hasattr(investment, 'ep_costs'):
                return self.extractor.extract_value(investment.ep_costs, 0)
        except Exception as e:
            self.logger.warning(f"Fehler bei EP-Costs-Extraktion: {e}")
        return 0
    
    def _extract_investment_param(self, investment, param_name: str, default_value) -> float:
        """Extrahiert Investment-Parameter mit FakeSequenceExtractor."""
        try:
            if hasattr(investment, param_name):
                param_value = getattr(investment, param_name)
                return self.extractor.extract_value(param_value, default_value)
        except Exception as e:
            self.logger.warning(f"Fehler bei {param_name}-Extraktion: {e}")
        return default_value
    
    def _extract_variable_costs(self, flow) -> Union[float, List[float]]:
        """Extrahiert variable Kosten mit FakeSequenceExtractor."""
        try:
            if hasattr(flow, 'variable_costs') and flow.variable_costs is not None:
                var_costs = flow.variable_costs
                
                # Prüfe ob es eine Zeitreihe ist
                if hasattr(var_costs, '_length'):
                    # Zeitreihe extrahieren
                    timeseries = self.extractor.extract_timeseries(var_costs)
                    if len(set(timeseries)) == 1:
                        # Konstante Werte → Einzelwert zurückgeben
                        return timeseries[0]
                    else:
                        # Variable Werte → Liste zurückgeben
                        return timeseries
                else:
                    # Einzelwert
                    return self.extractor.extract_value(var_costs, 0)
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
        
        # Test des FakeSequenceExtractor
        print("\n🔧 Teste FakeSequenceExtractor:")
        test_values = [42, [1, 2, 3], None, "invalid"]
        for value in test_values:
            result = analyzer.extractor.extract_value(value)
            print(f"   {value} → {result}")


if __name__ == "__main__":
    test_cost_analyzer()