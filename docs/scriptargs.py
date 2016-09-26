"""Generates the scriptargs.rst file that copies that script arguments with
descriptions and default values from the livemon code.
"""
from liveserial.livemon import script_options
lines = []
template = "- **{name}**: {help} Default: {default} ({type}).{choice}"

for name, options in dict(script_options).items():
    tempargs = {"name": name[1:]}
    if "default" not in options:
        tempargs["default"] = None
    else:
        tempargs["default"] = options["default"]
        
    if "type" not in options:
        if "action" in options and options["action"] == "store_true":
            tempargs["type"] = "bool"
        else:
            tempargs["type"] = "str"
    else:
        tempargs["type"] = options["type"].__name__

    if "choices" in options:
        tempargs["choice"] = "Must be one of {}".format(options["choices"])
    else:
        tempargs["choice"] = ""

    if "help" in options:
        tempargs["help"] = options["help"]
    else:
        tempargs["help"] = "No summary available."
        
    lines.append(template.format(**tempargs))

with open("scriptargs.rst", 'w') as f:
    f.write('\n'.join(lines))   
