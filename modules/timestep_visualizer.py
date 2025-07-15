#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Timestep-Visualisierungs-Modul
===============================================

Erstellt Vorher-Nachher-Visualisierungen für Timestep-Management.
Zeigt die Auswirkungen der Zeitreihen-Anpassung auf die Daten.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

# Optionale Imports für Visualisierung
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


class TimestepVisualizer:
    """Erstellt Visualisierungen für Timestep-Management-Effekte."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Timestep-Visualizer.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Erstellte Dateien
        self.created_files = []
        
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("⚠️  Matplotlib nicht verfügbar - Timestep-Visualisierungen deaktiviert")
    
    def create_timestep_comparison(self, original_data: Dict[str, Any], 
                                 processed_data: Dict[str, Any]) -> List[Path]:
        """
        Erstellt Vorher-Nachher-Vergleich der Timestep-Anpassung.
        
        Args:
            original_data: Original Excel-Daten vor Timestep-Management
            processed_data: Daten nach Timestep-Management
            
        Returns:
            Liste der erstellten Dateien
        """
        if not MATPLOTLIB_AVAILABLE:
            self.logger.info("📊 Timestep-Visualisierungen übersprungen (Matplotlib fehlt)")
            return []
        
        # Prüfe ob Timestep-Management angewendet wurde
        if 'timestep_reduction_stats' not in processed_data:
            self.logger.info("📊 Kein Timestep-Management erkannt - keine Vergleichs-Visualisierung")
            return []
        
        stats = processed_data['timestep_reduction_stats']
        strategy = stats.get('strategy', 'unknown')
        
        self.logger.info(f"📊 Erstelle Timestep-Vergleich für Strategie: {strategy}")
        
        # Verschiedene Visualisierungen erstellen
        self._create_timeindex_comparison(original_data, processed_data, stats)
        self._create_timeseries_comparison(original_data, processed_data, stats)
        self._create_reduction_summary(original_data, processed_data, stats)
        
        if len(self.created_files) > 0:
            self.logger.info(f"✅ {len(self.created_files)} Timestep-Visualisierungen erstellt")
        
        return self.created_files
    
    def _create_timeindex_comparison(self, original_data: Dict[str, Any], 
                                   processed_data: Dict[str, Any], 
                                   stats: Dict[str, Any]):
        """Erstellt Vergleich der Zeitindizes."""
        try:
            original_timeindex = original_data.get('timeindex')
            processed_timeindex = processed_data.get('timeindex')
            
            if original_timeindex is None or processed_timeindex is None:
                return
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10))
            fig.suptitle(f'Zeitindex-Vergleich: {stats["strategy"].title()} Strategie', 
                        fontsize=16, fontweight='bold')
            
            # 1. Original Zeitindex
            ax1.plot(range(len(original_timeindex)), [1] * len(original_timeindex), 
                    'b|', markersize=8, alpha=0.7, label='Original Zeitpunkte')
            ax1.set_ylabel('Original\n(Alle Zeitpunkte)')
            ax1.set_title(f'Original: {len(original_timeindex):,} Zeitschritte')
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0.5, 1.5)
            
            # 2. Verarbeiteter Zeitindex 
            processed_indices = self._map_processed_to_original_indices(
                original_timeindex, processed_timeindex)
            
            ax2.plot(processed_indices, [1] * len(processed_indices), 
                    'ro', markersize=6, alpha=0.8, label='Ausgewählte Zeitpunkte')
            ax2.set_ylabel('Nach Timestep-\nManagement')
            ax2.set_title(f'Nach {stats["strategy"]}: {len(processed_timeindex):,} Zeitschritte '
                         f'({stats["time_savings"]} Reduktion)')
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0.5, 1.5)
            
            # 3. Overlay-Vergleich
            ax3.plot(range(len(original_timeindex)), [1] * len(original_timeindex), 
                    'b|', markersize=6, alpha=0.5, label=f'Original ({len(original_timeindex)})')
            ax3.plot(processed_indices, [1.1] * len(processed_indices), 
                    'ro', markersize=4, alpha=0.8, label=f'Ausgewählt ({len(processed_indices)})')
            ax3.set_ylabel('Overlay')
            ax3.set_xlabel('Zeitschritt-Index')
            ax3.set_title('Überlagerung: Blau = Original, Rot = Ausgewählt')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            ax3.set_ylim(0.8, 1.3)
            
            # Formatierung der X-Achse
            for ax in [ax1, ax2, ax3]:
                if len(original_timeindex) > 100:
                    ax.locator_params(axis='x', nbins=10)
            
            plt.tight_layout()
            
            # Speichern
            output_file = self.output_dir / f"timestep_timeindex_comparison_{stats['strategy']}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(output_file)
            self.logger.debug(f"      📊 {output_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Zeitindex-Vergleich konnte nicht erstellt werden: {e}")
    
    def _create_timeseries_comparison(self, original_data: Dict[str, Any], 
                                    processed_data: Dict[str, Any], 
                                    stats: Dict[str, Any]):
        """Erstellt Vergleich der Zeitreihen-Profile."""
        try:
            original_timeseries = original_data.get('timeseries')
            processed_timeseries = processed_data.get('timeseries')
            
            if original_timeseries is None or processed_timeseries is None:
                return
            
            # Profile-Spalten identifizieren
            profile_columns = [col for col in original_timeseries.columns if col != 'timestamp']
            
            if not profile_columns:
                return
            
            # Für jeden Profil-Typ ein Vergleichsplot
            for profile_col in profile_columns[:3]:  # Maximal 3 Profile
                self._create_single_profile_comparison(
                    original_timeseries, processed_timeseries, profile_col, stats)
        
        except Exception as e:
            self.logger.warning(f"Zeitreihen-Vergleich konnte nicht erstellt werden: {e}")
    
    def _create_single_profile_comparison(self, original_ts: pd.DataFrame, 
                                        processed_ts: pd.DataFrame,
                                        profile_col: str, stats: Dict[str, Any]):
        """Erstellt Vergleich für ein einzelnes Profil."""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(16, 10))
            fig.suptitle(f'Profil-Vergleich: {profile_col} | {stats["strategy"].title()} Strategie', 
                        fontsize=16, fontweight='bold')
            
            # 1. Original Zeitreihe (oben links)
            ax1 = axes[0, 0]
            if 'timestamp' in original_ts.columns:
                ax1.plot(original_ts['timestamp'], original_ts[profile_col], 
                        'b-', linewidth=1, alpha=0.8, label='Original')
            else:
                ax1.plot(original_ts[profile_col], 'b-', linewidth=1, alpha=0.8, label='Original')
            
            ax1.set_title(f'Original: {len(original_ts):,} Datenpunkte')
            ax1.set_ylabel('Wert')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # 2. Verarbeitete Zeitreihe (oben rechts)
            ax2 = axes[0, 1]
            if 'timestamp' in processed_ts.columns:
                ax2.plot(processed_ts['timestamp'], processed_ts[profile_col], 
                        'ro-', linewidth=2, markersize=4, alpha=0.8, label='Nach Timestep-Management')
            else:
                ax2.plot(processed_ts[profile_col], 'ro-', linewidth=2, markersize=4, alpha=0.8, label='Verarbeitet')
            
            ax2.set_title(f'Nach {stats["strategy"]}: {len(processed_ts):,} Datenpunkte')
            ax2.set_ylabel('Wert')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # 3. Overlay-Vergleich (unten links)
            ax3 = axes[1, 0]
            
            # Original als Linie
            if 'timestamp' in original_ts.columns and 'timestamp' in processed_ts.columns:
                ax3.plot(original_ts['timestamp'], original_ts[profile_col], 
                        'b-', linewidth=1, alpha=0.6, label=f'Original ({len(original_ts)})')
                ax3.plot(processed_ts['timestamp'], processed_ts[profile_col], 
                        'ro-', linewidth=2, markersize=3, alpha=0.9, label=f'Verarbeitet ({len(processed_ts)})')
                ax3.set_xlabel('Zeit')
            else:
                # Fallback ohne Timestamps
                x_orig = range(len(original_ts))
                x_proc = np.linspace(0, len(original_ts)-1, len(processed_ts))
                
                ax3.plot(x_orig, original_ts[profile_col], 
                        'b-', linewidth=1, alpha=0.6, label=f'Original ({len(original_ts)})')
                ax3.plot(x_proc, processed_ts[profile_col], 
                        'ro-', linewidth=2, markersize=3, alpha=0.9, label=f'Verarbeitet ({len(processed_ts)})')
                ax3.set_xlabel('Zeitschritt-Index')
            
            ax3.set_title('Überlagerung')
            ax3.set_ylabel('Wert')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 4. Statistik-Vergleich (unten rechts)
            ax4 = axes[1, 1]
            
            orig_stats = {
                'Min': original_ts[profile_col].min(),
                'Max': original_ts[profile_col].max(),
                'Mean': original_ts[profile_col].mean(),
                'Std': original_ts[profile_col].std()
            }
            
            proc_stats = {
                'Min': processed_ts[profile_col].min(),
                'Max': processed_ts[profile_col].max(),
                'Mean': processed_ts[profile_col].mean(),
                'Std': processed_ts[profile_col].std()
            }
            
            # Balkendiagramm für Statistiken
            x_pos = np.arange(len(orig_stats))
            width = 0.35
            
            bars1 = ax4.bar(x_pos - width/2, list(orig_stats.values()), width, 
                           label='Original', alpha=0.7, color='blue')
            bars2 = ax4.bar(x_pos + width/2, list(proc_stats.values()), width, 
                           label='Verarbeitet', alpha=0.7, color='red')
            
            ax4.set_xlabel('Statistik')
            ax4.set_ylabel('Wert')
            ax4.set_title('Statistik-Vergleich')
            ax4.set_xticks(x_pos)
            ax4.set_xticklabels(list(orig_stats.keys()))
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            # Werte auf Balken
            for bar in bars1:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}', ha='center', va='bottom', fontsize=8)
            
            for bar in bars2:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            
            # Speichern
            safe_profile_name = profile_col.replace('/', '_').replace('\\', '_')
            output_file = self.output_dir / f"timestep_profile_comparison_{safe_profile_name}_{stats['strategy']}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(output_file)
            self.logger.debug(f"      📊 {output_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Profil-Vergleich für {profile_col} fehlgeschlagen: {e}")
    
    def _create_reduction_summary(self, original_data: Dict[str, Any], 
                                processed_data: Dict[str, Any], 
                                stats: Dict[str, Any]):
        """Erstellt eine Zusammenfassungs-Visualisierung."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f'Timestep-Management Zusammenfassung: {stats["strategy"].title()}', 
                        fontsize=16, fontweight='bold')
            
            # 1. Zeitschritt-Reduktion (Tortendiagramm)
            reduction_data = [stats['final_periods'], 
                            stats['original_periods'] - stats['final_periods']]
            labels = ['Behalten', 'Entfernt']
            colors = ['lightgreen', 'lightcoral']
            
            wedges, texts, autotexts = ax1.pie(reduction_data, labels=labels, colors=colors,
                                              autopct='%1.1f%%', startangle=90)
            ax1.set_title(f'Zeitschritt-Reduktion\n{stats["time_savings"]} gespart')
            
            # 2. Absolute Zahlen (Balkendiagramm)
            categories = ['Original', 'Nach Timestep-Mgmt']
            values = [stats['original_periods'], stats['final_periods']]
            colors_bar = ['lightblue', 'orange']
            
            bars = ax2.bar(categories, values, color=colors_bar, alpha=0.7)
            ax2.set_ylabel('Anzahl Zeitschritte')
            ax2.set_title('Absolute Zeitschritt-Zahlen')
            ax2.grid(True, alpha=0.3)
            
            # Werte auf Balken
            for bar, value in zip(bars, values):
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(values)*0.01,
                        f'{value:,}', ha='center', va='bottom', fontweight='bold')
            
            # 3. Strategie-spezifische Parameter
            ax3.axis('off')
            
            info_text = f"Strategie: {stats['strategy']}\n"
            info_text += f"Reduktionsfaktor: {stats['reduction_factor']:.3f}\n"
            info_text += f"Zeitersparnis: {stats['time_savings']}\n\n"
            
            # Strategie-spezifische Details
            if stats['strategy'] == 'averaging':
                info_text += f"Mittelwertbildung: {stats.get('averaging_hours', 'N/A')} Stunden\n"
            elif stats['strategy'] == 'sampling_24n':
                info_text += f"Sampling-Faktor n: {stats.get('n_factor', 'N/A')}\n"
                info_text += f"Sampling-Muster: {stats.get('sampling_pattern', 'N/A')}\n"
            elif stats['strategy'] == 'time_range':
                info_text += f"Zeitbereich: {stats.get('selected_range', 'N/A')}\n"
            
            # Solver-Zeit-Schätzung
            if 'solver_time_estimate' in processed_data:
                time_est = processed_data['solver_time_estimate']
                info_text += f"\nGeschätzte Solver-Zeit-Ersparnis:\n"
                info_text += f"{time_est.get('estimated_time_savings', 'N/A')}\n"
                info_text += f"Komplexitäts-Reduktion: {time_est.get('complexity_reduction', 'N/A')}"
            
            ax3.text(0.05, 0.95, info_text, transform=ax3.transAxes, fontsize=11,
                    verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.7))
            ax3.set_title('Parameter & Schätzungen')
            
            # 4. Datenqualitäts-Vergleich
            if 'timeseries' in original_data and 'timeseries' in processed_data:
                orig_ts = original_data['timeseries']
                proc_ts = processed_data['timeseries']
                
                profile_cols = [col for col in orig_ts.columns if col != 'timestamp']
                
                if profile_cols:
                    # Erste Profil für Vergleich verwenden
                    profile_col = profile_cols[0]
                    
                    orig_mean = orig_ts[profile_col].mean()
                    proc_mean = proc_ts[profile_col].mean()
                    orig_std = orig_ts[profile_col].std()
                    proc_std = proc_ts[profile_col].std()
                    
                    metrics = ['Mittelwert', 'Standardabw.']
                    orig_values = [orig_mean, orig_std]
                    proc_values = [proc_mean, proc_std]
                    
                    x = np.arange(len(metrics))
                    width = 0.35
                    
                    bars1 = ax4.bar(x - width/2, orig_values, width, label='Original', alpha=0.7)
                    bars2 = ax4.bar(x + width/2, proc_values, width, label='Verarbeitet', alpha=0.7)
                    
                    ax4.set_ylabel(f'Wert ({profile_col})')
                    ax4.set_title(f'Datenqualität: {profile_col}')
                    ax4.set_xticks(x)
                    ax4.set_xticklabels(metrics)
                    ax4.legend()
                    ax4.grid(True, alpha=0.3)
                else:
                    ax4.text(0.5, 0.5, 'Keine Zeitreihen-Profile\nverfügbar', 
                           ha='center', va='center', transform=ax4.transAxes, fontsize=12)
                    ax4.set_title('Datenqualität')
            else:
                ax4.text(0.5, 0.5, 'Keine Zeitreihen-Daten\nverfügbar', 
                       ha='center', va='center', transform=ax4.transAxes, fontsize=12)
                ax4.set_title('Datenqualität')
            
            plt.tight_layout()
            
            # Speichern
            output_file = self.output_dir / f"timestep_reduction_summary_{stats['strategy']}.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(output_file)
            self.logger.debug(f"      📊 {output_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Reduktions-Zusammenfassung konnte nicht erstellt werden: {e}")
    
    def _map_processed_to_original_indices(self, original_timeindex: pd.DatetimeIndex, 
                                         processed_timeindex: pd.DatetimeIndex) -> List[int]:
        """Mapt verarbeitete Zeitpunkte zurück auf Original-Indices."""
        try:
            indices = []
            
            for proc_time in processed_timeindex:
                # Finde den nächstgelegenen Original-Zeitpunkt
                time_diffs = abs(original_timeindex - proc_time)
                closest_idx = time_diffs.argmin()
                indices.append(closest_idx)
            
            return indices
            
        except Exception:
            # Fallback: Gleichmäßig verteilt
            if len(processed_timeindex) == 0:
                return []
            
            step = len(original_timeindex) // len(processed_timeindex)
            return list(range(0, len(original_timeindex), max(1, step)))[:len(processed_timeindex)]
    
    def is_available(self) -> bool:
        """Prüft ob die Visualisierung verfügbar ist."""
        return MATPLOTLIB_AVAILABLE


