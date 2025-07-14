# Fremof-Framework Entwicklungsprotokoll

## Projektübersicht
- **Haupt-Repository:** https://github.com/seehausf/fremof-1.0
- **Entwicklungsumgebung:** Anaconda/Spyder
- **Ziel:** Kompletter Workflow zwischen lokaler Entwicklung und GitHub

## Setup-Status
✅ **Spyder-Projekt erstellt**
- Pfad: `C:\Users\seehausf\OneDrive - BHI Consulting AG\Dokumente\GitHub\fremof-1.0`
- .spyproject Datei erstellt

✅ **Git-Workflow definiert**
- Entwicklung in Spyder
- Git-Befehle über Anaconda Prompt
- Kein Git-Plugin in Spyder erforderlich

## Workflow
1. **Code entwickeln** in Spyder
2. **Testen** in Spyder
3. **Versionskontrolle** im Anaconda Prompt:
   ```bash
   cd "C:\Users\seehausf\OneDrive - BHI Consulting AG\Dokumente\GitHub\fremof-1.0"
   git add .
   git commit -m "Beschreibung"
   git push origin main
   ```

## Pflichtenheft für Fremof-Framework

### 1. Projektziele
- [ ] **Hauptziel:** Excel-basierter Modell-Generator für Energiesysteme (basierend auf oemof-solph)
- [ ] **Zielgruppe:** Energiesystemanalytiker ohne Programmierkenntnisse
- [ ] **Ansatz:** Maximale Flexibilität durch User-Input über Excel-Sheets
- [ ] **Basis:** oemof-solph Excel-Reader Beispiel als Ausgangspunkt

### 2. Funktionale Anforderungen

## Detaillierte Excel-Interface Spezifikation

### Excel-Arbeitsblätter
1. **buses** - Energieknoten Definition
2. **sources** - Energiequellen  
3. **sinks** - Energieverbraucher
4. **converters** - Energiewandler
5. **timeseries** - Zeitreihen für variable Parameter

### Source-Arbeitsblatt
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| label | str | Eindeutige Bezeichnung |
| include | int | 1/0 - Komponente aktiv |
| investment | int | 1/0 - Investment-Optimierung |
| nonconvex_investment | int | 1/0 - Binäre Investment-Variable |
| existing | float | Bestehende Kapazität (falls investment=0) |
| outputs | str | Bus-Labels (Semikolon-getrennt) |
| output_relation | str/float | Verhältnisse (Semikolon-getrennt, dt. Komma) oder timeseries_keyword |
| invest_cost | float | Investitionskosten (nur bei investment=1) |
| lifetime | int | Lebensdauer Jahre (nur bei investment=1) |
| interest_rate | float | Zinssatz (nur bei investment=1) |
| min_invest | float | Min. Investment (optional) |
| max_invest | float | Max. Investment (optional) |

### Sink-Arbeitsblatt  
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| label | str | Eindeutige Bezeichnung |
| include | int | 1/0 - Komponente aktiv |
| investment | int | 1/0 - Investment-Optimierung |
| nonconvex_investment | int | 1/0 - Binäre Investment-Variable |
| existing | float | Bestehende Kapazität (falls investment=0) |
| inputs | str | Bus-Labels (Semikolon-getrennt) |
| input_relation | str/float | Verhältnisse (Semikolon-getrennt, dt. Komma) oder timeseries_keyword |
| invest_cost | float | Investitionskosten (nur bei investment=1) |
| lifetime | int | Lebensdauer Jahre (nur bei investment=1) |  
| interest_rate | float | Zinssatz (nur bei investment=1) |
| min_invest | float | Min. Investment (optional) |
| max_invest | float | Max. Investment (optional) |

### Converter-Arbeitsblatt
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| label | str | Eindeutige Bezeichnung |
| include | int | 1/0 - Komponente aktiv |
| investment | int | 1/0 - Investment-Optimierung |  
| nonconvex_investment | int | 1/0 - Binäre Investment-Variable |
| existing | float | Bestehende Kapazität (falls investment=0) |
| inputs | str | Bus-Labels (Semikolon-getrennt) |
| outputs | str | Bus-Labels (Semikolon-getrennt) |
| input_relation | str/float | Verhältnisse (Semikolon-getrennt, dt. Komma) oder timeseries_keyword |
| output_relation | str/float | Verhältnisse (Semikolon-getrennt, dt. Komma) oder timeseries_keyword |
| invest_cost | float | Investitionskosten (nur bei investment=1) |
| lifetime | int | Lebensdauer Jahre (nur bei investment=1) |
| interest_rate | float | Zinssatz (nur bei investment=1) |
| min_invest | float | Min. Investment (optional) |
| max_invest | float | Max. Investment (optional) |

