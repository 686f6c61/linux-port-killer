#!/usr/bin/env python3
"""
System Tray Standalone - Indicador independiente para la barra superior

Este módulo implementa el system tray indicator usando GTK3 y AppIndicator3.
Se ejecuta de forma independiente para evitar conflictos entre GTK3 y GTK4.

El tray muestra los puertos activos directamente en el menú y permite
matar procesos con un solo click.

Author: 686f6c61
Repository: https://github.com/686f6c61/linux-port-killer
Version: 1.0.0
Date: 2025-01-17
License: MIT

Dependencies:
    - GTK3 (gi.repository.Gtk '3.0')
    - AppIndicator3 (gi.repository.AppIndicator3 '0.1')
    - psutil (para port_manager)

Usage:
    python3 tray_standalone.py &
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GLib
import subprocess
import sys
import os

# Añadir el directorio src al path para importar port_manager
sys.path.insert(0, os.path.dirname(__file__))
from port_manager import PortManager


class TrayApp:
    """
    Aplicación System Tray para Port Killer.

    Crea un indicador en la barra superior del sistema que:
    - Muestra los puertos activos en el menú
    - Permite matar procesos con un click
    - Se actualiza automáticamente cada 5 segundos
    - Abre la GUI completa cuando se necesita

    Attributes:
        indicator: AppIndicator3.Indicator - El objeto del system tray
        menu: Gtk.Menu - Menú contextual del tray
    """

    def __init__(self):
        """
        Inicializa el system tray indicator.

        Crea el AppIndicator, configura el icono y construye el menú inicial.
        El menú se reconstruye automáticamente cada 5 segundos para mostrar
        los puertos activos actualizados.
        """
        # Crear indicator con icono de red
        # Icono: network-transmit-receive (flechas arriba/abajo)
        self.indicator = AppIndicator3.Indicator.new(
            'port-killer',
            'network-transmit-receive',
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )

        # Activar el indicator (hacerlo visible)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title('Port Killer')

        # Construir menú inicial
        self.rebuild_menu()

        # Actualizar menú cada 5 segundos automáticamente
        GLib.timeout_add_seconds(5, self.update_and_rebuild)

    def rebuild_menu(self):
        """
        Reconstruye completamente el menú del tray.

        Lee los puertos activos del sistema y crea un item de menú para cada uno.
        Los items son clickeables para matar el proceso correspondiente.

        Estructura del menú:
        - Header: Contador de puertos activos
        - Items de puertos (máx 10): Puerto - Proceso [clickeable para kill]
        - Separador
        - Abrir Port Killer (abre la GUI completa)
        - Actualizar (refresh manual)
        - Matar Todos (kill all dev ports)
        - Separador
        - Salir (cierra el tray)

        Note:
            Si hay más de 10 puertos, muestra "... y N más" para no saturar el menú
        """
        # Crear nuevo menú (GTK3)
        self.menu = Gtk.Menu()

        try:
            # Obtener puertos de desarrollo activos
            dev_ports = PortManager.get_dev_ports()

            if dev_ports:
                # Header con contador
                header = Gtk.MenuItem(label=f'═══ {len(dev_ports)} Puertos Activos ═══')
                header.set_sensitive(False)  # No clickeable
                self.menu.append(header)

                self.menu.append(Gtk.SeparatorMenuItem())

                # Mostrar cada puerto (máximo 10 para no llenar)
                for port in dev_ports[:10]:
                    # Formato: "3000 - python3"
                    label = f'{port.port} - {port.process_name}'
                    item = Gtk.MenuItem(label=label)

                    # Conectar click para matar este proceso
                    item.connect('activate', self.on_kill_port, port.pid, port.port)
                    self.menu.append(item)

                # Si hay más de 10, mostrar contador
                if len(dev_ports) > 10:
                    more = Gtk.MenuItem(label=f'... y {len(dev_ports) - 10} más')
                    more.set_sensitive(False)
                    self.menu.append(more)

            else:
                # Sin puertos activos
                empty = Gtk.MenuItem(label='Sin puertos dev activos')
                empty.set_sensitive(False)
                self.menu.append(empty)

        except Exception as e:
            # Error al leer puertos
            error = Gtk.MenuItem(label=f'Error: {e}')
            error.set_sensitive(False)
            self.menu.append(error)

        # Separador antes de acciones
        self.menu.append(Gtk.SeparatorMenuItem())

        # Abrir ventana principal (GUI completa)
        show_item = Gtk.MenuItem(label='Abrir Port Killer')
        show_item.connect('activate', self.on_show)
        self.menu.append(show_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Actualizar manualmente
        refresh_item = Gtk.MenuItem(label='Actualizar')
        refresh_item.connect('activate', self.on_refresh)
        self.menu.append(refresh_item)

        # Matar todos los puertos dev
        kill_all = Gtk.MenuItem(label='Matar Todos')
        kill_all.connect('activate', self.on_kill_all)
        self.menu.append(kill_all)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Salir del tray
        quit_item = Gtk.MenuItem(label='Salir')
        quit_item.connect('activate', self.on_quit)
        self.menu.append(quit_item)

        # Mostrar todos los items
        self.menu.show_all()

        # Asignar menú al indicator
        self.indicator.set_menu(self.menu)

    def update_and_rebuild(self):
        """
        Callback del timer de actualización.

        Se ejecuta cada 5 segundos para reconstruir el menú con los
        puertos activos actualizados.

        Returns:
            bool: True para continuar el timer, False para detenerlo
        """
        self.rebuild_menu()
        return True  # Continuar ejecutando cada 5 segundos

    def on_show(self, widget):
        """
        Abre la ventana principal de Port Killer.

        Lanza un proceso separado con la GUI completa (GTK4).
        Esto permite tener ambas interfaces corriendo simultáneamente.

        Args:
            widget: Widget GTK que disparó el evento (no usado)
        """
        subprocess.Popen(
            ['python3', 'src/main.py'],
            cwd='/home/r/Escritorio/Linux/port-killer'
        )

    def on_kill_port(self, widget, pid, port):
        """
        Mata un puerto específico.

        Callback cuando el usuario hace click en un puerto del menú.

        Args:
            widget: Widget GTK que disparó el evento
            pid (int): Process ID a matar
            port (int): Número de puerto (para logging)

        Note:
            Después de matar el proceso, espera 500ms y reconstruye el menú
            para reflejar los cambios inmediatamente.
        """
        try:
            # Matar el proceso
            PortManager.kill_process(pid)

            # Reconstruir menú después de 500ms para mostrar cambios
            GLib.timeout_add(500, self.rebuild_menu)

        except Exception as e:
            print(f'Error matando puerto {port}: {e}')

    def on_refresh(self, widget):
        """
        Actualiza el menú manualmente.

        Callback del botón "Actualizar" en el menú.

        Args:
            widget: Widget GTK que disparó el evento (no usado)
        """
        self.rebuild_menu()

    def on_kill_all(self, widget):
        """
        Mata todos los puertos de desarrollo.

        Callback del botón "Matar Todos" en el menú.

        Args:
            widget: Widget GTK que disparó el evento (no usado)

        Note:
            Los procesos protegidos (PostgreSQL, etc) no se matan.
            Después de matar, espera 500ms y reconstruye el menú.
        """
        try:
            # Matar todos los puertos dev (excepto protegidos)
            PortManager.kill_all_dev_ports()

            # Reconstruir menú después de 500ms
            GLib.timeout_add(500, self.rebuild_menu)

        except Exception as e:
            print(f'Error: {e}')

    def on_quit(self, widget):
        """
        Sale del system tray.

        Callback del botón "Salir" en el menú.
        Termina el loop principal de GTK.

        Args:
            widget: Widget GTK que disparó el evento (no usado)
        """
        Gtk.main_quit()


# Entry point
if __name__ == '__main__':
    """
    Punto de entrada del tray standalone.

    Crea la aplicación TrayApp e inicia el loop principal de GTK.
    El programa se ejecuta hasta que el usuario cierra el tray.
    """
    app = TrayApp()
    Gtk.main()
