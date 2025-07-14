#!/usr/bin/env python3
"""
importer.py - Datenimportmodul für Excel-Dateien

FIXED VERSION: Converter-Sheet wird korrekt geladen
- Verwendet core.utilities für gemeinsame Funktionen
- Vereinfachte Struktur durch Funktions-Extraktion
- Bessere Modularität
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Any

from .core import (
    setup_component_logger, resolve_timeseries_keywords, 
    validate_flow_extensions, validate_bus_references,
    log_dataframe_info
)

logger = setup_component_logger('importer')

class DataImporter:
    """Importiert Energiesystemdaten aus Excel-Dateien"""
    
    def __init__(self, excel_file: Path):
        """
        Initialisiert den Datenimporter
        
        Args:
            excel_file: Pfad zur Excel-Datei
        """
        self.excel_file = Path(excel_file)
        self.data = {}
        self.timeseries = None
        
        if not self.excel_file.exists():
            raise FileNotFoundError(f"Excel-Datei nicht gefunden: {excel_file}")
        
        logger.info(f"DataImporter initialisiert für: {self.excel_file.name}")
    
    def load_data(self) -> Dict[str, Any]:
        """
        Lädt alle Daten aus der Excel-Datei
        
        Returns:
            Dictionary mit allen geladenen Daten
        """
        logger.info(f"Lade Daten aus: {self.excel_file}")
        
        try:
            # 1. Verfügbare Sheets finden
            available_sheets = self._get_available_sheets()
            
            # 2. Zeitreihen laden (obligatorisch)
            self.timeseries = self._load_timeseries()
            self.data['timeseries'] = self.timeseries
            
            # 3. Komponenten-Sheets laden
            self._load_component_sheets(available_sheets)
            
            # 4. Datenvalidierung
            self._validate_all_data()
            
            # 5. Zeitreihen-Keywords auflösen
            self.data = resolve_timeseries_keywords(self.data, self.timeseries)
            
            logger.info("Datenimport erfolgreich abgeschlossen")
            return self.data
            
        except Exception as e:
            logger.error(f"Fehler beim Datenimport: {e}")
            raise
    
    def _get_available_sheets(self) -> list:
        """Ermittelt verfügbare Excel-Sheets"""
        xlsx_file = pd.ExcelFile(self.excel_file)
        available_sheets = xlsx_file.sheet_names
        logger.info(f"Verfügbare Sheets: {available_sheets}")
        return available_sheets
    
    def _load_timeseries(self) -> pd.DataFrame:
        """Lädt das timeseries Sheet"""
        logger.info("Lade Zeitreihen...")
        
        try:
            df = pd.read_excel(self.excel_file, sheet_name='timeseries')
        except Exception as e:
            raise ValueError(f"Fehler beim Laden des timeseries Sheets: {e}")
        
        # Validierung
        self._validate_timeseries(df)
        
        # Timestamps konvertieren und sortieren
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        logger.info(f"Zeitreihen geladen: {len(df)} Zeitschritte von {df['timestamp'].min()} bis {df['timestamp'].max()}")
        
        return df
    
    def _validate_timeseries(self, df: pd.DataFrame):
        """Validiert Zeitreihen-Daten"""
        # Timestamp-Spalte prüfen
        if 'timestamp' not in df.columns:
            raise ValueError("Spalte 'timestamp' in timeseries fehlt")
        
        # Duplikate prüfen
        if df['timestamp'].duplicated().any():
            raise ValueError("Duplikate in timestamp-Spalte gefunden")
        
        # Mindestens ein Zeitschritt
        if len(df) == 0:
            raise ValueError("Keine Zeitreihen-Daten gefunden")
    
    def _load_component_sheets(self, available_sheets: list):
        """Lädt alle Komponenten-Sheets"""
        # FIXED: Korrekte Sheet-Namen für alle Komponenten
        component_sheets = ['buses', 'sources', 'sinks', 'converters', 'storages']
        
        for sheet_name in component_sheets:
            if sheet_name in available_sheets:
                self.data[sheet_name] = self._load_component_sheet(sheet_name)
            else:
                logger.warning(f"Sheet '{sheet_name}' nicht gefunden - wird übersprungen")
                self.data[sheet_name] = pd.DataFrame()  # Leerer DataFrame
            
            log_dataframe_info(self.data[sheet_name], sheet_name)
    
    def _load_component_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Lädt ein einzelnes Komponenten-Sheet"""
        logger.debug(f"Lade {sheet_name}...")
        
        try:
            df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
        except Exception as e:
            raise ValueError(f"Fehler beim Laden von Sheet '{sheet_name}': {e}")
        
        # Validierung
        self._validate_component_sheet(df, sheet_name)
        
        # Include-Filter anwenden
        df = self._apply_include_filter(df, sheet_name)
        
        return df
    
    def _validate_component_sheet(self, df: pd.DataFrame, sheet_name: str):
        """Validiert ein Komponenten-Sheet"""
        # Leere DataFrames sind OK
        if df.empty:
            return
            
        # Pflichtfeld 'label' prüfen
        if 'label' not in df.columns:
            raise ValueError(f"Spalte 'label' in {sheet_name} fehlt")
        
        # Duplikate in labels prüfen
        if df['label'].duplicated().any():
            duplicates = df[df['label'].duplicated()]['label'].tolist()
            raise ValueError(f"Duplikate in {sheet_name} labels: {duplicates}")
        
        # NaN in label nicht erlaubt
        if df['label'].isna().any():
            raise ValueError(f"Leere labels in {sheet_name} nicht erlaubt")
    
    def _apply_include_filter(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """Wendet Include-Filter an"""
        if df.empty or 'include' not in df.columns:
            return df
        
        before_count = len(df)
        df = df[df['include'] == True].copy()
        after_count = len(df)
        
        if before_count != after_count:
            logger.info(f"  {before_count - after_count} Komponenten in {sheet_name} durch include=False gefiltert")
        
        return df
    
    def _validate_all_data(self):
        """Validiert alle geladenen Daten"""
        logger.info("Validiere Daten...")
        
        # Mindest-Anforderungen prüfen (nur wenn nicht leer)
        if self.data['sources'].empty:
            logger.warning("Keine Sources gefunden")
        
        if self.data['sinks'].empty:
            logger.warning("Keine Sinks gefunden")
        
        # Bus-Referenzen validieren
        validate_bus_references(self.data)
        
        # Flow-Erweiterungen validieren (Phase 2.1)
        validate_flow_extensions(self.data)
        
        logger.info("Datenvalidierung erfolgreich")
    
    def get_summary(self) -> str:
        """Erstellt eine Zusammenfassung der importierten Daten"""
        summary = []
        summary.append(f"Datenimport aus: {self.excel_file.name}")
        summary.append(f"Zeitreihen: {len(self.timeseries)} Zeitschritte")
        
        if not self.data['buses'].empty:
            summary.append(f"Buses: {len(self.data['buses'])}")
        
        if not self.data['sources'].empty:
            summary.append(f"Sources: {len(self.data['sources'])}")
            
        if not self.data['sinks'].empty:
            summary.append(f"Sinks: {len(self.data['sinks'])}")
            
        # FIXED: Converter-Summary hinzufügen
        if not self.data.get('converters', pd.DataFrame()).empty:
            summary.append(f"Converters: {len(self.data['converters'])}")
            
        if not self.data.get('storages', pd.DataFrame()).empty:
            summary.append(f"Storages: {len(self.data['storages'])}")
            
        return " | ".join(summary)
    
    def get_detailed_info(self) -> Dict[str, Any]:
        """
        Erstellt detaillierte Informationen über importierte Daten
        
        Returns:
            Dictionary mit detaillierten Infos
        """
        info = {
            'file_info': {
                'filename': self.excel_file.name,
                'file_size_mb': self.excel_file.stat().st_size / (1024*1024),
                'sheets_loaded': list(self.data.keys())
            },
            'timeseries_info': {
                'length': len(self.timeseries),
                'start_time': self.timeseries['timestamp'].min(),
                'end_time': self.timeseries['timestamp'].max(),
                'columns': list(self.timeseries.columns),
                'data_columns': [col for col in self.timeseries.columns if col != 'timestamp']
            },
            'component_counts': {}
        }
        
        # Komponenten-Anzahlen (FIXED: Converter hinzugefügt)
        for sheet_name in ['buses', 'sources', 'sinks', 'converters', 'storages']:
            df = self.data.get(sheet_name, pd.DataFrame())
            info['component_counts'][sheet_name] = len(df) if not df.empty else 0
        
        return info