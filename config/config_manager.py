#!/usr/bin/env python3
"""
Configuration Manager für oemof.solph Energiesystem-Optimierung
=============================================================

Zentrale Verwaltung aller Konfigurationseinstellungen.
Separiert die Konfiguration von der Geschäftslogik.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class ConfigManager:
    """Zentrale Verwaltung der Konfigurationseinstellungen."""
    
    def __init__(self, project_root: Path):
        """
        Initialisiert den Configuration Manager.
        
        Args:
            project_root: Wurzelverzeichnis des Projekts
        """
        self.project_root = project_root
        self.config_file = project_root / "config.json"
        self.logger = logging.getLogger(__name__)
        
        # Standard-Konfiguration
        self.default_config = self._get_default_config()
        
        # Aktuelle Konfiguration
        self.config = self.default_config.copy()
        
        # Konfiguration laden
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Gibt die Standard-Konfiguration zurück.
        
        Returns:
            Standard-Konfiguration
        """
        return {
            'modules': {
                'excel_reader': True,
                'system_builder': True,
                'optimizer': True,
                'results_processor': True,
                'visualizer': False,
                'analyzer': False,
                'system_exporter': False
            },
            'settings': {
                'solver': 'cbc',
                'debug_mode': False,
                'output_format': 'xlsx',
                'create_visualizations': True,
                'create_analysis': False,
                'save_model': False,
                'export_formats': ['json', 'yaml', 'txt']
            },
            'solver_options': {
                'cbc': {
                    'timeout': 300,
                    'gap': 0.01,
                    'threads': 4
                },
                'glpk': {
                    'timeout': 300,
                    'msg_lev': 'GLP_MSG_ERR'
                },
                'gurobi': {
                    'timeout': 300,
                    'MIPGap': 0.01,
                    'threads': 4
                }
            },
            'timestep_settings': {
                'default_strategy': 'full',
                'averaging_hours': 24,
                'sampling_factor': 4,
                'time_range_start': '2025-01-01 00:00',
                'time_range_end': '2025-12-31 23:00'
            },
            'export_settings': {
                'include_flows': True,
                'include_components': True,
                'include_buses': True,
                'include_investments': True,
                'simplify_large_arrays': True,
                'array_size_limit': 100
            },
            'visualization_settings': {
                'figure_size': [12, 8],
                'dpi': 300,
                'format': 'png',
                'style': 'seaborn-v0_8-whitegrid'
            },
            'directories': {
                'examples': 'examples',
                'modules': 'modules',
                'data': 'data',
                'output': 'data/output',
                'logs': 'logs'
            }
        }
    
    def load_config(self) -> bool:
        """
        Lädt die Konfiguration aus der Datei.
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.config_file.exists():
            self.logger.info("Keine Konfigurationsdatei gefunden - verwende Standards")
            return False
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Konfiguration rekursiv mergen
            self.config = self._merge_config(self.default_config, file_config)
            
            self.logger.info(f"Konfiguration geladen: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            self.config = self.default_config.copy()
            return False
    
    def save_config(self) -> bool:
        """
        Speichert die aktuelle Konfiguration.
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            # Verzeichnis erstellen falls nicht vorhanden
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Konfiguration gespeichert: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
            return False
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mergt geladene Konfiguration mit Standard-Konfiguration.
        
        Args:
            default: Standard-Konfiguration
            loaded: Geladene Konfiguration
            
        Returns:
            Gemergete Konfiguration
        """
        merged = default.copy()
        
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_module_config(self) -> Dict[str, bool]:
        """
        Gibt die Modul-Konfiguration zurück.
        
        Returns:
            Modul-Konfiguration
        """
        return self.config['modules'].copy()
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Gibt die allgemeinen Einstellungen zurück.
        
        Returns:
            Allgemeine Einstellungen
        """
        return self.config['settings'].copy()
    
    def get_solver_options(self, solver: str) -> Dict[str, Any]:
        """
        Gibt die Solver-Optionen zurück.
        
        Args:
            solver: Solver-Name
            
        Returns:
            Solver-Optionen
        """
        return self.config['solver_options'].get(solver, {})
    
    def get_timestep_settings(self) -> Dict[str, Any]:
        """
        Gibt die Timestep-Einstellungen zurück.
        
        Returns:
            Timestep-Einstellungen
        """
        return self.config['timestep_settings'].copy()
    
    def get_export_settings(self) -> Dict[str, Any]:
        """
        Gibt die Export-Einstellungen zurück.
        
        Returns:
            Export-Einstellungen
        """
        return self.config['export_settings'].copy()
    
    def get_visualization_settings(self) -> Dict[str, Any]:
        """
        Gibt die Visualisierung-Einstellungen zurück.
        
        Returns:
            Visualisierung-Einstellungen
        """
        return self.config['visualization_settings'].copy()
    
    def get_directories(self) -> Dict[str, str]:
        """
        Gibt die Verzeichnis-Konfiguration zurück.
        
        Returns:
            Verzeichnis-Konfiguration
        """
        return self.config['directories'].copy()
    
    def set_module_enabled(self, module_name: str, enabled: bool):
        """
        Aktiviert oder deaktiviert ein Modul.
        
        Args:
            module_name: Name des Moduls
            enabled: True für aktiviert, False für deaktiviert
        """
        if module_name in self.config['modules']:
            self.config['modules'][module_name] = enabled
            self.logger.info(f"Modul '{module_name}' {'aktiviert' if enabled else 'deaktiviert'}")
        else:
            self.logger.warning(f"Unbekanntes Modul: {module_name}")
    
    def set_setting(self, key: str, value: Any):
        """
        Setzt eine Einstellung.
        
        Args:
            key: Einstellungs-Schlüssel
            value: Wert
        """
        self.config['settings'][key] = value
        self.logger.info(f"Einstellung '{key}' = {value}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Gibt eine Einstellung zurück.
        
        Args:
            key: Einstellungs-Schlüssel
            default: Standard-Wert
            
        Returns:
            Einstellungs-Wert
        """
        return self.config['settings'].get(key, default)
    
    def reset_to_defaults(self):
        """Setzt die Konfiguration auf Standard-Werte zurück."""
        self.config = self.default_config.copy()
        self.logger.info("Konfiguration auf Standard-Werte zurückgesetzt")
    
    def export_config(self, format: str = 'json') -> str:
        """
        Exportiert die Konfiguration in verschiedenen Formaten.
        
        Args:
            format: Ausgabeformat ('json', 'yaml')
            
        Returns:
            Konfiguration als String
        """
        if format.lower() == 'yaml':
            return yaml.dump(self.config, default_flow_style=False, 
                           allow_unicode=True, indent=2)
        else:  # json
            return json.dumps(self.config, indent=2, ensure_ascii=False)
    
    def validate_config(self) -> List[str]:
        """
        Validiert die aktuelle Konfiguration.
        
        Returns:
            Liste der Validierungsfehler
        """
        errors = []
        
        # Module validieren
        required_modules = ['excel_reader', 'system_builder', 'optimizer', 'results_processor']
        for module in required_modules:
            if not self.config['modules'].get(module, False):
                errors.append(f"Erforderliches Modul '{module}' ist deaktiviert")
        
        # Solver validieren
        solver = self.config['settings'].get('solver', 'cbc')
        if solver not in self.config['solver_options']:
            errors.append(f"Unbekannter Solver: {solver}")
        
        # Verzeichnisse validieren
        for dir_name, dir_path in self.config['directories'].items():
            full_path = self.project_root / dir_path
            if dir_name in ['examples', 'modules'] and not full_path.exists():
                errors.append(f"Verzeichnis '{dir_name}' nicht gefunden: {full_path}")
        
        # Export-Formate validieren
        valid_formats = ['json', 'yaml', 'txt']
        export_formats = self.config['settings'].get('export_formats', [])
        for fmt in export_formats:
            if fmt not in valid_formats:
                errors.append(f"Ungültiges Export-Format: {fmt}")
        
        return errors
    
    def show_config_summary(self):
        """Zeigt eine Zusammenfassung der Konfiguration an."""
        print("\n⚙️ KONFIGURATION")
        print("-" * 40)
        
        # Module
        print("Module:")
        for module, enabled in self.config['modules'].items():
            status = "✓" if enabled else "✗"
            print(f"  {status} {module}")
        
        # Einstellungen
        print("\nEinstellungen:")
        for key, value in self.config['settings'].items():
            print(f"  {key}: {value}")
        
        # Solver
        current_solver = self.config['settings'].get('solver', 'cbc')
        print(f"\nSolver: {current_solver}")
        solver_options = self.get_solver_options(current_solver)
        for key, value in solver_options.items():
            print(f"  {key}: {value}")
        
        # Validierung
        errors = self.validate_config()
        if errors:
            print("\n❌ Validierungsfehler:")
            for error in errors:
                print(f"  • {error}")
        else:
            print("\n✅ Konfiguration gültig")
    
    def get_full_config(self) -> Dict[str, Any]:
        """
        Gibt die vollständige Konfiguration zurück.
        
        Returns:
            Vollständige Konfiguration
        """
        return self.config.copy()


# Test-Funktion
def test_config_manager():
    """Test-Funktion für den Configuration Manager."""
    from pathlib import Path
    
    # Test-Verzeichnis
    test_dir = Path("test_config")
    test_dir.mkdir(exist_ok=True)
    
    # Configuration Manager erstellen
    config_manager = ConfigManager(test_dir)
    
    # Konfiguration anzeigen
    config_manager.show_config_summary()
    
    # Modul konfigurieren
    config_manager.set_module_enabled('system_exporter', True)
    
    # Einstellung ändern
    config_manager.set_setting('debug_mode', True)
    
    # Konfiguration speichern
    config_manager.save_config()
    
    # Konfiguration laden
    config_manager.load_config()
    
    # Validierung
    errors = config_manager.validate_config()
    print(f"\nValidierungsfehler: {len(errors)}")
    
    # Export testen
    json_export = config_manager.export_config('json')
    print(f"\nJSON-Export: {len(json_export)} Zeichen")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_config_manager()
