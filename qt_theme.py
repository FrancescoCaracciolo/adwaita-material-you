"""Generate and apply Qt themes that look like kde-material-you-colors.

The color roles and the KDE color scheme layout follow
https://github.com/luisbocanegra/kde-material-you-colors so a Qt application
looks the same as it would under that project.  The same colors are then
exported to the other Qt configuration systems:

* ``kde``: a KDE ``.colors`` scheme (applied with ``plasma-apply-colorscheme``
  or merged into ``kdeglobals`` outside Plasma)
* ``qt5ct`` / ``qt6ct``: a palette file and the ``[Appearance]`` settings
* ``kvantum``: a theme recolored from an installed Kvantum base theme

Everything honors ``XDG_CONFIG_HOME`` and ``XDG_DATA_HOME``.
"""

from __future__ import annotations

import colorsys
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from materialyoucolor.blend import Blend
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.hct import Hct
from materialyoucolor.palettes.tonal_palette import TonalPalette
from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad
from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant

from theme_runtime import atomic_write


TARGETS = ("kde", "qt5ct", "qt6ct", "kvantum")
THEME_NAME = "AdwaitaMaterialYou"
KVANTUM_DEFAULT_BASE = {True: "KvAdaptaDark", False: "KvAdapta"}

VARIANT_SCHEMES = {
    "default": SchemeTonalSpot,
    "vibrant": SchemeVibrant,
    "expressive": SchemeExpressive,
    "fruit salad": SchemeFruitSalad,
    "muted": SchemeNeutral,
}

# Semantic text colors taken from the Breeze color scheme, as upstream does.
_TEXT_STATES = {
    "link": 0xFF2980B9,
    "visited": 0xFF9B59B6,
    "negative": 0xFFDA4453,
    "neutral": 0xFFF67400,
    "positive": 0xFF27AE60,
}

_PALETTE_ROLES = (
    "WindowText", "Button", "Light", "Midlight", "Dark", "Mid", "Text",
    "BrightText", "ButtonText", "Base", "Window", "Shadow", "Highlight",
    "HighlightedText", "Link", "LinkVisited", "AlternateBase", "NoRole",
    "ToolTipBase", "ToolTipText", "PlaceholderText",
)  # fmt: skip

_SECTION = re.compile(r"^\[(.*)\]\s*$")
_SVG_HEX = re.compile(r'(?<!href=")(?<=[:="\' ])#([0-9a-fA-F]{6})(?![0-9a-fA-F])')
_NEUTRAL_CHROMA = 12.0
_ACCENT_HUE_RANGE = 30.0


class QtThemeError(Exception):
    """Raised when a Qt target cannot be generated or applied."""


@dataclass
class QtColors:
    """Material You roles for one scheme, plus what recoloring needs."""

    is_dark: bool
    roles: dict[str, str]
    extras: dict[str, dict[str, str]]
    scheme: object


def _hex(argb: int) -> str:
    return "#{:06x}".format(argb & 0xFFFFFF)


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mix(first: str, second: str, amount: float) -> str:
    a, b = _rgb(first), _rgb(second)
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x + (y - x) * amount) for x, y in zip(a, b))
    )


def _lighter(color: str, factor: int = 150) -> str:
    """QColor::lighter, so derived palette roles match what Qt would compute."""

    r, g, b = (x / 255 for x in _rgb(color))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v = v * factor / 100
    if v > 1:
        s = max(0.0, s - (v - 1))
        v = 1.0
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
    )


def _darker(color: str, factor: int = 200) -> str:
    r, g, b = (x / 255 for x in _rgb(color))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x * 255) for x in colorsys.hsv_to_rgb(h, s, v * 100 / factor))
    )


def _qt_argb(color: str) -> str:
    return "#ff" + color.lstrip("#")


