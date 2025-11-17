#!/bin/bash
# Desinstalador de Port Killer

echo "Port Killer - Desinstalador"
echo "============================"
echo ""

# Matar procesos corriendo
echo "Cerrando Port Killer si está corriendo..."
pkill -f "port-killer/src/main.py" 2>/dev/null || true
sleep 1

echo ""
echo "Desinstalando Port Killer..."

# Eliminar enlace simbólico del CLI
if [ -L "$HOME/.local/bin/port-killer" ]; then
    echo "  - Eliminando CLI de ~/.local/bin/port-killer"
    rm -f "$HOME/.local/bin/port-killer"
fi

# Eliminar entrada de escritorio
if [ -f "$HOME/.local/share/applications/port-killer.desktop" ]; then
    echo "  - Eliminando entrada de escritorio"
    rm -f "$HOME/.local/share/applications/port-killer.desktop"
fi

# El icono se usa desde el tema del sistema, no hay nada que eliminar

# Actualizar caches para que desaparezca inmediatamente
echo "  - Actualizando caches del sistema..."
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# Forzar actualización del menú (GNOME/KDE)
if command -v gio &> /dev/null; then
    gio trash "$HOME/.local/share/applications/port-killer.desktop" 2>/dev/null || true
fi

echo ""
echo "Port Killer ha sido desinstalado"
echo ""
echo "NOTA: Si sigue apareciendo en el menú, cierra sesión y vuelve a entrar"
echo "      o ejecuta: killall -HUP nautilus gnome-shell"
echo ""
echo "Para eliminar el directorio del proyecto manualmente:"
echo "  rm -rf $(cd "$(dirname "$0")" && pwd)"
