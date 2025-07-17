# System Builder Analyse - Attribute und Datenfluss

## 📋 Übersicht

Der `system_builder.py` ist das Herzstück der Excel-zu-oemof.solph Transformation. Er liest Excel-Daten und erstellt daraus vollständige oemof.solph Energiesystem-Objekte.

## 🔍 Unterstützte Excel-Sheets und Attribute

### **1. BUSES Sheet**
```python
# Excel-Spalten:
'label'        → Bus-Name (eindeutig)
'include'      → 1/0 für aktiviert/deaktiviert
'description'  → Beschreibung (optional)

# Beispiel Excel-Zeile:
label: "el_bus"
include: 1
description: "Hauptelektrobus"

# Resultierendes oemof.solph Objekt:
solph.buses.Bus(label="el_bus")
```

### **2. SOURCES Sheet**
```python
# Excel-Spalten:
'label'              → Source-Name (eindeutig)
'include'            → 1/0 für aktiviert/deaktiviert
'bus'                → Verbundener Bus (Referenz)
'nominal_capacity'   → Kapazität in kW (kann "INVEST" sein)
'variable_costs'     → Variable Kosten in €/kWh
'profile_column'     → Spalte in timeseries Sheet
'existing'           → Bestehende Kapazität (Investment)
'investment'         → 1/0 für Investment aktiviert
'investment_costs'   → Investitionskosten in €/kW
'invest_min'         → Minimale Investition in kW
'invest_max'         → Maximale Investition in kW
'lifetime'           → Lebensdauer in Jahren
'interest_rate'      → Zinssatz (z.B. 0.04 für 4%)
'description'        → Beschreibung (optional)

# Beispiel Excel-Zeile:
label: "pv_plant"
bus: "el_bus"
existing: 0
investment: 1
investment_costs: 1000
lifetime: 25
interest_rate: 0.04
profile_column: "pv_profile"

# Resultierendes oemof.solph Objekt:
solph.components.Source(
    label="pv_plant",
    outputs={
        el_bus: solph.Flow(
            nominal_capacity=200.0,  # Fallback-Wert
            investment=Investment(
                ep_costs=71.05,      # Berechnet: 1000 * annuity_factor
                existing=0,
                maximum=500,         # Aus invest_max
                minimum=0           # Aus invest_min
            ),
            max=pv_profile_values   # Aus timeseries Sheet
        )
    }
)
```

### **3. SINKS Sheet**
```python
# Excel-Spalten:
'label'              → Sink-Name (eindeutig)
'include'            → 1/0 für aktiviert/deaktiviert
'bus'                → Verbundener Bus (Referenz)
'nominal_capacity'   → Kapazität in kW (optional)
'variable_costs'     → Variable Kosten in €/kWh
'profile_column'     → Spalte in timeseries Sheet
'existing'           → Bestehende Kapazität (Investment)
'investment'         → 1/0 für Investment aktiviert
'investment_costs'   → Investitionskosten in €/kW
'invest_min'         → Minimale Investition in kW
'invest_max'         → Maximale Investition in kW
'lifetime'           → Lebensdauer in Jahren
'interest_rate'      → Zinssatz
'description'        → Beschreibung (optional)

# Beispiel Excel-Zeile:
label: "house_load"
bus: "el_bus"
profile_column: "load_profile"
variable_costs: 0.0

# Resultierendes oemof.solph Objekt:
solph.components.Sink(
    label="house_load",
    inputs={
        el_bus: solph.Flow(
            fix=load_profile_values,        # Feste Last
            nominal_capacity=12.0,          # Auto-berechnet: max(profile) * 1.2
            variable_costs=0.0
        )
    }
)
```

### **4. SIMPLE_TRANSFORMERS Sheet**
```python
# Excel-Spalten:
'label'              → Transformer-Name (eindeutig)
'include'            → 1/0 für aktiviert/deaktiviert
'input_bus'          → Eingangs-Bus (Referenz)
'output_bus'         → Ausgangs-Bus (Referenz)
'conversion_factor'  → Wirkungsgrad/Umwandlungsfaktor
'nominal_capacity'   → Kapazität in kW (kann "INVEST" sein)
'variable_costs'     → Variable Kosten in €/kWh
'existing'           → Bestehende Kapazität (Investment)
'investment'         → 1/0 für Investment aktiviert
'investment_costs'   → Investitionskosten in €/kW
'invest_min'         → Minimale Investition in kW
'invest_max'         → Maximale Investition in kW
'lifetime'           → Lebensdauer in Jahren
'interest_rate'      → Zinssatz
'description'        → Beschreibung (optional)

# Beispiel Excel-Zeile:
label: "heat_pump"
input_bus: "el_bus"
output_bus: "heat_bus"
conversion_factor: 3.5
existing: 0
investment: 1
investment_costs: 1200
lifetime: 15
interest_rate: 0.05

# Resultierendes oemof.solph Objekt:
solph.components.Converter(
    label="heat_pump",
    inputs={
        el_bus: solph.Flow(
            nominal_capacity=200.0,  # Fallback-Wert
            investment=Investment(
                ep_costs=115.63,     # Berechnet: 1200 * annuity_factor
                existing=0,
                maximum=400,         # Aus invest_max
                minimum=0           # Aus invest_min
            ),
            variable_costs=0.01
        )
    },
    outputs={
        heat_bus: solph.Flow()      # Ohne Investment
    },
    conversion_factors={heat_bus: 3.5}  # COP = 3.5
)
```

