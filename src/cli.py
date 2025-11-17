#!/usr/bin/env python3
"""
CLI - Interfaz de línea de comandos para Port Killer

Proporciona comandos para gestionar puertos desde la terminal sin GUI.
Útil para scripts, automatización y uso en servidores.

Author: 686f6c61
Repository: https://github.com/686f6c61/linux-port-killer
Version: 1.0.0
Date: 2025-01-17
License: MIT

Commands:
    list        - Lista todos los puertos activos
    list-dev    - Lista solo puertos de desarrollo
    kill PORT   - Mata proceso en puerto específico
    kill-dev    - Mata todos los puertos de desarrollo
    info PORT   - Muestra información detallada de un puerto

Usage:
    port-killer list
    port-killer kill 3000
    port-killer kill-dev -y
"""

import argparse
import sys
from port_manager import PortManager


def list_ports(args):
    """
    Lista todos los puertos activos en el sistema.

    Muestra una tabla con:
    - Puerto
    - Protocolo (TCP/UDP)
    - PID del proceso
    - Nombre del proceso
    - Línea de comando
    - Badges: [P] para protegidos, [D] para dev

    Args:
        args: Argumentos de argparse (no usado)

    Output:
        Tabla formateada en stdout
    """
    ports = PortManager.get_listening_ports()

    if not ports:
        print('No ports found')
        return

    # Header de la tabla
    print(f'\n{"PORT":<8} {"PROTOCOL":<10} {"PID":<8} {"PROCESS":<20} {"COMMAND":<40}')
    print('-' * 90)

    # Cada puerto como fila
    for port in ports:
        # Badges para protected y dev
        protected = '[P]' if port.is_protected else '   '
        dev = '[D]' if PortManager.is_dev_port(port.port) else '   '

        print(
            f'{port.port:<8} {port.protocol:<10} {port.pid:<8} '
            f'{port.process_name:<20} {port.cmdline:<40} {protected} {dev}'
        )

    # Footer con leyenda
    print(f'\nTotal: {len(ports)} ports')
    print('[P] = Protected process')
    print('[D] = Development port\n')


def list_dev_ports(args):
    """
    Lista solo los puertos de desarrollo.

    Filtra y muestra únicamente puertos en rangos de desarrollo
    (3000-3999, 5000-5999, 8000-8999, etc.)

    Args:
        args: Argumentos de argparse (no usado)

    Output:
        Tabla simplificada solo con puertos dev
    """
    ports = PortManager.get_dev_ports()

    if not ports:
        print('No development ports found')
        return

    # Header
    print(f'\n{"PORT":<8} {"PID":<8} {"PROCESS":<20} {"COMMAND":<40}')
    print('-' * 80)

    # Cada puerto dev
    for port in ports:
        protected = '[PROTECTED]' if port.is_protected else ''
        print(
            f'{port.port:<8} {port.pid:<8} {port.process_name:<20} '
            f'{port.cmdline:<40} {protected}'
        )

    print(f'\nTotal: {len(ports)} development ports\n')


def kill_port(args):
    """
    Mata el proceso en un puerto específico.

    Workflow:
    1. Verificar que existe proceso en ese puerto
    2. Si es protegido, pedir confirmación (a menos que -y)
    3. Matar proceso con SIGTERM (o SIGKILL si -f)
    4. Reportar éxito/error

    Args:
        args: Argumentos con:
            - port (int): Número de puerto
            - force (bool): Usar SIGKILL en lugar de SIGTERM
            - yes (bool): Skip confirmación

    Exit codes:
        0 - Éxito
        1 - Error (puerto no encontrado o fallo al matar)
    """
    port = args.port
    force = args.force

    # Verificar si existe proceso en ese puerto
    port_info = PortManager.get_port_info(port)

    if not port_info:
        print(f'Error: No process found on port {port}')
        sys.exit(1)

    # Advertir si es un proceso protegido (DB, web server, etc)
    if port_info.is_protected and not args.yes:
        print(f'Warning: Process "{port_info.process_name}" is marked as protected')
        response = input('Continue? [y/N]: ')
        if response.lower() != 'y':
            print('Cancelled')
            sys.exit(0)

    # Intentar matar el proceso
    print(f'Killing process {port_info.process_name} (PID {port_info.pid}) on port {port}...')

    success = PortManager.kill_port(port, force=force)

    if success:
        print(f'Successfully killed process on port {port}')
    else:
        print(f'Error: Failed to kill process on port {port}')
        sys.exit(1)


