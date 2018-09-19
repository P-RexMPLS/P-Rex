#!/bin/bash -e

_title "Exercise swaps"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<100> s1 .* s2 <.>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<10> s1 .* s2 <.>" 2 compile run
