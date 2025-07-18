# Multi-IO Energy System - Complete Project Roadmap

## 📋 Projekt-Übersicht

**Datum:** Juli 2025  
**Status:** Phase 1 bereit für Implementierung  
**Ziel:** Erweiterte Multi-Input/Output-Energiesystem-Modellierung mit interaktiver Timestep-Anpassung

---

## 🎯 Aktueller Stand

### **✅ Bereits implementiert:**
- **Multi-IO System Builder**: Unterstützt Multi-Input/Output-Transformers
- **Multi-IO Excel Reader**: Parst Bus-Strings mit `|` Trennzeichen
- **Backward-Kompatibilität**: Bestehende Excel-Dateien funktionieren weiterhin
- **Investment-Logik**: Investment-Parameter am ersten Flow
- **Beispiel-Templates**: BHKW, Wärmepumpe, Komplexe Systeme

### **✅ Verfügbare Dateien:**
- `modules/system_builder.py` (Multi-IO Version)
- `modules/excel_reader.py` (Fixed Version)
- `create_multi_io_examples.py` (Beispiel-Generator)
- 4 Beispiel-Excel-Dateien (BHKW, Wärmepumpe, Komplex, Nahwärme)

### **✅ Getestete Funktionalität:**
- BHKW-System: `Gas → Strom + Wärme` erfolgreich getestet
- Investment-Optimierung funktioniert
- Multi-Bus-Parsing: `"el_bus|heat_bus"` → `["el_bus", "heat_bus"]`

---

## 🛠️ Implementierungs-Roadmap

### **Phase 1: Interaktive Timestep-Anpassung [NEXT]**

#### **1.1 Benutzer-Dialog für Timestep-Reduktion**
**Ziel:** Interaktiver Dialog zur Laufzeit-Optimierung

**Implementierung:**
```python
def ask_timestep_reduction(self, original_length, estimated_solve_time):
    """
    Interaktiver Dialog für Timestep-Reduktion
    """
    print(f"\n🕒 Zeitreihe: {original_length} Zeitschritte")
    print(f"⏱️ Geschätzte Lösungszeit: {estimated_solve_time}")
    print("\nZeitreihen-Reduktion verfügbar:")
    print("1. Nein - Vollständige Zeitreihe")
    print("2. Rolling Mean (Stunden-Mittelwerte)")
    print("3. Sampling (jede n-te Stunde)")
    
    choice = input("Auswahl (1-3): ").strip()
    
    if choice == "2":
        hours = int(input("Stunden für Rolling Mean (z.B. 24): "))
        return ("rolling_mean", hours)
    elif choice == "3":
        n = int(input("Sampling-Faktor (z.B. 4): "))
        return ("sampling", n)
    else:
        return ("none", None)
```

**Integration-Punkt:** Nach Excel-Einlesen, vor System-Builder

#### **1.2 Rolling Mean Integration**
**Ziel:** Stunden-Mittelwerte für alle Zeitreihen

**Implementierung:**
```python
def apply_rolling_mean(self, timeseries_data, hours):
    """
    Wendet Rolling Mean auf alle Zeitreihen an
    """
    new_data = {}
    
    for column in timeseries_data.columns:
        if column == 'timestamp':
            # Neuer Zeitindex mit reduzierter Länge
            new_data[column] = timeseries_data[column].iloc[::hours]
        else:
            # Rolling Mean anwenden
            new_data[column] = timeseries_data[column].rolling(window=hours).mean().iloc[::hours]
    
    return pd.DataFrame(new_data).dropna()
```

#### **1.3 Settings Sheet Erweiterung**
**Ziel:** Zeitraum-Validierung und automatische Anpassung

**Neue Settings-Parameter:**
```excel
Parameter          | Value              | Description
timeindex_start    | 2025-01-01        | Simulationsstart
timeindex_end      | 2025-12-31        | Simulationsende  
timeseries_freq    | h                 | Granularität (h/15min)
interactive_timestep| true              | Interaktive Reduktion aktivieren
auto_adjust_end    | true              | Enddatum automatisch anpassen
```

#### **1.4 Automatische Enddatum-Anpassung**
**Ziel:** Zeitreihen-Länge vs. gewünschter Zeitraum validieren

**Implementierung:**
```python
def validate_timerange(self, settings, timeseries_length):
    """
    Validiert Zeitraum gegen verfügbare Zeitreihen-Länge
    """
    start_date = pd.to_datetime(settings['timeindex_start'])
    end_date = pd.to_datetime(settings['timeindex_end'])
    freq = settings.get('timeseries_freq', 'h')
    
    # Gewünschte Zeitreihen-Länge
    desired_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    required_length = len(desired_range)
    
    if timeseries_length < required_length:
        # Enddatum anpassen
        actual_end = desired_range[timeseries_length - 1]
        settings['timeindex_end'] = actual_end.strftime('%Y-%m-%d')
        
        self.logger.warning(f"⚠️ Enddatum angepasst auf {actual_end.strftime('%Y-%m-%d')}")
        self.logger.warning(f"   Verfügbare Zeitreihen: {timeseries_length}")
        self.logger.warning(f"   Gewünschte Länge: {required_length}")
    
    return settings
```

