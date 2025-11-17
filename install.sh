#!/bin/bash
# Instalador de Port Killer

set -e

echo "Port Killer - Instalador"
echo "========================="
echo ""

# Detectar distribución
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "No se pudo detectar la distribución"
    exit 1
fi

echo "Sistema detectado: $OS"
echo ""

# Instalar dependencias del sistema
echo "Instalando dependencias del sistema..."

case $OS in
    ubuntu|debian|pop)
        sudo apt update
        sudo apt install -y \
            python3 \
            python3-pip \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-4.0 \
            gir1.2-adw-1 \
            gir1.2-appindicator3-0.1 \
            gnome-shell-extension-appindicator
        ;;
    fedora)
        sudo dnf install -y \
            python3 \
            python3-pip \
            python3-gobject \
            gtk4 \
            libadwaita \
            libappindicator-gtk3
        ;;
    arch|manjaro)
        sudo pacman -S --noconfirm \
            python \
            python-pip \
            python-gobject \
            gtk4 \
            libadwaita \
            libappindicator-gtk3
        ;;
    *)
        echo "Distribución no soportada: $OS"
        echo "Por favor instala manualmente las dependencias GTK4 y libadwaita"
        ;;
esac

echo ""
echo "Instalando dependencias Python..."
pip3 install --user -r requirements.txt --break-system-packages 2>/dev/null || \
    pip3 install --user -r requirements.txt || \
    python3 -m pip install --user -r requirements.txt --break-system-packages

echo ""
echo "Haciendo ejecutables los scripts..."
chmod +x src/main.py
chmod +x src/cli.py

echo ""
echo "Creando enlace simbólico para CLI..."
mkdir -p ~/.local/bin
ln -sf "$(pwd)/src/cli.py" ~/.local/bin/port-killer

# Verificar si ~/.local/bin está en PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "IMPORTANTE: Agrega ~/.local/bin a tu PATH"
    echo "Añade esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo ""
echo "Instalando entrada de escritorio..."
chmod +x port-killer.desktop
mkdir -p ~/.local/share/applications
mkdir -p ~/.local/share/icons/hicolor/256x256/apps

# Obtener ruta absoluta del proyecto
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# El icono se usa desde el tema del sistema (network-transmit-receive)
# No necesitamos copiar ningún archivo de icono

# Crear desktop entry con rutas absolutas
cat > ~/.local/share/applications/port-killer.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Port Killer
GenericName=Port Manager
Comment=Kill development server ports with ease
Exec=sh -c 'cd $PROJECT_DIR && python3 src/tray_standalone.py &'
Icon=network-transmit-receive
Terminal=false
Categories=Development;Utility;System;
Keywords=port;network;kill;process;development;server;
StartupNotify=false
X-GNOME-Autostart-enabled=false
EOF

chmod +x ~/.local/share/applications/port-killer.desktop

# Actualizar cache de iconos y aplicaciones
gtk-update-icon-cache ~/.local/share/icons/hicolor/ 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true

echo ""
echo "Habilitando extensión AppIndicator para system tray..."
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com 2>/dev/null || \
gnome-extensions enable ubuntu-appindicators@ubuntu.com 2>/dev/null || true

echo ""
echo "============================================"
echo "Instalación completada!"
echo "============================================"
echo ""
echo "IMPORTANTE: Para que el icono aparezca en la barra superior:"
echo "  1. Cierra sesión y vuelve a entrar"
echo "  2. O presiona Alt+F2, escribe 'r', Enter"
echo ""
echo "Ejecutar:"
echo "  GUI: Busca 'Port Killer' en el menú de aplicaciones"
echo "  CLI: port-killer list"
echo ""
