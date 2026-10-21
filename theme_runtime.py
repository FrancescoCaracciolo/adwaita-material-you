"""Write Adwaita Material You colors without replacing user GTK CSS.

GTK applications read the user stylesheet once and cache it.  ChromaLeon
(https://github.com/Fabito02/ChromaLeon) works around that by keeping the
generated colors in an imported stylesheet and toggling high-contrast briefly,
which makes GTK rebuild its stylesheet cache.  This module provides the same
behavior for this project.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping


GTK_VERSIONS = ("gtk-4.0", "gtk-3.0")
START_MARKER = "/* AdwaitaMaterialYou Start */"
END_MARKER = "/* AdwaitaMaterialYou End */"
_IMPORT_BLOCK = re.compile(
    rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\n?",
    re.DOTALL,
)
_A11Y_SCHEMA = "org.gnome.desktop.a11y.interface"


def render_css(base_preset: Mapping[str, object]) -> str:
    """Render a mapped preset as GTK ``@define-color`` declarations."""

    lines: list[str] = []
    variables = base_preset.get("variables", {})
    palette = base_preset.get("palette", {})

    for key, value in variables.items():
        lines.append(f"@define-color {key} {value};")

    for prefix, colors in palette.items():
        for key, value in colors.items():
            lines.append(f"@define-color {prefix}{key} {value};")

    return "\n".join(lines) + ("\n" if lines else "")


def _atomic_write(path: Path, content: str) -> None:
    """Replace a file atomically, keeping partial CSS out of GTK reads."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _install_import(gtk_css: Path) -> None:
    """Add or replace our import block while preserving other GTK CSS."""

    current = gtk_css.read_text(encoding="utf-8") if gtk_css.exists() else ""
    without_ours = _IMPORT_BLOCK.sub("", current).rstrip()
    block = (
        f'{START_MARKER}\n'
        '@import url("custom-accent.css");\n'
        f"{END_MARKER}\n"
    )
    updated = f"{without_ours}\n\n{block}" if without_ours else block

    if updated != current:
        _atomic_write(gtk_css, updated)


def _gsettings(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gsettings", *args],
        check=True,
        text=True,
        capture_output=capture_output,
    )


def reload_gtk_stylesheets() -> bool:
    """Ask running GTK applications to reload their user stylesheets.

    GTK 4 does not reliably notice a changed imported file by itself.  A
    high-contrast setting transition is the notification mechanism used by
    ChromaLeon.  If ``gsettings`` is unavailable (for example in a headless
    build or a non-GNOME session), the CSS is still written and this returns
    ``False``.
    """

    try:
        result = _gsettings(
            "get", _A11Y_SCHEMA, "high-contrast", capture_output=True
        )
        value = result.stdout.strip().lower()
        if value not in {"true", "false"}:
            return False
        current = value == "true"
        try:
            _gsettings(
                "set", _A11Y_SCHEMA, "high-contrast", str(not current).lower()
            )
            # Complete the transition before restoring the user's setting.  This
            # mirrors ChromaLeon's get-between-set calls and helps GTK process
            # both setting notifications in order.
            _gsettings(
                "get", _A11Y_SCHEMA, "high-contrast", capture_output=True
            )
            return True
        finally:
            # Never leave accessibility settings changed if the notification
            # command fails partway through.
            _gsettings("set", _A11Y_SCHEMA, "high-contrast", str(current).lower())
    except (OSError, subprocess.CalledProcessError):
        return False


def apply_live_gtk_theme(
    base_preset: Mapping[str, object],
    *,
    config_dir: str | os.PathLike[str] | None = None,
    reload: bool = True,
) -> bool:
    """Install a generated preset for GTK 3 and GTK 4.

    ``config_dir`` is injectable for tests and callers using a custom config
    root.  The return value says whether the live reload notification ran;
    writing the files succeeds independently of that notification.
    """

    root = Path(config_dir).expanduser() if config_dir else Path.home() / ".config"
    css = render_css(base_preset)

    for version in GTK_VERSIONS:
        version_dir = root / version
        _atomic_write(version_dir / "custom-accent.css", css)
        _install_import(version_dir / "gtk.css")

    return reload_gtk_stylesheets() if reload else False
