#!/bin/bash -e

_title "Simple sanity checks"

_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s1 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s1 .* s7 <.*>" 2 compile run

_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.+> s1 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s1 .* s7 <.+>" 2 compile run

_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s2 .* s7 <>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s3 .* s7 <>" 2 compile run

_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s2 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s2 .* s7 <.+>" 2 compile run

_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s6 .* s9 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s6 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s9 .* s7 <>" 2 compile run
