#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Energiesystem-Optimierung - Interaktives Hauptprogramm
======================================================================

Refactored main runner mit modularer Architektur.
Verwendet das neue Menu-System, Project-Selector und Configuration-Manager.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.0.0 (Refactored)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Neue modulare Komponenten
from ui.menu_system import MenuSystem
from ui.project_selector import ProjectSelector
from config.config_manager import ConfigManager
from utils.file_utils import FileUtils

# Importiere die main-Funktion aus dem ursprünglichen main.py
try:
    from main import main_program
except ImportError as e:
    print(f"❌ Fehler beim Importieren von main.py: {e}")
    print("Stellen Sie sicher, dass main.py im selben Verzeichnis vorhanden ist.")
    sys.exit(1)


class ProjectRunner:
    """
    Hauptklasse für das interaktive Programm.
    Orchestriert die verschiedenen Komponenten.
    """
    
    def __init__(self):
        """Initialisiert den Project Runner."""
        self.setup_logging()
        
        # Projekt-Grundkonfiguration
        self.project_root = Path.cwd()
        self.logger = logging.getLogger(__name__)
        
        # Komponenten initialisieren
        self.file_utils = FileUtils()
        self.config_manager = ConfigManager(self.project_root)
        self.menu_system = MenuSystem()
        
        # Verzeichnisse erstellen
        self.directories = self.setup_directories()
        
        # Project Selector initialisieren
        self.project_selector = ProjectSelector(self.directories['examples'])
        
        # Menu-Handler registrieren
        self.register_menu_handlers()
        
        self.logger.info("ProjectRunner initialisiert")
    
    def setup_logging(self):
        """Konfiguriert das Logging-System."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # oemof.solph Logging-Problem umgehen
        logging.getLogger('oemof.solph').setLevel(logging.WARNING)
        logging.getLogger('oemof.network').setLevel(logging.WARNING)
        logging.getLogger('pyomo').setLevel(logging.WARNING)
    
    def setup_directories(self) -> Dict[str, Path]:
        """
        Richtet die Verzeichnisstruktur ein.
        
        Returns:
            Dictionary mit Verzeichnis-Pfaden
        """
        directory_config = self.config_manager.get_directories()
        
        # Pfade als Path-Objekte konvertieren
        directories = {}
        for name, path_str in directory_config.items():
            directories[name] = self.project_root / path_str
        
        # Verzeichnisse erstellen
        return self.file_utils.ensure_directory_structure(directories)
    
    def register_menu_handlers(self):
        """Registriert die Handler für das Menü-System."""
        self.menu_system.set_handler("1", self.handle_run_project)
        self.menu_system.set_handler("2", self.handle_configure_modules)
        self.menu_system.set_handler("3", self.handle_create_project)
        self.menu_system.set_handler("4", self.handle_setup_structure)
        self.menu_system.set_handler("5", self.handle_show_project_info)
        self.menu_system.set_handler("6", self.handle_test_functions)
    
    def handle_run_project(self):
        """Handler für Projekt-Ausführung."""
        project = self.project_selector.show_project_menu()
        
        if project:
            self.run_project(project)
    
    def handle_configure_modules(self):
        """Handler für Modul-Konfiguration."""
        self.configure_modules()
    
    def handle_create_project(self):
        """Handler für Projekt-Erstellung."""
        self.create_new_project()
    
    def handle_setup_structure(self):
        """Handler für Struktur-Setup."""
        self.setup_project_structure_interactive()
    
    def handle_show_project_info(self):
        """Handler für Projekt-Informationen."""
        self.show_project_info()
    
    def handle_test_functions(self):
        """Handler für Test-Funktionen."""
        self.test_functions()
    
    def run_project(self, project: Dict[str, Any]):
        """
        Führt ein Projekt durch.
        
        Args:
            project: Projekt-Informationen
        """
        project_name = project['name']
        project_file = project['file']
        
        # Projekt validieren
        if not self.project_selector.validate_project(project):
            self.menu_system.show_error("Projekt-Validierung fehlgeschlagen")
            return
        
        self.menu_system.show_info(f"Starte Projekt: {project_file.name}")
        self.logger.info(f"Starte Projekt: {project_name}")
        
        # Konfiguration zusammenstellen
        config = {
            'modules': self.config_manager.get_module_config(),
            'settings': self.config_manager.get_settings()
        }
        
        try:
            # Projekt ausführen
            success = main_program(project_file, config)
            
            if success:
                self.menu_system.show_success(f"Projekt '{project_name}' erfolgreich abgeschlossen!")
                self.show_output_summary(project_name)
            else:
                self.menu_system.show_error(f"Projekt '{project_name}' fehlgeschlagen!")
                
        except Exception as e:
            self.menu_system.show_error(f"Fehler bei der Projektausführung: {e}")
            if self.config_manager.get_setting('debug_mode', False):
                import traceback
                traceback.print_exc()
    
    def show_output_summary(self, project_name: str):
        """
        Zeigt eine Zusammenfassung der Output-Dateien.
        
        Args:
            project_name: Name des Projekts
        """
        output_dir = self.directories['output'] / project_name
        
        if not output_dir.exists():
            return
        
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
    
    def configure_modules(self):
        """Konfiguriert Module-Einstellungen."""
        while True:
            print("\n⚙️ MODUL-KONFIGURATION")
            print("-" * 40)
            
            # Aktuelle Modul-Konfiguration anzeigen
            modules = self.config_manager.get_module_config()
            for i, (module_name, enabled) in enumerate(modules.items(), 1):
                status = "✓" if enabled else "✗"
                print(f" {i}. {status} {module_name}")
            
            print(f" {len(modules) + 1}. 🔧 Erweiterte Einstellungen")
            print(f" {len(modules) + 2}. 💾 Konfiguration speichern")
            print(f" {len(modules) + 3}. ↩️ Zurück zum Hauptmenü")
            
            choice = input("\nOption auswählen: ").strip()
            
            try:
                choice_num = int(choice)
                module_names = list(modules.keys())
                
                if 1 <= choice_num <= len(modules):
                    # Modul umschalten
                    module_name = module_names[choice_num - 1]
                    current_state = modules[module_name]
                    new_state = not current_state
                    
                    self.config_manager.set_module_enabled(module_name, new_state)
                    
                    status = "aktiviert" if new_state else "deaktiviert"
                    self.menu_system.show_success(f"Modul '{module_name}' {status}")
                
                elif choice_num == len(modules) + 1:
                    # Erweiterte Einstellungen
                    self.configure_advanced_settings()
                
                elif choice_num == len(modules) + 2:
                    # Konfiguration speichern
                    if self.config_manager.save_config():
                        self.menu_system.show_success("Konfiguration gespeichert")
                    else:
                        self.menu_system.show_error("Fehler beim Speichern der Konfiguration")
                
                elif choice_num == len(modules) + 3:
                    # Zurück
                    break
                
                else:
                    self.menu_system.show_error("Ungültige Auswahl")
                    
            except ValueError:
                self.menu_system.show_error("Ungültige Eingabe")
            except KeyboardInterrupt:
                break
    
    def configure_advanced_settings(self):
        """Konfiguriert erweiterte Einstellungen."""
        while True:
            print("\n🔧 ERWEITERTE EINSTELLUNGEN")
            print("-" * 40)
            
            settings = self.config_manager.get_settings()
            
            print("1. 🔨 Solver-Einstellungen")
            print("2. 🐛 Debug-Modus")
            print("3. 📊 Visualisierung")
            print("4. 📤 Export-Formate")
            print("5. 🕒 Timestep-Einstellungen")
            print("6. 📋 Konfiguration anzeigen")
            print("7. 🔄 Auf Standards zurücksetzen")
            print("8. ↩️ Zurück")
            
            choice = input("\nOption auswählen: ").strip()
            
            if choice == "1":
                self.configure_solver_settings()
            elif choice == "2":
                self.configure_debug_mode()
            elif choice == "3":
                self.configure_visualization()
            elif choice == "4":
                self.configure_export_formats()
            elif choice == "5":
                self.configure_timestep_settings()
            elif choice == "6":
                self.config_manager.show_config_summary()
            elif choice == "7":
                if self.menu_system.show_confirmation("Konfiguration wirklich zurücksetzen?"):
                    self.config_manager.reset_to_defaults()
                    self.menu_system.show_success("Konfiguration zurückgesetzt")
            elif choice == "8":
                break
            else:
                self.menu_system.show_error("Ungültige Auswahl")
    
    def configure_solver_settings(self):
        """Konfiguriert Solver-Einstellungen."""
        current_solver = self.config_manager.get_setting('solver', 'cbc')
        
        solver_options = {
            "1": "cbc",
            "2": "glpk", 
            "3": "gurobi"
        }
        
        choice = self.menu_system.show_submenu(
            "🔨 SOLVER AUSWÄHLEN",
            {k: f"{v} {'(aktuell)' if v == current_solver else ''}" 
             for k, v in solver_options.items()},
            "Solver auswählen: "
        )
        
        if choice and choice in solver_options:
            new_solver = solver_options[choice]
            self.config_manager.set_setting('solver', new_solver)
            self.menu_system.show_success(f"Solver auf '{new_solver}' gesetzt")
    
    def configure_debug_mode(self):
        """Konfiguriert Debug-Modus."""
        current_debug = self.config_manager.get_setting('debug_mode', False)
        
        if self.menu_system.show_confirmation(
            f"Debug-Modus {'deaktivieren' if current_debug else 'aktivieren'}?",
            default=not current_debug
        ):
            self.config_manager.set_setting('debug_mode', not current_debug)
            status = "aktiviert" if not current_debug else "deaktiviert"
            self.menu_system.show_success(f"Debug-Modus {status}")
    
    def configure_visualization(self):
        """Konfiguriert Visualisierung."""
        current_viz = self.config_manager.get_setting('create_visualizations', True)
        
        if self.menu_system.show_confirmation(
            f"Visualisierungen {'deaktivieren' if current_viz else 'aktivieren'}?",
            default=not current_viz
        ):
            self.config_manager.set_setting('create_visualizations', not current_viz)
            status = "aktiviert" if not current_viz else "deaktiviert"
            self.menu_system.show_success(f"Visualisierungen {status}")
    
    def configure_export_formats(self):
        """Konfiguriert Export-Formate."""
        available_formats = ['json', 'yaml', 'txt']
        current_formats = self.config_manager.get_setting('export_formats', [])
        
        print("\n📤 EXPORT-FORMATE KONFIGURIEREN")
        print("-" * 40)
        
        for i, fmt in enumerate(available_formats, 1):
            status = "✓" if fmt in current_formats else "✗"
            print(f" {i}. {status} {fmt.upper()}")
        
        choice = input("\nFormat umschalten (Nummer): ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_formats):
                fmt = available_formats[choice_num - 1]
                
                if fmt in current_formats:
                    current_formats.remove(fmt)
                    self.menu_system.show_success(f"Format '{fmt}' deaktiviert")
                else:
                    current_formats.append(fmt)
                    self.menu_system.show_success(f"Format '{fmt}' aktiviert")
                
                self.config_manager.set_setting('export_formats', current_formats)
                
        except ValueError:
            self.menu_system.show_error("Ungültige Eingabe")
    
    def configure_timestep_settings(self):
        """Konfiguriert Timestep-Einstellungen."""
        timestep_settings = self.config_manager.get_timestep_settings()
        
        print("\n🕒 TIMESTEP-EINSTELLUNGEN")
        print("-" * 40)
        
        for key, value in timestep_settings.items():
            print(f"{key}: {value}")
        
        # Hier könnte eine erweiterte Konfiguration implementiert werden
        self.menu_system.show_info("Timestep-Einstellungen werden über Excel-Dateien konfiguriert")
    
    def create_new_project(self):
        """Erstellt ein neues Beispielprojekt."""
        project_name = self.menu_system.show_input_dialog(
            "Name für das neue Projekt",
            "new_project"
        )
        
        if not project_name:
            return
        
        output_file = self.directories['examples'] / f"{project_name}.xlsx"
        
        if output_file.exists():
            if not self.menu_system.show_confirmation(
                f"Datei '{output_file.name}' existiert bereits. Überschreiben?"
            ):
                self.menu_system.show_info("Abgebrochen")
                return
        
        try:
            # Excel-Template-Creator importieren
            from excel_template_creator import create_test_excel_with_timestep_management
            
            create_test_excel_with_timestep_management(output_file)
            self.menu_system.show_success(f"Beispielprojekt erstellt: {output_file}")
            
            # Projekte neu laden
            self.project_selector.refresh_projects()
            
        except ImportError:
            self.menu_system.show_error("excel_template_creator.py nicht verfügbar")
        except Exception as e:
            self.menu_system.show_error(f"Fehler beim Erstellen: {e}")
    
    def setup_project_structure_interactive(self):
        """Richtet die Projektstruktur interaktiv ein."""
        print("\n🔧 PROJEKTSTRUKTUR EINRICHTEN")
        print("-" * 40)
        
        print("Erstelle erforderliche Verzeichnisse...")
        
        # Verzeichnisse neu erstellen
        self.directories = self.setup_directories()
        
        for name, path in self.directories.items():
            print(f"✅ {name}: {path}")
        
        self.menu_system.show_success("Projektstruktur eingerichtet!")
        
        # Prüfe auf fehlende Module
        self.check_missing_modules()
    
    def check_missing_modules(self):
        """Prüft auf fehlende Module."""
        print("\nPrüfe Module...")
        
        required_modules = [
            'excel_reader', 'system_builder', 'optimizer', 
            'results_processor', 'visualizer', 'analyzer',
            'energy_system_exporter'
        ]
        
        missing_modules = []
        
        for module_name in required_modules:
            module_file = self.directories['modules'] / f"{module_name}.py"
            if module_file.exists():
                print(f"✅ {module_name}.py")
            else:
                print(f"❌ {module_name}.py (fehlt)")
                missing_modules.append(module_name)
        
        if missing_modules:
            self.menu_system.show_warning(
                f"Fehlende Module: {', '.join(missing_modules)}",
                "Stellen Sie sicher, dass alle Module im 'modules/' Verzeichnis vorhanden sind."
            )
        else:
            self.menu_system.show_success("Alle Module verfügbar!")
    
    def show_project_info(self):
        """Zeigt Projektinformationen an."""
        print("\n📋 PROJEKTINFORMATIONEN")
        print("=" * 50)
        
        # Basis-Informationen
        print(f"Projektverzeichnis: {self.project_root}")
        print(f"Verfügbare Projekte: {self.project_selector.get_project_count()}")
        
        # Verzeichnisse
        print("\nVerzeichnisse:")
        for name, path in self.directories.items():
            exists = "✅" if path.exists() else "❌"
            print(f"  {exists} {name}: {path}")
        
        # Zuletzt geänderte Projekte
        print("\nZuletzt geänderte Projekte:")
        recent_projects = self.project_selector.get_recent_projects(3)
        for project in recent_projects:
            import time
            mod_time = time.strftime('%Y-%m-%d %H:%M', 
                                   time.localtime(project['modified']))
            print(f"  📋 {project['name']} ({mod_time})")
        
        # Konfiguration
        print("\nAktuelle Konfiguration:")
        modules = self.config_manager.get_module_config()
        for module, enabled in modules.items():
            status = "✓" if enabled else "✗"
            print(f"  {status} {module}")
        
        # Validierung
        errors = self.config_manager.validate_config()
        if errors:
            print("\n⚠️ Konfigurationsprobleme:")
            for error in errors:
                print(f"  • {error}")
        else:
            print("\n✅ Konfiguration gültig")
    
    def test_functions(self):
        """Führt System-Tests durch."""
        print("\n🧪 SYSTEM-TESTS")
        print("-" * 40)
        
        tests = [
            ("Verzeichnis-Struktur", self.test_directory_structure),
            ("Module-Verfügbarkeit", self.test_module_availability),
            ("Konfiguration", self.test_configuration),
            ("Projekt-Validierung", self.test_project_validation)
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n🔍 Test: {test_name}")
                result = test_func()
                if result:
                    print(f"✅ {test_name}: OK")
                else:
                    print(f"❌ {test_name}: FEHLER")
            except Exception as e:
                print(f"❌ {test_name}: EXCEPTION - {e}")
                if self.config_manager.get_setting('debug_mode', False):
                    import traceback
                    traceback.print_exc()
    
    def test_directory_structure(self) -> bool:
        """Testet die Verzeichnis-Struktur."""
        for name, path in self.directories.items():
            if not path.exists():
                print(f"  ❌ {name}: {path} nicht gefunden")
                return False
            print(f"  ✅ {name}: {path}")
        return True
    
    def test_module_availability(self) -> bool:
        """Testet die Verfügbarkeit der Module."""
        required_modules = ['excel_reader', 'system_builder', 'optimizer', 'results_processor']
        
        for module_name in required_modules:
            module_file = self.directories['modules'] / f"{module_name}.py"
            if not module_file.exists():
                print(f"  ❌ {module_name}.py nicht gefunden")
                return False
            print(f"  ✅ {module_name}.py")
        return True
    
    def test_configuration(self) -> bool:
        """Testet die Konfiguration."""
        errors = self.config_manager.validate_config()
        if errors:
            for error in errors:
                print(f"  ❌ {error}")
            return False
        print("  ✅ Konfiguration gültig")
        return True
    
    def test_project_validation(self) -> bool:
        """Testet die Projekt-Validierung."""
        projects = self.project_selector.available_projects
        if not projects:
            print("  ❌ Keine Projekte gefunden")
            return False
        
        valid_count = 0
        for project in projects:
            if self.project_selector.validate_project(project):
                valid_count += 1
                print(f"  ✅ {project['name']}")
            else:
                print(f"  ❌ {project['name']}")
        
        return valid_count > 0
    
    def run(self):
        """Hauptschleife des Programms."""
        # Header anzeigen
        self.menu_system.show_project_header(
            str(self.project_root),
            self.project_selector.get_project_count()
        )
        
        # Hauptschleife
        while True:
            try:
                choice = self.menu_system.show_main_menu()
                
                # Menü-Auswahl verarbeiten
                if not self.menu_system.handle_choice(choice):
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Programm beendet.")
                break
            except Exception as e:
                self.menu_system.show_error(f"Unerwarteter Fehler: {e}")
                if self.config_manager.get_setting('debug_mode', False):
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