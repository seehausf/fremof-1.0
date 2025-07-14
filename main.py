#!/usr/bin/env python3
"""
main.py - Hauptprogramm für oemof-solph Energiesystemmodell

KONSOLIDIERTE VERSION MIT ENHANCED DEBUGGING:
- Flow-Erweiterungen (full_load_time_max/min, investment_min)
- oemof-visio Visualisierung
- Automatisches Infeasible-Debugging
- Investment-spezifische Problemanalyse
- Erweiterte Ergebnis-Darstellung
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import pandas as pd

# Setup Logging
def setup_logging():
    """Konfiguriert Logging für das Projekt"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'oemof_run_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def find_input_files():
    """Findet alle Excel-Dateien im input/ Verzeichnis"""
    input_dir = Path('input')
    
    if not input_dir.exists():
        return []
    
    # Suche nach Excel-Dateien
    excel_files = []
    for file_path in input_dir.rglob('*.xlsx'):
        if not file_path.name.startswith('~'):  # Temporäre Excel-Dateien ignorieren
            excel_files.append(file_path)
    
    return sorted(excel_files)

def display_project_menu(excel_files):
    """Zeigt Projektauswahl-Menü an"""
    print("\n" + "="*60)
    print("🔋 oemof-solph Energiesystemmodell (Enhanced Debugging)")
    print("="*60)
    print("\nVerfügbare Projekte:")
    print("-" * 30)
    
    for i, file_path in enumerate(excel_files, 1):
        # Versuche relativen Pfad, falls das fehlschlägt, nutze absoluten Pfad
        try:
            rel_path = file_path.relative_to(Path.cwd())
            display_path = rel_path
        except ValueError:
            # Falls relative_to() fehlschlägt, nutze den Dateinamen
            display_path = file_path.name
        
        print(f"{i:2d}. {display_path}")
    
    print(f"{len(excel_files)+1:2d}. Beenden")
    print("-" * 30)

