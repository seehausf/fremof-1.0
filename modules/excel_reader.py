#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Excel-Datenimport Modul (Korrigiert)
=====================================================

Liest Excel-Dateien mit Energiesystemdefinitionen ein und validiert die Daten.
Unterstützt verschiedene Sheets für Komponenten, Zeitreihen und Einstellungen.

KORRIGIERT: Syntaxfehler im apply_timestep_management behoben.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.1
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
        self.optional_sheets = ['settings', 'timeseries', 'storages', 'links', 
                               'complex_components', 'timestep_settings']
        
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
        
        # Timestep-Settings validieren (falls vorhanden)
        if 'timestep_settings' in self.excel_data:
            self._validate_timestep_settings()
    
    def _validate_timestep_settings(self):
        """Validiert die Timestep-Settings."""
        timestep_df = self.excel_data['timestep_settings']
        
        self.logger.info("🕒 Validiere Timestep-Settings...")
        
        if 'Parameter' not in timestep_df.columns or 'Value' not in timestep_df.columns:
            self.validation_warnings.append("Timestep-Settings: Erwartete Spalten 'Parameter' und 'Value'")
            return
        
        # Parameter zu Dictionary konvertieren
        params = dict(zip(timestep_df['Parameter'], timestep_df['Value']))
        
        # Prüfe ob enabled gesetzt ist
        enabled = params.get('enabled', 'false')
        if str(enabled).lower() in ['true', '1', 'yes', 'ja']:
            self.logger.info("   ✅ Timestep-Management ist aktiviert")
            
            # Strategie prüfen
            strategy = params.get('timestep_strategy', 'full')
            valid_strategies = ['full', 'time_range', 'averaging', 'sampling_24n']
            
            if strategy not in valid_strategies:
                self.validation_warnings.append(
                    f"Timestep-Settings: Unbekannte Strategie '{strategy}'. "
                    f"Gültig: {valid_strategies}"
                )
            else:
                self.logger.info(f"   📋 Strategie: {strategy}")
                
                # Strategie-spezifische Parameter prüfen
                if strategy == 'time_range':
                    if 'start_date' not in params or 'end_date' not in params:
                        self.validation_errors.append(
                            "Timestep-Settings: time_range Strategie benötigt 'start_date' und 'end_date'"
                        )
                
                elif strategy == 'averaging':
                    hours = params.get('hours', 4)
                    try:
                        hours = int(hours)
                        if hours not in [4, 6, 8, 12, 24, 48]:
                            self.validation_warnings.append(
                                f"Timestep-Settings: Averaging hours {hours} nicht empfohlen. "
                                "Empfohlene Werte: 4, 6, 8, 12, 24, 48"
                            )
                    except (ValueError, TypeError):
                        self.validation_errors.append(
                            f"Timestep-Settings: Ungültiger 'hours' Wert: {hours}"
                        )
                
                elif strategy == 'sampling_24n':
                    n = params.get('n', 1)
                    try:
                        n = float(n)
                        valid_n = [1/24, 1/12, 1/8, 1/6, 1/4, 1/3, 1/2, 1, 2, 3, 4, 6, 8, 12, 24]
                        if n not in valid_n:
                            self.validation_warnings.append(
                                f"Timestep-Settings: n-Wert {n} nicht empfohlen. "
                                f"Empfohlene Werte: {valid_n}"
                            )
                    except (ValueError, TypeError):
                        self.validation_errors.append(
                            f"Timestep-Settings: Ungültiger 'n' Wert: {n}"
                        )
        else:
            self.logger.info("   ⏭️  Timestep-Management ist deaktiviert")
    
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
                if factor <= 0 or factor > 2:
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
        if len(time_diff.unique()) > 2:
            self.validation_warnings.append("Timeseries: Unregelmäßige Zeitintervalle erkannt")
        
        # Profile-Spalten prüfen
        profile_columns = [col for col in timeseries_df.columns if col != 'timestamp']
        
        for col in profile_columns:
            # Negative Werte prüfen
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
            
            if 'timestamp' in timeseries_df.columns:
                timestamps = pd.to_datetime(timeseries_df['timestamp'])
                
                if isinstance(timestamps, pd.Series):
                    timeindex = pd.DatetimeIndex(timestamps)
                else:
                    timeindex = timestamps
                
                # Frequenz ermitteln
                freq = timeindex.inferred_freq or pd.infer_freq(timeindex)
                
                if freq is None:
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
                
                if freq is not None:
                    try:
                        timeindex = pd.date_range(
                            start=timeindex[0],
                            periods=len(timeindex),
                            freq=freq
                        )
                    except Exception:
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
                        "Zeitindex-Frequenz konnte nicht ermittelt werden"
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
            # Standard-Zeitindex
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
    
    def process_excel_data(self, file_path: Path) -> Dict[str, Any]:
        """Hauptfunktion: Excel einlesen + Timestep-Management anwenden."""
        
        # Standard Excel-Einlesen
        excel_data = self.read_project_file(file_path)
        
        # Timestep-Management anwenden (falls konfiguriert)
        excel_data = self.apply_timestep_management(excel_data)
        
        return excel_data