def generate_qt_colors(
    source_argb: int,
    variant: str,
    is_dark: bool,
    *,
    contrast_level: float = 0.0,
    chroma_multiplier: float = 1.0,
    tone_multiplier: float = 1.0,
) -> QtColors:
    """Build every Material You role used by the Qt exporters."""

    try:
        scheme_class = VARIANT_SCHEMES[variant]
    except KeyError:
        raise QtThemeError(
            f"Unknown variant '{variant}', expected one of: "
            + ", ".join(VARIANT_SCHEMES)
        ) from None

    source = Hct.from_int(source_argb)

    def make_scheme():
        return scheme_class(source, is_dark, contrast_level)

    scheme = make_scheme()
    roles: dict[str, str] = {}
    for name, role in vars(MaterialDynamicColors).items():
        if not hasattr(role, "get_hct"):
            continue
        hct = role.get_hct(scheme)
        if role.is_background is True:
            hct.tone = int(
                hct.tone * _clip(tone_multiplier, 0.0 if is_dark else 0.5, 1.5)
            )
        hct.chroma = hct.chroma * _clip(chroma_multiplier, 0, 10)
        roles[name] = _hex(hct.to_int())

    # Semantic colors reuse the error roles with a palette built from the
    # state color, harmonized towards the source.  Each needs a fresh scheme
    # because dynamic colors cache their result per scheme object.
    extras: dict[str, dict[str, str]] = {}
    for state, argb in _TEXT_STATES.items():
        state_scheme = make_scheme()
        state_scheme.error_palette = TonalPalette.from_int(
            Blend.harmonize(argb, source_argb)
        )
        extras[state] = {
            "color": _hex(MaterialDynamicColors.error.get_hct(state_scheme).to_int()),
            "container": _hex(
                MaterialDynamicColors.errorContainer.get_hct(state_scheme).to_int()
            ),
        }

    return QtColors(is_dark=is_dark, roles=roles, extras=extras, scheme=scheme)


def _fixed_foregrounds(x: Mapping[str, dict[str, str]], key: str) -> dict[str, str]:
    return {
        "ForegroundLink": x["link"][key],
        "ForegroundNegative": x["negative"][key],
        "ForegroundNeutral": x["neutral"][key],
        "ForegroundPositive": x["positive"][key],
        "ForegroundVisited": x["visited"][key],
    }


def kde_color_sets(
    colors: QtColors, frame_contrast: float = 0.2
) -> dict[str, dict[str, str]]:
    """Return the KDE color scheme sections, in upstream's layout."""

    c, x, dark = colors.roles, colors.extras, colors.is_dark

    def colorset(background, alternate, fg_normal, fg_active, decoration, hover):
        return dict(
            sorted(
                {
                    "BackgroundAlternate": alternate,
                    "BackgroundNormal": background,
                    "DecorationFocus": decoration,
                    "DecorationHover": hover,
                    "ForegroundActive": fg_active,
                    "ForegroundInactive": c["outline"],
                    "ForegroundNormal": fg_normal,
                    **_fixed_foregrounds(x, "color"),
                }.items()
            )
        )

    primary = c["primary"]
    header = colorset(
        c["surfaceContainer"], c["surfaceContainer"],
        c["onSurfaceVariant"], c["inverseSurface"], primary, primary,
    )  # fmt: skip
    selection = {
        **colorset(
            primary, primary, c["onPrimary"], c["onPrimary"], primary, c["secondary"]
        ),
        "ForegroundInactive": c["onPrimary"],
        **_fixed_foregrounds(x, "container"),
    }
    view_hover = c["inversePrimary"] if dark else c["secondaryFixed"]
    effect_color = c["surfaceContainer"]

    return {
        "ColorEffects:Disabled": {
            "Color": effect_color,
            "ColorAmount": "0.5",
            "ColorEffect": "3",
            "ContrastAmount": "0",
            "ContrastEffect": "0",
            "IntensityAmount": "0",
            "IntensityEffect": "0",
        },
        "ColorEffects:Inactive": {
            "ChangeSelectionColor": "true",
            "Color": c["surfaceContainerLowest"],
            "ColorAmount": "0.025",
            "ColorEffect": "0",
            "ContrastAmount": "0.1",
            "ContrastEffect": "0",
            "Enable": "true" if dark else "false",
            "IntensityAmount": "0",
            "IntensityEffect": "0",
        },
        "Colors:Button": colorset(
            c["surfaceContainerHigh"], c["surfaceVariant"],
            c["onSurface"], c["onSurface"], primary, primary,
        ),  # fmt: skip
        "Colors:Complementary": colorset(
            c["surfaceContainer"], c["surface"],
            c["onSurfaceVariant"], c["inverseSurface"], primary, primary,
        ),  # fmt: skip
        "Colors:Header": header,
        "Colors:Header][Inactive": dict(header),
        "Colors:Selection": selection,
        "Colors:Tooltip": colorset(
            c["surfaceContainer"], c["surfaceVariant"],
            c["onSurface"], c["onSurface"], primary, primary,
        ),  # fmt: skip
        "Colors:View": colorset(
            c["surfaceDim"] if dark else c["surfaceBright"], c["surfaceContainer"],
            c["onSurface"], c["inverseSurface"], primary, view_hover,
        ),  # fmt: skip
        "Colors:Window": colorset(
            c["surfaceContainer"], c["surfaceVariant"],
            c["onSurfaceVariant"], x["link"]["color"], primary, primary,
        ),  # fmt: skip
        "General": {
            "ColorScheme": THEME_NAME + ("Dark" if dark else "Light"),
            "Name": "Adwaita Material You " + ("Dark" if dark else "Light"),
            "shadeSortColumn": "true",
        },
        "KDE": {"contrast": "4", "frameContrast": str(frame_contrast)},
        "WM": {
            "activeBackground": "#ff" + c["surfaceContainerHighest"].lstrip("#"),
            "activeBlend": "252,252,252" if dark else "227,229,231",
            "activeForeground": c["onSurface"],
            "inactiveBackground": "#ff" + c["secondaryContainer"].lstrip("#"),
            "inactiveBlend": "161,169,177" if dark else "239,240,241",
            "inactiveForeground": (
                c["onSecondaryContainer"] if dark else c["onSurfaceVariant"]
            ),
        },
    }


