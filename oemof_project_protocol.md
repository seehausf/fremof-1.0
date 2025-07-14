# oemof.solph 0.6.0 Entwicklungsprojekt - Protokoll

## Projektübersicht
**Datum:** 14. Juli 2025  
**Version:** oemof.solph 0.6.0  
**Status:** Planungsphase  
**Ziel:** Entwicklung eines neuen Energiesystemmodellierungsprogramms

---

## Wichtige Änderungen in oemof.solph 0.6.0

### API-Änderungen und neue Syntax

#### 1. **Komponentenstruktur (Refactored)**
- Clean definition of time indexes: You need N+1 points in time do define N time spans. Parts of the energy system graph are now clearly structured into buses, components, and flows
- Experimental code is now sitting in sub-modules called experimental (replaces "custom")

#### 2. **Investment API Vereinheitlichung**
- Unify API for constant sized objects and sizing of investment. For both, Flow and GenericStorage, the argument investment is now deprecated. Instead, nominal_capacity and nominal_storage_capacity accept an Investment object
- Neue Investment-Parameter: `nominal_capacity` statt `investment` Argument

#### 3. **Transformer zu Converter Umbenennung**
- The component Transformer is now named Converter
- Alle `Transformer` Klassen sind jetzt `Converter` Klassen

#### 4. **Flow Parameter Änderungen**
- The flow arguments summed_min and summed_max now have the more descriptive names full_load_time_min and full_load_time_max

#### 5. **Multi-Period Funktionalität (Experimentell)**
- Add option to run multi-period (dynamic) investment models with oemof.solph as an experimental feature
- You can change from standard model to multi-period model by defining the newly introduced periods attribute of your energy system

#### 6. **Neue Results Klasse**
- Add a new Results class

---

## Verfügbare Klassen und Komponenten in 0.6.0

### Basis-Komponenten
1. **Source** - Energiequellen
   - Parameter: `label`, `outputs`, `custom_properties`
   
2. **Sink** - Energiesenken
   - Parameter: `label`, `inputs`, `custom_properties`

3. **Converter** (früher Transformer)
   - Parameter: `label`, `inputs`, `outputs`, `conversion_factors`, `custom_properties`

4. **GenericStorage** - Allgemeiner Speicher
   - Parameter: `nominal_capacity`, `nominal_storage_capacity`, `initial_storage_level`, etc.

### Spezielle Komponenten
5. **ExtractionTurbineCHP** - Entnahme-Turbinen-KWK
   - Parameter: `conversion_factor_full_condensation`, `conversion_factors`

6. **GenericCHP** - Generisches KWK-System
   - Parameter: `fuel_input`, `electrical_output`, `heat_output`, `beta`, `back_pressure`

7. **OffsetConverter** - Konverter mit Offset
   - Parameter: `conversion_factors`, `normed_offsets`, `coefficients`

8. **Link** - Verbindung zwischen zwei Bussen
   - Parameter: `inputs`, `outputs`, `conversion_factors`

### Experimentelle Komponenten
9. **experimental.GenericCAES** - Compressed Air Energy Storage
10. **experimental.PiecewiseLinearConverter** - Stückweise linearer Konverter

### Flow-Klasse
- **Flow** - Energiefluss zwischen Komponenten
  - **Neue Parameter in 0.6.0:**
    - `nominal_capacity` (statt `nominal_value`)
    - `full_load_time_max`/`full_load_time_min` (statt `summed_max`/`summed_min`)
    - `nonconvex` (NonConvex-Objekt)
    - `lifetime`, `age` (für Multi-Period)

### Options-Klassen
11. **Investment** - Investitionsoptionen
    - Parameter: `maximum`, `minimum`, `ep_costs`, `existing`, `nonconvex`, `offset`, `overall_maximum`, `overall_minimum`, `lifetime`, `age`, `fixed_costs`

12. **NonConvex** - Nicht-konvexe Flusseigenschaften
    - Parameter: `initial_status`, `minimum_uptime`, `minimum_downtime`, `maximum_startups`, `maximum_shutdowns`, `startup_costs`, `shutdown_costs`, `activity_costs`

---

## Keyword Arguments - Übersicht

### EnergySystem
```python
solph.EnergySystem(
    timeindex=...,          # pandas.DatetimeIndex
    periods=...,            # Liste für Multi-Period (experimentell)
    infer_last_interval=..., # Boolean
    **kwargs
)
```