### **Phase 2: Erweiterte Conversion-Faktoren**

#### **2.1 Keyword-Erkennung für Conversion-Faktoren**
**Ziel:** Zeitvariable Conversion-Faktoren unterstützen

**Beispiel-Anwendung:**
```excel
# Wärmepumpe mit temperatuabhängiger COP
input_conversion_factors  | 1.0|ambient_heat_factor
output_conversion_factors | hp_cop_profile

# Timeseries Sheet
timestamp    | ambient_heat_factor | hp_cop_profile
2025-01-01   | 2.5                | 3.5
2025-01-02   | 2.2                | 3.2
```

**Implementierung:**
```python
def _parse_conversion_factor(self, factor_string, timeseries_data):
    """
    Parst Conversion-Faktor: Zahl oder Timeseries-Referenz
    """
    try:
        # Versuche als Zahl zu parsen
        return float(factor_string)
    except ValueError:
        # Ist ein Keyword - suche in Timeseries
        if factor_string in timeseries_data.columns:
            return timeseries_data[factor_string].values
        else:
            raise ValueError(f"Timeseries-Profil '{factor_string}' nicht gefunden")
```

#### **2.2 System Builder Integration**
**Ziel:** Zeitvariable Faktoren in oemof.solph

**Herausforderung:** oemof.solph conversion_factors sind normalerweise konstant

**Lösungsansatz:** 
```python
# Zeitvariable Faktoren als Flow-Parameter
if isinstance(conversion_factor, np.ndarray):
    # Zeitvariable Faktoren über Flow-Effizienz
    flow_params['efficiency'] = conversion_factor
else:
    # Konstante Faktoren über conversion_factors
    conversion_factors[bus] = conversion_factor
```

### **Phase 3: EBS-Kraftwerk Integration**

#### **3.1 EBS-Kraftwerk Spezifikation**
**Technische Daten:**
- **Input:** 90% Hausmüll + 10% Erdgas (Stützfeuerung)
- **Output:** 15% Strom + 20% Dampf + 45% Wärme (20% Verluste)
- **Investment:** Bezieht sich auf Strom-Erzeugung (erster Output)

**Excel-Konfiguration:**
```excel
label                    | ebs_plant
input_bus               | waste_bus|gas_bus
output_bus              | el_bus|steam_bus|heat_bus
input_conversion_factors | 0.9|0.1
output_conversion_factors| 0.15|0.2|0.45
investment              | 1
investment_costs        | 3000
existing                | 0
invest_max              | 100
```

#### **3.2 Investment-Logik Erweiterung**
**Problem:** Investment soll auf Strom-Erzeugung bezogen werden

**Lösung:**
```python
def _create_ebs_investment_flows(self, transformer_data, output_buses):
    """
    Spezielle Investment-Logik für EBS-Kraftwerk
    Investment bezieht sich auf ersten Output (Strom)
    """
    output_flows = {}
    
    for i, bus_obj in enumerate(output_buses):
        if i == 0:  # Erster Bus (Strom) mit Investment
            output_flows[bus_obj] = self._create_investment_flow(
                transformer_data, timeseries_data, 'output'
            )
        else:  # Weitere Busse ohne Investment
            output_flows[bus_obj] = self._create_standard_flow(
                transformer_data, timeseries_data, 'output'
            )
    
    return output_flows
```

#### **3.3 Neue Bus-Typen**
**Erforderliche Busse:**
```python
# Neue Bus-Definitionen
BUS_TYPES = {
    'waste_bus': 'Hausmüll-Bus',
    'steam_bus': 'Dampf-Bus (Prozessdampf)',
    'heat_bus': 'Wärme-Bus (Fernwärme)',
    'gas_bus': 'Erdgas-Bus (Stützfeuerung)'
}
```

### **Phase 4: Beispiel-Excel und Templates**

#### **4.1 EBS-Kraftwerk Beispiel**
**Dateiname:** `ebs_power_plant.xlsx`

**Vollständiges System:**
```excel
# Buses
waste_bus, gas_bus, el_bus, steam_bus, heat_bus

# Sources
waste_supply → waste_bus (variable_costs: 0.02)
gas_supply → gas_bus (variable_costs: 0.06)

# Transformers
ebs_plant: waste_bus|gas_bus → el_bus|steam_bus|heat_bus
Faktoren: 0.9|0.1 → 0.15|0.2|0.45

# Sinks
el_load ← el_bus (mit Profil)
steam_demand ← steam_bus (mit Profil)
heat_demand ← heat_bus (mit Profil)
```

