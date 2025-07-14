#!/usr/bin/env python3
"""
src/builder/investment_builder.py - FIXED Investment-Parameter-Mapping

FIXED VERSION: Korrekte Parameter-Zuordnung nach oemof-Beispielen
- existing nur bei tatsächlich vorhandener Kapazität  
- Korrekte ep_costs Berechnung
- Robuste Investment-Validierung
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
from .base_builder import BaseModelBuilder
from ..core import setup_component_logger, get_numeric_value, get_boolean_value, get_investment_extensions

logger = setup_component_logger('builder.investment')

class InvestmentBuilder(BaseModelBuilder):
    """
    FIXED: Spezialisierte Klasse für Investment-Berechnungen
    Folgt exakt den oemof-Beispielen
    """
    
    def build_investment(self, component_data: pd.Series) -> Optional[object]:
        """
        FIXED: Erstellt Investment-Objekt nach oemof-Beispielen
        
        Args:
            component_data: Pandas Series mit Komponenten-Daten
            
        Returns:
            oemof.solph Investment-Objekt oder None
        """
        # Prüfe ob Investment aktiviert ist
        investment_enabled = get_boolean_value(component_data, 'investment', False)
        if not investment_enabled:
            return None
            
        # FIXED: Validierung der Investment-Parameter
        investment_max = get_numeric_value(component_data, 'investment_max', 0)
        if investment_max <= 0:
            logger.error(f"Investment aktiviert aber investment_max={investment_max} für {component_data.get('label', 'unknown')}")
            return None
        
        # Investment-Parameter sammeln
        capex = get_numeric_value(component_data, 'capex', 0)
        lifetime = get_numeric_value(component_data, 'lifetime', 20)
        wacc = get_numeric_value(component_data, 'wacc', 0.05)
        existing = get_numeric_value(component_data, 'existing', 0)
        
        # Phase 2.1: Investment-Erweiterungen
        investment_extensions = get_investment_extensions(component_data)
        investment_minimum = investment_extensions.get('minimum', 0)
        
        # FIXED: Annuitätenfaktor berechnen (ep_costs)
        if wacc > 0 and lifetime > 0:
            try:
                annuity_factor = (wacc * (1 + wacc)**lifetime) / ((1 + wacc)**lifetime - 1)
                ep_costs = capex * annuity_factor
            except (OverflowError, ZeroDivisionError):
                logger.warning(f"Annuitätenfaktor-Berechnung fehlgeschlagen für {component_data.get('label', 'unknown')}, verwende lineare Abschreibung")
                ep_costs = capex / lifetime if lifetime > 0 else capex
        else:
            ep_costs = capex / lifetime if lifetime > 0 else capex
        
        logger.debug(
            f"Investment '{component_data.get('label', 'unknown')}': "
            f"max={investment_max}, min={investment_minimum}, "
            f"existing={existing}, capex={capex}, lifetime={lifetime}, "
            f"wacc={wacc}, ep_costs={ep_costs:.2f}"
        )
        
        # FIXED: Investment-Parameter für oemof-solph (nach Beispielen)
        investment_params = {
            'maximum': investment_max,
            'ep_costs': ep_costs
        }
        
        # FIXED: existing nur wenn tatsächlich vorhanden (> 0)
        if existing > 0:
            investment_params['existing'] = existing
            logger.debug(f"Investment mit bestehender Kapazität: {existing}")
        
        # FIXED: minimum nur wenn > 0 (Phase 2.1)
        if investment_minimum > 0:
            investment_params['minimum'] = investment_minimum
            logger.debug(f"Investment minimum gesetzt: {investment_minimum}")
        
        # VALIDIERUNG: ep_costs sollte > 0 sein (außer bei kostenlosen Investments)
        if ep_costs <= 0:
            logger.warning(f"Investment '{component_data.get('label', 'unknown')}': ep_costs={ep_costs} (kostenlos)")
        
        # oemof-solph Investment-Objekt erstellen
        try:
            self._load_oemof_modules()
            investment_obj = self.Investment(**investment_params)
            logger.debug(f"Investment-Objekt erstellt: {investment_params}")
            return investment_obj
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Investment-Objekts: {e}")
            return None
    
    def calculate_annuity_factor(self, wacc: float, lifetime: float) -> float:
        """
        FIXED: Berechnet Annuitätenfaktor (robuste Version)
        
        Args:
            wacc: Kalkulationszinssatz (0.05 = 5%)
            lifetime: Lebensdauer in Jahren
            
        Returns:
            Annuitätenfaktor
        """
        if wacc <= 0 or lifetime <= 0:
            return 1.0 / max(lifetime, 1)
        
        try:
            factor = (wacc * (1 + wacc)**lifetime) / ((1 + wacc)**lifetime - 1)
            
            # Plausibilitätsprüfung
            if factor <= 0 or factor > 1:
                logger.warning(f"Annuitätenfaktor außerhalb Plausibilitätsbereich: {factor}, verwende lineare Abschreibung")
                return 1.0 / lifetime
            
            return factor
        except (OverflowError, ZeroDivisionError):
            logger.warning(f"Annuitätenfaktor-Berechnung fehlgeschlagen für wacc={wacc}, lifetime={lifetime}")
            return 1.0 / lifetime
    
    def validate_investment_configuration(self, data: Dict[str, Any]) -> List[str]:
        """
        FIXED: Validiert Investment-Konfiguration aller Komponenten
        
        Args:
            data: Dictionary mit Komponenten-DataFrames
            
        Returns:
            Liste mit Validierungs-Meldungen/Warnungen
        """
        issues = []
        
        for sheet_name in ['sources', 'sinks', 'converters', 'storages']:
            df = data.get(sheet_name, pd.DataFrame())
            if df.empty:
                continue
                
            for _, component in df.iterrows():
                component_issues = self._validate_component_investment(component, sheet_name)
                issues.extend(component_issues)
        
        return issues if issues else ["✅ Investment-Konfiguration validiert"]
    
    def _validate_component_investment(self, component: pd.Series, sheet_name: str) -> List[str]:
        """
        FIXED: Validiert Investment-Parameter einer einzelnen Komponente
        
        Args:
            component: Komponenten-Daten
            sheet_name: Name des Sheets (sources, sinks, etc.)
            
        Returns:
            Liste mit Issues für diese Komponente
        """
        issues = []
        label = component.get('label', 'unknown')
        
        investment_enabled = get_boolean_value(component, 'investment', False)
        
        if investment_enabled:
            # Investment-Parameter prüfen
            investment_max = get_numeric_value(component, 'investment_max', 0)
            investment_min = get_numeric_value(component, 'investment_min', 0)
            capex = get_numeric_value(component, 'capex', 0)
            lifetime = get_numeric_value(component, 'lifetime', 20)
            wacc = get_numeric_value(component, 'wacc', 0.05)
            existing = get_numeric_value(component, 'existing', 0)
            
            # Kritische Validierungen
            if investment_max <= 0:
                issues.append(f"❌ {sheet_name} '{label}': investment_max={investment_max} muss > 0 sein")
            
            if investment_min > investment_max:
                issues.append(f"❌ {sheet_name} '{label}': investment_min ({investment_min}) > investment_max ({investment_max})")
            
            if lifetime <= 0:
                issues.append(f"❌ {sheet_name} '{label}': lifetime={lifetime} muss > 0 sein")
            
            if wacc < 0 or wacc > 0.5:
                issues.append(f"⚠️ {sheet_name} '{label}': wacc={wacc} außerhalb normalem Bereich (0-50%)")
            
            # Warnungen
            if capex == 0:
                issues.append(f"⚠️ {sheet_name} '{label}': capex=0 (kostenloses Investment)")
            
            if existing > investment_max:
                issues.append(f"⚠️ {sheet_name} '{label}': existing ({existing}) > investment_max ({investment_max})")
            
            # Wirtschaftlichkeits-Check
            if capex > 0 and investment_max > 0:
                total_investment = investment_max * capex
                if total_investment > 1000000:  # > 1 Mio €
                    issues.append(f"💰 {sheet_name} '{label}': Sehr hohe max. Investition ({total_investment:,.0f} €)")
        
        else:
            # Kein Investment - prüfe existing
            existing = get_numeric_value(component, 'existing', 0)
            has_fix = 'fix' in component and pd.notna(component['fix'])
            
            if existing <= 0 and not has_fix and sheet_name != 'sinks':
                issues.append(f"⚠️ {sheet_name} '{label}': Weder Investment noch existing > 0")
        
        return issues
    
    def get_investment_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        FIXED: Erstellt umfassende Investment-Zusammenfassung
        
        Args:
            data: Dictionary mit Komponenten-DataFrames
            
        Returns:
            Dictionary mit Investment-Zusammenfassung
        """
        summary = {
            'total_investments': 0,
            'total_max_capex': 0,
            'total_min_capex': 0,
            'investments_by_type': {},
            'components': [],
            'validation_issues': []
        }
        
        # Validierung durchführen
        summary['validation_issues'] = self.validate_investment_configuration(data)
        
        # Investment-Komponenten analysieren
        for sheet_name in ['sources', 'sinks', 'converters', 'storages']:
            df = data.get(sheet_name, pd.DataFrame())
            if df.empty:
                continue
                
            sheet_investments = 0
            
            for _, component in df.iterrows():
                if get_boolean_value(component, 'investment', False):
                    inv_info = self._analyze_component_investment_detailed(component, sheet_name)
                    summary['components'].append(inv_info)
                    summary['total_investments'] += 1
                    summary['total_max_capex'] += inv_info['max_total_capex']
                    summary['total_min_capex'] += inv_info['min_total_capex']
                    sheet_investments += 1
            
            if sheet_investments > 0:
                summary['investments_by_type'][sheet_name] = sheet_investments
        
        return summary
    
    def _analyze_component_investment_detailed(self, component: pd.Series, component_type: str) -> Dict[str, Any]:
        """
        FIXED: Detaillierte Investment-Analyse einer Komponente
        
        Args:
            component: Komponenten-Daten
            component_type: Typ der Komponente
            
        Returns:
            Dictionary mit detaillierter Investment-Analyse
        """
        capex = get_numeric_value(component, 'capex', 0)
        investment_max = get_numeric_value(component, 'investment_max', 0)
        investment_min = get_numeric_value(component, 'investment_min', 0)
        lifetime = get_numeric_value(component, 'lifetime', 20)
        wacc = get_numeric_value(component, 'wacc', 0.05)
        existing = get_numeric_value(component, 'existing', 0)
        
        # Annuitätenfaktor und Kosten berechnen
        annuity_factor = self.calculate_annuity_factor(wacc, lifetime)
        ep_costs = capex * annuity_factor
        
        return {
            'label': component.get('label', 'unknown'),
            'type': component_type,
            'investment_max': investment_max,
            'investment_min': investment_min,
            'existing': existing,
            'capex': capex,
            'max_total_capex': investment_max * capex,
            'min_total_capex': investment_min * capex,
            'lifetime': lifetime,
            'wacc': wacc,
            'annuity_factor': annuity_factor,
            'ep_costs': ep_costs,
            'annual_costs_per_kw': ep_costs,
            'validation_status': 'OK' if investment_max > 0 and lifetime > 0 else 'WARNING'
        }
    
    def create_investment_report(self, data: Dict[str, Any]) -> str:
        """
        FIXED: Erstellt detaillierten Investment-Report
        
        Args:
            data: Dictionary mit Komponenten-DataFrames
            
        Returns:
            Formatierter Investment-Report als String
        """
        summary = self.get_investment_summary(data)
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("INVESTMENT-ANALYSE REPORT")
        report_lines.append("=" * 60)
        
        # Zusammenfassung
        report_lines.append(f"\n📊 ZUSAMMENFASSUNG:")
        report_lines.append(f"   Investment-Komponenten: {summary['total_investments']}")
        report_lines.append(f"   Max. Gesamtinvestition: {summary['total_max_capex']:,.0f} €")
        report_lines.append(f"   Min. Gesamtinvestition: {summary['total_min_capex']:,.0f} €")
        
        # Nach Typen
        if summary['investments_by_type']:
            report_lines.append(f"\n📈 NACH KOMPONENTENTYP:")
            for comp_type, count in summary['investments_by_type'].items():
                report_lines.append(f"   {comp_type}: {count} Investment(s)")
        
        # Validierungs-Issues
        if len(summary['validation_issues']) > 1:  # > 1 weil "OK" message auch dabei ist
            report_lines.append(f"\n⚠️  VALIDIERUNGS-ISSUES:")
            for issue in summary['validation_issues']:
                if not issue.startswith("✅"):
                    report_lines.append(f"   {issue}")
        
        # Detaillierte Komponenten
        if summary['components']:
            report_lines.append(f"\n💰 INVESTMENT-KOMPONENTEN DETAIL:")
            for comp in summary['components']:
                report_lines.append(f"\n   {comp['type'].upper()}: {comp['label']}")
                report_lines.append(f"     Max Investment: {comp['investment_max']:,.0f} kW = {comp['max_total_capex']:,.0f} €")
                if comp['investment_min'] > 0:
                    report_lines.append(f"     Min Investment: {comp['investment_min']:,.0f} kW = {comp['min_total_capex']:,.0f} €")
                if comp['existing'] > 0:
                    report_lines.append(f"     Bestehend: {comp['existing']:,.0f} kW")
                report_lines.append(f"     CAPEX: {comp['capex']:,.0f} €/kW")
                report_lines.append(f"     Annuität: {comp['ep_costs']:,.2f} €/kW/Jahr")
                report_lines.append(f"     Lifetime: {comp['lifetime']} Jahre, WACC: {comp['wacc']*100:.1f}%")
        
        report_lines.append("\n" + "=" * 60)
        
        return "\n".join(report_lines)
        
        # Nach Typen
        if summary['investments_by_type']:
            report_lines.append(f"\n📈 NACH KOMPONENTENTYP:")
            for comp_type, count in summary['investments_by_type'].items():
                report_lines.append(f"   {comp_type}: {count} Investment(s)")
        
        # Validierungs-Issues
        if len(summary['validation_issues']) > 1:  # > 1 weil "OK" message auch dabei ist
            report_lines.append(f"\n⚠️  VALIDIERUNGS-ISSUES:")
            for issue in summary['validation_issues']:
                if not issue.startswith("✅"):
                    report_lines.append(f"   {issue}")
        
        # Detaillierte Komponenten
        if summary['components']:
            report_lines.append(f"\n💰 INVESTMENT-KOMPONENTEN DETAIL:")
            for comp in summary['components']:
                report_lines.append(f"\n   {comp['type'].upper()}: {comp['label']}")
                report_lines.append(f"     Max Investment: {comp['investment_max']:,.0f} kW = {comp['max_total_capex']:,.0f} €")
                if comp['investment_min'] > 0:
                    report_lines.append(f"     Min Investment: {comp['investment_min']:,.0f} kW = {comp['min_total_capex']:,.0f} €")
                if comp['existing'] > 0:
                    report_lines.append(f"     Bestehend: {comp['existing']:,.0f} kW")
                report_lines.append(f"     CAPEX: {comp['capex']:,.0f} €/kW")
                report_lines.append(f"     Annuität: {comp['ep_costs']:,.2f} €/kW/Jahr")
                report_lines.append(f"     Lifetime: {comp['lifetime']} Jahre, WACC: {comp['wacc']*100:.1f}%")
        
        report_lines.append("\n" + "=" * 60)
        
        return "\n".join(report_lines)

# Export der Klasse für Import
__all__ = ['InvestmentBuilder']