# Test-Funktion
def test_timestep_visualizer():
    """Testfunktion für den Timestep-Visualizer."""
    import tempfile
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ Matplotlib nicht verfügbar - Test übersprungen")
        return
    
    # Dummy-Daten erstellen
    timestamps_orig = pd.date_range('2025-01-01', periods=168, freq='h')
    timestamps_proc = pd.date_range('2025-01-01', periods=84, freq='2h')
    
    original_data = {
        'timeindex': timestamps_orig,
        'timeseries': pd.DataFrame({
            'timestamp': timestamps_orig,
            'pv_profile': np.random.rand(168),
            'load_profile': np.random.rand(168) * 40
        })
    }
    
    processed_data = {
        'timeindex': timestamps_proc,
        'timeseries': pd.DataFrame({
            'timestamp': timestamps_proc,
            'pv_profile': np.random.rand(84),
            'load_profile': np.random.rand(84) * 40
        }),
        'timestep_reduction_stats': {
            'strategy': 'sampling_24n',
            'original_periods': 168,
            'final_periods': 84,
            'reduction_factor': 0.5,
            'time_savings': '50.0%',
            'n_factor': 2,
            'sampling_pattern': 'Alle 2 Stunden'
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        visualizer = TimestepVisualizer(Path(temp_dir), settings)
        
        try:
            files = visualizer.create_timestep_comparison(original_data, processed_data)
            print(f"✅ Timestep-Visualizer Test erfolgreich! {len(files)} Dateien erstellt")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")


if __name__ == "__main__":
    test_timestep_visualizer()