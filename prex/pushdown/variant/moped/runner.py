import os
from subprocess import (
    Popen,
    PIPE,
)
from .output_parser import (
    parse_output,
)


def query_system(system):
    fd_r, fd_w = os.pipe()
    os_path = f"/dev/fd/{fd_r}"
    final_label_str = system.mapping[system.final_label]
    final_location_str = system.mapping[system.final]
    query = f"{final_location_str}:{final_label_str}"
    with (Popen(
            ["moped", os_path, "-s0", "-tr", query],
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            pass_fds=(fd_r,))) as handle:
        with os.fdopen(fd_w, "wt") as f:
            f.write(system.str)
        out, err = handle.communicate()
        lines = out.split(sep='\n')
        lines.extend(err.split(sep='\n'))
    # Need to close the pipe file descriptors
    os.close(fd_r)

    result, transitions = parse_output(lines, system.transition_mapping)

    return result, transitions


def query_file(system_path):
    with (Popen(
            ["moped", system_path, "-tr", "complete:e"],
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True)) as handle:
        out, err = handle.communicate()
        lines = out.split(sep='\n')
        lines.extend(err.split(sep='\n'))

    return lines
