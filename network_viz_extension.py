#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Network Visualization Extension
================================================

Optionale Erweiterung für das Visualizer-Modul zur Erstellung von
Netzwerk-Diagrammen mit oemof-visio und Graphviz.

WICHTIG: Diese Funktionalität ist optional und erfordert zusätzliche
         Installationen, die unter Windows problematisch sein können.

Installationsanweisungen:
1. Graphviz installieren: https://graphviz.org/download/
2. Unbedingt "Add to PATH" aktivieren!
3. pip install git+https://github.com/oemof/oemof_visio.git[network]
4. Windows: Eventuell "dot -c" ausführen
"""

import logging
from pathlib import Path
from typing import Optional, Any, Dict, List

# Optionale Imports für Netzwerk-Visualisierung
try:
    from oemof_visio import ESGraphRenderer
    OEMOF_VISIO_AVAILABLE = True
except ImportError:
    ESGraphRenderer = None
    OEMOF_VISIO_AVAILABLE = False

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    graphviz = None
    GRAPHVIZ_AVAILABLE = False


class NetworkDiagramGenerator:
    """Erstellt Netzwerk-Diagramme von oemof.solph EnergySystem-Objekten."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Network Diagram Generator.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Verfügbarkeit prüfen
        self.available = OEMOF_VISIO_AVAILABLE and GRAPHVIZ_AVAILABLE
        
        if not self.available:
            self._log_availability_status()
    
    def _log_availability_status(self):
        """Loggt den Status der Verfügbarkeit."""
        if not OEMOF_VISIO_AVAILABLE:
            self.logger.warning("⚠️  oemof-visio nicht verfügbar")
            self.logger.info("   💡 Installation: pip install git+https://github.com/oemof/oemof_visio.git[network]")
        
        if not GRAPHVIZ_AVAILABLE:
            self.logger.warning("⚠️  Graphviz nicht verfügbar")
            self.logger.info("   💡 Installation: https://graphviz.org/download/")
            self.logger.info("   ⚠️  Windows-Benutzer: Unbedingt 'Add to PATH' aktivieren!")
    
    def create_network_diagram(self, energy_system: Any, filename: str = "network_diagram") -> Optional[Path]:
        """
        Erstellt ein Netzwerk-Diagramm des EnergySystem.
        
        Args:
            energy_system: oemof.solph EnergySystem
            filename: Dateiname (ohne Erweiterung)
            
        Returns:
            Pfad zur erstellten Datei oder None bei Fehlern
        """
        if not self.available:
            self.logger.info("📊 Netzwerk-Diagramm übersprungen (Abhängigkeiten fehlen)")
            return None
        
        self.logger.info("🕸️  Erstelle Netzwerk-Diagramm...")
        
        try:
            # Prüfe Systemgröße
            num_nodes = len(energy_system.nodes) if hasattr(energy_system, 'nodes') else 0
            
            if num_nodes > 20:
                self.logger.warning(f"⚠️  Großes System ({num_nodes} Knoten) - Diagramm könnte unübersichtlich werden")
                if num_nodes > 50:
                    self.logger.warning("⚠️  System zu groß für sinnvolles Netzwerk-Diagramm - übersprungen")
                    return None
            
            # Ausgabepfad
            output_path = self.output_dir / filename
            
            # ESGraphRenderer erstellen und ausführen
            renderer = ESGraphRenderer(
                energy_system,
                legend=True,
                filepath=str(output_path),  # Ohne Dateierweiterung
                img_format="png"  # PNG ist universeller als PDF
            )
            
            # Diagramm rendern
            renderer.render()
            
            # Erfolg prüfen
            created_file = output_path.with_suffix('.png')
            if created_file.exists():
                self.logger.info(f"✅ Netzwerk-Diagramm erstellt: {created_file.name}")
                return created_file
            else:
                self.logger.warning("⚠️  Netzwerk-Diagramm wurde nicht erstellt")
                return None
        
        except Exception as e:
            self.logger.warning(f"⚠️  Fehler beim Erstellen des Netzwerk-Diagramms: {e}")
            self.logger.info("   💡 Prüfen Sie die Graphviz-Installation und PATH-Variable")
            return None
    
    def create_simple_networkx_diagram(self, energy_system: Any, filename: str = "simple_network") -> Optional[Path]:
        """
        Erstellt ein einfaches Netzwerk-Diagramm mit networkx und matplotlib.
        
        Fallback-Option wenn oemof-visio nicht verfügbar ist.
        """
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            self.logger.warning("⚠️  NetworkX oder Matplotlib nicht verfügbar für einfaches Netzwerk-Diagramm")
            return None
        
        self.logger.info("🕸️  Erstelle einfaches Netzwerk-Diagramm...")
        
        try:
            # Netzwerk-Graph aus EnergySystem erstellen
            if hasattr(energy_system, 'nodes'):
                G = nx.DiGraph()
                
                # Knoten hinzufügen
                node_colors = {}
                for node in energy_system.nodes:
                    node_label = str(node.label)
                    G.add_node(node_label)
                    
                    # Farben basierend auf Knotentyp
                    if 'bus' in node_label.lower():
                        node_colors[node_label] = 'lightblue'
                    elif any(word in node_label.lower() for word in ['pv', 'wind', 'solar']):
                        node_colors[node_label] = 'green'
                    elif any(word in node_label.lower() for word in ['load', 'demand']):
                        node_colors[node_label] = 'red'
                    elif any(word in node_label.lower() for word in ['grid', 'import', 'export']):
                        node_colors[node_label] = 'orange'
                    else:
                        node_colors[node_label] = 'lightgray'
                
                # Kanten hinzufügen (basierend auf inputs/outputs)
                for node in energy_system.nodes:
                    if hasattr(node, 'inputs'):
                        for input_node in node.inputs.keys():
                            G.add_edge(str(input_node.label), str(node.label))
                    if hasattr(node, 'outputs'):
                        for output_node in node.outputs.keys():
                            G.add_edge(str(node.label), str(output_node.label))
                
                # Layout berechnen
                if len(G.nodes()) <= 10:
                    pos = nx.spring_layout(G, k=2, iterations=50)
                else:
                    pos = nx.kamada_kawai_layout(G)
                
                # Plot erstellen
                plt.figure(figsize=(12, 8))
                
                # Knoten zeichnen
                colors = [node_colors.get(node, 'lightgray') for node in G.nodes()]
                nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=1500, alpha=0.9)
                
                # Kanten zeichnen
                nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, 
                                     arrowsize=20, arrowstyle='->', width=1.5)
                
                # Labels zeichnen
                nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
                
                # Legende
                legend_elements = [
                    mpatches.Patch(color='lightblue', label='Bus'),
                    mpatches.Patch(color='green', label='Renewable Source'),
                    mpatches.Patch(color='red', label='Load/Demand'),
                    mpatches.Patch(color='orange', label='Grid Connection'),
                    mpatches.Patch(color='lightgray', label='Other')
                ]
                plt.legend(handles=legend_elements, loc='upper right')
                
                plt.title('Energy System Network Diagram')
                plt.axis('off')
                plt.tight_layout()
                
                # Speichern
                output_file = self.output_dir / f"{filename}.png"
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                self.logger.info(f"✅ Einfaches Netzwerk-Diagramm erstellt: {output_file.name}")
                return output_file
            
        except Exception as e:
            self.logger.warning(f"⚠️  Fehler beim Erstellen des einfachen Netzwerk-Diagramms: {e}")
            return None
        
        return None
    
    def is_available(self) -> bool:
        """Prüft ob Netzwerk-Visualisierung verfügbar ist."""
        return self.available
    
    def get_installation_instructions(self) -> List[str]:
        """Gibt Installationsanweisungen zurück."""
        instructions = []
        
        if not GRAPHVIZ_AVAILABLE:
            instructions.extend([
                "1. Graphviz installieren:",
                "   Windows: https://graphviz.org/download/",
                "   ⚠️  Unbedingt 'Add Graphviz to the system PATH' aktivieren!",
                "   Linux: sudo apt-get install graphviz graphviz-dev",
                "   Mac: brew install graphviz",
                ""
            ])
        
        if not OEMOF_VISIO_AVAILABLE:
            instructions.extend([
                "2. oemof-visio installieren:",
                "   pip install git+https://github.com/oemof/oemof_visio.git[network]",
                ""
            ])
        
        instructions.extend([
            "3. Testen:",
            "   python -c \"import oemof_visio; print('✅ oemof-visio verfügbar')\"",
            "   dot -V  # Sollte Graphviz-Version anzeigen"
        ])
        
        return instructions


