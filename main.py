from color_utils import ColorUtils
from material_color_utilities_python import *
import json, os
import map_colors
import argparse
from materialyoucolor.scheme import Scheme
from material_color_utilities_python.utils import color_utils
from theme_runtime import apply_live_gtk_theme, render_css

MU_BACKEND = True
def main():
    parser = argparse.ArgumentParser()
    print(os.getcwd())
    parser.add_argument("scheme", help="Color scheme, light or dark", type=str)

    # Optional arguments
    parser.add_argument("-c", "--color", help="Hex code of the color to base the theme on", type=str)
    parser.add_argument("-w", "--wallpaper", help="Path of the wallpaper to base the theme on", type=str)
    parser.add_argument("-o", "--output", help="Choose the output file")
    parser.add_argument("-a", "--apply", action="store_true", help="Apply the theme after it is generated")
    parser.add_argument("-m", "--mappings", help="Color mappings file")
    parser.add_argument("-V", "--variant", help="Variant of the theme, with predefined color_mappings can be defualt, vibrant, expressive, fruit salad, muted")

    parser.add_argument("-q", "--qt", action="store_true", help="Generate and apply a Qt theme")
    parser.add_argument("--qt-targets", default="auto", help="Comma separated Qt targets: kde, qt5ct, qt6ct, kvantum, all or auto")
    parser.add_argument("--qt-no-apply", action="store_true", help="Only write the Qt theme files without selecting them")
    parser.add_argument("--qt-kvantum-base", help="Installed Kvantum theme to recolor")
    parser.add_argument("--qt-contrast-level", type=float, default=0.0, help="General contrast level from -1 to 1")
    parser.add_argument("--qt-frame-contrast", type=float, default=0.2, help="Frames and outlines contrast from 0 to 1")
    parser.add_argument("--qt-chroma-multiplier", type=float, default=1.0, help="Colorfulness of the Qt theme from 0 to 10")
    parser.add_argument("--qt-tone-multiplier", type=float, default=1.0, help="Brightness of the Qt theme backgrounds from 0 to 1.5")

    args = parser.parse_args()
    if args.color:
        color = args.color
        argb = argbFromHex(color) 
    elif args.wallpaper:
        img = Image.open(args.wallpaper)
        argb = sourceColorFromImage(img)
    else:
        print("Error: at least one argument between color and wallpaper must be specified")
        exit(-1)
    
    if MU_BACKEND:
        sch = Scheme.dark(argb).__dict__["props"]
        generated = {}
        for key, color in sch.items(): 
            color = [color_utils.redFromArgb(color), color_utils.greenFromArgb(color), color_utils.blueFromArgb(color), color_utils.alphaFromArgb(color)] 
            generated[key] = ColorUtils.argb_from_argb_arr(color[0], color[1], color[2], color[3])
        theme = generated
    else:
        theme = themeFromSourceColor(argb)
    scheme = args.scheme
    variant = args.variant if args.variant else "default"

    lib_dir = "/usr/lib/adwaita-material-you"
    cmfile = os.path.expanduser(args.mappings) if args.mappings else os.path.join(lib_dir, "color_mappings.json")
    bpfile = os.path.join(lib_dir, "base_presets.json")
    
    # Handle erorrs
    if args.scheme not in ["dark", "light"]:
        print("Color scheme must be dark or light")
        exit(-1)
    
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
    

    # Generate theme
    print(theme)
    base_preset = map_colors.map_colors(color_mappings[variant][scheme], base_presets[scheme], theme)
    # Generate css
    css = render_css(base_preset)

    if args.output:
        f = open(os.path.expanduser(args.output), "w+")
        f.write(css)
        f.close()
        print("Theme saved to file")
    if args.apply:
        reloaded = apply_live_gtk_theme(base_preset)
        print("Theme applied")
        if reloaded:
            print("Running GTK applications notified to reload their stylesheets")
        else:
            print("GTK stylesheets written; live reload notification unavailable")
    if args.qt:
        from qt_theme import apply_qt_theme, QtThemeError
        try:
            report = apply_qt_theme(
                argb,
                scheme,
                variant,
                targets=args.qt_targets,
                apply=not args.qt_no_apply,
                kvantum_base=args.qt_kvantum_base,
                contrast_level=args.qt_contrast_level,
                frame_contrast=args.qt_frame_contrast,
                chroma_multiplier=args.qt_chroma_multiplier,
                tone_multiplier=args.qt_tone_multiplier,
            )
        except QtThemeError as error:
            print(f"Qt theme failed: {error}")
            exit(-1)
        for line in report:
            print(line)

if __name__ == "__main__":
    main()
