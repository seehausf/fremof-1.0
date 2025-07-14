#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Timestep-Management-Modul
==========================================

Ermöglicht flexibles Management der Zeitauflösung für Optimierungsmodelle.
Unterstützt Zeitbereich-Auswahl, Mittelwertbildung und Sampling-Strategien.

Features:
1. Zeitbereich-Auswahl: Nur bestimmte Perioden simulieren
2. Mittelwertbildung: 4,6,8,12,24,48 Stunden-Mittelwerte
3. 24n+1 Sampling: Systematisches Sampling basierend auf 24h-Zyklen
4. Automatische Zeitreihen-Anpassung für alle Profile

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import logging
from datetime import datetime, timedelta


class TimestepManager:
    """
    Verwaltet verschiedene Zeitauflösungsstrategien für oemof.solph Modelle.
    
    oemof.solph behandelt Zeitskalierung automatisch:
    - timeincrement wird aus timeindex.freq berechnet
    - Variable Kosten werden automatisch mit timeincrement skaliert
    - Flow-Werte sind Power [kW], werden zu Energie [kWh] umgerechnet
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Timestep-Manager.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Verfügbare Strategien
        self.strategies = {
            'full': self._strategy_full,
            'time_range': self._strategy_time_range, 
            'averaging': self._strategy_averaging,
            'sampling_24n': self._strategy_sampling_24n
        }
        
        # Zeitauflösungs-Statistiken
        self.reduction_stats = {}
    
    def process_timeindex_and_data(self, excel_data: Dict[str, Any], 
                                 strategy: str = 'full',
                                 strategy_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Verarbeitet Zeitindex und Zeitreihen-Daten nach gewählter Strategie.
        
        Args:
            excel_data: Originale Excel-Daten
            strategy: Gewählte Zeitauflösungs-Strategie
            strategy_params: Parameter für die Strategie
            
        Returns:
            Modifizierte Excel-Daten mit angepasstem Zeitindex
        """
        if strategy_params is None:
            strategy_params = {}
        
        self.logger.info(f"🕒 Verarbeite Zeitauflösung mit Strategie: {strategy}")
        
        # Original-Daten kopieren
        processed_data = excel_data.copy()
        
        # Strategie anwenden
        if strategy in self.strategies:
            processed_data = self.strategies[strategy](processed_data, strategy_params)
        else:
            raise ValueError(f"Unbekannte Strategie: {strategy}")
        
        # Statistiken loggen
        self._log_reduction_statistics()
        
        return processed_data
    
    def _strategy_full(self, excel_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Strategie 1: Vollständige Zeitreihe ohne Änderungen."""
        self.logger.info("   📅 Verwende vollständige Zeitreihe")
        
        original_periods = len(excel_data.get('timeindex', []))
        self.reduction_stats = {
            'strategy': 'full',
            'original_periods': original_periods,
            'final_periods': original_periods,
            'reduction_factor': 1.0,
            'time_savings': '0%'
        }
        
        return excel_data
    
    def _strategy_time_range(self, excel_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Strategie 2: Auswahl eines bestimmten Zeitbereichs."""
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        
        if not start_date or not end_date:
            raise ValueError("time_range Strategie benötigt 'start_date' und 'end_date' Parameter")
        
        self.logger.info(f"   📅 Wähle Zeitbereich: {start_date} bis {end_date}")
        
        # Zeitindex beschneiden
        original_timeindex = excel_data.get('timeindex')
        if original_timeindex is None:
            raise ValueError("Kein Zeitindex in Excel-Daten gefunden")
        
        # Zeitbereich-Maske erstellen
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        
        mask = (original_timeindex >= start_ts) & (original_timeindex <= end_ts)
        new_timeindex = original_timeindex[mask]
        
        if len(new_timeindex) == 0:
            raise ValueError(f"Kein Zeitpunkt im Bereich {start_date} bis {end_date} gefunden")
        
        # Zeitreihen-Daten entsprechend beschneiden
        processed_data = excel_data.copy()
        processed_data['timeindex'] = new_timeindex
        
        # Timeseries-Daten anpassen (N-1 Werte für N Zeitpunkte)
        if 'timeseries' in processed_data:
            timeseries_df = processed_data['timeseries'].copy()
            
            # Timestamp-Spalte anpassen 
            if 'timestamp' in timeseries_df.columns:
                ts_mask = (timeseries_df['timestamp'] >= start_ts) & (timeseries_df['timestamp'] < end_ts)
                timeseries_df = timeseries_df[ts_mask].reset_index(drop=True)
                processed_data['timeseries'] = timeseries_df
        
        # Zeitindex-Info aktualisieren
        processed_data['timeindex_info'] = {
            'start': new_timeindex.min(),
            'end': new_timeindex.max(),
            'periods': len(new_timeindex),
            'freq': original_timeindex.freq,
            'has_freq': True
        }
        
        # Statistiken
        original_periods = len(original_timeindex)
        final_periods = len(new_timeindex)
        
        self.reduction_stats = {
            'strategy': 'time_range',
            'original_periods': original_periods,
            'final_periods': final_periods,
            'reduction_factor': final_periods / original_periods,
            'time_savings': f"{((original_periods - final_periods) / original_periods * 100):.1f}%",
            'selected_range': f"{start_date} to {end_date}"
        }
        
        return processed_data
    
    def _strategy_averaging(self, excel_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Strategie 3: Mittelwertbildung über mehrere Stunden."""
        hours = params.get('hours', 4)
        
        if hours not in [4, 6, 8, 12, 24, 48]:
            raise ValueError(f"Averaging-Stunden müssen in [4,6,8,12,24,48] sein, nicht {hours}")
        
        self.logger.info(f"   📅 Bilde {hours}-Stunden-Mittelwerte")
        
        original_timeindex = excel_data.get('timeindex')
        if original_timeindex is None:
            raise ValueError("Kein Zeitindex in Excel-Daten gefunden")
        
        # Prüfe ob Zeitindex stündlich ist
        if not self._is_hourly_timeindex(original_timeindex):
            raise ValueError("Averaging-Strategie benötigt stündlichen Zeitindex")
        
        processed_data = excel_data.copy()
        
        # Neuen Zeitindex erstellen (alle hours Stunden)
        start_time = original_timeindex[0]
        end_time = original_timeindex[-1]
        
        # Neuer Zeitindex mit hours-Stunden-Schritten
        new_timeindex = pd.date_range(
            start=start_time,
            end=end_time,
            freq=f'{hours}h'
        )
        
        processed_data['timeindex'] = new_timeindex
        
        # Zeitreihen-Daten über Intervalle mitteln
        if 'timeseries' in processed_data:
            original_timeseries = processed_data['timeseries'].copy()
            new_timeseries = self._average_timeseries(original_timeseries, hours)
            processed_data['timeseries'] = new_timeseries
        
        # Zeitindex-Info aktualisieren
        processed_data['timeindex_info'] = {
            'start': new_timeindex[0],
            'end': new_timeindex[-1], 
            'periods': len(new_timeindex),
            'freq': f'{hours}h',
            'has_freq': True
        }
        
        # Statistiken
        original_periods = len(original_timeindex)
        final_periods = len(new_timeindex)
        
        self.reduction_stats = {
            'strategy': 'averaging',
            'original_periods': original_periods,
            'final_periods': final_periods,
            'reduction_factor': final_periods / original_periods,
            'time_savings': f"{((original_periods - final_periods) / original_periods * 100):.1f}%",
            'averaging_hours': hours
        }
        
        return processed_data
    
    def _strategy_sampling_24n(self, excel_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Strategie 4: 24n+1 Sampling (n als Vielfaches/Divisor von 24)."""
        n = params.get('n', 1)
        
        # Validiere n-Parameter
        valid_n_values = [1/24, 1/12, 1/8, 1/6, 1/4, 1/3, 1/2, 1, 2, 3, 4, 6, 8, 12, 24]
        if n not in valid_n_values:
            raise ValueError(f"n muss einer von {valid_n_values} sein, nicht {n}")
        
        self.logger.info(f"   📅 Verwende 24n+1 Sampling mit n={n}")
        
        original_timeindex = excel_data.get('timeindex')
        if original_timeindex is None:
            raise ValueError("Kein Zeitindex in Excel-Daten gefunden")
        
        # Prüfe ob Zeitindex stündlich ist
        if not self._is_hourly_timeindex(original_timeindex):
            raise ValueError("24n+1 Sampling benötigt stündlichen Zeitindex")
        
        processed_data = excel_data.copy()
        
        # Sampling-Indices berechnen
        sampling_indices = self._calculate_24n_sampling_indices(original_timeindex, n)
        
        # Neuen Zeitindex erstellen
        new_timeindex = original_timeindex[sampling_indices]
        processed_data['timeindex'] = new_timeindex
        
        # Zeitreihen-Daten entsprechend sampeln
        if 'timeseries' in processed_data:
            original_timeseries = processed_data['timeseries'].copy()
            new_timeseries = self._sample_timeseries(original_timeseries, sampling_indices)
            processed_data['timeseries'] = new_timeseries
        
        # Zeitindex-Info aktualisieren
        processed_data['timeindex_info'] = {
            'start': new_timeindex[0],
            'end': new_timeindex[-1],
            'periods': len(new_timeindex),
            'freq': None,  # Unregelmäßiges Sampling
            'has_freq': False
        }
        
        # Statistiken
        original_periods = len(original_timeindex)
        final_periods = len(new_timeindex)
        
        self.reduction_stats = {
            'strategy': 'sampling_24n',
            'original_periods': original_periods,
            'final_periods': final_periods,
            'reduction_factor': final_periods / original_periods,
            'time_savings': f"{((original_periods - final_periods) / original_periods * 100):.1f}%",
            'n_factor': n,
            'sampling_pattern': self._describe_sampling_pattern(n)
        }
        
        return processed_data
    
    def _is_hourly_timeindex(self, timeindex: pd.DatetimeIndex) -> bool:
        """Prüft ob ein Zeitindex stündlich ist."""
        try:
            freq = timeindex.freq
            if freq is None:
                freq = pd.infer_freq(timeindex)
            return freq is not None and 'h' in str(freq) and '1h' in str(freq)
        except:
            return False
    
    def _average_timeseries(self, timeseries_df: pd.DataFrame, hours: int) -> pd.DataFrame:
        """Mittelt Zeitreihen-Daten über gegebene Stunden-Intervalle."""
        
        if 'timestamp' not in timeseries_df.columns:
            raise ValueError("Zeitreihen-DataFrame muss 'timestamp' Spalte haben")
        
        # Grouping-Variable erstellen (Stunden-Gruppen)
        timeseries_df = timeseries_df.copy()
        timeseries_df['hour_group'] = (timeseries_df.index // hours) * hours
        
        # Profile-Spalten identifizieren
        profile_columns = [col for col in timeseries_df.columns if col not in ['timestamp', 'hour_group']]
        
        # Mittelwerte für jede Gruppe berechnen
        averaged_data = []
        
        for group_start in range(0, len(timeseries_df), hours):
            group_end = min(group_start + hours, len(timeseries_df))
            group_data = timeseries_df.iloc[group_start:group_end]
            
            if len(group_data) == 0:
                continue
            
            # Zeitstempel: Beginn der Gruppe
            new_timestamp = group_data['timestamp'].iloc[0]
            
            # Mittelwerte berechnen
            averaged_row = {'timestamp': new_timestamp}
            
            for col in profile_columns:
                # Für Preise und Verfügbarkeiten: Einfacher Mittelwert
                if any(keyword in col.lower() for keyword in ['price', 'cost', 'availability', 'profile']):
                    averaged_row[col] = group_data[col].mean()
                # Für Temperatur: Mittelwert (zukünftig)
                elif 'temp' in col.lower():
                    averaged_row[col] = group_data[col].mean()
                else:
                    # Standard: Mittelwert
                    averaged_row[col] = group_data[col].mean()
            
            averaged_data.append(averaged_row)
        
        return pd.DataFrame(averaged_data).reset_index(drop=True)
    
    def _calculate_24n_sampling_indices(self, timeindex: pd.DatetimeIndex, n: float) -> List[int]:
        """Berechnet Sampling-Indices für 24n+1 Muster."""
        
        # Sampling-Abstand in Stunden
        if n >= 1:
            # n >= 1: Jeden n-ten Zeitpunkt nehmen
            step = int(n)
        else:
            # n < 1: Mehrere Punkte pro Stunde
            step = max(1, int(1/n))
        
        indices = []
        
        # Beginne bei Index 0 (erste Stunde)
        for i in range(0, len(timeindex), step):
            indices.append(i)
        
        # Sicherstellen, dass der letzte Zeitpunkt enthalten ist
        if len(timeindex) - 1 not in indices:
            indices.append(len(timeindex) - 1)
        
        return sorted(indices)
    
    def _sample_timeseries(self, timeseries_df: pd.DataFrame, sampling_indices: List[int]) -> pd.DataFrame:
        """Sampelt Zeitreihen-Daten basierend auf gegebenen Indices."""
        
        # Indices auf DataFrame-Länge begrenzen
        valid_indices = [i for i in sampling_indices if i < len(timeseries_df)]
        
        return timeseries_df.iloc[valid_indices].reset_index(drop=True)
    
    def _describe_sampling_pattern(self, n: float) -> str:
        """Beschreibt das Sampling-Muster in verständlicher Form."""
        if n == 1:
            return "Jede Stunde"
        elif n > 1:
            return f"Alle {int(n)} Stunden"
        elif n == 0.5:
            return "Alle 30 Minuten"
        elif n == 1/3:
            return "Alle 20 Minuten"
        elif n == 0.25:
            return "Alle 15 Minuten"
        elif n == 1/6:
            return "Alle 10 Minuten"
        elif n == 1/12:
            return "Alle 5 Minuten"
        else:
            return f"Alle {60/n:.0f} Minuten" if n < 1 else f"Alle {n:.1f} Stunden"
    
    def _log_reduction_statistics(self):
        """Loggt Zeitreduktions-Statistiken."""
        stats = self.reduction_stats
        
        self.logger.info(f"   📊 Zeitreduktions-Statistiken:")
        self.logger.info(f"      Original: {stats['original_periods']:,} Zeitschritte")
        self.logger.info(f"      Final: {stats['final_periods']:,} Zeitschritte")
        self.logger.info(f"      Reduktion: {stats['time_savings']}")
        self.logger.info(f"      Faktor: {stats['reduction_factor']:.3f}")
        
        # Strategie-spezifische Details
        if stats['strategy'] == 'time_range':
            self.logger.info(f"      Zeitbereich: {stats['selected_range']}")
        elif stats['strategy'] == 'averaging':
            self.logger.info(f"      Mittelwert: {stats['averaging_hours']}h-Intervalle")
        elif stats['strategy'] == 'sampling_24n':
            self.logger.info(f"      Sampling: n={stats['n_factor']} ({stats['sampling_pattern']})")
    
    def get_reduction_stats(self) -> Dict[str, Any]:
        """Gibt die Zeitreduktions-Statistiken zurück."""
        return self.reduction_stats.copy()
    
    def estimate_solver_time_reduction(self) -> Dict[str, Any]:
        """Schätzt die Solver-Zeit-Reduktion basierend auf Zeitschritt-Reduktion."""
        if not self.reduction_stats:
            return {}
        
        reduction_factor = self.reduction_stats['reduction_factor']
        
        # Grobe Schätzung: Solver-Zeit skaliert etwa quadratisch mit Zeitschritten
        # für kleine Systeme, linear für große Systeme
        estimated_time_factor = reduction_factor ** 1.5
        
        return {
            'estimated_time_factor': estimated_time_factor,
            'estimated_time_savings': f"{((1 - estimated_time_factor) * 100):.1f}%",
            'complexity_reduction': 'quadratic' if reduction_factor < 0.5 else 'linear'
        }


def create_timestep_settings_sheet() -> pd.DataFrame:
    """Erstellt ein Excel-Sheet für Timestep-Einstellungen."""
    
    timestep_settings = pd.DataFrame({
        'Parameter': [
            'timestep_strategy',
            'time_range_start',
            'time_range_end', 
            'averaging_hours',
            'sampling_n_factor',
            'enabled'
        ],
        'Value': [
            'full',
            '',
            '',
            '4',
            '1',
            'True'
        ],
        'Description': [
            'Strategie: full, time_range, averaging, sampling_24n',
            'Start-Datum für time_range (YYYY-MM-DD HH:MM)',
            'End-Datum für time_range (YYYY-MM-DD HH:MM)',
            'Stunden für averaging (4,6,8,12,24,48)',
            'n-Faktor für sampling_24n (1/24, 1/12, 1/8, 1/6, 1/4, 1/2, 1, 2, 4, 6, 8, 12, 24)',
            'Timestep-Management aktiviert (True/False)'
        ],
        'Examples': [
            'full (keine Änderung)',
            '2025-01-01 00:00',
            '2025-01-31 23:00',
            '6 (6-Stunden-Mittelwerte)',
            '0.5 (alle 30min), 2 (alle 2h)',
            'False (deaktiviert)'
        ]
    })
    
    return timestep_settings


# Integration in Excel-Reader
def integrate_timestep_management_in_excel_reader():
    """
    Code-Snippet zur Integration in excel_reader.py
    
    Fügen Sie diese Methode zur ExcelReader-Klasse hinzu:
    """
    
    integration_code = '''
    def apply_timestep_management(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wendet Timestep-Management auf Excel-Daten an."""
        
        # Prüfe ob Timestep-Settings verfügbar sind
        if 'timestep_settings' not in excel_data:
            return excel_data  # Keine Timestep-Einstellungen
        
        settings_df = excel_data['timestep_settings']
        
        # Parse Timestep-Einstellungen
        timestep_params = {}
        for _, row in settings_df.iterrows():
            param = row['Parameter']
            value = row['Value']
            
            if param == 'enabled' and value.lower() != 'true':
                return excel_data  # Timestep-Management deaktiviert
            
            timestep_params[param] = value
        
        # Timestep-Manager initialisieren
        from modules.timestep_manager import TimestepManager
        
        timestep_manager = TimestepManager(self.settings)
        
        # Strategie und Parameter bestimmen
        strategy = timestep_params.get('timestep_strategy', 'full')
        strategy_params = {}
        
        if strategy == 'time_range':
            strategy_params = {
                'start_date': timestep_params.get('time_range_start'),
                'end_date': timestep_params.get('time_range_end')
            }
        elif strategy == 'averaging':
            strategy_params = {
                'hours': int(timestep_params.get('averaging_hours', 4))
            }
        elif strategy == 'sampling_24n':
            strategy_params = {
                'n': float(timestep_params.get('sampling_n_factor', 1))
            }
        
        # Timestep-Management anwenden
        try:
            processed_data = timestep_manager.process_timeindex_and_data(
                excel_data, strategy, strategy_params
            )
            
            # Statistiken zu Excel-Daten hinzufügen
            processed_data['timestep_reduction_stats'] = timestep_manager.get_reduction_stats()
            processed_data['solver_time_estimate'] = timestep_manager.estimate_solver_time_reduction()
            
            return processed_data
            
        except Exception as e:
            self.logger.warning(f"⚠️  Timestep-Management fehlgeschlagen: {e}")
            return excel_data
    '''
    
    return integration_code


# Test-Funktion
def test_timestep_manager():
    """Testfunktion für den Timestep-Manager."""
    
    # Test-Daten erstellen
    timeindex = pd.date_range('2025-01-01', periods=168, freq='h')  # 1 Woche
    
    timeseries_df = pd.DataFrame({
        'timestamp': timeindex[:-1],  # N-1 Werte für N Zeitpunkte
        'pv_profile': np.random.rand(167) * 0.8,
        'load_profile': np.random.rand(167) * 50 + 20,
        'price_profile': np.random.rand(167) * 0.1 + 0.2
    })
    
    test_excel_data = {
        'timeindex': timeindex,
        'timeseries': timeseries_df,
        'timeindex_info': {
            'start': timeindex[0],
            'end': timeindex[-1],
            'periods': len(timeindex),
            'freq': 'h',
            'has_freq': True
        }
    }
    
    # Timestep-Manager testen
    settings = {'debug_mode': True}
    manager = TimestepManager(settings)
    
    print("🧪 Teste Timestep-Manager...")
    
    # Test 1: Full Strategy
    print("\n1. Test: Full Strategy")
    result1 = manager.process_timeindex_and_data(test_excel_data, 'full')
    stats1 = manager.get_reduction_stats()
    print(f"   Perioden: {stats1['original_periods']} → {stats1['final_periods']}")
    
    # Test 2: Time Range
    print("\n2. Test: Time Range Strategy")
    result2 = manager.process_timeindex_and_data(
        test_excel_data, 
        'time_range', 
        {'start_date': '2025-01-02', 'end_date': '2025-01-04'}
    )
    stats2 = manager.get_reduction_stats()
    print(f"   Perioden: {stats2['original_periods']} → {stats2['final_periods']} ({stats2['time_savings']})")
    
    # Test 3: Averaging
    print("\n3. Test: Averaging Strategy (6h)")
    result3 = manager.process_timeindex_and_data(test_excel_data, 'averaging', {'hours': 6})
    stats3 = manager.get_reduction_stats()
    print(f"   Perioden: {stats3['original_periods']} → {stats3['final_periods']} ({stats3['time_savings']})")
    
    # Test 4: Sampling 24n+1
    print("\n4. Test: Sampling 24n+1 (n=0.5)")
    result4 = manager.process_timeindex_and_data(test_excel_data, 'sampling_24n', {'n': 0.5})
    stats4 = manager.get_reduction_stats()
    print(f"   Perioden: {stats4['original_periods']} → {stats4['final_periods']} ({stats4['time_savings']})")
    print(f"   Muster: {stats4['sampling_pattern']}")
    
    # Solver-Zeit-Schätzung
    print("\n5. Solver-Zeit-Schätzungen:")
    for i, result in enumerate([result1, result2, result3, result4], 1):
        time_estimate = manager.estimate_solver_time_reduction()
        print(f"   Test {i}: {time_estimate.get('estimated_time_savings', 'N/A')}")
    
    print("\n✅ Timestep-Manager Test abgeschlossen!")


if __name__ == "__main__":
    test_timestep_manager()
