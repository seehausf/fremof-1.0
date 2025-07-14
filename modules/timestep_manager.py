#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Timestep-Management-Modul (Kompakte Version)
============================================================

Ermöglicht flexibles Management der Zeitauflösung für Optimierungsmodelle.
Unterstützt Zeitbereich-Auswahl, Mittelwertbildung und Sampling-Strategien.

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
    """Verwaltet verschiedene Zeitauflösungsstrategien für oemof.solph Modelle."""
    
    def __init__(self, settings: Dict[str, Any]):
        """Initialisiert den Timestep-Manager."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
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
        if strategy == 'full':
            processed_data = self._strategy_full(processed_data, strategy_params)
        elif strategy == 'time_range':
            processed_data = self._strategy_time_range(processed_data, strategy_params)
        elif strategy == 'averaging':
            processed_data = self._strategy_averaging(processed_data, strategy_params)
        elif strategy == 'sampling_24n':
            processed_data = self._strategy_sampling_24n(processed_data, strategy_params)
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
        
        # Timeseries-Daten anpassen 
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
        
        # Profile-Spalten identifizieren
        profile_columns = [col for col in timeseries_df.columns if col != 'timestamp']
        
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