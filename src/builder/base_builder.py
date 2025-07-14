#!/usr/bin/env python3
"""
src/builder/base_builder.py - Basis-Klasse für ModelBuilder

Zentrale Basis-Funktionalität:
- Zeitindex-Verwaltung
- oemof-solph Imports
- Grundlegende Model-Erstellung
- FIXED: Robuste Datenvalidierung
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging
from ..core import setup_component_logger

logger = setup_component_logger('builder.base')

class BaseModelBuilder:
    """Basis-Klasse für oemof-solph Modell-Erstellung"""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialisiert den BaseModelBuilder
        
        Args:
            data: Importierte Daten aus DataImporter
        """
        self.data = data
        self.buses_dict = {}
        self.nodes = []
        
        # oemof-solph Module (werden bei Bedarf geladen)
        self.solph = None
        self.buses = None
        self.components = None
        self.flows = None
        self.Investment = None
        
        # FIXED: Sichere Zeitindex-Erstellung
        self._setup_timeindex()
        
        logger.info(f"BaseModelBuilder initialisiert mit {len(self.data)} Datentypen")
    
    def _setup_timeindex(self):
        """
        Erstellt Zeitindex - WORKAROUND für oemof-solph v0.6.0
        FIXED: Robuste Behandlung verschiedener Eingabetypen
        """
        # Sichere Extraktion der Zeitreihen
        timeseries = self.data.get('timeseries')
        
        if timeseries is None:
            raise ValueError("Keine Zeitreihen-Daten in 'timeseries' gefunden")
        
        # Behandle verschiedene Eingabetypen
        if isinstance(timeseries, pd.DataFrame):
            self.timeseries = timeseries
            if 'timestamp' in timeseries.columns:
                # Numerischer Index als Workaround für v0.6.0 datetime-Probleme
                self.timeindex = list(range(len(timeseries)))
                # Original-Timestamps für Export behalten
                self.original_timestamps = pd.to_datetime(timeseries['timestamp']).tolist()
            else:
                raise ValueError("Spalte 'timestamp' in timeseries DataFrame fehlt")
                
        elif isinstance(timeseries, (list, tuple)):
            # Fallback für Listen-Input (z.B. aus Tests)
            if len(timeseries) == 0:
                # Leere Liste - erstelle minimalen Zeitindex
                logger.warning("Leere Zeitreihen-Liste - erstelle minimalen Zeitindex")
                self.timeindex = [0]
                self.original_timestamps = [pd.Timestamp.now()]
                # Erstelle minimales DataFrame
                self.timeseries = pd.DataFrame({
                    'timestamp': self.original_timestamps
                })
            else:
                raise ValueError("Zeitreihen als Liste nicht unterstützt - DataFrame erforderlich")
        else:
            raise ValueError(f"Unbekannter Zeitreihen-Typ: {type(timeseries)}")
        
        logger.info(f"Zeitindex erstellt: {len(self.timeindex)} Schritte (numerisch 0-{len(self.timeindex)-1})")
        if self.original_timestamps:
            logger.info(f"Zeitbereich: {self.original_timestamps[0]} bis {self.original_timestamps[-1]}")
    
    def _load_oemof_modules(self):
        """Lädt oemof-solph Module bei Bedarf"""
        if self.solph is not None:
            return  # Bereits geladen
        
        try:
            from oemof import solph
            from oemof.solph import buses, components, flows
            from oemof.solph._options import Investment
            
            self.solph = solph
            self.buses = buses
            self.components = components
            self.flows = flows
            self.Investment = Investment
            
            logger.info("oemof-solph Module erfolgreich geladen")
            
        except ImportError as e:
            logger.error(f"Fehler beim Laden der oemof-solph Module: {e}")
            raise
    
    def create_energy_system(self):
        """
        Erstellt das Basis-EnergySystem
        
        Returns:
            oemof.solph.EnergySystem
        """
        self._load_oemof_modules()
        
        energy_system = self.solph.EnergySystem(
            timeindex=self.timeindex,
            infer_last_interval=False
        )
        
        logger.info("EnergySystem erstellt")
        return energy_system
    
    def create_model(self, energy_system):
        """
        Erstellt das Optimierungsmodell
        
        Args:
            energy_system: oemof EnergySystem mit allen Komponenten
            
        Returns:
            oemof.solph.Model
        """
        self._load_oemof_modules()
        
        model = self.solph.Model(energy_system)
        logger.info("Optimierungsmodell erstellt")
        
        return model
    
    def add_nodes_to_system(self, energy_system):
        """
        Fügt alle Nodes zum EnergySystem hinzu
        
        Args:
            energy_system: oemof EnergySystem
        """
        if not self.nodes:
            logger.warning("Keine Nodes zum Hinzufügen vorhanden")
            return
        
        energy_system.add(*self.nodes)
        logger.info(f"EnergySystem erweitert um {len(self.nodes)} Komponenten")
    
    def get_model_summary(self) -> str:
        """
        Erstellt Zusammenfassung des erstellten Modells
        
        Returns:
            String mit Modell-Zusammenfassung
        """
        bus_count = len(self.buses_dict)
        
        # Sichere Extraktion der Komponenten-Anzahlen
        source_count = len(self.data.get('sources', [])) if isinstance(self.data.get('sources'), pd.DataFrame) and not self.data['sources'].empty else 0
        sink_count = len(self.data.get('sinks', [])) if isinstance(self.data.get('sinks'), pd.DataFrame) and not self.data['sinks'].empty else 0
        converter_count = len(self.data.get('converters', [])) if isinstance(self.data.get('converters'), pd.DataFrame) and not self.data['converters'].empty else 0
        storage_count = len(self.data.get('storages', [])) if isinstance(self.data.get('storages'), pd.DataFrame) and not self.data['storages'].empty else 0
        
        summary = (f"Modell: {bus_count} Buses, {source_count} Sources, "
                  f"{sink_count} Sinks, {converter_count} Converters, {storage_count} Storages, "
                  f"{len(self.timeindex)} Zeitschritte")
        
        return summary
    
    def get_timeindex_info(self) -> Dict[str, Any]:
        """
        Gibt Zeitindex-Informationen zurück
        
        Returns:
            Dictionary mit Zeitindex-Infos
        """
        return {
            'length': len(self.timeindex),
            'start_time': self.original_timestamps[0] if self.original_timestamps else None,
            'end_time': self.original_timestamps[-1] if self.original_timestamps else None,
            'numeric_index': self.timeindex,
            'datetime_index': self.original_timestamps
        }
    
    def validate_model_data(self):
        """
        Validiert die Basis-Modelldaten
        FIXED: Robuste Validierung für verschiedene Datentypen
        
        Raises:
            ValueError: Bei kritischen Validierungsfehlern
        """
        # Zeitreihen-Länge prüfen
        if len(self.timeindex) == 0:
            raise ValueError("Keine Zeitreihen-Daten vorhanden")
        
        # Sichere Validierung der Komponenten
        sources_df = self.data.get('sources', pd.DataFrame())
        sinks_df = self.data.get('sinks', pd.DataFrame())
        
        # Mindestens eine Source und Sink erforderlich (falls nicht leer)
        if isinstance(sources_df, pd.DataFrame) and sources_df.empty:
            logger.warning("Keine Sources vorhanden")
        
        if isinstance(sinks_df, pd.DataFrame) and sinks_df.empty:
            logger.warning("Keine Sinks vorhanden")
        
        logger.info("Basis-Modelldaten validiert")
    
    def reset_model(self):
        """Setzt das Modell zurück für Neuerstellung"""
        self.buses_dict = {}
        self.nodes = []
        logger.info("Modell-Zustand zurückgesetzt")
    
    def get_component_counts(self) -> Dict[str, int]:
        """
        Gibt Anzahl der Komponenten zurück
        
        Returns:
            Dictionary mit Komponenten-Anzahlen
        """
        counts = {}
        
        for component_type in ['buses', 'sources', 'sinks', 'converters', 'storages']:
            df = self.data.get(component_type, pd.DataFrame())
            if isinstance(df, pd.DataFrame):
                counts[component_type] = len(df) if not df.empty else 0
            else:
                counts[component_type] = 0
        
        counts['total_nodes'] = len(self.nodes)
        
        return counts

# Export der Klasse für Import
__all__ = ['BaseModelBuilder']