### Flow
```python
solph.Flow(
    nominal_capacity=...,            # Nennkapazität (NEU)
    variable_costs=...,              # Variable Kosten
    min=..., max=...,               # Grenzen (relativ)
    fix=...,                        # Fixer Wert
    positive_gradient_limit=...,     # Rampen-Limits
    negative_gradient_limit=...,
    full_load_time_max=...,         # NEU: statt summed_max
    full_load_time_min=...,         # NEU: statt summed_min
    integer=...,                    # Ganzzahl-Variable
    bidirectional=...,              # Bidirektional
    nonconvex=...,                  # NonConvex-Objekt
    lifetime=...,                   # Lebensdauer (Multi-Period)
    age=...,                        # Alter (Multi-Period)
    fixed_costs=...,                # Fixkosten
    custom_attributes=...           # Benutzerdefinierte Attribute
)
```

### Investment
```python
solph.Investment(
    maximum=...,           # Maximale Investition
    minimum=...,           # Minimale Investition
    ep_costs=...,          # Periodische Kosten
    existing=...,          # Bestehende Kapazität
    nonconvex=...,         # Boolean für binäre Investment
    offset=...,            # Fixkosten bei nonconvex=True
    overall_maximum=...,   # Gesamt-Maximum (Multi-Period)
    overall_minimum=...,   # Gesamt-Minimum (Multi-Period)
    lifetime=...,          # Lebensdauer
    age=...,              # Alter
    fixed_costs=...       # Fixkosten (Multi-Period)
)
```

### NonConvex
```python
solph.NonConvex(
    initial_status=...,         # Anfangsstatus
    minimum_uptime=...,         # Mindestlaufzeit
    minimum_downtime=...,       # Mindeststillstandszeit
    maximum_startups=...,       # Max. Anfahrvorgänge
    maximum_shutdowns=...,      # Max. Abschaltvorgänge
    startup_costs=...,          # Anfahrkosten
    shutdown_costs=...,         # Abschaltkosten
    activity_costs=...,         # Aktivitätskosten
    inactivity_costs=...,       # Inaktivitätskosten
    negative_gradient_limit=..., # Rampen-Limits
    positive_gradient_limit=...,
    custom_attributes=...       # Benutzerdefinierte Attribute
)
```

---

## Todos

### Phase 1: Projektplanung ✅
- [x] Recherche zu oemof.solph 0.6.0 Neuerungen
- [x] Dokumentation der API-Änderungen
- [x] Erstellung des Projektprotokolls

### Phase 2: Anforderungsanalyse
- [ ] Definition der zu modellierenden Energiesystemkomponenten
- [ ] Festlegung der Optimierungsziele
- [ ] Spezifikation der Eingangsdaten
- [ ] Definition der gewünschten Ausgaben/Visualisierungen

### Phase 3: Architektur-Design
- [ ] Modulare Programmstruktur definieren
- [ ] Datenstrukturen für Komponenten festlegen
- [ ] Input/Output-Schnittstellen designen
- [ ] Konfigurationssystem entwickeln

### Phase 4: Implementierung
- [ ] Basis-Framework entwickeln
- [ ] Energiesystemkomponenten implementieren
- [ ] Optimierungslogik integrieren
- [ ] Datenverarbeitung implementieren

### Phase 5: Testing & Validierung
- [ ] Unit-Tests für alle Komponenten
- [ ] Integrationstests des Gesamtsystems
- [ ] Validierung mit Referenzsystemen
- [ ] Performance-Tests

### Phase 6: Dokumentation & Finalisierung
- [ ] Code-Dokumentation
- [ ] Benutzerhandbuch
- [ ] Beispiele und Tutorials
- [ ] Deployment-Vorbereitung

---

## Nächste Schritte

1. **Sofort:** Spezifikation der Energiesystemanforderungen
2. **Diese Woche:** Architektur-Design und Modulstruktur
3. **Nächste Woche:** Implementierung des Basis-Frameworks

---

## Notizen

- oemof.solph 0.6.0 ist stabiler als Alpha-Versionen
- Most noticeable change probably is the completely revised and reshaped documentation
- Rückwärtskompatibilität teilweise vorhanden, aber deprecated Warnings
- Multi-Period Funktionalität ist experimentell
- Neue Results-Klasse für bessere Ergebnisverarbeitung

---

## Referenzen

- [oemof.solph GitHub Repository](https://github.com/oemof/oemof-solph)
- [oemof.solph 0.6.0 Dokumentation](https://oemof-solph.readthedocs.io/en/latest/)
- [oemof.solph API Reference](https://oemof-solph.readthedocs.io/en/latest/reference/)