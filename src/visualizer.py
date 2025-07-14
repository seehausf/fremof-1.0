#!/usr/bin/env python3
"""
src/visualizer.py - oemof-visio Integration für Energiesystem-Visualisierung

Phase 2: Visualisierung mit oemof-visio
- Energy System Graph (Netzwerk-Diagramm)  
- Sankey Diagramm (Energie-Flüsse)
- Plotting von Zeitreihen-Ergebnissen
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class EnergySystemVisualizer:
    """Visualisiert oemof-solph Energiesysteme und Ergebnisse mit oemof-visio"""
    
    def __init__(self, energy_system, results: Dict[str, Any] = None):
        """
        Initialisiert den Visualizer
        
        Args:
            energy_system: oemof EnergySystem
            results: Optimierungsergebnisse aus ModelRunner (optional)
        """
        self.energy_system = energy_system
        self.results = results['results'] if results and 'results' in results else None
        self.meta_results = results['meta_results'] if results and 'meta_results' in results else None
        
        # Output-Verzeichnis sicherstellen
        self.output_dir = Path('results')
        self.output_dir.mkdir(exist_ok=True)
        
        # oemof-visio verfügbar?
        self._check_visio_availability()
    
    def _check_visio_availability(self):
        """Prüft ob oemof-visio verfügbar ist"""
        try:
            import oemof_visio
            self.visio_available = True
            logger.info("oemof-visio verfügbar")
        except ImportError as e:
            self.visio_available = False
            logger.warning(f"oemof-visio nicht verfügbar: {e}")
            logger.info("Installation: pip install git+https://github.com/oemof/oemof_visio.git[network]")
    
    def create_energy_system_graph(self, 
                                 filepath: Optional[str] = None,
                                 img_format: str = "pdf",
                                 legend: bool = True) -> Optional[Path]:
        """
        Erstellt Netzwerk-Diagramm des Energiesystems
        
        Args:
            filepath: Pfad für Ausgabedatei (ohne Extension)
            img_format: Format ('pdf', 'png', 'svg')
            legend: Legende anzeigen
            
        Returns:
            Pfad der erstellten Datei oder None
        """
        if not self.visio_available:
            logger.error("oemof-visio nicht verfügbar - kann kein System-Graph erstellen")
            return None
        
        try:
            from oemof_visio import ESGraphRenderer
            
            # Standard-Pfad falls nicht angegeben
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = str(self.output_dir / f"energy_system_graph_{timestamp}")
            
            logger.info(f"Erstelle Energy System Graph: {filepath}.{img_format}")
            
            # Graph Renderer erstellen
            esgr = ESGraphRenderer(
                self.energy_system,
                legend=legend,
                filepath=filepath,
                img_format=img_format
            )
            
            # Graph rendern
            esgr.render()
            
            output_file = Path(f"{filepath}.{img_format}")
            if output_file.exists():
                logger.info(f"Energy System Graph erstellt: {output_file}")
                return output_file
            else:
                logger.warning(f"Energy System Graph nicht gefunden: {output_file}")
                return None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Energy System Graphs: {e}")
            return None
    
    def create_sankey_diagram(self, 
                            show: bool = True,
                            save_html: bool = True,
                            filepath: Optional[str] = None) -> Optional[Path]:
        """
        Erstellt Sankey-Diagramm der Energie-Flüsse
        
        Args:
            show: Diagramm anzeigen
            save_html: Als HTML speichern
            filepath: Pfad für HTML-Datei
            
        Returns:
            Pfad der HTML-Datei oder None
        """
        if not self.visio_available:
            logger.error("oemof-visio nicht verfügbar - kann kein Sankey-Diagramm erstellen")
            return None
        
        if self.results is None:
            logger.error("Keine Ergebnisse verfügbar - kann kein Sankey-Diagramm erstellen")
            return None
        
        try:
            import plotly.io as pio
            from oemof_visio import ESGraphRenderer
            
            logger.info("Erstelle Sankey-Diagramm...")
            
            # Graph Renderer erstellen
            esgr = ESGraphRenderer(self.energy_system)
            
            # Sankey erstellen
            fig_dict = esgr.sankey(self.results)
            
            # Anzeigen
            if show:
                pio.show(fig_dict)
            
            # Speichern
            if save_html:
                if filepath is None:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filepath = str(self.output_dir / f"sankey_diagram_{timestamp}.html")
                
                pio.write_html(fig_dict, filepath)
                output_file = Path(filepath)
                
                if output_file.exists():
                    logger.info(f"Sankey-Diagramm gespeichert: {output_file}")
                    return output_file
            
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Sankey-Diagramms: {e}")
            return None
    
    def create_bus_plot(self, 
                       bus_label: str,
                       filepath: Optional[str] = None,
                       figsize: tuple = (12, 8)) -> Optional[Path]:
        """
        Erstellt Bus-Plot (In/Out-Flows über Zeit)
        
        Args:
            bus_label: Label des Bus
            filepath: Pfad für Ausgabedatei
            figsize: Größe der Abbildung
            
        Returns:
            Pfad der erstellten Datei oder None
        """
        if not self.visio_available:
            logger.warning("oemof-visio nicht verfügbar - erstelle einfachen Bus-Plot")
            return self._create_simple_bus_plot(bus_label, filepath, figsize)
        
        if self.results is None:
            logger.error("Keine Ergebnisse verfügbar - kann keinen Bus-Plot erstellen")
            return None
        
        try:
            import matplotlib.pyplot as plt
            from oemof_visio.plot import io_plot
            
            logger.info(f"Erstelle Bus-Plot für: {bus_label}")
            
            # Ergebnisse für Bus extrahieren
            bus_results = self._extract_bus_results(bus_label)
            if bus_results.empty:
                logger.warning(f"Keine Ergebnisse für Bus '{bus_label}' gefunden")
                return None
            
            # Plot erstellen
            fig, ax = plt.subplots(figsize=figsize)
            
            # oemof-visio io_plot verwenden
            io_plot(
                bus_label=bus_label,
                df=bus_results,
                ax=ax
            )
            
            plt.title(f"Bus Flows: {bus_label}")
            plt.xlabel("Zeit")
            plt.ylabel("Power [kW]")
            plt.legend()
            plt.tight_layout()
            
            # Speichern
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = str(self.output_dir / f"bus_plot_{bus_label}_{timestamp}.png")
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            output_file = Path(filepath)
            if output_file.exists():
                logger.info(f"Bus-Plot erstellt: {output_file}")
                return output_file
            
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Bus-Plots: {e}")
            # Fallback auf einfachen Plot
            return self._create_simple_bus_plot(bus_label, filepath, figsize)
    
    def _create_simple_bus_plot(self, 
                               bus_label: str,
                               filepath: Optional[str] = None,
                               figsize: tuple = (12, 8)) -> Optional[Path]:
        """Fallback: Einfacher Bus-Plot ohne oemof-visio"""
        
        if self.results is None:
            return None
        
        try:
            import matplotlib.pyplot as plt
            
            logger.info(f"Erstelle einfachen Bus-Plot für: {bus_label}")
            
            # Bus-Flows extrahieren
            bus_flows = self._extract_bus_flows_simple(bus_label)
            
            if not bus_flows:
                logger.warning(f"Keine Flows für Bus '{bus_label}' gefunden")
                return None
            
            # Plot erstellen
            fig, ax = plt.subplots(figsize=figsize)
            
            for flow_name, flow_data in bus_flows.items():
                if 'sequences' in flow_data and not flow_data['sequences'].empty:
                    sequences = flow_data['sequences']
                    for col in sequences.columns:
                        ax.plot(sequences[col], label=f"{flow_name}_{col}")
            
            plt.title(f"Bus Flows: {bus_label}")
            plt.xlabel("Time Step")
            plt.ylabel("Power [kW]")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Speichern
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = str(self.output_dir / f"bus_plot_simple_{bus_label}_{timestamp}.png")
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            output_file = Path(filepath)
            if output_file.exists():
                logger.info(f"Einfacher Bus-Plot erstellt: {output_file}")
                return output_file
            
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim einfachen Bus-Plot: {e}")
            return None
    
    def _extract_bus_results(self, bus_label: str) -> pd.DataFrame:
        """Extrahiert Ergebnisse für einen spezifischen Bus (oemof-visio Format)"""
        
        bus_data = []
        
        for flow_key, flow_data in self.results.items():
            if 'sequences' in flow_data and not flow_data['sequences'].empty:
                # Prüfe ob Flow zu diesem Bus gehört
                if len(flow_key) == 2:
                    from_node, to_node = flow_key
                    if from_node == bus_label or to_node == bus_label:
                        sequences = flow_data['sequences']
                        for col in sequences.columns:
                            bus_data.append({
                                'flow_key': flow_key,
                                'column': col,
                                'data': sequences[col]
                            })
        
        if not bus_data:
            return pd.DataFrame()
        
        # DataFrame mit Multi-Index erstellen (oemof-visio kompatibel)
        result_df = pd.DataFrame()
        for item in bus_data:
            col_name = (item['flow_key'], item['column'])
            result_df[col_name] = item['data'].values
        
        return result_df
    
    def _extract_bus_flows_simple(self, bus_label: str) -> Dict[str, Any]:
        """Extrahiert Flows für einen Bus (einfaches Format)"""
        
        bus_flows = {}
        
        for flow_key, flow_data in self.results.items():
            if len(flow_key) == 2:
                from_node, to_node = flow_key
                if from_node == bus_label or to_node == bus_label:
                    flow_name = f"{from_node}→{to_node}"
                    bus_flows[flow_name] = flow_data
        
        return bus_flows
    
    def create_all_visualizations(self, project_name: str = "energy_system") -> List[Path]:
        """
        Erstellt alle verfügbaren Visualisierungen
        
        Args:
            project_name: Name für die Ausgabedateien
            
        Returns:
            Liste der erstellten Dateien
        """
        logger.info("Erstelle alle Visualisierungen...")
        
        created_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Energy System Graph
        graph_file = self.create_energy_system_graph(
            filepath=str(self.output_dir / f"{project_name}_graph_{timestamp}"),
            img_format="pdf"
        )
        if graph_file:
            created_files.append(graph_file)
        
        # 2. Sankey Diagramm (nur wenn Ergebnisse vorhanden)
        if self.results:
            sankey_file = self.create_sankey_diagram(
                show=False,
                save_html=True,
                filepath=str(self.output_dir / f"{project_name}_sankey_{timestamp}.html")
            )
            if sankey_file:
                created_files.append(sankey_file)
        
        # 3. Bus-Plots für alle Buses
        if self.results and hasattr(self.energy_system, 'nodes'):
            for node in self.energy_system.nodes:
                if hasattr(node, 'label') and 'bus' in str(type(node)).lower():
                    bus_plot_file = self.create_bus_plot(
                        bus_label=node.label,
                        filepath=str(self.output_dir / f"{project_name}_bus_{node.label}_{timestamp}.png")
                    )
                    if bus_plot_file:
                        created_files.append(bus_plot_file)
        
        logger.info(f"Visualisierungen erstellt: {len(created_files)} Dateien")
        return created_files
    
    def get_summary(self) -> str:
        """Erstellt Zusammenfassung der Visualisierungs-Möglichkeiten"""
        
        summary = []
        summary.append(f"oemof-visio verfügbar: {'✅' if self.visio_available else '❌'}")
        summary.append(f"Ergebnisse verfügbar: {'✅' if self.results else '❌'}")
        
        if self.visio_available:
            summary.append("Verfügbare Visualisierungen:")
            summary.append("  - Energy System Graph (PDF/PNG/SVG)")
            if self.results:
                summary.append("  - Sankey Diagramm (HTML)")
                summary.append("  - Bus-Plots (PNG)")
        else:
            summary.append("Für vollständige Visualisierung installieren:")
            summary.append("  pip install git+https://github.com/oemof/oemof_visio.git[network]")
        
        return " | ".join(summary)

# =============================================================================
# INTEGRATION INSTRUCTIONS
# =============================================================================

INSTALLATION_GUIDE = """
=== OEMOF-VISIO INSTALLATION ===

