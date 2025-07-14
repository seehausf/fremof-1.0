#!/usr/bin/env python3
"""
runner.py - Modellausführung und Optimierung

FIXED VERSION: Investment-Export repariert für oemof-solph v0.6.0
Problem behoben: 'Series' object has no attribute 'columns'
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from oemof import solph

logger = logging.getLogger(__name__)

class ModelRunner:
    """Führt oemof-solph Optimierung durch"""
    
    def __init__(self, model: solph.Model, solver: str = 'cbc'):
        """
        Initialisiert den ModelRunner
        
        Args:
            model: oemof-solph Model
            solver: Solver-Name ('cbc', 'glpk', 'gurobi', etc.)
        """
        self.model = model
        self.solver = solver
        self.results = None
        self.meta_results = None
        
    def solve(self, **solver_kwargs) -> Dict[str, Any]:
        """
        Löst das Optimierungsmodell
        
        Args:
            **solver_kwargs: Zusätzliche Solver-Parameter
            
        Returns:
            Dictionary mit Optimierungsergebnissen
        """
        logger.info(f"Starte Optimierung mit Solver: {self.solver}")
        
        try:
            # Standard Solver-Optionen
            default_kwargs = {
                'tee': True,  # Solver-Output anzeigen
                'solve_kwargs': {'tee': True}
            }
            
            # Benutzer-Parameter überschreiben Standard
            solve_options = {**default_kwargs, **solver_kwargs}
            
            # Modell-Statistiken vor Optimierung
            self._log_model_stats()
            
            # Optimierung durchführen
            logger.info("Führe Optimierung durch...")
            self.model.solve(solver=self.solver, **solve_options)
            
            # Ergebnisse verarbeiten
            logger.info("Verarbeite Optimierungsergebnisse...")
            self.results = solph.processing.results(self.model)
            self.meta_results = solph.processing.meta_results(self.model)
            
            # Optimierungsstatus prüfen
            self._check_solver_status()
            
            # Ergebnis-Statistiken
            self._log_results_stats()
            
            logger.info("Optimierung erfolgreich abgeschlossen")
            
            return {
                'results': self.results,
                'meta_results': self.meta_results,
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Optimierung: {e}")
            raise
    
    def _log_model_stats(self):
        """Protokolliert Modell-Statistiken vor Optimierung"""
        
        try:
            # Anzahl Variablen und Constraints
            num_vars = self.model.nvariables()
            num_constraints = self.model.nconstraints()
            
            logger.info(f"Modell-Statistiken:")
            logger.info(f"  Variablen: {num_vars}")
            logger.info(f"  Constraints: {num_constraints}")
            
            # Zeitindex-Info
            if hasattr(self.model, 'es') and hasattr(self.model.es, 'timeindex'):
                timeindex = self.model.es.timeindex
                logger.info(f"  Zeitschritte: {len(timeindex)}")
                logger.info(f"  Zeitbereich: {timeindex[0]} bis {timeindex[-1]}")
                
        except Exception as e:
            logger.warning(f"Konnte Modell-Statistiken nicht ermitteln: {e}")
    
    def _check_solver_status(self):
        """Prüft den Solver-Status und gibt entsprechende Meldungen aus"""
        
        try:
            # Solver-Status aus Meta-Results
            if self.meta_results and 'solver' in self.meta_results:
                solver_info = self.meta_results['solver']
                
                # Status prüfen
                status = solver_info.get('Status', 'unknown')
                termination_condition = solver_info.get('Termination condition', 'unknown')
                
                logger.info(f"Solver-Status: {status}")
                logger.info(f"Termination Condition: {termination_condition}")
                
                # Warnings für problematische Status
                if status.lower() not in ['ok', 'optimal']:
                    logger.warning(f"Solver-Status ist nicht optimal: {status}")
                
                if 'optimal' not in termination_condition.lower():
                    logger.warning(f"Keine optimale Lösung gefunden: {termination_condition}")
                
                # Lösungszeit
                if 'Time' in solver_info:
                    solve_time = solver_info['Time']
                    logger.info(f"Lösungszeit: {solve_time:.2f} Sekunden")
                
                # Objektiv-Wert
                if 'Lower bound' in solver_info:
                    obj_value = solver_info['Lower bound']
                    logger.info(f"Objektiv-Wert: {obj_value:.2f}")
                    
            else:
                logger.warning("Keine Solver-Informationen in Meta-Results gefunden")
                
        except Exception as e:
            logger.warning(f"Konnte Solver-Status nicht prüfen: {e}")
    
    def _log_results_stats(self):
        """Protokolliert Ergebnis-Statistiken (FIXED)"""
        
        try:
            if not self.results:
                logger.warning("Keine Ergebnisse zum Analysieren vorhanden")
                return
            
            # Anzahl Flows mit Ergebnissen
            num_flows = len(self.results)
            logger.info(f"Ergebnis-Statistiken:")
            logger.info(f"  Flows mit Ergebnissen: {num_flows}")
            
            # FIXED: Flows mit Investment-Ergebnissen zählen
            investment_flows = 0
            for flow_key, flow_data in self.results.items():
                if 'scalars' in flow_data:
                    scalars = flow_data['scalars']
                    
                    # FIX: Sichere Behandlung von Series vs DataFrame
                    if isinstance(scalars, pd.Series):
                        scalar_columns = scalars.index
                    elif isinstance(scalars, pd.DataFrame):
                        scalar_columns = scalars.columns
                    else:
                        continue
                    
                    if any('invest' in str(col).lower() for col in scalar_columns):
                        investment_flows += 1
            
            if investment_flows > 0:
                logger.info(f"  Flows mit Investment: {investment_flows}")
            
        except Exception as e:
            logger.warning(f"Konnte Ergebnis-Statistiken nicht ermitteln: {e}")
    
    def get_investment_results(self) -> Dict[str, float]:
        """
        FIXED: Extrahiert Investment-Ergebnisse
        Kompatibel mit oemof-solph v0.6.0 Results-Struktur
        
        Returns:
            Dictionary mit Investment-Kapazitäten pro Komponente
        """
        investments = {}
        
        if not self.results:
            return investments
        
        try:
            for flow_key, flow_data in self.results.items():
                if 'scalars' in flow_data:
                    scalars = flow_data['scalars']
                    
                    # FIX: Sichere Behandlung von Series vs DataFrame
                    if isinstance(scalars, pd.Series):
                        # Series zu DataFrame konvertieren für einheitliche Behandlung
                        scalars_df = scalars.to_frame().T
                        scalar_columns = scalars_df.columns
                        scalar_data = scalars_df
                    elif isinstance(scalars, pd.DataFrame):
                        scalar_columns = scalars.columns
                        scalar_data = scalars
                    else:
                        logger.warning(f"Unbekannter scalars Typ für {flow_key}: {type(scalars)}")
                        continue
                    
                    # Suche nach Investment-Spalten
                    invest_cols = [col for col in scalar_columns if 'invest' in str(col).lower()]
                    
                    for col in invest_cols:
                        if not scalar_data[col].empty and scalar_data[col].iloc[0] > 0:
                            # Flow-Key formatieren für bessere Lesbarkeit
                            component_name = f"{flow_key[0]}→{flow_key[1]}" if len(flow_key) == 2 else str(flow_key)
                            investments[component_name] = float(scalar_data[col].iloc[0])
            
            if investments:
                logger.info(f"Investment-Ergebnisse gefunden: {len(investments)} Komponenten")
                for comp, capacity in investments.items():
                    logger.info(f"  {comp}: {capacity:.2f} kW")
            
        except Exception as e:
            logger.warning(f"Konnte Investment-Ergebnisse nicht extrahieren: {e}")
            logger.debug("Results-Struktur Debug:", exc_info=True)
        
        return investments
    
    def get_total_costs(self) -> Optional[float]:
        """
        Berechnet die Gesamtkosten des Systems
        
        Returns:
            Gesamtkosten oder None falls nicht verfügbar
        """
        try:
            if self.meta_results and 'objective' in self.meta_results:
                total_costs = self.meta_results['objective']
                logger.info(f"Gesamtkosten: {total_costs:.2f} €")
                return total_costs
        except Exception as e:
            logger.warning(f"Konnte Gesamtkosten nicht ermitteln: {e}")
        
        return None
    
    def check_solver_availability(self, solver_name: str = None) -> bool:
        """
        Prüft ob ein Solver verfügbar ist
        
        Args:
            solver_name: Name des Solvers (default: self.solver)
            
        Returns:
            True wenn Solver verfügbar, False sonst
        """
        if solver_name is None:
            solver_name = self.solver
        
        try:
            # Dummy-Modell für Solver-Test
            from pyomo.environ import ConcreteModel, Var, Objective, SolverFactory
            
            test_model = ConcreteModel()
            test_model.x = Var()
            test_model.obj = Objective(expr=test_model.x)
            
            # Solver testen
            solver = SolverFactory(solver_name)
            
            if not solver.available():
                logger.error(f"Solver '{solver_name}' ist nicht verfügbar")
                return False
            
            logger.info(f"Solver '{solver_name}' ist verfügbar")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Solver-Test für '{solver_name}': {e}")
            return False
    
    def debug_results_structure(self):
        """
        DEBUG: Analysiert Results-Struktur für Debugging
        """
        if not self.results:
            print("Keine Results vorhanden")
            return
        
        print("\n=== RESULTS STRUCTURE DEBUG ===")
        
        for flow_key, flow_data in self.results.items():
            print(f"\nFlow: {flow_key}")
            print(f"Type: {type(flow_data)}")
            
            if isinstance(flow_data, dict):
                for key, value in flow_data.items():
                    print(f"  {key}: {type(value)}")
                    
                    if key == 'scalars':
                        print(f"    scalars type: {type(value)}")
                        if isinstance(value, pd.DataFrame) and hasattr(value, 'columns'):
                            print(f"    DataFrame columns: {list(value.columns)}")
                        elif isinstance(value, pd.Series) and hasattr(value, 'index'):
                            print(f"    Series index: {list(value.index)}")
                    
                    if key == 'sequences' and hasattr(value, 'columns'):
                        print(f"    sequences columns: {list(value.columns)}")
        
        print("=== END DEBUG ===\n")