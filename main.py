from material_color_utilities_python import *
import json
import map_colors

theme = themeFromSourceColor(argbFromHex('#f58c94'))

f = open("base_presets.json", "r")
base_presets = json.loads(f.read())
f.close()
f = open("color_mappings.json", "r")
color_mappings = json.loads(f.read())
f.close()


base_preset = map_colors.map_colors(color_mappings["default"]["dark"], base_presets["dark"], theme["schemes"]["dark"].props)
css = ""
for key in base_preset["variables"]:
    css +=  "@define-color " + key + " " + base_preset["variables"][key] + ";\n"
for prefix_key in base_preset["palette"]:
    for key_2 in base_preset["palette"][prefix_key]:
        css += "@define-color " + prefix_key + key_2 + " " + base_preset["palette"][prefix_key][key_2] + ";\n"

f = open("output.css", "w+")
f.write(css)
f.close()