# Korrigierte apply_timestep_management Methode in excel_reader.py
# Ersetzen Sie diese Methode in Ihrer excel_reader.py:

    def apply_timestep_management(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wendet Timestep-Management auf Excel-Daten an und erstellt Visualisierung."""
        
        # Prüfe ob Timestep-Settings verfügbar sind
        if 'timestep_settings' not in excel_data:
            self.logger.debug("Kein timestep_settings Sheet gefunden - Timestep-Management übersprungen")
            return excel_data
        
        settings_df = excel_data.get('timestep_settings')
        
        if settings_df is None or settings_df.empty:
            self.logger.debug("timestep_settings Sheet ist leer - Timestep-Management übersprungen")
            return excel_data
        
        # Parse Timestep-Einstellungen
        timestep_params = {}
        try:
            if 'Parameter' in settings_df.columns and 'Value' in settings_df.columns:
                for _, row in settings_df.iterrows():
                    param = row.get('Parameter')
                    value = row.get('Value')
                    
                    if pd.notna(param) and pd.notna(value):
                        timestep_params[str(param).strip()] = value
                        
            elif len(settings_df.columns) >= 2:
                param_col = settings_df.columns[0]
                value_col = settings_df.columns[1]
                
                for _, row in settings_df.iterrows():
                    param = row.get(param_col)
                    value = row.get(value_col)
                    
                    if pd.notna(param) and pd.notna(value):
                        timestep_params[str(param).strip()] = value
            else:
                self.logger.warning("Timestep-Settings haben unerkannte Struktur")
                return excel_data
                
        except Exception as e:
            self.logger.warning(f"Fehler beim Parsen der Timestep-Einstellungen: {e}")
            return excel_data
        
        self.logger.info(f"🕒 Gefundene Timestep-Parameter: {list(timestep_params.keys())}")
        
        # Prüfe ob aktiviert
        enabled_value = timestep_params.get('enabled', 'false')
        enabled_variants = ['true', '1', 'yes', 'ja', 'on', 'aktiv', 'enabled']
        
        if str(enabled_value).lower().strip() not in enabled_variants:
            self.logger.info(f"🕒 Timestep-Management nicht aktiviert (enabled = '{enabled_value}')")
            return excel_data
        
        # ** ORIGINAL DATEN FÜR VERGLEICH SICHERN **
        original_data_for_comparison = {
            'timeindex': excel_data.get('timeindex'),
            'timeseries': excel_data.get('timeseries'),
            'timeindex_info': excel_data.get('timeindex_info')
        }
        
        # Timestep-Manager importieren und anwenden
        try:
            from modules.timestep_manager import TimestepManager
            
            timestep_manager = TimestepManager(self.settings)
            
            # Strategie und Parameter bestimmen
            strategy = timestep_params.get('timestep_strategy', 'full')
            
            # Parameter-Zuordnung
            strategy_params = {}
            
            if strategy == 'time_range':
                strategy_params['start_date'] = timestep_params.get('time_range_start')
                strategy_params['end_date'] = timestep_params.get('time_range_end')
                
                if not strategy_params['start_date'] or not strategy_params['end_date']:
                    self.logger.warning("time_range Strategie benötigt 'time_range_start' und 'time_range_end' Parameter")
                    return excel_data
                    
            elif strategy == 'averaging':
                averaging_hours = timestep_params.get('averaging_hours', 4)
                try:
                    strategy_params['hours'] = int(averaging_hours)
                except (ValueError, TypeError):
                    self.logger.warning(f"Ungültiger averaging_hours Wert: {averaging_hours}, verwende 4")
                    strategy_params['hours'] = 4
                    
            elif strategy == 'sampling_24n':
                sampling_n = timestep_params.get('sampling_n_factor', 1)
                try:
                    strategy_params['n'] = float(sampling_n)
                except (ValueError, TypeError):
                    self.logger.warning(f"Ungültiger sampling_n_factor Wert: {sampling_n}, verwende 1.0")
                    strategy_params['n'] = 1.0
            
            self.logger.info(f"🕒 Strategie '{strategy}' mit Parametern: {strategy_params}")
            
            # Timestep-Management anwenden
            self.logger.info(f"🕒 Wende Timestep-Management an: Strategie '{strategy}'")
            
            processed_data = timestep_manager.process_timeindex_and_data(
                excel_data, strategy, strategy_params
            )
            
            # Statistiken zu Excel-Daten hinzufügen
            processed_data['timestep_reduction_stats'] = timestep_manager.get_reduction_stats()
            processed_data['solver_time_estimate'] = timestep_manager.estimate_solver_time_reduction()
            
            # ** TIMESTEP-VISUALISIERUNG ERSTELLEN **
            # Prüfe ob Visualisierung gewünscht ist
            create_viz = timestep_params.get('create_visualization', 'true')
            viz_enabled = str(create_viz).lower().strip() in ['true', '1', 'yes', 'ja', 'on']
            
            if viz_enabled and strategy != 'full':
                try:
                    from modules.timestep_visualizer import TimestepVisualizer
                    
                    # ** KORRIGIERT: Output-Verzeichnis aus Settings bestimmen **
                    # Das Hauptprogramm setzt das richtige output_dir in den Settings
                    viz_output_dir = self.settings.get('output_dir', Path('.'))
                    if isinstance(viz_output_dir, str):
                        viz_output_dir = Path(viz_output_dir)
                    
                    # Falls output_dir nicht gesetzt ist, versuche es aus project_name zu erstellen
                    if not viz_output_dir or viz_output_dir == Path('.'):
                        project_name = self.settings.get('project_name', 'default')
                        base_output = self.settings.get('base_output_dir', Path('./data/output'))
                        viz_output_dir = Path(base_output) / project_name
                        viz_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.logger.debug(f"🕒 Timestep-Visualisierung Output-Verzeichnis: {viz_output_dir}")
                    
                    # Timestep-Visualizer erstellen
                    timestep_viz = TimestepVisualizer(viz_output_dir, self.settings)
                    
                    if timestep_viz.is_available():
                        self.logger.info("📊 Erstelle Timestep-Management Visualisierung...")
                        
                        viz_files = timestep_viz.create_timestep_comparison(
                            original_data_for_comparison, processed_data
                        )
                        
                        if viz_files:
                            # Dateiliste zu processed_data hinzufügen
                            processed_data['timestep_visualization_files'] = [str(f) for f in viz_files]
                            self.logger.info(f"✅ {len(viz_files)} Timestep-Visualisierungen erstellt in: {viz_output_dir}")
                            
                            # Debug: Einzelne Dateien loggen
                            for viz_file in viz_files:
                                self.logger.debug(f"      📊 {Path(viz_file).name}")
                        else:
                            self.logger.info("📊 Keine Timestep-Visualisierungen erstellt")
                    else:
                        self.logger.info("📊 Timestep-Visualisierung übersprungen (Matplotlib fehlt)")
                        
                except ImportError:
                    self.logger.info("📊 TimestepVisualizer nicht verfügbar")
                except Exception as e:
                    self.logger.warning(f"⚠️  Timestep-Visualisierung fehlgeschlagen: {e}")
                    if self.settings.get('debug_mode', False):
                        import traceback
                        traceback.print_exc()
            
            self.logger.info("✅ Timestep-Management erfolgreich angewendet")
            
            return processed_data
            
        except ImportError as e:
            self.logger.warning(f"TimestepManager konnte nicht importiert werden: {e}")
            return excel_data
        except Exception as e:
            self.logger.warning(f"⚠️  Timestep-Management fehlgeschlagen: {e}")
            if self.settings.get('debug_mode', False):
                import traceback
                traceback.print_exc()
            return excel_data    
        
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
        
        # Timestep-Reduktion (falls angewendet)
        if 'timestep_reduction_stats' in data:
            stats = data['timestep_reduction_stats']
            summary['Zeitreduktion'] = f"{stats.get('time_savings', '0%')}"
        
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
            data = reader.process_excel_data(example_file)
            summary = reader.get_data_summary(data)
            
            print("✅ Test erfolgreich!")
            print("Zusammenfassung:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Beispieldatei nicht gefunden: {example_file}")


def test_timestep_management():
    """Spezifischer Test für Timestep-Management."""
    import tempfile
    import pandas as pd
    
    # Erstelle temporäre Excel-Datei mit timestep_settings
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
            
            # Basis-Komponenten
            buses_df = pd.DataFrame({
                'label': ['el_bus'],
                'include': [1]
            })
            buses_df.to_excel(writer, sheet_name='buses', index=False)
            
            sources_df = pd.DataFrame({
                'label': ['pv_plant'],
                'include': [1],
                'bus': ['el_bus'],
                'nominal_capacity': [100]
            })
            sources_df.to_excel(writer, sheet_name='sources', index=False)
            
            sinks_df = pd.DataFrame({
                'label': ['el_load'],
                'include': [1],
                'bus': ['el_bus']
            })
            sinks_df.to_excel(writer, sheet_name='sinks', index=False)
            
            transformers_df = pd.DataFrame({
                'label': ['dummy_transformer'],
                'include': [0],  # Deaktiviert
                'input_bus': ['el_bus'],
                'output_bus': ['el_bus'],
                'conversion_factor': [1.0]
            })
            transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
            
            # Zeitreihen
            timestamps = pd.date_range('2025-01-01', periods=168, freq='h')  # 1 Woche
            timeseries_df = pd.DataFrame({
                'timestamp': timestamps,
                'pv_profile': [0.5 + 0.5 * np.sin(i * 2 * np.pi / 24) for i in range(168)]
            })
            timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
            
            # Timestep-Settings - VERSCHIEDENE TEST-SZENARIEN
            timestep_df = pd.DataFrame({
                'Parameter': ['enabled', 'timestep_strategy', 'hours'],
                'Value': ['true', 'averaging', 4]
            })
            timestep_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        
        # Test durchführen
        settings = {'debug_mode': True}
        reader = ExcelReader(settings)
        
        try:
            print("🧪 Teste Timestep-Management...")
            data = reader.process_excel_data(Path(tmp_file.name))
            
            original_periods = 168
            final_periods = data['timeindex_info']['periods']
            
            print(f"✅ Test erfolgreich!")
            print(f"Original-Zeitschritte: {original_periods}")
            print(f"Final-Zeitschritte: {final_periods}")
            print(f"Reduktion: {((original_periods - final_periods) / original_periods * 100):.1f}%")
            
            if 'timestep_reduction_stats' in data:
                stats = data['timestep_reduction_stats']
                print(f"Strategie: {stats['strategy']}")
                print(f"Zeitersparnis: {stats['time_savings']}")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Temporäre Datei löschen
            import os
            os.unlink(tmp_file.name)


if __name__ == "__main__":
    print("Excel Reader Tests")
    print("=" * 50)
    test_excel_reader()
    print("\nTimestep Management Tests")
    print("=" * 50)
    test_timestep_management()