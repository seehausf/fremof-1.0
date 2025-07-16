#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Erweiterte Kostenanalyse und Energiesystem-Export
===================================================================

Vollständige Kostenaufschlüsselung durch Abgleich von EnergySystem-Objekten
mit Optimierungsergebnissen und kompletter Energiesystem-Export.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

try:
    import oemof.solph as solph
    from oemof.solph._options import Investment, NonConvex
except ImportError:
    solph = None


class EnergySystemAnalyzer:
    """Analysiert EnergySystem-Objekte und berechnet detaillierte Kosten."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """Initialisiert den Analyzer."""
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Caches für Performance
        self._system_export_cache = None
        self._cost_mapping_cache = None
    
    def export_complete_energy_system(self, energy_system: Any, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exportiert das komplette EnergySystem als strukturiertes Dictionary.
        
        Args:
            energy_system: oemof.solph EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Vollständiger System-Export
        """
        self.logger.info("🔍 Exportiere komplettes Energiesystem...")
        
        system_export = {
            'metadata': self._export_system_metadata(energy_system),
            'timeindex': self._export_timeindex(energy_system),
            'nodes': self._export_all_nodes(energy_system),
            'flows': self._export_all_flows(energy_system),
            'investments': self._export_investment_definitions(energy_system),
            'nonconvex': self._export_nonconvex_definitions(energy_system),
            'cost_parameters': self._export_cost_parameters(energy_system),
            'original_excel_data': self._export_excel_reference(excel_data),
            'system_statistics': self._calculate_system_statistics(energy_system)
        }
        
        # Cache für spätere Verwendung
        self._system_export_cache = system_export
        
        # Als JSON speichern
        self._save_system_export(system_export)
        
        self.logger.info("✅ Energiesystem-Export abgeschlossen")
        return system_export
    
    def calculate_comprehensive_costs(self, results: Dict[str, Any], 
                                    energy_system: Any, 
                                    excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Berechnet vollständige Kostenaufschlüsselung durch Abgleich 
        von EnergySystem-Parametern mit Optimierungsergebnissen.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: EnergySystem-Objekt
            excel_data: Original Excel-Daten
            
        Returns:
            Detaillierte Kostenaufschlüsselung
        """
        self.logger.info("💰 Berechne detaillierte Kostenaufschlüsselung...")
        
        # System-Export laden (falls nicht gecacht)
        if self._system_export_cache is None:
            system_export = self.export_complete_energy_system(energy_system, excel_data)
        else:
            system_export = self._system_export_cache
        
        cost_breakdown = {
            'investment_costs': self._calculate_investment_costs_detailed(results, system_export),
            'variable_costs': self._calculate_variable_costs_detailed(results, system_export),
            'fixed_costs': self._calculate_fixed_costs_detailed(results, system_export),
            'objective_breakdown': self._reconstruct_objective_function(results, system_export),
            'cost_by_technology': self._calculate_costs_by_technology(results, system_export),
            'cost_by_component': self._calculate_costs_by_component(results, system_export),
            'cost_validation': self._validate_cost_calculation(results, system_export)
        }
        
        # Gesamtkostenübersicht
        cost_breakdown['summary'] = self._create_cost_summary(cost_breakdown)
        
        # Als Excel und JSON speichern
        self._save_cost_breakdown(cost_breakdown)
        
        self.logger.info("✅ Kostenanalyse abgeschlossen")
        return cost_breakdown
    
    def _export_system_metadata(self, energy_system: Any) -> Dict[str, Any]:
        """Exportiert System-Metadaten."""
        return {
            'creation_timestamp': pd.Timestamp.now().isoformat(),
            'oemof_version': getattr(solph, '__version__', 'unknown'),
            'total_nodes': len(energy_system.nodes) if hasattr(energy_system, 'nodes') else 0,
            'timeindex_periods': len(energy_system.timeindex) if hasattr(energy_system, 'timeindex') else 0,
            'system_type': 'EnergySystem'
        }
    
    def _export_timeindex(self, energy_system: Any) -> Dict[str, Any]:
        """Exportiert Zeitindex-Informationen."""
        if not hasattr(energy_system, 'timeindex'):
            return {}
        
        timeindex = energy_system.timeindex
        
        return {
            'start': timeindex[0].isoformat() if len(timeindex) > 0 else None,
            'end': timeindex[-1].isoformat() if len(timeindex) > 0 else None,
            'periods': len(timeindex),
            'frequency': pd.infer_freq(timeindex),
            'first_10_timestamps': [ts.isoformat() for ts in timeindex[:10]],
            'last_10_timestamps': [ts.isoformat() for ts in timeindex[-10:]]
        }
    
    def _export_all_nodes(self, energy_system: Any) -> Dict[str, Dict[str, Any]]:
        """Exportiert alle Nodes mit vollständigen Eigenschaften."""
        nodes_export = {}
        
        if not hasattr(energy_system, 'nodes'):
            return nodes_export
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            node_export = {
                'label': node_label,
                'type': type(node).__name__,
                'module': type(node).__module__,
                'attributes': self._export_node_attributes(node),
                'inputs': self._export_node_connections(node, 'inputs'),
                'outputs': self._export_node_connections(node, 'outputs')
            }
            
            nodes_export[node_label] = node_export
        
        return nodes_export
    
    def _export_node_attributes(self, node: Any) -> Dict[str, Any]:
        """Exportiert alle Attribute eines Nodes."""
        attributes = {}
        
        # Basis-Attribute
        basic_attrs = ['label']
        for attr in basic_attrs:
            if hasattr(node, attr):
                attributes[attr] = str(getattr(node, attr))
        
        # Spezielle Attribute je nach Node-Typ
        if isinstance(node, solph.buses.Bus):
            # Bus hat meist keine speziellen Attribute
            attributes['bus_type'] = 'Bus'
        
        elif isinstance(node, solph.components.Source):
            attributes['component_type'] = 'Source'
        
        elif isinstance(node, solph.components.Sink):
            attributes['component_type'] = 'Sink'
        
        elif isinstance(node, solph.components.Converter):
            attributes['component_type'] = 'Converter'
            # Conversion factors
            if hasattr(node, 'conversion_factors'):
                attributes['conversion_factors'] = {
                    str(k.label): v for k, v in node.conversion_factors.items()
                }
        
        return attributes
    
    def _export_node_connections(self, node: Any, direction: str) -> Dict[str, Dict[str, Any]]:
        """Exportiert Input- oder Output-Verbindungen eines Nodes."""
        connections = {}
        
        if not hasattr(node, direction):
            return connections
        
        connections_dict = getattr(node, direction)
        
        for connected_node, flow in connections_dict.items():
            connection_key = str(connected_node.label)
            
            connections[connection_key] = {
                'connected_to': str(connected_node.label),
                'connected_type': type(connected_node).__name__,
                'flow_properties': self._export_flow_properties(flow)
            }
        
        return connections
    
    def _export_flow_properties(self, flow: Any) -> Dict[str, Any]:
        """Exportiert alle Eigenschaften eines Flows."""
        properties = {}
        
        # Standard Flow-Attribute
        flow_attrs = [
            'nominal_capacity', 'variable_costs', 'min', 'max', 
            'fix', 'summed_max', 'summed_min', 'positive_gradient_limit',
            'negative_gradient_limit', 'full_load_time_max', 'full_load_time_min'
        ]
        
        for attr in flow_attrs:
            if hasattr(flow, attr):
                value = getattr(flow, attr)
                
                if value is not None:
                    if isinstance(value, Investment):
                        properties[attr] = self._export_investment_properties(value)
                    elif isinstance(value, NonConvex):
                        properties[attr] = self._export_nonconvex_properties(value)
                    elif isinstance(value, (list, np.ndarray)):
                        # Zeitreihen als Statistiken speichern
                        properties[attr] = {
                            'type': 'timeseries',
                            'length': len(value),
                            'min': float(np.min(value)),
                            'max': float(np.max(value)),
                            'mean': float(np.mean(value)),
                            'sum': float(np.sum(value)),
                            'first_10': [float(v) for v in value[:10]],
                            'last_10': [float(v) for v in value[-10:]]
                        }
                    else:
                        try:
                            # Versuche JSON-serialisierbar zu machen
                            properties[attr] = float(value) if isinstance(value, (int, float)) else str(value)
                        except:
                            properties[attr] = str(value)
        
        return properties
    
    def _export_investment_properties(self, investment: Any) -> Dict[str, Any]:
        """Exportiert Investment-Eigenschaften."""
        properties = {'type': 'Investment'}
        
        investment_attrs = [
            'ep_costs', 'minimum', 'maximum', 'existing', 'offset',
            'nonconvex', 'overall_maximum', 'overall_minimum'
        ]
        
        for attr in investment_attrs:
            if hasattr(investment, attr):
                value = getattr(investment, attr)
                if value is not None:
                    if isinstance(value, NonConvex):
                        properties[attr] = self._export_nonconvex_properties(value)
                    else:
                        try:
                            properties[attr] = float(value) if isinstance(value, (int, float)) else str(value)
                        except:
                            properties[attr] = str(value)
        
        return properties
    
    def _export_nonconvex_properties(self, nonconvex: Any) -> Dict[str, Any]:
        """Exportiert NonConvex-Eigenschaften."""
        properties = {'type': 'NonConvex'}
        
        nonconvex_attrs = [
            'minimum_uptime', 'minimum_downtime', 'startup_costs', 'shutdown_costs',
            'maximum_startups', 'maximum_shutdowns', 'initial_status',
            'activity_costs', 'inactivity_costs'
        ]
        
        for attr in nonconvex_attrs:
            if hasattr(nonconvex, attr):
                value = getattr(nonconvex, attr)
                if value is not None:
                    try:
                        properties[attr] = float(value) if isinstance(value, (int, float)) else str(value)
                    except:
                        properties[attr] = str(value)
        
        return properties
    
    def _export_all_flows(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle Flows mit vollständigen Informationen."""
        flows_export = []
        
        if not hasattr(energy_system, 'nodes'):
            return flows_export
        
        for node in energy_system.nodes:
            # Output-Flows
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    flow_export = {
                        'source': str(node.label),
                        'target': str(output_node.label),
                        'source_type': type(node).__name__,
                        'target_type': type(output_node).__name__,
                        'direction': 'output',
                        'properties': self._export_flow_properties(flow)
                    }
                    flows_export.append(flow_export)
        
        return flows_export
    
    def _export_investment_definitions(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle Investment-Definitionen."""
        investments = []
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Input-Flows prüfen
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                        investment_def = {
                            'component': node_label,
                            'flow_direction': 'input',
                            'connection': f"{input_node.label} → {node_label}",
                            'investment_parameters': self._export_investment_properties(flow.nominal_capacity)
                        }
                        investments.append(investment_def)
            
            # Output-Flows prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                        investment_def = {
                            'component': node_label,
                            'flow_direction': 'output',
                            'connection': f"{node_label} → {output_node.label}",
                            'investment_parameters': self._export_investment_properties(flow.nominal_capacity)
                        }
                        investments.append(investment_def)
        
        return investments
    
    def _export_nonconvex_definitions(self, energy_system: Any) -> List[Dict[str, Any]]:
        """Exportiert alle NonConvex-Definitionen."""
        nonconvex_list = []
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Input-Flows prüfen
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_def = {
                            'component': node_label,
                            'flow_direction': 'input',
                            'connection': f"{input_node.label} → {node_label}",
                            'nonconvex_parameters': self._export_nonconvex_properties(flow.nonconvex)
                        }
                        nonconvex_list.append(nonconvex_def)
            
            # Output-Flows prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_def = {
                            'component': node_label,
                            'flow_direction': 'output',
                            'connection': f"{node_label} → {output_node.label}",
                            'nonconvex_parameters': self._export_nonconvex_properties(flow.nonconvex)
                        }
                        nonconvex_list.append(nonconvex_def)
        
        return nonconvex_list
    
    def _export_cost_parameters(self, energy_system: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Exportiert alle kostenrelevanten Parameter."""
        cost_params = {
            'variable_costs': [],
            'investment_costs': [],
            'fixed_costs': [],
            'startup_costs': [],
            'shutdown_costs': []
        }
        
        for node in energy_system.nodes:
            node_label = str(node.label)
            
            # Alle Flows durchgehen
            flows_to_check = []
            
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    flows_to_check.append((f"{input_node.label} → {node_label}", flow))
            
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    flows_to_check.append((f"{node_label} → {output_node.label}", flow))
            
            for connection, flow in flows_to_check:
                # Variable Kosten
                if hasattr(flow, 'variable_costs') and flow.variable_costs is not None:
                    cost_params['variable_costs'].append({
                        'component': node_label,
                        'connection': connection,
                        'variable_costs': float(flow.variable_costs)
                    })
                
                # Investment-Kosten (EP-Costs)
                if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                    investment = flow.nominal_capacity
                    if hasattr(investment, 'ep_costs') and investment.ep_costs is not None:
                        cost_params['investment_costs'].append({
                            'component': node_label,
                            'connection': connection,
                            'ep_costs': float(investment.ep_costs),
                            'existing': float(getattr(investment, 'existing', 0)),
                            'minimum': float(getattr(investment, 'minimum', 0)),
                            'maximum': float(getattr(investment, 'maximum', np.inf))
                        })
                
                # NonConvex-Kosten
                if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                    nonconvex = flow.nonconvex
                    
                    if hasattr(nonconvex, 'startup_costs') and nonconvex.startup_costs is not None:
                        cost_params['startup_costs'].append({
                            'component': node_label,
                            'connection': connection,
                            'startup_costs': float(nonconvex.startup_costs)
                        })
                    
                    if hasattr(nonconvex, 'shutdown_costs') and nonconvex.shutdown_costs is not None:
                        cost_params['shutdown_costs'].append({
                            'component': node_label,
                            'connection': connection,
                            'shutdown_costs': float(nonconvex.shutdown_costs)
                        })
        
        return cost_params
    
    def _export_excel_reference(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exportiert Referenz zu originalen Excel-Daten."""
        excel_ref = {
            'sheets_available': list(excel_data.keys()),
            'timeindex_info': excel_data.get('timeindex_info', {}),
            'data_summary': {}
        }
        
        # Zusammenfassung der Excel-Sheets
        for sheet_name, data in excel_data.items():
            if isinstance(data, pd.DataFrame):
                excel_ref['data_summary'][sheet_name] = {
                    'rows': len(data),
                    'columns': list(data.columns),
                    'shape': data.shape
                }
        
        return excel_ref
    
    def _calculate_system_statistics(self, energy_system: Any) -> Dict[str, Any]:
        """Berechnet System-Statistiken."""
        stats = {
            'total_nodes': 0,
            'total_flows': 0,
            'node_types': {},
            'investment_flows': 0,
            'nonconvex_flows': 0,
            'cost_relevant_flows': 0
        }
        
        if hasattr(energy_system, 'nodes'):
            stats['total_nodes'] = len(energy_system.nodes)
            
            for node in energy_system.nodes:
                node_type = type(node).__name__
                stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
                
                # Flows zählen
                if hasattr(node, 'outputs'):
                    for flow in node.outputs.values():
                        stats['total_flows'] += 1
                        
                        if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                            stats['investment_flows'] += 1
                        
                        if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                            stats['nonconvex_flows'] += 1
                        
                        if (hasattr(flow, 'variable_costs') and flow.variable_costs is not None and flow.variable_costs != 0):
                            stats['cost_relevant_flows'] += 1
        
        return stats
    
    def _calculate_investment_costs_detailed(self, results: Dict[str, Any], 
                                           system_export: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Berechnet detaillierte Investment-Kosten."""
        investment_costs = []
        
        # Investment-Definitionen aus System-Export
        investments = system_export.get('investments', [])
        
        for investment_def in investments:
            component = investment_def['component']
            connection = investment_def['connection']
            params = investment_def['investment_parameters']
            
            # Suche entsprechende Results
            for (source, target), flow_results in results.items():
                result_connection = f"{source} → {target}"
                
                if result_connection == connection and 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Investierte Kapazität
                    invested_capacity = scalars.get('invest', 0)
                    
                    if invested_capacity > 0:
                        # EP-Costs aus System-Export
                        ep_costs = params.get('ep_costs', 0)
                        
                        # Jährliche Investment-Kosten
                        annual_investment_costs = ep_costs * invested_capacity
                        
                        investment_cost = {
                            'component': component,
                            'connection': connection,
                            'invested_capacity_kW': invested_capacity,
                            'ep_costs_EUR_per_kW_per_year': ep_costs,
                            'annual_investment_costs_EUR': annual_investment_costs,
                            'existing_capacity_kW': params.get('existing', 0),
                            'investment_minimum_kW': params.get('minimum', 0),
                            'investment_maximum_kW': params.get('maximum', np.inf),
                            'total_capacity_kW': invested_capacity + params.get('existing', 0)
                        }
                        
                        investment_costs.append(investment_cost)
        
        return investment_costs
    
    def _calculate_variable_costs_detailed(self, results: Dict[str, Any], 
                                         system_export: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Berechnet detaillierte variable Kosten."""
        variable_costs = []
        
        # Variable Kosten-Parameter aus System-Export
        var_cost_params = system_export.get('cost_parameters', {}).get('variable_costs', [])
        
        for cost_param in var_cost_params:
            component = cost_param['component']
            connection = cost_param['connection']
            var_costs_rate = cost_param['variable_costs']
            
            # Suche entsprechende Results
            for (source, target), flow_results in results.items():
                result_connection = f"{source} → {target}"
                
                if result_connection == connection and 'sequences' in flow_results:
                    flow_values = flow_results['sequences'].get('flow')
                    
                    if flow_values is not None:
                        total_energy = flow_values.sum()
                        
                        if total_energy > 0 and var_costs_rate != 0:
                            total_variable_costs = total_energy * var_costs_rate
                            
                            variable_cost = {
                                'component': component,
                                'connection': connection,
                                'total_energy_kWh': total_energy,
                                'variable_costs_EUR_per_kWh': var_costs_rate,
                                'total_variable_costs_EUR': total_variable_costs,
                                'max_power_kW': flow_values.max(),
                                'average_power_kW': flow_values.mean(),
                                'operating_hours': (flow_values > 0).sum(),
                                'capacity_factor': flow_values.mean() / flow_values.max() if flow_values.max() > 0 else 0
                            }
                            
                            variable_costs.append(variable_cost)
        
        return variable_costs
    
    def _calculate_fixed_costs_detailed(self, results: Dict[str, Any], 
                                      system_export: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Berechnet detaillierte fixe Kosten."""
        # Placeholder für fixe Kosten (nicht Standard in oemof.solph)
        return []
    
    def _reconstruct_objective_function(self, results: Dict[str, Any], 
                                       system_export: Dict[str, Any]) -> Dict[str, Any]:
        """Rekonstruiert die Zielfunktion aus den Einzelkomponenten."""
        
        objective_breakdown = {
            'total_objective_value': 0,
            'investment_costs_total': 0,
            'variable_costs_total': 0,
            'fixed_costs_total': 0,
            'startup_costs_total': 0,
            'shutdown_costs_total': 0,
            'breakdown_by_component': {}
        }
        
        # Investment-Kosten summieren
        investment_costs = self._calculate_investment_costs_detailed(results, system_export)
        for inv_cost in investment_costs:
            objective_breakdown['investment_costs_total'] += inv_cost['annual_investment_costs_EUR']
        
        # Variable Kosten summieren
        variable_costs = self._calculate_variable_costs_detailed(results, system_export)
        for var_cost in variable_costs:
            objective_breakdown['variable_costs_total'] += var_cost['total_variable_costs_EUR']
        
        # Gesamtzielfunktionswert
        objective_breakdown['total_objective_value'] = (
            objective_breakdown['investment_costs_total'] + 
            objective_breakdown['variable_costs_total'] + 
            objective_breakdown['fixed_costs_total'] +
            objective_breakdown['startup_costs_total'] +
            objective_breakdown['shutdown_costs_total']
        )
        
        return objective_breakdown
    
    def _calculate_costs_by_technology(self, results: Dict[str, Any], 
                                     system_export: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Gruppiert Kosten nach Technologie-Typ."""
        tech_costs = {}
        
        # Investment-Kosten nach Technologie
        investment_costs = self._calculate_investment_costs_detailed(results, system_export)
        for inv_cost in investment_costs:
            component = inv_cost['component']
            tech_type = self._determine_technology_type(component)
            
            if tech_type not in tech_costs:
                tech_costs[tech_type] = {'investment': 0, 'variable': 0, 'total': 0}
            
            tech_costs[tech_type]['investment'] += inv_cost['annual_investment_costs_EUR']
        
        # Variable Kosten nach Technologie
        variable_costs = self._calculate_variable_costs_detailed(results, system_export)
        for var_cost in variable_costs:
            component = var_cost['component']
            tech_type = self._determine_technology_type(component)
            
            if tech_type not in tech_costs:
                tech_costs[tech_type] = {'investment': 0, 'variable': 0, 'total': 0}
            
            tech_costs[tech_type]['variable'] += var_cost['total_variable_costs_EUR']
        
        # Gesamtkosten berechnen
        for tech_type in tech_costs:
            tech_costs[tech_type]['total'] = (
                tech_costs[tech_type]['investment'] + 
                tech_costs[tech_type]['variable']
            )
        
        return tech_costs
    
    def _calculate_costs_by_component(self, results: Dict[str, Any], 
                                    system_export: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Gruppiert Kosten nach Komponente."""
        component_costs = {}
        
        # Investment-Kosten nach Komponente
        investment_costs = self._calculate_investment_costs_detailed(results, system_export)
        for inv_cost in investment_costs:
            component = inv_cost['component']
            
            if component not in component_costs:
                component_costs[component] = {'investment': 0, 'variable': 0, 'total': 0}
            
            component_costs[component]['investment'] += inv_cost['annual_investment_costs_EUR']
        
        # Variable Kosten nach Komponente
        variable_costs = self._calculate_variable_costs_detailed(results, system_export)
        for var_cost in variable_costs:
            component = var_cost['component']
            
            if component not in component_costs:
                component_costs[component] = {'investment': 0, 'variable': 0, 'total': 0}
            
            component_costs[component]['variable'] += var_cost['total_variable_costs_EUR']
        
        # Gesamtkosten berechnen
        for component in component_costs:
            component_costs[component]['total'] = (
                component_costs[component]['investment'] + 
                component_costs[component]['variable']
            )
        
        return component_costs
    
    def _validate_cost_calculation(self, results: Dict[str, Any], 
                                 system_export: Dict[str, Any]) -> Dict[str, Any]:
        """Validiert die Kostenberechnung."""
        validation = {
            'total_flows_checked': 0,
            'flows_with_costs': 0,
            'flows_with_investment': 0,
            'cost_calculation_complete': True,
            'missing_cost_data': [],
            'warnings': []
        }
        
        # Prüfe alle Flows in den Results
        for (source, target), flow_results in results.items():
            validation['total_flows_checked'] += 1
            
            connection = f"{source} → {target}"
            has_cost_data = False
            
            # Prüfe auf Investment
            if 'scalars' in flow_results and flow_results['scalars'].get('invest', 0) > 0:
                validation['flows_with_investment'] += 1
                has_cost_data = True
            
            # Prüfe auf variable Kosten (über System-Export)
            var_cost_params = system_export.get('cost_parameters', {}).get('variable_costs', [])
            for cost_param in var_cost_params:
                if cost_param['connection'] == connection and cost_param['variable_costs'] != 0:
                    has_cost_data = True
                    break
            
            if has_cost_data:
                validation['flows_with_costs'] += 1
            else:
                # Prüfe ob es ein Cost-neutraler Flow ist (z.B. Bus-zu-Bus)
                if 'bus' not in str(source).lower() or 'bus' not in str(target).lower():
                    validation['missing_cost_data'].append(connection)
        
        # Warnungen generieren
        if validation['missing_cost_data']:
            validation['warnings'].append(
                f"{len(validation['missing_cost_data'])} Flows ohne Kostendaten gefunden"
            )
        
        if validation['flows_with_costs'] == 0:
            validation['warnings'].append("Keine kostenrelevanten Flows gefunden")
            validation['cost_calculation_complete'] = False
        
        return validation
    
    def _create_cost_summary(self, cost_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """Erstellt eine Zusammenfassung der Kostenanalyse."""
        summary = {
            'total_system_costs_EUR': 0,
            'investment_costs_EUR': 0,
            'variable_costs_EUR': 0,
            'fixed_costs_EUR': 0,
            'cost_shares_percent': {},
            'dominant_cost_type': '',
            'number_of_investments': 0,
            'number_of_variable_cost_flows': 0
        }
        
        # Investment-Kosten
        investment_costs = cost_breakdown.get('investment_costs', [])
        summary['number_of_investments'] = len(investment_costs)
        summary['investment_costs_EUR'] = sum(inv['annual_investment_costs_EUR'] for inv in investment_costs)
        
        # Variable Kosten
        variable_costs = cost_breakdown.get('variable_costs', [])
        summary['number_of_variable_cost_flows'] = len(variable_costs)
        summary['variable_costs_EUR'] = sum(var['total_variable_costs_EUR'] for var in variable_costs)
        
        # Fixe Kosten
        fixed_costs = cost_breakdown.get('fixed_costs', [])
        summary['fixed_costs_EUR'] = sum(fix.get('total_fixed_costs_EUR', 0) for fix in fixed_costs)
        
        # Gesamtkosten
        summary['total_system_costs_EUR'] = (
            summary['investment_costs_EUR'] + 
            summary['variable_costs_EUR'] + 
            summary['fixed_costs_EUR']
        )
        
        # Kostenverteilung
        if summary['total_system_costs_EUR'] > 0:
            summary['cost_shares_percent'] = {
                'investment': (summary['investment_costs_EUR'] / summary['total_system_costs_EUR'] * 100),
                'variable': (summary['variable_costs_EUR'] / summary['total_system_costs_EUR'] * 100),
                'fixed': (summary['fixed_costs_EUR'] / summary['total_system_costs_EUR'] * 100)
            }
            
            # Dominante Kostenart
            max_cost_type = max(summary['cost_shares_percent'], key=summary['cost_shares_percent'].get)
            summary['dominant_cost_type'] = max_cost_type
        
        return summary
    
    def _determine_technology_type(self, component_label: str) -> str:
        """Bestimmt Technologie-Typ basierend auf Komponenten-Label."""
        label_lower = component_label.lower()
        
        if any(word in label_lower for word in ['pv', 'solar', 'photovoltaic']):
            return 'PV Solar'
        elif any(word in label_lower for word in ['wind', 'wtg']):
            return 'Wind Power'
        elif any(word in label_lower for word in ['grid', 'import']) and 'export' not in label_lower:
            return 'Grid Import'
        elif any(word in label_lower for word in ['grid', 'export']):
            return 'Grid Export'
        elif any(word in label_lower for word in ['gas']) and any(word in label_lower for word in ['plant', 'power']):
            return 'Gas Power Plant'
        elif any(word in label_lower for word in ['gas', 'boiler']):
            return 'Gas Boiler'
        elif any(word in label_lower for word in ['heat', 'pump']):
            return 'Heat Pump'
        elif any(word in label_lower for word in ['chp', 'kwk']):
            return 'CHP Plant'
        elif any(word in label_lower for word in ['battery', 'storage']) and 'thermal' not in label_lower:
            return 'Battery Storage'
        elif any(word in label_lower for word in ['thermal', 'storage']):
            return 'Thermal Storage'
        elif any(word in label_lower for word in ['load', 'demand']):
            return 'Electrical Load'
        elif 'bus' in label_lower:
            return 'Energy Bus'
        else:
            return 'Other Technology'
    
    def _save_system_export(self, system_export: Dict[str, Any]):
        """Speichert den kompletten System-Export."""
        try:
            # JSON-Export
            json_file = self.output_dir / "complete_energy_system_export.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(system_export, f, indent=2, default=str)
            
            self.logger.info(f"💾 System-Export gespeichert: {json_file.name}")
            
            # Excel-Export (vereinfacht)
            self._save_system_export_excel(system_export)
            
            # Text-Bericht
            self._save_system_export_report(system_export)
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des System-Exports: {e}")
    
    def _save_system_export_excel(self, system_export: Dict[str, Any]):
        """Speichert System-Export als Excel-Datei."""
        try:
            excel_file = self.output_dir / "energy_system_export.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                
                # 1. Metadaten
                metadata_df = pd.DataFrame([
                    {'Parameter': k, 'Value': v} 
                    for k, v in system_export['metadata'].items()
                ])
                metadata_df.to_excel(writer, sheet_name='metadata', index=False)
                
                # 2. Nodes-Übersicht
                nodes_data = []
                for node_label, node_info in system_export['nodes'].items():
                    nodes_data.append({
                        'label': node_label,
                        'type': node_info['type'],
                        'inputs_count': len(node_info['inputs']),
                        'outputs_count': len(node_info['outputs'])
                    })
                
                if nodes_data:
                    nodes_df = pd.DataFrame(nodes_data)
                    nodes_df.to_excel(writer, sheet_name='nodes_overview', index=False)
                
                # 3. Flows-Übersicht
                flows_data = []
                for flow in system_export['flows']:
                    flows_data.append({
                        'source': flow['source'],
                        'target': flow['target'],
                        'source_type': flow['source_type'],
                        'target_type': flow['target_type'],
                        'has_nominal_capacity': 'nominal_capacity' in flow['properties'],
                        'has_variable_costs': 'variable_costs' in flow['properties'],
                        'is_investment': flow['properties'].get('nominal_capacity', {}).get('type') == 'Investment'
                    })
                
                if flows_data:
                    flows_df = pd.DataFrame(flows_data)
                    flows_df.to_excel(writer, sheet_name='flows_overview', index=False)
                
                # 4. Investment-Definitionen
                if system_export['investments']:
                    investments_data = []
                    for inv in system_export['investments']:
                        inv_params = inv['investment_parameters']
                        investments_data.append({
                            'component': inv['component'],
                            'connection': inv['connection'],
                            'ep_costs': inv_params.get('ep_costs', 0),
                            'minimum': inv_params.get('minimum', 0),
                            'maximum': inv_params.get('maximum', 0),
                            'existing': inv_params.get('existing', 0)
                        })
                    
                    investments_df = pd.DataFrame(investments_data)
                    investments_df.to_excel(writer, sheet_name='investments', index=False)
                
                # 5. Kosten-Parameter
                cost_params = system_export.get('cost_parameters', {})
                for cost_type, cost_list in cost_params.items():
                    if cost_list:
                        cost_df = pd.DataFrame(cost_list)
                        sheet_name = f"costs_{cost_type}"[:31]  # Excel-Sheet-Name-Limit
                        cost_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            self.logger.debug(f"      📊 {excel_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Excel-Export des System-Exports fehlgeschlagen: {e}")
    
    def _save_system_export_report(self, system_export: Dict[str, Any]):
        """Speichert System-Export als Text-Bericht."""
        try:
            report_file = self.output_dir / "energy_system_documentation.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("VOLLSTÄNDIGE ENERGIESYSTEM-DOKUMENTATION\n")
                f.write("=" * 60 + "\n")
                f.write(f"Erstellt: {system_export['metadata']['creation_timestamp']}\n")
                f.write(f"oemof.solph Version: {system_export['metadata']['oemof_version']}\n\n")
                
                # System-Übersicht
                f.write("SYSTEM-ÜBERSICHT:\n")
                f.write("-" * 20 + "\n")
                stats = system_export['system_statistics']
                f.write(f"Gesamtanzahl Nodes: {stats['total_nodes']}\n")
                f.write(f"Gesamtanzahl Flows: {stats['total_flows']}\n")
                f.write(f"Investment-Flows: {stats['investment_flows']}\n")
                f.write(f"NonConvex-Flows: {stats['nonconvex_flows']}\n")
                f.write(f"Kostenrelevante Flows: {stats['cost_relevant_flows']}\n\n")
                
                # Node-Typen
                f.write("NODE-TYPEN:\n")
                f.write("-" * 12 + "\n")
                for node_type, count in stats['node_types'].items():
                    f.write(f"{node_type}: {count}\n")
                f.write("\n")
                
                # Zeitindex
                timeindex_info = system_export.get('timeindex', {})
                if timeindex_info:
                    f.write("ZEITINDEX:\n")
                    f.write("-" * 10 + "\n")
                    f.write(f"Start: {timeindex_info.get('start', 'N/A')}\n")
                    f.write(f"Ende: {timeindex_info.get('end', 'N/A')}\n")
                    f.write(f"Perioden: {timeindex_info.get('periods', 'N/A')}\n")
                    f.write(f"Frequenz: {timeindex_info.get('frequency', 'N/A')}\n\n")
                
                # Investment-Übersicht
                investments = system_export.get('investments', [])
                if investments:
                    f.write("INVESTMENT-DEFINITIONEN:\n")
                    f.write("-" * 24 + "\n")
                    for inv in investments:
                        f.write(f"Komponente: {inv['component']}\n")
                        f.write(f"  Verbindung: {inv['connection']}\n")
                        params = inv['investment_parameters']
                        f.write(f"  EP-Costs: {params.get('ep_costs', 'N/A')} €/kW/a\n")
                        f.write(f"  Minimum: {params.get('minimum', 'N/A')} kW\n")
                        f.write(f"  Maximum: {params.get('maximum', 'N/A')} kW\n")
                        f.write(f"  Existing: {params.get('existing', 'N/A')} kW\n")
                        f.write("\n")
                
                # Kosten-Parameter-Übersicht
                cost_params = system_export.get('cost_parameters', {})
                for cost_type, cost_list in cost_params.items():
                    if cost_list:
                        f.write(f"{cost_type.upper()}:\n")
                        f.write("-" * (len(cost_type) + 1) + "\n")
                        for cost_item in cost_list:
                            f.write(f"  {cost_item['component']}: {cost_item['connection']}\n")
                            for key, value in cost_item.items():
                                if key not in ['component', 'connection']:
                                    f.write(f"    {key}: {value}\n")
                        f.write("\n")
            
            self.logger.debug(f"      📋 {report_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Text-Bericht des System-Exports fehlgeschlagen: {e}")
    
    def _save_cost_breakdown(self, cost_breakdown: Dict[str, Any]):
        """Speichert die detaillierte Kostenaufschlüsselung."""
        try:
            # JSON-Export
            json_file = self.output_dir / "detailed_cost_breakdown.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(cost_breakdown, f, indent=2, default=str)
            
            # Excel-Export
            self._save_cost_breakdown_excel(cost_breakdown)
            
            # Text-Bericht
            self._save_cost_breakdown_report(cost_breakdown)
            
            self.logger.info(f"💾 Kostenaufschlüsselung gespeichert: {json_file.name}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Kostenaufschlüsselung: {e}")
    
    def _save_cost_breakdown_excel(self, cost_breakdown: Dict[str, Any]):
        """Speichert Kostenaufschlüsselung als Excel-Datei."""
        try:
            excel_file = self.output_dir / "detailed_cost_breakdown.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                
                # 1. Zusammenfassung
                summary = cost_breakdown['summary']
                summary_data = [
                    {'Kostenart': 'Investment-Kosten', 'Betrag_EUR': summary['investment_costs_EUR'], 
                     'Anteil_Prozent': summary['cost_shares_percent'].get('investment', 0)},
                    {'Kostenart': 'Variable Kosten', 'Betrag_EUR': summary['variable_costs_EUR'], 
                     'Anteil_Prozent': summary['cost_shares_percent'].get('variable', 0)},
                    {'Kostenart': 'Fixe Kosten', 'Betrag_EUR': summary['fixed_costs_EUR'], 
                     'Anteil_Prozent': summary['cost_shares_percent'].get('fixed', 0)},
                    {'Kostenart': 'GESAMT', 'Betrag_EUR': summary['total_system_costs_EUR'], 
                     'Anteil_Prozent': 100.0}
                ]
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='cost_summary', index=False)
                
                # 2. Investment-Kosten Detail
                if cost_breakdown['investment_costs']:
                    inv_df = pd.DataFrame(cost_breakdown['investment_costs'])
                    inv_df.to_excel(writer, sheet_name='investment_costs', index=False)
                
                # 3. Variable Kosten Detail
                if cost_breakdown['variable_costs']:
                    var_df = pd.DataFrame(cost_breakdown['variable_costs'])
                    var_df.to_excel(writer, sheet_name='variable_costs', index=False)
                
                # 4. Kosten nach Technologie
                tech_costs = cost_breakdown['cost_by_technology']
                if tech_costs:
                    tech_data = []
                    for tech, costs in tech_costs.items():
                        tech_data.append({
                            'technology': tech,
                            'investment_EUR': costs['investment'],
                            'variable_EUR': costs['variable'],
                            'total_EUR': costs['total']
                        })
                    
                    tech_df = pd.DataFrame(tech_data)
                    tech_df = tech_df.sort_values('total_EUR', ascending=False)
                    tech_df.to_excel(writer, sheet_name='costs_by_technology', index=False)
                
                # 5. Kosten nach Komponente
                comp_costs = cost_breakdown['cost_by_component']
                if comp_costs:
                    comp_data = []
                    for comp, costs in comp_costs.items():
                        comp_data.append({
                            'component': comp,
                            'investment_EUR': costs['investment'],
                            'variable_EUR': costs['variable'],
                            'total_EUR': costs['total']
                        })
                    
                    comp_df = pd.DataFrame(comp_data)
                    comp_df = comp_df.sort_values('total_EUR', ascending=False)
                    comp_df.to_excel(writer, sheet_name='costs_by_component', index=False)
                
                # 6. Validierung
                validation = cost_breakdown['cost_validation']
                val_data = [
                    {'Parameter': k, 'Value': v} 
                    for k, v in validation.items() 
                    if not isinstance(v, list)
                ]
                
                if validation.get('missing_cost_data'):
                    val_data.append({
                        'Parameter': 'missing_cost_data_count', 
                        'Value': len(validation['missing_cost_data'])
                    })
                
                if validation.get('warnings'):
                    val_data.append({
                        'Parameter': 'warnings_count', 
                        'Value': len(validation['warnings'])
                    })
                
                val_df = pd.DataFrame(val_data)
                val_df.to_excel(writer, sheet_name='validation', index=False)
            
            self.logger.debug(f"      📊 {excel_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Excel-Export der Kostenaufschlüsselung fehlgeschlagen: {e}")
    
    def _save_cost_breakdown_report(self, cost_breakdown: Dict[str, Any]):
        """Speichert Kostenaufschlüsselung als Text-Bericht."""
        try:
            report_file = self.output_dir / "cost_breakdown_report.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("DETAILLIERTE KOSTENAUFSCHLÜSSELUNG\n")
                f.write("=" * 50 + "\n\n")
                
                # Zusammenfassung
                summary = cost_breakdown['summary']
                f.write("KOSTENÜBERSICHT:\n")
                f.write("-" * 16 + "\n")
                f.write(f"Gesamtkosten: {summary['total_system_costs_EUR']:,.2f} €\n")
                f.write(f"Investment-Kosten: {summary['investment_costs_EUR']:,.2f} € ")
                f.write(f"({summary['cost_shares_percent'].get('investment', 0):.1f}%)\n")
                f.write(f"Variable Kosten: {summary['variable_costs_EUR']:,.2f} € ")
                f.write(f"({summary['cost_shares_percent'].get('variable', 0):.1f}%)\n")
                f.write(f"Fixe Kosten: {summary['fixed_costs_EUR']:,.2f} € ")
                f.write(f"({summary['cost_shares_percent'].get('fixed', 0):.1f}%)\n")
                f.write(f"Dominante Kostenart: {summary['dominant_cost_type']}\n\n")
                
                # Investment-Kosten Detail
                investment_costs = cost_breakdown['investment_costs']
                if investment_costs:
                    f.write("INVESTMENT-KOSTEN DETAIL:\n")
                    f.write("-" * 27 + "\n")
                    for inv in investment_costs:
                        f.write(f"{inv['component']} ({inv['connection']}):\n")
                        f.write(f"  Investierte Kapazität: {inv['invested_capacity_kW']:.1f} kW\n")
                        f.write(f"  EP-Costs: {inv['ep_costs_EUR_per_kW_per_year']:.2f} €/kW/a\n")
                        f.write(f"  Jährliche Kosten: {inv['annual_investment_costs_EUR']:,.2f} €\n")
                        f.write(f"  Gesamtkapazität: {inv['total_capacity_kW']:.1f} kW\n")
                        f.write("\n")
                
                # Variable Kosten Detail
                variable_costs = cost_breakdown['variable_costs']
                if variable_costs:
                    f.write("VARIABLE KOSTEN DETAIL:\n")
                    f.write("-" * 24 + "\n")
                    for var in variable_costs:
                        f.write(f"{var['component']} ({var['connection']}):\n")
                        f.write(f"  Energie: {var['total_energy_kWh']:,.1f} kWh\n")
                        f.write(f"  Kosten/kWh: {var['variable_costs_EUR_per_kWh']:.4f} €/kWh\n")
                        f.write(f"  Gesamtkosten: {var['total_variable_costs_EUR']:,.2f} €\n")
                        f.write(f"  Volllaststunden: {var['operating_hours']:.0f} h\n")
                        f.write(f"  Auslastung: {var['capacity_factor']:.1%}\n")
                        f.write("\n")
                
                # Kosten nach Technologie
                tech_costs = cost_breakdown['cost_by_technology']
                if tech_costs:
                    f.write("KOSTEN NACH TECHNOLOGIE:\n")
                    f.write("-" * 25 + "\n")
                    sorted_tech = sorted(tech_costs.items(), key=lambda x: x[1]['total'], reverse=True)
                    for tech, costs in sorted_tech:
                        f.write(f"{tech}:\n")
                        f.write(f"  Investment: {costs['investment']:,.2f} €\n")
                        f.write(f"  Variable: {costs['variable']:,.2f} €\n")
                        f.write(f"  Gesamt: {costs['total']:,.2f} €\n")
                        f.write("\n")
                
                # Validierung
                validation = cost_breakdown['cost_validation']
                f.write("VALIDIERUNG:\n")
                f.write("-" * 12 + "\n")
                f.write(f"Geprüfte Flows: {validation['total_flows_checked']}\n")
                f.write(f"Flows mit Kosten: {validation['flows_with_costs']}\n")
                f.write(f"Investment-Flows: {validation['flows_with_investment']}\n")
                f.write(f"Berechnung vollständig: {validation['cost_calculation_complete']}\n")
                
                if validation['warnings']:
                    f.write("\nWarnungen:\n")
                    for warning in validation['warnings']:
                        f.write(f"  ⚠️  {warning}\n")
                
                if validation['missing_cost_data']:
                    f.write(f"\nFlows ohne Kostendaten ({len(validation['missing_cost_data'])}):\n")
                    for missing in validation['missing_cost_data'][:10]:  # Nur erste 10
                        f.write(f"  • {missing}\n")
                    if len(validation['missing_cost_data']) > 10:
                        f.write(f"  ... und {len(validation['missing_cost_data']) - 10} weitere\n")
            
            self.logger.debug(f"      📋 {report_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Text-Bericht der Kostenaufschlüsselung fehlgeschlagen: {e}")


# Integration in das bestehende ResultsProcessor-Modul
class EnhancedResultsProcessor:
    """Erweiterte Results-Processor-Klasse mit System-Export und Kostenanalyse."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """Initialisiert den Enhanced Results-Processor."""
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Energy System Analyzer
        self.system_analyzer = EnergySystemAnalyzer(output_dir, settings)
        
        # Output-Format
        self.output_format = settings.get('output_format', 'xlsx')
        self.output_files = []
    
    def process_results_with_system_export(self, results: Dict[str, Any], 
                                         energy_system: Any, 
                                         excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet Ergebnisse mit vollständigem System-Export und Kostenanalyse.
        
        Args:
            results: oemof.solph Optimierungsergebnisse
            energy_system: Das optimierte EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Dictionary mit erweiterten Ergebnissen
        """
        self.logger.info("📈 Verarbeite Optimierungsergebnisse mit System-Export...")
        
        processed_results = {}
        
        # 1. Vollständiger Energiesystem-Export
        self.logger.info("🔍 Exportiere komplettes Energiesystem...")
        system_export = self.system_analyzer.export_complete_energy_system(energy_system, excel_data)
        processed_results['system_export'] = system_export
        
        # 2. Detaillierte Kostenanalyse
        self.logger.info("💰 Berechne detaillierte Kostenaufschlüsselung...")
        cost_breakdown = self.system_analyzer.calculate_comprehensive_costs(results, energy_system, excel_data)
        processed_results['cost_breakdown'] = cost_breakdown
        
        # 3. Standard Flow-Extraktion
        flows_df = self._extract_flows(results)
        processed_results['flows'] = flows_df
        self._save_dataframe(flows_df, 'flows')
        
        # 4. Bus-Bilanzen
        bus_balances = self._calculate_bus_balances(results, energy_system)
        processed_results['bus_balances'] = bus_balances
        self._save_dataframe(bus_balances, 'bus_balances')
        
        # 5. Investment-Ergebnisse (Legacy-Kompatibilität)
        investments = self._extract_investments(results)
        if not investments.empty:
            processed_results['investments'] = investments
            self._save_dataframe(investments, 'investments_legacy')
        
        # 6. Erweiterte Zusammenfassung
        summary = self._create_comprehensive_summary(processed_results, energy_system)
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
        """Extrahiert Investment-Ergebnisse (Legacy-Kompatibilität)."""
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
    
    def _create_comprehensive_summary(self, processed_results: Dict[str, Any], 
                                    energy_system: Any) -> Dict[str, Any]:
        """Erstellt eine umfassende Ergebnis-Zusammenfassung."""
        summary = {
            'simulation_info': {},
            'system_overview': {},
            'cost_summary': {},
            'investment_summary': {},
            'energy_flows': {},
            'performance_metrics': {}
        }
        
        # Simulation-Info
        if hasattr(energy_system, 'timeindex'):
            timeindex = energy_system.timeindex
            summary['simulation_info'] = {
                'start_date': timeindex[0].strftime('%Y-%m-%d %H:%M'),
                'end_date': timeindex[-1].strftime('%Y-%m-%d %H:%M'),
                'duration_hours': len(timeindex),
                'resolution': pd.infer_freq(timeindex) or 'variable',
                'total_periods': len(timeindex)
            }
        
        # System-Übersicht
        system_export = processed_results.get('system_export', {})
        system_stats = system_export.get('system_statistics', {})
        
        summary['system_overview'] = {
            'total_nodes': system_stats.get('total_nodes', 0),
            'total_flows': system_stats.get('total_flows', 0),
            'investment_flows': system_stats.get('investment_flows', 0),
            'cost_relevant_flows': system_stats.get('cost_relevant_flows', 0),
            'node_types': system_stats.get('node_types', {})
        }
        
        # Kosten-Zusammenfassung
        cost_breakdown = processed_results.get('cost_breakdown', {})
        cost_summary = cost_breakdown.get('summary', {})
        
        summary['cost_summary'] = {
            'total_system_costs_EUR': cost_summary.get('total_system_costs_EUR', 0),
            'investment_costs_EUR': cost_summary.get('investment_costs_EUR', 0),
            'variable_costs_EUR': cost_summary.get('variable_costs_EUR', 0),
            'fixed_costs_EUR': cost_summary.get('fixed_costs_EUR', 0),
            'dominant_cost_type': cost_summary.get('dominant_cost_type', 'unknown'),
            'cost_shares_percent': cost_summary.get('cost_shares_percent', {})
        }
        
        # Investment-Zusammenfassung
        investment_costs = cost_breakdown.get('investment_costs', [])
        if investment_costs:
            total_invested_capacity = sum(inv['invested_capacity_kW'] for inv in investment_costs)
            avg_ep_costs = np.mean([inv['ep_costs_EUR_per_kW_per_year'] for inv in investment_costs])
            
            summary['investment_summary'] = {
                'number_of_investments': len(investment_costs),
                'total_invested_capacity_kW': total_invested_capacity,
                'total_annual_investment_costs_EUR': cost_summary.get('investment_costs_EUR', 0),
                'average_ep_costs_EUR_per_kW': avg_ep_costs,
                'investment_components': [inv['component'] for inv in investment_costs]
            }
        else:
            summary['investment_summary'] = {
                'number_of_investments': 0,
                'total_invested_capacity_kW': 0,
                'total_annual_investment_costs_EUR': 0,
                'average_ep_costs_EUR_per_kW': 0,
                'investment_components': []
            }
        
        # Energie-Flüsse
        flows_df = processed_results.get('flows', pd.DataFrame())
        if not flows_df.empty:
            total_energy = flows_df.sum().sum()
            peak_power = flows_df.max().max()
            
            summary['energy_flows'] = {
                'total_energy_MWh': total_energy / 1000,
                'peak_power_MW': peak_power / 1000,
                'average_power_MW': (total_energy / len(flows_df)) / 1000 if len(flows_df) > 0 else 0,
                'number_of_flows': len(flows_df.columns)
            }
        else:
            summary['energy_flows'] = {
                'total_energy_MWh': 0,
                'peak_power_MW': 0,
                'average_power_MW': 0,
                'number_of_flows': 0
            }
        
        # Performance-Metriken
        validation = cost_breakdown.get('cost_validation', {})
        
        summary['performance_metrics'] = {
            'cost_calculation_complete': validation.get('cost_calculation_complete', False),
            'flows_with_costs_percent': (
                (validation.get('flows_with_costs', 0) / validation.get('total_flows_checked', 1)) * 100
                if validation.get('total_flows_checked', 0) > 0 else 0
            ),
            'system_complexity_score': self._calculate_complexity_score(system_stats),
            'data_quality_score': self._calculate_data_quality_score(validation)
        }
        
        return summary
    
    def _calculate_complexity_score(self, system_stats: Dict[str, Any]) -> float:
        """Berechnet einen Komplexitäts-Score für das System."""
        score = 0
        
        # Basis-Komplexität: Anzahl Nodes und Flows
        score += system_stats.get('total_nodes', 0) * 1.0
        score += system_stats.get('total_flows', 0) * 0.5
        
        # Investment erhöht Komplexität
        score += system_stats.get('investment_flows', 0) * 2.0
        
        # NonConvex erhöht Komplexität stark
        score += system_stats.get('nonconvex_flows', 0) * 3.0
        
        # Verschiedene Node-Typen erhöhen Komplexität
        node_types = system_stats.get('node_types', {})
        score += len(node_types) * 1.5
        
        return round(score, 1)
    
    def _calculate_data_quality_score(self, validation: Dict[str, Any]) -> float:
        """Berechnet einen Datenqualitäts-Score."""
        if validation.get('total_flows_checked', 0) == 0:
            return 0.0
        
        # Basis-Score: Anteil der Flows mit Kostendaten
        cost_coverage = validation.get('flows_with_costs', 0) / validation.get('total_flows_checked', 1)
        score = cost_coverage * 100
        
        # Abzug für Warnungen
        warnings_count = len(validation.get('warnings', []))
        score -= warnings_count * 10
        
        # Abzug für fehlende Kostendaten
        missing_data_count = len(validation.get('missing_cost_data', []))
        score -= missing_data_count * 5
        
        # Bonus für vollständige Berechnung
        if validation.get('cost_calculation_complete', False):
            score += 10
        
        return max(0.0, min(100.0, round(score, 1)))
    
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
        """Speichert die erweiterte Zusammenfassung."""
        # JSON-Format für maschinenlesbare Zusammenfassung
        import json
        
        json_file = self.output_dir / "comprehensive_summary.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.output_files.append(json_file)
        
        # Erweiterte Textformat-Zusammenfassung
        txt_file = self.output_dir / "comprehensive_summary.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("UMFASSENDE OPTIMIERUNGSERGEBNISSE - ZUSAMMENFASSUNG\n")
            f.write("=" * 70 + "\n\n")
            
            # Simulation-Info
            sim_info = summary.get('simulation_info', {})
            if sim_info:
                f.write("SIMULATION:\n")
                f.write("-" * 12 + "\n")
                f.write(f"Zeitraum: {sim_info.get('start_date', 'N/A')} bis {sim_info.get('end_date', 'N/A')}\n")
                f.write(f"Dauer: {sim_info.get('duration_hours', 0):,} Stunden\n")
                f.write(f"Auflösung: {sim_info.get('resolution', 'N/A')}\n")
                f.write(f"Zeitschritte: {sim_info.get('total_periods', 0):,}\n\n")
            
            # System-Übersicht
            sys_overview = summary.get('system_overview', {})
            f.write("SYSTEM-ÜBERSICHT:\n")
            f.write("-" * 17 + "\n")
            f.write(f"Gesamtanzahl Komponenten: {sys_overview.get('total_nodes', 0)}\n")
            f.write(f"Gesamtanzahl Flows: {sys_overview.get('total_flows', 0)}\n")
            f.write(f"Investment-Flows: {sys_overview.get('investment_flows', 0)}\n")
            f.write(f"Kostenrelevante Flows: {sys_overview.get('cost_relevant_flows', 0)}\n")
            
            node_types = sys_overview.get('node_types', {})
            if node_types:
                f.write("Komponententypen:\n")
                for node_type, count in node_types.items():
                    f.write(f"  {node_type}: {count}\n")
            f.write("\n")
            
            # Kosten-Zusammenfassung
            cost_summary = summary.get('cost_summary', {})
            f.write("KOSTEN-ZUSAMMENFASSUNG:\n")
            f.write("-" * 21 + "\n")
            f.write(f"Gesamtkosten: {cost_summary.get('total_system_costs_EUR', 0):,.2f} €\n")
            f.write(f"Investment-Kosten: {cost_summary.get('investment_costs_EUR', 0):,.2f} € ")
            
            cost_shares = cost_summary.get('cost_shares_percent', {})
            if 'investment' in cost_shares:
                f.write(f"({cost_shares['investment']:.1f}%)\n")
            else:
                f.write("\n")
            
            f.write(f"Variable Kosten: {cost_summary.get('variable_costs_EUR', 0):,.2f} € ")
            if 'variable' in cost_shares:
                f.write(f"({cost_shares['variable']:.1f}%)\n")
            else:
                f.write("\n")
            
            f.write(f"Fixe Kosten: {cost_summary.get('fixed_costs_EUR', 0):,.2f} € ")
            if 'fixed' in cost_shares:
                f.write(f"({cost_shares['fixed']:.1f}%)\n")
            else:
                f.write("\n")
            
            f.write(f"Dominante Kostenart: {cost_summary.get('dominant_cost_type', 'unbekannt')}\n\n")
            
            # Investment-Zusammenfassung
            inv_summary = summary.get('investment_summary', {})
            f.write("INVESTMENT-ZUSAMMENFASSUNG:\n")
            f.write("-" * 26 + "\n")
            f.write(f"Anzahl Investitionen: {inv_summary.get('number_of_investments', 0)}\n")
            f.write(f"Gesamte investierte Kapazität: {inv_summary.get('total_invested_capacity_kW', 0):,.1f} kW\n")
            f.write(f"Jährliche Investment-Kosten: {inv_summary.get('total_annual_investment_costs_EUR', 0):,.2f} €\n")
            f.write(f"Durchschnittliche EP-Costs: {inv_summary.get('average_ep_costs_EUR_per_kW', 0):.2f} €/kW/a\n")
            
            inv_components = inv_summary.get('investment_components', [])
            if inv_components:
                f.write("Investment-Komponenten:\n")
                for comp in inv_components:
                    f.write(f"  • {comp}\n")
            f.write("\n")
            
            # Energie-Flüsse
            energy_flows = summary.get('energy_flows', {})
            f.write("ENERGIE-FLÜSSE:\n")
            f.write("-" * 15 + "\n")
            f.write(f"Gesamtenergie: {energy_flows.get('total_energy_MWh', 0):,.1f} MWh\n")
            f.write(f"Spitzenleistung: {energy_flows.get('peak_power_MW', 0):,.1f} MW\n")
            f.write(f"Durchschnittsleistung: {energy_flows.get('average_power_MW', 0):,.1f} MW\n")
            f.write(f"Anzahl Flow-Verbindungen: {energy_flows.get('number_of_flows', 0)}\n\n")
            
            # Performance-Metriken
            performance = summary.get('performance_metrics', {})
            f.write("PERFORMANCE-METRIKEN:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Kostenberechnung vollständig: {'Ja' if performance.get('cost_calculation_complete', False) else 'Nein'}\n")
            f.write(f"Flows mit Kostendaten: {performance.get('flows_with_costs_percent', 0):.1f}%\n")
            f.write(f"System-Komplexität: {performance.get('system_complexity_score', 0):.1f}\n")
            f.write(f"Datenqualität: {performance.get('data_quality_score', 0):.1f}/100\n")
        
        self.output_files.append(txt_file)
        self.logger.debug(f"      💾 {json_file.name}, {txt_file.name}")


def test_enhanced_cost_analysis():
    """Testfunktion für die erweiterte Kostenanalyse."""
    import tempfile
    
    # Dummy-Ergebnisse erstellen
    timestamps = pd.date_range('2025-01-01', periods=24, freq='h')
    
    dummy_results = {
        ('pv_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 30, index=timestamps)
            },
            'scalars': {
                'invest': 100,
                'variable_costs': 0.0
            }
        },
        ('grid_import', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 20, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.25
            }
        }
    }
    
    # Dummy Energy System
    class DummyFlow:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class DummyInvestment:
        def __init__(self, ep_costs, minimum=0, maximum=1000, existing=0):
            self.ep_costs = ep_costs
            self.minimum = minimum
            self.maximum = maximum
            self.existing = existing
    
    class DummyNode:
        def __init__(self, label, node_type='Bus'):
            self.label = label
            self.node_type = node_type
            self.inputs = {}
            self.outputs = {}
    
    class DummyEnergySystem:
        def __init__(self):
            self.timeindex = timestamps
            
            # Nodes erstellen
            self.el_bus = DummyNode('el_bus', 'Bus')
            self.pv_plant = DummyNode('pv_plant', 'Source')
            self.grid_import = DummyNode('grid_import', 'Source')
            
            # Flows mit Investment und Kosten
            pv_flow = DummyFlow(
                nominal_capacity=DummyInvestment(ep_costs=71.05, maximum=500),
                variable_costs=0.0
            )
            
            grid_flow = DummyFlow(
                nominal_capacity=1000,
                variable_costs=0.25
            )
            
            # Verbindungen
            self.pv_plant.outputs[self.el_bus] = pv_flow
            self.grid_import.outputs[self.el_bus] = grid_flow
            
            self.el_bus.inputs[self.pv_plant] = pv_flow
            self.el_bus.inputs[self.grid_import] = grid_flow
            
            self.nodes = [self.el_bus, self.pv_plant, self.grid_import]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        processor = EnhancedResultsProcessor(Path(temp_dir), settings)
        
        # Dummy Energy System
        energy_system = DummyEnergySystem()
        excel_data = {}
        
        try:
            results = processor.process_results_with_system_export(
                dummy_results, energy_system, excel_data
            )
            
            print("✅ Enhanced Cost Analysis Test erfolgreich!")
            print(f"Erstellte Dateien: {len(processor.output_files)}")
            
            # System-Export prüfen
            if 'system_export' in results:
                system_export = results['system_export']
                print(f"System-Export: {len(system_export)} Kategorien")
                print(f"  Nodes: {len(system_export.get('nodes', {}))}")
                print(f"  Flows: {len(system_export.get('flows', []))}")
                print(f"  Investments: {len(system_export.get('investments', []))}")
            
            # Kosten-Aufschlüsselung prüfen
            if 'cost_breakdown' in results:
                cost_breakdown = results['cost_breakdown']
                print(f"Kosten-Aufschlüsselung:")
                summary = cost_breakdown.get('summary', {})
                print(f"  Gesamtkosten: {summary.get('total_system_costs_EUR', 0):.2f} €")
                print(f"  Investment-Kosten: {summary.get('investment_costs_EUR', 0):.2f} €")
                print(f"  Variable Kosten: {summary.get('variable_costs_EUR', 0):.2f} €")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_cost_analysis()