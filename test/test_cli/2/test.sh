#!/bin/bash -e

_title "Interfaces on input"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.+> s2 .* s7 <>" 2 compile run

_title "Interfaces on first hop"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s7 <>" 2 compile run

_title "Interfaces on last hop"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s7 <.+>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s5 .* s7 <>" 2 compile run
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s5 s2 .* s7 <>" 2 compile run

_title "Interfaces on multiple hops"
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s2 s1 .* s7 <>" 2 compile run

_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s4 s6 .* s7 s8 <.*>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s4 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s2 .* s7 <>" 2 compile run

_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s5 .* s7 <>" 2 compile run
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<.*> s2 .* s3 .* s7 <.+>" 2 compile run

_title "Multiple immediate hops with interfaces"
_exec 2 "YES" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 .* s2 .* s5 .* s7 <>" 2 compile run

_title "Dot shouldn't be wrong"
# There's certainly not a route with this many routers
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> ............... <>" 2 compile run
# This will be no, even if you can match 2 dots per router
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> ........................ <>" 3 compile run

_title "Under-approximation"
# Cycle detection should catch this one even though there is a path
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 s2 s4 s2 .* s7 <>" 3 compile --under run
# Here there just is no path
_exec 2 "NO" python3 $PROJECT_ROOT/prex/main.py xml topo.xml routing.xml adv-query "<> s1 s2 s4 s2 .* s7 <>" 2 compile --under run
