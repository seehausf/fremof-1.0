# Attribut-Import Datenfluss - Visueller Guide

## 🔄 Kompletter Datenfluss: Excel → oemof.solph

```
📊 EXCEL-DATEI (house_heatpump.xlsx)
├── 📋 settings Sheet
│   ├── timeindex_start: "2025-01-01"
│   ├── timeindex_periods: 8760
│   └── timeindex_freq: "h"
├── 📋 buses Sheet
│   ├── el_bus (include: 1)
│   └── heat_bus (include: 1)
├── 📋 sources Sheet
│   ├── pv_plant (investment: 1, profile: pv_profile)
│   └── grid_import (investment: 0, variable_costs: 0.30)
├── 📋 sinks Sheet
│   ├── house_load (profile: load_profile)
│   └── grid_export (variable_costs: -0.08)
├── 📋 simple_transformers Sheet
│   └── heat_pump (investment: 1, conversion_factor: 3.5)
└── 📋 timeseries Sheet
    ├── timestamp (8760 rows)
    ├── pv_profile (0.0 - 1.0)
    ├── load_profile (kW values)
    └── heat_profile (kW values)

           ⬇️ SYSTEM BUILDER VERARBEITUNG ⬇️

🏗️ SYSTEM BUILDER (system_builder.py)
├── 🔧 _build_buses()
│   ├── el_bus → solph.buses.Bus(label="el_bus")
│   └── heat_bus → solph.buses.Bus(label="heat_bus")
├── 🔧 _build_sources()
│   ├── pv_plant → Source mit Investment-Flow
│   │   ├── Investment: ep_costs=71.05 (1000€/25a/4%)
│   │   ├── Profile: max=[0.0, 0.0, 0.2, 0.8, 1.0, ...]
│   │   └── Output: el_bus
│   └── grid_import → Source mit Standard-Flow
│       ├── Kapazität: 999999 kW
│       ├── Variable Kosten: 0.30 €/kWh
│       └── Output: el_bus
├── 🔧 _build_sinks()
│   ├── house_load → Sink mit Fix-Profil
│   │   ├── Fix: [5.2, 4.8, 4.5, 6.2, 7.8, ...]
│   │   ├── Auto-Kapazität: 12.0 kW (max*1.2)
│   │   └── Input: el_bus
│   └── grid_export → Sink mit Standard-Flow
│       ├── Variable Kosten: -0.08 €/kWh
│       └── Input: el_bus
└── 🔧 _build_simple_transformers()
    └── heat_pump → Converter mit Investment-Flow
        ├── Input: el_bus (Investment-Flow)
        │   ├── Investment: ep_costs=115.63 (1200€/15a/5%)
        │   └── Variable Kosten: 0.01 €/kWh
        ├── Output: heat_bus (Standard-Flow)
        └── Conversion Factor: 3.5

           ⬇️ RESULTIERENDES ENERGIESYSTEM ⬇️

🎯 OEMOF.SOLPH ENERGIESYSTEM
├── 📊 Timeindex: 2025-01-01 bis 2025-12-31 (8760h)
├── 🔌 Buses: 2
│   ├── Bus(label="el_bus")
│   └── Bus(label="heat_bus")
├── ⚡ Sources: 2
│   ├── Source(label="pv_plant")
│   │   └── outputs={el_bus: Flow(investment=Investment(...), max=profile)}
│   └── Source(label="grid_import")
│       └── outputs={el_bus: Flow(nominal_capacity=999999, variable_costs=0.30)}
├── 🔽 Sinks: 2
│   ├── Sink(label="house_load")
│   │   └── inputs={el_bus: Flow(fix=profile, nominal_capacity=12.0)}
│   └── Sink(label="grid_export")
│       └── inputs={el_bus: Flow(variable_costs=-0.08)}
└── 🔄 Converters: 1
    └── Converter(label="heat_pump")
        ├── inputs={el_bus: Flow(investment=Investment(...))}
        ├── outputs={heat_bus: Flow()}
        └── conversion_factors={heat_bus: 3.5}
```

## 📊 Detaillierte Attribut-Zuordnung

### **1. Source-Komponente (PV-Anlage)**