1. STANDARD INSTALLATION:
   pip install git+https://github.com/oemof/oemof_visio.git

2. MIT NETZWERK-FEATURES (empfohlen):
   pip install git+https://github.com/oemof/oemof_visio.git[network]

3. FÜR WINDOWS zusätzlich:
   - Graphviz von https://graphviz.org/download/ installieren
   - "Add to PATH" während Installation aktivieren
   - System neu starten

4. TEST:
   python -c "import oemof_visio; print('✅ oemof-visio verfügbar')"

=== USAGE EXAMPLE ===

from src.visualizer import EnergySystemVisualizer

# Nach Optimierung
visualizer = EnergySystemVisualizer(energy_system, results)

# Einzelne Visualisierungen
graph_file = visualizer.create_energy_system_graph()
sankey_file = visualizer.create_sankey_diagram()
bus_plot = visualizer.create_bus_plot('house_bus')

# Alle Visualisierungen
all_files = visualizer.create_all_visualizations('household_pv')
"""

if __name__ == "__main__":
    print("🎨 oemof-visio Visualisierungs-Integration")
    print("✅ Energy System Graph (Netzwerk)")
    print("✅ Sankey Diagramm (Energie-Flüsse)")
    print("✅ Bus-Plots (Zeitreihen)")
    print("✅ Fallback ohne oemof-visio")
    print("\n" + INSTALLATION_GUIDE)