def kill_all_dev(args):
    """
    Mata todos los procesos en puertos de desarrollo.

    Workflow:
    1. Obtener lista de puertos dev
    2. Mostrar lista y pedir confirmación (a menos que -y)
    3. Matar todos excepto protegidos
    4. Reportar cantidad matada

    Args:
        args: Argumentos con:
            - force (bool): Usar SIGKILL en lugar de SIGTERM
            - yes (bool): Skip confirmación

    Note:
        Procesos protegidos (PostgreSQL, etc) son automáticamente
        excluidos y no se matan
    """
    dev_ports = PortManager.get_dev_ports()

    if not dev_ports:
        print('No development ports to kill')
        return

    print(f'Found {len(dev_ports)} development ports')

    # Pedir confirmación (a menos que -y)
    if not args.yes:
        for port in dev_ports:
            print(f'  - {port.port}: {port.process_name}')

        response = input('\nKill all these processes? [y/N]: ')
        if response.lower() != 'y':
            print('Cancelled')
            sys.exit(0)

    # Matar todos (excepto protegidos)
    killed = PortManager.kill_all_dev_ports(force=args.force)

    print(f'\nKilled {killed} processes')


def port_info(args):
    """
    Muestra información detallada de un puerto específico.

    Incluye:
    - Puerto y protocolo
    - PID y nombre del proceso
    - Línea de comando completa
    - Estado de la conexión
    - Si está protegido
    - Si es puerto de desarrollo

    Args:
        args: Argumentos con:
            - port (int): Número de puerto a consultar

    Exit codes:
        0 - Éxito
        1 - Puerto no encontrado
    """
    port = args.port
    port_info = PortManager.get_port_info(port)

    if not port_info:
        print(f'No process found on port {port}')
        sys.exit(1)

    # Mostrar toda la información disponible
    print(f'\nPort Information:')
    print(f'  Port:         {port_info.port}')
    print(f'  Protocol:     {port_info.protocol}')
    print(f'  PID:          {port_info.pid}')
    print(f'  Process:      {port_info.process_name}')
    print(f'  Command:      {port_info.cmdline}')
    print(f'  Status:       {port_info.status}')
    print(f'  Protected:    {"Yes" if port_info.is_protected else "No"}')
    print(f'  Dev Port:     {"Yes" if PortManager.is_dev_port(port) else "No"}')
    print()


def main():
    """
    Entry point del CLI.

    Parsea argumentos y ejecuta el comando correspondiente.
    Maneja errores y señales (Ctrl+C) gracefully.

    Exit codes:
        0   - Éxito
        1   - Error general
        130 - Interrupted (Ctrl+C)
    """
    # Parser principal
    parser = argparse.ArgumentParser(
        description='Port Killer - Manage and kill processes on ports',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Comando: list
    # Lista todos los puertos activos
    parser_list = subparsers.add_parser('list', help='List all active ports')
    parser_list.set_defaults(func=list_ports)

    # Comando: list-dev
    # Lista solo puertos de desarrollo
    parser_list_dev = subparsers.add_parser('list-dev', help='List development ports only')
    parser_list_dev.set_defaults(func=list_dev_ports)

    # Comando: kill PORT
    # Mata proceso en puerto específico
    parser_kill = subparsers.add_parser('kill', help='Kill process on specific port')
    parser_kill.add_argument('port', type=int, help='Port number')
    parser_kill.add_argument('-f', '--force', action='store_true', help='Force kill (SIGKILL)')
    parser_kill.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
    parser_kill.set_defaults(func=kill_port)

    # Comando: kill-dev
    # Mata todos los puertos de desarrollo
    parser_kill_dev = subparsers.add_parser('kill-dev', help='Kill all development ports')
    parser_kill_dev.add_argument('-f', '--force', action='store_true', help='Force kill (SIGKILL)')
    parser_kill_dev.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
    parser_kill_dev.set_defaults(func=kill_all_dev)

    # Comando: info PORT
    # Muestra información detallada
    parser_info = subparsers.add_parser('info', help='Show detailed port information')
    parser_info.add_argument('port', type=int, help='Port number')
    parser_info.set_defaults(func=port_info)

    # Parsear argumentos
    args = parser.parse_args()

    # Si no hay comando, mostrar help
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Ejecutar comando con manejo de errores
    try:
        args.func(args)
    except KeyboardInterrupt:
        # Ctrl+C presionado
        print('\n\nInterrupted')
        sys.exit(130)
    except Exception as e:
        # Error inesperado
        print(f'Error: {e}')
        sys.exit(1)


# Entry point
if __name__ == '__main__':
    main()
