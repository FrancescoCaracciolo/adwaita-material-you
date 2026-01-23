pkgname=adwaita-material-you
pkgver=0.1.0
pkgrel=1
pkgdesc="Generate and apply GTK4 themes based on a color or an image"
arch=('any')
url="https://github.com/francescocaracciolo/adwaita-material-you"
license=('GPL')
depends=('python-rich' 'python-pillow' 'python-gobject' 'python-pydantic' 'python-regex' 'python-numpy')
makedepends=('git')
source=("git+$url.git")
sha256sums=('SKIP')

package() {
    cd "$pkgname"

    install -Dm755 main.py "$pkgdir/usr/lib/adwaita-material-you/main.py"

    for pyfile in color_utils.py map_colors.py transformers.py extension_integration.py; do
        install -Dm644 "$pyfile" "$pkgdir/usr/lib/adwaita-material-you/$pyfile"
    done

    cp -r material_color_utilities_python "$pkgdir/usr/lib/adwaita-material-you/"

    install -Dm644 base_presets.json "$pkgdir/usr/lib/adwaita-material-you/base_presets.json"
    install -Dm644 color_mappings.json "$pkgdir/usr/lib/adwaita-material-you/color_mappings.json"

    install -Dm755 /dev/stdin "$pkgdir/usr/bin/adwmu" <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/adwaita-material-you")
exec(open("/usr/lib/adwaita-material-you/main.py").read())
EOF
}
