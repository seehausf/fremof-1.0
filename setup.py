#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Setup und Beispiel-Generierung
===============================================

Erstellt die Projektstruktur und generiert drei Beispiel-Excel-Dateien
für unterschiedliche Komplexitätsstufen der Energiesystemmodellierung.

NEU: Timestep-Management für flexible Zeitauflösungen

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml

# Projektverzeichnisse
PROJECT_ROOT = Path(__file__).parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
MODULES_DIR = PROJECT_ROOT / "modules"


def setup_project_structure():
    """Erstellt die vollständige Projektstruktur."""
    print("🏗️  Erstelle Projektstruktur...")
    
    # Verzeichnisse erstellen
    directories = [
        EXAMPLES_DIR,
        DATA_DIR / "input",
        DATA_DIR / "output", 
        CONFIG_DIR,
        MODULES_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   📁 {directory}")
    
    # __init__.py für modules Verzeichnis
    init_file = MODULES_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""oemof.solph 0.6.0 Projektmodule"""', encoding='utf-8')
    
    # Standard-Konfigurationsdatei
    config_file = CONFIG_DIR / "settings.yaml"
    if not config_file.exists():
        default_config = {
            'modules': {
                'excel_reader': True,
                'system_builder': True,
                'optimizer': True,
                'results_processor': True,
                'visualizer': False,
                'analyzer': False
            },
            'settings': {
                'solver': 'cbc',
                'output_format': 'xlsx',
                'create_plots': False,
                'save_model': False,
                'debug_mode': False
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        print(f"   ⚙️  Standard-Konfiguration: {config_file}")
    
    print("✅ Projektstruktur erstellt")


def create_timeindex(start_date="2025-01-01", periods=8760, freq="h"):
    """Erstellt einen Zeitindex für die Beispiele."""
    return pd.date_range(start=start_date, periods=periods, freq=freq)


def create_load_profile(timeindex, annual_demand=1000, profile_type="residential"):
    """Erstellt ein Lastprofil basierend auf dem Typ."""
    hours = len(timeindex)
    
    if profile_type == "residential":
        # Typisches Wohnlastprofil
        base_load = 0.3
        day_factor = np.array([0.7, 0.6, 0.6, 0.6, 0.7, 0.9, 1.2, 1.4, 1.1, 0.9, 0.8, 0.8,
                              0.9, 0.8, 0.8, 0.9, 1.1, 1.4, 1.6, 1.5, 1.3, 1.1, 0.9, 0.8])
        
        profile = []
        for i, timestamp in enumerate(timeindex):
            hour = timestamp.hour
            day_of_year = timestamp.timetuple().tm_yday
            
            # Saisonale Variation
            seasonal_factor = 1 + 0.3 * np.cos(2 * np.pi * (day_of_year - 30) / 365)
            
            # Wochentag/Wochenende
            weekend_factor = 0.9 if timestamp.weekday() >= 5 else 1.0
            
            # Zufällige Variation
            random_factor = 1 + 0.1 * (np.random.random() - 0.5)
            
            load = (base_load + day_factor[hour]) * seasonal_factor * weekend_factor * random_factor
            profile.append(load)
        
        # Normalisieren auf jährlichen Bedarf
        profile = np.array(profile)
        profile = profile / profile.sum() * annual_demand
        
    elif profile_type == "industrial":
        # Industrielles Lastprofil (relativ konstant)
        base_load = 0.8
        variation = 0.2
        profile = base_load + variation * np.random.random(hours)
        profile = profile / profile.sum() * annual_demand
        
    else:  # constant
        profile = np.full(hours, annual_demand / hours)
    
    return profile


def create_renewable_profile(timeindex, technology="pv", capacity_factor=0.15):
    """Erstellt Profile für erneuerbare Energien."""
    hours = len(timeindex)
    
    if technology == "pv":
        # PV-Profil
        profile = []
        for timestamp in timeindex:
            hour = timestamp.hour
            day_of_year = timestamp.timetuple().tm_yday
            
            # Nur tagsüber
            if 6 <= hour <= 18:
                # Saisonale Variation
                seasonal = 1 + 0.5 * np.cos(2 * np.pi * (day_of_year - 172) / 365)
                
                # Tagesverlauf (Sinuskurve)
                daily = np.sin(np.pi * (hour - 6) / 12)
                
                # Zufällige Wolken
                cloud_factor = 0.3 + 0.7 * np.random.random()
                
                output = seasonal * daily * cloud_factor
            else:
                output = 0
            
            profile.append(max(0, output))
        
    elif technology == "wind":
        # Wind-Profil (Weibull-ähnlich)
        np.random.seed(42)  # Für Reproduzierbarkeit
        profile = np.random.weibull(2, hours) * 2
        profile = np.clip(profile, 0, 1)
        
    else:  # constant
        profile = np.full(hours, capacity_factor)
    
    return np.array(profile)


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
            'False'
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
            'averaging (6h-Mittelwerte für schnelle Analyse)',
            '2025-01-01 00:00 (Start der Simulation)',
            '2025-01-31 23:00 (Ende der Simulation)',
            '6 (6-Stunden-Mittelwerte, 75% Zeitersparnis)',
            '0.25 (alle 6h), 1 (stündlich), 4 (alle 4h)',
            'True (aktiviert), False (deaktiviert)'
        ]
    })
    
    return timestep_settings


def create_example_1_simple():
    """Erstellt Beispiel 1: Einfaches System (PV + Netz + Last)."""
    print("📋 Erstelle Beispiel 1: Einfaches System...")
    
    # Zeitindex für eine Woche
    timeindex = create_timeindex(periods=168, freq="h")  # 1 Woche
    
    # Excel-Datei erstellen
    filename = EXAMPLES_DIR / "example_1.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # Settings Sheet
        settings_df = pd.DataFrame({
            'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
            'Value': ['2025-01-01', 168, 'h', 'cbc'],
            'Description': [
                'Startdatum der Simulation',
                'Anzahl Zeitschritte',
                'Frequenz der Zeitschritte',
                'Verwendeter Solver'
            ]
        })
        settings_df.to_excel(writer, sheet_name='settings', index=False)
        
        # Timestep Settings Sheet (NEU)
        timestep_settings_df = create_timestep_settings_sheet()
        timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        
        # Buses Sheet
        buses_df = pd.DataFrame({
            'label': ['el_bus'],
            'include': [1],
            'type': ['electrical'],
            'description': ['Elektrischer Bus']
        })
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        
        # Sources Sheet
        pv_profile = create_renewable_profile(timeindex, "pv")
        
        sources_df = pd.DataFrame({
            'label': ['pv_plant', 'grid_import'],
            'include': [1, 1],
            'bus': ['el_bus', 'el_bus'],
            'nominal_capacity': [100, 1000],
            'variable_costs': [0, 0.25],
            'profile_column': ['pv_profile', ''],
            'max_profile': ['', ''],
            'description': ['PV-Anlage 100 kW', 'Netzeinspeisung unbegrenzt']
        })
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        
        # Sinks Sheet
        load_profile = create_load_profile(timeindex, annual_demand=100, profile_type="residential")
        
        sinks_df = pd.DataFrame({
            'label': ['electrical_load', 'grid_export'],
            'include': [1, 1],
            'bus': ['el_bus', 'el_bus'],
            'nominal_capacity': ['', 1000],
            'variable_costs': [0, -0.08],
            'profile_column': ['load_profile', ''],
            'fix_profile': ['', ''],
            'description': ['Elektrische Last', 'Netzausspeisung']
        })
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        
        # Simple Transformers Sheet (leer für dieses Beispiel)
        transformers_df = pd.DataFrame({
            'label': [],
            'include': [],
            'input_bus': [],
            'output_bus': [],
            'conversion_factor': [],
            'nominal_capacity': [],
            'variable_costs': [],
            'description': []
        })
        transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
        
        # Zeitreihen Sheet
        timeseries_df = pd.DataFrame({
            'timestamp': timeindex,
            'pv_profile': pv_profile,
            'load_profile': load_profile
        })
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    print(f"   ✅ {filename}")


def create_example_2_medium():
    """Erstellt Beispiel 2: Mittleres System (PV + Wind + Gas + Speicher)."""
    print("📋 Erstelle Beispiel 2: Mittleres System...")
    
    # Zeitindex für einen Monat
    timeindex = create_timeindex(periods=744, freq="h")  # ~1 Monat
    
    filename = EXAMPLES_DIR / "example_2.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # Settings Sheet
        settings_df = pd.DataFrame({
            'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
            'Value': ['2025-01-01', 744, 'h', 'cbc'],
            'Description': [
                'Startdatum der Simulation',
                'Anzahl Zeitschritte',
                'Frequenz der Zeitschritte',
                'Verwendeter Solver'
            ]
        })
        settings_df.to_excel(writer, sheet_name='settings', index=False)
        
        # Timestep Settings Sheet (NEU) - Konfiguriert für 6h-Mittelwerte
        timestep_settings_df = create_timestep_settings_sheet()
        # Für mittleres Beispiel: 6h-Mittelwerte als Standard
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'timestep_strategy', 'Value'] = 'averaging'
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'averaging_hours', 'Value'] = '6'
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'enabled', 'Value'] = 'False'  # Standardmäßig deaktiviert
        timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        
        # Buses Sheet
        buses_df = pd.DataFrame({
            'label': ['el_bus', 'gas_bus'],
            'include': [1, 1],
            'type': ['electrical', 'gas'],
            'description': ['Elektrischer Bus', 'Gas-Bus']
        })
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        
        # Sources Sheet
        pv_profile = create_renewable_profile(timeindex, "pv")
        wind_profile = create_renewable_profile(timeindex, "wind")
        
        sources_df = pd.DataFrame({
            'label': ['pv_plant', 'wind_plant', 'grid_import', 'gas_import'],
            'include': [1, 1, 1, 1],
            'bus': ['el_bus', 'el_bus', 'el_bus', 'gas_bus'],
            'nominal_capacity': [200, 150, 500, 1000],
            'variable_costs': [0, 0, 0.28, 0.04],
            'profile_column': ['pv_profile', 'wind_profile', '', ''],
            'max_profile': ['', '', '', ''],
            'description': [
                'PV-Anlage 200 kW',
                'Windanlage 150 kW', 
                'Netzeinspeisung',
                'Gasversorgung'
            ]
        })
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        
        # Sinks Sheet
        load_profile = create_load_profile(timeindex, annual_demand=300, profile_type="residential")
        
        sinks_df = pd.DataFrame({
            'label': ['electrical_load', 'grid_export'],
            'include': [1, 1],
            'bus': ['el_bus', 'el_bus'],
            'nominal_capacity': ['', 200],
            'variable_costs': [0, -0.05],
            'profile_column': ['load_profile', ''],
            'fix_profile': ['', ''],
            'description': ['Elektrische Last', 'Netzausspeisung']
        })
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        
        # Simple Transformers Sheet
        transformers_df = pd.DataFrame({
            'label': ['gas_power_plant'],
            'include': [1],
            'input_bus': ['gas_bus'],
            'output_bus': ['el_bus'],
            'conversion_factor': [0.45],
            'nominal_capacity': [100],
            'variable_costs': [0.02],
            'description': ['Gas-Kraftwerk 100 kW, η=45%']
        })
        transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
        
        # Zeitreihen Sheet
        timeseries_df = pd.DataFrame({
            'timestamp': timeindex,
            'pv_profile': pv_profile,
            'wind_profile': wind_profile,
            'load_profile': load_profile
        })
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    print(f"   ✅ {filename}")


def create_example_3_complex():
    """Erstellt Beispiel 3: Komplexes System mit Investment."""
    print("📋 Erstelle Beispiel 3: Komplexes System...")
    
    # Zeitindex für 3 Monate
    timeindex = create_timeindex(periods=2160, freq="h")  # ~3 Monate
    
    filename = EXAMPLES_DIR / "example_3.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # Settings Sheet
        settings_df = pd.DataFrame({
            'Parameter': ['timeindex_start', 'timeindex_periods', 'timeindex_freq', 'solver'],
            'Value': ['2025-01-01', 2160, 'h', 'cbc'],
            'Description': [
                'Startdatum der Simulation',
                'Anzahl Zeitschritte',
                'Frequenz der Zeitschritte',
                'Verwendeter Solver'
            ]
        })
        settings_df.to_excel(writer, sheet_name='settings', index=False)
        
        # Timestep Settings Sheet (NEU) - Konfiguriert für Sampling
        timestep_settings_df = create_timestep_settings_sheet()
        # Für komplexes Beispiel: 24n+1 Sampling als Standard
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'timestep_strategy', 'Value'] = 'sampling_24n'
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'sampling_n_factor', 'Value'] = '0.25'  # Alle 6h
        timestep_settings_df.loc[timestep_settings_df['Parameter'] == 'enabled', 'Value'] = 'False'  # Standardmäßig deaktiviert
        timestep_settings_df.to_excel(writer, sheet_name='timestep_settings', index=False)
        
        # Buses Sheet
        buses_df = pd.DataFrame({
            'label': ['el_bus', 'heat_bus', 'gas_bus'],
            'include': [1, 1, 1],
            'type': ['electrical', 'heat', 'gas'],
            'description': ['Elektrischer Bus', 'Wärme-Bus', 'Gas-Bus']
        })
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        
        # Sources Sheet - mit Investment-Optionen
        pv_profile = create_renewable_profile(timeindex, "pv")
        wind_profile = create_renewable_profile(timeindex, "wind")
        
        sources_df = pd.DataFrame({
            'label': ['pv_plant', 'wind_plant', 'grid_import', 'gas_import'],
            'include': [1, 1, 1, 1],
            'bus': ['el_bus', 'el_bus', 'el_bus', 'gas_bus'],
            'nominal_capacity': ['INVEST', 'INVEST', 1000, 2000],
            'variable_costs': [0, 0, 0.30, 0.045],
            'investment_costs': [800, 1200, '', ''],
            'invest_min': [0, 0, '', ''],
            'invest_max': [500, 300, '', ''],
            'profile_column': ['pv_profile', 'wind_profile', '', ''],
            'description': [
                'PV-Anlage (Investment)',
                'Windanlage (Investment)',
                'Netzeinspeisung',
                'Gasversorgung'
            ]
        })
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        
        # Sinks Sheet
        el_load_profile = create_load_profile(timeindex, annual_demand=800, profile_type="residential")
        heat_load_profile = create_load_profile(timeindex, annual_demand=1200, profile_type="residential") * 1.5
        
        sinks_df = pd.DataFrame({
            'label': ['electrical_load', 'heat_load', 'grid_export'],
            'include': [1, 1, 1],
            'bus': ['el_bus', 'heat_bus', 'el_bus'],
            'nominal_capacity': ['', '', 300],
            'variable_costs': [0, 0, -0.06],
            'profile_column': ['el_load_profile', 'heat_load_profile', ''],
            'description': [
                'Elektrische Last',
                'Wärmelast',
                'Netzausspeisung'
            ]
        })
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        
        # Simple Transformers Sheet
        transformers_df = pd.DataFrame({
            'label': ['gas_power_plant', 'gas_boiler', 'heat_pump'],
            'include': [1, 1, 1],
            'input_bus': ['gas_bus', 'gas_bus', 'el_bus'],
            'output_bus': ['el_bus', 'heat_bus', 'heat_bus'],
            'conversion_factor': [0.42, 0.90, 3.5],
            'nominal_capacity': ['INVEST', 200, 'INVEST'],
            'variable_costs': [0.02, 0.01, 0.005],
            'investment_costs': [600, '', 1000],
            'invest_min': [0, '', 0],
            'invest_max': [200, '', 150],
            'description': [
                'Gas-KW (Investment)',
                'Gas-Kessel',
                'Wärmepumpe (Investment)'
            ]
        })
        transformers_df.to_excel(writer, sheet_name='simple_transformers', index=False)
        
        # Zeitreihen Sheet
        timeseries_df = pd.DataFrame({
            'timestamp': timeindex,
            'pv_profile': pv_profile,
            'wind_profile': wind_profile,
            'el_load_profile': el_load_profile,
            'heat_load_profile': heat_load_profile
        })
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
    
    print(f"   ✅ {filename}")


def create_example_files():
    """Erstellt alle drei Beispiel-Excel-Dateien."""
    print("📁 Erstelle Beispiel-Excel-Dateien...")
    
    # Sicherstellen, dass das Verzeichnis existiert
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Numpy Seed für reproduzierbare Zufallszahlen
    np.random.seed(42)
    
    # Beispiele erstellen
    create_example_1_simple()
    create_example_2_medium()
    create_example_3_complex()
    
    print("✅ Alle Beispiele erstellt!")
    print(f"📁 Verfügbar in: {EXAMPLES_DIR}")
    print("   📋 example_1.xlsx - Einfaches System (PV + Netz + Last)")
    print("   📋 example_2.xlsx - Mittleres System (PV + Wind + Gas)")
    print("   📋 example_3.xlsx - Komplexes System (mit Investment)")
    print("\n🕒 Timestep-Management:")
    print("   📊 Alle Beispiele enthalten 'timestep_settings' Sheet")
    print("   ⚙️  Standardmäßig deaktiviert - kann durch 'enabled: True' aktiviert werden")
    print("   📈 Example 2: Vorkonfiguriert für 6h-Mittelwerte")
    print("   🎯 Example 3: Vorkonfiguriert für 6h-Sampling")


def create_requirements_file():
    """Erstellt eine requirements.txt Datei."""
    requirements = [
        "oemof.solph>=0.6.0",
        "pandas>=1.5.0",
        "numpy>=1.20.0",
        "openpyxl>=3.0.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "pyyaml>=6.0",
        "pyomo>=6.0.0",
        "networkx>=2.8.0"
    ]
    
    req_file = PROJECT_ROOT / "requirements.txt"
    with open(req_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(requirements))
    
    print(f"📦 requirements.txt erstellt: {req_file}")


def main():
    """Hauptfunktion für Setup."""
    print("🚀 oemof.solph 0.6.0 Projekt-Setup")
    print("=" * 50)
    
    # Projektstruktur erstellen
    setup_project_structure()
    print()
    
    # Requirements-Datei erstellen
    create_requirements_file()
    print()
    
    # Beispiel-Excel-Dateien erstellen
    create_example_files()
    print()
    
    print("🎉 Setup abgeschlossen!")
    print("=" * 50)
    print("Nächste Schritte:")
    print("1. Installieren Sie die Abhängigkeiten: pip install -r requirements.txt")
    print("2. Starten Sie das Programm: python runme.py")
    print("3. Oder testen Sie direkt: python main.py examples/example_1.xlsx")
    print("\n🕒 Timestep-Management aktivieren:")
    print("1. Öffnen Sie eine example_X.xlsx Datei")
    print("2. Gehen Sie zum 'timestep_settings' Sheet")
    print("3. Setzen Sie 'enabled' auf 'True'")
    print("4. Wählen Sie eine Strategie (full, time_range, averaging, sampling_24n)")
    print("5. Konfigurieren Sie die entsprechenden Parameter")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Setup durch Benutzer unterbrochen")
    except Exception as e:
        print(f"\n❌ Fehler beim Setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)