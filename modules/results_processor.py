#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Ergebnisverarbeitung (VOLLSTÄNDIG ERWEITERT)
============================================================

Verarbeitet und speichert Optimierungsergebnisse in verschiedenen Formaten.
Erstellt strukturierte Ausgabedateien und detaillierte Zielfunktions-Aufschlüsselung.

VOLLSTÄNDIG ERWEITERT: Komplette Zielfunktions-Aufschlüsselung nach Technologien,
Kostenarten und Energiesystem-Objekten mit Investment-Annuity-Unterstützung.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

try:
    import oemof.solph as solph
    from oemof.solph._options import Investment, NonConvex
except ImportError:
    solph = None


class EnhancedResultsProcessor:
    """Erweiterte Klasse für die Verarbeitung und Speicherung von Optimierungsergebnissen."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Enhanced Results-Processor.
        
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
        
        # Zielfunktions-Cache für Performance
        self._objective_cache = {}
    
    def process_results(self, results: Dict[str, Any], energy_system: Any, 
                       excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Optimierungsergebnisse komplett mit erweiterter Kostenanalyse.
        
        Args:
            results: oemof.solph Ergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit verarbeiteten Ergebnissen
        """
        self.logger.info("📈 Verarbeite Optimierungsergebnisse...")
        
        processed_results = {}
        
        # ✅ NEUE ERWEITERTE ZIELFUNKTIONS-AUFSCHLÜSSELUNG
        self.logger.info("💰 Erstelle detaillierte Zielfunktions-Aufschlüsselung...")
        objective_breakdown = self._create_comprehensive_objective_breakdown(
            results, energy_system, excel_data
        )
        processed_results['objective_breakdown'] = objective_breakdown
        self._save_comprehensive_objective_breakdown(objective_breakdown)
        
        # Basis-Flows extrahieren und speichern
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
        
        # Legacy-Kosten-Aufschlüsselung (für Kompatibilität)
        costs = self._calculate_costs(results, energy_system)
        processed_results['costs'] = costs
        self._save_dataframe(costs, 'costs')
        
        # Zusammenfassung erstellen
        summary = self._create_enhanced_summary(processed_results, energy_system, objective_breakdown)
        processed_results['summary'] = summary
        self._save_summary(summary)
        
        self.logger.info(f"✅ {len(self.output_files)} Ergebnisdateien erstellt")
        
        return processed_results
    
    def _create_comprehensive_objective_breakdown(self, results: Dict[str, Any], 
                                                energy_system: Any, 
                                                excel_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        ✅ VOLLSTÄNDIG ERWEITERT: Erstellt eine umfassende Aufschlüsselung der Zielfunktion.
        
        Returns:
            Dictionary mit verschiedenen Aufschlüsselungs-DataFrames
        """
        self.logger.info("💰 Erstelle umfassende Zielfunktions-Aufschlüsselung...")
        
        breakdown = {}
        
        # 1. Investment-Kosten-Aufschlüsselung (ERWEITERT)
        investment_costs = self._calculate_comprehensive_investment_costs(results, energy_system, excel_data)
        breakdown['investment_costs'] = investment_costs
        
        # 2. Variable Kosten-Aufschlüsselung (ERWEITERT)
        variable_costs = self._calculate_comprehensive_variable_costs(results, energy_system, excel_data)
        breakdown['variable_costs'] = variable_costs
        
        # 3. Fixe Betriebskosten-Aufschlüsselung
        fixed_costs = self._calculate_fixed_operational_costs(results, energy_system, excel_data)
        breakdown['fixed_operational_costs'] = fixed_costs
        
        # ✅ NEU: 4. Component-Level Cost Breakdown
        component_costs = self._calculate_component_level_costs(results, energy_system, excel_data)
        breakdown['component_costs'] = component_costs
        
        # ✅ NEU: 5. Technology Category Breakdown
        technology_category_costs = self._calculate_technology_category_costs(breakdown)
        breakdown['technology_category_costs'] = technology_category_costs
        
        # ✅ NEU: 6. Flow-Level Cost Details
        flow_costs = self._calculate_flow_level_costs(results, energy_system, excel_data)
        breakdown['flow_costs'] = flow_costs
        
        # 7. Gesamtkostenübersicht pro Technologie (ERWEITERT)
        technology_totals = self._calculate_enhanced_technology_totals(breakdown)
        breakdown['technology_totals'] = technology_totals
        
        # 8. Kostenarten-Übersicht (ERWEITERT)
        cost_type_summary = self._calculate_enhanced_cost_type_summary(breakdown)
        breakdown['cost_type_summary'] = cost_type_summary
        
        # ✅ NEU: 9. Investment Comparison Analysis
        investment_analysis = self._calculate_investment_analysis(breakdown, excel_data)
        breakdown['investment_analysis'] = investment_analysis
        
        # ✅ NEU: 10. Cost per Energy Unit Analysis
        cost_per_unit = self._calculate_cost_per_energy_unit(breakdown, results)
        breakdown['cost_per_unit'] = cost_per_unit
        
        return breakdown
    
    def _calculate_comprehensive_investment_costs(self, results: Dict[str, Any], 
                                                energy_system: Any, 
                                                excel_data: Dict[str, Any]) -> pd.DataFrame:
        """✅ ERWEITERT: Berechnet Investment-Kosten mit detaillierter Annuity-Analyse."""
        investment_data = []
        
        for (source, target), flow_results in results.items():
            if 'scalars' in flow_results:
                scalars = flow_results['scalars']
                
                # Investment-Kapazität und -Kosten extrahieren
                if 'invest' in scalars and scalars['invest'] > 0:
                    invested_capacity = scalars['invest']
                    
                    # EP-Costs und Investment-Parameter aus System extrahieren
                    investment_params = self._get_comprehensive_investment_params(
                        source, target, energy_system, excel_data
                    )
                    
                    if investment_params:
                        # Jährliche Investment-Kosten berechnen
                        annual_investment_costs = investment_params['ep_costs'] * invested_capacity
                        
                        # Komponentenart und Technologie bestimmen
                        component_info = self._get_enhanced_component_info(source, target, energy_system)
                        
                        investment_entry = {
                            'component_label': component_info['component_label'],
                            'component_type': component_info['component_type'],
                            'technology_type': component_info['technology_type'],
                            'technology_category': component_info['technology_category'],
                            'connection': f"{source} → {target}",
                            'flow_direction': component_info['flow_direction'],
                            
                            # Kapazitäts-Informationen
                            'invested_capacity_kW': invested_capacity,
                            'existing_capacity_kW': investment_params.get('existing_capacity', 0),
                            'total_capacity_kW': invested_capacity + investment_params.get('existing_capacity', 0),
                            
                            # Kosten-Informationen
                            'ep_costs_EUR_per_kW_per_year': investment_params['ep_costs'],
                            'annual_investment_costs_EUR': annual_investment_costs,
                            
                            # Investment-Parameter-Details
                            'original_investment_costs_EUR_per_kW': investment_params.get('original_investment_costs'),
                            'lifetime_years': investment_params.get('lifetime'),
                            'interest_rate_percent': investment_params.get('interest_rate', 0) * 100,
                            'annuity_factor': investment_params.get('annuity_factor'),
                            
                            # Grenzen
                            'invest_min_kW': investment_params.get('invest_min', 0),
                            'invest_max_kW': investment_params.get('invest_max', np.inf),
                            
                            # Klassifikation
                            'cost_category': 'Investment',
                            'cost_subcategory': self._determine_investment_subcategory(investment_params),
                        }
                        
                        # Zusätzliche Metriken
                        investment_entry.update(self._calculate_investment_metrics(
                            invested_capacity, investment_params, scalars
                        ))
                        
                        investment_data.append(investment_entry)
        
        df = pd.DataFrame(investment_data)
        
        # Sortierung nach Gesamtkosten
        if not df.empty:
            df = df.sort_values('annual_investment_costs_EUR', ascending=False)
            
            # Relative Anteile berechnen
            total_investment_costs = df['annual_investment_costs_EUR'].sum()
            if total_investment_costs > 0:
                df['investment_share_percent'] = (df['annual_investment_costs_EUR'] / total_investment_costs * 100).round(2)
        
        return df
    
    def _calculate_comprehensive_variable_costs(self, results: Dict[str, Any], 
                                              energy_system: Any, 
                                              excel_data: Dict[str, Any]) -> pd.DataFrame:
        """✅ ERWEITERT: Berechnet variable Kosten mit detaillierter Energie-Analyse."""
        variable_data = []
        
        for (source, target), flow_results in results.items():
            if 'sequences' in flow_results and 'scalars' in flow_results:
                sequences = flow_results['sequences']
                scalars = flow_results['scalars']
                
                if 'flow' in sequences:
                    flow_values = sequences['flow']
                    total_energy = flow_values.sum()
                    
                    # Variable Kosten aus System extrahieren
                    var_costs_info = self._get_comprehensive_variable_costs(
                        source, target, energy_system, excel_data
                    )
                    
                    if var_costs_info and var_costs_info['var_costs'] != 0 and total_energy > 0:
                        total_variable_costs = total_energy * var_costs_info['var_costs']
                        
                        # Komponentenart bestimmen
                        component_info = self._get_enhanced_component_info(source, target, energy_system)
                        
                        # Zeitreihen-Statistiken
                        flow_stats = self._calculate_flow_statistics(flow_values)
                        
                        variable_entry = {
                            'component_label': component_info['component_label'],
                            'component_type': component_info['component_type'],
                            'technology_type': component_info['technology_type'],
                            'technology_category': component_info['technology_category'],
                            'connection': f"{source} → {target}",
                            'flow_direction': component_info['flow_direction'],
                            
                            # Energie-Informationen
                            'total_energy_kWh': total_energy,
                            'total_energy_MWh': total_energy / 1000,
                            'variable_costs_EUR_per_kWh': var_costs_info['var_costs'],
                            'total_variable_costs_EUR': total_variable_costs,
                            
                            # Flow-Statistiken
                            'max_power_kW': flow_stats['max'],
                            'average_power_kW': flow_stats['mean'],
                            'min_power_kW': flow_stats['min'],
                            'std_power_kW': flow_stats['std'],
                            'utilization_hours': flow_stats['utilization_hours'],
                            'capacity_factor': flow_stats['capacity_factor'],
                            
                            # Klassifikation
                            'cost_category': 'Variable',
                            'cost_subcategory': self._determine_variable_cost_subcategory(var_costs_info),
                            
                            # Zeitbezogene Metriken
                            'cost_per_hour_EUR': total_variable_costs / len(flow_values) if len(flow_values) > 0 else 0,
                            'energy_per_hour_kWh': total_energy / len(flow_values) if len(flow_values) > 0 else 0,
                        }
                        
                        variable_data.append(variable_entry)
        
        df = pd.DataFrame(variable_data)
        
        # Sortierung und relative Anteile
        if not df.empty:
            df = df.sort_values('total_variable_costs_EUR', ascending=False)
            
            total_variable_costs = df['total_variable_costs_EUR'].sum()
            if total_variable_costs > 0:
                df['variable_share_percent'] = (df['total_variable_costs_EUR'] / total_variable_costs * 100).round(2)
        
        return df
    
    def _calculate_component_level_costs(self, results: Dict[str, Any], 
                                       energy_system: Any, 
                                       excel_data: Dict[str, Any]) -> pd.DataFrame:
        """✅ NEU: Berechnet Kosten auf Komponenten-Level (aggregiert über alle Flows)."""
        component_costs = {}
        
        # Sammle alle Kosten pro Komponente
        for (source, target), flow_results in results.items():
            # Bestimme welche Komponente die "Besitzer" ist
            component_candidates = [source, target]
            
            for component_label in component_candidates:
                if str(component_label) not in component_costs:
                    component_info = self._get_component_by_label(str(component_label), energy_system)
                    if component_info:
                        component_costs[str(component_label)] = {
                            'component_label': str(component_label),
                            'component_type': component_info['type'],
                            'technology_type': component_info['technology_type'],
                            'technology_category': component_info['technology_category'],
                            'investment_costs_EUR': 0,
                            'variable_costs_EUR': 0,
                            'fixed_costs_EUR': 0,
                            'total_costs_EUR': row['total_variable_costs_EUR'],
                        'cost_per_kWh_EUR': row['total_variable_costs_EUR'] / row['total_energy_kWh'],
                        'cost_per_MWh_EUR': row['total_variable_costs_EUR'] / (row['total_energy_kWh'] / 1000),
                    }
        
        # Investment-Kosten pro Energieeinheit (basierend auf Volllaststunden)
        if 'investment_costs' in breakdown and not breakdown['investment_costs'].empty:
            inv_df = breakdown['investment_costs']
            
            for _, row in inv_df.iterrows():
                # Schätze Volllaststunden (kann aus variable_costs abgeleitet werden)
                estimated_full_load_hours = self._estimate_full_load_hours(
                    row['component_label'], breakdown.get('variable_costs', pd.DataFrame())
                )
                
                if estimated_full_load_hours > 0:
                    estimated_annual_energy = row['invested_capacity_kW'] * estimated_full_load_hours
                    
                    cost_per_unit_data.append({
                        'technology_type': row['technology_type'],
                        'cost_category': 'Investment (amortized)',
                        'total_energy_kWh': estimated_annual_energy,
                        'total_costs_EUR': row['annual_investment_costs_EUR'],
                        'cost_per_kWh_EUR': row['annual_investment_costs_EUR'] / estimated_annual_energy,
                        'cost_per_MWh_EUR': row['annual_investment_costs_EUR'] / (estimated_annual_energy / 1000),
                        'full_load_hours_estimate': estimated_full_load_hours,
                    })
        
        df = pd.DataFrame(cost_per_unit_data)
        
        if not df.empty:
            df = df.sort_values('cost_per_kWh_EUR', ascending=False)
        
        return df
    
    def _get_comprehensive_investment_params(self, source, target, energy_system, excel_data):
        """Extrahiert umfassende Investment-Parameter aus dem System."""
        try:
            # Suche Investment-Flow im EnergySystem
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for output_node, flow in node.outputs.items():
                        if str(node.label) == str(source) and str(output_node.label) == str(target):
                            if hasattr(flow, 'nominal_capacity') and hasattr(flow.nominal_capacity, 'ep_costs'):
                                return self._extract_investment_details(flow.nominal_capacity, source, excel_data)
                
                if hasattr(node, 'inputs'):
                    for input_node, flow in node.inputs.items():
                        if str(input_node.label) == str(source) and str(node.label) == str(target):
                            if hasattr(flow, 'nominal_capacity') and hasattr(flow.nominal_capacity, 'ep_costs'):
                                return self._extract_investment_details(flow.nominal_capacity, source, excel_data)
        except Exception as e:
            self.logger.debug(f"Fehler beim Extrahieren der Investment-Parameter: {e}")
        
        return None
    
    def _extract_investment_details(self, investment_obj, component_label, excel_data):
        """Extrahiert detaillierte Investment-Informationen."""
        details = {
            'ep_costs': investment_obj.ep_costs,
            'existing_capacity': getattr(investment_obj, 'existing', 0),
            'invest_min': getattr(investment_obj, 'minimum', 0),
            'invest_max': getattr(investment_obj, 'maximum', np.inf),
        }
        
        # Versuche Original-Parameter aus Excel-Daten zu rekonstruieren
        original_params = self._find_original_investment_params(component_label, excel_data)
        if original_params:
            details.update(original_params)
            
            # Berechne Annuity-Faktor falls Lifetime und Interest Rate verfügbar
            if 'lifetime' in original_params and 'interest_rate' in original_params:
                details['annuity_factor'] = self._calculate_annuity_factor(
                    original_params['lifetime'], original_params['interest_rate']
                )
        
        return details
    
    def _find_original_investment_params(self, component_label, excel_data):
        """Sucht Original-Investment-Parameter in Excel-Daten."""
        component_label_str = str(component_label)
        
        # Durchsuche alle relevanten Sheets
        for sheet_name in ['sources', 'sinks', 'simple_transformers']:
            if sheet_name in excel_data:
                df = excel_data[sheet_name]
                
                # Finde Komponente
                matching_rows = df[df['label'] == component_label_str]
                
                if not matching_rows.empty:
                    row = matching_rows.iloc[0]
                    
                    params = {}
                    
                    # Investment-Kosten
                    if 'investment_costs' in row and pd.notna(row['investment_costs']):
                        params['original_investment_costs'] = float(row['investment_costs'])
                    
                    # Lifetime
                    if 'lifetime' in row and pd.notna(row['lifetime']):
                        params['lifetime'] = float(row['lifetime'])
                    
                    # Interest Rate
                    if 'interest_rate' in row and pd.notna(row['interest_rate']):
                        params['interest_rate'] = float(row['interest_rate'])
                    
                    return params if params else None
        
        return None
    
    def _calculate_annuity_factor(self, lifetime, interest_rate):
        """Berechnet den Annuity-Faktor."""
        try:
            if interest_rate == 0:
                return 1 / lifetime
            else:
                return (interest_rate * (1 + interest_rate) ** lifetime) / ((1 + interest_rate) ** lifetime - 1)
        except:
            return None
    
    def _get_comprehensive_variable_costs(self, source, target, energy_system, excel_data):
        """Extrahiert umfassende Variable-Kosten-Informationen."""
        try:
            # Suche im EnergySystem
            for node in energy_system.nodes:
                if hasattr(node, 'outputs'):
                    for output_node, flow in node.outputs.items():
                        if str(node.label) == str(source) and str(output_node.label) == str(target):
                            if hasattr(flow, 'variable_costs'):
                                return {
                                    'var_costs': flow.variable_costs,
                                    'source': 'flow_attribute'
                                }
                
                if hasattr(node, 'inputs'):
                    for input_node, flow in node.inputs.items():
                        if str(input_node.label) == str(source) and str(node.label) == str(target):
                            if hasattr(flow, 'variable_costs'):
                                return {
                                    'var_costs': flow.variable_costs,
                                    'source': 'flow_attribute'
                                }
        except Exception as e:
            self.logger.debug(f"Fehler beim Extrahieren der variablen Kosten: {e}")
        
        return {'var_costs': 0, 'source': 'not_found'}
    
    def _get_enhanced_component_info(self, source, target, energy_system):
        """Erweiterte Komponenten-Informationen."""
        # Bestimme Haupt-Komponente (nicht Bus)
        component_label = str(source)
        flow_direction = 'output'
        
        # Prüfe ob source ein Bus ist
        if self._is_bus(source, energy_system):
            component_label = str(target)
            flow_direction = 'input'
        
        # Finde Komponente im System
        component_info = self._get_component_by_label(component_label, energy_system)
        
        if component_info:
            return {
                'component_label': component_label,
                'component_type': component_info['type'],
                'technology_type': component_info['technology_type'],
                'technology_category': component_info['technology_category'],
                'flow_direction': flow_direction
            }
        else:
            # Fallback
            return {
                'component_label': component_label,
                'component_type': 'Unknown',
                'technology_type': self._guess_technology_type(component_label),
                'technology_category': self._guess_technology_category(component_label),
                'flow_direction': flow_direction
            }
    
    def _get_component_by_label(self, label, energy_system):
        """Findet Komponente im EnergySystem nach Label."""
        try:
            for node in energy_system.nodes:
                if str(node.label) == label:
                    return {
                        'label': label,
                        'type': type(node).__name__,
                        'node': node,
                        'technology_type': self._determine_technology_type(node),
                        'technology_category': self._determine_technology_category(node)
                    }
        except:
            pass
        return None
    
    def _is_bus(self, label, energy_system):
        """Prüft ob Label ein Bus ist."""
        try:
            for node in energy_system.nodes:
                if str(node.label) == str(label):
                    return isinstance(node, solph.buses.Bus)
        except:
            pass
        return 'bus' in str(label).lower()
    
    def _determine_technology_type(self, node):
        """Bestimmt detaillierten Technologie-Typ."""
        label = str(node.label).lower()
        node_type = type(node).__name__.lower()
        
        # Detaillierte Technologie-Erkennung
        if any(word in label for word in ['pv', 'solar', 'photovoltaic']):
            return 'PV Solar'
        elif any(word in label for word in ['wind', 'wtg']):
            return 'Wind Power'
        elif any(word in label for word in ['grid', 'import']) and 'source' in node_type:
            return 'Grid Import'
        elif any(word in label for word in ['grid', 'export']) and 'sink' in node_type:
            return 'Grid Export'
        elif any(word in label for word in ['gas']) and any(word in label for word in ['plant', 'power', 'engine']):
            return 'Gas Power Plant'
        elif any(word in label for word in ['gas', 'boiler']):
            return 'Gas Boiler'
        elif any(word in label for word in ['heat', 'pump', 'hp']):
            return 'Heat Pump'
        elif any(word in label for word in ['chp', 'kwk', 'cogeneration']):
            return 'CHP Plant'
        elif any(word in label for word in ['battery', 'storage']) and 'el' in label:
            return 'Battery Storage'
        elif any(word in label for word in ['thermal', 'storage']) and 'heat' in label:
            return 'Thermal Storage'
        elif any(word in label for word in ['load', 'demand']) and 'el' in label:
            return 'Electrical Load'
        elif any(word in label for word in ['load', 'demand']) and 'heat' in label:
            return 'Heat Load'
        elif 'bus' in node_type:
            if 'el' in label:
                return 'Electrical Bus'
            elif 'heat' in label:
                return 'Heat Bus'
            elif 'gas' in label:
                return 'Gas Bus'
            else:
                return 'Energy Bus'
        else:
            return f'{node_type.title()} Component'
    
    def _determine_technology_category(self, node):
        """Bestimmt Technologie-Kategorie."""
        tech_type = self._determine_technology_type(node)
        
        renewable_sources = ['PV Solar', 'Wind Power']
        conventional_sources = ['Gas Power Plant', 'Grid Import']
        conversion_technologies = ['Heat Pump', 'Gas Boiler', 'CHP Plant']
        storage_technologies = ['Battery Storage', 'Thermal Storage']
        demand_components = ['Electrical Load', 'Heat Load', 'Grid Export']
        system_components = ['Electrical Bus', 'Heat Bus', 'Gas Bus', 'Energy Bus']
        
        if tech_type in renewable_sources:
            return 'Renewable Generation'
        elif tech_type in conventional_sources:
            return 'Conventional Generation'
        elif tech_type in conversion_technologies:
            return 'Conversion Technology'
        elif tech_type in storage_technologies:
            return 'Energy Storage'
        elif tech_type in demand_components:
            return 'Demand/Export'
        elif tech_type in system_components:
            return 'System Infrastructure'
        else:
            return 'Other Technology'
    
    def _guess_technology_type(self, label):
        """Errät Technologie-Typ basierend auf Label (Fallback)."""
        label_lower = str(label).lower()
        
        if any(word in label_lower for word in ['pv', 'solar']):
            return 'PV Solar'
        elif any(word in label_lower for word in ['wind']):
            return 'Wind Power'
        elif any(word in label_lower for word in ['grid', 'import']):
            return 'Grid Import'
        elif any(word in label_lower for word in ['load', 'demand']):
            return 'Load'
        elif any(word in label_lower for word in ['bus']):
            return 'Bus'
        else:
            return 'Unknown Technology'
    
    def _guess_technology_category(self, label):
        """Errät Technologie-Kategorie (Fallback)."""
        tech_type = self._guess_technology_type(label)
        
        if tech_type in ['PV Solar', 'Wind Power']:
            return 'Renewable Generation'
        elif tech_type in ['Grid Import']:
            return 'Conventional Generation'
        elif tech_type in ['Load']:
            return 'Demand/Export'
        elif tech_type in ['Bus']:
            return 'System Infrastructure'
        else:
            return 'Other Technology'
    
    def _calculate_flow_statistics(self, flow_values):
        """Berechnet Flow-Statistiken."""
        stats = {
            'max': flow_values.max(),
            'min': flow_values.min(),
            'mean': flow_values.mean(),
            'std': flow_values.std(),
            'utilization_hours': (flow_values > 0).sum(),
            'capacity_factor': 0
        }
        
        if stats['max'] > 0:
            stats['capacity_factor'] = stats['mean'] / stats['max']
        
        return stats
    
    def _determine_investment_subcategory(self, investment_params):
        """Bestimmt Investment-Unterkategorie."""
        if investment_params.get('lifetime') and investment_params.get('interest_rate'):
            return 'Annuity-based Investment'
        else:
            return 'Direct Cost Investment'
    
    def _determine_variable_cost_subcategory(self, var_costs_info):
        """Bestimmt Variable-Kosten-Unterkategorie."""
        var_costs = var_costs_info['var_costs']
        
        if var_costs > 0:
            return 'Operating Costs'
        elif var_costs < 0:
            return 'Revenue/Feed-in'
        else:
            return 'No Variable Costs'
    
    def _determine_flow_type(self, source, target, energy_system):
        """Bestimmt Flow-Typ."""
        source_is_bus = self._is_bus(source, energy_system)
        target_is_bus = self._is_bus(target, energy_system)
        
        if source_is_bus and target_is_bus:
            return 'Bus-to-Bus'
        elif source_is_bus:
            return 'Bus-to-Component'
        elif target_is_bus:
            return 'Component-to-Bus'
        else:
            return 'Component-to-Component'
    
    def _estimate_full_load_hours(self, component_label, variable_costs_df):
        """Schätzt Volllaststunden basierend auf Variable-Kosten-Daten."""
        if variable_costs_df.empty:
            return 2000  # Default-Schätzung
        
        # Suche Komponente in Variable-Kosten
        matching = variable_costs_df[variable_costs_df['component_label'] == component_label]
        
        if not matching.empty:
            row = matching.iloc[0]
            if row['max_power_kW'] > 0:
                return row['total_energy_kWh'] / row['max_power_kW']
        
        # Fallback-Schätzungen nach Technologie-Typ
        component_label_lower = str(component_label).lower()
        
        if any(word in component_label_lower for word in ['pv', 'solar']):
            return 1000  # Typisch für PV
        elif any(word in component_label_lower for word in ['wind']):
            return 2500  # Typisch für Wind
        elif any(word in component_label_lower for word in ['gas', 'plant']):
            return 4000  # Typisch für Gas-Kraftwerk
        else:
            return 3000  # Allgemeine Schätzung
    
    def _calculate_fixed_operational_costs(self, results, energy_system, excel_data):
        """Berechnet fixe Betriebskosten (erweiterte Implementierung)."""
        fixed_data = []
        
        # Hier könnte eine erweiterte Implementierung für fixe Kosten stehen
        # Aktuell als Platzhalter, da fixe Kosten oft nicht im Standard oemof.solph verwendet werden
        
        return pd.DataFrame(fixed_data)
    
    def _calculate_enhanced_technology_totals(self, breakdown):
        """Erweiterte Technologie-Gesamtkosten."""
        technology_totals = []
        
        # Sammle alle Technologien
        all_technologies = set()
        for df in breakdown.values():
            if isinstance(df, pd.DataFrame) and 'technology_type' in df.columns:
                all_technologies.update(df['technology_type'].unique())
        
        for technology in all_technologies:
            investment_total = 0
            variable_total = 0
            fixed_total = 0
            
            # Investment-Kosten
            if 'investment_costs' in breakdown and not breakdown['investment_costs'].empty:
                inv_df = breakdown['investment_costs']
                tech_inv = inv_df[inv_df['technology_type'] == technology]
                investment_total = tech_inv['annual_investment_costs_EUR'].sum()
            
            # Variable Kosten
            if 'variable_costs' in breakdown and not breakdown['variable_costs'].empty:
                var_df = breakdown['variable_costs']
                tech_var = var_df[var_df['technology_type'] == technology]
                variable_total = tech_var['total_variable_costs_EUR'].sum()
            
            # Fixe Kosten
            if 'fixed_operational_costs' in breakdown and not breakdown['fixed_operational_costs'].empty:
                fix_df = breakdown['fixed_operational_costs']
                tech_fix = fix_df[fix_df['technology_type'] == technology]
                fixed_total = tech_fix['total_fixed_costs_EUR'].sum()
            
            total_costs = investment_total + variable_total + fixed_total
            
            if total_costs > 0:  # Nur Technologien mit Kosten
                # Zusätzliche Metriken
                total_capacity = 0
                total_energy = 0
                
                if 'investment_costs' in breakdown:
                    tech_capacity = breakdown['investment_costs'][
                        breakdown['investment_costs']['technology_type'] == technology
                    ]['invested_capacity_kW'].sum()
                    total_capacity += tech_capacity
                
                if 'variable_costs' in breakdown:
                    tech_energy = breakdown['variable_costs'][
                        breakdown['variable_costs']['technology_type'] == technology
                    ]['total_energy_kWh'].sum()
                    total_energy += tech_energy
                
                technology_totals.append({
                    'technology_type': technology,
                    'investment_costs_EUR': investment_total,
                    'variable_costs_EUR': variable_total,
                    'fixed_operational_costs_EUR': fixed_total,
                    'total_costs_EUR': total_costs,
                    'total_capacity_kW': total_capacity,
                    'total_energy_kWh': total_energy,
                    'specific_costs_EUR_per_kW': total_costs / total_capacity if total_capacity > 0 else 0,
                    'specific_costs_EUR_per_kWh': total_costs / total_energy if total_energy > 0 else 0,
                    'share_of_total_percent': 0  # Wird später berechnet
                })
        
        df = pd.DataFrame(technology_totals)
        
        # Prozentualen Anteil berechnen
        if not df.empty:
            total_system_costs = df['total_costs_EUR'].sum()
            if total_system_costs > 0:
                df['share_of_total_percent'] = (df['total_costs_EUR'] / total_system_costs * 100).round(2)
            
            # Nach Gesamtkosten sortieren
            df = df.sort_values('total_costs_EUR', ascending=False)
        
        return df
    
    def _calculate_enhanced_cost_type_summary(self, breakdown):
        """Erweiterte Kostenarten-Übersicht."""
        cost_summary = []
        
        # Investment-Kosten
        if 'investment_costs' in breakdown and not breakdown['investment_costs'].empty:
            inv_total = breakdown['investment_costs']['annual_investment_costs_EUR'].sum()
            inv_count = len(breakdown['investment_costs'])
            cost_summary.append({
                'cost_type': 'Investment Costs',
                'description': 'Annualized investment costs (EP-Costs)',
                'total_EUR': inv_total,
                'components_count': inv_count,
                'avg_cost_per_component_EUR': inv_total / inv_count if inv_count > 0 else 0,
                'share_percent': 0
            })
        
        # Variable Kosten
        if 'variable_costs' in breakdown and not breakdown['variable_costs'].empty:
            var_total = breakdown['variable_costs']['total_variable_costs_EUR'].sum()
            var_count = len(breakdown['variable_costs'])
            total_energy = breakdown['variable_costs']['total_energy_kWh'].sum()
            cost_summary.append({
                'cost_type': 'Variable Costs',
                'description': 'Energy-dependent operational costs',
                'total_EUR': var_total,
                'components_count': var_count,
                'avg_cost_per_component_EUR': var_total / var_count if var_count > 0 else 0,
                'avg_cost_per_kWh_EUR': var_total / total_energy if total_energy > 0 else 0,
                'total_energy_kWh': total_energy,
                'share_percent': 0
            })
        
        # Fixe Kosten
        if 'fixed_operational_costs' in breakdown and not breakdown['fixed_operational_costs'].empty:
            fix_total = breakdown['fixed_operational_costs']['total_fixed_costs_EUR'].sum()
            fix_count = len(breakdown['fixed_operational_costs'])
            if fix_total > 0:
                cost_summary.append({
                    'cost_type': 'Fixed Operational Costs',
                    'description': 'Capacity-dependent operational costs',
                    'total_EUR': fix_total,
                    'components_count': fix_count,
                    'avg_cost_per_component_EUR': fix_total / fix_count if fix_count > 0 else 0,
                    'share_percent': 0
                })
        
        df = pd.DataFrame(cost_summary)
        
        # Prozentualen Anteil berechnen
        if not df.empty:
            total_costs = df['total_EUR'].sum()
            if total_costs > 0:
                df['share_percent'] = (df['total_EUR'] / total_costs * 100).round(2)
        
        return df
    
    def _save_comprehensive_objective_breakdown(self, breakdown: Dict[str, pd.DataFrame]):
        """Speichert die umfassende Zielfunktions-Aufschlüsselung als Excel-Datei."""
        try:
            excel_file = self.output_dir / "comprehensive_objective_breakdown.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                
                # Sheet-Reihenfolge für bessere Übersicht
                sheet_order = [
                    ('cost_type_summary', 'Cost Type Summary'),
                    ('technology_totals', 'Technology Totals'),
                    ('technology_category_costs', 'Technology Categories'),
                    ('component_costs', 'Component Costs'),
                    ('investment_costs', 'Investment Details'),
                    ('variable_costs', 'Variable Cost Details'),
                    ('fixed_operational_costs', 'Fixed Cost Details'),
                    ('flow_costs', 'Flow-Level Costs'),
                    ('investment_analysis', 'Investment Analysis'),
                    ('cost_per_unit', 'Cost per Energy Unit')
                ]
                
                for breakdown_key, sheet_name in sheet_order:
                    if breakdown_key in breakdown and not breakdown[breakdown_key].empty:
                        df = breakdown[breakdown_key]
                        
                        # Formatierung für bessere Lesbarkeit
                        df_formatted = self._format_dataframe_for_excel(df)
                        
                        df_formatted.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Auto-adjust column widths
                        worksheet = writer.sheets[sheet_name]
                        for column in worksheet.columns:
                            max_length = 0
                            column = [cell for cell in column]
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            self.output_files.append(excel_file)
            self.logger.info(f"💰 Umfassende Zielfunktions-Aufschlüsselung gespeichert: {excel_file.name}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der umfassenden Zielfunktions-Aufschlüsselung: {e}")
    
    def _format_dataframe_for_excel(self, df):
        """Formatiert DataFrame für bessere Excel-Darstellung."""
        df_formatted = df.copy()
        
        # Runde numerische Spalten
        numeric_columns = df_formatted.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if 'percent' in col.lower():
                df_formatted[col] = df_formatted[col].round(2)
            elif 'EUR' in col or 'costs' in col.lower():
                df_formatted[col] = df_formatted[col].round(2)
            elif 'kW' in col or 'capacity' in col.lower():
                df_formatted[col] = df_formatted[col].round(1)
            elif 'factor' in col.lower():
                df_formatted[col] = df_formatted[col].round(4)
            else:
                df_formatted[col] = df_formatted[col].round(3)
        
        return df_formatted
    
    def _create_enhanced_summary(self, processed_results, energy_system, objective_breakdown):
        """Erstellt eine erweiterte Ergebnis-Zusammenfassung."""
        summary = {
            'simulation_period': {},
            'energy_flows': {},
            'comprehensive_costs': {},
            'investments': {},
            'system_info': {},
            'cost_breakdown_summary': {}
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
                'total_energy_MWh': flows_df.sum().sum() / 1000,
                'peak_power_MW': flows_df.max().max() / 1000,
                'number_of_flows': len(flows_df.columns)
            }
        
        # ✅ ERWEITERTE KOSTEN-ZUSAMMENFASSUNG
        if 'cost_type_summary' in objective_breakdown and not objective_breakdown['cost_type_summary'].empty:
            cost_summary = objective_breakdown['cost_type_summary']
            total_costs = cost_summary['total_EUR'].sum()
            
            summary['comprehensive_costs'] = {
                'total_system_costs_EUR': total_costs,
                'investment_costs_EUR': 0,
                'variable_costs_EUR': 0,
                'fixed_costs_EUR': 0
            }
            
            # Einzelne Kostenarten
            for _, row in cost_summary.iterrows():
                if 'Investment' in row['cost_type']:
                    summary['comprehensive_costs']['investment_costs_EUR'] = row['total_EUR']
                elif 'Variable' in row['cost_type']:
                    summary['comprehensive_costs']['variable_costs_EUR'] = row['total_EUR']
                elif 'Fixed' in row['cost_type']:
                    summary['comprehensive_costs']['fixed_costs_EUR'] = row['total_EUR']
        
        # Investment-Zusammenfassung
        if 'investment_costs' in objective_breakdown and not objective_breakdown['investment_costs'].empty:
            investments_df = objective_breakdown['investment_costs']
            summary['investments'] = {
                'number_of_investments': len(investments_df),
                'total_invested_capacity_kW': investments_df['invested_capacity_kW'].sum(),
                'total_annual_investment_costs_EUR': investments_df['annual_investment_costs_EUR'].sum(),
                'average_ep_costs_EUR_per_kW': investments_df['ep_costs_EUR_per_kW_per_year'].mean()
            }
        
        # Kosten-Aufschlüsselung-Zusammenfassung
        if 'technology_totals' in objective_breakdown and not objective_breakdown['technology_totals'].empty:
            tech_totals = objective_breakdown['technology_totals']
            
            # Top 3 Technologien nach Kosten
            top_technologies = tech_totals.head(3)
            summary['cost_breakdown_summary'] = {
                'most_expensive_technology': {
                    'name': top_technologies.iloc[0]['technology_type'] if len(top_technologies) > 0 else 'N/A',
                    'costs_EUR': top_technologies.iloc[0]['total_costs_EUR'] if len(top_technologies) > 0 else 0,
                    'share_percent': top_technologies.iloc[0]['share_of_total_percent'] if len(top_technologies) > 0 else 0
                },
                'top_3_technologies': [
                    {
                        'technology': row['technology_type'],
                        'costs_EUR': row['total_costs_EUR'],
                        'share_percent': row['share_of_total_percent']
                    }
                    for _, row in top_technologies.iterrows()
                ]
            }
        
        # System-Info
        if hasattr(energy_system, 'nodes'):
            nodes = energy_system.nodes
            summary['system_info'] = {
                'total_components': len(nodes),
                'buses': len([n for n in nodes if isinstance(n, solph.buses.Bus)]),
                'sources': len([n for n in nodes if isinstance(n, solph.components.Source)]),
                'sinks': len([n for n in nodes if isinstance(n, solph.components.Sink)]),
                'converters': len([n for n in nodes if isinstance(n, solph.components.Converter)])
            }
        
        return summary
    
    # ===== LEGACY METHODS (für Kompatibilität) =====
    
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
        """Berechnet Kostenaufschlüsselung (Legacy-Version für Kompatibilität)."""
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
        
        json_file = self.output_dir / "enhanced_summary.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.output_files.append(json_file)
        
        # Erweiterte Textformat-Zusammenfassung
        txt_file = self.output_dir / "enhanced_summary.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("ERWEITERTE OPTIMIERUNGSERGEBNISSE - ZUSAMMENFASSUNG\n")
            f.write("=" * 60 + "\n\n")
            
            for section, data in summary.items():
                f.write(f"{section.upper().replace('_', ' ')}:\n")
                f.write("-" * 40 + "\n")
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            f.write(f"  {key.replace('_', ' ').title()}:\n")
                            for sub_key, sub_value in value.items():
                                f.write(f"    {sub_key.replace('_', ' ').title()}: {sub_value}\n")
                        elif isinstance(value, list):
                            f.write(f"  {key.replace('_', ' ').title()}:\n")
                            for i, item in enumerate(value, 1):
                                if isinstance(item, dict):
                                    f.write(f"    {i}. {item.get('technology', item.get('name', 'N/A'))}: ")
                                    f.write(f"{item.get('costs_EUR', 0):,.2f} € ")
                                    f.write(f"({item.get('share_percent', 0):.1f}%)\n")
                                else:
                                    f.write(f"    {i}. {item}\n")
                        else:
                            f.write(f"  {key.replace('_', ' ').title()}: {value}\n")
                else:
                    f.write(f"  {data}\n")
                
                f.write("\n")
        
        self.output_files.append(txt_file)
        self.logger.debug(f"      💾 {json_file.name}, {txt_file.name}")


# Test-Funktion für den erweiterten Results Processor
def test_enhanced_results_processor():
    """Testfunktion für den Enhanced Results-Processor."""
    import tempfile
    
    # Dummy-Ergebnisse erstellen
    dummy_results = {
        ('pv_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series([30, 35, 40], index=pd.date_range('2025-01-01', periods=3, freq='h'))
            },
            'scalars': {
                'invest': 100,
                'variable_costs': 0.0
            }
        },
        ('grid_import', 'el_bus'): {
            'sequences': {
                'flow': pd.Series([10, 15, 20], index=pd.date_range('2025-01-01', periods=3, freq='h'))
            },
            'scalars': {
                'variable_costs': 0.25
            }
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'output_format': 'xlsx', 'debug_mode': True}
        processor = EnhancedResultsProcessor(Path(temp_dir), settings)
        
        # Dummy Energy System
        class DummyNode:
            def __init__(self, label, node_type):
                self.label = label
                self._type = node_type
        
        class DummyEnergySystem:
            def __init__(self):
                self.timeindex = pd.date_range('2025-01-01', periods=3, freq='h')
                self.nodes = [
                    DummyNode('pv_plant', 'Source'),
                    DummyNode('el_bus', 'Bus'),
                    DummyNode('grid_import', 'Source')
                ]
        
        energy_system = DummyEnergySystem()
        excel_data = {
            'sources': pd.DataFrame({
                'label': ['pv_plant', 'grid_import'],
                'investment_costs': [800, ''],
                'lifetime': [25, ''],
                'interest_rate': [0.05, '']
            })
        }
        
        try:
            results = processor.process_results(dummy_results, energy_system, excel_data)
            print("✅ Enhanced Results-Processor Test erfolgreich!")
            print(f"Erstellte Dateien: {len(processor.output_files)}")
            
            if 'objective_breakdown' in results:
                breakdown = results['objective_breakdown']
                print(f"Zielfunktions-Breakdown-Kategorien: {list(breakdown.keys())}")
                
                if 'cost_type_summary' in breakdown:
                    print("Kostenarten-Zusammenfassung:")
                    print(breakdown['cost_type_summary'].to_string(index=False))
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_results_processor() 0,
                            'flows_count': 0,
                            'total_capacity_kW': 0,
                            'total_energy_kWh': 0,
                        }
                
                # Aggregiere Kosten für diese Komponente
                if 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Investment-Kosten
                    if 'invest' in scalars and scalars['invest'] > 0:
                        investment_params = self._get_comprehensive_investment_params(
                            source, target, energy_system, excel_data
                        )
                        if investment_params:
                            annual_inv_costs = investment_params['ep_costs'] * scalars['invest']
                            component_costs[str(component_label)]['investment_costs_EUR'] += annual_inv_costs
                            component_costs[str(component_label)]['total_capacity_kW'] += scalars['invest']
                    
                    # Variable Kosten
                    if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                        flow_values = flow_results['sequences']['flow']
                        total_energy = flow_values.sum()
                        
                        var_costs_info = self._get_comprehensive_variable_costs(
                            source, target, energy_system, excel_data
                        )
                        if var_costs_info and var_costs_info['var_costs'] != 0:
                            var_costs_total = total_energy * var_costs_info['var_costs']
                            component_costs[str(component_label)]['variable_costs_EUR'] += var_costs_total
                        
                        component_costs[str(component_label)]['total_energy_kWh'] += total_energy
                        component_costs[str(component_label)]['flows_count'] += 1
        
        # Berechne Gesamtkosten und zusätzliche Metriken
        component_data = []
        for comp_label, comp_data in component_costs.items():
            comp_data['total_costs_EUR'] = (
                comp_data['investment_costs_EUR'] + 
                comp_data['variable_costs_EUR'] + 
                comp_data['fixed_costs_EUR']
            )
            
            # Spezifische Kosten
            if comp_data['total_capacity_kW'] > 0:
                comp_data['specific_costs_EUR_per_kW'] = comp_data['total_costs_EUR'] / comp_data['total_capacity_kW']
            else:
                comp_data['specific_costs_EUR_per_kW'] = 0
            
            if comp_data['total_energy_kWh'] > 0:
                comp_data['specific_costs_EUR_per_kWh'] = comp_data['total_costs_EUR'] / comp_data['total_energy_kWh']
            else:
                comp_data['specific_costs_EUR_per_kWh'] = 0
            
            component_data.append(comp_data)
        
        df = pd.DataFrame(component_data)
        
        if not df.empty:
            df = df.sort_values('total_costs_EUR', ascending=False)
            
            # Relative Anteile
            total_costs = df['total_costs_EUR'].sum()
            if total_costs > 0:
                df['cost_share_percent'] = (df['total_costs_EUR'] / total_costs * 100).round(2)
        
        return df
    
    def _calculate_technology_category_costs(self, breakdown: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """✅ NEU: Berechnet Kosten nach Technologie-Kategorien."""
        category_costs = {}
        
        # Sammle Kosten aus allen Breakdown-Kategorien
        for breakdown_type, df in breakdown.items():
            if df.empty or 'technology_category' not in df.columns:
                continue
            
            for _, row in df.iterrows():
                category = row['technology_category']
                
                if category not in category_costs:
                    category_costs[category] = {
                        'technology_category': category,
                        'investment_costs_EUR': 0,
                        'variable_costs_EUR': 0,
                        'fixed_costs_EUR': 0,
                        'total_costs_EUR': 0,
                        'components_count': 0,
                        'total_capacity_kW': 0,
                        'total_energy_kWh': 0,
                    }
                
                # Kosten nach Typ addieren
                if breakdown_type == 'investment_costs':
                    category_costs[category]['investment_costs_EUR'] += row.get('annual_investment_costs_EUR', 0)
                    category_costs[category]['total_capacity_kW'] += row.get('invested_capacity_kW', 0)
                elif breakdown_type == 'variable_costs':
                    category_costs[category]['variable_costs_EUR'] += row.get('total_variable_costs_EUR', 0)
                    category_costs[category]['total_energy_kWh'] += row.get('total_energy_kWh', 0)
                elif breakdown_type == 'fixed_operational_costs':
                    category_costs[category]['fixed_costs_EUR'] += row.get('total_fixed_costs_EUR', 0)
                
                category_costs[category]['components_count'] += 1
        
        # Gesamtkosten berechnen
        category_data = []
        for category, data in category_costs.items():
            data['total_costs_EUR'] = (
                data['investment_costs_EUR'] + 
                data['variable_costs_EUR'] + 
                data['fixed_costs_EUR']
            )
            
            # Spezifische Metriken
            if data['total_capacity_kW'] > 0:
                data['avg_specific_investment_EUR_per_kW'] = data['investment_costs_EUR'] / data['total_capacity_kW']
            else:
                data['avg_specific_investment_EUR_per_kW'] = 0
            
            if data['total_energy_kWh'] > 0:
                data['avg_variable_costs_EUR_per_kWh'] = data['variable_costs_EUR'] / data['total_energy_kWh']
            else:
                data['avg_variable_costs_EUR_per_kWh'] = 0
            
            category_data.append(data)
        
        df = pd.DataFrame(category_data)
        
        if not df.empty:
            df = df.sort_values('total_costs_EUR', ascending=False)
            
            # Relative Anteile
            total_costs = df['total_costs_EUR'].sum()
            if total_costs > 0:
                df['category_share_percent'] = (df['total_costs_EUR'] / total_costs * 100).round(2)
        
        return df
    
    def _calculate_flow_level_costs(self, results: Dict[str, Any], 
                                  energy_system: Any, 
                                  excel_data: Dict[str, Any]) -> pd.DataFrame:
        """✅ NEU: Detaillierte Kosten auf Flow-Level."""
        flow_data = []
        
        for (source, target), flow_results in results.items():
            flow_entry = {
                'source': str(source),
                'target': str(target),
                'connection': f"{source} → {target}",
                'flow_type': self._determine_flow_type(source, target, energy_system),
                
                # Kosten-Komponenten
                'investment_costs_EUR': 0,
                'variable_costs_EUR': 0,
                'fixed_costs_EUR': 0,
                'total_costs_EUR': 0,
                
                # Flow-Eigenschaften
                'has_investment': False,
                'has_variable_costs': False,
                'has_fixed_costs': False,
                'nominal_capacity_kW': 0,
                'total_energy_kWh': 0,
            }
            
            # Investment-Kosten
            if 'scalars' in flow_results and 'invest' in flow_results['scalars']:
                if flow_results['scalars']['invest'] > 0:
                    investment_params = self._get_comprehensive_investment_params(
                        source, target, energy_system, excel_data
                    )
                    if investment_params:
                        flow_entry['investment_costs_EUR'] = (
                            investment_params['ep_costs'] * flow_results['scalars']['invest']
                        )
                        flow_entry['has_investment'] = True
                        flow_entry['nominal_capacity_kW'] = flow_results['scalars']['invest']
            
            # Variable Kosten
            if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                flow_values = flow_results['sequences']['flow']
                total_energy = flow_values.sum()
                flow_entry['total_energy_kWh'] = total_energy
                
                var_costs_info = self._get_comprehensive_variable_costs(
                    source, target, energy_system, excel_data
                )
                if var_costs_info and var_costs_info['var_costs'] != 0:
                    flow_entry['variable_costs_EUR'] = total_energy * var_costs_info['var_costs']
                    flow_entry['has_variable_costs'] = True
            
            # Gesamtkosten
            flow_entry['total_costs_EUR'] = (
                flow_entry['investment_costs_EUR'] + 
                flow_entry['variable_costs_EUR'] + 
                flow_entry['fixed_costs_EUR']
            )
            
            # Spezifische Kosten
            if flow_entry['total_energy_kWh'] > 0:
                flow_entry['specific_costs_EUR_per_kWh'] = (
                    flow_entry['total_costs_EUR'] / flow_entry['total_energy_kWh']
                )
            else:
                flow_entry['specific_costs_EUR_per_kWh'] = 0
            
            flow_data.append(flow_entry)
        
        df = pd.DataFrame(flow_data)
        
        if not df.empty:
            df = df.sort_values('total_costs_EUR', ascending=False)
            
            # Nur Flows mit Kosten > 0 anzeigen
            df = df[df['total_costs_EUR'] > 0].copy()
            
            if not df.empty:
                total_costs = df['total_costs_EUR'].sum()
                df['flow_share_percent'] = (df['total_costs_EUR'] / total_costs * 100).round(2)
        
        return df
    
    def _calculate_investment_analysis(self, breakdown: Dict[str, pd.DataFrame], 
                                     excel_data: Dict[str, Any]) -> pd.DataFrame:
        """✅ NEU: Investment-Analyse mit Vergleich zu Excel-Parametern."""
        if 'investment_costs' not in breakdown or breakdown['investment_costs'].empty:
            return pd.DataFrame()
        
        inv_df = breakdown['investment_costs']
        analysis_data = []
        
        for _, row in inv_df.iterrows():
            analysis_entry = {
                'component_label': row['component_label'],
                'technology_type': row['technology_type'],
                
                # Investment-Ergebnisse
                'invested_capacity_kW': row['invested_capacity_kW'],
                'annual_investment_costs_EUR': row['annual_investment_costs_EUR'],
                
                # Investment-Parameter
                'original_investment_costs_EUR_per_kW': row.get('original_investment_costs_EUR_per_kW', 0),
                'ep_costs_EUR_per_kW_per_year': row['ep_costs_EUR_per_kW_per_year'],
                'lifetime_years': row.get('lifetime_years', 0),
                'interest_rate_percent': row.get('interest_rate_percent', 0),
                
                # Investment-Effizienz
                'investment_utilization_percent': 0,
                'investment_efficiency_score': 0,
                'payback_period_years': 0,
            }
            
            # Berechne Investment-Effizienz-Metriken
            invest_max = row.get('invest_max_kW', np.inf)
            if invest_max != np.inf and invest_max > 0:
                analysis_entry['investment_utilization_percent'] = (
                    row['invested_capacity_kW'] / invest_max * 100
                )
            
            # Payback-Periode (vereinfacht)
            if row.get('original_investment_costs_EUR_per_kW', 0) > 0:
                analysis_entry['payback_period_years'] = (
                    row['original_investment_costs_EUR_per_kW'] / 
                    row['ep_costs_EUR_per_kW_per_year']
                )
            
            analysis_data.append(analysis_entry)
        
        df = pd.DataFrame(analysis_data)
        
        if not df.empty:
            df = df.sort_values('annual_investment_costs_EUR', ascending=False)
        
        return df
    
    def _calculate_cost_per_energy_unit(self, breakdown: Dict[str, pd.DataFrame], 
                                      results: Dict[str, Any]) -> pd.DataFrame:
        """✅ NEU: Kosten pro Energieeinheit nach Technologien."""
        cost_per_unit_data = []
        
        # Aggregiere Daten aus variable_costs breakdown
        if 'variable_costs' in breakdown and not breakdown['variable_costs'].empty:
            var_df = breakdown['variable_costs']
            
            # Gruppiere nach Technologie-Typ
            tech_groups = var_df.groupby('technology_type').agg({
                'total_energy_kWh': 'sum',
                'total_variable_costs_EUR': 'sum'
            }).reset_index()
            
            for _, row in tech_groups.iterrows():
                if row['total_energy_kWh'] > 0:
                    cost_per_unit_data.append({
                        'technology_type': row['technology_type'],
                        'cost_category': 'Variable',
                        'total_energy_kWh': row['total_energy_kWh'],
                        'total_costs_EUR':