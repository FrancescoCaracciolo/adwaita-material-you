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
