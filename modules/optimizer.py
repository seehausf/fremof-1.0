#!/usr/bin/env python3
"""
oemof.solph 0.6.0 Optimierungs-Modul
===================================

Führt die Optimierung von oemof.solph Energiesystemen durch.
Unterstützt verschiedene Solver und Optimierungsstrategien.

Autor: [Ihr Name]
Datum: Juli 2025
Version: 1.0.0
"""

import time
from typing import Dict, Any, Tuple, Optional
import logging

# oemof.solph 0.6.0 Imports
try:
    import oemof.solph as solph
    from oemof.solph import processing
    import pyomo.environ as pyo
    from pyomo.opt import SolverStatus, TerminationCondition
except ImportError as e:
    print(f"❌ oemof.solph oder pyomo nicht verfügbar: {e}")
    print("Installieren Sie: pip install oemof.solph>=0.6.0 pyomo")
    raise


class Optimizer:
    """Klasse für die Optimierung von oemof.solph Energiesystemen."""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialisiert den Optimizer.
        
        Args:
            settings: Konfigurationsdictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Solver-Konfiguration
        self.solver_name = settings.get('solver', 'cbc')
        self.solver_options = self._get_solver_options()
        
        # Optimierungs-Statistiken
        self.optimization_stats = {}
    
    def _get_solver_options(self) -> Dict[str, Any]:
        """Gibt solver-spezifische Optionen zurück."""
        if self.solver_name.lower() == 'cbc':
            return {
                'tee': self.settings.get('debug_mode', False),
                # CBC-spezifische Optionen (keine mipgap in solve_kwargs)
            }
        elif self.solver_name.lower() == 'glpk':
            return {
                'tee': self.settings.get('debug_mode', False),
                # GLPK-spezifische Optionen
            }
        elif self.solver_name.lower() == 'gurobi':
            return {
                'tee': self.settings.get('debug_mode', False),
                'MIPGap': 0.01,
                'TimeLimit': 3600,
                'Threads': 4,
            }
        else:
            # Allgemeine Optionen
            return {
                'tee': self.settings.get('debug_mode', False),
            }
    
    def optimize(self, energy_system: solph.EnergySystem) -> Tuple[solph.Model, Dict[str, Any]]:
        """
        Führt die Optimierung des Energiesystems durch.
        
        Args:
            energy_system: Das zu optimierende oemof.solph EnergySystem
            
        Returns:
            Tuple (optimization_model, results)
        """
        self.logger.info(f"⚡ Starte Optimierung mit Solver: {self.solver_name}")
        
        start_time = time.time()
        
        try:
            # Modell erstellen
            self.logger.info("   🔨 Erstelle Optimierungsmodell...")
            model_creation_start = time.time()
            
            # In oemof.solph 0.6.0: Model() statt BaseModel()
            optimization_model = solph.Model(energy_system)
            
            model_creation_time = time.time() - model_creation_start
            self.logger.info(f"   ✅ Modell erstellt ({model_creation_time:.2f}s)")
            
            # Modell-Statistiken sammeln
            self._collect_model_statistics(optimization_model)
            
            # Solver-Verfügbarkeit prüfen
            if not self._check_solver_availability():
                raise RuntimeError(f"Solver '{self.solver_name}' ist nicht verfügbar")
            
            # Optimierung durchführen
            self.logger.info("   🚀 Führe Optimierung durch...")
            solve_start = time.time()
            
            # Einfacher Solve-Aufruf ohne komplexe Optionen
            try:
                # Nur grundlegende Optionen verwenden
                solve_kwargs = {
                    'tee': self.settings.get('debug_mode', False)
                }
                
                optimization_model.solve(
                    solver=self.solver_name,
                    solve_kwargs=solve_kwargs
                )
                
            except Exception as solve_error:
                self.logger.warning(f"Solve mit Optionen fehlgeschlagen: {solve_error}")
                self.logger.info("   🔄 Versuche Solve ohne spezielle Optionen...")
                
                # Fallback: Solve ohne zusätzliche Optionen
                optimization_model.solve(solver=self.solver_name)
            
            solve_time = time.time() - solve_start
            self.logger.info(f"   ✅ Optimierung abgeschlossen ({solve_time:.2f}s)")
            
            # Solver-Status prüfen
            self._check_solution_status(optimization_model)
            
            # Ergebnisse extrahieren
            self.logger.info("   📊 Extrahiere Ergebnisse...")
            results_start = time.time()
            
            # In oemof.solph 0.6.0: processing.results()
            results = solph.processing.results(optimization_model)
            
            results_time = time.time() - results_start
            self.logger.info(f"   ✅ Ergebnisse extrahiert ({results_time:.2f}s)")
            
            # Gesamtzeit
            total_time = time.time() - start_time
            
            # Optimierungs-Statistiken speichern
            self.optimization_stats = {
                'solver': self.solver_name,
                'total_time': total_time,
                'model_creation_time': model_creation_time,
                'solve_time': solve_time,
                'results_extraction_time': results_time,
                'solver_status': self._get_solver_status(optimization_model),
                'objective_value': self._get_objective_value(optimization_model),
                'model_statistics': self._get_model_statistics(optimization_model)
            }
            
            self.logger.info(f"✅ Optimierung erfolgreich abgeschlossen (Gesamt: {total_time:.2f}s)")
            
            return optimization_model, results
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Optimierung: {e}")
            raise
    
    def _check_solver_availability(self) -> bool:
        """Prüft ob der gewählte Solver verfügbar ist."""
        try:
            from pyomo.opt import SolverFactory
            solver = SolverFactory(self.solver_name)
            available = solver.available()
            
            if available:
                self.logger.info(f"   ✅ Solver '{self.solver_name}' verfügbar")
            else:
                self.logger.error(f"   ❌ Solver '{self.solver_name}' nicht verfügbar")
                self._suggest_alternative_solvers()
            
            return available
            
        except Exception as e:
            self.logger.error(f"   ❌ Fehler bei Solver-Prüfung: {e}")
            return False
    
    def _suggest_alternative_solvers(self):
        """Schlägt alternative Solver vor."""
        from pyomo.opt import SolverFactory
        
        common_solvers = ['cbc', 'glpk', 'gurobi', 'cplex']
        available_solvers = []
        
        for solver_name in common_solvers:
            try:
                solver = SolverFactory(solver_name)
                if solver.available():
                    available_solvers.append(solver_name)
            except:
                pass
        
        if available_solvers:
            self.logger.info(f"   💡 Verfügbare alternative Solver: {', '.join(available_solvers)}")
        else:
            self.logger.warning("   ⚠️  Keine alternativen Solver gefunden")
            self.logger.info("   💡 Installationshinweise:")
            self.logger.info("      CBC: conda install -c conda-forge coincbc")
            self.logger.info("      GLPK: conda install -c conda-forge glpk")
    
    def _collect_model_statistics(self, model: solph.Model):
        """Sammelt Statistiken über das Optimierungsmodell."""
        try:
            # Pyomo-Modell-Statistiken
            pyomo_model = model
            
            # Variablen zählen
            num_vars = len([v for v in pyomo_model.component_objects(pyo.Var)])
            num_constraints = len([c for c in pyomo_model.component_objects(pyo.Constraint)])
            num_objectives = len([o for o in pyomo_model.component_objects(pyo.Objective)])
            
            # Detaillierte Variablen-/Constraint-Zählung
            total_vars = 0
            total_constraints = 0
            binary_vars = 0
            integer_vars = 0
            continuous_vars = 0
            
            for var in pyomo_model.component_objects(pyo.Var):
                var_count = len(var)
                total_vars += var_count
                
                # Variable Typen unterscheiden
                if hasattr(var, 'domain'):
                    if var.domain == pyo.Binary:
                        binary_vars += var_count
                    elif var.domain == pyo.Integers:
                        integer_vars += var_count
                    else:
                        continuous_vars += var_count
                else:
                    continuous_vars += var_count
            
            for constraint in pyomo_model.component_objects(pyo.Constraint):
                total_constraints += len(constraint)
            
            self.model_stats = {
                'components': num_vars,
                'total_variables': total_vars,
                'continuous_variables': continuous_vars,
                'binary_variables': binary_vars,
                'integer_variables': integer_vars,
                'total_constraints': total_constraints,
                'objectives': num_objectives,
                'problem_type': self._determine_problem_type(binary_vars, integer_vars)
            }
            
            self.logger.info(f"   📊 Modell: {total_vars} Variablen, {total_constraints} Constraints")
            if binary_vars > 0 or integer_vars > 0:
                self.logger.info(f"      🔢 {continuous_vars} kontinuierlich, {binary_vars} binär, {integer_vars} ganzzahlig")
            
        except Exception as e:
            self.logger.warning(f"   ⚠️  Konnte Modell-Statistiken nicht sammeln: {e}")
            self.model_stats = {}
    
    def _determine_problem_type(self, binary_vars: int, integer_vars: int) -> str:
        """Bestimmt den Problemtyp basierend auf Variablentypen."""
        if binary_vars > 0 or integer_vars > 0:
            return "MILP"  # Mixed Integer Linear Program
        else:
            return "LP"    # Linear Program
    
    def _check_solution_status(self, model: solph.Model):
        """Prüft den Status der Optimierungslösung."""
        try:
            # Pyomo Solver-Results zugreifen
            solver_results = model._solver_results
            
            if hasattr(solver_results, 'solver'):
                solver_status = solver_results.solver.status
                termination_condition = solver_results.solver.termination_condition
                
                self.logger.info(f"   🎯 Solver Status: {solver_status}")
                self.logger.info(f"   🏁 Termination: {termination_condition}")
                
                # Status bewerten
                if solver_status == SolverStatus.ok:
                    if termination_condition == TerminationCondition.optimal:
                        self.logger.info("   ✅ Optimale Lösung gefunden")
                    elif termination_condition == TerminationCondition.feasible:
                        self.logger.warning("   ⚠️  Zulässige, aber nicht optimale Lösung")
                    else:
                        self.logger.warning(f"   ⚠️  Ungewöhnlicher Termination-Status: {termination_condition}")
                else:
                    if termination_condition == TerminationCondition.infeasible:
                        raise RuntimeError("Optimierungsproblem ist unlösbar (infeasible)")
                    elif termination_condition == TerminationCondition.unbounded:
                        raise RuntimeError("Optimierungsproblem ist unbeschränkt (unbounded)")
                    else:
                        raise RuntimeError(f"Solver-Fehler: {solver_status}, {termination_condition}")
            
        except AttributeError:
            # Fallback wenn Solver-Results nicht verfügbar
            self.logger.warning("   ⚠️  Solver-Status nicht verfügbar")
        except Exception as e:
            self.logger.error(f"   ❌ Fehler bei Status-Prüfung: {e}")
            raise
    
    def _get_solver_status(self, model: solph.Model) -> Dict[str, str]:
        """Extrahiert Solver-Status Informationen."""
        try:
            solver_results = model._solver_results
            
            if hasattr(solver_results, 'solver'):
                return {
                    'status': str(solver_results.solver.status),
                    'termination_condition': str(solver_results.solver.termination_condition),
                    'return_code': str(getattr(solver_results.solver, 'return_code', 'unknown'))
                }
        except:
            pass
        
        return {'status': 'unknown', 'termination_condition': 'unknown', 'return_code': 'unknown'}
    
    def _get_objective_value(self, model: solph.Model) -> Optional[float]:
        """Extrahiert den Zielfunktionswert."""
        try:
            # Objective Value aus Pyomo-Modell
            for obj in model.component_objects(pyo.Objective):
                if obj.active:
                    return pyo.value(obj)
        except Exception as e:
            self.logger.warning(f"   ⚠️  Zielfunktionswert nicht verfügbar: {e}")
        
        return None
    
    def _get_model_statistics(self, model: solph.Model) -> Dict[str, Any]:
        """Gibt gesammelte Modell-Statistiken zurück."""
        return getattr(self, 'model_stats', {})
    
    def get_optimization_summary(self, model: solph.Model, results: Dict[str, Any]) -> Dict[str, str]:
        """
        Erstellt eine Zusammenfassung der Optimierung.
        
        Args:
            model: Das optimierte oemof.solph Model
            results: Die Optimierungsergebnisse
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        summary = {}
        
        if hasattr(self, 'optimization_stats'):
            stats = self.optimization_stats
            
            # Zeitinformationen
            summary['Gesamtzeit'] = f"{stats.get('total_time', 0):.2f} Sekunden"
            summary['Solve-Zeit'] = f"{stats.get('solve_time', 0):.2f} Sekunden"
            
            # Solver-Informationen
            summary['Solver'] = stats.get('solver', 'unbekannt')
            summary['Status'] = stats.get('solver_status', {}).get('status', 'unbekannt')
            
            # Zielfunktionswert
            obj_value = stats.get('objective_value')
            if obj_value is not None:
                summary['Zielfunktion'] = f"{obj_value:,.2f} €"
            
            # Modell-Typ
            model_stats = stats.get('model_statistics', {})
            if model_stats:
                summary['Problemtyp'] = model_stats.get('problem_type', 'unbekannt')
                summary['Variablen'] = str(model_stats.get('total_variables', 0))
                summary['Constraints'] = str(model_stats.get('total_constraints', 0))
                
                if model_stats.get('binary_variables', 0) > 0:
                    summary['Binärvariablen'] = str(model_stats.get('binary_variables', 0))
        
        # Ergebnis-Statistiken
        if results:
            summary['Ergebnis-Komponenten'] = str(len(results))
        
        return summary
    
    def save_model(self, model: solph.Model, filepath: str) -> bool:
        """
        Speichert das Optimierungsmodell (optional).
        
        Args:
            model: Das zu speichernde Model
            filepath: Pfad für die Modell-Datei
            
        Returns:
            bool: True bei Erfolg
        """
        if not self.settings.get('save_model', False):
            return False
        
        try:
            # Modell als LP-Datei speichern
            model.write(filepath + '.lp', io_options={'symbolic_solver_labels': True})
            self.logger.info(f"   💾 Modell gespeichert: {filepath}.lp")
            return True
            
        except Exception as e:
            self.logger.warning(f"   ⚠️  Modell konnte nicht gespeichert werden: {e}")
            return False
    
    def analyze_model_complexity(self, model: solph.Model) -> Dict[str, Any]:
        """
        Analysiert die Komplexität des Optimierungsmodells.
        
        Args:
            model: Das zu analysierende Model
            
        Returns:
            Dictionary mit Komplexitäts-Metriken
        """
        complexity = {
            'size_category': 'unknown',
            'expected_solve_time': 'unknown',
            'memory_estimate': 'unknown',
            'recommendations': []
        }
        
        try:
            model_stats = self._get_model_statistics(model)
            
            if model_stats:
                total_vars = model_stats.get('total_variables', 0)
                total_constraints = model_stats.get('total_constraints', 0)
                binary_vars = model_stats.get('binary_variables', 0)
                problem_type = model_stats.get('problem_type', 'LP')
                
                # Größenkategorisierung
                if total_vars < 1000 and total_constraints < 1000:
                    complexity['size_category'] = 'klein'
                    complexity['expected_solve_time'] = '< 1 Minute'
                elif total_vars < 10000 and total_constraints < 10000:
                    complexity['size_category'] = 'mittel'
                    complexity['expected_solve_time'] = '1-10 Minuten'
                elif total_vars < 100000 and total_constraints < 100000:
                    complexity['size_category'] = 'groß'
                    complexity['expected_solve_time'] = '10-60 Minuten'
                else:
                    complexity['size_category'] = 'sehr groß'
                    complexity['expected_solve_time'] = '> 1 Stunde'
                
                # MILP-spezifische Anpassungen
                if problem_type == 'MILP' and binary_vars > 0:
                    if binary_vars > 100:
                        complexity['expected_solve_time'] += ' (MILP: deutlich länger)'
                    
                    complexity['recommendations'].append("MILP-Problem: Verwenden Sie einen MIP-Solver wie CBC oder Gurobi")
                    
                    if binary_vars > 1000:
                        complexity['recommendations'].append("Viele Binärvariablen: Erwägen Sie Modell-Vereinfachungen")
                
                # Solver-Empfehlungen
                if total_vars > 50000:
                    complexity['recommendations'].append("Großes Problem: Gurobi oder CPLEX empfohlen")
                elif problem_type == 'LP':
                    complexity['recommendations'].append("LP-Problem: CBC, GLPK oder HiGHS geeignet")
                
                # Speicher-Schätzung (grob)
                estimated_memory_mb = (total_vars + total_constraints) * 0.001  # Sehr grobe Schätzung
                complexity['memory_estimate'] = f"~{estimated_memory_mb:.1f} MB"
                
        except Exception as e:
            self.logger.warning(f"Komplexitäts-Analyse fehlgeschlagen: {e}")
        
        return complexity


# Test-Funktionen
def test_optimizer():
    """Testfunktion für den Optimizer."""
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    try:
        from modules.excel_reader import ExcelReader
        from modules.system_builder import SystemBuilder
        
        # Test mit Beispieldatei
        example_file = Path("examples/example_1.xlsx")
        
        if example_file.exists():
            # System aufbauen
            settings = {'debug_mode': True, 'solver': 'cbc'}
            
            reader = ExcelReader(settings)
            excel_data = reader.read_project_file(example_file)
            
            builder = SystemBuilder(settings)
            energy_system = builder.build_energy_system(excel_data)
            
            # Optimierung testen
            optimizer = Optimizer(settings)
            
            # Komplexitäts-Analyse
            print("🔍 Erstelle Modell für Komplexitäts-Analyse...")
            test_model = solph.Model(energy_system)
            complexity = optimizer.analyze_model_complexity(test_model)
            
            print("📊 Komplexitäts-Analyse:")
            for key, value in complexity.items():
                if isinstance(value, list):
                    print(f"  {key}:")
                    for item in value:
                        print(f"    - {item}")
                else:
                    print(f"  {key}: {value}")
            
            # Optimierung durchführen
            print("\n⚡ Führe Optimierung durch...")
            model, results = optimizer.optimize(energy_system)
            
            print("✅ Test erfolgreich!")
            summary = optimizer.get_optimization_summary(model, results)
            print("Optimierungs-Zusammenfassung:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
                
        else:
            print(f"❌ Beispieldatei nicht gefunden: {example_file}")
            
    except ImportError as e:
        print(f"❌ Import-Fehler: {e}")
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_optimizer()
