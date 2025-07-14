#!/usr/bin/env python3
"""
Excel-Vorlage Creator für Timestep-Management Tests
=================================================

Erstellt eine einfache Excel-Vorlage zum Testen des Timestep-Managements.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def create_test_excel_with_timestep_management(output_path: Path):
    """
    Erstellt eine Test-Excel-Datei mit Timestep-Management-Konfiguration.
    
    Args:
        output_path: Pfad für die Excel-Datei
    """
    print(f"📝 Erstelle Test-Excel-Datei: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # 1. BUSES Sheet
        buses_df = pd.DataFrame({
            'label': ['el_bus', 'heat_bus'],
            'include': [1, 1],
            'description': ['Electricity Bus', 'Heat Bus']
        })
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        print("   ✅ Buses Sheet erstellt")
        
        # 2. SOURCES Sheet
        sources_df = pd.DataFrame({
            'label': ['pv_plant', 'grid_import', 'gas_boiler'],
            'include': [1, 1, 1],
            'bus': ['el_bus', 'el_bus', 'heat_bus'],
            'nominal_capacity': [100, 'INVEST', 50],
            'variable_costs': [0.0, 0.25, 0.08],
            'profile_column': ['pv_profile', '', ''],
            'investment_costs': ['', 800, ''],
            'invest_min': ['', 0, ''],
            'invest_max': ['', 200, ''],
            'description': ['PV Solar Plant', 'Grid Import', 'Gas Boiler']
        })
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        print("   ✅ Sources Sheet erstellt")
        
        # 3. SINKS Sheet  
        sinks_df = pd.DataFrame({
            'label': ['el_load', 'heat_load', 'grid_export'],
            'include': [1, 1, 1],
            'bus': ['el_bus', 'heat_bus', 'el_bus'],
            'profile_column': ['el_demand_profile', 'heat_demand_profile', ''],
            'variable_costs': [0, 0, -0.05],
            'description': ['Electrical Load', 'Heat Load', 'Grid Export']
        })
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        print("   ✅ Sinks Sheet erstellt")
        
        # 4. SIMPLE_TRANSFORMERS Sheet
        transformers_df = pd.DataFrame({
            'label': ['heat_pump'],
            'include': [1],
            'input_bus': ['el_bus'],
            'output_bus': ['heat_bus'],
            'conversion_factor': [3.0],
            'nominal_capacity': [30],
            'variable_costs': [0.02],
            'description': ['Heat Pump']
        })
        transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
        print("   ✅ Simple Transformers Sheet erstellt")
        
        # 5. TIMESERIES Sheet (1 Jahr, stündlich)
        print("   🕒 Erstelle Zeitreihen-Daten (365 Tage)...")
        timestamps = pd.date_range('2025-01-01', periods=8760, freq='h')
        
        # PV-Profil (Sinus-basiert mit tageszeitlicher Variation)
        pv_profile = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Tageszeitfaktor (Sinus, Peak um 12 Uhr)
            daily_factor = max(0, np.sin((hour - 6) * np.pi / 12))
            
            # Jahreszeitfaktor (mehr Sonne im Sommer)
            seasonal_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            
            # Zufällige Wolken-Variation
            cloud_factor = 0.7 + 0.3 * np.random.random()
            
            pv_value = daily_factor * seasonal_factor * cloud_factor
            pv_profile.append(pv_value)
        
        # Elektrische Last (Haushalts-typisch)
        el_demand_profile = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Basis-Last
            base_load = 5.0  # kW
            
            # Tageszeitfaktor (Morgens und Abends höher)
            if 6 <= hour <= 8 or 17 <= hour <= 22:
                time_factor = 1.8  # Spitzenzeiten
            elif 9 <= hour <= 16:
                time_factor = 1.2  # Tagzeit
            else:
                time_factor = 0.8  # Nachts
            
            # Jahreszeitfaktor (Winter mehr Verbrauch)
            seasonal_factor = 1.0 + 0.3 * np.sin((day_of_year + 180) * 2 * np.pi / 365)
            
            # Zufällige Variation
            random_factor = 0.8 + 0.4 * np.random.random()
            
            demand_value = base_load * time_factor * seasonal_factor * random_factor
            el_demand_profile.append(demand_value)
        
        # Wärme-Last (stark temperaturabhängig)
        heat_demand_profile = []
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            day_of_year = ts.dayofyear
            
            # Basis-Wärmebedarf
            base_heat = 8.0  # kW
            
            # Außentemperatur schätzen (vereinfacht)
            avg_temp = 10 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            daily_temp_variation = 5 * np.sin((hour - 14) * 2 * np.pi / 24)
            temperature = avg_temp + daily_temp_variation
            
            # Heizgrenze bei 15°C
            if temperature < 15:
                heat_factor = (20 - temperature) / 10
            else:
                heat_factor = 0.1  # Grundlast (Warmwasser)
            
            heat_value = base_heat * heat_factor * (0.9 + 0.2 * np.random.random())
            heat_demand_profile.append(max(0, heat_value))
        
        # Zeitreihen-DataFrame
        timeseries_df = pd.DataFrame({
            'timestamp': timestamps,
            'pv_profile': pv_profile,
            'el_demand_profile': el_demand_profile,
            'heat_demand_profile': heat_demand_profile
        })
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
        print("   ✅ Timeseries Sheet erstellt (8760 Zeitschritte)")
        
        # 6. SETTINGS Sheet
        settings_df = pd.DataFrame({
            'Parameter': ['solver', 'timeindex_start', 'timeindex_periods', 'timeindex_freq'],
            'Value': ['cbc', '2025-01-01', 8760, 'h'],
            'Description': ['Optimization Solver', 'Start Date', 'Number of Periods', 'Frequency']
        })
        settings_df.to_excel(writer, sheet_name='settings', index=False)
        print("   ✅ Settings Sheet erstellt")
        
        # 7. TIMESTEP_SETTINGS Sheet - VERSCHIEDENE BEISPIELE
        timestep_examples = {
            'Full Resolution': {
                'enabled': 'false',
                'timestep_strategy': 'full',
                'description': 'Vollständige Zeitauflösung (8760h)'
            },
            'Time Range': {
                'enabled': 'false',
                'timestep_strategy': 'time_range',
                'start_date': '2025-07-01',
                'end_date': '2025-07-31',
                'description': 'Nur Juli (744h)'
            },
            'Averaging 4h': {
                'enabled': 'true',  # STANDARDMÄSSIG AKTIVIERT
                'timestep_strategy': 'averaging',
                'hours': 4,
                'description': '4-Stunden Mittelwerte (2190h)'
            },
            'Sampling Weekly': {
                'enabled': 'false',
                'timestep_strategy': 'sampling_24n',
                'n': 24,
                'description': 'Wöchentliches Sampling (365h)'
            }
        }
        
        # Standard-Konfiguration (erste Zeile wird verwendet)
        timestep_df = pd.DataFrame({
            'Parameter': ['enabled', 'timestep_strategy', 'hours', 'description'],
            'Value': ['true', 'averaging', 4, '4-Stunden Mittelwerte'],
            'Alternative_1': ['false', 'time_range', '', 'Nur Juli'],
            'start_date': ['', '2025-07-01', '', ''],
            'end_date': ['', '2025-07-31', '', ''],
            'Alternative_2': ['false', 'sampling_24n', '', 'Wöchentlich'],
            'n': ['', '', '', 24]
        })
        timestep_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        print("   ✅ Timestep Settings Sheet erstellt")
        
        # 8. DOCUMENTATION Sheet
        doc_df = pd.DataFrame({
            'Sheet': ['timestep_settings', 'timestep_settings', 'timestep_settings', 
                     'timestep_settings', 'timestep_settings', 'timestep_settings'],
            'Parameter': ['enabled', 'timestep_strategy', 'hours', 'start_date', 'end_date', 'n'],
            'Description': [
                'Aktiviert/Deaktiviert Timestep-Management (true/false)',
                'Strategie: full, time_range, averaging, sampling_24n',
                'Für averaging: Stunden pro Mittelwert (4,6,8,12,24,48)',
                'Für time_range: Start-Datum (YYYY-MM-DD)',
                'Für time_range: End-Datum (YYYY-MM-DD)',
                'Für sampling_24n: Sampling-Faktor (0.5, 1, 2, 24, etc.)'
            ],
            'Example': ['true', 'averaging', '4', '2025-07-01', '2025-07-31', '24']
        })
        doc_df.to_excel(writer, sheet_name='documentation', index=False)
        print("   ✅ Documentation Sheet erstellt")
    
    print(f"✅ Test-Excel-Datei erfolgreich erstellt: {output_path}")
    print("\n📋 ANLEITUNG:")
    print("1. Öffnen Sie die Excel-Datei")
    print("2. Gehen Sie zum 'timestep_settings' Sheet")
    print("3. Setzen Sie 'enabled' auf 'true' um Timestep-Management zu aktivieren")
    print("4. Wählen Sie eine 'timestep_strategy':")
    print("   - 'full': Vollständige Zeitauflösung (8760h)")
    print("   - 'averaging': Mittelwerte bilden (Parameter: hours)")
    print("   - 'time_range': Zeitbereich wählen (Parameter: start_date, end_date)")
    print("   - 'sampling_24n': Sampling (Parameter: n)")
    print("5. Passen Sie die entsprechenden Parameter an")
    print("6. Speichern Sie die Datei und führen Sie Ihre Python-Analyse aus")


def create_multiple_test_scenarios(base_path: Path):
    """Erstellt mehrere Test-Szenarien für verschiedene Timestep-Strategien."""
    
    scenarios = {
        'test_full.xlsx': {
            'enabled': 'false',
            'strategy': 'full',
            'params': {}
        },
        'test_averaging_4h.xlsx': {
            'enabled': 'true',
            'strategy': 'averaging',
            'params': {'hours': 4}
        },
        'test_time_range.xlsx': {
            'enabled': 'true',
            'strategy': 'time_range',
            'params': {'start_date': '2025-06-01', 'end_date': '2025-08-31'}
        },
        'test_sampling.xlsx': {
            'enabled': 'true',
            'strategy': 'sampling_24n',
            'params': {'n': 24}
        }
    }
    
    for filename, config in scenarios.items():
        filepath = base_path / filename
        create_test_excel_with_timestep_management(filepath)
        
        # Timestep-Settings anpassen
        print(f"📝 Passe {filename} für Szenario '{config['strategy']}' an...")
        
        # Excel neu öffnen und timestep_settings anpassen
        with pd.ExcelWriter(filepath, mode='a', if_sheet_exists='replace', engine='openpyxl') as writer:
            timestep_params = ['enabled', 'timestep_strategy']
            timestep_values = [config['enabled'], config['strategy']]
            
            # Strategie-spezifische Parameter hinzufügen
            for param, value in config['params'].items():
                timestep_params.append(param)
                timestep_values.append(value)
            
            timestep_df = pd.DataFrame({
                'Parameter': timestep_params,
                'Value': timestep_values
            })
            timestep_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        
        print(f"   ✅ {filename} konfiguriert für '{config['strategy']}'")


if __name__ == "__main__":
    # Erstelle Beispiel-Excel-Datei
    output_path = Path("test_timestep_management.xlsx")
    create_test_excel_with_timestep_management(output_path)
    
    print("\n" + "="*60)
    print("TESTANLEITUNG:")
    print("="*60)
    print("1. Führen Sie dieses Skript aus: python excel_template_creator.py")
    print("2. Öffnen Sie test_timestep_management.xlsx")
    print("3. Ändern Sie im 'timestep_settings' Sheet die Parameter:")
    print("   - enabled: true/false")
    print("   - timestep_strategy: full/averaging/time_range/sampling_24n") 
    print("   - je nach Strategie weitere Parameter")
    print("4. Testen Sie mit dem verbesserten excel_reader.py")
    print("\nVORGEFERTIGTE SZENARIEN erstellen:")
    print("Auskommentieren Sie die nächste Zeile um mehrere Test-Dateien zu erstellen")
    # create_multiple_test_scenarios(Path("."))