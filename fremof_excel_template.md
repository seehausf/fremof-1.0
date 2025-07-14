# Fremof Excel Template - Arbeitsblatt-Struktur

## 1. Arbeitsblatt: "buses"
Definiert alle Energieknoten im System

| label | include |
|-------|---------|
| bus_el | 1 |
| bus_heat | 1 |
| bus_gas | 1 |

## 2. Arbeitsblatt: "sources"
Definiert alle Energiequellen

| label | include | investment | nonconvex_investment | existing | outputs | output_relation | invest_cost | lifetime | interest_rate | min_invest | max_invest |
|-------|---------|------------|---------------------|----------|---------|----------------|-------------|----------|---------------|------------|------------|
| grid_import | 1 | 0 | 0 | 1000 | bus_el | 1,0 | | | | | |
| gas_import | 1 | 0 | 0 | 500 | bus_gas | 1,0 | | | | | |
| pv_plant | 1 | 1 | 0 | 0 | bus_el | pv_profile | 1200 | 20 | 0,05 | 0 | 100 |
| wind_plant | 1 | 1 | 1 | 0 | bus_el | wind_profile | 1500 | 25 | 0,05 | 5 | 50 |

**Erklärungen:**
- `grid_import`: Netzbezug ohne Investment, bestehende Kapazität 1000 kW
- `gas_import`: Gasimport ohne Investment, bestehende Kapazität 500 kW  
- `pv_plant`: PV-Anlage mit kontinuierlichem Investment, Profil aus Zeitreihen
- `wind_plant`: Windanlage mit binärem Investment (nonconvex), Min. 5 MW, Max. 50 MW

## 3. Arbeitsblatt: "sinks"
Definiert alle Energieverbraucher

| label | include | investment | nonconvex_investment | existing | inputs | input_relation | invest_cost | lifetime | interest_rate | min_invest | max_invest |
|-------|---------|------------|---------------------|----------|--------|---------------|-------------|----------|---------------|------------|------------|
| el_demand | 1 | 0 | 0 | 1000 | bus_el | el_load_profile | | | | | |
| heat_demand | 1 | 0 | 0 | 800 | bus_heat | heat_load_profile | | | | | |
| grid_export | 1 | 0 | 0 | 1000 | bus_el | 1,0 | | | | | |

**Erklärungen:**
- `el_demand`: Elektrische Last mit Zeitreihenprofil
- `heat_demand`: Wärmelast mit Zeitreihenprofil
- `grid_export`: Netzeinspeisung (konstant möglich)

## 4. Arbeitsblatt: "converters"
Definiert alle Energiewandler

| label | include | investment | nonconvex_investment | existing | inputs | outputs | input_relation | output_relation | invest_cost | lifetime | interest_rate | min_invest | max_invest |
|-------|---------|------------|---------------------|----------|--------|---------|---------------|----------------|-------------|----------|---------------|------------|------------|
| gas_boiler | 1 | 1 | 0 | 0 | bus_gas | bus_heat | 1,0 | 0,9 | 800 | 15 | 0,05 | 0 | 200 |
| chp_plant | 1 | 1 | 1 | 0 | bus_gas | bus_el;bus_heat | 1,0 | 0,35;0,5 | 2500 | 20 | 0,05 | 10 | 100 |
| heat_pump | 1 | 1 | 0 | 0 | bus_el | bus_heat | 1,0 | cop_profile | 1200 | 18 | 0,05 | 0 | 50 |

**Erklärungen:**
- `gas_boiler`: Gaskessel mit kontinuierlichem Investment, 90% Wirkungsgrad
- `chp_plant`: KWK-Anlage mit binärem Investment, elektrischer WG 35%, thermischer WG 50%
- `heat_pump`: Wärmepumpe mit zeitvariablem COP aus Zeitreihen

## 5. Arbeitsblatt: "timeseries"
Enthält alle Zeitreihen-Daten

| timestamp | pv_profile | wind_profile | el_load_profile | heat_load_profile | cop_profile |
|-----------|------------|--------------|-----------------|-------------------|-------------|
| 2024-01-01 00:00:00 | 0,0 | 0,3 | 0,6 | 0,8 | 3,2 |
| 2024-01-01 01:00:00 | 0,0 | 0,4 | 0,5 | 0,7 | 3,1 |
| 2024-01-01 02:00:00 | 0,0 | 0,2 | 0,4 | 0,6 | 3,0 |
| ... | ... | ... | ... | ... | ... |
| 2024-01-01 12:00:00 | 0,8 | 0,1 | 0,9 | 0,3 | 2,8 |

**Wichtige Hinweise:**
- Alle Werte in deutscher Schreibweise (Komma als Dezimaltrennzeichen)
- Mehrere Busse/Relationen mit Semikolon getrennt (z.B. "bus_el;bus_heat")
- Zeitreihen-Keywords werden automatisch erkannt und verknüpft
- Investment-Parameter nur ausfüllen wenn investment=1

## Validierungsregeln

### Sources
- `outputs` muss mindestens einen gültigen Bus enthalten
- Bei `investment=1` müssen `invest_cost`, `lifetime`, `interest_rate` ausgefüllt sein
- `output_relation` muss gleiche Anzahl Werte wie `outputs` haben
- `nonconvex_investment=1` erfordert `min_invest > 0`

### Sinks  
- `inputs` muss mindestens einen gültigen Bus enthalten
- Bei `investment=1` müssen `invest_cost`, `lifetime`, `interest_rate` ausgefüllt sein
- `input_relation` muss gleiche Anzahl Werte wie `inputs` haben

### Converters
- `inputs` und `outputs` müssen mindestens je einen gültigen Bus enthalten
- Bei `investment=1` müssen `invest_cost`, `lifetime`, `interest_rate` ausgefüllt sein
- `input_relation` und `output_relation` müssen passende Anzahl Werte haben
- Erster Output-Flow trägt immer die `nominal_capacity`

## Automatische Berechnungen

### EP-Costs (Annuität)
```
ep_costs = invest_cost * (q^n * p) / (q^n - 1)
wobei:
- q = 1 + interest_rate  
- n = lifetime
- p = interest_rate
```

### Timeseries-Integration
- Keywords in `*_relation` Spalten verweisen auf `timeseries` Arbeitsblatt
- Automatische Verknüpfung über Spaltennamen
- Deutsche Zahlenformatierung wird automatisch konvertiert

## Beispiel-Szenarien

### Szenario 1: Einfaches Energiesystem
- 1 Bus (Strom)
- 1 Source (Netz)  
- 1 Sink (Last)
- Keine Investments

### Szenario 2: PV + Speicher (zukünftig)
- 2 Busse (Strom, Batterie)
- 2 Sources (Netz, PV)
- 2 Sinks (Last, Export)
- 1 Storage (Batterie)
- Investments in PV und Speicher

### Szenario 3: Multi-Energiesystem  
- 3 Busse (Strom, Wärme, Gas)
- 3 Sources (Netz, Gas, PV)
- 3 Sinks (el. Last, Wärmelast, Export)
- 3 Converter (Gaskessel, KWK, Wärmepumpe)
- Komplexe Investment-Optimierung