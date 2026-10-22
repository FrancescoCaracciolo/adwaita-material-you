# Adwaita Material You

Adwaita Material You is a script to generate and apply GTK4 themes (and GTK3 with adw-gtk3) based on a color or an image.

## Installation

### Arch Linux (AUR)

```bash
yay -S adwaita-material-you
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/francescocaracciolo/adwaita-material-you.git
cd adwaita-material-you
```

2. Run the install script:
```bash
./install.sh
```

This will create a virtual environment, install the dependencies, and link the `adwmu` command to `/usr/local/bin`.

### Dependencies

The project requires the following Python packages:
- `rich`
- `pillow`
- `pygobject`
- `material`
- `pydantic`
- `regex`
- `numpy`
- `materialyoucolors`

## Usage

The basic command syntax is:

```bash
adwmu <scheme> [options]
```

### Required Arguments

- `scheme`: Color scheme, either `light` or `dark`

### Options

- `-c, --color`: Hex code of the color to base the theme on
- `-w, --wallpaper`: Path to the wallpaper image to base the theme on
- `-o, --output`: Choose the output file path
- `-a, --apply`: Apply the theme automatically after generation
- `-m, --mappings`: Path to custom color mappings file
- `-V, --variant`: Theme variant - `default`, `vibrant`, `expressive`, `fruit salad`, or `muted`

**Note**: You must specify either `--color` or `--wallpaper`.

### Qt options

- `-q, --qt`: Generate and apply a Qt theme with the same colors as [kde-material-you-colors](https://github.com/luisbocanegra/kde-material-you-colors)
- `--qt-targets LIST`: Comma separated targets: `kde`, `qt5ct`, `qt6ct`, `kvantum`. Use `all` for every target, or `auto` (default) for the ones detected on your system
- `--qt-no-apply`: Only write the Qt theme files, without selecting them in the Qt settings
- `--qt-kvantum-base THEME`: Installed Kvantum theme to recolor (default: `KvAdaptaDark` for dark, `KvAdapta` for light)
- `--qt-contrast-level FLOAT`: General contrast level from -1 to 1 (default 0)
- `--qt-frame-contrast FLOAT`: Frames and outlines contrast from 0 to 1 (default 0.2)
- `--qt-chroma-multiplier FLOAT`: Colorfulness of the Qt theme from 0 to 10 (default 1)
- `--qt-tone-multiplier FLOAT`: Brightness of the Qt theme backgrounds from 0 to 1.5 (default 1)

### Examples

Generate a dark theme based on a color:
```bash
adwmu dark -c "#FF5733"
```

Generate a light theme based on a wallpaper and apply it:
```bash
adwmu light -w /path/to/wallpaper.png -a
```

Generate a vibrant dark theme and save to a custom file:
```bash
adwmu dark -w /path/to/wallpaper.jpg -V vibrant -o ~/.config/gtk-4.0/custom-gtk.css
```

Generate a muted light theme with custom color mappings:
```bash
adwmu light -c "#3498DB" -V muted -m /path/to/custom-mappings.json
```

## Qt theming

Generate a dark Qt theme from a color and apply it to every detected target:

```bash
adwmu dark -c "#FF5733" --qt
```

Only qt6ct and Kvantum, from a wallpaper, with a vibrant variant:

```bash
adwmu light -w /path/to/wallpaper.png -V vibrant --qt --qt-targets qt6ct,kvantum
```

Each target is written as follows. Paths honor `XDG_CONFIG_HOME` and `XDG_DATA_HOME`.

| Target | Files | What `--qt` changes |
| --- | --- | --- |
| `kde` | `~/.local/share/color-schemes/AdwaitaMaterialYou{Dark,Light}.colors` | Applies the scheme with `plasma-apply-colorscheme`. Without Plasma, merges the colors into `~/.config/kdeglobals` so KDE applications use them |
| `qt5ct`, `qt6ct` | `~/.config/qt{5,6}ct/colors/AdwaitaMaterialYou.conf` | Sets `color_scheme_path` and `custom_palette=true` in the `[Appearance]` section of `qt{5,6}ct.conf` |
| `kvantum` | `~/.config/Kvantum/AdwaitaMaterialYou/` | Selects the theme in `kvantum.kvconfig`. The theme is an installed Kvantum theme recolored with Material You colors. When Kvantum is selected, `qt5ct`/`qt6ct` also get `style=kvantum` (`kvantum-dark` for dark) |

For qt5ct and qt6ct, set `QT_QPA_PLATFORMTHEME=qt5ct` or `qt6ct` in your session
so Qt applications read those settings. Already running applications may need a
restart to pick up the new colors.

Other settings in those files are kept. Without `--qt`, no Qt file is touched.

## Live application

Using `--apply` writes the generated colors to `custom-accent.css` for both
GTK 3 and GTK 4 and adds an import to each user `gtk.css` without replacing
the rest of that file. The command then performs the same high-contrast
setting refresh used by ChromaLeon so running GTK applications can reload the
stylesheet without restarting them:

```bash
adwmu dark -c "#FF5733" --apply
```

The refresh is best-effort. If `gsettings` is unavailable, the files are
still updated and newly launched applications will use the new colors. Some
applications can choose to keep their own style cache and may still need to
be reopened.
