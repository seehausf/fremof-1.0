#!/usr/bin/env python3
"""
first_run_setup.py - VEREINFACHTE VERSION DIE FUNKTIONIERT

Erstellt funktionierende Excel-Dateien OHNE komplexe Formatierung
Nach dem Testen können wir die Formatierung später wieder hinzufügen
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def setup_project_structure():
    """Erstellt die Projektordner-Struktur"""
    
    directories = [
        'input',
        'input/examples', 
        'output',
        'results',
        'logs',
        'src',
        'src/core',
        'src/builder'
    ]
    
    print("📁 Erstelle Projektstruktur...")
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ {directory}/")
    
    print("✅ Projektstruktur erstellt")

def create_district_heat_example():
    """Erstellt District Heat Beispiel mit Converter-Komponenten"""
    
    # Zeitreihen (7 Tage Winter)
    start_date = datetime(2023, 1, 15)
    end_date = start_date + timedelta(days=7)
    timestamps = pd.date_range(start_date, end_date, freq='H')[:-1]
    
    hours = np.arange(len(timestamps)) % 24
    days = np.arange(len(timestamps)) // 24
    
    # Strom-Nachfrage (Gewerbegebiet)
    electricity_base = 2.0
    electricity_peak_morning = 1.5 * np.exp(-((hours - 8)**2) / 16)
    electricity_peak_evening = 1.0 * np.exp(-((hours - 17)**2) / 12)
    electricity_demand = electricity_base + electricity_peak_morning + electricity_peak_evening
    
    # Wärme-Nachfrage
    heat_base = 3.0
    heat_daily_variation = 1.5 * np.sin((hours - 6) * np.pi / 12)
    weekend_factor = np.where(days % 7 < 5, 1.0, 0.8)
    heat_demand = np.maximum(0.5, heat_base + heat_daily_variation) * weekend_factor
    
    # Preise
    electricity_price = np.where((hours >= 8) & (hours <= 20), 0.12, 0.08)
    gas_price = np.full(len(timestamps), 0.04)
    
    # CHP Effizienz (Wartung am Tag 3)
    chp_efficiency = np.where((days == 2), 0.0, 0.85)
    
    timeseries_df = pd.DataFrame({
        'timestamp': timestamps,
        'electricity_demand': electricity_demand,
        'heat_demand': heat_demand,
        'electricity_price': electricity_price,
        'gas_price': gas_price,
        'chp_efficiency': chp_efficiency
    })
    
    # Buses
    buses_df = pd.DataFrame({
        'label': ['electricity_bus', 'heat_bus', 'gas_bus'],
        'type': ['Bus', 'Bus', 'Bus'],
        'carrier': ['electricity', 'heat', 'gas'],
        'balanced': [True, True, True]
    })
    
    # Sources
    sources_df = pd.DataFrame({
        'label': ['gas_supply', 'grid_import'],
        'type': ['Source', 'Source'],
        'output': ['gas_bus', 'electricity_bus'],
        'carrier': ['gas', 'electricity'],
        'include': [True, True],
        
        'existing': [99999, 99999],
        'investment': [False, False],
        'investment_max': [0, 0],
        'investment_min': [None, None],
        'capex': [0, 0],
        'lifetime': [20, 20],
        'wacc': [0.05, 0.05],
        
        'max': [99999, 99999],
        'min': [0, 0],
        'fix': [None, None],
        'variable_costs': ['gas_price', 'electricity_price'],
        'availability': [1.0, 1.0],
        'emissions': [0.2, 0.4],
        
        'full_load_time_max': [None, None],
        'full_load_time_min': [None, None]
    })
    
    # Sinks
    sinks_df = pd.DataFrame({
        'label': ['electricity_demand', 'heat_demand'],
        'type': ['Sink', 'Sink'],
        'input': ['electricity_bus', 'heat_bus'],
        'carrier': ['electricity', 'heat'],
        'include': [True, True],
        
        'existing': [1, 1],
        'investment': [False, False],
        'investment_max': [0, 0],
        'investment_min': [None, None],
        'capex': [0, 0],
        'lifetime': [20, 20],
        'wacc': [0.05, 0.05],
        
        'max': [None, None],
        'min': [None, None],
        'fix': ['electricity_demand', 'heat_demand'],
        'variable_costs': [0, 0],
        'availability': [1.0, 1.0],
        'emissions': [0, 0],
        
        'full_load_time_max': [None, None],
        'full_load_time_min': [None, None]
    })
    
    # Converters - NEUE KOMPONENTEN-KLASSE
    converters_df = pd.DataFrame({
        'label': ['gas_chp_plant', 'power_to_heat'],
        'type': ['Converter', 'Converter'],
        'technology': ['CHP', 'Electric_Heater'],
        'include': [True, True],
        
        'inputs': ['gas_bus', 'electricity_bus'],
        'outputs': ['electricity_bus;heat_bus', 'heat_bus'],
        'input_conversions': [1.0, 1.0],
        'output_conversions': ['0.4;0.5', 0.95],
        
        'existing': [0, 0],
        'investment': [True, True],
        'investment_max': [10, 5],
        'investment_min': [1, 0.5],
        'capex': [1500, 300],
        'lifetime': [20, 15],
        'wacc': [0.05, 0.05],
        
        'max': ['chp_efficiency', 1.0],
        'min': [0.3, 0.1],
        'fix': [None, None],
        'variable_costs': [0.02, 0.005],
        'availability': [0.95, 0.98],
        'emissions': [0, 0],
        
        'full_load_time_max': [7000, 2000],
        'full_load_time_min': [3000, 100],
        
        'startup_costs': [100, 0],
        'shutdown_costs': [50, 0],
        'maintenance_interval': [8760, 2000],
        'part_load_efficiency': [0.85, 0.90]
    })
    
    # Leerer Storages DataFrame
    storages_df = pd.DataFrame(columns=[
        'label', 'type', 'bus', 'carrier', 'include', 'existing', 'investment',
        'investment_max', 'investment_min', 'capex', 'lifetime', 'wacc',
        'max_storage_level', 'min_storage_level', 'inflow_conversion_factor',
        'outflow_conversion_factor', 'loss_rate', 'initial_storage_level'
    ])
    
    return {
        'timeseries': timeseries_df,
        'buses': buses_df,
        'sources': sources_df,
        'sinks': sinks_df,
        'converters': converters_df,
        'storages': storages_df
    }

def create_household_pv_example():
    """Erstellt PV-Household Beispiel"""
    
    # Zeitreihen (7 Tage Sommer)
    start_date = datetime(2023, 6, 15)
    end_date = start_date + timedelta(days=7)
    timestamps = pd.date_range(start_date, end_date, freq='H')[:-1]
    
    hours = np.arange(len(timestamps)) % 24
    
    # Haushalts-Stromverbrauch
    demand_base = 0.3
    demand_peak_morning = 0.5 * np.exp(-((hours - 7)**2) / 8)
    demand_peak_evening = 0.8 * np.exp(-((hours - 19)**2) / 12)
    demand_profile = demand_base + demand_peak_morning + demand_peak_evening
    
    # PV-Verfügbarkeit
    pv_availability = np.zeros(len(timestamps))
    for i, hour in enumerate(hours):
        if 6 <= hour <= 20:
            pv_availability[i] = 0.8 * np.sin((hour - 6) * np.pi / 14) ** 2
    
    # Strompreis
    price_grid = np.where((hours >= 6) & (hours <= 22), 0.30, 0.25)
    
    timeseries_df = pd.DataFrame({
        'timestamp': timestamps,
        'demand_profile': demand_profile,
        'pv_availability': pv_availability,
        'price_grid': price_grid
    })
    
    # Buses
    buses_df = pd.DataFrame({
        'label': ['house_bus', 'grid_bus'],
        'type': ['Bus', 'Bus'],
        'carrier': ['electricity', 'electricity'],
        'balanced': [True, True]
    })
    
    # Sources
    sources_df = pd.DataFrame({
        'label': ['grid_import', 'pv_plant'],
        'type': ['Source', 'Source'],
        'output': ['house_bus', 'house_bus'],
        'carrier': ['electricity', 'electricity'],
        'include': [True, True],
        
        'existing': [0, 0],
        'investment': [False, True],
        'investment_max': [99999, 10],
        'investment_min': [None, 0.5],
        'capex': [0, 1200],
        'lifetime': [1, 20],
        'wacc': [0.05, 0.05],
        
        'max': ['price_grid', 'pv_availability'],
        'min': [0, 0],
        'fix': [None, None],
        'variable_costs': [0, 0],
        'availability': [1.0, 1.0],
        'emissions': [0.5, 0.0],
        
        'full_load_time_max': [None, None],
        'full_load_time_min': [None, None]
    })
    
    # Sinks
    sinks_df = pd.DataFrame({
        'label': ['household_demand', 'grid_export'],
        'type': ['Sink', 'Sink'],
        'input': ['house_bus', 'house_bus'],
        'carrier': ['electricity', 'electricity'],
        'include': [True, True],
        
        'existing': [1, 0],
        'investment': [False, False],
        'investment_max': [0, 99999],
        'investment_min': [None, None],
        'capex': [0, 0],
        'lifetime': [20, 20],
        'wacc': [0.05, 0.05],
        
        'max': [None, 99999],
        'min': [None, 0],
        'fix': ['demand_profile', None],
        'variable_costs': [0, -0.08],
        'availability': [1.0, 1.0],
        'emissions': [0, 0],
        
        'full_load_time_max': [None, None],
        'full_load_time_min': [None, None]
    })
    
    # Leere DataFrames für Konsistenz
    converters_df = pd.DataFrame(columns=[
        'label', 'type', 'technology', 'include', 'inputs', 'outputs',
        'input_conversions', 'output_conversions', 'existing', 'investment',
        'investment_max', 'investment_min', 'capex', 'lifetime', 'wacc',
        'max', 'min', 'fix', 'variable_costs', 'availability', 'emissions',
        'full_load_time_max', 'full_load_time_min', 'startup_costs',
        'shutdown_costs', 'maintenance_interval', 'part_load_efficiency'
    ])
    
    storages_df = pd.DataFrame(columns=[
        'label', 'type', 'bus', 'carrier', 'include', 'existing', 'investment',
        'investment_max', 'investment_min', 'capex', 'lifetime', 'wacc',
        'max_storage_level', 'min_storage_level', 'inflow_conversion_factor',
        'outflow_conversion_factor', 'loss_rate', 'initial_storage_level'
    ])
    
    return {
        'timeseries': timeseries_df,
        'buses': buses_df,
        'sources': sources_df,
        'sinks': sinks_df,
        'converters': converters_df,
        'storages': storages_df
    }

def save_simple_excel(data, filename):
    """Speichert Excel ohne komplexe Formatierung - FUNKTIONIERT GARANTIERT"""
    
    output_path = Path(f'input/examples/{filename}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Erstelle {filename}...")
    
    # Einfacher Excel-Export ohne Formatierung
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"   ✅ Gespeichert: {output_path}")
    
    # Zusammenfassung
    total_components = 0
    for sheet_name, df in data.items():
        if sheet_name != 'timeseries' and len(df) > 0:
            print(f"   📊 {sheet_name}: {len(df)} Komponenten")
            total_components += len(df)
    
    print(f"   📊 Zeitreihen: {len(data['timeseries'])} Zeitschritte")
    print(f"   📊 Gesamt: {total_components} Komponenten")
    
    return output_path

def main():
    """Hauptfunktion - VEREINFACHT"""
    
    print("🔋 oemof-solph Projekt Setup (Vereinfacht)")
    print("="*50)
    print("Erstellt funktionierende Excel-Dateien:")
    print("✅ PV-Haushalt (household_pv.xlsx)")
    print("✅ Fernwärme mit CHP (district_heat.xlsx)")
    print("✅ Converter-Komponenten")
    print("="*50)
    
    try:
        # 1. Projektstruktur erstellen
        setup_project_structure()
        
        # 2. PV-Haushalt Beispiel erstellen
        print("\n🏠 Erstelle PV-Haushalt Beispiel...")
        pv_data = create_household_pv_example()
        pv_path = save_simple_excel(pv_data, 'household_pv.xlsx')
        
        # 3. Fernwärme Beispiel erstellen
        print("\n🔥 Erstelle District Heat Beispiel...")
        heat_data = create_district_heat_example()
        heat_path = save_simple_excel(heat_data, 'district_heat.xlsx')
        
        # 4. Erfolg
        print("\n" + "="*60)
        print("✅ SETUP ERFOLGREICH ABGESCHLOSSEN!")
        print("="*60)
        print(f"\n📁 Beispiele erstellt:")
        print(f"   🏠 {pv_path}")
        print(f"   🔥 {heat_path}")
        
        print(f"\n🚀 Nächste Schritte:")
        print(f"   1. python main.py")
        print(f"   2. District Heat Beispiel wählen")
        print(f"   3. Converter-System testen!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ FEHLER beim Setup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n🆘 Setup fehlgeschlagen!")
        sys.exit(1)
    
    print("\n👋 Setup abgeschlossen - viel Erfolg mit oemof-solph!")
    sys.exit(0)