def render_ini(sections: Mapping[str, Mapping[str, str]]) -> str:
    blocks = []
    for name, items in sections.items():
        lines = [f"[{name}]"] + [f"{key}={value}" for key, value in items.items()]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def qt_palette(
    sets: Mapping[str, Mapping[str, str]],
) -> tuple[dict[str, str], dict[str, str]]:
    """Map KDE color sets to QPalette roles (active, disabled).

    This is the same mapping KColorScheme uses when it builds a palette.
    """

    window, button, view = sets["Colors:Window"], sets["Colors:Button"], sets["Colors:View"]
    selection, tooltip = sets["Colors:Selection"], sets["Colors:Tooltip"]
    button_bg = button["BackgroundNormal"]

    active = {
        "WindowText": window["ForegroundNormal"],
        "Button": button_bg,
        "Light": _lighter(button_bg, 150),
        "Midlight": _lighter(button_bg, 125),
        "Dark": _darker(button_bg, 200),
        "Mid": _darker(button_bg, 150),
        "Text": view["ForegroundNormal"],
        "BrightText": view["ForegroundNegative"],
        "ButtonText": button["ForegroundNormal"],
        "Base": view["BackgroundNormal"],
        "Window": window["BackgroundNormal"],
        "Shadow": "#000000",
        "Highlight": selection["BackgroundNormal"],
        "HighlightedText": selection["ForegroundNormal"],
        "Link": view["ForegroundLink"],
        "LinkVisited": view["ForegroundVisited"],
        "AlternateBase": view["BackgroundAlternate"],
        "NoRole": window["BackgroundNormal"],
        "ToolTipBase": tooltip["BackgroundNormal"],
        "ToolTipText": tooltip["ForegroundNormal"],
        "PlaceholderText": view["ForegroundInactive"],
    }

    fade_to = sets["ColorEffects:Disabled"]["Color"]
    disabled = dict(active)
    for role in ("WindowText", "Text", "ButtonText", "HighlightedText"):
        disabled[role] = _mix(active[role], fade_to, 0.5)
    return active, disabled


def render_qtct_palette(active: Mapping[str, str], disabled: Mapping[str, str]) -> str:
    def row(palette: Mapping[str, str]) -> str:
        return ", ".join(_qt_argb(palette[role]) for role in _PALETTE_ROLES)

    return (
        "[ColorScheme]\n"
        f"active_colors={row(active)}\n"
        f"disabled_colors={row(disabled)}\n"
        f"inactive_colors={row(active)}\n"
    )