```python
# EXCEL-ZEILE:
{
    'label': 'pv_plant',
    'include': 1,
    'bus': 'el_bus',
    'existing': 0,
    'investment': 1,
    'investment_costs': 1000,
    'lifetime': 25,
    'interest_rate': 0.04,
    'invest_max': 20,
    'profile_column': 'pv_profile',
    'variable_costs': 0.0
}

# VERARBEITUNGSSCHRITTE:
Step 1: Investment-Berechnung
├── ep_costs = 1000 * annuity_factor(25, 0.04)
├── annuity_factor = 0.04 * (1.04^25) / ((1.04^25) - 1) = 0.071
└── ep_costs = 1000 * 0.071 = 71.05 €/kW/a

Step 2: Profil-Verarbeitung
├── profile_column = 'pv_profile'
├── profile_values = timeseries['pv_profile'].values
├── max(profile_values) = 1.0 (bereits normalisiert)
└── flow_params['max'] = [0.0, 0.0, 0.2, 0.8, 1.0, ...]

Step 3: Flow-Erstellung
├── Investment-Objekt: Investment(ep_costs=71.05, existing=0, maximum=20, minimum=0)
├── Profile: max=pv_profile_values
└── Variable Kosten: 0.0 €/kWh

# RESULTIERENDES OEMOF.SOLPH OBJEKT:
solph.components.Source(
    label='pv_plant',
    outputs={
        el_bus: solph.Flow(
            nominal_capacity=200.0,        # Fallback-Wert
            investment=Investment(
                ep_costs=71.05,            # ✅ Berechnete Annuität
                existing=0,                # ✅ Aus Excel
                maximum=20,                # ✅ Aus invest_max
                minimum=0                  # ✅ Aus invest_min
            ),
            max=[0.0, 0.0, 0.2, ...],     # ✅ PV-Profil
            variable_costs=0.0             # ✅ Aus Excel
        )
    }
)
```

### **2. Sink-Komponente (Haushaltslast)**

```python
# EXCEL-ZEILE:
{
    'label': 'house_load',
    'include': 1,
    'bus': 'el_bus',
    'profile_column': 'load_profile',
    'variable_costs': 0.0
}

# VERARBEITUNGSSCHRITTE:
Step 1: Profil-Verarbeitung
├── profile_column = 'load_profile'
├── profile_values = timeseries['load_profile'].values
├── max(profile_values) = 10.0 kW
└── flow_params['fix'] = [5.2, 4.8, 4.5, 6.2, 7.8, ...]

Step 2: Auto-Kapazität
├── Keine nominal_capacity in Excel
├── max_profile = max([5.2, 4.8, 4.5, 6.2, 7.8, ...]) = 10.0
└── auto_capacity = 10.0 * 1.2 = 12.0 kW

Step 3: Flow-Erstellung
├── Fix-Profil: [5.2, 4.8, 4.5, ...]
├── Auto-Kapazität: 12.0 kW
└── Variable Kosten: 0.0 €/kWh

# RESULTIERENDES OEMOF.SOLPH OBJEKT:
solph.components.Sink(
    label='house_load',
    inputs={
        el_bus: solph.Flow(
            fix=[5.2, 4.8, 4.5, ...],     # ✅ Fix-Lastprofil
            nominal_capacity=12.0,         # ✅ Auto-berechnet
            variable_costs=0.0             # ✅ Aus Excel
        )
    }
)
```

### **3. Converter-Komponente (Wärmepumpe)**

```python
# EXCEL-ZEILE:
{
    'label': 'heat_pump',
    'include': 1,
    'input_bus': 'el_bus',
    'output_bus': 'heat_bus',
    'conversion_factor': 3.5,
    'existing': 0,
    'investment': 1,
    'investment_costs': 1200,
    'lifetime': 15,
    'interest_rate': 0.05,
    'invest_max': 15,
    'variable_costs': 0.01
}

# VERARBEITUNGSSCHRITTE:
Step 1: Investment-Berechnung (Input-Flow)
├── ep_costs = 1200 * annuity_factor(15, 0.05)
├── annuity_factor = 0.05 * (1.05^15) / ((1.05^15) - 1) = 0.096
└── ep_costs = 1200 * 0.096 = 115.63 €/kW/a

Step 2: Input-Flow-Erstellung
├── Investment-Objekt: Investment(ep_costs=115.63, maximum=15)
└── Variable Kosten: 0.01 €/kWh

Step 3: Output-Flow-Erstellung
├── Normaler Flow ohne Investment
└── Conversion Factor: 3.5

# RESULTIERENDES OEMOF.SOLPH OBJEKT:
solph.components.Converter(
    label='heat_pump',
    inputs={
        el_bus: solph.Flow(
            nominal_capacity=200.0,        # Fallback-Wert
            investment=Investment(
                ep_costs=115.63,           # ✅ Berechnete Annuität
                existing=0,                # ✅ Aus Excel
                maximum=15,                # ✅ Aus invest_max
                minimum=0                  # ✅ Standard
            ),
            variable_costs=0.01            # ✅ Aus Excel
        )
    },
    outputs={
        heat_bus: solph.Flow()             # ✅ Standard-Flow
    },
    conversion_factors={
        heat_bus: 3.5                      # ✅ COP aus Excel
    }
)
```

