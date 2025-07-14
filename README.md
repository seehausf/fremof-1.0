# oemof-solph Energiesystemmodellierung

Dieses Projekt verwendet oemof-solph für die Modellierung und Optimierung von Energiesystemen.

## 🚀 Quick Start

### 1. Setup (einmalig)
```bash
python first_run_setup.py
```

### 2. Dependencies installieren
```bash
pip install -r requirements.txt
conda install -c conda-forge coincbc  # CBC Solver
```

### 3. Installation testen
```bash
oemof_installation_test
```

### 4. Beispiel ausführen
```bash
python main.py
```

## 📁 Projektstruktur

```
project_root/
├── main.py                    # Hauptprogramm
├── first_run_setup.py         # Setup-Script
├── requirements.txt           # Dependencies
├── README.md                  # Diese Datei
│
├── input/                     # Excel-Eingabedateien
│   └── examples/
│       ├── household_pv.xlsx  # PV-Haushalt Beispiel
│       └── district_heat.xlsx # Fernwärme mit CHP
│
├── output/                    # Temporäre Ausgaben
├── results/                   # Endergebnisse (Excel + Visualisierungen)
├── logs/                      # Log-Dateien
│
└── src/                       # Python Module
    ├── importer.py            # Datenimport aus Excel
    ├── runner.py              # Optimierung
    ├── exporter.py            # Ergebnisexport
    ├── visualizer.py          # Visualisierung (oemof-visio)
    │
    ├── core/                  # Gemeinsame Funktionen
    │   ├── __init__.py
    │   └── utilities.py
    │
    └── builder/               # Modellaufbau (modular)
        ├── __init__.py
        ├── base_builder.py
        ├── bus_builder.py
        ├── component_builder.py
        └── investment_builder.py
```

## 📊 Beispiele

### PV-Haushalt (household_pv.xlsx)
- Haushaltsstromverbrauch mit PV-Anlage
- Netzbezug und Einspeisung
- Investment-Optimierung für PV-Kapazität
- 7 Tage Sommer-Szenario

### Fernwärme (district_heat.xlsx)
- Gas-CHP-Anlage (Kraft-Wärme-Kopplung)
- Power-to-Heat Spitzenlastkessel
- Multi-Input/Output Converter-Komponenten
- 7 Tage Winter-Szenario

## 🆕 Phase 2.1 Features

### Erweiterte Flow-Parameter
- `full_load_time_max`: Maximale Volllaststunden
- `full_load_time_min`: Minimale Volllaststunden
- `investment_min`: Minimale Investment-Kapazität

### Neue Converter-Komponenten
- Multi-Input/Output Flows
- Conversion-Faktoren für Ein- und Ausgänge
- CHP-Anlagen, Power-to-Heat, etc.

### Visualisierung
- oemof-visio Integration
- Energy System Graphs
- Sankey Diagramme
- Bus-Plots für Zeitreihen

## 🔧 Excel-Struktur

Jedes Excel-Beispiel enthält umfassende Spaltendokumentation:

### Sheets
- **timeseries**: Zeitreihen-Daten (Keywords für andere Sheets)
- **buses**: Energieträger-Knoten
- **sources**: Energiequellen (Kraftwerke, Imports)
- **sinks**: Energiesenken (Lasten, Exports)
- **converters**: Energiewandler (CHP, P2H) - NEU
- **storages**: Energiespeicher (Batterien, Wärme)

### Dokumentation
Oberhalb jeder Datentabelle finden Sie:
- Sheet-Beschreibung
- Spalten-Definition mit Datentypen
- Anwendungsbeispiele

## 🎯 Workflow

1. **Excel-Datei erstellen/bearbeiten** in `input/`
2. **Hauptprogramm starten**: `python main.py`
3. **Projekt auswählen** aus verfügbaren Excel-Dateien
4. **Optimierung läuft** automatisch
5. **Ergebnisse finden** in `results/`:
   - Flow-Ergebnisse (Zeitreihen)
   - Investment-Ergebnisse
   - Zusammenfassung
   - Visualisierungen

## 📈 Ergebnisse

### Excel-Export
- `*_flow_results.xlsx`: Detaillierte Zeitreihen
- `*_investment_results.xlsx`: Investment-Kapazitäten
- `*_summary.xlsx`: Zusammenfassung und Kosten

### Visualisierungen
- `*_graph.pdf`: Energiesystem-Netzwerk
- `*_sankey.html`: Energie-Flüsse interaktiv
- `*_bus_*.png`: Bus-Plots für Zeitreihen

## 🔗 Links

- [oemof.solph Dokumentation](https://oemof-solph.readthedocs.io/)
- [oemof Community](https://github.com/oemof/oemof-solph)
- [Solver Installation](https://oemof-solph.readthedocs.io/en/latest/getting_started.html#solver)

## 🆘 Troubleshooting

### Solver-Probleme
```bash
# CBC installieren
conda install -c conda-forge coincbc

# Installation testen
oemof_installation_test
```

### Visualisierung
```bash
# oemof-visio installieren
pip install git+https://github.com/oemof/oemof_visio.git[network]

# Windows: Graphviz zusätzlich installieren
# https://graphviz.org/download/
```

### Import-Fehler
- Prüfen Sie Excel-Dateien auf korrekte Spalten-Namen
- `include` Spalte: True/False für Aktivierung
- Bus-Referenzen müssen in `buses` Sheet definiert sein
