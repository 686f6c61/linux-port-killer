#!/usr/bin/env python3
"""
Port Manager - Detección y gestión de procesos en puertos

Este módulo proporciona la funcionalidad core para detectar, analizar y
gestionar procesos que están escuchando en puertos de red.

Author: 686f6c61
Repository: https://github.com/686f6c61/linux-port-killer
Version: 1.0.0
Date: 2025-01-17
License: MIT
"""

import psutil
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PortProcess:
    """
    Dataclass que representa un proceso escuchando en un puerto.

    Attributes:
        port (int): Número de puerto (1-65535)
        pid (int): Process ID del sistema
        process_name (str): Nombre del proceso (ej: 'python3', 'node')
        cmdline (str): Línea de comando completa del proceso
        protocol (str): Protocolo de red ('TCP' o 'UDP')
        status (str): Estado de la conexión (normalmente 'LISTEN')
        is_protected (bool): True si es un servicio crítico (DB, web server)
    """
    port: int
    pid: int
    process_name: str
    cmdline: str
    protocol: str
    status: str
    is_protected: bool = False


class PortManager:
    """
    Gestor principal para operaciones con puertos y procesos.

    Esta clase proporciona métodos estáticos para:
    - Detectar puertos activos en el sistema
    - Identificar puertos de desarrollo
    - Humanizar comandos crípticos a descripciones legibles
    - Matar procesos de forma segura (SIGTERM → SIGKILL)
    """

    # Procesos protegidos que requieren confirmación antes de matar
    # Estos son servicios críticos que normalmente no deberían terminarse
    PROTECTED_PROCESSES = {
        'postgres', 'postgresql', 'mysqld', 'mysql',
        'redis-server', 'mongod', 'nginx', 'apache2'
    }

    # Rangos de puertos comunes para desarrollo web
    # Estos se usan para filtrar y destacar puertos de desarrollo
    DEV_PORT_RANGES = [
        (3000, 3999),  # Node.js, React, Vue, Next.js
        (4200, 4299),  # Angular CLI
        (5000, 5999),  # Flask, Django Dev Server
        (8000, 8999),  # Django, FastAPI, Go servers
        (5173, 5173),  # Vite dev server
        (8080, 8080),  # Tomcat, Spring Boot
    ]

    @staticmethod
    def get_listening_ports() -> List[PortProcess]:
        """
        Obtiene todos los procesos que están escuchando en puertos.

        Usa psutil para leer las conexiones de red del sistema y filtrar
        solo aquellas en estado LISTEN (servidores activos).

        Returns:
            List[PortProcess]: Lista de procesos ordenados por número de puerto

        Note:
            - Solo procesos en estado LISTEN son incluidos
            - Procesos sin PID o puerto son ignorados
            - Procesos inaccesibles (sin permisos) son ignorados silenciosamente
        """
        ports = []

        # Iterar sobre todas las conexiones inet (IPv4/IPv6)
        for conn in psutil.net_connections(kind='inet'):
            # Solo procesos en estado LISTEN (servidores)
            if conn.status != 'LISTEN':
                continue

            # Solo si tiene puerto local válido
            if not conn.laddr or not conn.laddr.port:
                continue

            try:
                # Obtener información del proceso
                process = psutil.Process(conn.pid) if conn.pid else None

                if process:
                    cmdline = ' '.join(process.cmdline())
                    process_name = process.name()

                    # Humanizar comandos crípticos a descripciones legibles
                    cmdline_human = PortManager._humanize_cmdline(cmdline, process_name)

                    # Detectar si es un proceso protegido (DB, web server, etc)
                    is_protected = any(
                        protected in process_name.lower()
                        for protected in PortManager.PROTECTED_PROCESSES
                    )

                    # Crear objeto PortProcess
                    port_proc = PortProcess(
                        port=conn.laddr.port,
                        pid=conn.pid,
                        process_name=process_name,
                        cmdline=cmdline_human[:150],  # Limitar longitud a 150 chars
                        protocol='TCP' if conn.type == 1 else 'UDP',
                        status=conn.status,
                        is_protected=is_protected
                    )
                    ports.append(port_proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Ignorar procesos que ya no existen o no tenemos permisos
                continue

        # Ordenar por número de puerto (ascendente)
        return sorted(ports, key=lambda x: x.port)

    @staticmethod
    def _humanize_cmdline(cmdline: str, process_name: str) -> str:
        """
        Convierte comandos crípticos en descripciones legibles para humanos.

        Muchos procesos modernos (especialmente Electron/VSCode) tienen
        líneas de comando muy largas y crípticas. Este método las detecta
        y convierte en descripciones claras.

        Args:
            cmdline (str): Línea de comando completa del proceso
            process_name (str): Nombre del proceso

        Returns:
            str: Descripción humanizada o cmdline original si no se reconoce

        Examples:
            '/proc/self/exe --type=utility' → 'VSCode - Utility Process'
            'python3 manage.py runserver' → 'Django Dev Server'
            'node node_modules/.bin/vite' → 'Vite Dev Server'
        """

        # VSCode / Electron apps
        # VSCode usa /proc/self/exe con diferentes tipos de procesos
        if 'code' in process_name.lower() or '/snap/code/' in cmdline:
            if '/proc/self/exe' in cmdline and 'type=utility' in cmdline:
                return 'VSCode - Utility Process'
            elif '/proc/self/exe' in cmdline and 'type=renderer' in cmdline:
                return 'VSCode - Renderer Process'
            elif 'pylance' in cmdline.lower() or 'vscode-pylance' in cmdline:
                return 'VSCode - Pylance Language Server'
            elif 'extensions' in cmdline and '.js' in cmdline:
                # Detectar extensiones específicas de VSCode
                if 'ms-python' in cmdline:
                    return 'VSCode - Python Extension'
                elif 'ms-vscode' in cmdline:
                    return 'VSCode - Extension Server'
                return 'VSCode - Extension Process'

        # Procesos Electron genéricos
        if '/proc/self/exe' in cmdline and 'type=utility' in cmdline:
            return f'{process_name} - Utility Process'

        if '/proc/self/exe' in cmdline and 'type=renderer' in cmdline:
            return f'{process_name} - Renderer Process'

        # Node.js servers comunes
        if 'node' in process_name.lower():
            if 'vite' in cmdline.lower():
                return 'Vite Dev Server'
            elif 'webpack' in cmdline.lower():
                return 'Webpack Dev Server'
            elif 'next' in cmdline.lower():
                return 'Next.js Dev Server'
            elif 'react-scripts' in cmdline.lower():
                return 'React Dev Server'
            elif 'vue-cli-service' in cmdline.lower():
                return 'Vue Dev Server'
            elif 'nodemon' in cmdline.lower():
                return 'Nodemon - ' + cmdline.split()[-1] if cmdline else 'Nodemon'
            elif 'ts-node' in cmdline.lower():
                return 'TypeScript Node - ' + cmdline.split()[-1] if cmdline else 'TypeScript Node'

        # Python servers
        if 'python' in process_name.lower():
            if 'manage.py runserver' in cmdline:
                return 'Django Dev Server'
            elif 'flask run' in cmdline or 'app.py' in cmdline:
                return 'Flask Dev Server'
            elif 'uvicorn' in cmdline:
                return 'Uvicorn (FastAPI/Starlette)'
            elif 'gunicorn' in cmdline:
                return 'Gunicorn WSGI Server'

        # Java/Spring servers
        if 'java' in process_name.lower():
            if 'spring' in cmdline.lower():
                return 'Spring Boot Application'
            elif '.jar' in cmdline:
                # Extraer nombre del JAR
                jar_name = [p for p in cmdline.split() if '.jar' in p]
                return f'Java Application - {jar_name[0] if jar_name else "jar"}'

        # Docker
        if 'docker-proxy' in process_name:
            return 'Docker Container Port Proxy'

        # Default: retornar cmdline original sin modificar
        return cmdline

    @staticmethod
    def is_dev_port(port: int) -> bool:
        """
        Verifica si un puerto está en el rango de desarrollo.

        Args:
            port (int): Número de puerto a verificar

        Returns:
            bool: True si está en algún rango de desarrollo, False en caso contrario

        Examples:
            is_dev_port(3000) → True (Node.js)
            is_dev_port(5432) → False (PostgreSQL)
        """
        return any(
            start <= port <= end
            for start, end in PortManager.DEV_PORT_RANGES
        )

    @staticmethod
    def get_dev_ports() -> List[PortProcess]:
        """
        Obtiene solo los puertos de desarrollo.

        Filtra los puertos activos para mostrar únicamente aquellos
        que están en rangos típicos de desarrollo web.

        Returns:
            List[PortProcess]: Lista de puertos de desarrollo
        """
        all_ports = PortManager.get_listening_ports()
        return [p for p in all_ports if PortManager.is_dev_port(p.port)]

    @staticmethod
    def kill_process(pid: int, force: bool = False) -> bool:
        """
        Mata un proceso por PID de forma segura.

        Estrategia de terminación:
        1. Intenta SIGTERM (señal 15) - permite cleanup graceful
        2. Espera hasta 3 segundos a que termine
        3. Si falla o force=True, usa SIGKILL (señal 9) - terminación forzada

        Args:
            pid (int): Process ID a matar
            force (bool): Si True, usa SIGKILL directamente sin esperar

        Returns:
            bool: True si se mató exitosamente, False en caso de error

        Note:
            - SIGTERM permite al proceso hacer cleanup (cerrar archivos, etc)
            - SIGKILL es instantáneo pero no permite cleanup
            - Si el proceso no responde a SIGTERM, automáticamente usa SIGKILL
        """
        try:
            process = psutil.Process(pid)

            if force:
                # Matar inmediatamente con SIGKILL
                process.kill()
            else:
                # Intentar terminación graceful con SIGTERM
                process.terminate()

            # Esperar hasta 3 segundos a que termine
            process.wait(timeout=3)
            return True

        except psutil.NoSuchProcess:
            # El proceso ya no existe (probablemente ya terminó)
            return True
        except psutil.AccessDenied:
            # Sin permisos para matar este proceso
            return False
        except psutil.TimeoutExpired:
            # El proceso no terminó con SIGTERM, forzar SIGKILL
            if not force:
                return PortManager.kill_process(pid, force=True)
            return False

    @staticmethod
    def kill_port(port: int, force: bool = False) -> bool:
        """
        Mata el proceso escuchando en un puerto específico.

        Args:
            port (int): Número de puerto
            force (bool): Usar SIGKILL en lugar de SIGTERM

        Returns:
            bool: True si se mató exitosamente, False si no se encontró o falló
        """
        ports = PortManager.get_listening_ports()

        # Buscar el proceso en ese puerto
        for port_proc in ports:
            if port_proc.port == port:
                return PortManager.kill_process(port_proc.pid, force)

        # Puerto no encontrado
        return False

    @staticmethod
    def kill_all_dev_ports(force: bool = False) -> int:
        """
        Mata todos los procesos en puertos de desarrollo.

        Itera sobre todos los puertos de desarrollo y termina sus procesos,
        excepto aquellos marcados como protegidos.

        Args:
            force (bool): Usar SIGKILL en lugar de SIGTERM

        Returns:
            int: Cantidad de procesos matados exitosamente

        Note:
            Los procesos protegidos (PostgreSQL, etc) son ignorados
        """
        dev_ports = PortManager.get_dev_ports()
        killed_count = 0

        for port_proc in dev_ports:
            # Saltar procesos protegidos
            if not port_proc.is_protected:
                if PortManager.kill_process(port_proc.pid, force):
                    killed_count += 1

        return killed_count

    @staticmethod
    def get_port_info(port: int) -> Optional[PortProcess]:
        """
        Obtiene información detallada de un puerto específico.

        Args:
            port (int): Número de puerto a consultar

        Returns:
            Optional[PortProcess]: Info del puerto o None si no existe
        """
        ports = PortManager.get_listening_ports()

        for port_proc in ports:
            if port_proc.port == port:
                return port_proc

        return None


# Ejecución directa para testing
if __name__ == '__main__':
    print("Port Manager - Test de funcionalidad\n")
    print("Puertos activos en el sistema:\n")
    print(f"{'Puerto':<8} {'Proceso':<20} {'PID':<8} {'Protocolo':<10} {'Estado':<10}")
    print("-" * 70)

    for port in PortManager.get_listening_ports():
        protected = "[PROTECTED]" if port.is_protected else ""
        dev = "[DEV]" if PortManager.is_dev_port(port.port) else ""

        print(f"{port.port:<8} {port.process_name:<20} {port.pid:<8} "
              f"{port.protocol:<10} {protected} {dev}")

    print(f"\nTotal: {len(PortManager.get_listening_ports())} puertos")
    print(f"Dev ports: {len(PortManager.get_dev_ports())} puertos")
