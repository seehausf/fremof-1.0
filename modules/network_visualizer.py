#!/usr/bin/env python3
"""
oemof.solph 0.6.0 NetworkX Energy System Visualizer
===================================================

Erstellt Netzwerk-Diagramme von oemof.solph EnergySystem-Objekten
mit NetworkX und Matplotlib. Zeigt die exakte Interpretation der
Excel-Eingaben durch oemof.solph.

Vorteile gegenüber oemof-visio:
- Keine externen Abhängigkeiten (Graphviz)
- Funktioniert zuverlässig unter Windows
- Zeigt Investment-Parameter und Flow-Details
- Anpassbare Layouts und Farben

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import logging
import textwrap

# Basis-Imports (sollten immer verfügbar sein)
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    import matplotlib.lines as mlines
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None
    plt = None
    mpatches = None

# oemof.solph Imports für Typ-Erkennung
try:
    import oemof.solph as solph
    from oemof.solph import buses, components
    from oemof.solph._options import Investment, NonConvex
    OEMOF_AVAILABLE = True
except ImportError:
    OEMOF_AVAILABLE = False
    solph = None


class EnergySystemNetworkVisualizer:
    """Erstellt detaillierte Netzwerk-Visualisierungen von oemof.solph EnergySystem-Objekten."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Visualizer.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Verfügbarkeit prüfen
        self.available = NETWORKX_AVAILABLE and OEMOF_AVAILABLE
        
        if not self.available:
            self._log_availability_status()
        
        # Farb- und Style-Schema
        self.setup_visual_schema()
    
    def _log_availability_status(self):
        """Loggt den Status der Verfügbarkeit."""
        missing = []
        if not NETWORKX_AVAILABLE:
            missing.append("networkx, matplotlib")
        if not OEMOF_AVAILABLE:
            missing.append("oemof.solph")
        
        self.logger.warning(f"⚠️  Netzwerk-Visualisierung nicht verfügbar: {', '.join(missing)} fehlt")
    
    def setup_visual_schema(self):
        """Definiert Farben und Styles für verschiedene Komponententypen."""
        
        # Komponenten-Farben (basierend auf oemof-Konventionen)
        self.component_colors = {
            # Buses
            'bus': '#E8F4FD',           # Hellblau
            'bus_electrical': '#B3D9FF', # Elektrisch
            'bus_thermal': '#FFB3B3',   # Thermisch  
            'bus_gas': '#B3FFB3',       # Gas
            'bus_h2': '#FFB3FF',        # Wasserstoff
            
            # Sources (Erzeuger)
            'source': '#90EE90',        # Hellgrün
            'source_renewable': '#228B22', # Dunkelgrün (PV, Wind)
            'source_fossil': '#8B4513',  # Braun (Gas, Kohle)
            'source_grid': '#FFA500',    # Orange (Grid Import)
            
            # Sinks (Verbraucher)
            'sink': '#FFB6C1',          # Rosa
            'sink_load': '#DC143C',     # Rot (Last)
            'sink_export': '#FF8C00',   # Orange (Export)
            
            # Converters (Wandler)
            'converter': '#DDA0DD',     # Plum
            'converter_chp': '#9932CC', # Violett (KWK)
            'converter_hp': '#4169E1',  # Königsblau (WP)
            'converter_boiler': '#B22222', # Dunkelrot (Kessel)
            
            # Storages
            'storage': '#F0E68C',       # Khaki
            'storage_battery': '#FFD700', # Gold
            'storage_thermal': '#DEB887', # Beige
            
            # Investment
            'investment': '#FF6347',    # Tomato (Investment-Rahmen)
        }
        
        # Node-Größen
        self.node_sizes = {
            'bus': 2000,
            'source': 1500,
            'sink': 1500,
            'converter': 1800,
            'storage': 1600
        }
        
        # Edge-Styles
        self.edge_styles = {
            'normal': {'width': 2, 'style': 'solid', 'alpha': 0.7},
            'investment': {'width': 3, 'style': 'dashed', 'alpha': 0.9},
            'nonconvex': {'width': 2, 'style': 'dotted', 'alpha': 0.8}
        }
    
    def analyze_energy_system(self, energy_system) -> Dict[str, Any]:
        """
        Analysiert das EnergySystem und extrahiert alle relevanten Informationen.
        
        Args:
            energy_system: oemof.solph EnergySystem
            
        Returns:
            Dictionary mit System-Analyse
        """
        analysis = {
            'nodes': {},
            'edges': [],
            'investments': [],
            'nonconvex': [],
            'timeindex_info': {},
            'statistics': {}
        }
        
        if not hasattr(energy_system, 'nodes'):
            self.logger.warning("⚠️  EnergySystem hat keine 'nodes' Eigenschaft")
            return analysis
        
        # Zeitindex analysieren
        if hasattr(energy_system, 'timeindex'):
            timeindex = energy_system.timeindex
            analysis['timeindex_info'] = {
                'start': timeindex[0],
                'end': timeindex[-1],
                'periods': len(timeindex),
                'freq': pd.infer_freq(timeindex),
                'total_hours': len(timeindex)
            }
        
        # Nodes analysieren
        for node in energy_system.nodes:
            node_info = self._analyze_node(node)
            analysis['nodes'][str(node.label)] = node_info
            
            # Edges aus inputs/outputs extrahieren
            edges = self._extract_edges_from_node(node)
            analysis['edges'].extend(edges)
        
        # Investment und NonConvex sammeln
        analysis['investments'] = self._collect_investments(energy_system)
        analysis['nonconvex'] = self._collect_nonconvex(energy_system)
        
        # Statistiken berechnen
        analysis['statistics'] = self._calculate_system_statistics(analysis)
        
        return analysis
    
    def _analyze_node(self, node) -> Dict[str, Any]:
        """Analysiert einen einzelnen Node."""
        node_info = {
            'label': str(node.label),
            'type': type(node).__name__,
            'category': self._categorize_node(node),
            'color': self._get_node_color(node),
            'size': self._get_node_size(node),
            'properties': {},
            'flows': {'inputs': [], 'outputs': []}
        }
        
        # Bus-spezifische Eigenschaften
        if isinstance(node, solph.buses.Bus):
            node_info['properties']['bus_type'] = self._detect_bus_type(node)
        
        # Source-spezifische Eigenschaften  
        elif isinstance(node, solph.components.Source):
            node_info['properties'].update(self._analyze_source_properties(node))
        
        # Sink-spezifische Eigenschaften
        elif isinstance(node, solph.components.Sink):
            node_info['properties'].update(self._analyze_sink_properties(node))
        
        # Converter-spezifische Eigenschaften
        elif isinstance(node, solph.components.Converter):
            node_info['properties'].update(self._analyze_converter_properties(node))
        
        # Flow-Eigenschaften analysieren
        if hasattr(node, 'inputs'):
            for input_node, flow in node.inputs.items():
                flow_info = self._analyze_flow(flow, str(input_node.label), str(node.label))
                node_info['flows']['inputs'].append(flow_info)
        
        if hasattr(node, 'outputs'):
            for output_node, flow in node.outputs.items():
                flow_info = self._analyze_flow(flow, str(node.label), str(output_node.label))
                node_info['flows']['outputs'].append(flow_info)
        
        return node_info
    
    def _analyze_source_properties(self, source) -> Dict[str, Any]:
        """Analysiert Source-spezifische Eigenschaften."""
        properties = {}
        
        # Renewable detection basierend auf Label
        label = str(source.label).lower()
        if any(word in label for word in ['pv', 'solar', 'wind', 'hydro']):
            properties['renewable'] = True
        elif any(word in label for word in ['grid', 'import']):
            properties['grid_connection'] = True
        elif any(word in label for word in ['gas', 'coal', 'fossil']):
            properties['fossil'] = True
        
        return properties
    
    def _analyze_sink_properties(self, sink) -> Dict[str, Any]:
        """Analysiert Sink-spezifische Eigenschaften."""
        properties = {}
        
        # Load vs Export detection
        label = str(sink.label).lower()
        if any(word in label for word in ['load', 'demand', 'last']):
            properties['load_type'] = 'demand'
        elif any(word in label for word in ['export', 'grid']):
            properties['load_type'] = 'export'
        
        return properties
    
    def _analyze_converter_properties(self, converter) -> Dict[str, Any]:
        """Analysiert Converter-spezifische Eigenschaften."""
        properties = {}
        
        # Converter type detection
        label = str(converter.label).lower()
        if any(word in label for word in ['chp', 'kwk']):
            properties['converter_type'] = 'chp'
        elif any(word in label for word in ['heat_pump', 'hp', 'wärmepumpe']):
            properties['converter_type'] = 'heat_pump'
        elif any(word in label for word in ['boiler', 'kessel']):
            properties['converter_type'] = 'boiler'
        elif any(word in label for word in ['gas', 'power']):
            properties['converter_type'] = 'power_plant'
        
        # Conversion factors (falls verfügbar)
        if hasattr(converter, 'conversion_factors'):
            try:
                factors = {}
                for output_bus, factor in converter.conversion_factors.items():
                    factors[str(output_bus.label)] = factor
                properties['conversion_factors'] = factors
            except:
                pass
        
        return properties
    
    def _categorize_node(self, node) -> str:
        """Kategorisiert einen Node für Visualisierungszwecke."""
        try:
            if isinstance(node, solph.buses.Bus):
                return 'bus'
            elif isinstance(node, solph.components.Source):
                return 'source'
            elif isinstance(node, solph.components.Sink):
                return 'sink'
            elif isinstance(node, solph.components.Converter):
                return 'converter'
            elif hasattr(solph.components, 'GenericStorage') and isinstance(node, solph.components.GenericStorage):
                return 'storage'
            else:
                return 'unknown'
        except:
            # Fallback für Nodes ohne solph-Typen (z.B. in Tests)
            node_type = type(node).__name__.lower()
            if 'bus' in node_type:
                return 'bus'
            elif 'source' in node_type:
                return 'source'  
            elif 'sink' in node_type:
                return 'sink'
            elif 'converter' in node_type or 'transformer' in node_type:
                return 'converter'
            elif 'storage' in node_type:
                return 'storage'
            else:
                return 'unknown'
    
    def _detect_bus_type(self, bus) -> str:
        """Erkennt den Typ eines Buses basierend auf dem Label."""
        label = str(bus.label).lower()
        
        if any(word in label for word in ['el', 'electric', 'power', 'strom']):
            return 'electrical'
        elif any(word in label for word in ['heat', 'thermal', 'wärme', 'therm']):
            return 'thermal'
        elif any(word in label for word in ['gas', 'fuel', 'brennstoff']):
            return 'gas'
        elif any(word in label for word in ['h2', 'hydrogen', 'wasserstoff']):
            return 'h2'
        else:
            return 'generic'
    
    def _get_node_color(self, node) -> str:
        """Bestimmt die Farbe eines Nodes."""
        category = self._categorize_node(node)
        label = str(node.label).lower()
        
        if category == 'bus':
            bus_type = self._detect_bus_type(node)
            return self.component_colors.get(f'bus_{bus_type}', self.component_colors['bus'])
        
        elif category == 'source':
            if any(word in label for word in ['pv', 'solar', 'wind', 'hydro', 'renewable']):
                return self.component_colors['source_renewable']
            elif any(word in label for word in ['grid', 'import', 'netz']):
                return self.component_colors['source_grid']
            elif any(word in label for word in ['gas', 'coal', 'oil', 'fossil']):
                return self.component_colors['source_fossil']
            else:
                return self.component_colors['source']
        
        elif category == 'sink':
            if any(word in label for word in ['load', 'demand', 'last', 'verbrauch']):
                return self.component_colors['sink_load']
            elif any(word in label for word in ['export', 'grid', 'einspeisung']):
                return self.component_colors['sink_export']
            else:
                return self.component_colors['sink']
        
        elif category == 'converter':
            if any(word in label for word in ['chp', 'kwk', 'bhkw']):
                return self.component_colors['converter_chp']
            elif any(word in label for word in ['heat_pump', 'hp', 'wärmepumpe', 'wp']):
                return self.component_colors['converter_hp']
            elif any(word in label for word in ['boiler', 'kessel']):
                return self.component_colors['converter_boiler']
            else:
                return self.component_colors['converter']
        
        elif category == 'storage':
            if any(word in label for word in ['battery', 'batterie', 'akku']):
                return self.component_colors['storage_battery']
            elif any(word in label for word in ['thermal', 'heat', 'wärme']):
                return self.component_colors['storage_thermal']
            else:
                return self.component_colors['storage']
        
        else:
            return '#DDDDDD'  # Grau für unbekannte Typen
    
    def _get_node_size(self, node) -> int:
        """Bestimmt die Größe eines Nodes."""
        category = self._categorize_node(node)
        base_size = self.node_sizes.get(category, 1000)
        
        # Größe basierend auf Kapazität anpassen (falls verfügbar)
        max_capacity = 0
        
        if hasattr(node, 'outputs'):
            for flow in node.outputs.values():
                if hasattr(flow, 'nominal_capacity') and flow.nominal_capacity:
                    if isinstance(flow.nominal_capacity, (int, float)):
                        max_capacity = max(max_capacity, flow.nominal_capacity)
        
        if hasattr(node, 'inputs'):
            for flow in node.inputs.values():
                if hasattr(flow, 'nominal_capacity') and flow.nominal_capacity:
                    if isinstance(flow.nominal_capacity, (int, float)):
                        max_capacity = max(max_capacity, flow.nominal_capacity)
        
        # Größe skalieren (10% - 200% des Basis-Wertes)
        if max_capacity > 0:
            scale_factor = min(2.0, max(0.1, max_capacity / 100))
            return int(base_size * scale_factor)
        
        return base_size
    
    def _analyze_flow(self, flow, source: str, target: str) -> Dict[str, Any]:
        """Analysiert die Eigenschaften eines Flows."""
        flow_info = {
            'source': source,
            'target': target,
            'properties': {},
            'style': 'normal'
        }
        
        try:
            # Nominal Capacity
            if hasattr(flow, 'nominal_capacity') and flow.nominal_capacity is not None:
                if isinstance(flow.nominal_capacity, Investment):
                    flow_info['properties']['investment'] = self._analyze_investment(flow.nominal_capacity)
                    flow_info['style'] = 'investment'
                elif isinstance(flow.nominal_capacity, (int, float)):
                    flow_info['properties']['nominal_capacity'] = flow.nominal_capacity
            
            # Variable Costs
            if hasattr(flow, 'variable_costs') and flow.variable_costs is not None:
                flow_info['properties']['variable_costs'] = flow.variable_costs
            
            # Min/Max
            if hasattr(flow, 'min') and flow.min is not None:
                flow_info['properties']['min'] = flow.min
            
            if hasattr(flow, 'max') and flow.max is not None:
                flow_info['properties']['max'] = flow.max
            
            # Fix
            if hasattr(flow, 'fix') and flow.fix is not None:
                flow_info['properties']['fix'] = "Profile (fix)"
            
            # NonConvex
            if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                flow_info['properties']['nonconvex'] = self._analyze_nonconvex(flow.nonconvex)
                flow_info['style'] = 'nonconvex'
                
        except Exception as e:
            # Bei Fehlern einfach leere Properties zurückgeben
            pass
        
        return flow_info
    
    def _analyze_investment(self, investment) -> Dict[str, Any]:
        """Analysiert Investment-Parameter."""
        inv_info = {}
        
        try:
            if hasattr(investment, 'ep_costs') and investment.ep_costs is not None:
                inv_info['ep_costs'] = investment.ep_costs
            
            if hasattr(investment, 'minimum') and investment.minimum is not None:
                inv_info['minimum'] = investment.minimum
            
            if hasattr(investment, 'maximum') and investment.maximum is not None:
                inv_info['maximum'] = investment.maximum
            
            if hasattr(investment, 'existing') and investment.existing is not None:
                inv_info['existing'] = investment.existing
            
            if hasattr(investment, 'nonconvex') and investment.nonconvex:
                inv_info['nonconvex'] = True
        except:
            pass
        
        return inv_info
    
    def _analyze_nonconvex(self, nonconvex) -> Dict[str, Any]:
        """Analysiert NonConvex-Parameter."""
        nc_info = {}
        
        try:
            attributes = ['minimum_uptime', 'minimum_downtime', 'startup_costs', 
                         'shutdown_costs', 'maximum_startups', 'maximum_shutdowns']
            
            for attr in attributes:
                if hasattr(nonconvex, attr):
                    value = getattr(nonconvex, attr)
                    if value is not None:
                        nc_info[attr] = value
        except:
            pass
        
        return nc_info
    
    def _extract_edges_from_node(self, node) -> List[Dict[str, Any]]:
        """Extrahiert Edges aus den inputs/outputs eines Nodes."""
        edges = []
        
        # Input-Edges
        if hasattr(node, 'inputs'):
            for input_node, flow in node.inputs.items():
                edge_info = {
                    'source': str(input_node.label),
                    'target': str(node.label),
                    'flow': flow,
                    'flow_info': self._analyze_flow(flow, str(input_node.label), str(node.label))
                }
                edges.append(edge_info)
        
        # Output-Edges
        if hasattr(node, 'outputs'):
            for output_node, flow in node.outputs.items():
                edge_info = {
                    'source': str(node.label),
                    'target': str(output_node.label),
                    'flow': flow,
                    'flow_info': self._analyze_flow(flow, str(node.label), str(output_node.label))
                }
                edges.append(edge_info)
        
        return edges
    
    def _collect_investments(self, energy_system) -> List[Dict[str, Any]]:
        """Sammelt alle Investment-Optionen im System."""
        investments = []
        
        for node in energy_system.nodes:
            # Inputs prüfen
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                        investments.append({
                            'node': str(node.label),
                            'connection': f"{input_node.label} → {node.label}",
                            'investment': self._analyze_investment(flow.nominal_capacity)
                        })
            
            # Outputs prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'nominal_capacity') and isinstance(flow.nominal_capacity, Investment):
                        investments.append({
                            'node': str(node.label),
                            'connection': f"{node.label} → {output_node.label}",
                            'investment': self._analyze_investment(flow.nominal_capacity)
                        })
        
        return investments
    
    def _collect_nonconvex(self, energy_system) -> List[Dict[str, Any]]:
        """Sammelt alle NonConvex-Definitionen im System."""
        nonconvex_list = []
        
        for node in energy_system.nodes:
            # Inputs prüfen
            if hasattr(node, 'inputs'):
                for input_node, flow in node.inputs.items():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_list.append({
                            'node': str(node.label),
                            'connection': f"{input_node.label} → {node.label}",
                            'nonconvex': self._analyze_nonconvex(flow.nonconvex)
                        })
            
            # Outputs prüfen
            if hasattr(node, 'outputs'):
                for output_node, flow in node.outputs.items():
                    if hasattr(flow, 'nonconvex') and flow.nonconvex is not None:
                        nonconvex_list.append({
                            'node': str(node.label),
                            'connection': f"{node.label} → {output_node.label}",
                            'nonconvex': self._analyze_nonconvex(flow.nonconvex)
                        })
        
        return nonconvex_list
    
    def _calculate_system_statistics(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Berechnet System-Statistiken."""
        stats = {
            'total_nodes': len(analysis['nodes']),
            'total_edges': len(analysis['edges']),
            'total_investments': len(analysis['investments']),
            'total_nonconvex': len(analysis['nonconvex']),
            'node_types': {},
            'complexity_score': 0
        }
        
        # Node-Typen zählen
        for node_info in analysis['nodes'].values():
            category = node_info['category']
            stats['node_types'][category] = stats['node_types'].get(category, 0) + 1
        
        # Komplexitäts-Score (grober Indikator)
        stats['complexity_score'] = (
            stats['total_nodes'] + 
            stats['total_edges'] * 0.5 + 
            stats['total_investments'] * 2 + 
            stats['total_nonconvex'] * 3
        )
        
        return stats
    
    def create_network_diagram(self, energy_system, filename: str = "energy_system_network") -> Optional[Path]:
        """
        Erstellt das Haupt-Netzwerk-Diagramm.
        
        Args:
            energy_system: oemof.solph EnergySystem
            filename: Dateiname (ohne Erweiterung)
            
        Returns:
            Pfad zur erstellten Datei oder None bei Fehlern
        """
        if not self.available:
            self.logger.info("📊 Netzwerk-Diagramm übersprungen (Abhängigkeiten fehlen)")
            return None
        
        self.logger.info("🕸️  Erstelle detailliertes Netzwerk-Diagramm...")
        
        try:
            # System analysieren
            analysis = self.analyze_energy_system(energy_system)
            
            if not analysis['nodes']:
                self.logger.warning("⚠️  Keine Nodes im EnergySystem gefunden")
                return None
            
            # Größe basierend auf Komplexität
            num_nodes = len(analysis['nodes'])
            if num_nodes <= 8:
                figsize = (12, 8)
                layout_func = nx.spring_layout
                layout_kwargs = {'k': 3, 'iterations': 100}
            elif num_nodes <= 15:
                figsize = (16, 12)
                layout_func = nx.kamada_kawai_layout
                layout_kwargs = {}
            else:
                figsize = (20, 16)
                layout_func = nx.spring_layout
                layout_kwargs = {'k': 5, 'iterations': 200}
            
            # NetworkX Graph erstellen
            G = nx.DiGraph()
            
            # Nodes hinzufügen
            for node_label, node_info in analysis['nodes'].items():
                G.add_node(node_label, **node_info)
            
            # Edges hinzufügen
            for edge in analysis['edges']:
                G.add_edge(
                    edge['source'], 
                    edge['target'],
                    flow_info=edge['flow_info']
                )
            
            # Layout berechnen
            try:
                pos = layout_func(G, **layout_kwargs)
            except:
                # Fallback bei Layout-Problemen
                pos = nx.spring_layout(G, iterations=50)
            
            # Plot erstellen
            fig, ax = plt.subplots(figsize=figsize)
            fig.suptitle('Energy System Network Diagram\n(oemof.solph Interpretation)', 
                        fontsize=16, fontweight='bold')
            
            # Nodes zeichnen
            self._draw_nodes(G, pos, analysis, ax)
            
            # Edges zeichnen
            self._draw_edges(G, pos, analysis, ax)
            
            # Labels zeichnen
            self._draw_labels(G, pos, analysis, ax)
            
            # Legende erstellen
            self._create_legend(analysis, ax)
            
            # Investment-Info hinzufügen (falls vorhanden)
            if analysis['investments']:
                self._add_investment_info(analysis, fig)
            
            ax.set_title(f"Nodes: {len(analysis['nodes'])} | " +
                        f"Edges: {len(analysis['edges'])} | " +
                        f"Investments: {len(analysis['investments'])}", 
                        fontsize=12)
            ax.axis('off')
            
            plt.tight_layout()
            
            # Speichern
            output_file = self.output_dir / f"{filename}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            self.logger.info(f"✅ Netzwerk-Diagramm erstellt: {output_file.name}")
            
            # Zusätzlich System-Analyse als Text speichern
            self._save_system_analysis(analysis, filename)
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen des Netzwerk-Diagramms: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
            return None
    
    def _draw_nodes(self, G, pos, analysis, ax):
        """Zeichnet die Nodes mit entsprechenden Farben und Größen."""
        for node_label in G.nodes():
            node_info = analysis['nodes'][node_label]
            
            # Investment-Komponenten hervorheben
            has_investment = any(inv['node'] == node_label for inv in analysis['investments'])
            
            if has_investment:
                # Äußerer Ring für Investment
                nx.draw_networkx_nodes(
                    G, pos, nodelist=[node_label],
                    node_color=self.component_colors['investment'],
                    node_size=node_info['size'] + 400,
                    alpha=0.4, ax=ax
                )
            
            # Haupt-Node
            nx.draw_networkx_nodes(
                G, pos, nodelist=[node_label],
                node_color=node_info['color'],
                node_size=node_info['size'],
                alpha=0.8, ax=ax
            )
    
    def _draw_edges(self, G, pos, analysis, ax):
        """Zeichnet die Edges mit entsprechenden Styles."""
        
        # Nach Style gruppieren
        edge_groups = {'normal': [], 'investment': [], 'nonconvex': []}
        
        for edge in G.edges(data=True):
            source, target, data = edge
            flow_info = data.get('flow_info', {})
            style = flow_info.get('style', 'normal')
            edge_groups[style].append((source, target))
        
        # Jede Gruppe mit entsprechendem Style zeichnen
        for style, edges in edge_groups.items():
            if edges:
                style_props = self.edge_styles[style]
                nx.draw_networkx_edges(
                    G, pos, edgelist=edges,
                    edge_color='black' if style == 'normal' else self.component_colors['investment'],
                    width=style_props['width'],
                    style=style_props['style'],
                    alpha=style_props['alpha'],
                    arrows=True, arrowsize=20, arrowstyle='->',
                    ax=ax
                )
    
    def _draw_labels(self, G, pos, analysis, ax):
        """Zeichnet Node-Labels mit Hintergrund."""
        
        # Labels mit Kapazitäts-Info vorbereiten
        labels = {}
        for node_label in G.nodes():
            node_info = analysis['nodes'][node_label]
            
            # Hauptlabel
            main_label = node_label
            
            # Kapazitäts-Info hinzufügen (falls verfügbar)
            capacity_info = []
            
            for flow_info in node_info['flows']['outputs']:
                if 'nominal_capacity' in flow_info['properties']:
                    cap = flow_info['properties']['nominal_capacity']
                    capacity_info.append(f"{cap:.0f}kW")
                elif 'investment' in flow_info['properties']:
                    inv = flow_info['properties']['investment']
                    if 'maximum' in inv:
                        capacity_info.append(f"≤{inv['maximum']:.0f}kW")
            
            if capacity_info:
                labels[node_label] = f"{main_label}\n({', '.join(capacity_info)})"
            else:
                labels[node_label] = main_label
        
        # Labels mit weißem Hintergrund zeichnen
        for node, (x, y) in pos.items():
            ax.text(x, y, labels[node], 
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=8, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8, edgecolor='gray'))
    
    def _create_legend(self, analysis, ax):
        """Erstellt eine umfassende Legende."""
        
        legend_elements = []
        
        # Node-Typ Legende
        node_types_present = set()
        for node_info in analysis['nodes'].values():
            category = node_info['category']
            node_types_present.add(category)
        
        legend_elements.append(mlines.Line2D([], [], color='white', marker='o', linestyle='None',
                                           markersize=0, label='Node Types:'))
        
        type_labels = {
            'bus': 'Bus (Energy Hub)',
            'source': 'Source (Generator)',
            'sink': 'Sink (Consumer)',
            'converter': 'Converter (Transformer)',
            'storage': 'Storage'
        }
        
        for node_type in sorted(node_types_present):
            if node_type in self.component_colors:
                color = self.component_colors[node_type]
                label = type_labels.get(node_type, node_type.title())
                legend_elements.append(mpatches.Patch(color=color, label=f'  {label}'))
        
        # Edge-Style Legende
        legend_elements.append(mlines.Line2D([], [], color='white', marker='o', linestyle='None',
                                           markersize=0, label=''))
        legend_elements.append(mlines.Line2D([], [], color='white', marker='o', linestyle='None',
                                           markersize=0, label='Flow Types:'))
        
        legend_elements.append(mlines.Line2D([], [], color='black', linewidth=2, 
                                           label='  Normal Flow'))
        
        if analysis['investments']:
            legend_elements.append(mlines.Line2D([], [], color=self.component_colors['investment'], 
                                               linewidth=3, linestyle='--',
                                               label='  Investment Flow'))
        
        if analysis['nonconvex']:
            legend_elements.append(mlines.Line2D([], [], color='black', linewidth=2, 
                                               linestyle=':',
                                               label='  NonConvex Flow'))
        
        # Investment-Highlight
        if analysis['investments']:
            legend_elements.append(mlines.Line2D([], [], color='white', marker='o', linestyle='None',
                                               markersize=0, label=''))
            legend_elements.append(mpatches.Patch(color=self.component_colors['investment'], 
                                                alpha=0.4, label='Investment Component'))
        
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5),
                 frameon=True, fancybox=True, shadow=True)
    
    def _add_investment_info(self, analysis, fig):
        """Fügt Investment-Informationen als Text hinzu."""
        
        if not analysis['investments']:
            return
        
        info_text = "Investment Options:\n"
        info_text += "=" * 20 + "\n"
        
        for i, inv in enumerate(analysis['investments'][:5]):  # Nur erste 5 anzeigen
            inv_data = inv['investment']
            info_text += f"{i+1}. {inv['node']}:\n"
            
            if 'ep_costs' in inv_data:
                info_text += f"   Costs: {inv_data['ep_costs']:.1f} €/kW\n"
            
            if 'minimum' in inv_data and 'maximum' in inv_data:
                info_text += f"   Range: {inv_data['minimum']:.0f}-{inv_data['maximum']:.0f} kW\n"
            elif 'maximum' in inv_data:
                info_text += f"   Max: {inv_data['maximum']:.0f} kW\n"
            
            info_text += "\n"
        
        if len(analysis['investments']) > 5:
            info_text += f"... and {len(analysis['investments']) - 5} more\n"
        
        # Text-Box hinzufügen
        fig.text(0.02, 0.02, info_text, fontsize=8, fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.8))
    
    def _save_system_analysis(self, analysis, filename):
        """Speichert die detaillierte System-Analyse als Text-Datei."""
        
        analysis_file = self.output_dir / f"{filename}_analysis.txt"
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write("OEMOF.SOLPH ENERGY SYSTEM ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            
            # Zeitindex-Info
            if analysis['timeindex_info']:
                f.write("SIMULATION TIMEFRAME:\n")
                f.write("-" * 25 + "\n")
                info = analysis['timeindex_info']
                f.write(f"Start: {info['start']}\n")
                f.write(f"End: {info['end']}\n")
                f.write(f"Periods: {info['periods']}\n")
                f.write(f"Frequency: {info['freq']}\n")
                f.write(f"Total Hours: {info['total_hours']}\n\n")
            
            # System-Statistiken
            f.write("SYSTEM STATISTICS:\n")
            f.write("-" * 20 + "\n")
            stats = analysis['statistics']
            f.write(f"Total Nodes: {stats['total_nodes']}\n")
            f.write(f"Total Connections: {stats['total_edges']}\n")
            f.write(f"Investment Options: {stats['total_investments']}\n")
            f.write(f"NonConvex Components: {stats['total_nonconvex']}\n")
            f.write(f"Complexity Score: {stats['complexity_score']:.1f}\n\n")
            
            # Node-Typen
            f.write("NODE TYPES:\n")
            f.write("-" * 12 + "\n")
            for node_type, count in stats['node_types'].items():
                f.write(f"{node_type.title()}: {count}\n")
            f.write("\n")
            
            # Detaillierte Node-Analyse
            f.write("DETAILED NODE ANALYSIS:\n")
            f.write("-" * 25 + "\n")
            
            for node_label, node_info in analysis['nodes'].items():
                f.write(f"{node_label} ({node_info['type']}):\n")
                
                # Eigenschaften
                if node_info['properties']:
                    f.write("  Properties:\n")
                    for prop, value in node_info['properties'].items():
                        f.write(f"    {prop}: {value}\n")
                
                # Input Flows
                if node_info['flows']['inputs']:
                    f.write("  Input Flows:\n")
                    for flow in node_info['flows']['inputs']:
                        f.write(f"    ← {flow['source']}")
                        if flow['properties']:
                            props = [f"{k}={v}" for k, v in flow['properties'].items()]
                            f.write(f" ({', '.join(props)})")
                        f.write("\n")
                
                # Output Flows  
                if node_info['flows']['outputs']:
                    f.write("  Output Flows:\n")
                    for flow in node_info['flows']['outputs']:
                        f.write(f"    → {flow['target']}")
                        if flow['properties']:
                            props = [f"{k}={v}" for k, v in flow['properties'].items()]
                            f.write(f" ({', '.join(props)})")
                        f.write("\n")
                
                f.write("\n")
            
            # Investment-Details
            if analysis['investments']:
                f.write("INVESTMENT DETAILS:\n")
                f.write("-" * 20 + "\n")
                
                for inv in analysis['investments']:
                    f.write(f"{inv['connection']}:\n")
                    for param, value in inv['investment'].items():
                        f.write(f"  {param}: {value}\n")
                    f.write("\n")
            
            # NonConvex-Details
            if analysis['nonconvex']:
                f.write("NONCONVEX DETAILS:\n")
                f.write("-" * 18 + "\n")
                
                for nc in analysis['nonconvex']:
                    f.write(f"{nc['connection']}:\n")
                    for param, value in nc['nonconvex'].items():
                        f.write(f"  {param}: {value}\n")
                    f.write("\n")
        
        self.logger.debug(f"      📋 {analysis_file.name}")
    
    def create_flow_capacity_diagram(self, energy_system, filename: str = "flow_capacities") -> Optional[Path]:
        """
        Erstellt ein Diagramm, das die Kapazitäten aller Flows zeigt.
        """
        if not self.available:
            return None
        
        self.logger.info("📊 Erstelle Flow-Kapazitäts-Diagramm...")
        
        try:
            analysis = self.analyze_energy_system(energy_system)
            
            # Kapazitätsdaten sammeln
            flow_capacities = {}
            investment_flows = {}
            
            for edge in analysis['edges']:
                flow_info = edge['flow_info']
                connection = f"{edge['source']} → {edge['target']}"
                
                if 'nominal_capacity' in flow_info['properties']:
                    flow_capacities[connection] = flow_info['properties']['nominal_capacity']
                elif 'investment' in flow_info['properties']:
                    inv_data = flow_info['properties']['investment']
                    if 'maximum' in inv_data:
                        investment_flows[connection] = inv_data['maximum']
            
            if not flow_capacities and not investment_flows:
                self.logger.info("📊 Keine Kapazitätsdaten für Flow-Diagramm verfügbar")
                return None
            
            # Plot erstellen
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            fig.suptitle('Flow Capacities Overview', fontsize=16, fontweight='bold')
            
            # Feste Kapazitäten
            if flow_capacities:
                connections = list(flow_capacities.keys())
                capacities = list(flow_capacities.values())
                
                bars1 = ax1.barh(connections, capacities, color='steelblue', alpha=0.7)
                ax1.set_xlabel('Nominal Capacity [kW]')
                ax1.set_title('Fixed Capacities')
                ax1.grid(True, alpha=0.3)
                
                # Werte auf Balken
                for bar, capacity in zip(bars1, capacities):
                    ax1.text(bar.get_width() + max(capacities) * 0.01, bar.get_y() + bar.get_height()/2,
                            f'{capacity:.1f}', va='center', fontsize=8)
            else:
                ax1.text(0.5, 0.5, 'No fixed capacities defined', ha='center', va='center',
                        transform=ax1.transAxes, fontsize=12)
                ax1.set_xlim(0, 1)
                ax1.set_ylim(0, 1)
            
            # Investment-Kapazitäten
            if investment_flows:
                connections = list(investment_flows.keys())
                max_capacities = list(investment_flows.values())
                
                bars2 = ax2.barh(connections, max_capacities, color='orange', alpha=0.7)
                ax2.set_xlabel('Maximum Investment Capacity [kW]')
                ax2.set_title('Investment Options')
                ax2.grid(True, alpha=0.3)
                
                # Werte auf Balken
                for bar, capacity in zip(bars2, max_capacities):
                    ax2.text(bar.get_width() + max(max_capacities) * 0.01, bar.get_y() + bar.get_height()/2,
                            f'{capacity:.1f}', va='center', fontsize=8)
            else:
                ax2.text(0.5, 0.5, 'No investment options defined', ha='center', va='center',
                        transform=ax2.transAxes, fontsize=12)
                ax2.set_xlim(0, 1)
                ax2.set_ylim(0, 1)
            
            plt.tight_layout()
            
            # Speichern
            output_file = self.output_dir / f"{filename}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"✅ Flow-Kapazitäts-Diagramm erstellt: {output_file.name}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen des Kapazitäts-Diagramms: {e}")
            return None
    
    def create_system_overview_dashboard(self, energy_system, filename: str = "system_dashboard") -> Optional[Path]:
        """
        Erstellt ein Dashboard mit mehreren System-Übersichten.
        """
        if not self.available:
            return None
        
        self.logger.info("📊 Erstelle System-Dashboard...")
        
        try:
            analysis = self.analyze_energy_system(energy_system)
            
            # Dashboard mit 4 Subplots
            fig = plt.figure(figsize=(20, 16))
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
            
            fig.suptitle('Energy System Dashboard\n(oemof.solph Configuration Overview)', 
                        fontsize=20, fontweight='bold')
            
            # 1. Hauptnetzwerk (groß, oben links)
            ax_network = fig.add_subplot(gs[0:2, 0:2])
            self._create_mini_network(analysis, ax_network)
            
            # 2. Node-Typ Verteilung (oben rechts)
            ax_nodes = fig.add_subplot(gs[0, 2])
            self._create_node_distribution_pie(analysis, ax_nodes)
            
            # 3. Kapazitäts-Übersicht (mitte rechts)
            ax_capacity = fig.add_subplot(gs[1, 2])
            self._create_capacity_overview(analysis, ax_capacity)
            
            # 4. Investment-Übersicht (unten links)
            ax_investment = fig.add_subplot(gs[2, 0])
            self._create_investment_overview(analysis, ax_investment)
            
            # 5. System-Statistiken (unten mitte)
            ax_stats = fig.add_subplot(gs[2, 1])
            self._create_stats_table(analysis, ax_stats)
            
            # 6. Zeitindex-Info (unten rechts)
            ax_time = fig.add_subplot(gs[2, 2])
            self._create_timeindex_info(analysis, ax_time)
            
            # Speichern
            output_file = self.output_dir / f"{filename}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"✅ System-Dashboard erstellt: {output_file.name}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen des Dashboards: {e}")
            return None
    
    def _create_mini_network(self, analysis, ax):
        """Erstellt eine vereinfachte Netzwerk-Darstellung für das Dashboard."""
        
        # NetworkX Graph erstellen
        G = nx.DiGraph()
        
        for node_label, node_info in analysis['nodes'].items():
            G.add_node(node_label, **node_info)
        
        for edge in analysis['edges']:
            G.add_edge(edge['source'], edge['target'])
        
        # Einfaches Layout
        try:
            pos = nx.spring_layout(G, k=2, iterations=50)
        except:
            pos = nx.circular_layout(G)
        
        # Nodes zeichnen
        for node_label in G.nodes():
            node_info = analysis['nodes'][node_label]
            
            nx.draw_networkx_nodes(
                G, pos, nodelist=[node_label],
                node_color=node_info['color'],
                node_size=800,  # Kleinere Größe für Dashboard
                alpha=0.8, ax=ax
            )
        
        # Edges zeichnen
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, 
                              arrowsize=15, width=1.5, alpha=0.7, ax=ax)
        
        # Labels
        labels = {node: node.split('_')[0] if '_' in node else node for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
        
        ax.set_title('Network Structure', fontweight='bold')
        ax.axis('off')
    
    def _create_node_distribution_pie(self, analysis, ax):
        """Erstellt ein Tortendiagramm der Node-Verteilung."""
        
        node_types = analysis['statistics']['node_types']
        
        if node_types:
            colors = [self.component_colors.get(ntype, '#DDDDDD') for ntype in node_types.keys()]
            
            wedges, texts, autotexts = ax.pie(
                node_types.values(), 
                labels=node_types.keys(),
                colors=colors,
                autopct='%1.0f',
                startangle=90
            )
            
            ax.set_title('Node Distribution', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No nodes', ha='center', va='center', transform=ax.transAxes)
    
    def _create_capacity_overview(self, analysis, ax):
        """Erstellt eine Kapazitäts-Übersicht."""
        
        # Kapazitäten sammeln
        capacities = {}
        
        for node_info in analysis['nodes'].values():
            for flow in node_info['flows']['outputs']:
                if 'nominal_capacity' in flow['properties']:
                    node_name = node_info['label']
                    capacities[node_name] = flow['properties']['nominal_capacity']
        
        if capacities:
            nodes = list(capacities.keys())
            caps = list(capacities.values())
            
            bars = ax.bar(range(len(nodes)), caps, color='steelblue', alpha=0.7)
            ax.set_xticks(range(len(nodes)))
            ax.set_xticklabels([n.split('_')[0] for n in nodes], rotation=45, ha='right')
            ax.set_ylabel('Capacity [kW]')
            ax.set_title('Component Capacities', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Werte auf Balken
            for bar, cap in zip(bars, caps):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(caps)*0.02,
                       f'{cap:.0f}', ha='center', va='bottom', fontsize=8)
        else:
            ax.text(0.5, 0.5, 'No capacity data', ha='center', va='center', transform=ax.transAxes)
    
    def _create_investment_overview(self, analysis, ax):
        """Erstellt eine Investment-Übersicht."""
        
        if analysis['investments']:
            inv_data = []
            labels = []
            
            for inv in analysis['investments'][:5]:  # Nur erste 5
                inv_info = inv['investment']
                labels.append(inv['node'].split('_')[0])
                
                if 'maximum' in inv_info:
                    inv_data.append(inv_info['maximum'])
                else:
                    inv_data.append(0)
            
            bars = ax.barh(range(len(labels)), inv_data, color='orange', alpha=0.7)
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)
            ax.set_xlabel('Max Investment [kW]')
            ax.set_title('Investment Options', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Werte
            for bar, val in zip(bars, inv_data):
                if val > 0:
                    ax.text(bar.get_width() + max(inv_data)*0.02, bar.get_y() + bar.get_height()/2,
                           f'{val:.0f}', va='center', fontsize=8)
        else:
            ax.text(0.5, 0.5, 'No investments', ha='center', va='center', transform=ax.transAxes)
    
    def _create_stats_table(self, analysis, ax):
        """Erstellt eine Statistik-Tabelle."""
        
        stats = analysis['statistics']
        
        table_data = [
            ['Nodes', stats['total_nodes']],
            ['Connections', stats['total_edges']],
            ['Investments', stats['total_investments']],
            ['NonConvex', stats['total_nonconvex']],
            ['Complexity', f"{stats['complexity_score']:.1f}"]
        ]
        
        table = ax.table(cellText=table_data,
                        colLabels=['Parameter', 'Value'],
                        cellLoc='center',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Header styling
        for i in range(2):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax.set_title('System Statistics', fontweight='bold')
        ax.axis('off')
    
    def _create_timeindex_info(self, analysis, ax):
        """Erstellt Zeitindex-Informationen."""
        
        time_info = analysis['timeindex_info']
        
        if time_info:
            info_text = f"Start: {time_info['start'].strftime('%Y-%m-%d')}\n"
            info_text += f"End: {time_info['end'].strftime('%Y-%m-%d')}\n"
            info_text += f"Periods: {time_info['periods']:,}\n"
            info_text += f"Frequency: {time_info['freq']}\n"
            info_text += f"Total Hours: {time_info['total_hours']:,}"
            
            ax.text(0.1, 0.5, info_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='center', fontfamily='monospace',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.7))
        else:
            ax.text(0.5, 0.5, 'No time info', ha='center', va='center', transform=ax.transAxes)
        
        ax.set_title('Simulation Timeframe', fontweight='bold')
        ax.axis('off')
    
    def is_available(self) -> bool:
        """Prüft ob die Visualisierung verfügbar ist."""
        return self.available


# Integration in das bestehende Visualizer-Modul
def add_network_visualization_to_visualizer():
    """
    Code-Snippet zur Integration in das bestehende visualizer.py Modul.
    
    Fügen Sie diese Methode zur Visualizer-Klasse hinzu:
    """
    
    network_visualization_extension = '''
    def create_network_visualizations(self, results, energy_system, excel_data):
        """Erstellt Netzwerk-Visualisierungen (Erweiterung für Visualizer)."""
        
        # Network Visualizer erstellen
        from modules.network_visualizer import EnergySystemNetworkVisualizer
        
        network_viz = EnergySystemNetworkVisualizer(self.output_dir, self.settings)
        
        if network_viz.is_available():
            # Haupt-Netzwerk-Diagramm
            network_file = network_viz.create_network_diagram(energy_system)
            if network_file:
                self.created_files.append(network_file)
            
            # Flow-Kapazitäts-Diagramm
            capacity_file = network_viz.create_flow_capacity_diagram(energy_system)
            if capacity_file:
                self.created_files.append(capacity_file)
            
            # System-Dashboard
            dashboard_file = network_viz.create_system_overview_dashboard(energy_system)
            if dashboard_file:
                self.created_files.append(dashboard_file)
        else:
            self.logger.info("📊 Netzwerk-Visualisierungen übersprungen (NetworkX/Matplotlib fehlt)")
    '''
    
    return network_visualization_extension


# Test-Funktion
def test_network_visualizer():
    """Testfunktion für den Network Visualizer."""
    import tempfile
    from pathlib import Path
    
    # Dummy EnergySystem simulieren
    class DummyFlow:
        def __init__(self, nominal_capacity=None, variable_costs=None):
            self.nominal_capacity = nominal_capacity
            self.variable_costs = variable_costs
    
    class DummyNode:
        def __init__(self, label, node_type='Bus'):
            self.label = label
            self.inputs = {}
            self.outputs = {}
            self._type = node_type
    
    class DummyEnergySystem:
        def __init__(self):
            # Einfaches Test-System erstellen
            self.el_bus = DummyNode('el_bus', 'Bus')
            self.pv = DummyNode('pv_plant', 'Source')
            self.load = DummyNode('el_load', 'Sink')
            self.grid = DummyNode('grid_import', 'Source')
            
            # Verbindungen
            self.pv.outputs[self.el_bus] = DummyFlow(nominal_capacity=100)
            self.grid.outputs[self.el_bus] = DummyFlow(nominal_capacity=500, variable_costs=0.25)
            self.load.inputs[self.el_bus] = DummyFlow()
            
            self.el_bus.inputs[self.pv] = DummyFlow(nominal_capacity=100)
            self.el_bus.inputs[self.grid] = DummyFlow(nominal_capacity=500, variable_costs=0.25)
            self.el_bus.outputs[self.load] = DummyFlow()
            
            self.nodes = [self.el_bus, self.pv, self.load, self.grid]
            self.timeindex = pd.date_range('2025-01-01', periods=24, freq='h')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        visualizer = EnergySystemNetworkVisualizer(Path(temp_dir), settings)
        
        print(f"Network Visualizer verfügbar: {visualizer.is_available()}")
        
        if visualizer.is_available():
            dummy_system = DummyEnergySystem()
            
            # Test-Visualisierungen erstellen
            network_file = visualizer.create_network_diagram(dummy_system)
            capacity_file = visualizer.create_flow_capacity_diagram(dummy_system)
            dashboard_file = visualizer.create_system_overview_dashboard(dummy_system)
            
            print(f"✅ Network Visualizer Test erfolgreich!")
            if network_file:
                print(f"   📊 Netzwerk-Diagramm: {network_file}")
            if capacity_file:
                print(f"   📊 Kapazitäts-Diagramm: {capacity_file}")
            if dashboard_file:
                print(f"   📊 Dashboard: {dashboard_file}")
        else:
            print("❌ NetworkX oder matplotlib nicht verfügbar")


if __name__ == "__main__":
    test_network_visualizer()
                   