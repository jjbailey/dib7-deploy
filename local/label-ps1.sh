#!/bin/bash
# local/label-ps1.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

# this script just rewrites the file name in the comment
# NB: assumes the first four lines are already reserved for this

tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT

find . -name '*.ps1' ! -path '*OLD*' -print0 | sort -z | while IFS= read -r -d '' file ; do
    (
        echo "#!/usr/bin/pwsh"
        echo "# ${file#./}"
        echo "# vim: set tabstop=4 shiftwidth=4 expandtab:"
        echo
        sed '1,4d' "$file" | sed 's/ $//'
        echo
    ) | cat -s > "$tmpfile"

    if ! diff -q "$file" "$tmpfile" > /dev/null ; then
        cp -b "$tmpfile" "$file"
    fi
done

exit 0
