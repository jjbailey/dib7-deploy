#!/bin/bash
# local/label-yaml.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

# this script just rewrites the file name in the comment
# NB: assumes the first four lines are already reserved for this

PATH=$HOME/.local/bin:/usr/bin:/usr/local/bin
PROJECT_HOME="$(CDPATH= builtin cd -- "$(dirname -- "$0")/.." && builtin pwd -P)" || exit 1
umask 022

cd "$PROJECT_HOME" || exit 1

TOP="*"

[ -n "$1" ] && {
    [ -d "$1" ] || exit 1
    TOP="$1/*"
}

LIST=$(find $TOP -name '*.yml' | grep -v OLD | grep -v block-device |
    grep -v dictionaries/ | grep -v requirements | sort)

for file in $LIST ; do
    grep -q ANSIBLE_VAULT $file && continue

    (
        echo "---"
        echo "# $file"
        echo "# vim: set tabstop=2 shiftwidth=2 expandtab:"
        echo
        if [ "$(head -1 $file)" == '---' ] ; then
            sed '1,3d' $file
        else
            cat $file
        fi
        echo
    ) | sed 's/ $//' | cat -s > /tmp/$$

    if diff -q $file /tmp/$$ ; then
        rm -f /tmp/$$
    else
        mv -b /tmp/$$ $file
    fi
done

exit 0