def get_user_choice(max_choice):
    """Holt Benutzerauswahl ab"""
    while True:
        try:
            choice = input(f"\nBitte wählen Sie ein Projekt (1-{max_choice}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= max_choice:
                return choice_num
            else:
                print(f"❌ Bitte eine Zahl zwischen 1 und {max_choice} eingeben.")
        except ValueError:
            print("❌ Bitte eine gültige Zahl eingeben.")
        except KeyboardInterrupt:
            print("\n\n👋 Auf Wiedersehen!")
            sys.exit(0)

def check_dependencies():
    """Prüft ob oemof.solph und Visualisierungs-Dependencies verfügbar sind"""
    missing_deps = []
    
    # Basis-Dependencies
    try:
        import oemof.solph
    except ImportError:
        missing_deps.append("oemof.solph")
    
    # Visualisierungs-Dependencies (optional)
    try:
        import matplotlib.pyplot
    except ImportError:
        missing_deps.append("matplotlib (für Visualisierung)")
    
    try:
        import plotly
    except ImportError:
        missing_deps.append("plotly (für Sankey-Diagramme)")
    
    try:
        import oemof_visio
        print("✅ oemof-visio verfügbar - vollständige Visualisierung möglich")
    except ImportError:
        print("⚠️  oemof-visio nicht verfügbar - eingeschränkte Visualisierung")
        print("    Für vollständige Visualisierung:")
        print("    pip install git+https://github.com/oemof/oemof_visio.git[network]")
    
    if missing_deps:
        print(f"\n❌ Fehlende Abhängigkeiten: {', '.join(missing_deps)}")
        print("\nBitte installieren Sie die Abhängigkeiten:")
        print("  pip install -r requirements.txt")
        print("  conda install -c conda-forge coincbc  # für CBC solver")
        return False
    
    return True

def check_for_new_parameters(data):
    """Prüft welche neuen Parameter verwendet wurden"""
    new_params = []
    
    # Prüfe Sources
    if not data.get('sources', pd.DataFrame()).empty:
        sources_df = data['sources']
        
        if 'full_load_time_min' in sources_df.columns and sources_df['full_load_time_min'].notna().any():
            new_params.append("full_load_time_min (Sources)")
        
        if 'full_load_time_max' in sources_df.columns and sources_df['full_load_time_max'].notna().any():
            new_params.append("full_load_time_max (Sources)")
        
        if 'investment_min' in sources_df.columns and sources_df['investment_min'].notna().any():
            new_params.append("investment_min (Sources)")
    
    # Prüfe Sinks
    if not data.get('sinks', pd.DataFrame()).empty:
        sinks_df = data['sinks']
        
        if 'full_load_time_min' in sinks_df.columns and sinks_df['full_load_time_min'].notna().any():
            new_params.append("full_load_time_min (Sinks)")
        
        if 'full_load_time_max' in sinks_df.columns and sinks_df['full_load_time_max'].notna().any():
            new_params.append("full_load_time_max (Sinks)")
        
        if 'investment_min' in sinks_df.columns and sinks_df['investment_min'].notna().any():
            new_params.append("investment_min (Sinks)")
    
    return new_params

def run_enhanced_debugging(energy_system, model, data, logger):
    """
    Führt Enhanced Debugging aus bei Infeasible-Modellen
    
    Args:
        energy_system: oemof EnergySystem
        model: oemof Model
        data: Original Excel-Daten
        logger: Logger-Instanz
        
    Returns:
        Debug-Ergebnisse Dictionary
    """
    print("\n🔍 STARTE ENHANCED DEBUGGING...")
    print("=" * 50)
    
    debug_results = {}
    
    try:
        # 1. Standard Model-Debugger
        logger.info("Importiere Model-Debugger...")
        from model_debugger import ModelDebugger
        
        debugger = ModelDebugger(energy_system, model, data)
        debug_results['model_debug'] = debugger.run_full_debug()
        
        print("✅ Model-Debugging abgeschlossen")
        
    except ImportError as e:
        print(f"⚠️  Model-Debugger nicht verfügbar: {e}")
        debug_results['model_debug'] = None
    except Exception as e:
        print(f"❌ Model-Debugging fehlgeschlagen: {e}")
        debug_results['model_debug'] = None
    
    try:
        # 2. Investment-spezifisches Debugging
        logger.info("Importiere Investment-Debugger...")
        from investment_debugger import debug_investment_configuration, debug_converter_investment_issues
        
        # Debug-Verzeichnis erstellen falls nicht vorhanden
        debug_dir = Path('debug')
        debug_dir.mkdir(exist_ok=True)
        
        # Dummy-Debugger-Instanz für Investment-Debugging
        class DummyDebugger:
            def __init__(self):
                self.debug_dir = debug_dir
        
        dummy_debugger = DummyDebugger()
        
        # Investment-Debugging ausführen
        investment_debug = debug_investment_configuration(data, dummy_debugger)
        converter_debug = debug_converter_investment_issues(data)
        
        debug_results['investment_debug'] = investment_debug
        debug_results['converter_debug'] = converter_debug
        
        print("✅ Investment-Debugging abgeschlossen")
        
    except ImportError as e:
        print(f"⚠️  Investment-Debugger nicht verfügbar: {e}")
        debug_results['investment_debug'] = None
        debug_results['converter_debug'] = None
    except Exception as e:
        print(f"❌ Investment-Debugging fehlgeschlagen: {e}")
        debug_results['investment_debug'] = None
        debug_results['converter_debug'] = None
    
    # 3. Zusammenfassung der Debugging-Ergebnisse
    print_debug_summary(debug_results)
    
    return debug_results

def print_debug_summary(debug_results):
    """Gibt Debugging-Zusammenfassung aus"""
    print("\n" + "="*60)
    print("🔍 ENHANCED DEBUGGING ZUSAMMENFASSUNG")
    print("="*60)
    
    # Model-Debug Summary
    if debug_results.get('model_debug'):
        model_debug = debug_results['model_debug']
        if 'energy_system_analysis' in model_debug:
            analysis = model_debug['energy_system_analysis']
            print(f"📊 EnergySystem: {analysis['summary']['total_nodes']} Nodes, {len(analysis['flows'])} Flows")
            print(f"💰 Investments: {len(analysis['investments'])} Investment-Flows")
            
            if analysis['potential_issues']:
                print(f"\n⚠️  MODEL-PROBLEME ({len(analysis['potential_issues'])}):")
                for issue in analysis['potential_issues'][:3]:  # Erste 3 anzeigen
                    print(f"   • {issue}")
                if len(analysis['potential_issues']) > 3:
                    print(f"   ... und {len(analysis['potential_issues']) - 3} weitere")
    
    # Investment-Debug Summary
    if debug_results.get('investment_debug'):
        inv_debug = debug_results['investment_debug']
        print(f"\n💰 INVESTMENT-ANALYSE:")
        print(f"   Komponenten mit Investment: {len(inv_debug['investment_components'])}")
        if inv_debug['potential_issues']:
            print(f"   Probleme gefunden: {len(inv_debug['potential_issues'])}")
            for issue in inv_debug['potential_issues'][:2]:  # Erste 2 anzeigen
                print(f"   • {issue}")
    
    # Converter-Debug Summary
    if debug_results.get('converter_debug'):
        conv_debug = debug_results['converter_debug']
        print(f"\n🔄 CONVERTER-ANALYSE:")
        print(f"   Converter gefunden: {conv_debug['converters_found']}")
        print(f"   Investment-Converter: {conv_debug['investment_converters']}")
        
        all_conv_issues = (conv_debug['bus_issues'] + 
                          conv_debug['conversion_issues'] + 
                          conv_debug['investment_issues'])
        if all_conv_issues:
            print(f"   Converter-Probleme: {len(all_conv_issues)}")
    
    # Debug-Dateien
    debug_dir = Path('debug')
    if debug_dir.exists():
        debug_files = list(debug_dir.glob('*'))
        if debug_files:
            print(f"\n📁 Debug-Dateien erstellt: {len(debug_files)}")
            print(f"   Verzeichnis: {debug_dir}")
            
            # Wichtigste Dateien anzeigen
            lp_files = [f for f in debug_files if f.suffix == '.lp']
            if lp_files:
                print(f"   📄 LP-Datei: {lp_files[-1].name}")
    
    print("\n💡 NÄCHSTE SCHRITTE:")
    print("   1. Debug-Reports in debug/ Verzeichnis analysieren")
    print("   2. LP-Datei mit Solver-Tool untersuchen (optional)")
    print("   3. Investment-Parameter in Excel korrigieren")
    print("   4. Converter-Konfiguration prüfen")
    print("   5. Erneut testen mit korrigierter Excel-Datei")
    print("="*60)

def main():
    """Hauptfunktion mit Enhanced Debugging"""
    
    # Logging einrichten
    logger = setup_logging()
    logger.info("="*60)
    logger.info("oemof-solph Energiesystemmodell gestartet (Enhanced Debugging)")
    logger.info("="*60)
    
    try:
        # 0. Dependencies prüfen
        if not check_dependencies():
            return False
        
        # 1. Excel-Dateien finden
        excel_files = find_input_files()
        
        if not excel_files:
            print("\n❌ Keine Excel-Dateien im 'input/' Verzeichnis gefunden!")
            print("\nBitte führen Sie zuerst 'python first_run_setup.py' aus, um Beispieldateien zu erstellen.")
            return False
        
        logger.info(f"Gefunden: {len(excel_files)} Excel-Datei(en)")
        
        # 2. Projektauswahl anzeigen
        display_project_menu(excel_files)
        
        # 3. Benutzerauswahl
        max_choice = len(excel_files) + 1
        choice = get_user_choice(max_choice)
        
        # Beenden gewählt?
        if choice == max_choice:
            print("\n👋 Auf Wiedersehen!")
            return True
        
        # Gewählte Datei
        selected_file = excel_files[choice - 1]
        
        # Sicherer relativer Pfad für Display
        try:
            rel_path = selected_file.relative_to(Path.cwd())
            display_path = rel_path
        except ValueError:
            display_path = selected_file.name
        
        print(f"\n✅ Gewählt: {display_path}")
        logger.info(f"Projekt gewählt: {selected_file}")
        
        # 4. Import der Module aus src/
        try:
            from src.importer import DataImporter
            from src.builder import ModelBuilder  # ✅ Verwendet modulare Version aus src/builder/__init__.py
            from src.runner import ModelRunner
            from src.exporter import ResultExporter
            from src.visualizer import EnergySystemVisualizer  # NEU
            
            logger.info("Module erfolgreich aus src/ importiert (modular)")
            
        except ImportError as e:
            logger.error(f"Fehler beim Import der Module aus src/: {e}")
            print(f"\n❌ Module konnten nicht importiert werden: {e}")
            print("Bitte stellen Sie sicher, dass alle Module in src/ vorhanden sind:")
            print("  - src/importer.py")
            print("  - src/builder/ (modulare Implementation)")
            print("  - src/runner.py")
            print("  - src/exporter.py")
            print("  - src/visualizer.py")
            return False
        
        # 5. Workflow ausführen (erweitert mit Enhanced Debugging)
        logger.info("Starte erweiterten Modellierungsworkflow...")
        
        # Import der Daten (erweitert)
        print("\n📂 Lade Eingabedaten (erweitert)...")
        importer = DataImporter(selected_file)
        data = importer.load_data()
        
        # Zusammenfassung der importierten Daten
        summary = importer.get_summary()
        print(f"✅ {summary}")
        logger.info(f"Datenimport: {summary}")
        
        # Prüfe auf neue Parameter
        new_params_found = check_for_new_parameters(data)
        if new_params_found:
            print("🆕 Neue Flow-Parameter erkannt:")
            for param in new_params_found:
                print(f"   - {param}")
        
        # Modell erstellen (erweitert)
        print("🔧 Erstelle Energiesystem (erweitert)...")
        builder = ModelBuilder(data)
        energy_system, model = builder.build_model()
        
        # Modell-Zusammenfassung
        model_summary = builder.get_model_summary()
        print(f"✅ {model_summary}")
        logger.info(f"Modell: {model_summary}")
        
        # Simulation ausführen (mit Enhanced Debugging)
        print("⚡ Führe Optimierung durch...")
        runner = ModelRunner(model)
        
        try:
            results = runner.solve()
            
            # Prüfe Solver-Status
            solver_status = "unknown"
            termination_condition = "unknown"
            
            if runner.meta_results and 'solver' in runner.meta_results:
                solver_info = runner.meta_results['solver']
                solver_status = solver_info.get('Status', 'unknown')
                termination_condition = solver_info.get('Termination condition', 'unknown')
                
                print(f"🔍 Solver-Status: {solver_status}")
                print(f"🔍 Termination: {termination_condition}")
                
                # Bei Infeasible: Enhanced Debugging ausführen
                if 'optimal' not in termination_condition.lower() or 'ok' not in solver_status.lower():
                    print("\n❌ MODELL IST INFEASIBLE - STARTE ENHANCED DEBUGGING...")
                    
                    # Enhanced Debugging ausführen
                    debug_results = run_enhanced_debugging(energy_system, model, data, logger)
                    
                    print("\n⚠️  OPTIMIERUNG NICHT ERFOLGREICH")
                    print("💡 Siehe Debug-Reports für detaillierte Problemanalyse")
                    print("🔧 Korrigieren Sie die Excel-Parameter basierend auf den Empfehlungen")
                    
                    # Trotzdem versuchen weiterzumachen für Export (möglicherweise unvollständige Ergebnisse)
                    print("\n⚠️  Versuche trotzdem Export (möglicherweise unvollständige Ergebnisse)...")
            
            # Investment-Ergebnisse anzeigen
            investments = runner.get_investment_results()
            if investments:
                print("\n💰 Investment-Ergebnisse:")
                for component, capacity in investments.items():
                    print(f"   {component}: {capacity:.2f} kW")
            else:
                print("\n⚠️  Keine Investment-Ergebnisse gefunden")
                print("💡 Mögliche Ursachen:")
                print("   - Modell infeasible")
                print("   - Investment-Parameter nicht korrekt")
                print("   - Keine Investment-Komponenten aktiviert")
            
            # Gesamtkosten anzeigen
            total_costs = runner.get_total_costs()
            if total_costs:
                print(f"\n💵 Gesamtkosten: {total_costs:,.2f} €")
            else:
                print("\n⚠️  Keine Gesamtkosten verfügbar (Modell möglicherweise infeasible)")
                
        except Exception as e:
            print(f"\n❌ OPTIMIERUNGSFEHLER: {e}")
            print("\n🔍 STARTE NOTFALL-DEBUGGING...")
            
            # Notfall-Debugging auch bei Exception
            try:
                debug_results = run_enhanced_debugging(energy_system, model, data, logger)
                print("📁 Debug-Dateien erstellt trotz Optimierungsfehler")
            except Exception as debug_error:
                print(f"❌ Auch Enhanced Debugging fehlgeschlagen: {debug_error}")
            
            # Exception weiterwerfen für weitere Behandlung
            print("🛑 Optimierung abgebrochen - siehe Debug-Reports für Problemanalyse")
            logger.error(f"Optimierung fehlgeschlagen: {e}")
            
            # Nicht komplett abbrechen, versuche trotzdem Export falls möglich
            print("\n⚠️  Versuche trotzdem Export der verfügbaren Daten...")
        
        # Ergebnisse exportieren (auch bei Problemen versuchen)
        print("💾 Exportiere Ergebnisse...")
        try:
            exporter = ResultExporter(energy_system, {'results': runner.results, 'meta_results': runner.meta_results, 'model': model})
            output_files = exporter.export_all(selected_file.stem)
            print(f"✅ {len(output_files)} Excel-Datei(en) erstellt")
        except Exception as e:
            print(f"⚠️  Export teilweise fehlgeschlagen: {e}")
            output_files = []
        
        # Visualisierungen erstellen (auch bei Problemen versuchen)
        print("🎨 Erstelle Visualisierungen...")
        try:
            visualizer = EnergySystemVisualizer(energy_system, {'results': runner.results, 'meta_results': runner.meta_results})
            
            # Visualisierungs-Zusammenfassung
            vis_summary = visualizer.get_summary()
            print(f"📊 {vis_summary}")
            logger.info(f"Visualisierung: {vis_summary}")
            
            # Alle Visualisierungen erstellen
            vis_files = visualizer.create_all_visualizations(selected_file.stem)
            print(f"✅ {len(vis_files)} Visualisierung(en) erstellt")
            
            # Visualisierungs-Dateien zu Output hinzufügen
            output_files.extend(vis_files)
            
        except Exception as e:
            logger.warning(f"Visualisierung teilweise fehlgeschlagen: {e}")
            print(f"⚠️  Visualisierung teilweise fehlgeschlagen: {e}")
            print("    Für vollständige Visualisierung:")
            print("    pip install git+https://github.com/oemof/oemof_visio.git[network]")
        
        # Abschluss und Ergebnisübersicht
        print("\n" + "="*60)
        print("✅ Erweiterte Modellierung abgeschlossen!")
        print("="*60)
        
        if output_files:
            print(f"\nErgebnisse gespeichert:")
            
            # Kategorisierte Ausgabe
            result_files = [f for f in output_files if 'result' in f.name or 'summary' in f.name]
            vis_files_actual = [f for f in output_files if f not in result_files]
            
            if result_files:
                print("\n📊 Berechnungsergebnisse:")
                for output_file in result_files:
                    print(f"  📄 {output_file}")
            
            if vis_files_actual:
                print("\n🎨 Visualisierungen:")
                for vis_file in vis_files_actual:
                    print(f"  🖼️  {vis_file}")
        
        # Debug-Dateien anzeigen falls vorhanden
        debug_dir = Path('debug')
        if debug_dir.exists():
            debug_files = list(debug_dir.glob('*'))
            if debug_files:
                print(f"\n🔍 Debug-Dateien:")
                for debug_file in debug_files:
                    print(f"  📄 debug/{debug_file.name}")
        
        # Phase 2.1 Features hervorheben
        print(f"\n🆕 Enhanced Features verwendet:")
        print(f"   ✅ Flow-Erweiterungen (full_load_time, investment_min)")
        print(f"   ✅ oemof-visio Visualisierung")
        print(f"   ✅ Enhanced Debugging (model_debugger + investment_debugger)")
        if new_params_found:
            print(f"   ✅ Neue Parameter: {', '.join(new_params_found)}")
        
        logger.info("Erweiterte Modellierung mit Enhanced Debugging abgeschlossen")
        return True
        
    except Exception as e:
        logger.error(f"Fehler in main(): {e}", exc_info=True)
        print(f"\n❌ Fehler: {e}")
        
        # Auch bei kritischen Fehlern versuchen Debug-Info zu geben
        print("\n🔍 Bei kritischen Fehlern:")
        print("   1. Prüfen Sie die Log-Datei in logs/")
        print("   2. Validieren Sie die Excel-Datei-Struktur")
        print("   3. Führen Sie 'python test_import.py' aus")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)