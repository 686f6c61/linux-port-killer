#!/usr/bin/env python3
"""
Main - Aplicación principal GTK4 de Port Killer

Entry point de la interfaz gráfica completa. Usa GTK4 + libadwaita
para una UI moderna y nativa en GNOME.

Esta aplicación muestra la ventana principal con lista de puertos,
filtros, auto-refresh y acciones de kill.

Author: 686f6c61
Repository: https://github.com/686f6c61/linux-port-killer
Version: 1.0.0
Date: 2025-01-17
License: MIT

Dependencies:
    - GTK4 (gi.repository.Gtk '4.0')
    - libadwaita (gi.repository.Adw '1')
    - port_manager (módulo local)
    - main_window (módulo local)

Usage:
    python3 src/main.py
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio
from main_window import MainWindow
import sys


class PortKillerApp(Adw.Application):
    """
    Aplicación principal Port Killer usando Adwaita.

    Gestiona el ciclo de vida de la aplicación:
    - Inicialización
    - Creación de ventana
    - Carga de CSS
    - Manejo de señales (activate, shutdown)
    - Acciones globales (About, Quit)

    Attributes:
        main_window: MainWindow - Ventana principal (None hasta activate)
    """

    def __init__(self):
        """
        Inicializa la aplicación Adwaita.

        Configura:
        - Application ID único
        - Señales de activate y shutdown
        - Acciones globales
        """
        super().__init__(
            application_id='com.portkiller.app',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        self.main_window = None

        # Conectar señales del ciclo de vida
        self.connect('activate', self.on_activate)
        self.connect('shutdown', self.on_shutdown)

        # Crear acciones globales (About, Quit)
        self._create_actions()

    def _create_actions(self):
        """
        Crea las acciones globales de la aplicación.

        Acciones:
        - app.about: Muestra diálogo About
        - app.quit: Cierra la aplicación

        También configura shortcuts de teclado.
        """
        # Acción: About
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.add_action(about_action)

        # Acción: Quit
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit)
        self.add_action(quit_action)

        # Atajos de teclado
        self.set_accels_for_action('app.quit', ['<Ctrl>Q'])

    def on_activate(self, app):
        """
        Callback cuando la aplicación se activa.

        Se llama:
        - Al lanzar la aplicación por primera vez
        - Al hacer click en el icono si ya está corriendo

        Crea la ventana principal la primera vez y la presenta siempre.

        Args:
            app: La aplicación (self)
        """
        if not self.main_window:
            # Crear ventana principal
            self.main_window = MainWindow(self)

            # Cargar estilos CSS personalizados
            self._load_css()

        # Presentar ventana (traer al frente)
        self.main_window.present()

    def on_shutdown(self, app):
        """
        Callback al cerrar la aplicación.

        Limpia recursos:
        - Detiene timers de auto-refresh
        - Cierra conexiones

        Args:
            app: La aplicación (self)
        """
        if self.main_window:
            self.main_window.stop_auto_refresh()

    def on_about(self, action, param):
        """
        Muestra el diálogo About.

        Callback de la acción app.about.

        Args:
            action: La acción que disparó el evento
            param: Parámetros (no usado)
        """
        about = Adw.AboutWindow(
            transient_for=self.main_window,
            application_name='Port Killer',
            application_icon='network-server',
            developer_name='686f6c61',
            version='1.0.0',
            website='https://github.com/686f6c61/linux-port-killer',
            issue_url='https://github.com/686f6c61/linux-port-killer/issues',
            copyright='© 2025 686f6c61',
            license_type=Gtk.License.MIT_X11,
            developers=['686f6c61']
        )

        about.present()

    def on_quit(self, action, param):
        """
        Cierra la aplicación.

        Callback de la acción app.quit.

        Args:
            action: La acción que disparó el evento
            param: Parámetros (no usado)
        """
        self.quit()

    def _load_css(self):
        """
        Carga los estilos CSS personalizados.

        Lee el archivo assets/style.css y lo aplica a toda la aplicación.
        Si falla, continúa sin estilos (graceful degradation).

        Note:
            Los estilos incluyen:
            - Colores de badges (DEV, PROTECTED)
            - Estilo de filas de puertos
            - Botones destructivos
            - Scrollbars personalizadas
        """
        css_provider = Gtk.CssProvider()

        try:
            # Cargar CSS desde archivo
            css_provider.load_from_path('/home/r/Escritorio/Linux/port-killer/assets/style.css')

            # Aplicar a toda la aplicación
            Gtk.StyleContext.add_provider_for_display(
                self.main_window.get_display(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            # No crítico, continuar sin estilos
            print(f'Warning: Could not load CSS: {e}')


def main():
    """
    Entry point de la aplicación.

    Crea la aplicación y ejecuta el main loop de GTK.

    Returns:
        int: Exit code (0 = éxito, 1 = error)
    """
    app = PortKillerApp()
    return app.run(sys.argv)


# Entry point
if __name__ == '__main__':
    sys.exit(main())
