#!/bin/bash

cd "$(dirname "$0")"

sudo install -Dm755 main.py "/usr/lib/adwaita-material-you/main.py"

for pyfile in color_utils.py map_colors.py transformers.py extension_integration.py; do
    sudo install -Dm644 "$pyfile" "/usr/lib/adwaita-material-you/$pyfile"
done

sudo cp -r material_color_utilities_python "/usr/lib/adwaita-material-you/"

sudo install -Dm644 base_presets.json "/usr/lib/adwaita-material-you/base_presets.json"
sudo install -Dm644 color_mappings.json "/usr/lib/adwaita-material-you/color_mappings.json"

sudo install -Dm755 /dev/stdin "/usr/bin/adwmu" <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/adwaita-material-you")
exec(open("/usr/lib/adwaita-material-you/main.py").read())
EOF

echo "Installation complete. You can now run 'adwmu' from anywhere."
echo "Make sure you have the required Python packages installed:"
echo "  rich, pillow, pygobject, material, pydantic, regex, numpy, materialyoucolor"
