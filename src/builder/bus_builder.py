#!/usr/bin/env python3
"""
src/builder/bus_builder.py - Bus-Erstellung und -Verwaltung

Spezialisiert auf:
- Bus-Erkennung aus Komponenten-Referenzen
- Bus-Erstellung und -Verwaltung
- Bus-Validierung
- Verbindungsanalyse
"""

import pandas as pd
from typing import Dict, Any, Set, List
import logging
from .base_builder import BaseModelBuilder
from ..core import setup_component_logger, parse_bus_list

logger = setup_component_logger('builder.bus')

class BusBuilder(BaseModelBuilder):
    """Spezialisierte Klasse für Bus-Erstellung"""
    
    def create_buses(self):
        """Erstellt alle Bus-Komponenten basierend auf Referenzen"""
        logger.info("Erstelle Buses...")
        
        # Sammle alle referenzierten Buses
        referenced_buses = self._collect_referenced_buses()
        
        # Buses erstellen
        self._create_bus_objects(referenced_buses)
        
        # Bus-Verbindungen validieren
        self.validate_buses()
        
        logger.info(f"Buses erstellt: {len(self.buses_dict)}")
    
    def _collect_referenced_buses(self) -> Set[str]:
        """Sammelt alle in Komponenten referenzierten Buses"""
        referenced_buses = set()
        
        # Aus Sources sammeln
        referenced_buses.update(self._get_buses_from_sources())
        
        # Aus Sinks sammeln
        referenced_buses.update(self._get_buses_from_sinks())
        
        # Aus Storages sammeln (falls vorhanden)
        referenced_buses.update(self._get_buses_from_storages())
        
        # Aus Transformers sammeln (falls vorhanden)
        referenced_buses.update(self._get_buses_from_transformers())
        
        # NEU: Aus Converters sammeln
        referenced_buses.update(self._get_buses_from_converters())
        
        # Explizit definierte Buses hinzufügen
        referenced_buses.update(self._get_buses_from_bus_sheet())
        
        logger.debug(f"Referenzierte Buses gefunden: {sorted(referenced_buses)}")
        
        return referenced_buses
    
    def _get_buses_from_sources(self) -> Set[str]:
        """Sammelt Bus-Referenzen aus Sources"""
        buses = set()
        
        sources_df = self.data.get('sources', pd.DataFrame())
        if sources_df.empty:
            return buses
            
        for _, source in sources_df.iterrows():
            if 'output' in source and pd.notna(source['output']):
                output_buses = [bus.strip() for bus in str(source['output']).split(';')]
                buses.update(output_buses)
                logger.debug(f"Source '{source['label']}' → Buses: {output_buses}")
        
        return buses
    
    def _get_buses_from_sinks(self) -> Set[str]:
        """Sammelt Bus-Referenzen aus Sinks"""
        buses = set()
        
        sinks_df = self.data.get('sinks', pd.DataFrame())
        if sinks_df.empty:
            return buses
            
        for _, sink in sinks_df.iterrows():
            if 'input' in sink and pd.notna(sink['input']):
                input_buses = [bus.strip() for bus in str(sink['input']).split(';')]
                buses.update(input_buses)
                logger.debug(f"Sink '{sink['label']}' ← Buses: {input_buses}")
        
        return buses
    
    def _get_buses_from_storages(self) -> Set[str]:
        """Sammelt Bus-Referenzen aus Storages"""
        buses = set()
        
        storages_df = self.data.get('storages', pd.DataFrame())
        if storages_df.empty:
            return buses
            
        for _, storage in storages_df.iterrows():
            if 'bus' in storage and pd.notna(storage['bus']):
                storage_bus = str(storage['bus']).strip()
                buses.add(storage_bus)
                logger.debug(f"Storage '{storage['label']}' ↔ Bus: {storage_bus}")
        
        return buses
    
    def _get_buses_from_transformers(self) -> Set[str]:
        """Sammelt Bus-Referenzen aus Transformers"""
        buses = set()
        
        transformers_df = self.data.get('transformers', pd.DataFrame())
        if transformers_df.empty:
            return buses
            
        for _, transformer in transformers_df.iterrows():
            # Input-Buses
            if 'input' in transformer and pd.notna(transformer['input']):
                input_buses = [bus.strip() for bus in str(transformer['input']).split(';')]
                buses.update(input_buses)
                
            # Output-Buses
            if 'output' in transformer and pd.notna(transformer['output']):
                output_buses = [bus.strip() for bus in str(transformer['output']).split(';')]
                buses.update(output_buses)
                
            logger.debug(f"Transformer '{transformer['label']}' → Buses gefunden")
        
        return buses
    
    def _get_buses_from_converters(self) -> Set[str]:
        """NEU: Sammelt Bus-Referenzen aus Converter-Komponenten"""
        buses = set()
        
        converters_df = self.data.get('converters', pd.DataFrame())
        if converters_df.empty:
            return buses
        
        for _, converter in converters_df.iterrows():
            converter_label = converter.get('label', 'unknown')
            
            # Input-Buses (können mehrere sein)
            if 'inputs' in converter and pd.notna(converter['inputs']):
                input_buses = parse_bus_list(converter['inputs'])
                buses.update(input_buses)
                logger.debug(f"Converter '{converter_label}' ← Input-Buses: {input_buses}")
            
            # Output-Buses (können mehrere sein)
            if 'outputs' in converter and pd.notna(converter['outputs']):
                output_buses = parse_bus_list(converter['outputs'])
                buses.update(output_buses)
                logger.debug(f"Converter '{converter_label}' → Output-Buses: {output_buses}")
        
        if buses:
            logger.info(f"Converter-Buses gefunden: {sorted(buses)}")
        
        return buses
    
    def _get_buses_from_bus_sheet(self) -> Set[str]:
        """Sammelt explizit definierte Buses aus Bus-Sheet"""
        buses = set()
        
        buses_df = self.data.get('buses', pd.DataFrame())
        if buses_df.empty:
            return buses
            
        for _, bus_data in buses_df.iterrows():
            bus_label = str(bus_data['label']).strip()
            buses.add(bus_label)
            logger.debug(f"Expliziter Bus: {bus_label}")
        
        return buses
    
    def _create_bus_objects(self, referenced_buses: Set[str]):
        """Erstellt oemof-solph Bus-Objekte"""
        self._load_oemof_modules()
        
        for bus_label in sorted(referenced_buses):
            try:
                # Bus-Objekt erstellen
                bus = self.buses.Bus(label=bus_label)
                
                # Speichern
                self.buses_dict[bus_label] = bus
                self.nodes.append(bus)
                
                logger.debug(f"Bus erstellt: {bus_label}")
                
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von Bus '{bus_label}': {e}")
                raise
    
    def validate_buses(self):
        """Validiert Bus-Konfiguration"""
        logger.info("Validiere Bus-Konfiguration...")
        
        # Mindestens ein Bus erforderlich
        if not self.buses_dict:
            raise ValueError("Mindestens ein Bus erforderlich")
        
        # Prüfe isolierte Buses (nur Warnung)
        isolated_buses = self._find_isolated_buses()
        if isolated_buses:
            logger.warning(f"Isolierte Buses (keine Verbindungen): {isolated_buses}")
        
        # Prüfe Bus-Verbindungen
        connection_stats = self._analyze_bus_connections()
        logger.info(f"Bus-Verbindungen analysiert: {connection_stats}")
        
        logger.info("Bus-Validierung abgeschlossen")
    
    def _find_isolated_buses(self) -> List[str]:
        """Findet Buses ohne Verbindungen"""
        connected_buses = set()
        
        # Buses mit Sources
        sources_df = self.data.get('sources', pd.DataFrame())
        if not sources_df.empty:
            for _, source in sources_df.iterrows():
                if 'output' in source and pd.notna(source['output']):
                    output_buses = [bus.strip() for bus in str(source['output']).split(';')]
                    connected_buses.update(output_buses)
        
        # Buses mit Sinks
        sinks_df = self.data.get('sinks', pd.DataFrame())
        if not sinks_df.empty:
            for _, sink in sinks_df.iterrows():
                if 'input' in sink and pd.notna(sink['input']):
                    input_buses = [bus.strip() for bus in str(sink['input']).split(';')]
                    connected_buses.update(input_buses)
        
        # Buses mit Storages
        storages_df = self.data.get('storages', pd.DataFrame())
        if not storages_df.empty:
            for _, storage in storages_df.iterrows():
                if 'bus' in storage and pd.notna(storage['bus']):
                    connected_buses.add(str(storage['bus']).strip())
        
        # NEU: Buses mit Converters
        converters_df = self.data.get('converters', pd.DataFrame())
        if not converters_df.empty:
            for _, converter in converters_df.iterrows():
                # Input-Buses
                if 'inputs' in converter and pd.notna(converter['inputs']):
                    input_buses = parse_bus_list(converter['inputs'])
                    connected_buses.update(input_buses)
                
                # Output-Buses
                if 'outputs' in converter and pd.notna(converter['outputs']):
                    output_buses = parse_bus_list(converter['outputs'])
                    connected_buses.update(output_buses)
        
        # Isolierte finden
        all_buses = set(self.buses_dict.keys())
        isolated = list(all_buses - connected_buses)
        
        return isolated
    
    def _analyze_bus_connections(self) -> Dict[str, Any]:
        """Analysiert Bus-Verbindungen"""
        bus_stats = {}
        
        for bus_name in self.buses_dict.keys():
            stats = {
                'sources': 0,
                'sinks': 0,
                'storages': 0,
                'converters': 0,
                'total_connections': 0
            }
            
            # Sources zählen
            sources_df = self.data.get('sources', pd.DataFrame())
            if not sources_df.empty:
                for _, source in sources_df.iterrows():
                    if 'output' in source and pd.notna(source['output']):
                        if bus_name in [bus.strip() for bus in str(source['output']).split(';')]:
                            stats['sources'] += 1
            
            # Sinks zählen
            sinks_df = self.data.get('sinks', pd.DataFrame())
            if not sinks_df.empty:
                for _, sink in sinks_df.iterrows():
                    if 'input' in sink and pd.notna(sink['input']):
                        if bus_name in [bus.strip() for bus in str(sink['input']).split(';')]:
                            stats['sinks'] += 1
            
            # Storages zählen
            storages_df = self.data.get('storages', pd.DataFrame())
            if not storages_df.empty:
                for _, storage in storages_df.iterrows():
                    if 'bus' in storage and pd.notna(storage['bus']):
                        if bus_name == str(storage['bus']).strip():
                            stats['storages'] += 1
            
            # NEU: Converters zählen
            converters_df = self.data.get('converters', pd.DataFrame())
            if not converters_df.empty:
                for _, converter in converters_df.iterrows():
                    # Input-Verbindungen
                    if 'inputs' in converter and pd.notna(converter['inputs']):
                        input_buses = parse_bus_list(converter['inputs'])
                        if bus_name in input_buses:
                            stats['converters'] += 1
                    
                    # Output-Verbindungen
                    if 'outputs' in converter and pd.notna(converter['outputs']):
                        output_buses = parse_bus_list(converter['outputs'])
                        if bus_name in output_buses:
                            stats['converters'] += 1
            
            # Gesamtverbindungen
            stats['total_connections'] = (stats['sources'] + stats['sinks'] + 
                                        stats['storages'] + stats['converters'])
            
            bus_stats[bus_name] = stats
        
        # Zusammenfassung
        total_buses = len(bus_stats)
        connected_buses = sum(1 for stats in bus_stats.values() if stats['total_connections'] > 0)
        
        return {
            'total_buses': total_buses,
            'connected_buses': connected_buses,
            'isolated_buses': total_buses - connected_buses,
            'bus_details': bus_stats
        }
    
    def get_bus_summary(self) -> Dict[str, Any]:
        """Erstellt Zusammenfassung aller Buses"""
        if not self.buses_dict:
            return {'total_buses': 0, 'bus_list': []}
        
        bus_summary = {
            'total_buses': len(self.buses_dict),
            'bus_list': list(self.buses_dict.keys()),
            'connections': self._analyze_bus_connections()
        }
        
        return bus_summary
    
    def get_bus_by_label(self, label: str):
        """Gibt Bus-Objekt für Label zurück"""
        return self.buses_dict.get(label)
    
    def has_bus(self, label: str) -> bool:
        """Prüft ob Bus existiert"""
        return label in self.buses_dict
    
    def get_all_bus_labels(self) -> List[str]:
        """Gibt alle Bus-Labels zurück"""
        return sorted(self.buses_dict.keys())
    
    def debug_bus_structure(self):
        """DEBUG: Gibt detaillierte Bus-Struktur aus"""
        logger.info("=== BUS STRUCTURE DEBUG ===")
        
        for bus_name, bus_obj in self.buses_dict.items():
            logger.info(f"Bus: {bus_name}")
            logger.info(f"  Objekt: {bus_obj}")
            logger.info(f"  Typ: {type(bus_obj)}")
        
        # Verbindungsanalyse
        connections = self._analyze_bus_connections()
        logger.info(f"Verbindungen: {connections}")
        
        logger.info("=== END BUS DEBUG ===")

# Export der Klasse für Import
__all__ = ['BusBuilder']