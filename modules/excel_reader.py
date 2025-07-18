#!/usr/bin/env python3
"""
Excel Reader für Multi-Input/Output Energiesysteme - FIXED VERSION
================================================================

Erweiterte Version des Excel-Readers mit Multi-IO-Unterstützung.
FIXED: Alle erforderlichen Methoden für main.py Kompatibilität hinzugefügt.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 2.1.0 (Fixed)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging


class ExcelReader:
    """
    Excel-Reader-Klasse mit Multi-Input/Output-Unterstützung.
    Vollständig kompatibel mit bestehendem main.py.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Excel-Reader.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Konfiguration
        self.bus_separator = settings.get('bus_separator', '|')
        self.factor_separator = settings.get('factor_separator', '|')
        
        # Erweiterte Spalten-Definitionen
        self.required_columns = self._get_required_columns()
        self.optional_columns = self._get_optional_columns()
    
    def read_project_file(self, excel_file: Path) -> Dict[str, Any]:
        """
        Hauptmethode für main.py Kompatibilität.
        Liest Excel-Datei und gibt verarbeitete Daten zurück.
        
        Args:
            excel_file: Pfad zur Excel-Datei
            
        Returns:
            Dictionary mit verarbeiteten Daten
        """
        return self.process_excel_data(excel_file)
    
    def process_excel_data(self, excel_file: Path) -> Dict[str, Any]:
        """
        Verarbeitet Excel-Datei mit Multi-IO-Unterstützung.
        
        Args:
            excel_file: Pfad zur Excel-Datei
            
        Returns:
            Dictionary mit verarbeiteten Daten
        """
        self.logger.info(f"📖 Lade Excel-Datei: {excel_file.name}")
        
        try:
            # Excel-Datei laden
            excel_data = pd.ExcelFile(excel_file)
            
            # Daten-Dictionary
            processed_data = {}
            
            # Sheets verarbeiten
            processed_data['settings'] = self._process_settings_sheet(excel_data)
            processed_data['timestep_settings'] = self._process_timestep_settings_sheet(excel_data)
            processed_data['buses'] = self._process_buses_sheet(excel_data)
            processed_data['sources'] = self._process_sources_sheet(excel_data)
            processed_data['sinks'] = self._process_sinks_sheet(excel_data)
            processed_data['simple_transformers'] = self._process_transformers_sheet(excel_data)
            processed_data['timeseries'] = self._process_timeseries_sheet(excel_data)
            
            # Validierung
            self._validate_processed_data(processed_data)
            
            self.logger.info("✅ Excel-Daten erfolgreich verarbeitet")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Verarbeiten der Excel-Datei: {e}")
            raise
    
    def get_data_summary(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Erstellt eine Zusammenfassung der verarbeiteten Daten.
        ERFORDERLICH für main.py Kompatibilität.
        
        Args:
            processed_data: Verarbeitete Excel-Daten
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        summary = {}
        
        try:
            # Buses
            if 'buses' in processed_data and not processed_data['buses'].empty:
                active_buses = len(processed_data['buses'][processed_data['buses']['include'] == 1])
                summary['Buses'] = f"{active_buses} aktiv"
            
            # Sources
            if 'sources' in processed_data and not processed_data['sources'].empty:
                active_sources = len(processed_data['sources'][processed_data['sources']['include'] == 1])
                multi_output = 0
                for _, row in processed_data['sources'].iterrows():
                    if row.get('include', 0) == 1:
                        buses = self._parse_bus_string(row.get('output_bus', row.get('bus', '')))
                        if len(buses) > 1:
                            multi_output += 1
                summary['Sources'] = f"{active_sources} aktiv" + (f" ({multi_output} Multi-Output)" if multi_output > 0 else "")
            
            # Sinks
            if 'sinks' in processed_data and not processed_data['sinks'].empty:
                active_sinks = len(processed_data['sinks'][processed_data['sinks']['include'] == 1])
                multi_input = 0
                for _, row in processed_data['sinks'].iterrows():
                    if row.get('include', 0) == 1:
                        buses = self._parse_bus_string(row.get('input_bus', row.get('bus', '')))
                        if len(buses) > 1:
                            multi_input += 1
                summary['Sinks'] = f"{active_sinks} aktiv" + (f" ({multi_input} Multi-Input)" if multi_input > 0 else "")
            
            # Transformers
            if 'simple_transformers' in processed_data and not processed_data['simple_transformers'].empty:
                active_transformers = len(processed_data['simple_transformers'][processed_data['simple_transformers']['include'] == 1])
                multi_io = 0
                for _, row in processed_data['simple_transformers'].iterrows():
                    if row.get('include', 0) == 1:
                        input_buses = self._parse_bus_string(row.get('input_bus', ''))
                        output_buses = self._parse_bus_string(row.get('output_bus', ''))
                        if len(input_buses) > 1 or len(output_buses) > 1:
                            multi_io += 1
                summary['Transformers'] = f"{active_transformers} aktiv" + (f" ({multi_io} Multi-IO)" if multi_io > 0 else "")
            
            # Timeseries
            if 'timeseries' in processed_data and not processed_data['timeseries'].empty:
                profile_count = len(processed_data['timeseries'].columns) - 1  # Minus timestamp
                summary['Zeitreihen'] = f"{len(processed_data['timeseries'])} Zeitschritte, {profile_count} Profile"
            
            # Investment-Komponenten
            investment_count = 0
            for sheet_name in ['sources', 'sinks', 'simple_transformers']:
                if sheet_name in processed_data and not processed_data[sheet_name].empty:
                    df = processed_data[sheet_name]
                    if 'investment' in df.columns and 'include' in df.columns:
                        investment_count += len(df[
                            (df['include'] == 1) & 
                            (df['investment'] == 1)
                        ])
            
            if investment_count > 0:
                summary['Investment'] = f"{investment_count} Komponenten"
                
        except Exception as e:
            self.logger.warning(f"Fehler bei Zusammenfassung: {e}")
            summary['Hinweis'] = "Teilweise Zusammenfassung aufgrund von Fehlern"
        
        return summary
    
    def _get_required_columns(self) -> Dict[str, List[str]]:
        """Gibt erforderliche Spalten für jeden Sheet-Typ zurück."""
        return {
            'settings': ['Parameter', 'Value'],
            'buses': ['label', 'include'],
            'sources': ['label', 'include'],
            'sinks': ['label', 'include'],
            'simple_transformers': ['label', 'include'],
            'timeseries': ['timestamp']
        }
    
    def _get_optional_columns(self) -> Dict[str, List[str]]:
        """Gibt optionale Spalten für jeden Sheet-Typ zurück."""
        return {
            'buses': ['description'],
            'sources': [
                'bus', 'output_bus',  # Flexibilität für bestehende Dateien
                'nominal_capacity', 'existing',  # Backward-Kompatibilität
                'variable_costs', 'profile_column',
                'investment', 'investment_costs', 'invest_min', 'invest_max',
                'lifetime', 'interest_rate', 'description', 'output_conversion_factors'
            ],
            'sinks': [
                'bus', 'input_bus',  # Flexibilität für bestehende Dateien
                'nominal_capacity', 'existing',  # Backward-Kompatibilität
                'variable_costs', 'profile_column',
                'investment', 'investment_costs', 'invest_min', 'invest_max',
                'lifetime', 'interest_rate', 'description'
            ],
            'simple_transformers': [
                'input_bus', 'output_bus',
                'conversion_factor', 'input_conversion_factors', 'output_conversion_factors',
                'nominal_capacity', 'existing',  # Backward-Kompatibilität
                'variable_costs', 'profile_column',
                'investment', 'investment_costs', 'invest_min', 'invest_max',
                'lifetime', 'interest_rate', 'description'
            ],
            'timestep_settings': ['Parameter', 'Value', 'Description']
        }
    
    def _process_settings_sheet(self, excel_data: pd.ExcelFile) -> Dict[str, Any]:
        """Verarbeitet das Settings-Sheet."""
        if 'settings' not in excel_data.sheet_names:
            self.logger.warning("Settings-Sheet nicht gefunden - verwende Standardwerte")
            return self._get_default_settings()
        
        try:
            settings_df = pd.read_excel(excel_data, sheet_name='settings')
            
            # Parameter-Dictionary erstellen
            settings_dict = {}
            for _, row in settings_df.iterrows():
                parameter = str(row['Parameter']).strip()
                value = row['Value']
                
                # Typ-Konvertierung
                if parameter in ['timeindex_periods']:
                    value = int(value)
                elif parameter in ['timeindex_start', 'timeindex_freq', 'solver']:
                    value = str(value)
                
                settings_dict[parameter] = value
            
            self.logger.debug(f"Settings geladen: {len(settings_dict)} Parameter")
            return settings_dict
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verarbeiten des Settings-Sheets: {e}")
            return self._get_default_settings()
    
    def _process_timestep_settings_sheet(self, excel_data: pd.ExcelFile) -> Dict[str, Any]:
        """Verarbeitet das Timestep-Settings-Sheet."""
        if 'timestep_settings' not in excel_data.sheet_names:
            self.logger.info("Timestep-Settings-Sheet nicht gefunden - verwende Standardwerte")
            return self._get_default_timestep_settings()
        
        try:
            timestep_df = pd.read_excel(excel_data, sheet_name='timestep_settings')
            
            # Parameter-Dictionary erstellen
            timestep_dict = {}
            for _, row in timestep_df.iterrows():
                parameter = str(row['Parameter']).strip()
                value = row['Value']
                
                # Typ-Konvertierung
                if parameter == 'enabled':
                    value = str(value).lower() in ['true', '1', 'yes', 'ja']
                elif parameter in ['averaging_hours', 'sampling_n_factor']:
                    value = int(value)
                
                timestep_dict[parameter] = value
            
            self.logger.debug(f"Timestep-Settings geladen: {len(timestep_dict)} Parameter")
            return timestep_dict
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verarbeiten des Timestep-Settings-Sheets: {e}")
            return self._get_default_timestep_settings()
    
    def _process_buses_sheet(self, excel_data: pd.ExcelFile) -> pd.DataFrame:
        """Verarbeitet das Buses-Sheet."""
        if 'buses' not in excel_data.sheet_names:
            self.logger.error("Buses-Sheet nicht gefunden!")
            raise ValueError("Buses-Sheet ist erforderlich")
        
        buses_df = pd.read_excel(excel_data, sheet_name='buses')
        
        # Datenbereinigung
        buses_df = self._clean_dataframe(buses_df)
        
        self.logger.debug(f"Buses geladen: {len(buses_df[buses_df['include'] == 1])} von {len(buses_df)} aktiviert")
        return buses_df
    
    def _process_sources_sheet(self, excel_data: pd.ExcelFile) -> pd.DataFrame:
        """Verarbeitet das Sources-Sheet mit Multi-Output-Unterstützung."""
        if 'sources' not in excel_data.sheet_names:
            self.logger.info("Sources-Sheet nicht gefunden")
            return pd.DataFrame()
        
        sources_df = pd.read_excel(excel_data, sheet_name='sources')
        
        # Datenbereinigung
        sources_df = self._clean_dataframe(sources_df)
        
        # Multi-Output-Kompatibilität
        sources_df = self._ensure_bus_compatibility(sources_df, 'output')
        
        # Investment-Parameter verarbeiten
        sources_df = self._process_investment_parameters(sources_df)
        
        self.logger.debug(f"Sources geladen: {len(sources_df[sources_df['include'] == 1])} von {len(sources_df)} aktiviert")
        return sources_df
    
    def _process_sinks_sheet(self, excel_data: pd.ExcelFile) -> pd.DataFrame:
        """Verarbeitet das Sinks-Sheet mit Multi-Input-Unterstützung."""
        if 'sinks' not in excel_data.sheet_names:
            self.logger.info("Sinks-Sheet nicht gefunden")
            return pd.DataFrame()
        
        sinks_df = pd.read_excel(excel_data, sheet_name='sinks')
        
        # Datenbereinigung
        sinks_df = self._clean_dataframe(sinks_df)
        
        # Multi-Input-Kompatibilität
        sinks_df = self._ensure_bus_compatibility(sinks_df, 'input')
        
        # Investment-Parameter verarbeiten
        sinks_df = self._process_investment_parameters(sinks_df)
        
        self.logger.debug(f"Sinks geladen: {len(sinks_df[sinks_df['include'] == 1])} von {len(sinks_df)} aktiviert")
        return sinks_df
    
    def _process_transformers_sheet(self, excel_data: pd.ExcelFile) -> pd.DataFrame:
        """Verarbeitet das Transformers-Sheet mit Multi-IO-Unterstützung."""
        if 'simple_transformers' not in excel_data.sheet_names:
            self.logger.info("Simple-Transformers-Sheet nicht gefunden")
            return pd.DataFrame()
        
        transformers_df = pd.read_excel(excel_data, sheet_name='simple_transformers')
        
        # Datenbereinigung
        transformers_df = self._clean_dataframe(transformers_df)
        
        # Investment-Parameter verarbeiten
        transformers_df = self._process_investment_parameters(transformers_df)
        
        self.logger.debug(f"Transformers geladen: {len(transformers_df[transformers_df['include'] == 1])} von {len(transformers_df)} aktiviert")
        return transformers_df
    
    def _process_timeseries_sheet(self, excel_data: pd.ExcelFile) -> pd.DataFrame:
        """Verarbeitet das Timeseries-Sheet."""
        if 'timeseries' not in excel_data.sheet_names:
            self.logger.warning("Timeseries-Sheet nicht gefunden")
            return pd.DataFrame()
        
        timeseries_df = pd.read_excel(excel_data, sheet_name='timeseries')
        
        # Timestamp-Spalte zu DateTime konvertieren
        if 'timestamp' in timeseries_df.columns:
            timeseries_df['timestamp'] = pd.to_datetime(timeseries_df['timestamp'])
        
        self.logger.debug(f"Timeseries geladen: {len(timeseries_df)} Zeitschritte, {len(timeseries_df.columns)-1} Profile")
        return timeseries_df
    
    def _ensure_bus_compatibility(self, df: pd.DataFrame, direction: str) -> pd.DataFrame:
        """
        Stellt Kompatibilität zwischen 'bus' und 'input_bus'/'output_bus' Spalten her.
        
        Args:
            df: DataFrame
            direction: 'input' oder 'output'
            
        Returns:
            DataFrame mit konsistenten Bus-Spalten
        """
        bus_column = f"{direction}_bus"
        
        # Wenn neue Spalte nicht vorhanden, aber 'bus' vorhanden: kopieren
        if bus_column not in df.columns and 'bus' in df.columns:
            df[bus_column] = df['bus']
            self.logger.debug(f"Kopiere 'bus' → '{bus_column}' für Backward-Kompatibilität")
        
        # Wenn neue Spalte vorhanden, aber 'bus' leer: kopieren
        elif bus_column in df.columns and 'bus' in df.columns:
            # Für leere 'bus'-Einträge: von neuer Spalte kopieren
            mask = df['bus'].isna() | (df['bus'] == '')
            df.loc[mask, 'bus'] = df.loc[mask, bus_column]
        
        return df
    
    def _parse_bus_string(self, bus_string: str) -> List[str]:
        """
        Parst Bus-String mit Trennzeichen.
        
        Args:
            bus_string: "el_bus|heat_bus" oder "el_bus"
            
        Returns:
            Liste der Bus-Namen
        """
        if not bus_string or pd.isna(bus_string):
            return []
        
        bus_str = str(bus_string).strip()
        
        if self.bus_separator in bus_str:
            bus_list = [bus.strip() for bus in bus_str.split(self.bus_separator)]
            return [bus for bus in bus_list if bus]
        else:
            return [bus_str] if bus_str else []
    
    def _process_investment_parameters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Verarbeitet Investment-Parameter mit verbesserter Validierung.
        
        Args:
            df: DataFrame mit Investment-Parametern
            
        Returns:
            DataFrame mit verarbeiteten Investment-Parametern
        """
        # Fehlende Investment-Spalten hinzufügen
        investment_columns = ['investment', 'investment_costs', 'existing', 'invest_min', 'invest_max', 'lifetime', 'interest_rate']
        
        for col in investment_columns:
            if col not in df.columns:
                df[col] = np.nan
        
        # Standard-Werte setzen
        df['investment'] = df['investment'].fillna(0)
        df['existing'] = df['existing'].fillna(0)
        df['invest_min'] = df['invest_min'].fillna(0)
        df['invest_max'] = df['invest_max'].fillna(500)  # Standard-Maximum
        
        # Backward-Kompatibilität: nominal_capacity → existing
        if 'nominal_capacity' in df.columns:
            # Wo existing leer ist, aber nominal_capacity vorhanden
            mask = (df['existing'].isna() | (df['existing'] == 0)) & df['nominal_capacity'].notna()
            df.loc[mask, 'existing'] = df.loc[mask, 'nominal_capacity']
            self.logger.debug("Backward-Kompatibilität: nominal_capacity → existing")
        
        return df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Bereinigt DataFrame von häufigen Problemen.
        
        Args:
            df: DataFrame
            
        Returns:
            Bereinigtes DataFrame
        """
        # Leere Zeilen entfernen
        df = df.dropna(how='all')
        
        # String-Spalten trimmen
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            # 'nan' strings zurück zu NaN
            df[col] = df[col].replace('nan', np.nan)
        
        # Include-Spalte sicherstellen
        if 'include' in df.columns:
            df['include'] = df['include'].fillna(0)
            df['include'] = df['include'].astype(int)
        
        return df
    
    def _validate_processed_data(self, processed_data: Dict[str, Any]):
        """
        Validiert die verarbeiteten Daten auf Konsistenz.
        
        Args:
            processed_data: Dictionary mit verarbeiteten Daten
        """
        # Einfache Validierung - nur prüfen ob Busse vorhanden
        if processed_data['buses'].empty:
            raise ValueError("Keine Busse definiert")
        
        self.logger.debug("Daten-Validierung erfolgreich")
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Gibt Standard-Settings zurück."""
        return {
            'timeindex_start': '2025-01-01',
            'timeindex_periods': 8760,
            'timeindex_freq': 'h',
            'solver': 'cbc'
        }
    
    def _get_default_timestep_settings(self) -> Dict[str, Any]:
        """Gibt Standard-Timestep-Settings zurück."""
        return {
            'enabled': False,
            'timestep_strategy': 'full',
            'averaging_hours': 24,
            'sampling_n_factor': 4,
            'time_range_start': '2025-01-01 00:00',
            'time_range_end': '2025-12-31 23:00',
            'create_visualization': True
        }


# Alias für Backward-Kompatibilität
MultiIOExcelReader = ExcelReader


# Test-Funktion
def test_excel_reader():
    """Test-Funktion für den Excel-Reader."""
    settings = {'debug_mode': True}
    reader = ExcelReader(settings)
    
    # Test Bus-Parsing
    test_cases = [
        ("el_bus", ["el_bus"]),
        ("el_bus|heat_bus", ["el_bus", "heat_bus"]),
        ("", [])
    ]
    
    print("🧪 Teste Bus-Parsing:")
    for input_str, expected in test_cases:
        result = reader._parse_bus_string(input_str)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{input_str}' → {result}")
    
    print("✅ Excel-Reader Tests abgeschlossen!")


if __name__ == "__main__":
    test_excel_reader()
