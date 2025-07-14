#!/usr/bin/env python3
"""
exporter.py - Export der Optimierungsergebnisse

FIXED VERSION: Investment-Export repariert für oemof-solph v0.6.0
Problem behoben: 'Series' object has no attribute 'columns'
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ResultExporter:
    """Exportiert oemof-solph Ergebnisse in Excel-Dateien"""
    
    def __init__(self, energy_system, results: Dict[str, Any]):
        """
        Initialisiert den ResultExporter
        
        Args:
            energy_system: oemof EnergySystem
            results: Optimierungsergebnisse aus ModelRunner
        """
        self.energy_system = energy_system
        self.results = results['results']
        self.meta_results = results['meta_results']
        self.model = results['model']
        
        # Output-Verzeichnis sicherstellen
        self.output_dir = Path('results')
        self.output_dir.mkdir(exist_ok=True)
        
        # Zeitindex extrahieren
        self.timeindex = energy_system.timeindex if hasattr(energy_system, 'timeindex') else None
    
    def export_all(self, project_name: str = "oemof_results") -> List[Path]:
        """
        Exportiert alle Ergebnisse in Excel-Dateien
        
        Args:
            project_name: Name für die Ausgabedateien
            
        Returns:
            Liste der erstellten Dateien
        """
        logger.info("Starte Ergebnisexport...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{project_name}_{timestamp}"
        
        exported_files = []
        
        try:
            # 1. Flow-Ergebnisse exportieren
            flow_file = self.export_flow_results(base_filename)
            if flow_file:
                exported_files.append(flow_file)
            
            # 2. Investment-Ergebnisse exportieren (FIXED)
            investment_file = self.export_investment_results(base_filename)
            if investment_file:
                exported_files.append(investment_file)
            
            # 3. Zusammenfassung exportieren (FIXED)
            summary_file = self.export_summary(base_filename)
            if summary_file:
                exported_files.append(summary_file)
            
            logger.info(f"Ergebnisexport abgeschlossen: {len(exported_files)} Dateien erstellt")
            return exported_files
            
        except Exception as e:
            logger.error(f"Fehler beim Ergebnisexport: {e}")
            raise
    
    def export_flow_results(self, base_filename: str) -> Optional[Path]:
        """Exportiert detaillierte Flow-Ergebnisse"""
        
        try:
            logger.info("Exportiere Flow-Ergebnisse...")
            
            # Sammle alle Flow-Zeitreihen
            all_flows = {}
            
            for flow_key, flow_data in self.results.items():
                if 'sequences' in flow_data and not flow_data['sequences'].empty:
                    sequences = flow_data['sequences']
                    
                    # Flow-Name erstellen
                    if len(flow_key) == 2:
                        flow_name = f"{flow_key[0]}→{flow_key[1]}"
                    else:
                        flow_name = str(flow_key)
                    
                    # Alle Spalten des Flows hinzufügen
                    for col in sequences.columns:
                        col_name = f"{flow_name}_{col}" if len(sequences.columns) > 1 else flow_name
                        all_flows[col_name] = sequences[col].values
            
            if not all_flows:
                logger.warning("Keine Flow-Zeitreihen zum Exportieren gefunden")
                return None
            
            # DataFrame erstellen
            flow_df = pd.DataFrame(all_flows)
            
            # Zeitindex hinzufügen falls verfügbar
            if self.timeindex and len(self.timeindex) == len(flow_df):
                flow_df.insert(0, 'timestamp', self.timeindex)
            
            # Excel-Export
            output_file = self.output_dir / f"{base_filename}_flow_results.xlsx"
            flow_df.to_excel(output_file, index=False)
            
            logger.info(f"Flow-Ergebnisse exportiert: {output_file}")
            logger.info(f"  {len(flow_df)} Zeitschritte, {len(flow_df.columns)-1} Flows")
            
            return output_file
            
        except Exception as e:
            logger.error(f"Fehler beim Export der Flow-Ergebnisse: {e}")
            return None
    
    def export_investment_results(self, base_filename: str) -> Optional[Path]:
        """
        FIXED: Exportiert Investment-Ergebnisse
        Kompatibel mit oemof-solph v0.6.0 Results-Struktur
        """
        try:
            logger.info("Exportiere Investment-Ergebnisse...")
            
            investment_data = []
            
            for flow_key, flow_data in self.results.items():
                if 'scalars' in flow_data:
                    scalars = flow_data['scalars']
                    
                    # FIX: Sichere Behandlung von Series vs DataFrame
                    if isinstance(scalars, pd.Series):
                        # Series zu DataFrame konvertieren
                        scalars_df = scalars.to_frame().T
                        scalar_columns = scalars_df.columns
                        scalar_values = scalars_df
                    elif isinstance(scalars, pd.DataFrame):
                        scalar_columns = scalars.columns
                        scalar_values = scalars
                    else:
                        logger.warning(f"Unbekannter scalars Typ für {flow_key}: {type(scalars)}")
                        continue
                    
                    # Flow-Informationen
                    if len(flow_key) == 2:
                        from_node, to_node = flow_key
                        flow_name = f"{from_node}→{to_node}"
                    else:
                        from_node = str(flow_key)
                        to_node = ""
                        flow_name = from_node
                    
                    # Investment-Spalten suchen
                    investment_cols = [col for col in scalar_columns if 'invest' in str(col).lower()]
                    
                    if investment_cols:
                        for col in investment_cols:
                            if not scalar_values[col].empty:
                                investment_value = scalar_values[col].iloc[0]
                                if investment_value > 0:
                                    investment_data.append({
                                        'flow_name': flow_name,
                                        'from_node': from_node,
                                        'to_node': to_node,
                                        'investment_type': col,
                                        'capacity_kW': investment_value,
                                        'capacity_MW': investment_value / 1000
                                    })
                    
                    # Auch andere skalare Werte exportieren
                    for col in scalar_columns:
                        if col not in investment_cols and not scalar_values[col].empty:
                            value = scalar_values[col].iloc[0]
                            if abs(value) > 1e-6:  # Nur signifikante Werte
                                investment_data.append({
                                    'flow_name': flow_name,
                                    'from_node': from_node,
                                    'to_node': to_node,
                                    'investment_type': col,
                                    'value': value,
                                    'unit': self._get_unit_for_scalar(col)
                                })
            
            if not investment_data:
                logger.warning("Keine Investment-Ergebnisse zum Exportieren gefunden")
                return None
            
            # DataFrame erstellen
            investment_df = pd.DataFrame(investment_data)
            
            # Excel-Export
            output_file = self.output_dir / f"{base_filename}_investment_results.xlsx"
            investment_df.to_excel(output_file, index=False)
            
            logger.info(f"Investment-Ergebnisse exportiert: {output_file}")
            logger.info(f"  {len(investment_df)} Einträge")
            
            return output_file
            
        except Exception as e:
            logger.error(f"Fehler beim Export der Investment-Ergebnisse: {e}")
            logger.debug("Results-Struktur Debug:", exc_info=True)
            return None
    
    def export_summary(self, base_filename: str) -> Optional[Path]:
        """
        FIXED: Exportiert Zusammenfassung der Ergebnisse
        Kompatibel mit oemof-solph v0.6.0 Results-Struktur
        """
        try:
            logger.info("Exportiere Zusammenfassung...")
            
            summary_data = {}
            
            # 1. Meta-Informationen
            summary_data['Meta-Informationen'] = self._get_meta_summary()
            
            # 2. Investment-Zusammenfassung (FIXED)
            summary_data['Investment-Zusammenfassung'] = self._get_investment_summary()
            
            # 3. Energie-Bilanz
            summary_data['Energie-Bilanz'] = self._get_energy_balance()
            
            # 4. Kosten-Übersicht
            summary_data['Kosten-Übersicht'] = self._get_cost_summary()
            
            # Excel-Export mit mehreren Sheets
            output_file = self.output_dir / f"{base_filename}_summary.xlsx"
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for sheet_name, data in summary_data.items():
                    if isinstance(data, pd.DataFrame):
                        data.to_excel(writer, sheet_name=sheet_name, index=False)
                    elif isinstance(data, dict):
                        # Dictionary in DataFrame umwandeln
                        df = pd.DataFrame(list(data.items()), columns=['Parameter', 'Wert'])
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"Zusammenfassung exportiert: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Fehler beim Export der Zusammenfassung: {e}")
            logger.debug("Results-Struktur Debug:", exc_info=True)
            return None
    
    def _get_meta_summary(self) -> Dict[str, Any]:
        """Erstellt Meta-Informationen-Zusammenfassung"""
        
        meta_info = {
            'Zeitstempel': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Anzahl_Zeitschritte': len(self.timeindex) if self.timeindex else 0,
        }
        
        if self.timeindex:
            meta_info['Start_Zeit'] = str(self.timeindex[0])
            meta_info['End_Zeit'] = str(self.timeindex[-1])
        
        # Solver-Informationen
        if self.meta_results and 'solver' in self.meta_results:
            solver_info = self.meta_results['solver']
            meta_info['Solver_Status'] = solver_info.get('Status', 'unbekannt')
            meta_info['Termination_Condition'] = solver_info.get('Termination condition', 'unbekannt')
            
            if 'Time' in solver_info:
                meta_info['Lösungszeit_Sekunden'] = solver_info['Time']
            
            if 'Lower bound' in solver_info:
                meta_info['Objektiv_Wert'] = solver_info['Lower bound']
        
        return meta_info
    
    def _get_investment_summary(self) -> pd.DataFrame:
        """
        FIXED: Erstellt Investment-Zusammenfassung
        Kompatibel mit oemof-solph v0.6.0 Results-Struktur
        """
        investments = []
        
        try:
            for flow_key, flow_data in self.results.items():
                if 'scalars' in flow_data:
                    scalars = flow_data['scalars']
                    
                    # FIX: Sichere Behandlung von Series vs DataFrame
                    if isinstance(scalars, pd.Series):
                        scalars_df = scalars.to_frame().T
                        scalar_columns = scalars_df.columns
                        scalar_data = scalars_df
                    elif isinstance(scalars, pd.DataFrame):
                        scalar_columns = scalars.columns
                        scalar_data = scalars
                    else:
                        continue
                    
                    invest_cols = [col for col in scalar_columns if 'invest' in str(col).lower()]
                    
                    for col in invest_cols:
                        if not scalar_data[col].empty and scalar_data[col].iloc[0] > 0:
                            flow_name = f"{flow_key[0]}→{flow_key[1]}" if len(flow_key) == 2 else str(flow_key)
                            investments.append({
                                'Komponente': flow_name,
                                'Investierte_Kapazität_kW': scalar_data[col].iloc[0],
                                'Investierte_Kapazität_MW': scalar_data[col].iloc[0] / 1000
                            })
        except Exception as e:
            logger.warning(f"Fehler bei Investment-Zusammenfassung: {e}")
        
        return pd.DataFrame(investments)
    
    def _get_energy_balance(self) -> pd.DataFrame:
        """Erstellt Energie-Bilanz"""
        
        energy_flows = []
        
        for flow_key, flow_data in self.results.items():
            if 'sequences' in flow_data and not flow_data['sequences'].empty:
                sequences = flow_data['sequences']
                
                for col in sequences.columns:
                    total_energy = sequences[col].sum()
                    if abs(total_energy) > 1e-6:
                        flow_name = f"{flow_key[0]}→{flow_key[1]}" if len(flow_key) == 2 else str(flow_key)
                        energy_flows.append({
                            'Flow': f"{flow_name}_{col}" if len(sequences.columns) > 1 else flow_name,
                            'Gesamt_Energie_kWh': total_energy,
                            'Gesamt_Energie_MWh': total_energy / 1000,
                            'Durchschnitt_kW': total_energy / len(sequences) if len(sequences) > 0 else 0
                        })
        
        return pd.DataFrame(energy_flows)
    
    def _get_cost_summary(self) -> Dict[str, float]:
        """Erstellt Kosten-Übersicht"""
        
        costs = {}
        
        if self.meta_results and 'objective' in self.meta_results:
            costs['Gesamtkosten_Euro'] = self.meta_results['objective']
        
        # Weitere Kosten-Details könnten hier hinzugefügt werden
        
        return costs
    
    def _get_unit_for_scalar(self, scalar_name: str) -> str:
        """Bestimmt Einheit für skalare Werte"""
        
        scalar_name_lower = str(scalar_name).lower()
        
        if 'invest' in scalar_name_lower or 'capacity' in scalar_name_lower:
            return 'kW'
        elif 'cost' in scalar_name_lower:
            return '€'
        elif 'energy' in scalar_name_lower:
            return 'kWh'
        else:
            return '-'