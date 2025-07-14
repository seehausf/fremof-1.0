#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Excel-Datenimport Modul
========================================

Liest Excel-Dateien mit Energiesystemdefinitionen ein und validiert die Daten.
Unterstützt verschiedene Sheets für Komponenten, Zeitreihen und Einstellungen.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime


class ExcelReader:
    """Klasse für das Einlesen und Validieren von Excel-Projektdateien."""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Excel-Reader.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Erwartete Sheets
        self.required_sheets = ['buses', 'sources', 'sinks', 'simple_transformers']
        self.optional_sheets = ['settings', 'timeseries', 'storages', 'links', 'complex_components']
        
        # Datencontainer
        self.excel_data = {}
        self.validation_errors = []
        self.validation_warnings = []
    
    def read_project_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Liest eine Excel-Projektdatei vollständig ein.
        
        Args:
            file_path: Pfad zur Excel-Datei
            
        Returns:
            Dictionary mit allen eingelesenen Daten
        """
        self.logger.info(f"📊 Lese Excel-Datei: {file_path.name}")
        
        try:
            # Excel-Datei öffnen und verfügbare Sheets prüfen
            xl_file = pd.ExcelFile(file_path)
            available_sheets = xl_file.sheet_names
            
            self.logger.info(f"   📋 Verfügbare Sheets: {', '.join(available_sheets)}")
            
            # Sheets einlesen
            self.excel_data = {}
            
            # Required Sheets
            for sheet in self.required_sheets:
                if sheet in available_sheets:
                    self.excel_data[sheet] = self._read_sheet(xl_file, sheet)
                    self.logger.info(f"   ✅ {sheet}: {len(self.excel_data[sheet])} Einträge")
                else:
                    self.validation_errors.append(f"Erforderliches Sheet '{sheet}' fehlt")
            
            # Optional Sheets
            for sheet in self.optional_sheets:
                if sheet in available_sheets:
                    self.excel_data[sheet] = self._read_sheet(xl_file, sheet)
                    self.logger.info(f"   📄 {sheet}: {len(self.excel_data[sheet])} Einträge")
            
            # Validierung durchführen
            self._validate_data()
            
            # Daten aufbereiten
            self._process_data()
            
            if self.validation_errors:
                error_msg = f"Validierungsfehler: {'; '.join(self.validation_errors)}"
                raise ValueError(error_msg)
            
            if self.validation_warnings:
                for warning in self.validation_warnings:
                    self.logger.warning(f"⚠️  {warning}")
            
            self.logger.info("✅ Excel-Datei erfolgreich eingelesen und validiert")
            return self.excel_data
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Einlesen der Excel-Datei: {e}")
            raise
    
    def _read_sheet(self, xl_file: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
        """
        Liest ein einzelnes Sheet ein und bereinigt die Daten.
        
        Args:
            xl_file: Excel-File-Objekt
            sheet_name: Name des Sheets
            
        Returns:
            Bereinigte DataFrame
        """
        try:
            df = pd.read_excel(xl_file, sheet_name=sheet_name)
            
            # Spalten bereinigen (Leerzeichen entfernen)
            df.columns = df.columns.str.strip()
            
            # Leere Zeilen entfernen
            df = df.dropna(how='all')
            
            # String-Spalten bereinigen
            string_cols = df.select_dtypes(include=['object']).columns
            for col in string_cols:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', np.nan)
                df[col] = df[col].replace('', np.nan)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Einlesen von Sheet '{sheet_name}': {e}")
            raise
    
    def _validate_data(self):
        """Validiert die eingelesenen Daten."""
        self.logger.info("🔍 Validiere Daten...")
        
        # Buses validieren
        self._validate_buses()
        
        # Sources validieren
        self._validate_sources()
        
        # Sinks validieren
        self._validate_sinks()
        
        # Simple Transformers validieren
        self._validate_simple_transformers()
        
        # Zeitreihen validieren (falls vorhanden)
        if 'timeseries' in self.excel_data:
            self._validate_timeseries()
        
        # Settings validieren (falls vorhanden)
        if 'settings' in self.excel_data:
            self._validate_settings()
    
    def _validate_buses(self):
        """Validiert die Bus-Definitionen."""
        if 'buses' not in self.excel_data:
            self.validation_errors.append("Buses Sheet fehlt")
            return
        
        buses_df = self.excel_data['buses']
        required_cols = ['label', 'include']
        
        # Erforderliche Spalten prüfen
        missing_cols = [col for col in required_cols if col not in buses_df.columns]
        if missing_cols:
            self.validation_errors.append(f"Buses: Fehlende Spalten: {missing_cols}")
        
        # Nur aktive Buses berücksichtigen
        active_buses = buses_df[buses_df['include'] == 1]
        
        if len(active_buses) == 0:
            self.validation_errors.append("Keine aktiven Buses definiert")
        
        # Eindeutige Labels prüfen
        if len(active_buses['label'].unique()) != len(active_buses):
            self.validation_errors.append("Buses: Doppelte Labels gefunden")
        
        # Bus-Labels für spätere Validierung speichern
        self.valid_bus_labels = set(active_buses['label'].values)
    
    def _validate_sources(self):
        """Validiert die Source-Definitionen."""
        if 'sources' not in self.excel_data:
            self.validation_errors.append("Sources Sheet fehlt")
            return
        
        sources_df = self.excel_data['sources']
        required_cols = ['label', 'include', 'bus']
        
        # Erforderliche Spalten prüfen
        missing_cols = [col for col in required_cols if col not in sources_df.columns]
        if missing_cols:
            self.validation_errors.append(f"Sources: Fehlende Spalten: {missing_cols}")
            return
        
        # Nur aktive Sources berücksichtigen
        active_sources = sources_df[sources_df['include'] == 1]
        
        # Bus-Referenzen prüfen
        invalid_buses = []
        for _, source in active_sources.iterrows():
            if hasattr(self, 'valid_bus_labels') and source['bus'] not in self.valid_bus_labels:
                invalid_buses.append(f"{source['label']} -> {source['bus']}")
        
        if invalid_buses:
            self.validation_errors.append(f"Sources: Ungültige Bus-Referenzen: {invalid_buses}")
        
        # Investment-Parameter prüfen
        self._validate_investment_parameters(active_sources, 'Sources')
    
    def _validate_sinks(self):
        """Validiert die Sink-Definitionen."""
        if 'sinks' not in self.excel_data:
            self.validation_errors.append("Sinks Sheet fehlt")
            return
        
        sinks_df = self.excel_data['sinks']
        required_cols = ['label', 'include', 'bus']
        
        # Erforderliche Spalten prüfen
        missing_cols = [col for col in required_cols if col not in sinks_df.columns]
        if missing_cols:
            self.validation_errors.append(f"Sinks: Fehlende Spalten: {missing_cols}")
            return
        
        # Nur aktive Sinks berücksichtigen
        active_sinks = sinks_df[sinks_df['include'] == 1]
        
        # Bus-Referenzen prüfen
        invalid_buses = []
        for _, sink in active_sinks.iterrows():
            if hasattr(self, 'valid_bus_labels') and sink['bus'] not in self.valid_bus_labels:
                invalid_buses.append(f"{sink['label']} -> {sink['bus']}")
        
        if invalid_buses:
            self.validation_errors.append(f"Sinks: Ungültige Bus-Referenzen: {invalid_buses}")
    
    def _validate_simple_transformers(self):
        """Validiert die Simple Transformer-Definitionen."""
        if 'simple_transformers' not in self.excel_data:
            return  # Optional
        
        transformers_df = self.excel_data['simple_transformers']
        
        if len(transformers_df) == 0:
            return  # Leer ist OK
        
        required_cols = ['label', 'include', 'input_bus', 'output_bus', 'conversion_factor']
        
        # Erforderliche Spalten prüfen
        missing_cols = [col for col in required_cols if col not in transformers_df.columns]
        if missing_cols:
            self.validation_errors.append(f"Simple Transformers: Fehlende Spalten: {missing_cols}")
            return
        
        # Nur aktive Transformers berücksichtigen
        active_transformers = transformers_df[transformers_df['include'] == 1]
        
        # Bus-Referenzen prüfen
        invalid_buses = []
        for _, transformer in active_transformers.iterrows():
            if hasattr(self, 'valid_bus_labels'):
                if transformer['input_bus'] not in self.valid_bus_labels:
                    invalid_buses.append(f"{transformer['label']} input -> {transformer['input_bus']}")
                if transformer['output_bus'] not in self.valid_bus_labels:
                    invalid_buses.append(f"{transformer['label']} output -> {transformer['output_bus']}")
        
        if invalid_buses:
            self.validation_errors.append(f"Transformers: Ungültige Bus-Referenzen: {invalid_buses}")
        
        # Conversion Factor prüfen
        invalid_factors = []
        for _, transformer in active_transformers.iterrows():
            try:
                factor = float(transformer['conversion_factor'])
                if factor <= 0 or factor > 2:  # Warnung bei unplausiblen Werten
                    self.validation_warnings.append(
                        f"Transformer '{transformer['label']}': Unplausible Conversion Factor {factor}"
                    )
            except (ValueError, TypeError):
                invalid_factors.append(transformer['label'])
        
        if invalid_factors:
            self.validation_errors.append(f"Transformers: Ungültige Conversion Factors: {invalid_factors}")
        
        # Investment-Parameter prüfen
        self._validate_investment_parameters(active_transformers, 'Transformers')
    
    def _validate_investment_parameters(self, df: pd.DataFrame, component_type: str):
        """Validiert Investment-Parameter für Komponenten."""
        if 'nominal_capacity' not in df.columns:
            return
        
        investment_components = df[df['nominal_capacity'].astype(str).str.upper() == 'INVEST']
        
        for _, comp in investment_components.iterrows():
            comp_name = comp['label']
            
            # Investment_costs prüfen
            if 'investment_costs' in df.columns:
                try:
                    inv_costs = float(comp.get('investment_costs', 0))
                    if inv_costs <= 0:
                        self.validation_warnings.append(
                            f"{component_type} '{comp_name}': Investment ohne Kosten definiert"
                        )
                except (ValueError, TypeError):
                    self.validation_errors.append(
                        f"{component_type} '{comp_name}': Ungültige Investment-Kosten"
                    )
            
            # Min/Max Investment prüfen
            if 'invest_min' in df.columns and 'invest_max' in df.columns:
                try:
                    min_val = float(comp.get('invest_min', 0))
                    max_val = float(comp.get('invest_max', np.inf))
                    
                    if min_val < 0:
                        self.validation_errors.append(
                            f"{component_type} '{comp_name}': Negativer Mindest-Investment"
                        )
                    
                    if max_val <= min_val:
                        self.validation_errors.append(
                            f"{component_type} '{comp_name}': Max-Investment <= Min-Investment"
                        )
                        
                except (ValueError, TypeError):
                    self.validation_errors.append(
                        f"{component_type} '{comp_name}': Ungültige Investment-Grenzen"
                    )
    
    def _validate_timeseries(self):
        """Validiert die Zeitreihen-Daten."""
        timeseries_df = self.excel_data['timeseries']
        
        if 'timestamp' not in timeseries_df.columns:
            self.validation_errors.append("Timeseries: 'timestamp' Spalte fehlt")
            return
        
        # Timestamp-Spalte konvertieren
        try:
            timeseries_df['timestamp'] = pd.to_datetime(timeseries_df['timestamp'])
        except Exception:
            self.validation_errors.append("Timeseries: Ungültige Zeitstempel")
            return
        
        # Auf Duplikate prüfen
        if timeseries_df['timestamp'].duplicated().any():
            self.validation_errors.append("Timeseries: Doppelte Zeitstempel gefunden")
        
        # Auf Lücken prüfen (nur Warnung)
        time_diff = timeseries_df['timestamp'].diff()
        if len(time_diff.unique()) > 2:  # Mehr als NaT und ein Intervall
            self.validation_warnings.append("Timeseries: Unregelmäßige Zeitintervalle erkannt")
        
        # Profile-Spalten prüfen
        profile_columns = [col for col in timeseries_df.columns if col != 'timestamp']
        
        for col in profile_columns:
            # Negative Werte prüfen (nur Warnung für manche Profile)
            if timeseries_df[col].min() < 0 and not col.endswith('_demand'):
                self.validation_warnings.append(f"Timeseries: Negative Werte in '{col}'")
            
            # NaN-Werte prüfen
            nan_count = timeseries_df[col].isna().sum()
            if nan_count > 0:
                self.validation_warnings.append(f"Timeseries: {nan_count} fehlende Werte in '{col}'")
    
    def _validate_settings(self):
        """Validiert die Settings."""
        settings_df = self.excel_data['settings']
        
        if 'Parameter' not in settings_df.columns or 'Value' not in settings_df.columns:
            self.validation_warnings.append("Settings: Erwartete Spalten 'Parameter' und 'Value'")
            return
        
        # Wichtige Parameter prüfen
        params = dict(zip(settings_df['Parameter'], settings_df['Value']))
        
        if 'solver' in params:
            valid_solvers = ['cbc', 'glpk', 'gurobi', 'cplex']
            if params['solver'] not in valid_solvers:
                self.validation_warnings.append(f"Settings: Unbekannter Solver '{params['solver']}'")
    
    def _process_data(self):
        """Bereitet die Daten für die weitere Verarbeitung auf."""
        self.logger.info("🔧 Bereite Daten auf...")
        
        # Nur aktive Komponenten behalten
        for sheet in ['buses', 'sources', 'sinks', 'simple_transformers']:
            if sheet in self.excel_data:
                df = self.excel_data[sheet]
                if 'include' in df.columns:
                    self.excel_data[sheet] = df[df['include'] == 1].copy()
        
        # Investment-Parameter verarbeiten
        self._process_investment_data()
        
        # Profile-Referenzen auflösen
        self._process_profile_references()
        
        # Zeitindex erstellen/validieren
        self._process_timeindex()
    
    def _process_investment_data(self):
        """Verarbeitet Investment-Definitionen."""
        for sheet in ['sources', 'sinks', 'simple_transformers']:
            if sheet not in self.excel_data:
                continue
            
            df = self.excel_data[sheet]
            if 'nominal_capacity' not in df.columns:
                continue
            
            # Investment-Flag hinzufügen
            df['is_investment'] = df['nominal_capacity'].astype(str).str.upper() == 'INVEST'
            
            # Investment-Parameter standardisieren
            investment_cols = ['investment_costs', 'invest_min', 'invest_max']
            for col in investment_cols:
                if col not in df.columns:
                    df[col] = np.nan
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
    
    def _process_profile_references(self):
        """Löst Referenzen zu Zeitreihen-Profilen auf."""
        if 'timeseries' not in self.excel_data:
            return
        
        timeseries_df = self.excel_data['timeseries']
        available_profiles = [col for col in timeseries_df.columns if col != 'timestamp']
        
        # Profile-Referenzen in Sources und Sinks prüfen
        for sheet in ['sources', 'sinks']:
            if sheet not in self.excel_data:
                continue
            
            df = self.excel_data[sheet]
            
            # Profile-Spalten suchen
            profile_cols = [col for col in df.columns if 'profile' in col.lower()]
            
            for col in profile_cols:
                for idx, profile_ref in df[col].items():
                    if pd.notna(profile_ref) and profile_ref != '':
                        if profile_ref not in available_profiles:
                            self.validation_warnings.append(
                                f"{sheet.title()}: Profil '{profile_ref}' nicht in Zeitreihen gefunden"
                            )
    
    def _process_timeindex(self):
        """Erstellt oder validiert den Zeitindex."""
        if 'timeseries' in self.excel_data:
            # Zeitindex aus Zeitreihen-Daten
            timeseries_df = self.excel_data['timeseries']
            
            # Sicherstellen, dass timestamp eine DatetimeIndex ist
            if 'timestamp' in timeseries_df.columns:
                timestamps = pd.to_datetime(timeseries_df['timestamp'])
                
                # Als DatetimeIndex erstellen, nicht als Series
                if isinstance(timestamps, pd.Series):
                    timeindex = pd.DatetimeIndex(timestamps)
                else:
                    timeindex = timestamps
                
                # Frequenz ermitteln und explizit setzen
                freq = timeindex.inferred_freq or pd.infer_freq(timeindex)
                
                if freq is None:
                    # Frequenz aus den ersten zwei Zeitpunkten ableiten
                    if len(timeindex) >= 2:
                        time_diff = timeindex[1] - timeindex[0]
                        if time_diff == pd.Timedelta(hours=1):
                            freq = 'h'
                        elif time_diff == pd.Timedelta(minutes=15):
                            freq = '15min'
                        elif time_diff == pd.Timedelta(minutes=30):
                            freq = '30min'
                        elif time_diff == pd.Timedelta(days=1):
                            freq = 'D'
                        else:
                            # Fallback: Versuche die Frequenz aus der Zeitdifferenz zu bestimmen
                            total_seconds = time_diff.total_seconds()
                            if total_seconds == 3600:  # 1 Stunde
                                freq = 'h'
                            elif total_seconds == 900:  # 15 Minuten
                                freq = '15min'
                            elif total_seconds == 1800:  # 30 Minuten
                                freq = '30min'
                            elif total_seconds == 86400:  # 1 Tag
                                freq = 'D'
                
                # DatetimeIndex mit expliziter Frequenz neu erstellen
                if freq is not None:
                    try:
                        timeindex = pd.date_range(
                            start=timeindex[0],
                            periods=len(timeindex),
                            freq=freq
                        )
                    except Exception:
                        # Fallback: Originaler Index ohne Frequenz
                        freq = None
                
                self.excel_data['timeindex'] = timeindex
                self.excel_data['timeindex_info'] = {
                    'start': timeindex.min(),
                    'end': timeindex.max(),
                    'periods': len(timeindex),
                    'freq': freq,
                    'has_freq': freq is not None
                }
                
                if freq is None:
                    self.validation_warnings.append(
                        "Zeitindex-Frequenz konnte nicht ermittelt werden - "
                        "infer_last_interval wird auf False gesetzt"
                    )
                
            else:
                raise ValueError("Timeseries Sheet hat keine 'timestamp' Spalte")
            
        elif 'settings' in self.excel_data:
            # Zeitindex aus Settings erstellen
            settings_df = self.excel_data['settings']
            params = dict(zip(settings_df['Parameter'], settings_df['Value']))
            
            try:
                start = params.get('timeindex_start', '2025-01-01')
                periods = int(params.get('timeindex_periods', 8760))
                freq = params.get('timeindex_freq', 'h')
                
                timeindex = pd.date_range(start=start, periods=periods, freq=freq)
                
                self.excel_data['timeindex'] = timeindex
                self.excel_data['timeindex_info'] = {
                    'start': timeindex[0],
                    'end': timeindex[-1],
                    'periods': periods,
                    'freq': freq,
                    'has_freq': True
                }
                
            except Exception as e:
                self.validation_warnings.append(f"Settings: Fehler beim Erstellen des Zeitindex: {e}")
        
        else:
            # Standard-Zeitindex (1 Jahr, stündlich)
            timeindex = pd.date_range(start='2025-01-01', periods=8760, freq='h')
            
            self.excel_data['timeindex'] = timeindex
            self.excel_data['timeindex_info'] = {
                'start': timeindex[0],
                'end': timeindex[-1],
                'periods': 8760,
                'freq': 'h',
                'has_freq': True
            }
            
            self.validation_warnings.append("Kein Zeitindex definiert - verwende Standard (8760h)")
    
    def get_data_summary(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Erstellt eine Zusammenfassung der eingelesenen Daten.
        
        Args:
            data: Dictionary mit Excel-Daten
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        summary = {}
        
        # Komponenten zählen
        for sheet in ['buses', 'sources', 'sinks', 'simple_transformers']:
            if sheet in data:
                count = len(data[sheet])
                summary[sheet.title()] = f"{count} Komponenten"
        
        # Zeitindex-Info
        if 'timeindex_info' in data:
            info = data['timeindex_info']
            summary['Zeitbereich'] = f"{info['start'].strftime('%Y-%m-%d')} bis {info['end'].strftime('%Y-%m-%d')}"
            summary['Zeitschritte'] = f"{info['periods']} ({info['freq']})"
        
        # Investment-Komponenten
        investment_count = 0
        for sheet in ['sources', 'sinks', 'simple_transformers']:
            if sheet in data and 'is_investment' in data[sheet].columns:
                investment_count += data[sheet]['is_investment'].sum()
        
        if investment_count > 0:
            summary['Investments'] = f"{investment_count} Komponenten"
        
        # Zeitreihen-Profile
        if 'timeseries' in data:
            profile_count = len(data['timeseries'].columns) - 1  # -1 für timestamp
            summary['Profile'] = f"{profile_count} Zeitreihen"
        
        return summary


# Test-Funktionen für Entwicklung
def test_excel_reader():
    """Testfunktion für den Excel-Reader."""
    from pathlib import Path
    
    # Test mit Beispieldatei
    example_file = Path("examples/example_1.xlsx")
    
    if example_file.exists():
        settings = {'debug_mode': True}
        reader = ExcelReader(settings)
        
        try:
            data = reader.read_project_file(example_file)
            summary = reader.get_data_summary(data)
            
            print("✅ Test erfolgreich!")
            print("Zusammenfassung:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
    else:
        print(f"❌ Beispieldatei nicht gefunden: {example_file}")


if __name__ == "__main__":
    # Test ausführen wenn direkt gestartet
    test_excel_reader()