def set_ini_values(text: str, updates: Mapping[str, Mapping[str, str]]) -> str:
    """Set keys in an INI/KConfig text while leaving everything else as is."""

    pending = {section: dict(items) for section, items in updates.items()}
    out: list[str] = []
    section: str | None = None

    def flush() -> None:
        items = pending.pop(section, None) if section is not None else None
        if not items:
            return
        trailing = 0
        while out and not out[-1].strip():
            out.pop()
            trailing += 1
        out.extend(f"{key}={value}" for key, value in items.items())
        out.extend([""] * trailing)

    for line in text.splitlines():
        header = _SECTION.match(line)
        if header:
            flush()
            section = header.group(1)
            out.append(line)
            continue
        stripped = line.strip()
        if (
            section in pending
            and "=" in stripped
            and not stripped.startswith(("#", ";"))
        ):
            key = stripped.split("=", 1)[0].strip()
            if key in pending[section]:
                out.append(f"{key}={pending[section].pop(key)}")
                continue
        out.append(line)
    flush()

    for name, items in pending.items():
        if not items:
            continue
        if out and out[-1].strip():
            out.append("")
        out.append(f"[{name}]")
        out.extend(f"{key}={value}" for key, value in items.items())

    return "\n".join(out) + "\n"


def _update_ini_file(path: Path, updates: Mapping[str, Mapping[str, str]]) -> None:
    """Rewrite a settings file in place.

    Qt and KDE watch these files for modification; a rename would drop their
    inotify watch, so the file is truncated and rewritten instead.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(set_ini_values(current, updates), encoding="utf-8")


def notify_kconfig_changed(
    name: str, changes: Mapping[str, Mapping[str, str]]
) -> bool:
    """Tell running KDE applications that a KConfig file changed.

    This is the signal KConfig itself emits when it saves, and the one
    KConfigWatcher listens for.  Editing the file directly sends nothing, so
    without it Kirigami and KDE applications only see new colors on restart.
    Returns False when the session bus is not reachable.
    """

    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        # Nested groups such as "Colors:Header][Inactive" are joined with 0x1d.
        payload = {
            "\x1d".join(section.split("][")): [key.encode() for key in items]
            for section, items in changes.items()
        }
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.emit_signal(
            None,
            f"/{name}",
            "org.kde.kconfig.notify",
            "ConfigChanged",
            GLib.Variant("(a{saay})", (payload,)),
        )
        bus.flush_sync(None)
        return True
    except Exception:
        return False


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def detect_targets() -> list[str]:
    """Return the Qt targets that look installed on this system."""

    config = _config_home()
    checks = {
        "kde": shutil.which("plasma-apply-colorscheme") or (config / "kdeglobals").exists(),
        "qt5ct": shutil.which("qt5ct") or (config / "qt5ct").is_dir(),
        "qt6ct": shutil.which("qt6ct") or (config / "qt6ct").is_dir(),
        "kvantum": shutil.which("kvantummanager") or (config / "Kvantum").is_dir(),
    }
    return [target for target in TARGETS if checks[target]]


def parse_targets(value: str | None) -> list[str]:
    value = (value or "auto").strip().lower()
    if value == "all":
        return list(TARGETS)
    if value == "auto":
        detected = detect_targets()
        if not detected:
            raise QtThemeError(
                "No Qt theming tool detected (kde, qt5ct, qt6ct, kvantum); "
                "use --qt-targets to choose targets explicitly"
            )
        return detected
    targets = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in targets if item not in TARGETS]
    if unknown or not targets:
        raise QtThemeError(
            f"Unknown Qt target(s): {', '.join(unknown) or value}. "
            f"Valid targets: auto, all, {', '.join(TARGETS)}"
        )
    return list(dict.fromkeys(targets))


def _apply_kde(sets: Mapping[str, Mapping[str, str]], apply: bool) -> str:
    schemes = _data_home() / "color-schemes"
    name = sets["General"]["ColorScheme"]
    text = render_ini(sets)
    main_file, alternate_file = schemes / f"{name}.colors", schemes / f"{name}2.colors"
    # plasma-apply-colorscheme ignores a scheme that is already active, so a
    # second copy is applied first to force it to reload the real one.
    atomic_write(alternate_file, text)
    atomic_write(main_file, text)
    if not apply:
        return f"kde: scheme written to {main_file}"

    tool = shutil.which("plasma-apply-colorscheme")
    kdeglobals = _config_home() / "kdeglobals"
    if tool:
        subprocess.run([tool, str(alternate_file)], capture_output=True, check=False)
        try:
            subprocess.run(
                [tool, str(main_file)], capture_output=True, text=True, check=True
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise QtThemeError(f"plasma-apply-colorscheme failed: {error}") from error
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        _update_ini_file(kdeglobals, {"General": {"ColorSchemeHash": digest}})
        return f"kde: scheme applied with plasma-apply-colorscheme ({name})"

    # Outside Plasma there is nothing to apply a scheme, so write it where KDE
    # applications read their colors.
    updates = {section: dict(items) for section, items in sets.items()}
    updates["General"] = {"ColorScheme": name}
    _update_ini_file(kdeglobals, updates)
    notified = notify_kconfig_changed("kdeglobals", updates)
    suffix = "; KConfig change signal sent" if notified else ""
    return f"kde: scheme written to {main_file} and merged into {kdeglobals}{suffix}"


def _apply_qtct(
    tool: str, palette_text: str, apply: bool, kvantum_style: str | None
) -> str:
    root = _config_home() / tool
    colors_file = root / "colors" / f"{THEME_NAME}.conf"
    atomic_write(colors_file, palette_text)
    if not apply:
        return f"{tool}: palette written to {colors_file}"

    appearance = {"color_scheme_path": str(colors_file), "custom_palette": "true"}
    if kvantum_style:
        appearance["style"] = kvantum_style
    _update_ini_file(root / f"{tool}.conf", {"Appearance": appearance})
    return f"{tool}: palette {colors_file} set in {tool}.conf"


def _find_kvantum_base(name: str) -> Path:
    candidates = [_config_home() / "Kvantum", _data_home() / "Kvantum"]
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    candidates += [Path(path) / "Kvantum" for path in data_dirs.split(":") if path]
    for directory in candidates:
        if (directory / name / f"{name}.kvconfig").is_file():
            return directory / name
    raise QtThemeError(
        f"Kvantum base theme '{name}' not found; install it or choose another "
        "one with --qt-kvantum-base"
    )


def recolor_theme_text(text: str, colors: QtColors) -> str:
    """Recolor a Kvantum theme file with the Material You palette.

    Neutral colors move to the same tone in the scheme's neutral palette.  The
    base theme's accent hue moves to the primary role, keeping the relative
    tone of each shade.  Other hues (red, green, ...) are left alone.
    """

    counts: dict[str, int] = {}
    for match in _SVG_HEX.finditer(text):
        key = match.group(1).lower()
        counts[key] = counts.get(key, 0) + 1

    scheme = colors.scheme
    parsed = {key: Hct.from_int(int("ff" + key, 16)) for key in counts}
    chromatic = {k: h for k, h in parsed.items() if h.chroma >= _NEUTRAL_CHROMA}

    accent: dict[str, str] = {}
    if chromatic:
        dominant = max(chromatic, key=lambda key: counts[key])
        primary = Hct.from_int(int("ff" + colors.roles["primary"].lstrip("#"), 16))
        shift = primary.tone - chromatic[dominant].tone
        for key, hct in chromatic.items():
            distance = abs(hct.hue - chromatic[dominant].hue)
            if min(distance, 360 - distance) > _ACCENT_HUE_RANGE:
                continue
            tone = round(_clip(hct.tone + shift, 0, 100))
            accent[key] = _hex(scheme.primary_palette.tone(tone))
        accent[dominant] = colors.roles["primary"]

    replacements = dict(accent)
    for key, hct in parsed.items():
        if key not in chromatic:
            replacements[key] = _hex(scheme.neutral_palette.tone(round(hct.tone)))

    return _SVG_HEX.sub(
        lambda m: replacements.get(m.group(1).lower(), "#" + m.group(1)), text
    )


def kvantum_general_colors(
    active: Mapping[str, str], disabled: Mapping[str, str]
) -> dict[str, str]:
    return {
        "window.color": active["Window"],
        "base.color": active["Base"],
        "alt.base.color": active["AlternateBase"],
        "button.color": active["Button"],
        "light.color": active["Light"],
        "mid.light.color": active["Midlight"],
        "dark.color": active["Dark"],
        "mid.color": active["Mid"],
        "highlight.color": active["Highlight"],
        "inactive.highlight.color": active["Highlight"],
        "text.color": active["Text"],
        "window.text.color": active["WindowText"],
        "button.text.color": active["ButtonText"],
        "disabled.text.color": disabled["Text"],
        "tooltip.base.color": active["ToolTipBase"],
        "tooltip.text.color": active["ToolTipText"],
        "highlight.text.color": active["HighlightedText"],
        "link.color": active["Link"],
        "link.visited.color": active["LinkVisited"],
        "progress.indicator.text.color": active["HighlightedText"],
    }


def _apply_kvantum(
    colors: QtColors,
    active: Mapping[str, str],
    disabled: Mapping[str, str],
    base_name: str | None,
    apply: bool,
) -> str:
    base = _find_kvantum_base(base_name or KVANTUM_DEFAULT_BASE[colors.is_dark])
    kvconfig = recolor_theme_text(
        (base / f"{base.name}.kvconfig").read_text(encoding="utf-8"), colors
    )
    kvconfig = set_ini_values(
        kvconfig,
        {
            "%General": {
                "author": "Adwaita Material You",
                "comment": f"Material You colors generated on top of {base.name}",
            },
            "GeneralColors": kvantum_general_colors(active, disabled),
        },
    )

    destination = _config_home() / "Kvantum" / THEME_NAME
    atomic_write(destination / f"{THEME_NAME}.kvconfig", kvconfig)
    svg = base / f"{base.name}.svg"
    if svg.is_file():
        atomic_write(
            destination / f"{THEME_NAME}.svg",
            recolor_theme_text(svg.read_text(encoding="utf-8"), colors),
        )
    if not apply:
        return f"kvantum: theme written to {destination} (based on {base.name})"

    _update_ini_file(
        _config_home() / "Kvantum" / "kvantum.kvconfig",
        {"General": {"theme": THEME_NAME}},
    )
    return f"kvantum: theme {THEME_NAME} selected (based on {base.name})"


def apply_qt_theme(
    source_argb: int,
    scheme: str,
    variant: str = "default",
    *,
    targets: str | None = "auto",
    apply: bool = True,
    kvantum_base: str | None = None,
    contrast_level: float = 0.0,
    frame_contrast: float = 0.2,
    chroma_multiplier: float = 1.0,
    tone_multiplier: float = 1.0,
) -> list[str]:
    """Generate the Qt theme and write or apply it for each target.

    Returns one report line per target, plus notes about the environment.  A
    target that fails is reported without stopping the others.
    """

    selected = parse_targets(targets)
    colors = generate_qt_colors(
        source_argb,
        variant,
        scheme == "dark",
        contrast_level=contrast_level,
        chroma_multiplier=chroma_multiplier,
        tone_multiplier=tone_multiplier,
    )
    sets = kde_color_sets(colors, frame_contrast)
    active, disabled = qt_palette(sets)
    palette_text = render_qtct_palette(active, disabled)
    kvantum_style = None
    if "kvantum" in selected:
        kvantum_style = "kvantum-dark" if colors.is_dark else "kvantum"

    handlers = {
        "kde": lambda: _apply_kde(sets, apply),
        "qt5ct": lambda: _apply_qtct("qt5ct", palette_text, apply, kvantum_style),
        "qt6ct": lambda: _apply_qtct("qt6ct", palette_text, apply, kvantum_style),
        "kvantum": lambda: _apply_kvantum(colors, active, disabled, kvantum_base, apply),
    }

    report = []
    for target in selected:
        try:
            report.append(handlers[target]())
        except (OSError, QtThemeError) as error:
            report.append(f"{target}: failed: {error}")

    platform_theme = os.environ.get("QT_QPA_PLATFORMTHEME", "")
    for tool in ("qt5ct", "qt6ct"):
        if tool in selected and apply and platform_theme != tool:
            report.append(
                f"note: set QT_QPA_PLATFORMTHEME={tool} so Qt applications use {tool} settings"
            )
    return report
