#!/usr/bin/env python3
"""
test_core_imports.py - Testet alle Core Imports
"""

print("🧪 TESTE CORE IMPORTS")
print("=" * 50)

try:
    # Test 1: Importiere direkt aus utilities
    print("📦 Teste direkten Import aus utilities...")
    from src.core.utilities import parse_bus_list
    print("✅ parse_bus_list direkt importierbar")
    
    # Test 2: Teste alle erwarteten Funktionen
    expected_functions = [
        'get_numeric_value',
        'get_boolean_value',
        'get_flow_parameter',
        'get_flow_extensions',
        'get_investment_extensions',
        'parse_bus_list',
        'parse_conversion_factors',
        'validate_converter_flows',
        'get_converter_bus_references',
        'validate_converter_data',
        'get_converter_summary',
        'resolve_keyword',
        'resolve_timeseries_keywords',
        'validate_flow_extensions',
        'validate_bus_references',
        'safe_get_scalars',
        'extract_investment_data',
        'setup_component_logger',
        'log_dataframe_info'
    ]
    
    missing_functions = []
    
    for func_name in expected_functions:
        try:
            from src.core.utilities import *
            if func_name in globals() or hasattr(__import__('src.core.utilities'), func_name):
                print(f"✅ {func_name}")
            else:
                print(f"❌ {func_name} - NICHT GEFUNDEN")
                missing_functions.append(func_name)
        except ImportError:
            print(f"❌ {func_name} - IMPORT FEHLER")
            missing_functions.append(func_name)
    
    # Test 3: Teste Import über core __init__
    print("\n🔧 Teste Import über core.__init__...")
    try:
        from src.core import parse_bus_list
        print("✅ parse_bus_list über core importierbar")
    except ImportError as e:
        print(f"❌ parse_bus_list über core NICHT importierbar: {e}")
    
    # Test 4: Zeige was tatsächlich exportiert wird
    print("\n📋 Was wird tatsächlich von core exportiert:")
    try:
        import src.core
        if hasattr(src.core, '__all__'):
            print(f"__all__: {src.core.__all__}")
        else:
            print("Kein __all__ definiert")
            
        available_attrs = [attr for attr in dir(src.core) if not attr.startswith('_')]
        print(f"Verfügbare Attribute: {available_attrs}")
        
    except Exception as e:
        print(f"Fehler beim Analysieren: {e}")
    
    if missing_functions:
        print(f"\n❌ FEHLENDE FUNKTIONEN: {missing_functions}")
        print("Diese müssen in utilities.py implementiert werden!")
    else:
        print("\n✅ ALLE FUNKTIONEN GEFUNDEN!")
        
except Exception as e:
    print(f"❌ UNERWARTETER FEHLER: {e}")
    import traceback
    traceback.print_exc()