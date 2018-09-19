#!/bin/bash -e

_title "Advanced headers"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<62 .> s2 .* s7 <>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<62+> s2 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<62 .*> s2 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<10> s2 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<10|(10 11)> s2 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<(10|(10 11))+> s2 .* s7 <>" 2 compile run
