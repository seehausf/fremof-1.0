#!/usr/bin/env python3
"""
Menu System für oemof.solph Energiesystem-Optimierung
===================================================

Zentrale Menü-Verwaltung und Benutzerinteraktion.
Separiert die UI-Logik von der Geschäftslogik.

Autor: [Ihr Name]
Datum: Juli 2025  
Version: 1.0.0
"""

from typing import Dict, Any, Optional, Callable
import logging


class MenuSystem:
    """Zentrale Menü-Verwaltung für das Energiesystem-Tool."""
    
    def __init__(self):
        """Initialisiert das Menü-System."""
        self.logger = logging.getLogger(__name__)
        self.menu_options: Dict[str, Dict[str, Any]] = {}
        self.setup_default_menu()
    
    def setup_default_menu(self):
        """Richtet das Standard-Hauptmenü ein."""
        self.menu_options = {
            "1": {
                "title": "🚀 Projekt ausführen",
                "description": "Führt ein ausgewähltes Energiesystem-Projekt aus",
                "handler": None  # Wird vom ProjectRunner gesetzt
            },
            "2": {
                "title": "⚙️ Module konfigurieren", 
                "description": "Konfiguriert die verfügbaren Module",
                "handler": None
            },
            "3": {
                "title": "📁 Neues Beispielprojekt erstellen",
                "description": "Erstellt ein neues Excel-Beispielprojekt",
                "handler": None
            },
            "4": {
                "title": "🔧 Projektstruktur einrichten",
                "description": "Richtet die Projektverzeichnisse ein",
                "handler": None
            },
            "5": {
                "title": "ℹ️ Projektinformationen anzeigen",
                "description": "Zeigt Informationen über das aktuelle Projekt",
                "handler": None
            },
            "6": {
                "title": "🧪 Test-Funktionen",
                "description": "Führt System-Tests durch",
                "handler": None
            },
            "7": {
                "title": "❌ Beenden",
                "description": "Beendet das Programm",
                "handler": None
            }
        }
    
    def add_menu_option(self, key: str, title: str, description: str, handler: Callable):
        """
        Fügt eine neue Menü-Option hinzu.
        
        Args:
            key: Menü-Schlüssel (z.B. "1", "2", etc.)
            title: Anzeige-Titel
            description: Beschreibung der Funktion
            handler: Callback-Funktion
        """
        self.menu_options[key] = {
            "title": title,
            "description": description,
            "handler": handler
        }
    
    def set_handler(self, key: str, handler: Callable):
        """
        Setzt den Handler für eine existierende Menü-Option.
        
        Args:
            key: Menü-Schlüssel
            handler: Callback-Funktion
        """
        if key in self.menu_options:
            self.menu_options[key]["handler"] = handler
        else:
            self.logger.warning(f"Menü-Option '{key}' nicht gefunden")
    
    def show_main_menu(self) -> str:
        """
        Zeigt das Hauptmenü an und nimmt Benutzereingabe entgegen.
        
        Returns:
            Ausgewählte Menü-Option als String
        """
        print("\n📋 HAUPTMENÜ")
        print("-" * 40)
        
        for key, option in self.menu_options.items():
            print(f"{key}. {option['title']}")
        
        try:
            choice = input("\nOption auswählen (1-7): ").strip()
            return choice
        except KeyboardInterrupt:
            print("\n👋 Programm beendet.")
            return "7"
    
    def show_project_header(self, project_root: str, project_count: int):
        """
        Zeigt den Programm-Header an.
        
        Args:
            project_root: Projektverzeichnis-Pfad
            project_count: Anzahl verfügbarer Projekte
        """
        print("🚀 oemof.solph 0.6.0 Energiesystem-Optimierung")
        print("=" * 60)
        print("Interaktives Hauptprogramm mit System-Export")
        print(f"Projektverzeichnis: {project_root}")
        print(f"Verfügbare Projekte: {project_count}")
    
    def handle_choice(self, choice: str) -> bool:
        """
        Verarbeitet die Menü-Auswahl.
        
        Args:
            choice: Ausgewählte Menü-Option
            
        Returns:
            False wenn das Programm beendet werden soll, sonst True
        """
        if choice == "7":
            print("👋 Auf Wiedersehen!")
            return False
        
        if choice not in self.menu_options:
            print("❌ Ungültige Auswahl. Bitte wählen Sie 1-7.")
            return True
        
        option = self.menu_options[choice]
        handler = option["handler"]
        
        if handler:
            try:
                handler()
            except Exception as e:
                self.logger.error(f"Fehler beim Ausführen von '{option['title']}': {e}")
                print(f"❌ Fehler beim Ausführen von '{option['title']}': {e}")
        else:
            self.logger.warning(f"Kein Handler für Option '{choice}' definiert")
            print(f"❌ Funktion '{option['title']}' nicht verfügbar")
        
        return True
    
    def show_submenu(self, title: str, options: Dict[str, str], 
                    prompt: str = "Option auswählen: ") -> Optional[str]:
        """
        Zeigt ein Untermenü an.
        
        Args:
            title: Titel des Untermenüs
            options: Dictionary mit Optionen {key: description}
            prompt: Eingabeaufforderung
            
        Returns:
            Ausgewählte Option oder None bei Fehler
        """
        print(f"\n{title}")
        print("-" * len(title))
        
        for key, description in options.items():
            print(f"{key}. {description}")
        
        try:
            choice = input(f"\n{prompt}").strip()
            return choice if choice in options else None
        except KeyboardInterrupt:
            print("\n❌ Abgebrochen.")
            return None
    
    def show_confirmation(self, message: str, default: bool = False) -> bool:
        """
        Zeigt eine Bestätigungsabfrage an.
        
        Args:
            message: Bestätigungs-Nachricht
            default: Standard-Antwort bei Enter
            
        Returns:
            True bei Bestätigung, False bei Ablehnung
        """
        default_text = "(J/n)" if default else "(j/N)"
        
        try:
            response = input(f"{message} {default_text}: ").strip().lower()
            
            if not response:
                return default
                
            return response in ['j', 'ja', 'y', 'yes']
        except KeyboardInterrupt:
            print("\n❌ Abgebrochen.")
            return False
    
    def show_input_dialog(self, prompt: str, default: str = "") -> Optional[str]:
        """
        Zeigt einen Eingabedialog an.
        
        Args:
            prompt: Eingabeaufforderung
            default: Standard-Wert
            
        Returns:
            Eingabe oder None bei Abbruch
        """
        try:
            if default:
                response = input(f"{prompt} [{default}]: ").strip()
                return response if response else default
            else:
                return input(f"{prompt}: ").strip()
        except KeyboardInterrupt:
            print("\n❌ Abgebrochen.")
            return None
    
    def show_error(self, message: str, details: Optional[str] = None):
        """
        Zeigt eine Fehlermeldung an.
        
        Args:
            message: Haupt-Fehlermeldung
            details: Optionale Details
        """
        print(f"❌ {message}")
        if details:
            print(f"   Details: {details}")
    
    def show_success(self, message: str, details: Optional[str] = None):
        """
        Zeigt eine Erfolgsmeldung an.
        
        Args:
            message: Haupt-Erfolgsmeldung
            details: Optionale Details
        """
        print(f"✅ {message}")
        if details:
            print(f"   {details}")
    
    def show_info(self, message: str, details: Optional[str] = None):
        """
        Zeigt eine Informationsmeldung an.
        
        Args:
            message: Haupt-Informationsmeldung
            details: Optionale Details
        """
        print(f"ℹ️ {message}")
        if details:
            print(f"   {details}")
    
    def show_warning(self, message: str, details: Optional[str] = None):
        """
        Zeigt eine Warnmeldung an.
        
        Args:
            message: Haupt-Warnmeldung
            details: Optionale Details
        """
        print(f"⚠️ {message}")
        if details:
            print(f"   {details}")


# Test-Funktion
def test_menu_system():
    """Test-Funktion für das Menü-System."""
    menu = MenuSystem()
    
    # Test-Handler
    def test_handler():
        print("Test-Handler ausgeführt!")
    
    # Handler setzen
    menu.set_handler("1", test_handler)
    
    # Untermenü testen
    submenu_options = {
        "1": "Option 1",
        "2": "Option 2",
        "3": "Zurück"
    }
    
    choice = menu.show_submenu("Test-Untermenü", submenu_options)
    print(f"Gewählte Option: {choice}")
    
    # Bestätigung testen
    confirmed = menu.show_confirmation("Test-Bestätigung", default=True)
    print(f"Bestätigt: {confirmed}")
    
    # Eingabe testen
    user_input = menu.show_input_dialog("Test-Eingabe", "Standard-Wert")
    print(f"Eingabe: {user_input}")
    
    # Nachrichten testen
    menu.show_error("Test-Fehler", "Fehler-Details")
    menu.show_success("Test-Erfolg", "Erfolg-Details")
    menu.show_info("Test-Info", "Info-Details")
    menu.show_warning("Test-Warnung", "Warn-Details")


if __name__ == "__main__":
    test_menu_system()
