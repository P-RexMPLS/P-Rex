#!/bin/bash -e

_title "Network should have no path at k=0"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 0 compile run

_title "Default should over-approximate"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 1 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 2 compile run

_title "--under should under-approximate"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 1 compile --under run
# There might be some off by one error, 2 should still go through
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 2 compile --under run
# If there's an off by one error AT LEAST this should work
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 3 compile --under run
