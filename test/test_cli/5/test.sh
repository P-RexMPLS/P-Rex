#!/bin/bash -e

_title "Multiple actions"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <>" 0 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <10>" 2 compile run

_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<100> s1 .* s3 <100>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<100> s1 .* s3 <200>" 2 compile run

_title "Doesn't overestimate for no failures"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<1000> s1 .* s3 <1003 1002>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<1000> s1 .* s3 <1003 1002>" 0 compile run
