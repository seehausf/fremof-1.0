#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Interaktives Hauptprogramm
=============================================

Benutzerfreundliches Interface für die Energiesystemmodellierung
mit interaktiver Projektverwaltung und Modulkonfiguration.

Erweitert um System-Export-Konfiguration.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.1.0 (mit System Export)
"""

import sys
import time
import logging
import tempfile
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
    from main import main_program
except ImportError as e:
    print(f"❌ Fehler beim Importieren der Module: {e}")
    print("Stellen Sie sicher, dass alle Module im 'modules/' Verzeichnis vorhanden sind.")
    sys.exit(1)


class ProjectRunner:
    """Interaktive Projektverwaltung und -ausführung."""
    
    def __init__(self):
        """Initialisiert den Project Runner."""
        # Projektstruktur einrichten
        self.setup_project_structure()
        
        # Logging einrichten
        self.setup_logging()
        
        # Standard-Einstellungen
        self.initialize_settings()
        
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
        """Richtet das Logging-System ein - oemof.solph 0.6.0 kompatibel."""
        # FIX: Root-Logger NIEMALS auf DEBUG wegen oemof.solph Performance-Problem
        logging.getLogger().setLevel(logging.INFO)
        
        self.logger = logging.getLogger('runme')
        self.logger.setLevel(logging.INFO)
        
        # Console Handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def initialize_settings(self):
        """Initialisiert die Standard-Einstellungen."""
        # Module-Konfiguration
        self.modules = {
            'excel_reader': True,
            'system_builder': True,
            'optimizer': True,
            'results_processor': True,
            'visualizer': False,
            'analyzer': False,
            'system_exporter': False  # NEU: Standardmäßig deaktiviert
        }
        
        # System-Einstellungen
        self.settings = {
            'solver': 'cbc',
            'debug_mode': False,  # FIX: Standardmäßig FALSE wegen oemof.solph Logging-Problem
            'output_format': 'xlsx',
            'create_visualizations': True,
            'create_analysis': False,
            'save_model': False,
            'project_root': self.project_root,
            'output_dir': self.directories['output'],
            # NEU: Export-Einstellungen
            'export_formats': ['json', 'yaml', 'txt']
        }
    
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
        print("6. 🧪 Test-Funktionen")
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
        """Führt ein Projekt durch."""
        project_name = project['name']
        project_file = project['file']
        
        print(f"🚀 Starte Projekt: {project_file.name}")
        self.logger.info(f"🚀 Starte Projekt: {project_name}")
        
        # Konfiguration für dieses Projekt zusammenstellen
        config = {
            'modules': self.modules.copy(),
            'settings': self.settings.copy()
        }
        
        try:
            # Projekt ausführen
            success = main_program(project_file, config)
            
            if success:
                print(f"\n✅ Projekt '{project_name}' erfolgreich abgeschlossen!")
                
                # Output-Verzeichnis anzeigen
                output_dir = Path("data/output") / project_name
                if output_dir.exists():
                    output_files = list(output_dir.glob("*"))
                    print(f"📁 {len(output_files)} Dateien erstellt in: {output_dir}")
                    
                    # System-Export-Dateien hervorheben
                    export_dir = output_dir / "system_exports"
                    if export_dir.exists():
                        export_files = list(export_dir.glob("*"))
                        if export_files:
                            print(f"📤 {len(export_files)} System-Export-Dateien:")
                            for export_file in export_files:
                                print(f"   • {export_file.name}")
            else:
                print(f"\n❌ Projekt '{project_name}' fehlgeschlagen!")
                
        except Exception as e:
            print(f"\n❌ Fehler bei der Projektausführung: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
    
    def configure_modules(self):
        """Konfiguriert Module-Einstellungen."""
        print("\n⚙️  MODUL-KONFIGURATION")
        print("-" * 40)
        print("1. Solver ändern")
        print("2. Visualisierungen ein/ausschalten")
        print("3. Analysen ein/ausschalten")
        print("4. System-Export konfigurieren")  # NEU
        print("5. Debug-Modus ein/ausschalten")
        print("6. Output-Format ändern")
        print("7. Zurück zum Hauptmenü")
        
        try:
            choice = input("\nOption auswählen (1-7): ").strip()
            
            if choice == "1":
                self.configure_solver()
            elif choice == "2":
                self.toggle_visualizations()
            elif choice == "3":
                self.toggle_analysis()
            elif choice == "4":
                self.configure_system_export()  # NEU
            elif choice == "5":
                self.toggle_debug_mode()
            elif choice == "6":
                self.configure_output_format()
            elif choice == "7":
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
                print(f"✅ Solver geändert zu: {new_solver}")
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def toggle_visualizations(self):
        """Schaltet Visualisierungen ein/aus."""
        current = self.modules.get('visualizer', False)
        self.modules['visualizer'] = not current
        
        status = "aktiviert" if self.modules['visualizer'] else "deaktiviert"
        print(f"✅ Visualisierungen {status}")
    
    def toggle_analysis(self):
        """Schaltet vertiefende Analysen ein/aus."""
        current = self.modules.get('analyzer', False)
        self.modules['analyzer'] = not current
        
        status = "aktiviert" if self.modules['analyzer'] else "deaktiviert"
        print(f"✅ Analysen {status}")
    
    def configure_system_export(self):
        """Konfiguriert System-Export-Einstellungen - NEU."""
        print(f"\n📤 SYSTEM-EXPORT KONFIGURATION")
        print("-" * 40)
        
        current_status = self.modules.get('system_exporter', False)
        print(f"Aktueller Status: {'Aktiviert' if current_status else 'Deaktiviert'}")
        
        if current_status:
            current_formats = self.settings.get('export_formats', ['json', 'yaml', 'txt'])
            print(f"Aktuelle Formate: {', '.join(current_formats)}")
        
        print("\n1. System-Export aktivieren/deaktivieren")
        print("2. Export-Formate konfigurieren")
        print("3. Zurück")
        
        try:
            choice = input("\nOption auswählen (1-3): ").strip()
            
            if choice == "1":
                self.toggle_system_export()
            elif choice == "2":
                self.configure_export_formats()
            elif choice == "3":
                return
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def toggle_system_export(self):
        """Schaltet System-Export ein/aus - NEU."""
        current = self.modules.get('system_exporter', False)
        self.modules['system_exporter'] = not current
        
        status = "aktiviert" if self.modules['system_exporter'] else "deaktiviert"
        print(f"✅ System-Export {status}")
        
        if self.modules['system_exporter']:
            print("💡 System-Export erstellt computer- und menschenlesbare Dateien")
            print("   mit allen Energiesystem-Parametern vor der Optimierung.")
    
    def configure_export_formats(self):
        """Konfiguriert gewünschte Export-Formate - NEU."""
        available_formats = ['json', 'yaml', 'txt']
        current_formats = self.settings.get('export_formats', ['json', 'yaml', 'txt'])
        
        print("\nVerfügbare Export-Formate:")
        for i, fmt in enumerate(available_formats, 1):
            status = "✓" if fmt in current_formats else " "
            description = {
                'json': 'Computer-lesbar, ideal für weitere Verarbeitung',
                'yaml': 'Computer- und menschenlesbar, strukturiert',
                'txt': 'Rein menschenlesbar, übersichtlich formatiert'
            }[fmt]
            print(f"  {i}. [{status}] {fmt.upper()} - {description}")
        
        print(f"\nAktuell gewählt: {', '.join(current_formats)}")
        print("Geben Sie die Nummern der gewünschten Formate ein (z.B. 1,3)")
        print("Oder drücken Sie Enter um aktuelle Auswahl zu behalten:")
        
        try:
            user_input = input("Auswahl: ").strip()
            
            # Wenn leer, aktuelle Einstellung beibehalten
            if not user_input:
                print("✅ Aktuelle Format-Auswahl beibehalten.")
                return
            
            choices = user_input.split(',')
            selected_formats = []
            
            for choice in choices:
                try:
                    idx = int(choice.strip()) - 1
                    if 0 <= idx < len(available_formats):
                        selected_formats.append(available_formats[idx])
                    else:
                        print(f"⚠️  Ungültige Auswahl ignoriert: {choice}")
                except ValueError:
                    print(f"⚠️  Ungültige Eingabe ignoriert: {choice}")
            
            if selected_formats:
                self.settings['export_formats'] = selected_formats
                print(f"✅ Export-Formate konfiguriert: {', '.join(selected_formats)}")
            else:
                print("❌ Keine gültigen Formate ausgewählt. Aktuelle Einstellung beibehalten.")
                
        except KeyboardInterrupt:
            print("\n❌ Abgebrochen.")
    
    def toggle_debug_mode(self):
        """Schaltet Debug-Modus ein/aus - mit oemof.solph Warnung."""
        current = self.settings.get('debug_mode', False)
        
        if not current:
            # Debug-Modus aktivieren - Warnung anzeigen
            print("\n⚠️  WARNUNG: Debug-Modus und oemof.solph 0.6.0")
            print("-" * 50)
            print("Der Debug-Modus kann die Optimierung um Faktor ~100 verlangsamen")
            print("aufgrund eines bekannten Problems zwischen oemof.solph und Pyomo.")
            print("Verwenden Sie Debug-Modus nur für kleine Testmodelle!")
            print("\nMöchten Sie den Debug-Modus trotzdem aktivieren?")
            
            confirm = input("Debug-Modus aktivieren? (j/n): ").strip().lower()
            if confirm in ['j', 'ja', 'y', 'yes']:
                self.settings['debug_mode'] = True
                print("✅ Debug-Modus aktiviert (Vorsicht bei großen Modellen!)")
            else:
                print("❌ Debug-Modus bleibt deaktiviert.")
        else:
            # Debug-Modus deaktivieren
            self.settings['debug_mode'] = False
            print("✅ Debug-Modus deaktiviert (empfohlen für oemof.solph 0.6.0)")
    
    
    def configure_output_format(self):
        """Konfiguriert das Output-Format."""
        available_formats = ['xlsx', 'csv', 'json']
        
        print(f"\nAktuelles Output-Format: {self.settings['output_format']}")
        print("Verfügbare Formate:")
        for i, fmt in enumerate(available_formats, 1):
            print(f"  {i}. {fmt}")
        
        try:
            choice = input("\nFormat auswählen (Nummer): ").strip()
            format_idx = int(choice) - 1
            
            if 0 <= format_idx < len(available_formats):
                new_format = available_formats[format_idx]
                self.settings['output_format'] = new_format
                print(f"✅ Output-Format geändert zu: {new_format}")
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def create_new_project(self):
        """Erstellt ein neues Beispielprojekt."""
        print("\n📁 NEUES BEISPIELPROJEKT ERSTELLEN")
        print("-" * 40)
        
        try:
            from examples.excel_template_creator import create_test_excel_with_timestep_management
            
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
        
        required_modules = [
            'excel_reader', 'system_builder', 'optimizer', 
            'results_processor', 'visualizer', 'analyzer',
            'energy_system_exporter'  # NEU
        ]
        
        for module_name in required_modules:
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
        print("\n ℹ️  PROJEKTINFORMATIONEN")
        print("-" * 40)
        
        print(f"📁 Projektverzeichnis: {self.project_root}")
        print(f"📊 Verfügbare Projekte: {len(self.available_projects)}")
        
        # Module-Status
        print("\n🔧 MODUL-STATUS:")
        for module, active in self.modules.items():
            status = "✅ Aktiviert" if active else "❌ Deaktiviert"
            if module == 'system_exporter' and active:
                formats = ', '.join(self.settings.get('export_formats', []))
                status += f" ({formats})"
            print(f"   {module}: {status}")
        
        # Einstellungen
        print("\n⚙️  AKTUELLE EINSTELLUNGEN:")
        for key, value in self.settings.items():
            if key not in ['project_root', 'output_dir']:  # Pfade ausblenden
                print(f"   {key}: {value}")
        
        # Verzeichnisse
        print("\n📂 VERZEICHNISSE:")
        for name, path in self.directories.items():
            exists = "✅" if path.exists() else "❌"
            print(f"   {name}: {exists} {path}")
        
        # Verfügbare Projekte
        if self.available_projects:
            print(f"\n📋 VERFÜGBARE PROJEKTE ({len(self.available_projects)}):")
            for project in self.available_projects:
                print(f"   • {project['name']}")
        else:
            print("\n📋 Keine Projekte gefunden")
    
    def test_functions(self):
        """Zeigt Test-Funktionen an."""
        print("\n🧪 TEST-FUNKTIONEN")
        print("-" * 40)
        print("1. System-Export testen")
        print("2. Module-Import testen")
        print("3. Beispiel-Projekt validieren")
        print("4. Zurück")
        
        try:
            choice = input("\nOption auswählen (1-4): ").strip()
            
            if choice == "1":
                self.test_system_export()
            elif choice == "2":
                self.test_module_imports()
            elif choice == "3":
                self.test_example_project()
            elif choice == "4":
                return
            else:
                print("❌ Ungültige Auswahl.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
    
    def test_system_export(self):
        """Testet das System-Export-Modul."""
        print("\n🧪 SYSTEM-EXPORT TEST")
        print("-" * 30)
        
        try:
            # Export-Modul importieren und testen
            from modules.energy_system_exporter import create_export_module, test_export_module
            
            print("1. Modul-Import... ", end="")
            exporter = create_export_module({'debug_mode': True})
            print("✅")
            
            print("2. Metadaten-Erstellung... ", end="")
            metadata = exporter.export_metadata
            print("✅")
            print(f"   Version: {metadata['exporter_version']}")
            print(f"   Timestamp: {metadata['export_timestamp']}")
            
            print("3. Test-Funktion ausführen...")
            test_export_module()
            
            print("\n✅ System-Export-Test erfolgreich!")
            
        except ImportError as e:
            print(f"❌ Import-Fehler: {e}")
            print("   Das energy_system_exporter Modul ist nicht verfügbar.")
        except Exception as e:
            print(f"❌ Test-Fehler: {e}")
    
    def test_module_imports(self):
        """Testet alle Modul-Imports."""
        print("\n🧪 MODUL-IMPORT TEST")
        print("-" * 30)
        
        modules_to_test = [
            ('excel_reader', 'ExcelReader'),
            ('system_builder', 'SystemBuilder'),
            ('optimizer', 'Optimizer'),
            ('results_processor', 'ResultsProcessor'),
            ('visualizer', 'Visualizer'),
            ('analyzer', 'Analyzer'),
            ('energy_system_exporter', 'create_export_module')
        ]
        
        successful_imports = 0
        
        for module_name, class_name in modules_to_test:
            try:
                print(f"Teste {module_name}... ", end="")
                module = __import__(f'modules.{module_name}', fromlist=[class_name])
                getattr(module, class_name)
                print("✅")
                successful_imports += 1
            except ImportError as e:
                print(f"❌ Import-Fehler: {e}")
            except AttributeError as e:
                print(f"❌ Attribut-Fehler: {e}")
            except Exception as e:
                print(f"❌ Unbekannter Fehler: {e}")
        
        print(f"\n📊 Ergebnis: {successful_imports}/{len(modules_to_test)} Module erfolgreich importiert")
        
        if successful_imports == len(modules_to_test):
            print("✅ Alle Module verfügbar!")
        else:
            print("⚠️  Einige Module fehlen oder haben Probleme.")
    
    def test_example_project(self):
        """Testet ein Beispiel-Projekt."""
        print("\n🧪 BEISPIEL-PROJEKT TEST")
        print("-" * 30)
        
        if not self.available_projects:
            print("❌ Keine Beispiel-Projekte verfügbar.")
            print("Erstellen Sie zunächst ein Projekt (Hauptmenü → Option 3).")
            return
        
        # Erstes verfügbares Projekt wählen
        test_project = self.available_projects[0]
        print(f"Teste Projekt: {test_project['name']}")
        
        try:
            # Nur Excel-Reader und System-Builder testen (ohne Optimierung)
            test_config = {
                'modules': {
                    'excel_reader': True,
                    'system_builder': True,
                    'optimizer': False,
                    'results_processor': False,
                    'visualizer': False,
                    'analyzer': False,
                    'system_exporter': self.modules.get('system_exporter', False)
                },
                'settings': self.settings.copy()
            }
            
            print("\n1. Excel-Daten einlesen...")
            excel_reader = ExcelReader(test_config['settings'])
            excel_data = excel_reader.process_excel_data(test_project['file'])
            print("✅ Excel-Daten erfolgreich eingelesen")
            
            print("2. Energiesystem aufbauen...")
            system_builder = SystemBuilder(test_config['settings'])
            energy_system = system_builder.build_energy_system(excel_data)
            print("✅ Energiesystem erfolgreich aufgebaut")
            
            # System-Zusammenfassung
            summary = system_builder.get_system_summary(energy_system)
            print("\n📊 SYSTEM-ZUSAMMENFASSUNG:")
            for key, value in summary.items():
                print(f"   {key}: {value}")
            
            # Optional: System-Export testen
            if test_config['modules']['system_exporter']:
                print("\n3. System-Export testen...")
                from modules.energy_system_exporter import create_export_module
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    exporter = create_export_module(test_config['settings'])
                    export_files = exporter.export_system(
                        energy_system=energy_system,
                        excel_data=excel_data,
                        output_dir=Path(temp_dir),
                        formats=['json', 'txt']
                    )
                    print(f"✅ System-Export erfolgreich ({len(export_files)} Dateien)")
                    for fmt, filepath in export_files.items():
                        print(f"   • {fmt.upper()}: {filepath.name}")
            
            print("\n✅ Beispiel-Projekt Test erfolgreich!")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
    
    def run(self):
        """Hauptschleife des Programms."""
        print("🚀 oemof.solph 0.6.0 Energiesystem-Optimierung")
        print("=" * 60)
        print("Interaktives Hauptprogramm mit System-Export")
        print(f"Projektverzeichnis: {self.project_root}")
        print(f"Verfügbare Projekte: {len(self.available_projects)}")
        
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
                    # Neues Projekt erstellen
                    self.create_new_project()
                
                elif choice == "4":
                    # Projektstruktur einrichten
                    self.setup_project_structure_interactive()
                
                elif choice == "5":
                    # Projektinformationen anzeigen
                    self.show_project_info()
                
                elif choice == "6":
                    # Test-Funktionen
                    self.test_functions()
                
                elif choice == "7":
                    # Beenden
                    print("👋 Auf Wiedersehen!")
                    break
                
                else:
                    print("❌ Ungültige Auswahl. Bitte wählen Sie 1-7.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Programm beendet.")
                break
            except Exception as e:
                print(f"\n❌ Unerwarteter Fehler: {e}")
                if self.settings.get('debug_mode', False):
                    import traceback
                    traceback.print_exc()


def main():
    """Hauptfunktion."""
    try:
        runner = ProjectRunner()
        runner.run()
    except KeyboardInterrupt:
        print("\n👋 Programm beendet.")
    except Exception as e:
        print(f"❌ Schwerwiegender Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
