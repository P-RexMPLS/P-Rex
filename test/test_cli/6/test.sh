#!/bin/bash -e

_title "Works correctly with the initial empty header"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<1000> s1 .* s3 <1003>" 0 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s3 <1003>" 0 compile run

_title "Doesn't match incorrectly"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<1000> s1 .* s3 <1002>" 0 compile run

_title "Does not allow the first hop to be a failure"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<2000> s1 .* s1 <2001,2000>" 1 compile run
