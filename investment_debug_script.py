"""
Investment Debug Script

Dieses Script analysiert die Investment-Parameter in einem aufgebauten Energy System
und erstellt detaillierte Debug-Informationen für die System-Export-Funktionalität.

Verwendung:
python investment_debug.py
"""

import sys
from pathlib import Path

# Projekt-Module importieren
sys.path.append(str(Path(__file__).parent))

def debug_investment_export():
    """Debuggt Investment-Export für example_1b.xlsx"""
    
    try:
        from modules.excel_reader import ExcelReader
        from modules.system_builder import SystemBuilder
        from modules.energy_system_exporter import create_export_module
        
        print("🔍 Investment Debug für example_1b.xlsx")
        print("=" * 50)
        
        # Excel-Datei einlesen
        excel_file = Path("examples/example_1b.xlsx")
        if not excel_file.exists():
            print(f"❌ Datei nicht gefunden: {excel_file}")
            return
        
        # Settings
        settings = {'debug_mode': False}  # INFO-Level für oemof.solph 0.6.0
        
        # 1. Excel-Daten einlesen
        print("📊 1. Excel-Daten einlesen...")
        excel_reader = ExcelReader(settings)
        excel_data = excel_reader.process_excel_data(excel_file)
        print("✅ Excel-Daten eingelesen")
        
        # 2. System aufbauen
        print("🏗️  2. Energy System aufbauen...")
        system_builder = SystemBuilder(settings)
        energy_system = system_builder.build_energy_system(excel_data)
        print("✅ Energy System aufgebaut")
        
        # 3. System-Export mit Debug
        print("📤 3. System-Export mit Debug-Informationen...")
        exporter = create_export_module(settings)
        
        # Debug-Export durchführen
        export_files = exporter.export_system_with_debug(
            energy_system=energy_system,
            excel_data=excel_data,
            output_dir=Path("debug_output"),
            formats=['json']
        )
        
        print("✅ Export abgeschlossen")
        print("\n📁 Erstellte Dateien:")
        for fmt, filepath in export_files.items():
            print(f"   • {fmt.upper()}: {filepath}")
        
        # 4. Investment-Analyse anzeigen
        print("\n🔍 INVESTMENT-ANALYSE:")
        debug_info = exporter.debug_investment_objects(energy_system)
        
        print(f"Gefundene Investment-Objekte: {len(debug_info['investment_objects_found'])}")
        for flow_id in debug_info['investment_objects_found']:
            print(f"\n--- {flow_id} ---")
            analysis = debug_info['investment_analysis'][flow_id]
            
            print(f"Objekt-Typ: {analysis['object_type']}")
            print(f"ep_costs vorhanden: {analysis['has_ep_costs']}")
            print(f"ep_costs Wert: {analysis['ep_costs_value']}")
            print(f"existing vorhanden: {analysis['has_existing']}")
            print(f"existing Wert: {analysis['existing_value']}")
            print(f"maximum vorhanden: {analysis['has_maximum']}")
            print(f"maximum Wert: {analysis['maximum_value']}")
            
            # Alle verfügbaren Attribute
            raw_attrs = debug_info['raw_attributes'][flow_id]
            print("Verfügbare Attribute:")
            for attr_name, attr_info in raw_attrs.items():
                if isinstance(attr_info, dict):
                    print(f"  {attr_name}: {attr_info['value']} ({attr_info['type']})")
                else:
                    print(f"  {attr_name}: {attr_info}")
        
        print("\n" + "=" * 50)
        print("🎯 Investment-Debug abgeschlossen!")
        print("📋 Prüfen Sie die debug_output/investment_debug_*.json Datei für Details")
        
    except Exception as e:
        print(f"❌ Fehler beim Investment-Debug: {e}")
        import traceback
        traceback.print_exc()


def analyze_json_export():
    """Analysiert eine bestehende JSON-Export-Datei"""
    
    import json
    from pathlib import Path
    
    # Suche nach JSON-Export-Dateien
    output_dirs = [
        Path("data/output"),
        Path("debug_output")
    ]
    
    json_files = []
    for output_dir in output_dirs:
        if output_dir.exists():
            json_files.extend(list(output_dir.glob("**/energy_system_export_*.json")))
    
    if not json_files:
        print("❌ Keine JSON-Export-Dateien gefunden")
        return
    
    # Neueste Datei analysieren
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    print(f"🔍 Analysiere: {latest_file}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n📊 JSON-EXPORT ANALYSE:")
        print("=" * 30)
        
        # System-Info
        system_info = data.get('system_info', {})
        print(f"Investment-Flows: {system_info.get('investment_flows_count', 0)}")
        print(f"Investment-Komponenten: {system_info.get('investment_components', [])}")
        
        # Komponenten durchgehen
        components = data.get('components', {})
        print(f"\nKomponenten: {len(components)}")
        
        for comp_name, comp_data in components.items():
            flows = comp_data.get('flows', {})
            has_investment = False
            
            for flow_name, flow_props in flows.items():
                if 'investment' in flow_props:
                    has_investment = True
                    print(f"\n--- {comp_name} → {flow_name} ---")
                    investment = flow_props['investment']
                    print(f"Investment-Parameter:")
                    for key, value in investment.items():
                        print(f"  {key}: {value}")
            
            if not has_investment and len(flows) > 0:
                print(f"\n--- {comp_name} (KEIN INVESTMENT) ---")
                for flow_name, flow_props in flows.items():
                    if 'nominal_capacity' in flow_props:
                        print(f"  {flow_name}: nominal_capacity = {flow_props['nominal_capacity']}")
    
    except Exception as e:
        print(f"❌ Fehler beim Analysieren: {e}")


if __name__ == "__main__":
    print("🧪 INVESTMENT DEBUG TOOL")
    print("=" * 40)
    print("1. Investment Debug für example_1b.xlsx")
    print("2. JSON-Export-Datei analysieren")
    print("3. Beide")
    
    try:
        choice = input("\nOption auswählen (1-3): ").strip()
        
        if choice == "1":
            debug_investment_export()
        elif choice == "2":
            analyze_json_export()
        elif choice == "3":
            debug_investment_export()
            print("\n" + "="*40)
            analyze_json_export()
        else:
            print("❌ Ungültige Auswahl")
            
    except KeyboardInterrupt:
        print("\n👋 Abgebrochen")
