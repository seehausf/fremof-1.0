# -*- coding: utf-8 -*-
"""
Fremof Excel Example Generator
==============================

Erstellt eine vollständige Excel-Datei mit Beispieldaten für das Fremof Framework.
Diese Datei kann direkt mit dem FremofExcelReader verwendet werden.

Author: Fremof Development Team
Date: 14. Juli 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_fremof_example_excel(filename='fremof_example.xlsx'):
    """
    Erstellt eine vollständige Excel-Datei mit allen erforderlichen Arbeitsblättern
    und realistischen Beispieldaten für ein Multi-Energiesystem.
    
    Parameters
    ----------
    filename : str
        Name der zu erstellenden Excel-Datei
    """
    
    # Excel Writer erstellen
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        
        # =================================================================
        # 1. BUSES - Energieknoten
        # =================================================================
        buses_data = {
            'label': [
                'bus_el',      # Stromnetz
                'bus_heat',    # Wärmenetz  
                'bus_gas',     # Gasnetz
                'bus_h2'       # Wasserstoffnetz
            ],
            'include': [1, 1, 1, 1]
        }
        
        buses_df = pd.DataFrame(buses_data)
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        
        # =================================================================
        # 2. SOURCES - Energiequellen
        # =================================================================
        sources_data = {
            'label': [
                'grid_import',
                'gas_import', 
                'pv_plant',
                'wind_plant',
                'biogas_plant'
            ],
            'include': [1, 1, 1, 1, 1],
            'investment': [0, 0, 1, 1, 0],
            'nonconvex_investment': [0, 0, 0, 1, 0],
            'existing': [1000, 500, 0, 0, 200],
            'outputs': [
                'bus_el',
                'bus_gas',
                'bus_el', 
                'bus_el',
                'bus_gas'
            ],
            'output_relation': [
                '1,0',           # Konstant verfügbar
                '1,0',           # Konstant verfügbar
                'pv_profile',    # Zeitreihe
                'wind_profile',  # Zeitreihe
                '0,8'            # 80% Verfügbarkeit
            ],
            'invest_cost': [None, None, 1200, 1500, None],
            'lifetime': [None, None, 20, 25, None],
            'interest_rate': [None, None, 0.05, 0.05, None],
            'min_invest': [None, None, 0, 5, None],
            'max_invest': [None, None, 100, 50, None]
        }
        
        sources_df = pd.DataFrame(sources_data)
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        
        # =================================================================
        # 3. SINKS - Energieverbraucher
        # =================================================================
        sinks_data = {
            'label': [
                'el_demand',
                'heat_demand',
                'h2_demand',
                'grid_export'
            ],
            'include': [1, 1, 1, 1],
            'investment': [0, 0, 0, 0],
            'nonconvex_investment': [0, 0, 0, 0],
            'existing': [800, 600, 50, 1000],
            'inputs': [
                'bus_el',
                'bus_heat', 
                'bus_h2',
                'bus_el'
            ],
            'input_relation': [
                'el_load_profile',    # Zeitreihe
                'heat_load_profile',  # Zeitreihe
                'h2_load_profile',    # Zeitreihe
                '1,0'                 # Export konstant möglich
            ],
            'invest_cost': [None, None, None, None],
            'lifetime': [None, None, None, None],
            'interest_rate': [None, None, None, None],
            'min_invest': [None, None, None, None],
            'max_invest': [None, None, None, None]
        }
        
        sinks_df = pd.DataFrame(sinks_data)
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        
        # =================================================================
        # 4. CONVERTERS - Energiewandler
        # =================================================================
        converters_data = {
            'label': [
                'gas_boiler',
                'chp_plant',
                'heat_pump',
                'electrolyzer',
                'fuel_cell'
            ],
            'include': [1, 1, 1, 1, 1],
            'investment': [1, 1, 1, 1, 0],
            'nonconvex_investment': [0, 1, 0, 0, 0],
            'existing': [0, 0, 0, 0, 100],
            'inputs': [
                'bus_gas',
                'bus_gas',
                'bus_el',
                'bus_el',
                'bus_h2'
            ],
            'outputs': [
                'bus_heat',
                'bus_el;bus_heat',
                'bus_heat',
                'bus_h2',
                'bus_el'
            ],
            'input_relation': [
                '1,0',         # Gaskessel
                '1,0',         # KWK
                '1,0',         # Wärmepumpe
                '1,0',         # Elektrolyseur
                '1,0'          # Brennstoffzelle
            ],
            'output_relation': [
                '0,9',              # Gaskessel: 90% Wirkungsgrad
                '0,35;0,5',         # KWK: 35% elektrisch, 50% thermisch
                'cop_profile',      # Wärmepumpe: variable COP
                '0,7',              # Elektrolyseur: 70% Wirkungsgrad
                '0,55'              # Brennstoffzelle: 55% Wirkungsgrad
            ],
            'invest_cost': [800, 2500, 1200, 1800, None],
            'lifetime': [15, 20, 18, 15, None],
            'interest_rate': [0.05, 0.05, 0.05, 0.05, None],
            'min_invest': [0, 10, 0, 0, None],
            'max_invest': [200, 100, 50, 30, None]
        }
        
        converters_df = pd.DataFrame(converters_data)
        converters_df.to_excel(writer, sheet_name='converters', index=False)
        
        # =================================================================
        # 5. TIMESERIES - Zeitreihen (24 Stunden)
        # =================================================================
        
        # Zeitindex für einen Tag mit stündlicher Auflösung
        start_time = datetime(2024, 1, 15, 0, 0, 0)  # Wintertag
        time_index = [start_time + timedelta(hours=i) for i in range(24)]
        
        # PV-Profil (Winter, gedämpft)
        pv_profile = [0.0] * 7 + [0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.8, 0.7, 0.5, 0.3] + [0.1] + [0.0] * 6
        
        # Wind-Profil (variable Windgeschwindigkeiten)
        wind_profile = [0.3, 0.4, 0.2, 0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1, 0.2, 0.3, 
                       0.4, 0.5, 0.6, 0.7, 0.8, 0.6, 0.4, 0.3, 0.2, 0.3, 0.4, 0.3]
        
        # Elektrische Last (typischer Haushalt + Industrie)
        el_load_profile = [0.6, 0.5, 0.4, 0.4, 0.5, 0.6, 0.8, 0.9, 0.8, 0.7, 0.7, 0.8,
                          0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 0.9, 0.8, 0.7, 0.7, 0.6]
        
        # Wärmelast (Winter - hoch morgens und abends)
        heat_load_profile = [0.8, 0.7, 0.6, 0.6, 0.7, 0.9, 1.0, 0.8, 0.6, 0.5, 0.4, 0.4,
                            0.4, 0.4, 0.4, 0.5, 0.6, 0.8, 1.0, 0.9, 0.8, 0.8, 0.8, 0.8]
        
        # Wasserstoff-Last (Industrieprozesse)
        h2_load_profile = [0.3, 0.2, 0.2, 0.2, 0.3, 0.5, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8,
                          0.8, 0.9, 1.0, 1.0, 0.9, 0.8, 0.6, 0.4, 0.3, 0.3, 0.3, 0.3]
        
        # COP-Profil für Wärmepumpe (temperaturabhängig)
        cop_profile = [3.2, 3.1, 3.0, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7,
                      3.8, 3.7, 3.6, 3.5, 3.4, 3.3, 3.2, 3.1, 3.0, 3.1, 3.2, 3.2]
        
        # Zeitreihen-DataFrame erstellen
        timeseries_data = {
            'timestamp': time_index,
            'pv_profile': pv_profile,
            'wind_profile': wind_profile,
            'el_load_profile': el_load_profile,
            'heat_load_profile': heat_load_profile,
            'h2_load_profile': h2_load_profile,
            'cop_profile': cop_profile
        }
        
        timeseries_df = pd.DataFrame(timeseries_data)
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
        
        # =================================================================
        # Excel-Formatierung
        # =================================================================
        workbook = writer.book
        
        # Header-Format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1
        })
        
        # Daten-Format
        data_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })
        
        # Float-Format für deutsche Zahlen
        float_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': '0,00'
        })
        
        # Formatierung für alle Arbeitsblätter
        sheet_names = ['buses', 'sources', 'sinks', 'converters', 'timeseries']
        
        for sheet_name in sheet_names:
            worksheet = writer.sheets[sheet_name]
            
            # Auto-fit Spaltenbreite
            for i, col in enumerate(eval(f'{sheet_name}_df').columns):
                max_len = max(
                    eval(f'{sheet_name}_df')[col].astype(str).str.len().max(),
                    len(col)
                ) + 2
                worksheet.set_column(i, i, max_len)
            
            # Header formatieren
            for col_num, value in enumerate(eval(f'{sheet_name}_df').columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        print(f"✅ Excel-Datei '{filename}' erfolgreich erstellt!")
        print(f"📊 Enthält: {len(buses_df)} Buses, {len(sources_df)} Sources, {len(sinks_df)} Sinks, {len(converters_df)} Converters")
        print(f"⏰ Zeitraum: 24 Stunden mit stündlicher Auflösung")
        print(f"🔋 Features: Investment-Optimierung, NonConvex Investment, Zeitreihen")


def create_simple_example(filename='fremof_simple_example.xlsx'):
    """
    Erstellt ein einfaches Beispiel für erste Tests
    """
    
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        
        # Einfaches 3-Bus System
        buses_df = pd.DataFrame({
            'label': ['bus_el', 'bus_heat', 'bus_gas'],
            'include': [1, 1, 1]
        })
        buses_df.to_excel(writer, sheet_name='buses', index=False)
        
        # Eine Source
        sources_df = pd.DataFrame({
            'label': ['gas_import'],
            'include': [1],
            'investment': [0],
            'nonconvex_investment': [0],
            'existing': [1000],
            'outputs': ['bus_gas'],
            'output_relation': ['1,0'],
            'invest_cost': [None],
            'lifetime': [None],
            'interest_rate': [None],
            'min_invest': [None],
            'max_invest': [None]
        })
        sources_df.to_excel(writer, sheet_name='sources', index=False)
        
        # Eine Sink
        sinks_df = pd.DataFrame({
            'label': ['heat_demand'],
            'include': [1],
            'investment': [0],
            'nonconvex_investment': [0],
            'existing': [500],
            'inputs': ['bus_heat'],
            'input_relation': ['1,0'],
            'invest_cost': [None],
            'lifetime': [None],
            'interest_rate': [None],
            'min_invest': [None],
            'max_invest': [None]
        })
        sinks_df.to_excel(writer, sheet_name='sinks', index=False)
        
        # Ein Converter
        converters_df = pd.DataFrame({
            'label': ['gas_boiler'],
            'include': [1],
            'investment': [1],
            'nonconvex_investment': [0],
            'existing': [0],
            'inputs': ['bus_gas'],
            'outputs': ['bus_heat'],
            'input_relation': ['1,0'],
            'output_relation': ['0,9'],
            'invest_cost': [800],
            'lifetime': [15],
            'interest_rate': [0.05],
            'min_invest': [0],
            'max_invest': [100]
        })
        converters_df.to_excel(writer, sheet_name='converters', index=False)
        
        # Einfache Zeitreihen (nur 3 Stunden)
        timeseries_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='H'),
            'dummy_profile': [1.0, 1.0, 1.0]
        })
        timeseries_df.to_excel(writer, sheet_name='timeseries', index=False)
        
        print(f"✅ Einfache Excel-Datei '{filename}' erstellt!")


if __name__ == "__main__":
    # Vollständiges Beispiel erstellen
    create_fremof_example_excel('fremof_example.xlsx')
    
    # Einfaches Beispiel für Tests erstellen
    create_simple_example('fremof_simple_example.xlsx')
    
    print("\n🎯 Nächste Schritte:")
    print("1. Führe dieses Script aus: python create_excel_example.py")
    print("2. Teste mit: FremofExcelReader('fremof_example.xlsx')")
    print("3. Lade die Excel-Dateien in dein Repository hoch")