# Erweiterung für das bestehende Visualizer-Modul
def extend_visualizer_with_network_diagrams():
    """
    Erweitert das bestehende Visualizer-Modul um Netzwerk-Diagramm-Funktionalität.
    
    Diese Funktion kann in visualizer.py eingefügt werden.
    """
    
    # Ergänzung für die Visualizer-Klasse:
    def create_network_visualizations(self, results, energy_system, excel_data):
        """Erstellt Netzwerk-Visualisierungen (Erweiterung für Visualizer)."""
        
        # Network Diagram Generator erstellen
        network_gen = NetworkDiagramGenerator(self.output_dir, self.settings)
        
        if network_gen.is_available():
            # Vollständiges oemof-visio Diagramm versuchen
            network_file = network_gen.create_network_diagram(energy_system)
            if network_file:
                self.created_files.append(network_file)
        else:
            # Fallback: Einfaches NetworkX-Diagramm
            simple_file = network_gen.create_simple_networkx_diagram(energy_system)
            if simple_file:
                self.created_files.append(simple_file)
            else:
                # Installationsanweisungen loggen
                self.logger.info("💡 Netzwerk-Visualisierung Installationsanweisungen:")
                for instruction in network_gen.get_installation_instructions():
                    self.logger.info(f"   {instruction}")


# Test-Funktion
def test_network_visualization():
    """Testfunktion für Netzwerk-Visualisierung."""
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        network_gen = NetworkDiagramGenerator(Path(temp_dir), settings)
        
        print(f"Netzwerk-Visualisierung verfügbar: {network_gen.is_available()}")
        
        if not network_gen.is_available():
            print("\nInstallationsanweisungen:")
            for instruction in network_gen.get_installation_instructions():
                print(instruction)


if __name__ == "__main__":
    test_network_visualization()
