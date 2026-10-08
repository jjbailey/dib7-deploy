#!/bin/bash
# local/label-python.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

# this script just rewrites the file name in the comment
# NB: assumes the first three lines are already reserved for this

PATH=$HOME/.local/bin:/usr/bin:/usr/local/bin
PROJECT_HOME="$(CDPATH= builtin cd -- "$(dirname -- "$0")/.." && builtin pwd -P)" || exit 1
umask 022

cd "$PROJECT_HOME" || exit 1

TOP="."

[ -n "$1" ] && {
    [ -d "$1" ] || exit 1
    TOP="$1"
}

while IFS= read -r -d '' file ; do
    tmpfile=$(mktemp "${TMPDIR:-/tmp}/label-python.XXXXXX") || exit 1
    (
        echo "#!/usr/bin/env python3"
        echo "# ${file#./}"
        echo "# vim: set tabstop=4 shiftwidth=4 expandtab:"
        echo
        sed '1,3d' "$file"
    ) | cat -s > "$tmpfile"

    if diff -q "$file" "$tmpfile" > /dev/null ; then
        rm -f "$tmpfile"
    else
        mv -b "$tmpfile" "$file"
        chmod 755 "$file"
        echo "$file"
    fi
done < <(find "$TOP" -type f -name '*.py' ! -path '*OLD*' -print0 | sort -z)

exit 0
