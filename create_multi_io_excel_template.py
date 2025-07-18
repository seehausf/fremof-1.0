#!/usr/bin/env python3
"""
Multi-Input/Output Excel Template Creator
========================================

Erstellt Excel-Beispiele für Multi-IO-Energiesysteme:
1. BHKW-System (Gas → Strom + Wärme)
2. Wärmepumpen-System (Strom + Umwelt → Wärme)
3. Komplexes Multi-IO-System
4. Nahwärme mit CO2-Tracking

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import logging


class MultiIOExampleCreator:
    """
    Erstellt Excel-Beispiele für Multi-Input/Output-Systeme.
    """
    
    def __init__(self, output_dir: Path = Path("examples")):
        """
        Initialisiert den Example Creator.
        
        Args:
            output_dir: Ausgabeverzeichnis
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Numpy Seed für reproduzierbare Ergebnisse
        np.random.seed(42)
    
    def create_all_examples(self):
        """Erstellt alle Multi-IO-Beispiele."""
        self.logger.info("🏗️ Erstelle Multi-IO-Beispiele...")
        
        examples = [
            ("bhkw_system", "BHKW-System (Gas → Strom + Wärme)", self.create_bhkw_example),
            ("heatpump_system", "Wärmepumpen-System (Strom + Umwelt → Wärme)", self.create_heatpump_example),
            ("complex_multi_io", "Komplexes Multi-IO-System", self.create_complex_example),
            ("district_heating_co2", "Nahwärme mit CO2-Tracking", self.create_district_heating_example)
        ]
        
        created_files = []
        
        for filename, description, creator_func in examples:
            try:
                output_path = self.output_dir / f"{filename}.xlsx"
                creator_func(output_path)
                created_files.append((output_path, description))
                print(f"✅ {description}: {output_path}")
            except Exception as e:
                print(f"❌ Fehler bei {description}: {e}")
                self.logger.error(f"Fehler bei {description}: {e}")
        
        print(f"\n🎉 {len(created_files)} Multi-IO-Beispiele erstellt!")
        return created_files
    
    def create_bhkw_example(self, output_path: Path):
        """
        Erstellt BHKW-Beispiel: Gas → Strom + Wärme
        
        Args:
            output_path: Ausgabepfad
        """
        print(f"📝 Erstelle BHKW-Beispiel: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # 1. SETTINGS Sheet
            settings_df = pd.DataFrame({
                'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
                'Value': ['2025-01-01', 8760, 'h', 'cbc'],
                'Description': [
                    'Startdatum der Simulation',
                    'Anzahl Zeitschritte (1 Jahr)',
                    'Frequenz der Zeitschritte',
                    'Verwendeter Solver'
                ]
            })
            settings_df.to_excel(writer, sheet_name='settings', index=False)
            
            # 2. TIMESTEP_SETTINGS Sheet
            timestep_settings_df = self._create_timestep_settings_sheet()
            timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
            
            # 3. BUSES Sheet
            buses_df = pd.DataFrame({
                'label': ['el_bus', 'heat_bus', 'gas_bus'],
                'include': [1, 1, 1],
                'description': [
                    'Elektrobus für Stromerzeugung und -verbrauch',
                    'Wärmebus für Wärmeversorgung',
                    'Gasbus für Brennstoffversorgung'
                ]
            })
            buses_df.to_excel(writer, sheet_name='buses', index=False)
            
            # 4. SOURCES Sheet
            sources_df = pd.DataFrame({
                'label': ['grid_import', 'gas_supply'],
                'include': [1, 1],
                'output_bus': ['el_bus', 'gas_bus'],
                'existing': [0, 0],
                'investment': [0, 0],
                'variable_costs': [0.30, 0.06],
                'description': [
                    'Strombezug aus öffentlichem Netz',
                    'Erdgasversorgung'
                ]
            })
            sources_df.to_excel(writer, sheet_name='sources', index=False)
            
            # 5. SINKS Sheet
            sinks_df = pd.DataFrame({
                'label': ['el_load', 'heat_load', 'grid_export'],
                'include': [1, 1, 1],
                'input_bus': ['el_bus', 'heat_bus', 'el_bus'],
                'existing': [0, 0, 0],
                'investment': [0, 0, 0],
                'variable_costs': [0.0, 0.0, -0.08],
                'profile_column': ['el_load_profile', 'heat_load_profile', ''],
                'description': [
                    'Elektrische Last',
                    'Wärmelast',
                    'Stromeinspeisung ins öffentliche Netz'
                ]
            })
            sinks_df.to_excel(writer, sheet_name='sinks', index=False)
            
            # 6. SIMPLE_TRANSFORMERS Sheet (BHKW mit Multi-Output)
            transformers_df = pd.DataFrame({
                'label': ['chp_plant', 'gas_boiler'],
                'include': [1, 1],
                'input_bus': ['gas_bus', 'gas_bus'],
                'output_bus': ['el_bus|heat_bus', 'heat_bus'],  # Multi-Output für BHKW
                'output_conversion_factors': ['0.35|0.50', '0.90'],  # 35% Strom, 50% Wärme
                'existing': [0, 0],
                'investment': [1, 1],
                'investment_costs': [2000, 400],
                'invest_min': [0, 0],
                'invest_max': [500, 1000],
                'lifetime': [15, 20],
                'interest_rate': [0.04, 0.04],
                'variable_costs': [0.02, 0.01],
                'description': [
                    'Blockheizkraftwerk (Gas → Strom + Wärme)',
                    'Gas-Spitzenlastkessel'
                ]
            })
            transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
            
            # 7. TIMESERIES Sheet
            timeseries_df = self._create_bhkw_timeseries(8760)
            timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    def create_heatpump_example(self, output_path: Path):
        """
        Erstellt Wärmepumpen-Beispiel: Strom + Umweltwärme → Wärme
        
        Args:
            output_path: Ausgabepfad
        """
        print(f"📝 Erstelle Wärmepumpen-Beispiel: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # 1. SETTINGS Sheet
            settings_df = pd.DataFrame({
                'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
                'Value': ['2025-01-01', 8760, 'h', 'cbc'],
                'Description': [
                    'Startdatum der Simulation',
                    'Anzahl Zeitschritte (1 Jahr)',
                    'Frequenz der Zeitschritte',
                    'Verwendeter Solver'
                ]
            })
            settings_df.to_excel(writer, sheet_name='settings', index=False)
            
            # 2. TIMESTEP_SETTINGS Sheet
            timestep_settings_df = self._create_timestep_settings_sheet()
            timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
            
            # 3. BUSES Sheet
            buses_df = pd.DataFrame({
                'label': ['el_bus', 'heat_bus', 'ambient_heat_bus'],
                'include': [1, 1, 1],
                'description': [
                    'Elektrobus',
                    'Wärmebus für Hausheizung',
                    'Umweltwärme-Bus (Luft/Erde/Wasser)'
                ]
            })
            buses_df.to_excel(writer, sheet_name='buses', index=False)
            
            # 4. SOURCES Sheet
            sources_df = pd.DataFrame({
                'label': ['pv_plant', 'grid_import', 'ambient_heat'],
                'include': [1, 1, 1],
                'output_bus': ['el_bus', 'el_bus', 'ambient_heat_bus'],
                'existing': [0, 0, 0],
                'investment': [1, 0, 0],
                'investment_costs': [800, 0, 0],
                'invest_max': [50, 0, 0],
                'lifetime': [25, 0, 0],
                'interest_rate': [0.04, 0, 0],
                'variable_costs': [0.0, 0.30, 0.0],
                'profile_column': ['pv_profile', '', 'ambient_heat_profile'],
                'description': [
                    'PV-Anlage (Investment)',
                    'Strombezug aus öffentlichem Netz',
                    'Kostenlose Umweltwärme'
                ]
            })
            sources_df.to_excel(writer, sheet_name='sources', index=False)
            
            # 5. SINKS Sheet
            sinks_df = pd.DataFrame({
                'label': ['el_load', 'heat_load', 'grid_export'],
                'include': [1, 1, 1],
                'input_bus': ['el_bus', 'heat_bus', 'el_bus'],
                'existing': [0, 0, 0],
                'investment': [0, 0, 0],
                'variable_costs': [0.0, 0.0, -0.08],
                'profile_column': ['el_load_profile', 'heat_load_profile', ''],
                'description': [
                    'Elektrische Haushaltslast',
                    'Wärmebedarf für Heizung',
                    'Stromeinspeisung ins Netz'
                ]
            })
            sinks_df.to_excel(writer, sheet_name='sinks', index=False)
            
            # 6. SIMPLE_TRANSFORMERS Sheet (Wärmepumpe mit Multi-Input)
            transformers_df = pd.DataFrame({
                'label': ['heat_pump', 'electric_heater'],
                'include': [1, 1],
                'input_bus': ['el_bus|ambient_heat_bus', 'el_bus'],  # Multi-Input für Wärmepumpe
                'output_bus': ['heat_bus', 'heat_bus'],
                'input_conversion_factors': ['1.0|2.5', '1.0'],  # 1 kW Strom + 2.5 kW Umwelt
                'output_conversion_factors': ['3.5', '0.95'],  # 3.5 kW Wärme, 95% Effizienz
                'existing': [0, 0],
                'investment': [1, 1],
                'investment_costs': [1200, 300],
                'invest_min': [0, 0],
                'invest_max': [20, 15],
                'lifetime': [20, 15],
                'interest_rate': [0.04, 0.04],
                'variable_costs': [0.01, 0.02],
                'description': [
                    'Wärmepumpe (Strom + Umwelt → Wärme)',
                    'Elektrischer Heizstab (Backup)'
                ]
            })
            transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
            
            # 7. TIMESERIES Sheet
            timeseries_df = self._create_heatpump_timeseries(8760)
            timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    def create_complex_example(self, output_path: Path):
        """
        Erstellt komplexes Multi-IO-System.
        
        Args:
            output_path: Ausgabepfad
        """
        print(f"📝 Erstelle komplexes Multi-IO-System: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # 1. SETTINGS Sheet
            settings_df = pd.DataFrame({
                'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
                'Value': ['2025-01-01', 8760, 'h', 'cbc'],
                'Description': [
                    'Startdatum der Simulation',
                    'Anzahl Zeitschritte (1 Jahr)',
                    'Frequenz der Zeitschritte',
                    'Verwendeter Solver'
                ]
            })
            settings_df.to_excel(writer, sheet_name='settings', index=False)
            
            # 2. TIMESTEP_SETTINGS Sheet
            timestep_settings_df = self._create_timestep_settings_sheet()
            timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
            
            # 3. BUSES Sheet
            buses_df = pd.DataFrame({
                'label': ['el_bus', 'heat_bus', 'gas_bus', 'h2_bus', 'cooling_bus'],
                'include': [1, 1, 1, 1, 1],
                'description': [
                    'Elektrobus',
                    'Wärmebus',
                    'Gasbus',
                    'Wasserstoffbus',
                    'Kältebus'
                ]
            })
            buses_df.to_excel(writer, sheet_name='buses', index=False)
            
            # 4. SOURCES Sheet
            sources_df = pd.DataFrame({
                'label': ['pv_plant', 'wind_plant', 'grid_import', 'gas_supply'],
                'include': [1, 1, 1, 1],
                'output_bus': ['el_bus', 'el_bus', 'el_bus', 'gas_bus'],
                'existing': [0, 0, 0, 0],
                'investment': [1, 1, 0, 0],
                'investment_costs': [800, 1200, 0, 0],
                'invest_max': [200, 100, 0, 0],
                'lifetime': [25, 20, 0, 0],
                'interest_rate': [0.04, 0.04, 0, 0],
                'variable_costs': [0.0, 0.0, 0.30, 0.06],
                'profile_column': ['pv_profile', 'wind_profile', '', ''],
                'description': [
                    'PV-Anlage',
                    'Windkraftanlage',
                    'Strombezug aus Netz',
                    'Gasversorgung'
                ]
            })
            sources_df.to_excel(writer, sheet_name='sources', index=False)
            
            # 5. SINKS Sheet
            sinks_df = pd.DataFrame({
                'label': ['el_load', 'heat_load', 'cooling_load', 'h2_demand', 'grid_export'],
                'include': [1, 1, 1, 1, 1],
                'input_bus': ['el_bus', 'heat_bus', 'cooling_bus', 'h2_bus', 'el_bus'],
                'existing': [0, 0, 0, 0, 0],
                'investment': [0, 0, 0, 0, 0],
                'variable_costs': [0.0, 0.0, 0.0, 0.0, -0.08],
                'profile_column': ['el_load_profile', 'heat_load_profile', 'cooling_load_profile', 'h2_demand_profile', ''],
                'description': [
                    'Elektrische Last',
                    'Wärmelast',
                    'Kältelast',
                    'Wasserstoffbedarf',
                    'Stromeinspeisung'
                ]
            })
            sinks_df.to_excel(writer, sheet_name='sinks', index=False)
            
            # 6. SIMPLE_TRANSFORMERS Sheet (Komplexe Multi-IO-Transformers)
            transformers_df = pd.DataFrame({
                'label': ['chp_plant', 'electrolyzer', 'fuel_cell', 'trigeneration'],
                'include': [1, 1, 1, 1],
                'input_bus': ['gas_bus', 'el_bus', 'h2_bus', 'gas_bus'],
                'output_bus': ['el_bus|heat_bus', 'h2_bus', 'el_bus|heat_bus', 'el_bus|heat_bus|cooling_bus'],
                'output_conversion_factors': ['0.35|0.50', '0.70', '0.50|0.35', '0.30|0.45|0.15'],
                'existing': [0, 0, 0, 0],
                'investment': [1, 1, 1, 1],
                'investment_costs': [2000, 1500, 2500, 3000],
                'invest_max': [200, 50, 100, 150],
                'lifetime': [15, 15, 15, 20],
                'interest_rate': [0.04, 0.04, 0.04, 0.04],
                'variable_costs': [0.02, 0.02, 0.03, 0.025],
                'description': [
                    'BHKW (Gas → Strom + Wärme)',
                    'Elektrolyseur (Strom → Wasserstoff)',
                    'Brennstoffzelle (Wasserstoff → Strom + Wärme)',
                    'Trigeneration (Gas → Strom + Wärme + Kälte)'
                ]
            })
            transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
            
            # 7. TIMESERIES Sheet
            timeseries_df = self._create_complex_timeseries(8760)
            timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    def create_district_heating_example(self, output_path: Path):
        """
        Erstellt Nahwärme-Beispiel mit CO2-Tracking.
        
        Args:
            output_path: Ausgabepfad
        """
        print(f"📝 Erstelle Nahwärme mit CO2-Tracking: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # 1. SETTINGS Sheet
            settings_df = pd.DataFrame({
                'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
                'Value': ['2025-01-01', 8760, 'h', 'cbc'],
                'Description': [
                    'Startdatum der Simulation',
                    'Anzahl Zeitschritte (1 Jahr)',
                    'Frequenz der Zeitschritte',
                    'Verwendeter Solver'
                ]
            })
            settings_df.to_excel(writer, sheet_name='settings', index=False)
            
            # 2. TIMESTEP_SETTINGS Sheet
            timestep_settings_df = self._create_timestep_settings_sheet()
            timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
            
            # 3. BUSES Sheet (mit CO2-Bus)
            buses_df = pd.DataFrame({
                'label': ['el_bus', 'heat_bus', 'gas_bus', 'biomass_bus', 'co2_bus'],
                'include': [1, 1, 1, 1, 1],
                'description': [
                    'Elektrobus',
                    'Nahwärme-Bus',
                    'Gasbus',
                    'Biomasse-Bus',
                    'CO2-Emissionen-Bus (Tracking)'
                ]
            })
            buses_df.to_excel(writer, sheet_name='buses', index=False)
            
            # 4. SOURCES Sheet
            sources_df = pd.DataFrame({
                'label': ['grid_import', 'gas_supply', 'biomass_supply'],
                'include': [1, 1, 1],
                'output_bus': ['el_bus', 'gas_bus|co2_bus', 'biomass_bus'],  # Gas mit CO2
                'output_conversion_factors': ['1.0', '1.0|0.2', '1.0'],  # 0.2 kg CO2/kWh Gas
                'existing': [0, 0, 0],
                'investment': [0, 0, 0],
                'variable_costs': [0.30, 0.06, 0.04],
                'description': [
                    'Strombezug aus Netz',
                    'Gasversorgung (mit CO2-Emission)',
                    'Biomasse-Versorgung (CO2-neutral)'
                ]
            })
            sources_df.to_excel(writer, sheet_name='sources', index=False)
            
            # 5. SINKS Sheet
            sinks_df = pd.DataFrame({
                'label': ['district_heat_load', 'grid_export', 'co2_emissions'],
                'include': [1, 1, 1],
                'input_bus': ['heat_bus', 'el_bus', 'co2_bus'],
                'existing': [0, 0, 0],
                'investment': [0, 0, 0],
                'variable_costs': [0.0, -0.08, 25.0],  # 25 €/t CO2-Preis
                'profile_column': ['district_heat_profile', '', ''],
                'description': [
                    'Nahwärme-Bedarf',
                    'Stromeinspeisung',
                    'CO2-Emissionen (mit CO2-Preis)'
                ]
            })
            sinks_df.to_excel(writer, sheet_name='sinks', index=False)
            
            # 6. SIMPLE_TRANSFORMERS Sheet
            transformers_df = pd.DataFrame({
                'label': ['gas_chp', 'biomass_chp', 'gas_boiler', 'electric_boiler'],
                'include': [1, 1, 1, 1],
                'input_bus': ['gas_bus', 'biomass_bus', 'gas_bus', 'el_bus'],
                'output_bus': ['el_bus|heat_bus|co2_bus', 'el_bus|heat_bus', 'heat_bus|co2_bus', 'heat_bus'],
                'output_conversion_factors': ['0.35|0.50|0.18', '0.30|0.60', '0.90|0.20', '0.95'],
                'existing': [0, 0, 0, 0],
                'investment': [1, 1, 1, 1],
                'investment_costs': [2000, 2500, 400, 200],
                'invest_max': [300, 200, 500, 100],
                'lifetime': [15, 20, 20, 15],
                'interest_rate': [0.04, 0.04, 0.04, 0.04],
                'variable_costs': [0.02, 0.015, 0.01, 0.005],
                'description': [
                    'Gas-BHKW (mit CO2-Emission)',
                    'Biomasse-BHKW (CO2-neutral)',
                    'Gas-Kessel (mit CO2-Emission)',
                    'Elektro-Kessel (strombasiert)'
                ]
            })
            transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
            
            # 7. TIMESERIES Sheet
            timeseries_df = self._create_district_heating_timeseries(8760)
            timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    def _create_timestep_settings_sheet(self) -> pd.DataFrame:
        """Erstellt Standard-Timestep-Settings-Sheet."""
        return pd.DataFrame({
            'Parameter': [
                'enabled',
                'timestep_strategy',
                'averaging_hours',
                'sampling_n_factor',
                'time_range_start',
                'time_range_end',
                'create_visualization'
            ],
            'Value': [
                'False',
                'full',
                '24',
                '4',
                '2025-07-01 00:00',
                '2025-09-30 23:00',
                'True'
            ],
            'Description': [
                'Timestep-Management aktivieren',
                'Strategie: full/averaging/sampling_24n/time_range',
                'Stunden für Averaging-Strategie',
                'Sampling-Faktor (jede n-te Stunde)',
                'Startzeit für Time-Range-Strategie',
                'Endzeit für Time-Range-Strategie',
                'Timestep-Visualisierung erstellen'
            ]
        })
    
    def _create_bhkw_timeseries(self, periods: int) -> pd.DataFrame:
        """Erstellt Zeitreihen für BHKW-Beispiel."""
        timestamps = pd.date_range('2025-01-01', periods=periods, freq='h')
        
        # Elektrische Last (Industriebetrieb)
        el_load = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            weekday = ts.weekday()  # 0=Montag, 6=Sonntag
            
            # Basis-Last
            if weekday < 5:  # Werktag
                if 6 <= hour <= 18:
                    base_load = 80 + 20 * np.sin((hour - 6) * np.pi / 12)
                else:
                    base_load = 30
            else:  # Wochenende
                base_load = 20
            
            # Zufällige Variation
            load = base_load * (0.8 + 0.4 * np.random.random())
            el_load.append(load)
        
        # Wärme-Last (Gebäudeheizung)
        heat_load = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Temperaturmodell
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp = 3 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp
            
            # Heizlast
            if temperature < 16:
                heat_factor = (20 - temperature) / 15
            else:
                heat_factor = 0.1  # Warmwasser
            
            heat = 60 * heat_factor * (0.9 + 0.2 * np.random.random())
            heat_load.append(max(5, heat))
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'el_load_profile': el_load,
            'heat_load_profile': heat_load
        })
    
    def _create_heatpump_timeseries(self, periods: int) -> pd.DataFrame:
        """Erstellt Zeitreihen für Wärmepumpen-Beispiel."""
        timestamps = pd.date_range('2025-01-01', periods=periods, freq='h')
        
        # PV-Profil
        pv_profile = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Tageszeitfaktor
            if 6 <= hour <= 18:
                daily_factor = np.sin((hour - 6) * np.pi / 12)
            else:
                daily_factor = 0
            
            # Jahreszeitfaktor
            seasonal_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            
            # Wetter-Variation
            weather_factor = 0.7 + 0.3 * np.random.random()
            
            pv_value = daily_factor * seasonal_factor * weather_factor
            pv_profile.append(max(0, pv_value))
        
        # Umweltwärme-Profil (temperaturabhängig)
        ambient_heat = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Temperaturmodell
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp = 3 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp
            
            # Umweltwärme verfügbar (normalisiert)
            # Bei -10°C: 0.5, bei 20°C: 1.0
            heat_availability = 0.5 + 0.5 * (temperature + 10) / 30
            ambient_heat.append(max(0.3, min(1.0, heat_availability)))
        
        # Elektrische Haushaltslast
        el_load = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            
            # Tageszeitfaktor
            if 6 <= hour <= 8 or 17 <= hour <= 22:
                time_factor = 1.5
            elif 9 <= hour <= 16:
                time_factor = 1.0
            else:
                time_factor = 0.7
            
            load = 3.0 * time_factor * (0.8 + 0.4 * np.random.random())
            el_load.append(load)
        
        # Wärme-Last (Heizung)
        heat_load = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Temperaturmodell (gleich wie oben)
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp = 3 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp
            
            # Heizlast
            if temperature < 16:
                heat_factor = (20 - temperature) / 15
            else:
                heat_factor = 0.15  # Warmwasser
            
            heat = 8.0 * heat_factor * (0.9 + 0.2 * np.random.random())
            heat_load.append(max(1, heat))
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'pv_profile': pv_profile,
            'ambient_heat_profile': ambient_heat,
            'el_load_profile': el_load,
            'heat_load_profile': heat_load
        })
    
    def _create_complex_timeseries(self, periods: int) -> pd.DataFrame:
        """Erstellt Zeitreihen für komplexes System."""
        timestamps = pd.date_range('2025-01-01', periods=periods, freq='h')
        
        # PV-Profil
        pv_profile = []
        wind_profile = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # PV
            if 6 <= hour <= 18:
                pv_daily = np.sin((hour - 6) * np.pi / 12)
            else:
                pv_daily = 0
            
            pv_seasonal = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            pv_weather = 0.7 + 0.3 * np.random.random()
            pv_profile.append(max(0, pv_daily * pv_seasonal * pv_weather))
            
            # Wind (weniger tageszeitabhängig)
            wind_base = 0.3 + 0.4 * np.sin((day_of_year - 200) * 2 * np.pi / 365)  # Mehr Wind im Winter
            wind_variation = 0.5 + np.random.random()
            wind_profile.append(max(0, min(1, wind_base * wind_variation)))
        
        # Verschiedene Lasten
        el_load = []
        heat_load = []
        cooling_load = []
        h2_demand = []
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Temperaturmodell
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp = 3 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp
            
            # Elektrische Last
            if 6 <= hour <= 22:
                el_factor = 1.2
            else:
                el_factor = 0.8
            el_load.append(50 * el_factor * (0.9 + 0.2 * np.random.random()))
            
            # Heizlast
            if temperature < 16:
                heat_factor = (20 - temperature) / 15
            else:
                heat_factor = 0.1
            heat_load.append(40 * heat_factor * (0.9 + 0.2 * np.random.random()))
            
            # Kühllast
            if temperature > 22:
                cool_factor = (temperature - 22) / 10
            else:
                cool_factor = 0
            cooling_load.append(20 * cool_factor * (0.9 + 0.2 * np.random.random()))
            
            # H2-Bedarf (konstanter mit Variation)
            h2_demand.append(10 * (0.8 + 0.4 * np.random.random()))
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'pv_profile': pv_profile,
            'wind_profile': wind_profile,
            'el_load_profile': el_load,
            'heat_load_profile': heat_load,
            'cooling_load_profile': cooling_load,
            'h2_demand_profile': h2_demand
        })
    
    def _create_district_heating_timeseries(self, periods: int) -> pd.DataFrame:
        """Erstellt Zeitreihen für Nahwärme-Beispiel."""
        timestamps = pd.date_range('2025-01-01', periods=periods, freq='h')
        
        # Nahwärme-Profil (größer als Einzelhaus)
        district_heat = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            weekday = ts.weekday()
            
            # Temperaturmodell
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp = 3 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp
            
            # Heizlast
            if temperature < 16:
                heat_factor = (20 - temperature) / 15
            else:
                heat_factor = 0.2  # Warmwasser
            
            # Tageszeitfaktor
            if 6 <= hour <= 22:
                time_factor = 1.2
            else:
                time_factor = 0.8
            
            # Wochentag-Faktor
            if weekday < 5:
                week_factor = 1.0
            else:
                week_factor = 0.9
            
            heat = 300 * heat_factor * time_factor * week_factor * (0.9 + 0.2 * np.random.random())
            district_heat.append(max(50, heat))
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'district_heat_profile': district_heat
        })


def main():
    """Hauptfunktion."""
    logging.basicConfig(level=logging.INFO)
    
    print("🏗️ Multi-Input/Output Excel Template Creator")
    print("=" * 60)
    
    # Output-Verzeichnis
    output_dir = Path("examples")
    
    # Creator erstellen
    creator = MultiIOExampleCreator(output_dir)
    
    # Alle Beispiele erstellen
    try:
        created_files = creator.create_all_examples()
        
        print(f"\n📊 ÜBERSICHT DER ERSTELLTEN BEISPIELE:")
        print("=" * 60)
        
        for i, (file_path, description) in enumerate(created_files, 1):
            print(f"{i}. {description}")
            print(f"   📄 Datei: {file_path}")
            print(f"   📁 Größe: {file_path.stat().st_size / 1024:.1f} KB")
            print()
        
        print("🎯 VERWENDUNG:")
        print("1. Öffnen Sie die Excel-Dateien zur Inspektion")
        print("2. Verwenden Sie python runme.py für die Ausführung")
        print("3. Passen Sie die Parameter nach Bedarf an")
        print("4. Testen Sie Multi-Input/Output-Funktionalität")
        
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der Beispiele: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
