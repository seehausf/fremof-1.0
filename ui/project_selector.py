#!/usr/bin/env python3
"""
Project Selector für oemof.solph Energiesystem-Optimierung
========================================================

Verwaltet die Auswahl und Anzeige von verfügbaren Projekten.
Separiert die Projekt-Verwaltung von der Menü-Logik.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging


class ProjectSelector:
    """Verwaltet die Auswahl und Anzeige von Projekten."""
    
    def __init__(self, examples_dir: Path):
        """
        Initialisiert den Project Selector.
        
        Args:
            examples_dir: Verzeichnis mit Beispiel-Projekten
        """
        self.examples_dir = examples_dir
        self.available_projects: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        
        # Projekte initial laden
        self.load_available_projects()
    
    def load_available_projects(self):
        """Lädt verfügbare Projekte aus dem examples/ Verzeichnis."""
        self.available_projects = []
        
        if not self.examples_dir.exists():
            self.logger.warning(f"Examples-Verzeichnis nicht gefunden: {self.examples_dir}")
            return
        
        excel_files = list(self.examples_dir.glob('*.xlsx'))
        
        for excel_file in excel_files:
            # Temporäre Excel-Dateien ignorieren
            if not excel_file.name.startswith('~'):
                project_info = self._extract_project_info(excel_file)
                self.available_projects.append(project_info)
        
        # Projekte alphabetisch sortieren
        self.available_projects.sort(key=lambda x: x['name'])
        
        self.logger.info(f"Gefunden: {len(self.available_projects)} verfügbare Projekte")
    
    def _extract_project_info(self, excel_file: Path) -> Dict[str, Any]:
        """
        Extrahiert Projekt-Informationen aus einer Excel-Datei.
        
        Args:
            excel_file: Pfad zur Excel-Datei
            
        Returns:
            Dictionary mit Projekt-Informationen
        """
        project_info = {
            'name': excel_file.stem,
            'file': excel_file,
            'size': excel_file.stat().st_size,
            'modified': excel_file.stat().st_mtime,
            'description': self._generate_description(excel_file)
        }
        
        return project_info
    
    def _generate_description(self, excel_file: Path) -> str:
        """
        Generiert eine Beschreibung für ein Projekt.
        
        Args:
            excel_file: Pfad zur Excel-Datei
            
        Returns:
            Beschreibung des Projekts
        """
        name = excel_file.stem
        
        # Spezielle Beschreibungen für bekannte Beispiele
        descriptions = {
            'example_1': 'Basis-Beispiel (PV + Load)',
            'example_1b': 'Investment-Beispiel mit System-Export',
            'example_2': 'Investment-Optimierung (PV + Battery)',
            'example_3': 'Komplexes System (Multi-Technologie)',
            'test_timestep_management': 'Timestep-Management Test'
        }
        
        if name in descriptions:
            return descriptions[name]
        
        # Fallback-Beschreibung
        return f"Projekt - {excel_file.name}"
    
    def show_project_menu(self) -> Optional[Dict[str, Any]]:
        """
        Zeigt das Projekt-Auswahlmenü an.
        
        Returns:
            Ausgewähltes Projekt oder None bei Abbruch
        """
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
                selected_project = self.available_projects[project_idx]
                self.logger.info(f"Projekt ausgewählt: {selected_project['name']}")
                return selected_project
            else:
                print("❌ Ungültige Auswahl.")
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Ungültige Eingabe.")
            return None
    
    def show_project_details(self, project: Dict[str, Any]):
        """
        Zeigt Details zu einem Projekt an.
        
        Args:
            project: Projekt-Informationen
        """
        print(f"\n📋 PROJEKT-DETAILS: {project['name']}")
        print("-" * 40)
        print(f"Beschreibung: {project['description']}")
        print(f"Datei: {project['file'].name}")
        print(f"Größe: {project['size']:,} Bytes")
        
        # Zeitstempel formatieren
        import time
        modified_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(project['modified']))
        print(f"Letzte Änderung: {modified_time}")
        
        # Zusätzliche Informationen aus der Excel-Datei extrahieren
        try:
            self._show_excel_info(project['file'])
        except Exception as e:
            self.logger.warning(f"Konnte Excel-Informationen nicht laden: {e}")
    
    def _show_excel_info(self, excel_file: Path):
        """
        Zeigt Informationen aus der Excel-Datei an.
        
        Args:
            excel_file: Pfad zur Excel-Datei
        """
        try:
            import pandas as pd
            
            # Excel-Datei laden
            excel_data = pd.ExcelFile(excel_file)
            
            print(f"Excel-Sheets: {len(excel_data.sheet_names)}")
            for sheet_name in excel_data.sheet_names:
                print(f"  • {sheet_name}")
            
            # Komponenten-Informationen
            if 'components' in excel_data.sheet_names:
                components_df = pd.read_excel(excel_file, sheet_name='components')
                component_types = components_df['type'].value_counts()
                print(f"Komponenten: {len(components_df)}")
                for comp_type, count in component_types.items():
                    print(f"  • {comp_type}: {count}")
            
            # Flows-Informationen
            if 'flows' in excel_data.sheet_names:
                flows_df = pd.read_excel(excel_file, sheet_name='flows')
                print(f"Flows: {len(flows_df)}")
            
        except ImportError:
            print("pandas nicht verfügbar - keine Excel-Details")
        except Exception as e:
            self.logger.debug(f"Fehler beim Laden der Excel-Details: {e}")
    
    def get_project_count(self) -> int:
        """
        Gibt die Anzahl verfügbarer Projekte zurück.
        
        Returns:
            Anzahl verfügbarer Projekte
        """
        return len(self.available_projects)
    
    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Sucht ein Projekt nach Namen.
        
        Args:
            name: Projekt-Name
            
        Returns:
            Projekt-Informationen oder None wenn nicht gefunden
        """
        for project in self.available_projects:
            if project['name'] == name:
                return project
        return None
    
    def refresh_projects(self):
        """Aktualisiert die Liste der verfügbaren Projekte."""
        self.load_available_projects()
    
    def validate_project(self, project: Dict[str, Any]) -> bool:
        """
        Validiert ein Projekt.
        
        Args:
            project: Projekt-Informationen
            
        Returns:
            True wenn gültig, False sonst
        """
        project_file = project['file']
        
        # Datei existiert?
        if not project_file.exists():
            self.logger.error(f"Projekt-Datei nicht gefunden: {project_file}")
            return False
        
        # Ist es eine Excel-Datei?
        if not project_file.suffix.lower() == '.xlsx':
            self.logger.error(f"Ungültiger Dateityp: {project_file.suffix}")
            return False
        
        # Mindestgröße?
        if project_file.stat().st_size < 1000:  # 1KB Minimum
            self.logger.error(f"Datei zu klein: {project_file.stat().st_size} Bytes")
            return False
        
        # Kann geöffnet werden?
        try:
            import pandas as pd
            pd.ExcelFile(project_file)
            return True
        except Exception as e:
            self.logger.error(f"Kann Excel-Datei nicht öffnen: {e}")
            return False
    
    def get_recent_projects(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Gibt die zuletzt geänderten Projekte zurück.
        
        Args:
            limit: Maximale Anzahl von Projekten
            
        Returns:
            Liste der zuletzt geänderten Projekte
        """
        sorted_projects = sorted(self.available_projects, 
                               key=lambda x: x['modified'], 
                               reverse=True)
        return sorted_projects[:limit]
    
    def show_recent_projects(self):
        """Zeigt die zuletzt geänderten Projekte an."""
        recent_projects = self.get_recent_projects()
        
        if not recent_projects:
            print("Keine kürzlich geänderten Projekte gefunden.")
            return
        
        print("\n📅 ZULETZT GEÄNDERTE PROJEKTE")
        print("-" * 40)
        
        for i, project in enumerate(recent_projects, 1):
            import time
            modified_time = time.strftime('%Y-%m-%d %H:%M', 
                                         time.localtime(project['modified']))
            print(f" {i}. 📋 {project['description']} ({modified_time})")


# Test-Funktion
def test_project_selector():
    """Test-Funktion für den Project Selector."""
    from pathlib import Path
    
    # Test-Verzeichnis
    examples_dir = Path("examples")
    
    # Project Selector erstellen
    selector = ProjectSelector(examples_dir)
    
    print(f"Gefundene Projekte: {selector.get_project_count()}")
    
    # Zuletzt geänderte Projekte
    selector.show_recent_projects()
    
    # Projekt-Details für erstes Projekt
    if selector.available_projects:
        first_project = selector.available_projects[0]
        selector.show_project_details(first_project)
        
        # Validierung
        is_valid = selector.validate_project(first_project)
        print(f"Projekt gültig: {is_valid}")


if __name__ == "__main__":
    test_project_selector()
