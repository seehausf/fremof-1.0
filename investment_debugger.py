#!/usr/bin/env python3
"""
investment_debugger.py - Spezifisches Debugging für Investment-Probleme

Erweitert model_debugger.py um Investment-spezifische Analyse
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def debug_investment_configuration(data, debugger_instance):
    """
    Analysiert Investment-Konfiguration für häufige Probleme
    
    Args:
        data: Original Excel-Daten
        debugger_instance: ModelDebugger Instanz
        
    Returns:
        Dictionary mit Investment-Debugging-Ergebnissen
    """
    print("\n🔍 INVESTMENT-DEBUGGING")
    print("=" * 50)
    
    investment_debug = {
        'investment_components': [],
        'potential_issues': [],
        'recommendations': []
    }
    
    # 1. Analysiere alle Investment-Komponenten
    for sheet_name in ['sources', 'sinks', 'converters', 'storages']:
        df = data.get(sheet_name, pd.DataFrame())
        if df.empty:
            continue
            
        for _, component in df.iterrows():
            if component.get('investment', False):
                inv_analysis = _analyze_investment_component(component, sheet_name)
                investment_debug['investment_components'].append(inv_analysis)
                
                # Sammle Probleme
                issues = _check_investment_issues(inv_analysis)
                investment_debug['potential_issues'].extend(issues)
    
    # 2. Gesamtanalyse
    total_investments = len(investment_debug['investment_components'])
    print(f"📊 Investment-Komponenten gefunden: {total_investments}")
    
    if total_investments == 0:
        investment_debug['potential_issues'].append(
            "KRITISCH: Keine Investment-Komponenten gefunden - Modell hat möglicherweise keine Erzeugungskapazität"
        )
        investment_debug['recommendations'].append(
            "Setzen Sie 'investment=True' für mindestens eine Source-Komponente"
        )
    
    # 3. Ausgabe der Probleme
    if investment_debug['potential_issues']:
        print(f"\n⚠️  INVESTMENT-PROBLEME GEFUNDEN ({len(investment_debug['potential_issues'])}):")
        for i, issue in enumerate(investment_debug['potential_issues'], 1):
            print(f"   {i}. {issue}")
    
    # 4. Empfehlungen
    recommendations = _generate_investment_recommendations(investment_debug)
    investment_debug['recommendations'].extend(recommendations)
    
    if investment_debug['recommendations']:
        print(f"\n💡 EMPFEHLUNGEN:")
        for i, rec in enumerate(investment_debug['recommendations'], 1):
            print(f"   {i}. {rec}")
    
    # 5. Investment-Report speichern
    _save_investment_debug_report(investment_debug, debugger_instance.debug_dir)
    
    return investment_debug

def _analyze_investment_component(component, sheet_name):
    """Analysiert eine einzelne Investment-Komponente"""
    return {
        'label': component.get('label', 'unknown'),
        'sheet': sheet_name,
        'investment': component.get('investment', False),
        'investment_max': component.get('investment_max', 0),
        'investment_min': component.get('investment_min', 0),
        'existing': component.get('existing', 0),
        'capex': component.get('capex', 0),
        'lifetime': component.get('lifetime', 20),
        'wacc': component.get('wacc', 0.05),
        'include': component.get('include', True)
    }

def _check_investment_issues(inv_analysis):
    """Prüft eine Investment-Komponente auf häufige Probleme"""
    issues = []
    label = inv_analysis['label']
    sheet = inv_analysis['sheet']
    
    # Problem 1: Investment aktiviert aber max = 0
    if inv_analysis['investment'] and inv_analysis['investment_max'] <= 0:
        issues.append(f"KRITISCH: {sheet} '{label}' - investment=True aber investment_max={inv_analysis['investment_max']}")
    
    # Problem 2: Investment min > max
    if inv_analysis['investment_min'] > inv_analysis['investment_max']:
        issues.append(f"KRITISCH: {sheet} '{label}' - investment_min > investment_max")
    
    # Problem 3: CAPEX = 0 (kostenlose Investments sind verdächtig)
    if inv_analysis['investment'] and inv_analysis['capex'] == 0:
        issues.append(f"WARNUNG: {sheet} '{label}' - CAPEX=0 (kostenloses Investment)")
    
    # Problem 4: Unrealistische Parameter
    if inv_analysis['lifetime'] <= 0:
        issues.append(f"KRITISCH: {sheet} '{label}' - lifetime={inv_analysis['lifetime']} (muss > 0 sein)")
    
    if inv_analysis['wacc'] < 0 or inv_analysis['wacc'] > 0.5:
        issues.append(f"WARNUNG: {sheet} '{label}' - wacc={inv_analysis['wacc']} (ungewöhnlich)")
    
    # Problem 5: Komponente deaktiviert
    if not inv_analysis['include']:
        issues.append(f"WARNUNG: {sheet} '{label}' - include=False (Investment-Komponente deaktiviert)")
    
    return issues

def _generate_investment_recommendations(investment_debug):
    """Generiert Empfehlungen basierend auf Investment-Analyse"""
    recommendations = []
    
    # Keine Investment-Komponenten
    if not investment_debug['investment_components']:
        recommendations.extend([
            "Aktivieren Sie Investment für mindestens eine Source (z.B. PV, Wind, Kraftwerk)",
            "Setzen Sie 'investment=True' und 'investment_max > 0' in Excel",
            "Prüfen Sie 'include=True' für alle relevanten Komponenten"
        ])
    
    # Viele Probleme gefunden
    if len(investment_debug['potential_issues']) > 3:
        recommendations.append(
            "Viele Investment-Probleme gefunden - prüfen Sie Excel-Datei systematisch"
        )
    
    # Converter-spezifische Empfehlungen
    converter_investments = [comp for comp in investment_debug['investment_components'] 
                           if comp['sheet'] == 'converters']
    if converter_investments:
        recommendations.append(
            "Converter-Investments gefunden - prüfen Sie Input/Output-Bus-Verbindungen"
        )
    
    return recommendations

def _save_investment_debug_report(investment_debug, debug_dir):
    """Speichert detaillierten Investment-Debug-Report"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = debug_dir / f"investment_debug_{timestamp}.txt"
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("INVESTMENT-DEBUGGING REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Investment-Komponenten
            f.write("INVESTMENT-KOMPONENTEN:\n")
            f.write("-" * 30 + "\n")
            for comp in investment_debug['investment_components']:
                f.write(f"Komponente: {comp['label']} ({comp['sheet']})\n")
                f.write(f"  Investment: {comp['investment']}\n")
                f.write(f"  Max: {comp['investment_max']}, Min: {comp['investment_min']}\n")
                f.write(f"  Existing: {comp['existing']}\n")
                f.write(f"  CAPEX: {comp['capex']}, Lifetime: {comp['lifetime']}, WACC: {comp['wacc']}\n")
                f.write(f"  Include: {comp['include']}\n")
                f.write("\n")
            
            # Probleme
            if investment_debug['potential_issues']:
                f.write("IDENTIFIZIERTE PROBLEME:\n")
                f.write("-" * 30 + "\n")
                for issue in investment_debug['potential_issues']:
                    f.write(f"• {issue}\n")
                f.write("\n")
            
            # Empfehlungen
            if investment_debug['recommendations']:
                f.write("EMPFEHLUNGEN:\n")
                f.write("-" * 20 + "\n")
                for rec in investment_debug['recommendations']:
                    f.write(f"→ {rec}\n")
        
        print(f"📄 Investment-Debug-Report gespeichert: {report_path.name}")
        
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Investment-Reports: {e}")

def debug_converter_investment_issues(data):
    """
    Spezifisches Debugging für Converter-Investment-Probleme
    
    Args:
        data: Original Excel-Daten
        
    Returns:
        Dictionary mit Converter-spezifischen Issues
    """
    print("\n🔄 CONVERTER-INVESTMENT-DEBUGGING")
    print("=" * 40)
    
    converter_issues = {
        'converters_found': 0,
        'investment_converters': 0,
        'bus_issues': [],
        'conversion_issues': [],
        'investment_issues': []
    }
    
    converters_df = data.get('converters', pd.DataFrame())
    if converters_df.empty:
        print("ℹ️  Keine Converter-Komponenten gefunden")
        return converter_issues
    
    converter_issues['converters_found'] = len(converters_df)
    
    for _, converter in converters_df.iterrows():
        label = converter.get('label', 'unknown')
        
        # Investment-Status prüfen
        if converter.get('investment', False):
            converter_issues['investment_converters'] += 1
            
            # Investment-Parameter prüfen
            inv_max = converter.get('investment_max', 0)
            if inv_max <= 0:
                converter_issues['investment_issues'].append(
                    f"Converter '{label}': investment_max={inv_max} (sollte > 0 sein)"
                )
        
        # Bus-Verbindungen prüfen
        inputs = converter.get('inputs', '')
        outputs = converter.get('outputs', '')
        
        if not inputs or pd.isna(inputs):
            converter_issues['bus_issues'].append(f"Converter '{label}': Keine Input-Buses definiert")
        
        if not outputs or pd.isna(outputs):
            converter_issues['bus_issues'].append(f"Converter '{label}': Keine Output-Buses definiert")
        
        # Conversion-Faktoren prüfen
        input_conv = converter.get('input_conversions', '')
        output_conv = converter.get('output_conversions', '')
        
        if not input_conv or pd.isna(input_conv):
            converter_issues['conversion_issues'].append(
                f"Converter '{label}': Keine input_conversions definiert"
            )
        
        if not output_conv or pd.isna(output_conv):
            converter_issues['conversion_issues'].append(
                f"Converter '{label}': Keine output_conversions definiert"
            )
    
    # Ausgabe
    print(f"📊 Converter gefunden: {converter_issues['converters_found']}")
    print(f"📊 Investment-Converter: {converter_issues['investment_converters']}")
    
    all_issues = (converter_issues['bus_issues'] + 
                  converter_issues['conversion_issues'] + 
                  converter_issues['investment_issues'])
    
    if all_issues:
        print(f"\n⚠️  CONVERTER-PROBLEME ({len(all_issues)}):")
        for issue in all_issues:
            print(f"   • {issue}")
    else:
        print("✅ Keine Converter-Probleme gefunden")
    
    return converter_issues

# Integration in model_debugger.py
def run_enhanced_investment_debugging(energy_system, model=None, data=None):
    """
    Erweiterte Investment-Debugging-Funktion
    Integriert in model_debugger.py Workflow
    """
    from model_debugger import ModelDebugger
    
    # Standard-Debugging
    debugger = ModelDebugger(energy_system, model, data)
    debug_results = debugger.run_full_debug()
    
    # Investment-spezifisches Debugging
    if data:
        investment_debug = debug_investment_configuration(data, debugger)
        converter_debug = debug_converter_investment_issues(data)
        
        debug_results['investment_debug'] = investment_debug
        debug_results['converter_debug'] = converter_debug
    
    return debug_results