### **5. TIMESERIES Sheet**
```python
# Excel-Spalten:
'timestamp'          → Zeitstempel (DateTime)
'pv_profile'         → PV-Erzeugungsprofil (0-1)
'load_profile'       → Lastprofil (kW)
'wind_profile'       → Wind-Erzeugungsprofil (0-1)
'heat_profile'       → Wärmeprofil (kW)
# ... weitere Profile nach Bedarf

# Beispiel Excel-Daten:
timestamp            | pv_profile | load_profile | heat_profile
2025-01-01 00:00:00 | 0.0        | 5.2         | 8.5
2025-01-01 01:00:00 | 0.0        | 4.8         | 8.2
2025-01-01 02:00:00 | 0.0        | 4.5         | 7.8
...

# Verwendung im System:
# - profile_column in anderen Sheets referenziert diese Spalten
# - Automatische Längen-Validierung gegen timeindex
# - Normalisierung für Sources (max=1.0)
```

## 🔄 Datenfluss-Analyse

### **Phase 1: Excel-Daten Einlesen**
```python
def build_energy_system(self, excel_data: Dict[str, Any]) -> solph.EnergySystem:
    """
    Hauptmethode - orchestriert den gesamten Aufbau
    """
    # 1. Zeitindex aus settings erstellen
    timeindex = self._create_timeindex(excel_data['settings'])
    
    # 2. Leeres EnergySystem erstellen
    energy_system = solph.EnergySystem(timeindex=timeindex)
    
    # 3. Komponenten in korrekter Reihenfolge erstellen
    self._build_buses(excel_data)           # Zuerst Buses
    self._build_sources(excel_data)         # Dann Sources
    self._build_sinks(excel_data)           # Dann Sinks
    self._build_simple_transformers(excel_data)  # Dann Transformers
    
    # 4. Alle Objekte zum EnergySystem hinzufügen
    energy_system.add(*self.component_objects.values())
    energy_system.add(*self.bus_objects.values())
    
    return energy_system
```

### **Phase 2: Bus-Erstellung**
```python
def _build_buses(self, excel_data: Dict[str, Any]):
    """
    Erstellt alle Bus-Objekte
    """
    buses_df = excel_data['buses']
    
    for _, bus_data in buses_df.iterrows():
        if bus_data['include'] == 1:
            # Einfacher Bus ohne Parameter
            bus = solph.buses.Bus(label=bus_data['label'])
            self.bus_objects[bus_data['label']] = bus
```

### **Phase 3: Investment-Parameter-Verarbeitung**
```python
def _process_new_investment_capacity(self, component_data: pd.Series):
    """
    KERNLOGIK: Investment-Parameter berechnen
    """
    # 1. Prüfe ob Investment aktiviert
    if component_data.get('investment', 0) != 1:
        # Einfache Kapazität
        if 'nominal_capacity' in component_data:
            return float(component_data['nominal_capacity'])
        return None
    
    # 2. Investment-Parameter sammeln
    investment_costs = component_data.get('investment_costs', 0)
    lifetime = component_data.get('lifetime', None)
    interest_rate = component_data.get('interest_rate', None)
    
    # 3. EP-Costs berechnen
    if lifetime and interest_rate is not None:
        # Annuity-Formel anwenden
        if interest_rate == 0:
            ep_costs = investment_costs / lifetime
        else:
            q = 1 + interest_rate
            annuity_factor = (interest_rate * q**lifetime) / (q**lifetime - 1)
            ep_costs = investment_costs * annuity_factor
    else:
        # Direkte Kosten
        ep_costs = investment_costs
    
    # 4. Investment-Objekt erstellen
    investment = Investment(
        ep_costs=ep_costs,
        existing=component_data.get('existing', 0),
        maximum=component_data.get('invest_max', 500),  # Fallback
        minimum=component_data.get('invest_min', 0)
    )
    
    return investment
```

