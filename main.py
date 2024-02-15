from material_color_utilities_python import *
import json, os
import map_colors
import argparse

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("color", help="Hex code of the color to base the theme on", type=str)
    parser.add_argument("scheme", help="Color scheme, light or dark", type=str)

    # Optional arguments
    parser.add_argument("-o", "--output", action="store_true", help="Choose the output file")
    parser.add_argument("-a", "--apply", action="store_true", help="Apply the theme after it is generated")
    parser.add_argument("-c", "--color_mappings", action="store_true", help="Color mappings file")
    parser.add_argument("-V", "--variant", action="store_true", help="Variant of the theme, with predefined color_mappings can be defualt, vibrant, expressive, fruit salad, muted")

    args = parser.parse_args()
    scheme = parser.parse_args()

    color = args.color
    theme = themeFromSourceColor(argbFromHex(color))
    scheme = args.scheme
    variant = args.variant if args.variant else "default"

    cmfile = args.color_mappings if args.color_mappings else "color_mappings.json"
    bpfile = "base_presets.json"

    f = open(bpfile, "r")
    base_presets = json.loads(f.read())
    f.close()
    f = open(cmfile, "r")
    color_mappings = json.loads(f.read())
    f.close()

    # Generate theme
    base_preset = map_colors.map_colors(color_mappings[variant][scheme], base_presets[scheme], theme["schemes"][scheme].props)
    # Generate css
    css = ""
    for key in base_preset["variables"]:
        css +=  "@define-color " + key + " " + base_preset["variables"][key] + ";\n"
    for prefix_key in base_preset["palette"]:
        for key_2 in base_preset["palette"][prefix_key]:
            css += "@define-color " + prefix_key + key_2 + " " + base_preset["palette"][prefix_key][key_2] + ";\n"

    if args.output:
        f = open(os.path.expanduser(args.output), "w+")
        f.write(css)
        f.close()
        print("Theme saved to file")
    if args.apply:
        f = open(os.path.expanduser("~/.config/gtk-4.0/gtk.css"), "w+")
        f.write(css)
        f.close()
        f = open(os.path.expanduser("~/.config/gtk-3.0/gtk.css"), "w+")
        f.write(css)
        f.close()
        print("Theme applied")

if __name__ == "__main__":
    main()