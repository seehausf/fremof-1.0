#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Visualisierungs-Modul
======================================

Erstellt Visualisierungen und Plots für Optimierungsergebnisse.
Unterstützt verschiedene Diagrammtypen und Exportformate.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Optionale Imports für Visualisierung
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    plt.style.use('default')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None


class Visualizer:
    """Klasse für die Erstellung von Visualisierungen."""
    
    def __init__(self, output_dir: Path, settings: Dict[str, Any]):
        """
        Initialisiert den Visualizer.
        
        Args:
            output_dir: Ausgabeverzeichnis
            settings: Konfigurationsdictionary
        """
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Erstellte Dateien
        self.created_files = []
        
        # Verfügbarkeit prüfen
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("⚠️  Matplotlib nicht verfügbar - Visualisierungen deaktiviert")
    
    def create_visualizations(self, results: Dict[str, Any], energy_system: Any,
                            excel_data: Dict[str, Any]) -> List[Path]:
        """
        Erstellt alle Visualisierungen.
        
        Args:
            results: Optimierungsergebnisse
            energy_system: EnergySystem
            excel_data: Original Excel-Daten
            
        Returns:
            Liste der erstellten Dateien
        """
        if not MATPLOTLIB_AVAILABLE:
            self.logger.info("📊 Visualisierungen übersprungen (Matplotlib fehlt)")
            return []
        
        self.logger.info("🎨 Erstelle Visualisierungen...")
        
        # Basis-Plots erstellen
        self._create_flow_plot(results)
        self._create_energy_balance_plot(results)
        self._create_cost_breakdown_plot(results)
        
        # Erweiterte Plots (falls Daten verfügbar)
        if excel_data.get('timeseries') is not None:
            self._create_timeseries_comparison(results, excel_data)
        
        self.logger.info(f"✅ {len(self.created_files)} Visualisierungen erstellt")
        return self.created_files
    
    def _create_flow_plot(self, results: Dict[str, Any]):
        """Erstellt Flow-Zeitreihen-Plot."""
        try:
            # Flow-Daten extrahieren
            flows_data = []
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    
                    df_temp = pd.DataFrame({
                        'timestamp': flow_values.index,
                        'flow': flow_values.values,
                        'connection': f"{source} → {target}"
                    })
                    flows_data.append(df_temp)
            
            if not flows_data:
                return
            
            flows_df = pd.concat(flows_data, ignore_index=True)
            
            # Plot erstellen
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Nur die wichtigsten Flows plotten (Top 10 nach Summe)
            flow_sums = flows_df.groupby('connection')['flow'].sum().sort_values(ascending=False)
            top_flows = flow_sums.head(10).index
            
            flows_subset = flows_df[flows_df['connection'].isin(top_flows)]
            
            for connection in top_flows:
                data = flows_subset[flows_subset['connection'] == connection]
                ax.plot(data['timestamp'], data['flow'], label=connection, linewidth=1.5)
            
            ax.set_xlabel('Zeit')
            ax.set_ylabel('Energiefluss [kW]')
            ax.set_title('Energieflüsse über Zeit (Top 10)')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            
            # Zeitachse formatieren
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Speichern
            filepath = self.output_dir / "flow_timeseries.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(filepath)
            self.logger.debug(f"      🎨 {filepath.name}")
            
        except Exception as e:
            self.logger.warning(f"Flow-Plot konnte nicht erstellt werden: {e}")
    
    def _create_energy_balance_plot(self, results: Dict[str, Any]):
        """Erstellt Energiebilanz-Balkendiagramm."""
        try:
            # Energie-Summen berechnen
            energy_data = {}
            
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    flow_values = flow_results['sequences']['flow']
                    total_energy = flow_values.sum()
                    
                    # Nach Source und Target kategorisieren
                    if total_energy > 0:
                        if str(source) not in energy_data:
                            energy_data[str(source)] = {'output': 0, 'input': 0}
                        if str(target) not in energy_data:
                            energy_data[str(target)] = {'output': 0, 'input': 0}
                        
                        energy_data[str(source)]['output'] += total_energy
                        energy_data[str(target)]['input'] += total_energy
            
            if not energy_data:
                return
            
            # DataFrame erstellen
            components = list(energy_data.keys())
            inputs = [energy_data[comp]['input'] for comp in components]
            outputs = [energy_data[comp]['output'] for comp in components]
            
            # Plot erstellen
            fig, ax = plt.subplots(figsize=(12, 8))
            
            x = np.arange(len(components))
            width = 0.35
            
            bars1 = ax.bar(x - width/2, inputs, width, label='Input', alpha=0.8, color='lightblue')
            bars2 = ax.bar(x + width/2, outputs, width, label='Output', alpha=0.8, color='orange')
            
            ax.set_xlabel('Komponenten')
            ax.set_ylabel('Energie [kWh]')
            ax.set_title('Energiebilanz nach Komponenten')
            ax.set_xticks(x)
            ax.set_xticklabels(components, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Werte auf Balken anzeigen
            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}', ha='center', va='bottom', fontsize=8)
            
            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            
            # Speichern
            filepath = self.output_dir / "energy_balance.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(filepath)
            self.logger.debug(f"      🎨 {filepath.name}")
            
        except Exception as e:
            self.logger.warning(f"Energiebilanz-Plot konnte nicht erstellt werden: {e}")
    
    def _create_cost_breakdown_plot(self, results: Dict[str, Any]):
        """Erstellt Kostenaufschlüsselung als Tortendiagramm."""
        try:
            # Kosten sammeln (vereinfacht)
            cost_categories = {'Variable Kosten': 0, 'Investment-Kosten': 0, 'Fixkosten': 0}
            
            for (source, target), flow_results in results.items():
                if 'scalars' in flow_results:
                    scalars = flow_results['scalars']
                    
                    # Variable Kosten schätzen
                    if 'variable_costs' in scalars and 'sequences' in flow_results:
                        var_costs = scalars.get('variable_costs', 0)
                        if 'flow' in flow_results['sequences']:
                            total_flow = flow_results['sequences']['flow'].sum()
                            cost_categories['Variable Kosten'] += var_costs * total_flow
                    
                    # Investment-Kosten
                    inv_costs = scalars.get('investment_costs', 0)
                    cost_categories['Investment-Kosten'] += inv_costs
            
            # Nur Kategorien mit Werten > 0 plotten
            filtered_costs = {k: v for k, v in cost_categories.items() if v > 0}
            
            if not filtered_costs:
                self.logger.debug("      ⏭️  Keine Kostendaten für Plot verfügbar")
                return
            
            # Tortendiagramm erstellen
            fig, ax = plt.subplots(figsize=(10, 8))
            
            costs = list(filtered_costs.values())
            labels = list(filtered_costs.keys())
            colors = ['lightcoral', 'lightskyblue', 'lightgreen'][:len(costs)]
            
            wedges, texts, autotexts = ax.pie(costs, labels=labels, autopct='%1.1f%%',
                                             colors=colors, startangle=90)
            
            ax.set_title('Kostenaufschlüsselung', fontsize=14, fontweight='bold')
            
            # Legende mit absoluten Werten
            legend_labels = [f'{label}: {value:,.0f} €' for label, value in filtered_costs.items()]
            ax.legend(wedges, legend_labels, title="Kosten", loc="center left",
                     bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.tight_layout()
            
            # Speichern
            filepath = self.output_dir / "cost_breakdown.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(filepath)
            self.logger.debug(f"      🎨 {filepath.name}")
            
        except Exception as e:
            self.logger.warning(f"Kosten-Plot konnte nicht erstellt werden: {e}")
    
    def _create_timeseries_comparison(self, results: Dict[str, Any], excel_data: Dict[str, Any]):
        """Erstellt Vergleich zwischen Original-Zeitreihen und Ergebnissen."""
        try:
            timeseries_df = excel_data.get('timeseries')
            if timeseries_df is None or timeseries_df.empty:
                return
            
            # Relevante Profile identifizieren
            profile_columns = [col for col in timeseries_df.columns 
                             if col != 'timestamp' and 'profile' in col.lower()]
            
            if not profile_columns:
                return
            
            # Ersten verfügbaren Flow extrahieren
            first_flow = None
            for (source, target), flow_results in results.items():
                if 'sequences' in flow_results and 'flow' in flow_results['sequences']:
                    first_flow = flow_results['sequences']['flow']
                    break
            
            if first_flow is None:
                return
            
            # Plot erstellen
            fig, axes = plt.subplots(len(profile_columns) + 1, 1, figsize=(14, 4 * (len(profile_columns) + 1)))
            
            if len(profile_columns) == 0:
                axes = [axes]
            
            # Original-Profile plotten
            for i, profile in enumerate(profile_columns):
                ax = axes[i] if len(profile_columns) > 1 else axes[0]
                
                ax.plot(timeseries_df['timestamp'], timeseries_df[profile], 
                       label=f'Original {profile}', linewidth=1.5)
                ax.set_ylabel('Wert')
                ax.set_title(f'Profil: {profile}')
                ax.grid(True, alpha=0.3)
                ax.legend()
            
            # Ersten Flow plotten
            ax_flow = axes[-1] if len(profile_columns) > 0 else axes[0]
            ax_flow.plot(first_flow.index, first_flow.values, 
                        label='Optimierter Flow', linewidth=1.5, color='red')
            ax_flow.set_ylabel('Flow [kW]')
            ax_flow.set_xlabel('Zeit')
            ax_flow.set_title('Optimierungsergebnis (erster Flow)')
            ax_flow.grid(True, alpha=0.3)
            ax_flow.legend()
            
            # Zeitachse formatieren
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Speichern
            filepath = self.output_dir / "timeseries_comparison.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.created_files.append(filepath)
            self.logger.debug(f"      🎨 {filepath.name}")
            
        except Exception as e:
            self.logger.warning(f"Zeitreihen-Vergleich konnte nicht erstellt werden: {e}")


# Test-Funktion
def test_visualizer():
    """Testfunktion für den Visualizer."""
    import tempfile
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ Matplotlib nicht verfügbar - Test übersprungen")
        return
    
    # Dummy-Daten erstellen
    timestamps = pd.date_range('2025-01-01', periods=24, freq='h')
    
    dummy_results = {
        ('pv_plant', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 50, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.0,
                'investment_costs': 1000
            }
        },
        ('grid_import', 'el_bus'): {
            'sequences': {
                'flow': pd.Series(np.random.rand(24) * 30, index=timestamps)
            },
            'scalars': {
                'variable_costs': 0.25
            }
        }
    }
    
    excel_data = {
        'timeseries': pd.DataFrame({
            'timestamp': timestamps,
            'pv_profile': np.random.rand(24),
            'load_profile': np.random.rand(24) * 40
        })
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = {'debug_mode': True}
        visualizer = Visualizer(Path(temp_dir), settings)
        
        try:
            files = visualizer.create_visualizations(dummy_results, None, excel_data)
            print(f"✅ Visualizer Test erfolgreich! {len(files)} Dateien erstellt")
            
        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")


if __name__ == "__main__":
    test_visualizer()