## 🎯 Kernfunktionen im Detail

### **1. Investment-Berechnung**
```python
def _calculate_annuity(investment_costs, lifetime, interest_rate):
    """
    Berechnet die Annuität für Investment-Kosten
    """
    if interest_rate == 0:
        return investment_costs / lifetime
    
    q = 1 + interest_rate
    annuity_factor = (interest_rate * q**lifetime) / (q**lifetime - 1)
    return investment_costs * annuity_factor

# Beispiele:
annuity(1000, 25, 0.04) = 71.05 €/kW/a   # PV-Anlage
annuity(1200, 15, 0.05) = 115.63 €/kW/a  # Wärmepumpe
annuity(800, 20, 0.0) = 40.0 €/kW/a      # Zinslos
```

### **2. Profil-Verarbeitung**
```python
def _process_profile(profile_column, timeseries_data, flow_type):
    """
    Lädt und verarbeitet Profile aus Excel
    """
    if profile_column in timeseries_data.columns:
        profile_values = timeseries_data[profile_column].values
        
        # Für Sources: Normalisierung auf max=1.0
        if flow_type == 'source' and max(profile_values) > 1.0:
            profile_values = profile_values / max(profile_values)
        
        return profile_values.tolist()
    
    return None

# Anwendung:
pv_profile = _process_profile('pv_profile', timeseries, 'source')
# → [0.0, 0.0, 0.2, 0.8, 1.0, ...] (normalisiert)

load_profile = _process_profile('load_profile', timeseries, 'sink')
# → [5.2, 4.8, 4.5, 6.2, 7.8, ...] (absolute Werte)
```

### **3. Automatische Kapazitäts-Berechnung**
```python
def _auto_calculate_capacity(profile_values, component_type):
    """
    Berechnet automatische Kapazität basierend auf Profil
    """
    if component_type == 'sink' and profile_values:
        # Für Sinks: 20% Puffer über Maximum
        return max(profile_values) * 1.2
    
    elif component_type == 'source' and profile_values:
        # Für Sources: Investment bestimmt Kapazität
        return 500  # Fallback-Wert
    
    return None

# Beispiel:
load_profile = [5.2, 4.8, 4.5, 6.2, 7.8, 9.1, 8.5, ...]
auto_capacity = max(load_profile) * 1.2 = 9.1 * 1.2 = 10.9 kW
```

## 🔧 Wichtige Implementierungsdetails

### **Investment-Flow-Zuordnung**
```python
# WICHTIG: Investment wird immer am INPUT-Flow eines Converters angebracht
# Converter(
#     inputs={bus: Flow(investment=Investment(...))},   # ← Investment hier
#     outputs={bus: Flow()},                           # ← Kein Investment
#     conversion_factors={bus: factor}
# )
```

### **Profile-Längen-Validierung**
```python
# Profile müssen exakt die Länge des Zeitindex haben
timeindex_length = len(energy_system.timeindex)  # z.B. 8760
profile_length = len(profile_values)             # muss 8760 sein

if profile_length != timeindex_length:
    raise ValueError(f"Profil-Länge {profile_length} ≠ Zeitindex-Länge {timeindex_length}")
```

### **Fallback-Strategien**
```python
# 1. Fehlende Investment-Parameter
invest_max = component_data.get('invest_max', 500)     # Standard: 500 kW
invest_min = component_data.get('invest_min', 0)       # Standard: 0 kW

# 2. Fehlende Kapazität
if 'nominal_capacity' not in component_data:
    nominal_capacity = 200.0  # Standard-Fallback

# 3. Fehlende Variable Kosten
variable_costs = component_data.get('variable_costs', 0.0)  # Standard: 0 €/kWh
```

Diese Analyse zeigt, wie der SystemBuilder systematisch Excel-Daten in vollständige oemof.solph-Objekte transformiert, mit intelligenten Fallback-Strategien und automatischen Berechnungen.