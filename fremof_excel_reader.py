# -*- coding: utf-8 -*-
"""
Fremof Excel Reader - Version 1.0
==================================

Erweiterte Excel-basierte Energiesystemmodellierung auf Basis von oemof-solph

Funktionen:
- Flexibler Excel-Import für Sources, Sinks, Converter
- Investment-Optimierung mit automatischer EP-Cost Berechnung  
- Timeseries-Integration mit deutscher Zahlenformatierung
- Robuste Validierung und Fehlerbehandlung

Author: Fremof Development Team
Date: 14. Juli 2025
"""

import pandas as pd
import numpy as np
import os
import logging
from typing import Dict, List, Any, Optional, Union

# Oemof-solph 0.6.0 Imports
import oemof.solph as solph
from oemof.solph import buses, components, flows, _options

# Aliase für einfachere Verwendung
Bus = buses.Bus
EnergySystem = solph.EnergySystem
Model = solph.Model
Source = components.Source
Sink = components.Sink
Converter = components.Converter
Flow = flows.Flow
Investment = _options.Investment


class FremofExcelReader:
    """Erweiterte Excel-Reader Klasse für Fremof Framework"""
    
    def __init__(self, filename: str):
        """
        Initialisierung des Excel-Readers
        
        Parameters
        ----------
        filename : str
            Pfad zur Excel-Datei
        """
        self.filename = filename
        self.nodes_data = {}
        self.timeseries_data = pd.DataFrame()
        self.buses = {}
        self.components = []
        
    def read_excel_data(self) -> Dict[str, pd.DataFrame]:
        """
        Liest alle relevanten Excel-Arbeitsblätter ein
        
        Returns
        -------
        dict
            Dictionary mit allen eingelesenen Daten
        """
        if not os.path.isfile(self.filename):
            raise FileNotFoundError(f"Excel-Datei {self.filename} nicht gefunden!")
            
        try:
            xls = pd.ExcelFile(self.filename)
            
            # Pflichtarbeitsblätter
            required_sheets = ['buses', 'sources', 'sinks', 'converters', 'timeseries']
            missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]
            
            if missing_sheets:
                raise ValueError(f"Fehlende Arbeitsblätter: {missing_sheets}")
            
            # Daten einlesen
            self.nodes_data = {
                'buses': xls.parse('buses'),
                'sources': xls.parse('sources'), 
                'sinks': xls.parse('sinks'),
                'converters': xls.parse('converters'),
                'timeseries': xls.parse('timeseries')
            }
            
            # Timeseries-Index verarbeiten
            self._process_timeseries()
            
            logging.info(f"Excel-Daten aus {self.filename} erfolgreich eingelesen")
            return self.nodes_data
            
        except Exception as e:
            logging.error(f"Fehler beim Einlesen der Excel-Datei: {e}")
            raise
    
    def _process_timeseries(self):
        """Verarbeitet das Timeseries-Arbeitsblatt"""
        ts_df = self.nodes_data['timeseries']
        
        # Prüfe ob timestamp Spalte existiert
        if 'timestamp' not in ts_df.columns:
            raise ValueError("Timeseries-Arbeitsblatt muss 'timestamp' Spalte enthalten!")
            
        # Setze timestamp als Index
        ts_df.set_index('timestamp', inplace=True)
        ts_df.index = pd.to_datetime(ts_df.index)
        
        self.timeseries_data = ts_df
        self.nodes_data['timeseries'] = ts_df
    
    def _parse_german_numbers(self, value: str) -> List[float]:
        """
        Konvertiert deutsche Zahlenformate (Komma als Dezimaltrennzeichen)
        
        Parameters
        ---------- 
        value : str
            String mit deutschen Zahlen (Semikolon-getrennt)
            
        Returns
        -------
        list
            Liste von Float-Werten
        """
        if pd.isna(value) or value == '':
            return []
            
        if isinstance(value, (int, float)):
            return [float(value)]
            
        # Semikolon-getrennte Werte verarbeiten
        values = str(value).split(';')
        result = []
        
        for val in values:
            val = val.strip()
            if val:
                # Deutsche Zahlenformatierung: Komma -> Punkt
                val = val.replace(',', '.')
                try:
                    result.append(float(val))
                except ValueError:
                    # Möglicherweise timeseries_keyword
                    result.append(val)
                    
        return result
    
    def _calculate_ep_costs(self, invest_cost: float, lifetime: int, interest_rate: float) -> float:
        """
        Berechnet Equivalent Periodical Costs (Annuität)
        
        Parameters
        ----------
        invest_cost : float
            Investitionskosten
        lifetime : int  
            Lebensdauer in Jahren
        interest_rate : float
            Zinssatz (als Dezimalzahl, z.B. 0.05 für 5%)
            
        Returns
        -------
        float
            EP-Costs (Annuität)
        """
        if interest_rate == 0:
            return invest_cost / lifetime
        else:
            return invest_cost * (interest_rate * (1 + interest_rate)**lifetime) / ((1 + interest_rate)**lifetime - 1)
    
    def _create_investment_args(self, row: pd.Series) -> Dict[str, Any]:
        """
        Erstellt Investment-Argumente aus Excel-Zeile
        
        Parameters
        ----------
        row : pd.Series
            Excel-Zeile mit Investment-Parametern
            
        Returns
        -------
        dict
            Investment-Argumente für oemof-solph
        """
        invest_args = {}
        
        # EP-Costs berechnen
        ep_costs = self._calculate_ep_costs(
            row['invest_cost'], 
            row['lifetime'], 
            row['interest_rate']
        )
        invest_args['ep_costs'] = ep_costs
        
        # Optional: min/max Investment
        if not pd.isna(row.get('min_invest')):
            invest_args['minimum'] = row['min_invest']
        if not pd.isna(row.get('max_invest')):
            invest_args['maximum'] = row['max_invest']
            
        # NonConvex Investment
        if row.get('nonconvex_investment', 0) == 1:
            invest_args['nonconvex'] = True
            
        return invest_args
    
    def _get_timeseries_data(self, keyword: str) -> Optional[pd.Series]:
        """
        Holt Zeitreihen-Daten anhand des Keywords
        
        Parameters
        ----------
        keyword : str
            Spaltenname in timeseries-Arbeitsblatt
            
        Returns
        -------
        pd.Series or None
            Zeitreihen-Daten oder None falls nicht gefunden
        """
        if keyword in self.timeseries_data.columns:
            return self.timeseries_data[keyword]
        else:
            logging.warning(f"Timeseries-Keyword '{keyword}' nicht gefunden!")
            return None
    
    def create_buses(self) -> Dict[str, Bus]:
        """
        Erstellt alle Bus-Objekte
        
        Returns
        -------
        dict
            Dictionary mit Bus-Objekten
        """
        buses_df = self.nodes_data['buses']
        buses = {}
        
        for _, row in buses_df.iterrows():
            if row.get('include', 1) == 1:  # Default: include=1
                bus = Bus(label=row['label'])
                buses[row['label']] = bus
                
        self.buses = buses
        logging.info(f"{len(buses)} Busse erstellt")
        return buses
    
    def create_sources(self) -> List[Source]:
        """
        Erstellt alle Source-Komponenten
        
        Returns
        -------
        list
            Liste mit Source-Objekten
        """
        sources_df = self.nodes_data['sources']
        sources = []
        
        for _, row in sources_df.iterrows():
            if row.get('include', 1) == 0:
                continue
                
            # Output-Busse verarbeiten
            output_labels = str(row['outputs']).split(';')
            output_labels = [label.strip() for label in output_labels if label.strip()]
            
            # Output-Relations verarbeiten
            output_relations = self._parse_german_numbers(row['output_relation'])
            
            # Flows erstellen
            outputs = {}
            for i, bus_label in enumerate(output_labels):
                if bus_label not in self.buses:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden für Source '{row['label']}'")
                
                # Flow-Parameter
                flow_args = {}
                
                # Nominal Capacity (nur für ersten Output)
                if i == 0:
                    if row.get('investment', 0) == 1:
                        invest_args = self._create_investment_args(row)
                        flow_args['nominal_capacity'] = Investment(**invest_args)
                    else:
                        flow_args['nominal_capacity'] = row.get('existing', 0)
                
                # Output Relation
                if i < len(output_relations):
                    relation = output_relations[i]
                    if isinstance(relation, str):
                        # Timeseries-Keyword
                        ts_data = self._get_timeseries_data(relation)
                        if ts_data is not None:
                            flow_args['fix'] = ts_data
                    else:
                        # Fester Wert
                        if i == 0:
                            flow_args['fix'] = relation if relation != 1.0 else None
                        else:
                            # Für weitere Outputs als conversion_factor
                            flow_args['conversion_factors'] = relation
                
                outputs[self.buses[bus_label]] = Flow(**flow_args)
            
            # Source erstellen
            source = Source(
                label=row['label'],
                outputs=outputs
            )
            sources.append(source)
        
        logging.info(f"{len(sources)} Sources erstellt")
        return sources
    
    def create_sinks(self) -> List[Sink]:
        """
        Erstellt alle Sink-Komponenten
        
        Returns
        -------
        list
            Liste mit Sink-Objekten
        """
        sinks_df = self.nodes_data['sinks']
        sinks = []
        
        for _, row in sinks_df.iterrows():
            if row.get('include', 1) == 0:
                continue
                
            # Input-Busse verarbeiten
            input_labels = str(row['inputs']).split(';')
            input_labels = [label.strip() for label in input_labels if label.strip()]
            
            # Input-Relations verarbeiten
            input_relations = self._parse_german_numbers(row['input_relation'])
            
            # Flows erstellen
            inputs = {}
            for i, bus_label in enumerate(input_labels):
                if bus_label not in self.buses:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden für Sink '{row['label']}'")
                
                # Flow-Parameter
                flow_args = {}
                
                # Nominal Capacity (nur für ersten Input)
                if i == 0:
                    if row.get('investment', 0) == 1:
                        invest_args = self._create_investment_args(row)
                        flow_args['nominal_capacity'] = Investment(**invest_args)
                    else:
                        flow_args['nominal_capacity'] = row.get('existing', 0)
                
                # Input Relation
                if i < len(input_relations):
                    relation = input_relations[i]
                    if isinstance(relation, str):
                        # Timeseries-Keyword
                        ts_data = self._get_timeseries_data(relation)
                        if ts_data is not None:
                            flow_args['fix'] = ts_data
                    else:
                        # Fester Wert
                        if i == 0:
                            flow_args['fix'] = relation if relation != 1.0 else None
                        else:
                            # Für weitere Inputs als conversion_factor
                            flow_args['conversion_factors'] = relation
                
                inputs[self.buses[bus_label]] = Flow(**flow_args)
            
            # Sink erstellen
            sink = Sink(
                label=row['label'],
                inputs=inputs
            )
            sinks.append(sink)
        
        logging.info(f"{len(sinks)} Sinks erstellt")
        return sinks
    
    def create_converters(self) -> List[Converter]:
        """
        Erstellt alle Converter-Komponenten
        
        Returns
        -------
        list
            Liste mit Converter-Objekten
        """
        converters_df = self.nodes_data['converters']
        converters = []
        
        for _, row in converters_df.iterrows():
            if row.get('include', 1) == 0:
                continue
                
            # Input/Output-Busse verarbeiten
            input_labels = str(row['inputs']).split(';')
            input_labels = [label.strip() for label in input_labels if label.strip()]
            
            output_labels = str(row['outputs']).split(';')
            output_labels = [label.strip() for label in output_labels if label.strip()]
            
            # Relations verarbeiten
            input_relations = self._parse_german_numbers(row['input_relation'])
            output_relations = self._parse_german_numbers(row['output_relation'])
            
            # Input-Flows erstellen
            inputs = {}
            for i, bus_label in enumerate(input_labels):
                if bus_label not in self.buses:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden für Converter '{row['label']}'")
                
                flow_args = {}
                if i < len(input_relations):
                    relation = input_relations[i]
                    if isinstance(relation, str):
                        ts_data = self._get_timeseries_data(relation)
                        if ts_data is not None:
                            flow_args['fix'] = ts_data
                    else:
                        if relation != 1.0:
                            flow_args['conversion_factors'] = relation
                
                inputs[self.buses[bus_label]] = Flow(**flow_args)
            
            # Output-Flows erstellen  
            outputs = {}
            for i, bus_label in enumerate(output_labels):
                if bus_label not in self.buses:
                    raise ValueError(f"Bus '{bus_label}' nicht gefunden für Converter '{row['label']}'")
                
                flow_args = {}
                
                # Nominal Capacity (nur für ersten Output)
                if i == 0:
                    if row.get('investment', 0) == 1:
                        invest_args = self._create_investment_args(row)
                        flow_args['nominal_capacity'] = Investment(**invest_args)
                    else:
                        flow_args['nominal_capacity'] = row.get('existing', 0)
                
                # Output Relation
                if i < len(output_relations):
                    relation = output_relations[i]
                    if isinstance(relation, str):
                        ts_data = self._get_timeseries_data(relation)
                        if ts_data is not None:
                            flow_args['fix'] = ts_data
                    else:
                        if relation != 1.0:
                            flow_args['conversion_factors'] = relation
                
                outputs[self.buses[bus_label]] = Flow(**flow_args)
            
            # Converter erstellen
            converter = Converter(
                label=row['label'],
                inputs=inputs,
                outputs=outputs
            )
            converters.append(converter)
        
        logging.info(f"{len(converters)} Converters erstellt")
        return converters
    
    def create_energy_system(self, timeindex: pd.DatetimeIndex) -> EnergySystem:
        """
        Erstellt das komplette Energiesystem
        
        Parameters
        ----------
        timeindex : pd.DatetimeIndex
            Zeitindex für die Simulation
            
        Returns
        -------
        EnergySystem
            Vollständiges Energiesystem
        """
        # Daten einlesen
        self.read_excel_data()
        
        # Komponenten erstellen
        buses = self.create_buses()
        sources = self.create_sources()
        sinks = self.create_sinks()
        converters = self.create_converters()
        
        # Energiesystem zusammenbauen
        all_components = list(buses.values()) + sources + sinks + converters
        
        energy_system = EnergySystem(
            timeindex=timeindex,
            infer_last_interval=False
        )
        
        energy_system.add(*all_components)
        
        logging.info(f"Energiesystem mit {len(all_components)} Komponenten erstellt")
        return energy_system


def create_energy_system_from_excel(filename: str, timeindex: pd.DatetimeIndex) -> EnergySystem:
    """
    Convenience-Funktion zum Erstellen eines Energiesystems aus Excel
    
    Parameters
    ----------
    filename : str
        Pfad zur Excel-Datei
    timeindex : pd.DatetimeIndex
        Zeitindex für die Simulation
        
    Returns
    -------
    solph.EnergySystem
        Energiesystem-Objekt
    """
    reader = FremofExcelReader(filename)
    return reader.create_energy_system(timeindex)


# Beispiel für die Verwendung
if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(level=logging.INFO)
    
    # Zeitindex definieren
    timeindex = pd.date_range(
        start='2024-01-01 00:00:00',
        end='2024-01-02 00:00:00', 
        freq='1h'
    )
    
    # Energiesystem aus Excel erstellen
    try:
        energy_system = create_energy_system_from_excel('fremof_simple_example.xlsx', timeindex)
        print("Energiesystem erfolgreich erstellt!")
        
        # Optional: Modell erstellen und lösen
        # model = solph.Model(energy_system)
        # model.solve(solver='cbc')
        # results = solph.processing.results(model)
        
    except Exception as e:
        print(f"Fehler: {e}")