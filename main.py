#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Energiesystemmodellierung - Hauptprogramm
==========================================================

Zentrale Koordination der Energiesystemoptimierung mit modularer Architektur.
Orchestriert den Datenfluss zwischen Excel-Import, Systemaufbau, Optimierung
und Ergebnisverarbeitung.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Projektmodule importieren
try:
    from modules.excel_reader import ExcelReader
    from modules.system_builder import SystemBuilder
    from modules.optimizer import Optimizer
    from modules.results_processor import ResultsProcessor
    from modules.visualizer import Visualizer
    from modules.analyzer import Analyzer
except ImportError as e:
    print(f"❌ Fehler beim Importieren der Module: {e}")
    print("Stellen Sie sicher, dass alle Module im 'modules/' Verzeichnis vorhanden sind.")
    sys.exit(1)


class EnergySystemProject:
    """Hauptklasse für die Energiesystemmodellierung."""
    
    def __init__(self, project_file: Path, config: Dict[str, Any]):
        """
        Initialisiert das Energiesystemprojekt.
        
        Args:
            project_file: Pfad zur Excel-Projektdatei
            config: Konfigurationsdictionary mit Modul- und Systemeinstellungen
        """
        self.project_file = project_file
        self.config = config
        self.project_name = project_file.stem
        
        # Output-Verzeichnis erstellen
        self.output_dir = Path("data/output") / self.project_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Logger konfigurieren
        self.setup_logging()
        
        # Datencontainer
        self.excel_data = None
        self.energy_system = None
        self.optimization_model = None
        self.results = None
        
        # Module initialisieren
        self.initialize_modules()
    
    def setup_logging(self):
        """Konfiguriert das Logging-System."""
        log_level = logging.DEBUG if self.config['settings']['debug_mode'] else logging.INFO
        
        # Logger konfigurieren
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / f"{self.project_name}.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 Starte Projekt: {self.project_name}")
    
    def initialize_modules(self):
        """Initialisiert alle verfügbaren Module."""
        self.modules = {}
        
        # Excel Reader (immer erforderlich)
        self.modules['excel_reader'] = ExcelReader(self.config['settings'])
        
        # System Builder (immer erforderlich)
        self.modules['system_builder'] = SystemBuilder(self.config['settings'])
        
        # Optimizer (immer erforderlich)
        self.modules['optimizer'] = Optimizer(self.config['settings'])
        
        # Results Processor (immer erforderlich)
        self.modules['results_processor'] = ResultsProcessor(
            self.output_dir, self.config['settings']
        )
        
        # Optionale Module
        if self.config['modules']['visualizer']:
            self.modules['visualizer'] = Visualizer(
                self.output_dir, self.config['settings']
            )
        
        if self.config['modules']['analyzer']:
            self.modules['analyzer'] = Analyzer(
                self.output_dir, self.config['settings']
            )
        
        self.logger.info(f"✅ {len(self.modules)} Module initialisiert")
    
    def validate_input_file(self) -> bool:
        """Validiert die Excel-Eingabedatei."""
        if not self.project_file.exists():
            self.logger.error(f"❌ Projektdatei nicht gefunden: {self.project_file}")
            return False
        
        if not self.project_file.suffix.lower() in ['.xlsx', '.xls']:
            self.logger.error(f"❌ Ungültiges Dateiformat: {self.project_file.suffix}")
            return False
        
        self.logger.info(f"✅ Eingabedatei validiert: {self.project_file.name}")
        return True
    
    def step_1_read_excel(self) -> bool:
        """Schritt 1: Excel-Daten einlesen."""
        self.logger.info("📊 Schritt 1: Excel-Daten einlesen")
        
        try:
            start_time = time.time()
            self.excel_data = self.modules['excel_reader'].read_project_file(self.project_file)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Excel-Daten erfolgreich eingelesen ({elapsed_time:.2f}s)")
            
            # Kurze Zusammenfassung der eingelesenen Daten
            summary = self.modules['excel_reader'].get_data_summary(self.excel_data)
            for key, value in summary.items():
                self.logger.info(f"   📋 {key}: {value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Einlesen der Excel-Daten: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def step_2_build_system(self) -> bool:
        """Schritt 2: Energiesystem aufbauen."""
        self.logger.info("🏗️  Schritt 2: Energiesystem aufbauen")
        
        try:
            start_time = time.time()
            self.energy_system = self.modules['system_builder'].build_energy_system(
                self.excel_data
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Energiesystem erfolgreich aufgebaut ({elapsed_time:.2f}s)")
            
            # System-Zusammenfassung
            system_info = self.modules['system_builder'].get_system_summary(
                self.energy_system
            )
            for key, value in system_info.items():
                self.logger.info(f"   🔧 {key}: {value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Aufbau des Energiesystems: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def step_3_optimize(self) -> bool:
        """Schritt 3: Optimierung durchführen."""
        self.logger.info("⚡ Schritt 3: Optimierung durchführen")
        
        try:
            start_time = time.time()
            
            # Modell erstellen und optimieren
            self.optimization_model, self.results = self.modules['optimizer'].optimize(
                self.energy_system
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Optimierung erfolgreich abgeschlossen ({elapsed_time:.2f}s)")
            
            # Optimierungs-Zusammenfassung
            opt_info = self.modules['optimizer'].get_optimization_summary(
                self.optimization_model, self.results
            )
            for key, value in opt_info.items():
                self.logger.info(f"   ⚡ {key}: {value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Optimierung: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def step_4_process_results(self) -> bool:
        """Schritt 4: Ergebnisse verarbeiten."""
        self.logger.info("📈 Schritt 4: Ergebnisse verarbeiten")
        
        try:
            start_time = time.time()
            
            # Ergebnisse verarbeiten und speichern
            processed_results = self.modules['results_processor'].process_results(
                self.results, self.energy_system, self.excel_data
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Ergebnisse erfolgreich verarbeitet ({elapsed_time:.2f}s)")
            
            # Gespeicherte Dateien auflisten
            output_files = list(self.output_dir.glob("*"))
            self.logger.info(f"   💾 {len(output_files)} Dateien erstellt:")
            for file in sorted(output_files)[:5]:  # Nur erste 5 anzeigen
                self.logger.info(f"      • {file.name}")
            if len(output_files) > 5:
                self.logger.info(f"      ... und {len(output_files) - 5} weitere")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Ergebnisverarbeitung: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def step_5_visualize(self) -> bool:
        """Schritt 5: Ergebnisse visualisieren (optional)."""
        if not self.config['modules']['visualizer']:
            self.logger.info("⏭️  Schritt 5: Visualisierung übersprungen (deaktiviert)")
            return True
        
        self.logger.info("📊 Schritt 5: Ergebnisse visualisieren")
        
        try:
            start_time = time.time()
            
            # Visualisierungen erstellen
            viz_files = self.modules['visualizer'].create_visualizations(
                self.results, self.energy_system, self.excel_data
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Visualisierungen erfolgreich erstellt ({elapsed_time:.2f}s)")
            
            # Erstellte Visualisierungen auflisten
            self.logger.info(f"   🎨 {len(viz_files)} Visualisierungen erstellt:")
            for file in sorted(viz_files)[:3]:  # Nur erste 3 anzeigen
                self.logger.info(f"      • {file.name}")
            if len(viz_files) > 3:
                self.logger.info(f"      ... und {len(viz_files) - 3} weitere")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Visualisierung: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def step_6_analyze(self) -> bool:
        """Schritt 6: Vertiefende Analysen (optional)."""
        if not self.config['modules']['analyzer']:
            self.logger.info("⏭️  Schritt 6: Analysen übersprungen (deaktiviert)")
            return True
        
        self.logger.info("🔍 Schritt 6: Vertiefende Analysen")
        
        try:
            start_time = time.time()
            
            # Analysen durchführen
            analysis_results = self.modules['analyzer'].perform_analysis(
                self.results, self.energy_system, self.excel_data
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Analysen erfolgreich durchgeführt ({elapsed_time:.2f}s)")
            
            # Analyse-Zusammenfassung
            for analysis_type, result in analysis_results.items():
                self.logger.info(f"   🔍 {analysis_type}: {result.get('summary', 'Abgeschlossen')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei den Analysen: {e}")
            if self.config['settings']['debug_mode']:
                import traceback
                traceback.print_exc()
            return False
    
    def save_project_summary(self):
        """Speichert eine Projekt-Zusammenfassung."""
        try:
            summary_file = self.output_dir / f"{self.project_name}_summary.txt"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Energiesystem-Optimierung: {self.project_name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Projektdatei: {self.project_file}\n")
                f.write(f"Ausgabeverzeichnis: {self.output_dir}\n")
                f.write(f"Solver: {self.config['settings']['solver']}\n")
                f.write(f"Ausführungszeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Modulstatus
                f.write("Verwendete Module:\n")
                for module, active in self.config['modules'].items():
                    status = "✅" if active else "❌"
                    f.write(f"  {status} {module}\n")
                f.write("\n")
                
                # Dateien im Output-Verzeichnis
                output_files = list(self.output_dir.glob("*"))
                f.write(f"Erstellte Dateien ({len(output_files)}):\n")
                for file in sorted(output_files):
                    f.write(f"  • {file.name}\n")
            
            self.logger.info(f"💾 Projekt-Zusammenfassung gespeichert: {summary_file.name}")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Fehler beim Speichern der Zusammenfassung: {e}")
    
    def run(self) -> bool:
        """Führt das komplette Projekt aus."""
        self.logger.info("🎯 Starte Projektausführung")
        project_start_time = time.time()
        
        # Schritt 0: Eingabedatei validieren
        if not self.validate_input_file():
            return False
        
        # Schritt 1: Excel-Daten einlesen
        if not self.step_1_read_excel():
            return False
        
        # Schritt 2: Energiesystem aufbauen
        if not self.step_2_build_system():
            return False
        
        # Schritt 3: Optimierung durchführen
        if not self.step_3_optimize():
            return False
        
        # Schritt 4: Ergebnisse verarbeiten
        if not self.step_4_process_results():
            return False
        
        # Schritt 5: Visualisierungen erstellen (optional)
        if not self.step_5_visualize():
            return False
        
        # Schritt 6: Vertiefende Analysen (optional)
        if not self.step_6_analyze():
            return False
        
        # Projekt-Zusammenfassung speichern
        self.save_project_summary()
        
        # Gesamtzeit berechnen
        total_time = time.time() - project_start_time
        self.logger.info(f"🎉 Projekt erfolgreich abgeschlossen!")
        self.logger.info(f"⏱️  Gesamtausführungszeit: {total_time:.2f} Sekunden")
        self.logger.info(f"📁 Ergebnisse verfügbar in: {self.output_dir}")
        
        return True


def main_program(project_file: Path, config: Dict[str, Any]) -> bool:
    """
    Hauptfunktion für die Ausführung eines Energiesystemprojekts.
    
    Args:
        project_file: Pfad zur Excel-Projektdatei
        config: Konfigurationsdictionary
    
    Returns:
        bool: True bei erfolgreichem Abschluss, False bei Fehlern
    """
    try:
        # Projekt initialisieren und ausführen
        project = EnergySystemProject(project_file, config)
        return project.run()
        
    except KeyboardInterrupt:
        print("\n⚠️  Ausführung durch Benutzer unterbrochen")
        return False
        
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {e}")
        if config.get('settings', {}).get('debug_mode', False):
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    # Testausführung wenn direkt gestartet
    if len(sys.argv) > 1:
        project_file = Path(sys.argv[1])
        
        # Standard-Konfiguration für Testausführung
        test_config = {
            'modules': {
                'excel_reader': True,
                'system_builder': True,
                'optimizer': True,
                'results_processor': True,
                'visualizer': False,
                'analyzer': False
            },
            'settings': {
                'solver': 'cbc',
                'output_format': 'xlsx',
                'create_plots': False,
                'save_model': False,
                'debug_mode': True
            }
        }
        
        success = main_program(project_file, test_config)
        sys.exit(0 if success else 1)
    else:
        print("❌ Keine Projektdatei angegeben")
        print("Verwendung: python main.py <projektdatei.xlsx>")
        print("Oder starten Sie 'python runme.py' für das interaktive Menü")
        sys.exit(1)