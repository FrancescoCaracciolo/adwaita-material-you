from os.path import expanduser
import subprocess, os
from map_colors import map_colors
from material_color_utilities_python.utils.theme_utils import *
from PIL import Image
EXTENSION_UUID = "material-you-colors@francescocaracciolo.github.io"
EXTENSIONDIR = "~/.local/share/gnome-shell/extensions/" + EXTENSION_UUID
EXTENSION_SCHEMA = "org.gnome.shell.extensions.material-you-colors"
VERSION = 47 

def execute_command(command):
    try:
        result = subprocess.check_output(["bash", "-c", command])
    except Exception as e:
        print(e)
        return None
    return result.decode("utf-8")

def get_setting(key, schema, uuid = None):
    if uuid is not None:
        command  = "gsettings --schemadir ~/.local/share/gnome-shell/extensions/" + EXTENSION_UUID + "/schemas get " + EXTENSION_SCHEMA + " " + key
    else:
        command  = "gsettings get " + schema + " " + key
    result = execute_command(command)
    if result is None:
        return ""
    return result.replace("\n", "").replace("'", "")

def set_setting(key, value, schema, uuid = None):
    if uuid is not None:
        command  = "gsettings --schemadir ~/.local/share/gnome-shell/extensions/" + EXTENSION_UUID + "/schemas set " + EXTENSION_SCHEMA + " " + key + " " + value
    else:
        command  = "gsettings set " + schema + " " + key + " " + value
    execute_command(command)

def get_ext_settings(key):
    return get_setting(key, EXTENSION_SCHEMA, EXTENSION_UUID)
def parse_bool(value: str) -> bool:
    return value.lower() == "true"

def modify_colors(scss_path, output_path, vars):
    colors_template = open(scss_path, "r").read()
    for key in vars:
        colors_template = colors_template.replace("{{" + key+ "}}", vars[key])
    open(output_path, "w").write(colors_template)

def compile_sass(scss_path, output_path):
    execute_command("sass " + scss_path + " " + output_path)

def apply_theme():
    color_scheme = get_ext_settings("scheme")
    accent_color_enabled = parse_bool(get_ext_settings("enable-accent-colors"))
    accent_color = get_ext_settings("accent-color")
    show_notifications = parse_bool(get_ext_settings("show-notifications"))
    extra_command = get_ext_settings("extra-command")
    height = get_ext_settings("resize-height")
    width = get_ext_settings("resize-width")
    enable_pywal_theming = parse_bool(get_ext_settings("enable-pywal-theming"))
    enable_arcmenu_theming = parse_bool(get_ext_settings("arcmenu-theming"))
    dark_pref = get_setting("color-scheme", "org.gnome.desktop.interface")
    is_dark = dark_pref == "prefer-dark"

    wall_uri_type = "-dark" if is_dark else ""
    wall_path = get_setting("picture-uri" + wall_uri_type, "org.gnome.desktop.background").lstrip("file://")
    # Generate theme
    if accent_color_enabled:
        theme = themeFromSourceColor(int(accent_color))
    else:
        theme = themeFromImage(Image.open(wall_path))
    
    # Map colors
    cmfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "color_mappings.json")
    bpfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_presets.json")
    f = open(bpfile, "r")
    base_presets = json.loads(f.read())
    f.close()
    try:
        f = open(cmfile, "r")
        color_mappings = json.loads(f.read())
        f.close()
    except Exception as e:
        print("Cannot open color mappings file")
        exit(-1)

    variant = color_scheme.lower()
    scheme = "light" if not is_dark else "dark"
    base_preset = map_colors(color_mappings[variant][scheme], base_presets[scheme], theme["schemes"][scheme].props)
    
    # Generate css
    css = ""
    for key in base_preset["variables"]:
        css +=  "@define-color " + key + " " + base_preset["variables"][key] + ";\n"
    for prefix_key in base_preset["palette"]:
        for key_2 in base_preset["palette"][prefix_key]:
            css += "@define-color " + prefix_key + key_2 + " " + base_preset["palette"][prefix_key][key_2] + ";\n"
    f = open(os.path.expanduser("~/.config/gtk-4.0/gtk.css"), "w+")
    f.write(css)
    f.close()
    f = open(os.path.expanduser("~/.config/gtk-3.0/gtk.css"), "w+")
    f.write(css)
    f.close()
    print("Theme applied")
    open(os.path.expanduser("~/.config/gtk-4.0/.materialyou"), "w+").close()
    # Generate gnome shell theme 
    modify_colors(expanduser(EXTENSIONDIR + "/shell/" + str(VERSION) + "/gnome-shell-sass/_colors.txt"), expanduser(EXTENSIONDIR + "/shell/" + str(VERSION) + "/gnome-shell-sass/_colors.scss"), base_preset["variables"])
    modify_colors(expanduser(EXTENSIONDIR + "/shell/" + str(VERSION) + "/gnome-shell-sass/_default-colors.txt"), expanduser(EXTENSIONDIR + "/shell/" + str(VERSION) + "/gnome-shell-sass/_default-colors.scss"), base_preset["variables"])
    if not os.path.exists(expanduser("~/.local/share/themes/MaterialYou")):
        os.makedirs(expanduser("~/.local/share/themes/MaterialYou"))
        os.makedirs(expanduser("~/.local/share/themes/MaterialYou/gnome-shell"))
    compile_sass(expanduser(EXTENSIONDIR+ "/shell/" + str(VERSION) + "/gnome-shell.scss"), expanduser("~/.local/share/themes/MaterialYou/gnome-shell/gnome-shell.css"))
    set_setting("name", "reset", "org.gnome.shell.extensions.user-theme")


apply_theme()