### Wichtige Konventionen
- **nominal_capacity Referenz:**
  - Sources: Bezieht sich auf ersten Output-Flow
  - Sinks: Bezieht sich auf ersten Input-Flow  
  - Converter: Bezieht sich auf ersten Output-Flow
- **Investment-Modus:** `nominal_capacity = solph.Investment(**invest_args)`
- **Existing-Modus:** `nominal_capacity = existing`
- **EP-Costs Berechnung:** Automatische Annuitäts-Berechnung aus invest_cost, lifetime, interest_rate
- **Timeseries-Integration:** output_relation/input_relation kann timeseries_keyword referenzieren

#### 2.2 Modell-Generator
- [ ] **Excel-Parser:** Robustes Einlesen aller Arbeitsblätter
- [ ] **Automatische Validierung:** Konsistenzprüfung der Eingabedaten
- [ ] **Flexible Komponenten-Erstellung:** Dynamische oemof-solph Objekt-Generierung
- [ ] **Error-Handling:** Verständliche Fehlermeldungen bei ungültigen Eingaben

#### 2.3 Optimierung & Ergebnisse
- [ ] **Solver-Integration:** CBC, GLPK, Gurobi, CPLEX Support
- [ ] **Ergebnis-Export:** Automatische Excel-Ausgabe der Optimierungsergebnisse
- [ ] **Visualisierung:** Grundlegende Plots und Grafiken
- [ ] **Reporting:** Standardisierte Ergebnisberichte

### 3. Technische Architektur

#### 3.1 Core-Module
- [ ] **ExcelReader:** Erweiterte Version des oemof-Beispiels
- [ ] **ModelBuilder:** Dynamische Energiesystem-Erstellung
- [ ] **ComponentFactory:** Flexible Komponenten-Generator
- [ ] **ResultsProcessor:** Ergebnis-Aufbereitung und Export

#### 3.2 Flexibilitäts-Features
- [ ] **Custom Properties:** Beliebige zusätzliche Parameter pro Komponente
- [ ] **Conditional Logic:** If-Then Regeln in Excel definierbar
- [ ] **Multi-Scenario:** Mehrere Szenarien in einer Excel-Datei
- [ ] **Parameter-Sets:** Wiederverwendbare Parametersätze

### 4. Entwicklungsplan

#### Phase 1: Excel-Interface (Priorität 1)
- [ ] Analyse des oemof Excel-Reader Beispiels
- [ ] Erweiterung um alle oemof-solph Komponenten
- [ ] Robuster Excel-Parser mit Validierung
- [ ] Erste funktionsfähige Version

#### Phase 2: Model-Generator (Priorität 2)  
- [ ] Dynamische Modell-Erstellung
- [ ] Flexible Parametrierung
- [ ] Error-Handling und Debugging

#### Phase 3: Ergebnis-Management (Priorität 3)
- [ ] Excel-Export der Ergebnisse
- [ ] Basis-Visualisierung
- [ ] Reporting-Templates

## Repositories
### Haupt-Repository (fremof-1.0)
- **URL:** https://github.com/seehausf/fremof-1.0
- **Zweck:** Entwicklung des neuen Fremof-Frameworks
- **Status:** Setup abgeschlossen

### Source-Code Repository (oemof-solph)
- **URL:** https://github.com/oemof/oemof-solph
- **Zweck:** Basis-Framework für Energiesystemmodellierung
- **Status:** Analysiert
- **Beschreibung:** Open-source Framework für Energiesystemmodellierung und -optimierung (LP/MILP)
  - Graph-basierte Modellierung von Energiesystemen
  - Pyomo-basierte Optimierung mit verschiedenen Solvern (CBC, GLPK, Gurobi, CPLEX)
  - Komponenten: Bus, Source, Sink, Converter, Storage, Transformer
  - Investment- und Dispatch-Optimierung
  - Multi-Period Unterstützung

## Sitzungsnotizen
### Sitzung 1 (14. Juli 2025)
- Projekt-Setup in Spyder abgeschlossen
- Git-Workflow etabliert
- oemof-solph Repository analysiert - Framework für Energiesystemmodellierung
- Excel-Reader Beispiel studiert - perfekte Basis für Fremof
- Fokus definiert: Excel-basierter Modell-Generator (keine GUI erstmal)
- Detaillierte Excel-Interface Spezifikation erstellt
- **Erster Prototyp implementiert:** FremofExcelReader Klasse mit allen Features
- **Excel-Template Struktur definiert:** Vollständige Arbeitsblatt-Spezifikation
- Investment-Optimierung mit automatischer EP-Cost Berechnung implementiert

---
*Letzte Aktualisierung: 14. Juli 2025*