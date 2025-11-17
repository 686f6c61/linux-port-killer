#!/usr/bin/env python3
"""
Main Window - Ventana principal GTK4 de Port Killer

Implementa la interfaz gráfica completa con:
- Lista de puertos activos en tiempo real
- Filtros (All Ports / Dev Only)
- Auto-refresh cada 5 segundos
- Kill individual y masivo
- Confirmaciones para procesos protegidos

Author: 686f6c61
Repository: https://github.com/686f6c61/linux-port-killer
Version: 1.0.0
Date: 2025-01-17
License: MIT
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from port_manager import PortManager, PortProcess
from typing import List


class PortRow(Gtk.Box):
    """
    Widget que representa una fila de puerto en la lista.

    Muestra:
    - Número de puerto
    - Icono de protocolo
    - Nombre del proceso
    - Línea de comando (seleccionable para copiar)
    - Badges: [DEV], [PROTECTED]
    - PID
    - Botón kill (rojo)

    Attributes:
        port_proc (PortProcess): Información del puerto
        on_kill_callback: Función a llamar cuando se hace click en kill
    """

    def __init__(self, port_proc: PortProcess, on_kill_callback):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.port_proc = port_proc
        self.on_kill_callback = on_kill_callback

        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        # Puerto
        port_label = Gtk.Label(label=str(port_proc.port))
        port_label.set_width_chars(6)
        port_label.add_css_class('port-number')
        self.append(port_label)

        # Icono de protocolo
        protocol_icon = Gtk.Image.new_from_icon_name('network-transmit-symbolic')
        self.append(protocol_icon)

        # Información del proceso
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        process_label = Gtk.Label(label=port_proc.process_name)
        process_label.set_xalign(0)
        process_label.add_css_class('process-name')
        info_box.append(process_label)

        cmd_label = Gtk.Label(label=port_proc.cmdline)
        cmd_label.set_xalign(0)
        cmd_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        cmd_label.set_selectable(True)  # Hacer seleccionable/copiable
        cmd_label.add_css_class('command-line')
        info_box.append(cmd_label)

        self.append(info_box)

        # Badge si es protegido
        if port_proc.is_protected:
            protected_badge = Gtk.Label(label='PROTECTED')
            protected_badge.add_css_class('protected-badge')
            self.append(protected_badge)

        # Badge si es puerto de desarrollo
        if PortManager.is_dev_port(port_proc.port):
            dev_badge = Gtk.Label(label='DEV')
            dev_badge.add_css_class('dev-badge')
            self.append(dev_badge)

        # PID
        pid_label = Gtk.Label(label=f'PID {port_proc.pid}')
        pid_label.add_css_class('pid-label')
        self.append(pid_label)

        # Botón kill
        kill_button = Gtk.Button()
        kill_button.set_icon_name('process-stop-symbolic')
        kill_button.add_css_class('destructive-action')
        kill_button.connect('clicked', self._on_kill_clicked)
        self.append(kill_button)

        # Estilo de la fila
        self.add_css_class('port-row')

    def _on_kill_clicked(self, button):
        """Callback al hacer click en kill"""
        self.on_kill_callback(self.port_proc)


class MainWindow(Adw.ApplicationWindow):
    """
    Ventana principal de Port Killer.

    Estructura:
    - Header bar (con refresh y menú)
    - Toolbar (filtros y contador)
    - Lista scrollable de puertos
    - Action bar (auto-refresh, kill all)

    Features:
    - Auto-refresh cada 5 segundos
    - Filtros: All / Dev Only
    - Kill individual con confirmación para protegidos
    - Kill masivo de dev ports
    - Líneas de comando seleccionables

    Attributes:
        refresh_timeout: ID del timer de auto-refresh
        auto_refresh (bool): Si está activo el auto-refresh
        filter_all (Gtk.CheckButton): Botón del filtro "All"
        port_count_label (Gtk.Label): Label con contador de puertos
        ports_box (Gtk.Box): Container de la lista de puertos
    """

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title('Port Killer')
        self.set_default_size(700, 500)
        self.set_hide_on_close(True)  # No cerrar al hacer X, solo ocultar

        # Configuración de actualización
        self.refresh_timeout = None
        self.auto_refresh = True

        # Layout principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()

        # Botón refresh
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name('view-refresh-symbolic')
        refresh_button.connect('clicked', self._on_refresh_clicked)
        header.pack_start(refresh_button)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('open-menu-symbolic')
        menu = self._create_menu()
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        main_box.append(header)

        # Toolbar con filtros
        toolbar = self._create_toolbar()
        main_box.append(toolbar)

        # ScrolledWindow para la lista de puertos
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Lista de puertos
        self.ports_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.ports_box.set_margin_top(12)
        self.ports_box.set_margin_bottom(12)

        scrolled.set_child(self.ports_box)
        main_box.append(scrolled)

        # Action bar inferior
        action_bar = self._create_action_bar()
        main_box.append(action_bar)

        self.set_content(main_box)

        # Cargar puertos iniciales
        self.refresh_ports()

        # Iniciar auto-refresh
        self.start_auto_refresh()

    def _create_toolbar(self) -> Gtk.Box:
        """
        Crea la barra de herramientas con filtros y contador de puertos.

        Construye un Gtk.Box horizontal con:
        - Label "Filter:"
        - Radio buttons: "All Ports" y "Dev Only"
        - Spacer para empujar el contador a la derecha
        - Label con contador de puertos (ej: "5 ports")

        Los filtros están implementados como CheckButtons en grupo,
        lo que permite seleccionar solo uno a la vez (comportamiento radio).

        Returns:
            Gtk.Box: Container con todos los widgets de la toolbar
        """
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.add_css_class('toolbar')

        # Filtro: Todos / Solo Dev
        filter_label = Gtk.Label(label='Filter:')
        toolbar.append(filter_label)

        self.filter_all = Gtk.CheckButton(label='All Ports')
        self.filter_all.set_active(True)
        toolbar.append(self.filter_all)

        filter_dev = Gtk.CheckButton(label='Dev Only')
        filter_dev.set_group(self.filter_all)
        filter_dev.connect('toggled', self._on_filter_changed)
        toolbar.append(filter_dev)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Contador de puertos
        self.port_count_label = Gtk.Label(label='0 ports')
        self.port_count_label.add_css_class('port-count')
        toolbar.append(self.port_count_label)

        return toolbar

    def _create_action_bar(self) -> Gtk.Box:
        """
        Crea la barra de acciones inferior con controles globales.

        Construye un Gtk.Box horizontal con:
        - CheckButton "Auto-refresh (5s)" - Toggle para activar/desactivar
          el refresco automático de la lista de puertos
        - Spacer para empujar el botón a la derecha
        - Botón "Kill All Dev Ports" - Mata todos los puertos de desarrollo
          con confirmación previa

        Returns:
            Gtk.Box: Container con todos los widgets del action bar
        """
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_bar.set_margin_start(12)
        action_bar.set_margin_end(12)
        action_bar.set_margin_top(8)
        action_bar.set_margin_bottom(8)
        action_bar.add_css_class('action-bar')

        # Auto-refresh toggle
        auto_refresh_check = Gtk.CheckButton(label='Auto-refresh (5s)')
        auto_refresh_check.set_active(True)
        auto_refresh_check.connect('toggled', self._on_auto_refresh_toggled)
        action_bar.append(auto_refresh_check)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        action_bar.append(spacer)

        # Botón: Kill all dev
        kill_dev_button = Gtk.Button(label='Kill All Dev Ports')
        kill_dev_button.add_css_class('destructive-action')
        kill_dev_button.connect('clicked', self._on_kill_all_dev)
        action_bar.append(kill_dev_button)

        return action_bar

    def _create_menu(self) -> Gio.Menu:
        """
        Crea el menú hamburger de la aplicación.

        Construye un Gio.Menu con las acciones globales:
        - About: Muestra el diálogo About con info del autor y repo
        - Quit: Cierra la aplicación (Ctrl+Q)

        Estas acciones están definidas en la clase PortKillerApp
        en src/main.py y están disponibles globalmente.

        Returns:
            Gio.Menu: Modelo de menú para el MenuButton del header
        """
        menu = Gio.Menu()
        menu.append('About', 'app.about')
        menu.append('Quit', 'app.quit')
        return menu

    def refresh_ports(self):
        """
        Actualiza la lista de puertos leyendo el estado actual del sistema.

        Workflow:
        1. Limpia todos los widgets de self.ports_box
        2. Lee puertos según el filtro activo (All o Dev Only)
        3. Actualiza el contador de puertos en la toolbar
        4. Renderiza filas:
           - Si no hay puertos: muestra "No ports found"
           - Si hay puertos: crea un PortRow por cada uno + separador

        Este método se llama:
        - Al iniciar la aplicación
        - Cada 5 segundos (auto-refresh)
        - Al hacer click en el botón Refresh
        - Al cambiar el filtro
        - Después de matar un proceso (con 500ms de delay)

        Note:
            Los puertos se obtienen de PortManager.get_listening_ports() o
            PortManager.get_dev_ports() dependiendo del filtro activo.
        """
        # Limpiar lista actual
        while True:
            child = self.ports_box.get_first_child()
            if child is None:
                break
            self.ports_box.remove(child)

        # Obtener puertos según filtro
        if self.filter_all.get_active():
            ports = PortManager.get_listening_ports()
        else:
            ports = PortManager.get_dev_ports()

        # Actualizar contador
        self.port_count_label.set_label(f'{len(ports)} ports')

        # Agregar filas
        if not ports:
            empty_label = Gtk.Label(label='No ports found')
            empty_label.add_css_class('empty-state')
            empty_label.set_margin_top(50)
            empty_label.set_margin_bottom(50)
            self.ports_box.append(empty_label)
        else:
            for port_proc in ports:
                row = PortRow(port_proc, self._on_kill_port)
                self.ports_box.append(row)
                # Agregar separador
                separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                separator.set_margin_start(12)
                separator.set_margin_end(12)
                self.ports_box.append(separator)

    def _on_refresh_clicked(self, button):
        """
        Callback del botón Refresh en el header bar.

        Actualiza manualmente la lista de puertos al hacer click.

        Args:
            button (Gtk.Button): El botón que disparó el evento (no usado)
        """
        self.refresh_ports()

    def _on_filter_changed(self, button):
        """
        Callback cuando cambia el filtro (All Ports / Dev Only).

        Se ejecuta al hacer click en cualquiera de los radio buttons
        del filtro. Refresca la lista para mostrar los puertos según
        el filtro seleccionado.

        Args:
            button (Gtk.CheckButton): El botón de filtro que se activó
        """
        self.refresh_ports()

    def _on_kill_port(self, port_proc: PortProcess):
        """
        Callback para matar un puerto individual.

        Se ejecuta cuando el usuario hace click en el botón Kill de una fila.
        Implementa protección para procesos críticos:

        - Si el proceso NO es protegido: lo mata directamente
        - Si el proceso ES protegido (ej: PostgreSQL, MySQL): muestra
          un diálogo de confirmación con advertencia

        Args:
            port_proc (PortProcess): Información del puerto a matar
                (incluye pid, port, process_name, is_protected)

        Note:
            Los procesos protegidos están definidos en PortManager.PROTECTED_PROCESSES
            e incluyen bases de datos, web servers y servicios críticos.
        """
        # Si es protegido, confirmar
        if port_proc.is_protected:
            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading('Kill Protected Process?')
            dialog.set_body(
                f'Process "{port_proc.process_name}" on port {port_proc.port} '
                f'is marked as protected. Are you sure?'
            )
            dialog.add_response('cancel', 'Cancel')
            dialog.add_response('kill', 'Kill Process')
            dialog.set_response_appearance('kill', Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect('response', lambda d, r: self._confirm_kill(r, port_proc.pid))
            dialog.present()
        else:
            self._kill_process(port_proc.pid)

    def _confirm_kill(self, response: str, pid: int):
        """
        Procesa la respuesta del diálogo de confirmación de kill.

        Se ejecuta cuando el usuario responde al diálogo de advertencia
        para procesos protegidos.

        Args:
            response (str): Respuesta del diálogo ('kill' o 'cancel')
            pid (int): Process ID a matar si se confirma

        Note:
            Solo se mata el proceso si response == 'kill'.
            Si el usuario cancela, no hace nada.
        """
        if response == 'kill':
            self._kill_process(pid)

    def _kill_process(self, pid: int):
        """
        Mata un proceso y actualiza la interfaz.

        Workflow:
        1. Llama a PortManager.kill_process(pid) con SIGTERM
        2. Si tiene éxito:
           - Muestra toast de confirmación
           - Espera 500ms para que el proceso termine
           - Refresca la lista de puertos (el proceso ya no aparece)
        3. Si falla:
           - Muestra toast de error

        Args:
            pid (int): Process ID del proceso a matar

        Note:
            El delay de 500ms permite que el proceso termine completamente
            antes de refrescar, evitando mostrar procesos zombies.
        """
        success = PortManager.kill_process(pid)

        if success:
            # Mostrar toast
            toast = Adw.Toast.new(f'Process {pid} killed')
            toast.set_timeout(2)
            # Refrescar lista
            GLib.timeout_add(500, self.refresh_ports)
        else:
            # Error toast
            toast = Adw.Toast.new(f'Failed to kill process {pid}')
            toast.set_timeout(3)

    def _on_kill_all_dev(self, button):
        """
        Mata todos los puertos de desarrollo con confirmación.

        Se ejecuta al hacer click en el botón "Kill All Dev Ports"
        del action bar inferior.

        Muestra un diálogo de confirmación explicando que se matarán
        todos los procesos en puertos de desarrollo (3000-3999,
        5000-5999, 8000-8999, etc.).

        Args:
            button (Gtk.Button): El botón que disparó el evento (no usado)

        Note:
            Los procesos protegidos (PostgreSQL en 5432, etc.) NO se matan
            aunque estén en rangos de desarrollo.
        """
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading('Kill All Dev Ports?')
        dialog.set_body('This will terminate all processes running on development ports.')
        dialog.add_response('cancel', 'Cancel')
        dialog.add_response('kill', 'Kill All')
        dialog.set_response_appearance('kill', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect('response', self._confirm_kill_all_dev)
        dialog.present()

    def _confirm_kill_all_dev(self, dialog, response: str):
        """
        Procesa la confirmación de "Kill All Dev Ports".

        Si el usuario confirma, mata todos los puertos de desarrollo
        y muestra un toast con la cantidad de procesos matados.

        Args:
            dialog (Adw.MessageDialog): El diálogo que disparó el evento
            response (str): Respuesta del usuario ('kill' o 'cancel')

        Note:
            PortManager.kill_all_dev_ports() automáticamente excluye
            procesos protegidos y retorna la cantidad de procesos matados.
        """
        if response == 'kill':
            killed = PortManager.kill_all_dev_ports()
            toast = Adw.Toast.new(f'Killed {killed} processes')
            toast.set_timeout(2)
            GLib.timeout_add(500, self.refresh_ports)

    def _on_auto_refresh_toggled(self, button):
        """
        Toggle del auto-refresh activado/desactivado.

        Se ejecuta cuando el usuario hace click en el CheckButton
        "Auto-refresh (5s)" del action bar.

        - Si se activa: inicia el timer de 5 segundos
        - Si se desactiva: detiene el timer

        Args:
            button (Gtk.CheckButton): El CheckButton del auto-refresh
        """
        self.auto_refresh = button.get_active()

        if self.auto_refresh:
            self.start_auto_refresh()
        else:
            self.stop_auto_refresh()

    def start_auto_refresh(self):
        """
        Inicia el timer de auto-refresh.

        Crea un timeout de GLib que ejecuta refresh_ports() cada 5 segundos.
        Solo crea el timer si no existe uno activo.

        El ID del timer se guarda en self.refresh_timeout para poder
        detenerlo después.

        Note:
            Se llama automáticamente al iniciar la aplicación y cuando
            el usuario activa el auto-refresh manualmente.
        """
        if self.refresh_timeout is None:
            self.refresh_timeout = GLib.timeout_add_seconds(5, self._auto_refresh_callback)

    def stop_auto_refresh(self):
        """
        Detiene el timer de auto-refresh.

        Elimina el timeout de GLib si existe, parando el refresco
        automático de la lista de puertos.

        Note:
            Se llama cuando el usuario desactiva el auto-refresh o
            cuando la aplicación se cierra.
        """
        if self.refresh_timeout is not None:
            GLib.source_remove(self.refresh_timeout)
            self.refresh_timeout = None

    def _auto_refresh_callback(self):
        """
        Callback del timer de auto-refresh.

        Se ejecuta cada 5 segundos cuando el auto-refresh está activo.
        Refresca la lista de puertos y determina si el timer debe continuar.

        Returns:
            bool: True para continuar el timer, False para detenerlo

        Note:
            Verifica self.auto_refresh antes de refrescar para respetar
            si el usuario lo desactivó durante la ejecución.
        """
        if self.auto_refresh:
            self.refresh_ports()
            return True  # Continuar
        return False  # Detener
