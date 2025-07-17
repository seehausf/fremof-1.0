#!/usr/bin/env python3
"""
File Utilities für oemof.solph Energiesystem-Optimierung
======================================================

Hilfsfunktionen für Datei- und Verzeichnisoperationen.
Separiert die Datei-Logik von der Geschäftslogik.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging


class FileUtils:
    """Hilfsfunktionen für Datei- und Verzeichnisoperationen."""
    
    def __init__(self):
        """Initialisiert die FileUtils."""
        self.logger = logging.getLogger(__name__)
    
    def ensure_directory_structure(self, directories: Dict[str, Union[str, Path]]) -> Dict[str, Path]:
        """
        Stellt sicher, dass alle Verzeichnisse existieren.
        
        Args:
            directories: Dictionary mit Verzeichnis-Namen und Pfaden
            
        Returns:
            Dictionary mit Verzeichnis-Namen und Path-Objekten
        """
        created_directories = {}
        
        for name, path in directories.items():
            dir_path = Path(path)
            
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Verzeichnis erstellt: {dir_path}")
                except Exception as e:
                    self.logger.error(f"Fehler beim Erstellen von {name}: {e}")
                    raise
            
            created_directories[name] = dir_path
        
        return created_directories
    
    def create_output_directory(self, base_dir: Path, project_name: str) -> Path:
        """
        Erstellt ein Output-Verzeichnis für ein Projekt.
        
        Args:
            base_dir: Basis-Verzeichnis
            project_name: Name des Projekts
            
        Returns:
            Pfad zum Output-Verzeichnis
        """
        output_dir = base_dir / project_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp-Datei erstellen
        timestamp_file = output_dir / ".timestamp"
        with open(timestamp_file, 'w') as f:
            f.write(str(time.time()))
        
        self.logger.info(f"Output-Verzeichnis erstellt: {output_dir}")
        return output_dir
    
    def cleanup_old_outputs(self, output_base_dir: Path, max_age_days: int = 30):
        """
        Räumt alte Output-Verzeichnisse auf.
        
        Args:
            output_base_dir: Basis-Verzeichnis für Outputs
            max_age_days: Maximales Alter in Tagen
        """
        if not output_base_dir.exists():
            return
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        for project_dir in output_base_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            timestamp_file = project_dir / ".timestamp"
            
            if timestamp_file.exists():
                try:
                    with open(timestamp_file, 'r') as f:
                        timestamp = float(f.read().strip())
                    
                    if timestamp < cutoff_time:
                        shutil.rmtree(project_dir)
                        self.logger.info(f"Altes Output-Verzeichnis gelöscht: {project_dir}")
                
                except Exception as e:
                    self.logger.warning(f"Fehler beim Überprüfen von {project_dir}: {e}")
    
    def get_file_info(self, file_path: Path) -> Dict[str, Union[str, int, float]]:
        """
        Gibt Informationen über eine Datei zurück.
        
        Args:
            file_path: Pfad zur Datei
            
        Returns:
            Dictionary mit Datei-Informationen
        """
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        
        return {
            'name': file_path.name,
            'stem': file_path.stem,
            'suffix': file_path.suffix,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'readable': os.access(file_path, os.R_OK),
            'writable': os.access(file_path, os.W_OK),
            'executable': os.access(file_path, os.X_OK)
        }
    
    def find_files(self, directory: Path, pattern: str = "*", 
                  recursive: bool = True) -> List[Path]:
        """
        Findet Dateien in einem Verzeichnis.
        
        Args:
            directory: Suchverzeichnis
            pattern: Suchmuster (glob-Pattern)
            recursive: Rekursive Suche
            
        Returns:
            Liste der gefundenen Dateien
        """
        if not directory.exists():
            return []
        
        if recursive:
            return list(directory.rglob(pattern))
        else:
            return list(directory.glob(pattern))
    
    def copy_file(self, source: Path, destination: Path, 
                 overwrite: bool = False) -> bool:
        """
        Kopiert eine Datei.
        
        Args:
            source: Quell-Datei
            destination: Ziel-Datei
            overwrite: Überschreiben erlaubt
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not source.exists():
            self.logger.error(f"Quell-Datei nicht gefunden: {source}")
            return False
        
        if destination.exists() and not overwrite:
            self.logger.error(f"Ziel-Datei existiert bereits: {destination}")
            return False
        
        try:
            # Ziel-Verzeichnis erstellen
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Datei kopieren
            shutil.copy2(source, destination)
            
            self.logger.info(f"Datei kopiert: {source} -> {destination}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Kopieren: {e}")
            return False
    
    def move_file(self, source: Path, destination: Path, 
                 overwrite: bool = False) -> bool:
        """
        Verschiebt eine Datei.
        
        Args:
            source: Quell-Datei
            destination: Ziel-Datei
            overwrite: Überschreiben erlaubt
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not source.exists():
            self.logger.error(f"Quell-Datei nicht gefunden: {source}")
            return False
        
        if destination.exists() and not overwrite:
            self.logger.error(f"Ziel-Datei existiert bereits: {destination}")
            return False
        
        try:
            # Ziel-Verzeichnis erstellen
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Datei verschieben
            shutil.move(str(source), str(destination))
            
            self.logger.info(f"Datei verschoben: {source} -> {destination}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verschieben: {e}")
            return False
    
    def delete_file(self, file_path: Path, confirm: bool = True) -> bool:
        """
        Löscht eine Datei.
        
        Args:
            file_path: Zu löschende Datei
            confirm: Bestätigung erforderlich
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not file_path.exists():
            self.logger.warning(f"Datei nicht gefunden: {file_path}")
            return False
        
        if confirm:
            response = input(f"Datei '{file_path.name}' wirklich löschen? (j/N): ")
            if response.lower() not in ['j', 'ja', 'y', 'yes']:
                self.logger.info("Löschen abgebrochen")
                return False
        
        try:
            file_path.unlink()
            self.logger.info(f"Datei gelöscht: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen: {e}")
            return False
    
    def create_backup(self, file_path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Erstellt eine Backup-Kopie einer Datei.
        
        Args:
            file_path: Zu sichernde Datei
            backup_dir: Backup-Verzeichnis (optional)
            
        Returns:
            Pfad zur Backup-Datei oder None bei Fehler
        """
        if not file_path.exists():
            self.logger.error(f"Datei nicht gefunden: {file_path}")
            return None
        
        if backup_dir is None:
            backup_dir = file_path.parent / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Timestamp für eindeutigen Namen
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        
        if self.copy_file(file_path, backup_path):
            return backup_path
        else:
            return None
    
    def get_temp_directory(self) -> Path:
        """
        Gibt ein temporäres Verzeichnis zurück.
        
        Returns:
            Pfad zum temporären Verzeichnis
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="oemof_"))
        self.logger.info(f"Temporäres Verzeichnis erstellt: {temp_dir}")
        return temp_dir
    
    def cleanup_temp_directory(self, temp_dir: Path):
        """
        Räumt ein temporäres Verzeichnis auf.
        
        Args:
            temp_dir: Temporäres Verzeichnis
        """
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                self.logger.info(f"Temporäres Verzeichnis gelöscht: {temp_dir}")
            except Exception as e:
                self.logger.warning(f"Fehler beim Löschen von {temp_dir}: {e}")
    
    def check_disk_space(self, directory: Path, required_mb: int = 100) -> bool:
        """
        Überprüft verfügbaren Speicherplatz.
        
        Args:
            directory: Zu prüfendes Verzeichnis
            required_mb: Erforderlicher Speicherplatz in MB
            
        Returns:
            True wenn genügend Speicherplatz vorhanden
        """
        try:
            stat = shutil.disk_usage(directory)
            available_mb = stat.free / (1024 * 1024)
            
            if available_mb >= required_mb:
                return True
            else:
                self.logger.warning(f"Nicht genügend Speicherplatz: {available_mb:.1f} MB verfügbar, {required_mb} MB erforderlich")
                return False
                
        except Exception as e:
            self.logger.error(f"Fehler beim Überprüfen des Speicherplatzes: {e}")
            return False
    
    def format_file_size(self, size_bytes: int) -> str:
        """
        Formatiert eine Dateigröße menschenlesbar.
        
        Args:
            size_bytes: Größe in Bytes
            
        Returns:
            Formatierte Größe
        """
        if size_bytes == 0:
            return "0 Bytes"
        
        size_units = ['Bytes', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and unit_index < len(size_units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.1f} {size_units[unit_index]}"
    
    def get_directory_size(self, directory: Path) -> int:
        """
        Berechnet die Größe eines Verzeichnisses.
        
        Args:
            directory: Verzeichnis
            
        Returns:
            Größe in Bytes
        """
        total_size = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except Exception as e:
                    self.logger.warning(f"Fehler beim Lesen von {file_path}: {e}")
        
        return total_size
    
    def show_directory_info(self, directory: Path):
        """
        Zeigt Informationen über ein Verzeichnis an.
        
        Args:
            directory: Verzeichnis
        """
        if not directory.exists():
            print(f"❌ Verzeichnis nicht gefunden: {directory}")
            return
        
        print(f"\n📁 VERZEICHNIS-INFORMATIONEN: {directory}")
        print("-" * 50)
        
        # Basis-Informationen
        print(f"Pfad: {directory.absolute()}")
        print(f"Existiert: {'Ja' if directory.exists() else 'Nein'}")
        
        if directory.exists():
            # Anzahl Dateien und Unterverzeichnisse
            files = list(directory.rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            dir_count = len([f for f in files if f.is_dir()])
            
            print(f"Dateien: {file_count}")
            print(f"Unterverzeichnisse: {dir_count}")
            
            # Größe
            total_size = self.get_directory_size(directory)
            print(f"Gesamtgröße: {self.format_file_size(total_size)}")
            
            # Letzte Änderung
            mod_time = directory.stat().st_mtime
            print(f"Letzte Änderung: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))}")


# Globale Instanz
file_utils = FileUtils()


# Test-Funktion
def test_file_utils():
    """Test-Funktion für die FileUtils."""
    
    # Test-Verzeichnis erstellen
    test_dir = Path("test_file_utils")
    test_dir.mkdir(exist_ok=True)
    
    # Verzeichnis-Struktur erstellen
    directories = {
        'input': test_dir / 'input',
        'output': test_dir / 'output',
        'temp': test_dir / 'temp'
    }
    
    created_dirs = file_utils.ensure_directory_structure(directories)
    print(f"Erstellt: {list(created_dirs.keys())}")
    
    # Test-Datei erstellen
    test_file = test_dir / 'input' / 'test.txt'
    with open(test_file, 'w') as f:
        f.write("Test-Inhalt")
    
    # Datei-Informationen
    file_info = file_utils.get_file_info(test_file)
    print(f"Datei-Info: {file_info}")
    
    # Datei kopieren
    copy_success = file_utils.copy_file(test_file, test_dir / 'output' / 'test_copy.txt')
    print(f"Kopiert: {copy_success}")
    
    # Backup erstellen
    backup_path = file_utils.create_backup(test_file)
    print(f"Backup: {backup_path}")
    
    # Verzeichnis-Informationen
    file_utils.show_directory_info(test_dir)
    
    # Cleanup
    shutil.rmtree(test_dir)
    print("Test-Verzeichnis gelöscht")


if __name__ == "__main__":
    test_file_utils()