#### **4.2 Zeitvariable Conversion Beispiel**
**Dateiname:** `heat_pump_variable_cop.xlsx`

**Wärmepumpe mit variablem COP:**
```excel
# Transformer
heat_pump: el_bus|ambient_heat_bus → heat_bus
Input-Faktoren: 1.0|ambient_heat_factor
Output-Faktoren: hp_cop_profile

# Timeseries
timestamp, ambient_heat_factor, hp_cop_profile
(Temperaturabhängige Werte)
```

#### **4.3 Template Creator Update**
**Neue Methoden:**
- `create_ebs_example()`
- `create_variable_cop_example()`
- `create_interactive_timestep_example()`

### **Phase 5: Testing & Validierung**

#### **5.1 Interaktive Tests**
- [ ] Timestep-Reduktion Dialog
- [ ] Rolling Mean Funktionalität
- [ ] Automatische Enddatum-Anpassung

#### **5.2 EBS-Validierung**
- [ ] Multi-Input/Output Investment
- [ ] Conversion-Faktoren Bilanzierung
- [ ] Optimierungsergebnisse

#### **5.3 Backward-Kompatibilität**
- [ ] Bestehende Excel-Dateien
- [ ] Alte API-Aufrufe
- [ ] Main.py Integration

---

## 📝 TODO-Liste (Spätere Implementierung)

### **24n+1 Algorithmus Überarbeitung**
- [ ] **TODO-1**: 24n+1 Strategie komplett neu implementieren
  - **Problem:** Aktueller Algorithmus ist nicht korrekt
  - **Gewünschte Logik:** Typtag-Bildung aus verschiedenen Tagen
  - **n=1 Beispiel:** Jede 25. Stunde → H0_Tag1, H1_Tag2, H2_Tag3, etc.
  - **n=0.5 Beispiel:** Jede 12.5. Stunde → 2 Stunden pro Tag
  - **Zeitabstand:** Bleibt 1 Stunde zwischen ausgewählten Punkten
  
**Korrekte Implementierung:**
```python
def _apply_24n_plus_1_strategy(self, timeseries, n_factor):
    """
    Korrekte 24n+1 Implementierung
    Erstellt Typtag aus verschiedenen Tagen
    """
    # Berechne Sampling-Intervall
    interval = int(24 * n_factor) + 1
    
    # Erstelle Typtag (24 Stunden)
    selected_indices = []
    for hour in range(24):
        # Finde diese Stunde aus verschiedenen Tagen
        day_index = hour // interval
        hour_in_day = hour % 24
        
        # Berechne absoluten Index
        absolute_index = day_index * 24 + hour_in_day
        
        if absolute_index < len(timeseries):
            selected_indices.append(absolute_index)
    
    # Neue Zeitreihe mit 1h Abstand
    new_timeindex = pd.date_range(start='2025-01-01', periods=len(selected_indices), freq='h')
    return timeseries.iloc[selected_indices], new_timeindex
```

- [ ] **TODO-2**: Visualisierung der 24n+1 Strategie
  - [ ] Vorher-Nachher-Vergleich des Typtags
  - [ ] Zeige welche Stunden aus welchen Tagen stammen
  - [ ] Typtag-Charakteristika visualisieren

- [ ] **TODO-3**: Validierung der 24n+1 Ergebnisse
  - [ ] Sicherstellen dass Typtag repräsentativ ist
  - [ ] Statistik-Vergleich Original vs. Typtag
  - [ ] Optimierungsergebnisse vergleichen

### **Weitere Verbesserungen**
- [ ] **TODO-4**: Erweiterte Zeitreihen-Strategien
  - [ ] Saisonale Auswahl (nur Winter/Sommer)
  - [ ] Wochentag-basierte Reduktion
  - [ ] Extremwert-fokussierte Auswahl
  - [ ] Clustering-basierte Typtag-Erstellung

- [ ] **TODO-5**: Performance-Optimierungen
  - [ ] Speicher-effiziente Zeitreihen-Verarbeitung
  - [ ] Parallel-Processing für große Zeitreihen
  - [ ] Caching von Zwischenergebnissen

- [ ] **TODO-6**: Erweiterte Validierung
  - [ ] Automatische Plausibilitätsprüfung
  - [ ] Energie-Bilanz-Validierung
  - [ ] Conversion-Faktoren Konsistenz-Check

---

## 🔧 Technische Implementierungs-Details

### **Excel Reader Erweiterungen**

