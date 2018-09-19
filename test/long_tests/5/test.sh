#!/bin/bash -e

_title "Juniper"

_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py juniper-xml mini_dump/isis mini_dump/forwarding/ adv-query "<.*> Uranus .* Hypnos <.*>" 0 compile run
