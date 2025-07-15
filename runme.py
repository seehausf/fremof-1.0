#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Hauptprogramm (AKTUALISIERT)
=============================================

Vollständiges Hauptprogramm mit integriertem Timestep-Management
und automatischen Timestep-Visualisierungen.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.1 (mit Timestep-Management)
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

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


class EnergySystemOptimizer:
    """Hauptklasse für die Energiesystem-Optimierung mit Timestep-Management."""
    
    def __init__(self):
        """Initialisiert das Hauptprogramm."""
        
        # Projektstruktur einrichten
        self.setup_project_structure()
        
        # Logging einrichten
        self.setup_logging()
        
        # Module initialisieren
        self.initialize_modules()
        
        # Verfügbare Projekte laden
        self.load_available_projects()
    
    def setup_project_structure(self):
        """Erstellt die erforderliche Projektstruktur."""
        self.project_root = Path(__file__).parent
        
        # Verzeichnisse erstellen
        self.directories = {
            'examples': self.project_root / 'examples',
            'data': self.project_root / 'data',
            'output': self.project_root / 'data' / 'output',
            'modules': self.project_root / 'modules',
            'logs': self.project_root / 'logs'
        }
        
        for name, path in self.directories.items():
            path.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Richtet das Logging-System ein."""
        # Haupt-Logger
        self.logger = logging.getLogger('main')
        self.logger.setLevel(logging.INFO)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Handler hinzufügen
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
    
    def initialize_modules(self):
        """Initialisiert alle Module mit Timestep-Management-Support."""
        
        # Basis-Einstellungen
        self.settings = {
            'solver': 'cbc',
            'debug_mode': True,
            'output_format': 'xlsx',
            'create_visualizations': True,
            'create_analysis': False,  # Standardmäßig deaktiviert
            'save_model': False,
            'project_root': self.project_root,
            'output_dir': self.directories['output']  # Für Timestep-Visualisierungen
        }
        
        try:
            # Module erstellen
            self.excel_reader = ExcelReader(self.settings)
            self.system_builder = SystemBuilder(self.settings)
            self.optimizer = Optimizer(self.settings)
            self.results_processor = ResultsProcessor(self.directories['output'], self.settings)
            self.visualizer = Visualizer(self.directories['output'], self.settings)
            self.analyzer = Analyzer(self.directories['output'], self.settings)
            
            # Module-Liste für Übersicht
            self.modules = {
                'excel_reader': self.excel_reader,
                'system_builder': self.system_builder,
                'optimizer': self.optimizer,
                'results_processor': self.results_processor,
                'visualizer': self.visualizer,
                'analyzer': self.analyzer
            }
            
            self.logger.info(f"✅ {len(self.modules)} Module initialisiert")
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Modul-Initialisierung: {e}")
            raise
    
    def load_available_projects(self):
        """Lädt verfügbare Projekte aus dem examples/ Verzeichnis."""
        self.available_projects = []
        
        examples_dir = self.directories['examples']
        
        if examples_dir.exists():
            excel_files = list(examples_dir.glob('*.xlsx'))
            
            for excel_file in excel_files:
                if not excel_file.name.startswith('~'):  # Temporäre Excel-Dateien ignorieren
                    self.available_projects.append({
                        'name': excel_file.stem,
                        'file': excel_file,
                        'description': f"Beispiel - {excel_file.name}"
                    })
            
            self.available_projects.sort(key=lambda x: x['name'])
    
    def show_main_menu(self):
        """Zeigt das Hauptmenü an."""
        print("\n📋 HAUPTMENÜ")
        print("-" * 40)
        print("1. 🚀 Projekt ausführen")
        print("2. ⚙️  Module konfigurieren")
        print("3. 📁 Neues Beispielprojekt erstellen")
        print("4. 🔧 Projektstruktur einrichten")
        print("5. ℹ️  Projektinformationen anzeigen")
        print("6. 🕒 Timestep-Management testen")  # NEU
        print("7. ❌ Beenden")
        
        try:
            choice = input("\nOption auswählen (1-7): ").strip()
            return choice
        except KeyboardInterrupt:
            print("\n👋 Programm beendet.")
            return "7"
    
    def show_project_menu(self):
        """Zeigt verfügbare Projekte an."""
        if not self.available_projects:
            print("❌ Keine Projekte im 'examples/' Verzeichnis gefunden.")
            print("Erstellen Sie zunächst ein Beispielprojekt (Option 3).")
            return None
        
        print("\n📂 VERFÜGBARE PROJEKTE")
        print("-" * 40)
        
        for i, project in enumerate(self.available_projects, 1):
            print(f" {i}. 📋 {project['description']}")
        
        try:
            choice = input("\nProjekt auswählen (Nummer): ").strip()
            project_idx = int(choice) - 1
            
            if 0 <= project_idx < len(self.available_projects):
                return self.available_projects[project_idx]
            else:
                print("❌ Ungültige Auswahl.")
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
            return None
    

    def run_project(self, project: Dict[str, Any]):
        """Führt ein Projekt komplett durch - KORRIGIERT für richtige Output-Verzeichnisse."""
        project_name = project['name']
        project_file = project['file']
        
        print(f"🚀 Starte Projekt: {project_file.name}")
        self.logger.info(f"🚀 Starte Projekt: {project_name}")
        
        # Output-Verzeichnis für dieses Projekt
        project_output_dir = self.directories['output'] / project_name
        project_output_dir.mkdir(exist_ok=True)
        
        # ** KORRIGIERT: Settings für dieses Projekt aktualisieren **
        project_settings = self.settings.copy()
        project_settings['output_dir'] = project_output_dir  # Für Timestep-Visualizer
        project_settings['project_name'] = project_name     # Für Fallback-Logik
        project_settings['base_output_dir'] = self.directories['output']  # Basis-Output-Verzeichnis
        
        # ** WICHTIG: Excel-Reader mit den aktualisierten Settings versorgen **
        self.excel_reader.settings = project_settings
        
        # Module mit projekt-spezifischen Settings aktualisieren
        self.results_processor.output_dir = project_output_dir
        self.visualizer.output_dir = project_output_dir
        self.analyzer.output_dir = project_output_dir
        
        # File-Logger für dieses Projekt einrichten
        self.setup_project_logging(project_output_dir, project_name)
        
        try:
            self.logger.info("🎯 Starte Projektausführung")
            total_start_time = time.time()
            
            # Eingabedatei validieren
            if not project_file.exists():
                raise FileNotFoundError(f"Projektdatei nicht gefunden: {project_file}")
            
            self.logger.info(f"✅ Eingabedatei validiert: {project_file.name}")
            
            # 📊 Schritt 1: Excel-Daten einlesen (MIT TIMESTEP-MANAGEMENT)
            self.logger.info("📊 Schritt 1: Excel-Daten einlesen")
            step_start = time.time()
            
            # ** KORRIGIERT: process_excel_data verwendet jetzt die aktualisierten Settings **
            excel_data = self.excel_reader.process_excel_data(project_file)
            
            step_time = time.time() - step_start
            self.logger.info(f"✅ Excel-Daten erfolgreich eingelesen ({step_time:.2f}s)")
            
            # Excel-Daten-Zusammenfassung
            summary = self.excel_reader.get_data_summary(excel_data)
            for key, value in summary.items():
                self.logger.info(f"   📋 {key}: {value}")
            
            # ** TIMESTEP-MANAGEMENT ERGEBNISSE LOGGEN **
            self.log_timestep_management_results(excel_data, project_output_dir)
            
            # Rest der Methode bleibt gleich...
            # 🏗️ Schritt 2: Energiesystem aufbauen
            self.logger.info("🏗️  Schritt 2: Energiesystem aufbauen")
            step_start = time.time()
            
            energy_system = self.system_builder.build_energy_system(excel_data)
            
            step_time = time.time() - step_start
            self.logger.info(f"✅ Energiesystem erfolgreich aufgebaut ({step_time:.2f}s)")
            
            # System-Zusammenfassung
            system_summary = self.system_builder.get_system_summary(energy_system)
            for key, value in system_summary.items():
                self.logger.info(f"   🔧 {key}: {value}")
            
            # ⚡ Schritt 3: Optimierung durchführen
            self.logger.info("⚡ Schritt 3: Optimierung durchführen")
            step_start = time.time()
            
            optimization_model, results = self.optimizer.optimize(energy_system)
            
            step_time = time.time() - step_start
            self.logger.info(f"✅ Optimierung erfolgreich abgeschlossen ({step_time:.2f}s)")
            
            # Optimierungs-Zusammenfassung
            opt_summary = self.optimizer.get_optimization_summary(optimization_model, results)
            for key, value in opt_summary.items():
                self.logger.info(f"   ⚡ {key}: {value}")
            
            # 📈 Schritt 4: Ergebnisse verarbeiten
            self.logger.info("📈 Schritt 4: Ergebnisse verarbeiten")
            step_start = time.time()
            
            processed_results = self.results_processor.process_results(
                results, energy_system, excel_data
            )
            
            step_time = time.time() - step_start
            self.logger.info(f"✅ Ergebnisse erfolgreich verarbeitet ({step_time:.2f}s)")
            
            # Erstellte Dateien loggen
            output_files = getattr(self.results_processor, 'output_files', [])
            if output_files:
                self.logger.info(f"   💾 {len(output_files)} Dateien erstellt:")
                for output_file in output_files[:5]:  # Erste 5 anzeigen
                    self.logger.info(f"      • {Path(output_file).name}")
                if len(output_files) > 5:
                    self.logger.info(f"      ... und {len(output_files) - 5} weitere")
            
            # 📊 Schritt 5: Visualisierungen erstellen
            if self.settings.get('create_visualizations', True):
                self.logger.info("📊 Schritt 5: Ergebnisse visualisieren")
                step_start = time.time()
                
                visualization_files = self.visualizer.create_visualizations(
                    results, energy_system, excel_data
                )
                
                step_time = time.time() - step_start
                self.logger.info(f"✅ Visualisierungen erfolgreich erstellt ({step_time:.2f}s)")
                
                # Visualisierungen loggen
                if visualization_files:
                    self.logger.info(f"   🎨 {len(visualization_files)} Visualisierungen erstellt:")
                    for viz_file in visualization_files[:5]:  # Erste 5 anzeigen
                        self.logger.info(f"      • {Path(viz_file).name}")
                    if len(visualization_files) > 5:
                        self.logger.info(f"      ... und {len(visualization_files) - 5} weitere")
            else:
                self.logger.info("⏭️  Schritt 5: Visualisierungen übersprungen (deaktiviert)")
            
            # 🔍 Schritt 6: Vertiefende Analysen (optional)
            if self.settings.get('create_analysis', False):
                self.logger.info("🔍 Schritt 6: Vertiefende Analysen")
                step_start = time.time()
                
                analysis_results = self.analyzer.perform_analysis(
                    results, energy_system, excel_data
                )
                
                step_time = time.time() - step_start
                self.logger.info(f"✅ Analysen erfolgreich abgeschlossen ({step_time:.2f}s)")
                
                # Analyse-Zusammenfassung
                if analysis_results:
                    self.logger.info(f"   🔍 {len(analysis_results)} Analysen durchgeführt:")
                    for analysis_type in analysis_results.keys():
                        self.logger.info(f"      • {analysis_type.title()}")
            else:
                self.logger.info("⏭️  Schritt 6: Analysen übersprungen (deaktiviert)")
            
            # Projekt-Zusammenfassung erstellen
            self.create_project_summary(
                project_name, excel_data, energy_system, 
                optimization_model, results, project_output_dir
            )
            
            # Gesamtzeit
            total_time = time.time() - total_start_time
            
            self.logger.info("🎉 Projekt erfolgreich abgeschlossen!")
            self.logger.info(f"⏱️  Gesamtausführungszeit: {total_time:.2f} Sekunden")
            self.logger.info(f"📁 Ergebnisse verfügbar in: {project_output_dir.relative_to(self.project_root)}")
            
            print(f"\n✅ Projekt '{project_name}' erfolgreich abgeschlossen!")
            print(f"⏱️  Ausführungszeit: {total_time:.2f} Sekunden")
            print(f"📁 Ergebnisse: {project_output_dir}")
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Projektausführung: {e}")
            print(f"\n❌ Projekt fehlgeschlagen: {e}")
            
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
    
    
    def log_timestep_management_results(self, excel_data: Dict[str, Any], project_output_dir: Path):
        """Loggt die Ergebnisse des Timestep-Managements mit korrektem Output-Verzeichnis."""
        
        # Timestep-Reduktions-Statistiken
        if 'timestep_reduction_stats' in excel_data:
            stats = excel_data['timestep_reduction_stats']
            
            self.logger.info("🕒 TIMESTEP-MANAGEMENT ANGEWENDET:")
            self.logger.info(f"   📊 Strategie: {stats['strategy']}")
            self.logger.info(f"   📊 Original: {stats['original_periods']:,} Zeitschritte")
            self.logger.info(f"   📊 Reduziert auf: {stats['final_periods']:,} Zeitschritte")
            self.logger.info(f"   📊 Zeitersparnis: {stats['time_savings']}")
            self.logger.info(f"   📊 Reduktionsfaktor: {stats['reduction_factor']:.3f}")
            
            # Strategie-spezifische Details
            if stats['strategy'] == 'averaging':
                self.logger.info(f"   📊 Mittelwertbildung: {stats.get('averaging_hours', 'N/A')} Stunden")
            elif stats['strategy'] == 'sampling_24n':
                self.logger.info(f"   📊 Sampling n-Faktor: {stats.get('n_factor', 'N/A')}")
                self.logger.info(f"   📊 Sampling-Muster: {stats.get('sampling_pattern', 'N/A')}")
            elif stats['strategy'] == 'time_range':
                self.logger.info(f"   📊 Zeitbereich: {stats.get('selected_range', 'N/A')}")
            
            # Solver-Zeit-Schätzung
            if 'solver_time_estimate' in excel_data:
                time_est = excel_data['solver_time_estimate']
                self.logger.info(f"   ⚡ Geschätzte Solver-Zeitersparnis: {time_est.get('estimated_time_savings', 'N/A')}")
                self.logger.info(f"   ⚡ Komplexitäts-Reduktion: {time_est.get('complexity_reduction', 'N/A')}")
        
        # Timestep-Visualisierungen
        if 'timestep_visualization_files' in excel_data:
            viz_files = excel_data['timestep_visualization_files']
            if viz_files:
                self.logger.info(f"   🎨 {len(viz_files)} Timestep-Visualisierungen erstellt in:")
                self.logger.info(f"      📁 {project_output_dir.relative_to(self.project_root)}")
                for viz_file in viz_files:
                    # Zeige nur den Dateinamen, nicht den vollständigen Pfad
                    file_path = Path(viz_file)
                    self.logger.info(f"      📊 {file_path.name}")
                    
                    # Prüfe ob die Datei wirklich im richtigen Verzeichnis ist
                    if not file_path.is_absolute():
                        file_path = project_output_dir / file_path.name
                    
                    if file_path.exists():
                        self.logger.debug(f"✅ Timestep-Visualisierung bestätigt: {file_path}")
                    else:
                        self.logger.warning(f"⚠️  Timestep-Visualisierung nicht gefunden: {file_path}")
    
    def setup_project_logging(self, output_dir: Path, project_name: str):
        """Richtet projektspezifisches Logging ein."""
        try:
            # File Handler für dieses Projekt
            log_file = output_dir / f"{project_name}.log"
            
            file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Zu allen Loggern hinzufügen
            loggers = [
                logging.getLogger('main'),
                logging.getLogger('modules.excel_reader'),
                logging.getLogger('modules.system_builder'),
                logging.getLogger('modules.optimizer'),
                logging.getLogger('modules.results_processor'),
                logging.getLogger('modules.visualizer'),
                logging.getLogger('modules.analyzer'),
                logging.getLogger('modules.timestep_manager'),  # NEU
                logging.getLogger('modules.timestep_visualizer')  # NEU
            ]
            
            for logger in loggers:
                # Entferne alte File Handler
                logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.FileHandler)]
                # Füge neuen hinzu
                logger.addHandler(file_handler)
                
        except Exception as e:
            self.logger.warning(f"Projekt-Logging konnte nicht eingerichtet werden: {e}")
    
    def create_project_summary(self, project_name: str, excel_data: Dict[str, Any],
                             energy_system: Any, optimization_model: Any, 
                             results: Dict[str, Any], output_dir: Path):
        """Erstellt eine Projekt-Zusammenfassung."""
        try:
            summary_file = output_dir / f"{project_name}_summary.txt"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"PROJEKT-ZUSAMMENFASSUNG: {project_name}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Erstellt: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Excel-Daten-Zusammenfassung
                f.write("EINGABEDATEN:\n")
                f.write("-" * 20 + "\n")
                summary = self.excel_reader.get_data_summary(excel_data)
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # Timestep-Management (falls angewendet)
                if 'timestep_reduction_stats' in excel_data:
                    f.write("TIMESTEP-MANAGEMENT:\n")
                    f.write("-" * 22 + "\n")
                    stats = excel_data['timestep_reduction_stats']
                    f.write(f"Strategie: {stats['strategy']}\n")
                    f.write(f"Original Zeitschritte: {stats['original_periods']:,}\n")
                    f.write(f"Reduziert auf: {stats['final_periods']:,}\n")
                    f.write(f"Zeitersparnis: {stats['time_savings']}\n")
                    f.write(f"Reduktionsfaktor: {stats['reduction_factor']:.3f}\n")
                    
                    if 'solver_time_estimate' in excel_data:
                        time_est = excel_data['solver_time_estimate']
                        f.write(f"Geschätzte Solver-Zeitersparnis: {time_est.get('estimated_time_savings', 'N/A')}\n")
                    f.write("\n")
                
                # System-Zusammenfassung
                f.write("ENERGIESYSTEM:\n")
                f.write("-" * 15 + "\n")
                system_summary = self.system_builder.get_system_summary(energy_system)
                for key, value in system_summary.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # Optimierungs-Zusammenfassung
                f.write("OPTIMIERUNG:\n")
                f.write("-" * 13 + "\n")
                opt_summary = self.optimizer.get_optimization_summary(optimization_model, results)
                for key, value in opt_summary.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # Dateien-Liste
                f.write("ERSTELLTE DATEIEN:\n")
                f.write("-" * 17 + "\n")
                
                output_files = list(output_dir.glob('*.*'))
                for output_file in sorted(output_files):
                    if output_file.name != summary_file.name:
                        f.write(f"• {output_file.name}\n")
            
            self.logger.info(f"💾 Projekt-Zusammenfassung gespeichert: {summary_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Projekt-Zusammenfassung konnte nicht erstellt werden: {e}")
    
    def configure_modules(self):
        """Konfiguriert Module-Einstellungen."""
        print("\n⚙️  MODUL-KONFIGURATION")
        print("-" * 40)
        print("1. Solver ändern")
        print("2. Visualisierungen ein/ausschalten")
        print("3. Analysen ein/ausschalten")
        print("4. Debug-Modus ein/ausschalten")
        print("5. Timestep-Management testen")  # NEU
        print("6. Zurück zum Hauptmenü")
        
        try:
            choice = input("\nOption auswählen (1-6): ").strip()
            
            if choice == "1":
                self.configure_solver()
            elif choice == "2":
                self.toggle_visualizations()
            elif choice == "3":
                self.toggle_analysis()
            elif choice == "4":
                self.toggle_debug_mode()
            elif choice == "5":
                self.test_timestep_management()  # NEU
            elif choice == "6":
                return
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def configure_solver(self):
        """Konfiguriert den Solver."""
        available_solvers = ['cbc', 'glpk', 'gurobi', 'cplex']
        
        print(f"\nAktueller Solver: {self.settings['solver']}")
        print("Verfügbare Solver:")
        for i, solver in enumerate(available_solvers, 1):
            print(f"  {i}. {solver}")
        
        try:
            choice = input("\nSolver auswählen (Nummer): ").strip()
            solver_idx = int(choice) - 1
            
            if 0 <= solver_idx < len(available_solvers):
                new_solver = available_solvers[solver_idx]
                self.settings['solver'] = new_solver
                self.optimizer.solver_name = new_solver
                print(f"✅ Solver geändert zu: {new_solver}")
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def toggle_visualizations(self):
        """Schaltet Visualisierungen ein/aus."""
        current = self.settings.get('create_visualizations', True)
        self.settings['create_visualizations'] = not current
        
        status = "aktiviert" if self.settings['create_visualizations'] else "deaktiviert"
        print(f"✅ Visualisierungen {status}")
    
    def toggle_analysis(self):
        """Schaltet vertiefende Analysen ein/aus."""
        current = self.settings.get('create_analysis', False)
        self.settings['create_analysis'] = not current
        
        status = "aktiviert" if self.settings['create_analysis'] else "deaktiviert"
        print(f"✅ Vertiefende Analysen {status}")
    
    def toggle_debug_mode(self):
        """Schaltet Debug-Modus ein/aus."""
        current = self.settings.get('debug_mode', False)
        self.settings['debug_mode'] = not current
        
        status = "aktiviert" if self.settings['debug_mode'] else "deaktiviert"
        print(f"✅ Debug-Modus {status}")
    
    def test_timestep_management(self):
        """Testet das Timestep-Management mit verschiedenen Strategien."""
        print("\n🕒 TIMESTEP-MANAGEMENT TEST")
        print("-" * 40)
        
        if not self.available_projects:
            print("❌ Keine Projekte zum Testen verfügbar.")
            return
        
        # Projekt auswählen
        print("Wählen Sie ein Projekt zum Testen:")
        project = self.show_project_menu()
        
        if not project:
            return
        
        print("\nWählen Sie eine Timestep-Strategie:")
        print("1. Full (keine Änderung)")
        print("2. Averaging (6-Stunden-Mittelwerte)")
        print("3. Time Range (nur Januar)")
        print("4. Sampling 24n (alle 4 Stunden)")
        
        try:
            choice = input("\nStrategie auswählen (1-4): ").strip()
            
            strategies = {
                "1": ("full", {}),
                "2": ("averaging", {"averaging_hours": 6}),
                "3": ("time_range", {"time_range_start": "2025-01-01 00:00", "time_range_end": "2025-01-31 23:00"}),
                "4": ("sampling_24n", {"sampling_n_factor": 4})
            }
            
            if choice in strategies:
                strategy, params = strategies[choice]
                self.run_timestep_test(project, strategy, params)
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def run_timestep_test(self, project: Dict[str, Any], strategy: str, params: Dict[str, Any]):
        """Führt einen Timestep-Management-Test durch."""
        print(f"\n🧪 Teste Strategie: {strategy}")
        print(f"Parameter: {params}")
        
        try:
            # Excel-Daten laden
            excel_data = self.excel_reader.read_project_file(project['file'])
            
            print(f"Original: {len(excel_data.get('timeindex', []))} Zeitschritte")
            
            # Timestep-Manager simulieren
            from modules.timestep_manager import TimestepManager
            
            timestep_manager = TimestepManager(self.settings)
            processed_data = timestep_manager.process_timeindex_and_data(
                excel_data, strategy, params
            )
            
            stats = timestep_manager.get_reduction_stats()
            
            print(f"Nach {strategy}: {stats['final_periods']} Zeitschritte")
            print(f"Reduktion: {stats['time_savings']}")
            print(f"Faktor: {stats['reduction_factor']:.3f}")
            
            if 'solver_time_estimate' in processed_data:
                time_est = processed_data['solver_time_estimate']
                print(f"Geschätzte Solver-Zeitersparnis: {time_est.get('estimated_time_savings', 'N/A')}")
            
            print("✅ Test erfolgreich!")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
    
    def create_example_project(self):
        """Erstellt ein neues Beispielprojekt."""
        print("\n📁 NEUES BEISPIELPROJEKT ERSTELLEN")
        print("-" * 40)
        print("Diese Funktion würde ein neues Excel-Template erstellen.")
        print("Verwenden Sie den excel_template_creator.py für detaillierte Vorlagen.")
        
        # Hier könnte der Template-Creator integriert werden
        try:
            from excel_template_creator import create_test_excel_with_timestep_management
            
            project_name = input("Projektname eingeben: ").strip()
            if not project_name:
                print("❌ Kein Projektname eingegeben.")
                return
            
            output_file = self.directories['examples'] / f"{project_name}.xlsx"
            
            if output_file.exists():
                overwrite = input(f"Datei existiert bereits. Überschreiben? (j/n): ").strip().lower()
                if overwrite not in ['j', 'ja', 'y', 'yes']:
                    print("❌ Abgebrochen.")
                    return
            
            create_test_excel_with_timestep_management(output_file)
            print(f"✅ Beispielprojekt erstellt: {output_file}")
            
            # Projekte neu laden
            self.load_available_projects()
            
        except ImportError:
            print("❌ excel_template_creator.py nicht verfügbar.")
        except Exception as e:
            print(f"❌ Fehler beim Erstellen: {e}")
    
    def setup_project_structure_interactive(self):
        """Richtet die Projektstruktur interaktiv ein."""
        print("\n🔧 PROJEKTSTRUKTUR EINRICHTEN")
        print("-" * 40)
        
        print("Erstelle erforderliche Verzeichnisse...")
        
        for name, path in self.directories.items():
            if path.exists():
                print(f"✅ {name}: {path} (bereits vorhanden)")
            else:
                path.mkdir(parents=True, exist_ok=True)
                print(f"📁 {name}: {path} (erstellt)")
        
        print("\n✅ Projektstruktur eingerichtet!")
        
        # Prüfe auf fehlende Module
        print("\nPrüfe Module...")
        missing_modules = []
        
        for module_name in ['excel_reader', 'system_builder', 'optimizer', 
                           'results_processor', 'visualizer', 'analyzer',
                           'timestep_manager', 'timestep_visualizer']:
            module_file = self.directories['modules'] / f"{module_name}.py"
            if module_file.exists():
                print(f"✅ {module_name}.py")
            else:
                print(f"❌ {module_name}.py (fehlt)")
                missing_modules.append(module_name)
        
        if missing_modules:
            print(f"\n⚠️  Fehlende Module: {', '.join(missing_modules)}")
            print("Stellen Sie sicher, dass alle Module im 'modules/' Verzeichnis vorhanden sind.")
        else:
            print("\n✅ Alle Module verfügbar!")
    
    def show_project_info(self):
        """Zeigt Projektinformationen an."""
        print("\nℹ️  PROJEKTINFORMATIONEN")
        print("-" * 40)
        print(f"🏠 Projekt-Verzeichnis: {self.project_root}")
        print(f"📂 Verfügbare Projekte: {len(self.available_projects)}")
        print(f"⚙️  Aktueller Solver: {self.settings['solver']}")
        print(f"🎨 Visualisierungen: {'✅' if self.settings.get('create_visualizations') else '❌'}")
        print(f"🔍 Analysen: {'✅' if self.settings.get('create_analysis') else '❌'}")
        print(f"🐛 Debug-Modus: {'✅' if self.settings.get('debug_mode') else '❌'}")
        
        print(f"\n📁 Verzeichnisse:")
        for name, path in self.directories.items():
            status = "✅" if path.exists() else "❌"
            print(f"   {status} {name}: {path}")
        
        print(f"\n🔧 Module:")
        for name, module in self.modules.items():
            status = "✅" if module else "❌"
            print(f"   {status} {name}")
        
        if self.available_projects:
            print(f"\n📋 Verfügbare Projekte:")
            for project in self.available_projects:
                print(f"   📄 {project['name']} ({project['file'].name})")
        else:
            print(f"\n📋 Keine Projekte verfügbar")
            print("   Erstellen Sie ein Beispielprojekt mit Option 3")
        
        # Timestep-Management Info
        print(f"\n🕒 Timestep-Management Features:")
        try:
            from modules.timestep_manager import TimestepManager
            print("   ✅ TimestepManager verfügbar")
        except ImportError:
            print("   ❌ TimestepManager nicht verfügbar")
        
        try:
            from modules.timestep_visualizer import TimestepVisualizer
            print("   ✅ TimestepVisualizer verfügbar")
        except ImportError:
            print("   ❌ TimestepVisualizer nicht verfügbar")
        
        print(f"\n📊 Unterstützte Timestep-Strategien:")
        print("   • full - Vollständige Zeitauflösung")
        print("   • averaging - Mittelwertbildung über Stunden")
        print("   • time_range - Auswahl eines Zeitbereichs")
        print("   • sampling_24n - Regelmäßiges Sampling")
    
    def run(self):
        """Startet das Hauptprogramm."""
        print("🚀 oemof.solph 0.6.0 Energiesystem-Optimierer")
        print("=" * 60)
        print("Mit integriertem Timestep-Management und Visualisierung")
        print("=" * 60)
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "1":
                    # Projekt ausführen
                    project = self.show_project_menu()
                    if project:
                        self.run_project(project)
                        
                elif choice == "2":
                    # Module konfigurieren
                    self.configure_modules()
                    
                elif choice == "3":
                    # Neues Beispielprojekt erstellen
                    self.create_example_project()
                    
                elif choice == "4":
                    # Projektstruktur einrichten
                    self.setup_project_structure_interactive()
                    
                elif choice == "5":
                    # Projektinformationen anzeigen
                    self.show_project_info()
                    
                elif choice == "6":
                    # Timestep-Management testen
                    self.test_timestep_management()
                    
                elif choice == "7":
                    # Beenden
                    print("\n👋 Auf Wiedersehen!")
                    break
                    
                else:
                    print("❌ Ungültige Auswahl. Bitte wählen Sie 1-7.")
                
                # Pause vor nächster Menü-Anzeige
                if choice in ["1", "3", "4", "5", "6"]:
                    input("\n" + "="*50 + "\n\n⏸️  Drücken Sie Enter zum Fortfahren...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Programm beendet.")
                break
            except Exception as e:
                print(f"\n❌ Unerwarteter Fehler: {e}")
                if self.settings.get('debug_mode', False):
                    import traceback
                    traceback.print_exc()
                
                input("\n⏸️  Drücken Sie Enter zum Fortfahren...")


def main():
    """Haupteinstiegspunkt."""
    try:
        # Energiesystem-Optimierer erstellen und starten
        optimizer = EnergySystemOptimizer()
        optimizer.run()
        
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Programmstart: {e}")
        import traceback
        traceback.print_exc()
        input("\n⏸️  Drücken Sie Enter zum Beenden...")


if __name__ == "__main__":
    main()