#### **Interaktive Timestep-Integration:**
```python
class ExcelReader:
    def __init__(self, settings):
        self.interactive_mode = settings.get('interactive_timestep', True)
        # ... existing code
    
    def process_excel_data(self, excel_file):
        # ... existing processing
        
        if self.interactive_mode:
            # Frage Benutzer nach Timestep-Reduktion
            strategy, params = self.ask_timestep_reduction(
                len(processed_data['timeseries']),
                self.estimate_solve_time(processed_data)
            )
            
            if strategy != "none":
                processed_data = self.apply_timestep_strategy(
                    processed_data, strategy, params
                )
        
        return processed_data
```

#### **Zeitvariable Conversion-Faktoren:**
```python
def _parse_conversion_factors_enhanced(self, factor_string, expected_count, timeseries_data):
    """
    Erweiterte Conversion-Faktoren mit Timeseries-Referenz
    """
    if self.factor_separator in factor_string:
        factors = [f.strip() for f in factor_string.split(self.factor_separator)]
    else:
        factors = [factor_string.strip()]
    
    # Parse jeden Faktor
    parsed_factors = []
    for factor in factors:
        try:
            # Versuche als Zahl
            parsed_factors.append(float(factor))
        except ValueError:
            # Als Timeseries-Referenz
            if factor in timeseries_data.columns:
                parsed_factors.append(timeseries_data[factor].values)
            else:
                raise ValueError(f"Timeseries-Profil '{factor}' nicht gefunden")
    
    return parsed_factors
```

### **System Builder Erweiterungen**

#### **EBS-Kraftwerk Integration:**
```python
def _build_multi_transformers(self, excel_data):
    # ... existing code
    
    # Spezielle Behandlung für EBS-Kraftwerke
    if self._is_ebs_plant(transformer_data):
        converter = self._create_ebs_converter(transformer_data, timeseries_data)
    else:
        converter = self._create_standard_converter(transformer_data, timeseries_data)
```

#### **Zeitvariable Conversion-Faktoren:**
```python
def _create_conversion_factors_enhanced(self, transformer_data, output_buses, timeseries_data):
    """
    Erweiterte Conversion-Faktoren mit Zeitvariabilität
    """
    conversion_factors = {}
    
    factors_str = transformer_data.get('output_conversion_factors', '1.0')
    factors = self._parse_conversion_factors_enhanced(factors_str, len(output_buses), timeseries_data)
    
    for i, (bus_obj, factor) in enumerate(zip(output_buses, factors)):
        if isinstance(factor, np.ndarray):
            # Zeitvariable Faktoren - spezielle Behandlung
            conversion_factors[bus_obj] = factor
        else:
            # Konstante Faktoren
            conversion_factors[bus_obj] = factor
    
    return conversion_factors
```

---

## 🎯 Implementierungsreihenfolge

### **Empfohlene Reihenfolge:**

1. **Phase 1.1-1.2**: Interaktive Timestep-Anpassung (sofortiger Nutzen)
2. **Phase 1.3-1.4**: Settings Sheet Erweiterung (Grundlage für weitere Features)
3. **Phase 3.1-3.2**: EBS-Kraftwerk Integration (neues Feature)
4. **Phase 4.1**: EBS-Beispiel erstellen (Validierung)
5. **Phase 2.1-2.2**: Zeitvariable Conversion-Faktoren (erweiterte Funktionalität)
6. **Phase 4.2-4.3**: Weitere Beispiele und Templates
7. **Phase 5**: Comprehensive Testing

### **Kritische Erfolgsfaktoren:**
- Backward-Kompatibilität während gesamter Implementierung
- Schrittweise Tests nach jeder Phase
- Benutzer-Feedback für interaktive Features
- Dokumentation parallel zur Implementierung

---

## 📚 Referenz-Informationen

### **Aktuelle Dateistruktur:**
```
project/
├── modules/
│   ├── excel_reader.py (Fixed Version)
│   ├── system_builder.py (Multi-IO Version)
│   └── energy_system_exporter.py
├── examples/
│   ├── bhkw_system.xlsx
│   ├── heatpump_system.xlsx
│   ├── complex_multi_io.xlsx
│   └── district_heating_co2.xlsx
├── create_multi_io_examples.py
├── main.py
└── runme.py
```

### **Wichtige Abhängigkeiten:**
- oemof.solph >= 0.6.0
- pandas >= 1.5.0
- numpy >= 1.20.0
- openpyxl >= 3.0.0

### **Bekannte Kompatibilitätsprobleme:**
- 24n+1 Algorithmus: Aktuell nicht korrekt implementiert
- Zeitvariable Conversion-Faktoren: Noch nicht unterstützt
- EBS-Kraftwerk Investment: Erfordert spezielle Logik

---

**Status:** Bereit für Phase 1 Implementierung  
**Nächster Schritt:** Interaktive Timestep-Anpassung implementieren  
**Estimated Time:** 2-3 Stunden für Phase 1.1-1.2