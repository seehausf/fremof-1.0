#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Energiesystemmodellierung - Hauptauswahlmenü
===============================================================

Interaktive Projektauswahl und Modulsteuerung für die Energiesystemoptimierung.
Ermöglicht das Ein-/Ausschalten verschiedener Module und die Auswahl von Projekten.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import os
import sys
from pathlib import Path
import yaml
from typing import Dict, List, Optional

# Projektpfad zum Python-Path hinzufügen
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import der Projektmodule
try:
    from main import main_program
    from setup import create_example_files, setup_project_structure
except ImportError as e:
    print(f"❌ Fehler beim Importieren der Module: {e}")
    print("Führen Sie zuerst 'python setup.py' aus.")
    sys.exit(1)


class ProjectManager:
    """Verwaltet Projektauswahl und Modulkonfiguration."""
    
    def __init__(self):
        self.config_file = project_root / "config" / "settings.yaml"
        self.examples_dir = project_root / "examples"
        self.data_dir = project_root / "data"
        self.modules_config = self.load_modules_config()
        
    def load_modules_config(self) -> Dict:
        """Lädt die Modulkonfiguration."""
        default_config = {
            'modules': {
                'excel_reader': True,
                'system_builder': True,
                'optimizer': True,
                'results_processor': True,
                'visualizer': False,  # Optional
                'analyzer': False     # Optional
            },
            'settings': {
                'solver': 'cbc',
                'output_format': 'xlsx',
                'create_plots': False,
                'save_model': False,
                'debug_mode': False
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                # Merge mit Default-Werten
                for section in default_config:
                    if section not in config:
                        config[section] = default_config[section]
                    else:
                        config[section] = {**default_config[section], **config[section]}
                return config
            except Exception as e:
                print(f"⚠️  Fehler beim Laden der Konfiguration: {e}")
                return default_config
        else:
            return default_config
    
    def save_modules_config(self):
        """Speichert die aktuelle Modulkonfiguration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.modules_config, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            print("✅ Konfiguration gespeichert")
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Konfiguration: {e}")
    
    def get_available_projects(self) -> List[Path]:
        """Findet alle verfügbaren Excel-Projekte."""
        projects = []
        
        # Beispielprojekte
        if self.examples_dir.exists():
            for file in self.examples_dir.glob("*.xlsx"):
                projects.append(file)
        
        # Benutzerprojekte im data/input Verzeichnis
        input_dir = self.data_dir / "input"
        if input_dir.exists():
            for file in input_dir.glob("*.xlsx"):
                projects.append(file)
        
        return sorted(projects)
    
    def display_header(self):
        """Zeigt den Programm-Header an."""
        print("=" * 80)
        print("  🔋 oemof.solph 0.6.0 - Energiesystemmodellierung")
        print("  📊 Interaktive Projektauswahl und Modulsteuerung")
        print("=" * 80)
        print()
    
    def display_main_menu(self):
        """Zeigt das Hauptmenü an."""
        print("📋 HAUPTMENÜ")
        print("-" * 40)
        print("1. 🚀 Projekt ausführen")
        print("2. ⚙️  Module konfigurieren")
        print("3. 📁 Neues Beispielprojekt erstellen")
        print("4. 🔧 Projektstruktur einrichten")
        print("5. ℹ️  Projektinformationen anzeigen")
        print("6. ❌ Beenden")
        print()
    
    def select_project(self) -> Optional[Path]:
        """Projektauswahl durch Benutzer."""
        projects = self.get_available_projects()
        
        if not projects:
            print("❌ Keine Projekte gefunden!")
            print("Erstellen Sie zuerst Beispielprojekte (Option 3)")
            return None
        
        print("📂 VERFÜGBARE PROJEKTE")
        print("-" * 40)
        for i, project in enumerate(projects, 1):
            project_type = "📋 Beispiel" if "examples" in str(project) else "👤 Benutzer"
            print(f"{i:2d}. {project_type} - {project.name}")
        print()
        
        while True:
            try:
                choice = input("Projekt auswählen (Nummer): ").strip()
                if not choice:
                    return None
                    
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    return projects[idx]
                else:
                    print("❌ Ungültige Auswahl!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")
    
    def configure_modules(self):
        """Modulkonfiguration durch Benutzer."""
        print("⚙️  MODULKONFIGURATION")
        print("-" * 40)
        
        modules = self.modules_config['modules']
        settings = self.modules_config['settings']
        
        print("Module (✅ aktiv, ❌ inaktiv):")
        for i, (module, active) in enumerate(modules.items(), 1):
            status = "✅" if active else "❌"
            print(f"{i}. {status} {module}")
        
        print(f"\n{len(modules)+1}. 🔧 Erweiterte Einstellungen")
        print(f"{len(modules)+2}. 💾 Konfiguration speichern")
        print(f"{len(modules)+3}. ↩️  Zurück zum Hauptmenü")
        
        while True:
            try:
                choice = input("\nOption auswählen: ").strip()
                if not choice:
                    continue
                    
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(modules):
                    module_name = list(modules.keys())[choice_num - 1]
                    modules[module_name] = not modules[module_name]
                    status = "✅ aktiviert" if modules[module_name] else "❌ deaktiviert"
                    print(f"Modul '{module_name}' {status}")
                    
                elif choice_num == len(modules) + 1:
                    self.configure_advanced_settings()
                    
                elif choice_num == len(modules) + 2:
                    self.save_modules_config()
                    
                elif choice_num == len(modules) + 3:
                    break
                    
                else:
                    print("❌ Ungültige Auswahl!")
                    
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")
    
    def configure_advanced_settings(self):
        """Erweiterte Einstellungen konfigurieren."""
        print("\n🔧 ERWEITERTE EINSTELLUNGEN")
        print("-" * 40)
        
        settings = self.modules_config['settings']
        
        for key, value in settings.items():
            print(f"{key}: {value}")
        
        print("\nVerfügbare Einstellungen:")
        print("1. solver (cbc, glpk, gurobi)")
        print("2. output_format (xlsx, csv)")
        print("3. create_plots (True/False)")
        print("4. save_model (True/False)")
        print("5. debug_mode (True/False)")
        print("6. Zurück")
        
        while True:
            choice = input("\nEinstellung ändern (1-6): ").strip()
            if choice == "6" or not choice:
                break
            elif choice == "1":
                solver = input("Solver (cbc/glpk/gurobi): ").strip().lower()
                if solver in ['cbc', 'glpk', 'gurobi']:
                    settings['solver'] = solver
                    print(f"✅ Solver auf '{solver}' gesetzt")
            elif choice == "2":
                fmt = input("Output-Format (xlsx/csv): ").strip().lower()
                if fmt in ['xlsx', 'csv']:
                    settings['output_format'] = fmt
                    print(f"✅ Output-Format auf '{fmt}' gesetzt")
            elif choice in ["3", "4", "5"]:
                setting_map = {"3": "create_plots", "4": "save_model", "5": "debug_mode"}
                setting_key = setting_map[choice]
                value = input(f"{setting_key} (True/False): ").strip().lower()
                if value in ['true', 'false']:
                    settings[setting_key] = value == 'true'
                    print(f"✅ {setting_key} auf '{settings[setting_key]}' gesetzt")
    
    def show_project_info(self):
        """Zeigt Projektinformationen an."""
        print("ℹ️  PROJEKTINFORMATIONEN")
        print("-" * 40)
        print(f"🏠 Projektverzeichnis: {project_root}")
        print(f"📁 Beispiele: {len(list(self.examples_dir.glob('*.xlsx')))} Dateien")
        print(f"⚙️  Aktive Module: {sum(self.modules_config['modules'].values())}")
        print(f"🔧 Solver: {self.modules_config['settings']['solver']}")
        print(f"📊 Debug-Modus: {self.modules_config['settings']['debug_mode']}")
        
        # Verfügbare Projekte anzeigen
        projects = self.get_available_projects()
        print(f"\n📂 Verfügbare Projekte: {len(projects)}")
        for project in projects[:5]:  # Nur erste 5 anzeigen
            print(f"   • {project.name}")
        if len(projects) > 5:
            print(f"   ... und {len(projects) - 5} weitere")
    
    def run(self):
        """Hauptprogrammschleife."""
        self.display_header()
        
        while True:
            self.display_main_menu()
            choice = input("Option auswählen (1-6): ").strip()
            print()
            
            if choice == "1":
                # Projekt ausführen
                project_file = self.select_project()
                if project_file:
                    print(f"🚀 Starte Projekt: {project_file.name}")
                    try:
                        main_program(project_file, self.modules_config)
                    except KeyboardInterrupt:
                        print("\n⚠️  Ausführung durch Benutzer unterbrochen")
                    except Exception as e:
                        print(f"❌ Fehler bei der Ausführung: {e}")
                        if self.modules_config['settings']['debug_mode']:
                            import traceback
                            traceback.print_exc()
                    print("\n" + "=" * 50)
            
            elif choice == "2":
                # Module konfigurieren
                self.configure_modules()
            
            elif choice == "3":
                # Beispielprojekte erstellen
                print("📁 Erstelle Beispielprojekte...")
                try:
                    create_example_files()
                    print("✅ Beispielprojekte erfolgreich erstellt!")
                except Exception as e:
                    print(f"❌ Fehler beim Erstellen der Beispiele: {e}")
            
            elif choice == "4":
                # Projektstruktur einrichten
                print("🔧 Richte Projektstruktur ein...")
                try:
                    setup_project_structure()
                    print("✅ Projektstruktur erfolgreich eingerichtet!")
                except Exception as e:
                    print(f"❌ Fehler beim Einrichten der Struktur: {e}")
            
            elif choice == "5":
                # Projektinformationen
                self.show_project_info()
            
            elif choice == "6":
                # Beenden
                print("👋 Auf Wiedersehen!")
                break
            
            else:
                print("❌ Ungültige Auswahl! Bitte wählen Sie 1-6.")
            
            input("\n⏸️  Drücken Sie Enter zum Fortfahren...")
            print()


if __name__ == "__main__":
    try:
        manager = ProjectManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n👋 Programm beendet.")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        sys.exit(1)