### **Phase 4: Flow-Erstellung**
```python
def _create_investment_flow(self, component_data: pd.Series, timeseries_data: pd.DataFrame, flow_type: str):
    """
    Erstellt Flow-Objekte mit allen Parametern
    """
    flow_params = {}
    
    # 1. Kapazität (Investment oder Normal)
    nominal_capacity = self._process_new_investment_capacity(component_data)
    if nominal_capacity is not None:
        flow_params['nominal_capacity'] = nominal_capacity
    
    # 2. Variable Kosten
    if 'variable_costs' in component_data:
        flow_params['variable_costs'] = float(component_data['variable_costs'])
    
    # 3. Profile verarbeiten
    profile = self._process_profiles(component_data, timeseries_data, flow_type)
    if profile is not None:
        if flow_type == 'sink':
            flow_params['fix'] = profile  # Feste Last
            # Auto-Kapazität wenn nicht gesetzt
            if 'nominal_capacity' not in flow_params:
                flow_params['nominal_capacity'] = max(profile) * 1.2
        else:
            flow_params['max'] = profile  # Maximal-Profil
    
    # 4. Flow erstellen
    return solph.Flow(**flow_params)
```

### **Phase 5: Komponenten-Erstellung**
```python
def _build_sources(self, excel_data: Dict[str, Any]):
    """
    Erstellt alle Source-Objekte
    """
    sources_df = excel_data['sources']
    timeseries_data = excel_data.get('timeseries', pd.DataFrame())
    
    for _, source_data in sources_df.iterrows():
        if source_data['include'] == 1:
            # Bus-Referenz auflösen
            bus = self.bus_objects[source_data['bus']]
            
            # Flow erstellen
            flow = self._create_investment_flow(source_data, timeseries_data, 'source')
            
            # Source erstellen
            source = solph.components.Source(
                label=source_data['label'],
                outputs={bus: flow}
            )
            
            self.component_objects[source_data['label']] = source
```

## 💡 Besonderheiten und Automatismen

### **1. Automatische Kapazitäts-Berechnung**
```python
# Für Sinks mit Profile aber ohne nominal_capacity:
if flow_type == 'sink' and profile and 'nominal_capacity' not in flow_params:
    flow_params['nominal_capacity'] = max(profile) * 1.2  # 20% Puffer
```

### **2. Investment-Fallback-Strategien**
```python
# 1. Vollständige Annuity-Berechnung
if lifetime and interest_rate is not None:
    ep_costs = investment_costs * annuity_factor

# 2. Direkte Kosten-Verwendung
else:
    ep_costs = investment_costs

# 3. Fallback-Kapazitäten
invest_max = component_data.get('invest_max', 500)  # Standard: 500 kW
invest_min = component_data.get('invest_min', 0)    # Standard: 0 kW
```

### **3. Profil-Verarbeitung**
```python
def _process_profiles(self, component_data, timeseries_data, flow_type):
    """
    Lädt Profile aus timeseries Sheet
    """
    if 'profile_column' not in component_data:
        return None
    
    profile_col = component_data['profile_column']
    if profile_col and profile_col in timeseries_data.columns:
        profile_values = timeseries_data[profile_col].values
        
        # Validierung
        if len(profile_values) == 0:
            return None
        
        # Für Sources: Normalisierung auf max=1.0
        if flow_type == 'source' and max(profile_values) > 1.0:
            profile_values = profile_values / max(profile_values)
        
        return profile_values.tolist()
    
    return None
```

### **4. Robuste Fehlerbehandlung**
```python
try:
    # Komponente erstellen
    component = solph.components.Source(...)
    self.component_objects[label] = component
    
except Exception as e:
    self.logger.error(f"❌ Fehler beim Erstellen von {label}: {e}")
    # Weiter mit nächster Komponente
    continue
```

## 🎯 Zusammenfassung

Der SystemBuilder transformiert Excel-Daten in oemof.solph Objekte durch:

1. **Strukturierte Verarbeitung**: Buses → Sources → Sinks → Transformers
2. **Intelligente Investment-Berechnung**: Annuity-Formel mit Fallbacks
3. **Automatische Profil-Integration**: Zeitreihen aus timeseries Sheet
4. **Robuste Fehlerbehandlung**: Systembau auch bei teilweise fehlerhaften Daten
5. **Flexible Kapazitäts-Strategien**: Investment oder feste Kapazitäten

**Resultat**: Vollständiges oemof.solph EnergySystem bereit für die Optimierung.