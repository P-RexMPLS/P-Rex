#!/bin/bash

_init() {
    ##
    ## Initialize the script variables depending of the environment
    ##

    case $TERM in
        xterm*|screen)
            export _DUMBTERM=0
            export LINES=$(stty size | cut -d ' ' -f 1)
            export COLUMNS=$(stty size | cut -d ' ' -f 2)
            export _COLOR_SUCCESS="\e[1;32m"
            export _COLOR_OUTPUT="\e[1;37m"
            export _COLOR_ERROR="\e[1;31m"
            export _COLOR_WARNING="\e[1;33m"
            export _COLOR_BULLET="\e[1;34m"
            export _COLOR_TITLE="\e[1;36m"
            export _COLOR_NORMAL="\e[0m"
            ;;
        *)
            export _DUMBTERM=1
            export LINES=24
            export COLUMNS=80
            ;;
    esac

    export PROJECT_ROOT="$PWD"

    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    export PATH="$PROJECT_ROOT/optimized_bin:$PROJECT_ROOT/bin:$PATH"
    export SPINDIR="$PROJECT_ROOT/optimized_bin:$PROJECT_ROOT/bin"
}

_exec() {
    skip=1
    if [ "$1" -eq "$1" ] 2>/dev/null; then
        skip=$(($1 + 1))
        shift
    fi
    ##
    ## Execute a command
    ##

    # Display the command
    msg="${@:$skip}"
    if [[ $_DUMBTERM == 0 ]]; then
        if [ $(echo -n "$msg" | wc -c) -gt $(($COLUMNS - 12)) ]; then
            msg=$(echo "$msg" | head -c $(($COLUMNS - 15)))
            echo -en "  ${_COLOR_BULLET}>${_COLOR_NORMAL} ${msg}"
            echo -en "... "
        else
            echo -en "  ${_COLOR_BULLET}🤔${_COLOR_NORMAL} ${msg}"
            echo -en "\e[$(($COLUMNS - ${#msg} - 13))C"
        fi
    else
        echo -n "  > $msg "
    fi
    # Exec the command and display the result
    output=$(/usr/bin/time -v "$@" 2>&1)
	code="$?"
    if [[ $code != 0 ]]; then
        echo -e "${_COLOR_BULLET}[${_COLOR_ERROR}FAIL${_COLOR_BULLET}]${_COLOR_NORMAL}";
    else
        echo -e "${_COLOR_BULLET}[${_COLOR_SUCCESS}DONE${_COLOR_BULLET}]${_COLOR_NORMAL}"
    fi

	echo -e "\n${_COLOR_OUTPUT}PROGRAM EXIT CODE: $code";
	echo "$output";
	echo -e "${_COLOR_NORMAL}\n";
}

_title() {
    ##
    ## Write a title
    ##

    echo -e "${_COLOR_TITLE} $*${_COLOR_NORMAL}"
}

_test() {
    ##
    ## Write a title
    ##
    echo -e "\n${_COLOR_BULLET}::${_COLOR_TITLE} $*${_COLOR_NORMAL}"
}

TEST_DIRECTORY="bench_cli/"

TEMP=$(getopt -o 'l' --long 'long' -n 'bench_cli.sh' -- "$@")

if [ $? -ne 0 ]; then
            cat <<EOF
Usage:
 $0 [options] [--] <testquery>

Options:
 -l, --long         run long tests instead
EOF
    exit 1
fi

# Note the quotes around "$TEMP": they are essential!
eval set -- "$TEMP"
unset TEMP

while true; do
    case "$1" in
        '-l'|'--long')
            TEST_DIRECTORY="long_tests/"
            shift
            continue
            ;;
        '--')
            shift
            break
            ;;
        *)
            echo 'Internal error!' >&2
            exit 1
            ;;
    esac
done

TEST_QUERY=$1
if [ -z "$TEST_QUERY" ]; then
    TEST_QUERY=""
fi

_init
python3 --version
echo "Moped $(bin/moped --version 2>&1 | grep -w Version)"
echo "Spin md5 $(md5sum bin/spin | cut -d ' ' -f 1)"

export -f _exec

cd benchmark
while read path; do
    _test "$path"
    (
    cd $(dirname $path)
    . $(basename $path)
    )
    _TERROR=$(($_TERROR + $?))
done < <(find "$TEST_DIRECTORY/$TEST_QUERY" -name "bench.sh" -type "f")
