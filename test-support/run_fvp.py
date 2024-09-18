#!/usr/bin/env python3

# Copyright (c) 2023-2024, Arm Limited and affiliates.

import subprocess
import sys
from os import path
from dataclasses import dataclass
import shlex

@dataclass
class FVP:
    model_exe: str
    tarmac_plugin: str
    cmdline_param: str

MODELS = {
    "corstone-310": FVP(
        "Corstone-310/models/Linux64_GCC-9.3/FVP_Corstone_SSE-310",
        "Corstone-310/plugins/Linux64_GCC-9.3/TarmacTrace.so",
        "cpu0.semihosting-cmd_line",
    ),
    "aem-a": FVP(
        "Base_RevC_AEMvA_pkg/models/Linux64_GCC-9.3/FVP_Base_RevC-2xAEMvA",
        "Base_RevC_AEMvA_pkg/plugins/Linux64_GCC-9.3/TarmacTrace.so",
        "cluster0.cpu0.semihosting-cmd_line",
    ),
    "aem-r": FVP(
        "AEMv8R_base_pkg/models/Linux64_GCC-9.3/FVP_BaseR_AEMv8R",
        "AEMv8R_base_pkg/plugins/Linux64_GCC-9.3/TarmacTrace.so",
        "cluster0.cpu0.semihosting-cmd_line",
    ),
}


def run_fvp(
    fvp_root_dir,
    fvp_model,
    fvp_configs,
    image,
    arguments,
    timeout,
    working_directory,
    verbose,
    tarmac_file,
):
    """Execute the program using an FVP and return the subprocess return code."""
    if fvp_model not in MODELS:
        raise Exception(f"{fvp_model} is not a recognised model name")
    model = MODELS[fvp_model]

    command = [path.join(fvp_root_dir, model.model_exe)]
    command.extend(["--quiet"])
    for config in fvp_configs:
        command.extend(["--config-file", path.join(fvp_root_dir, "config", config + ".cfg")])
    command.extend(["--application", image])
    command.extend(["--parameter", f"{model.cmdline_param}={shlex.join(arguments)}"])
    if tarmac_file is not None:
        command.extend([
            "--plugin",
            path.join(fvp_root_dir, model.tarmac_plugin),
            "--parameter",
            "TRACE.TarmacTrace.trace-file=" + tarmac_file,
        ])

    if verbose:
        print("running: {}".format(shlex.join(command)))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        timeout=timeout,
        cwd=working_directory,
        check=False,
    )
    sys.stdout.buffer.write(result.stdout)
    return result.returncode

