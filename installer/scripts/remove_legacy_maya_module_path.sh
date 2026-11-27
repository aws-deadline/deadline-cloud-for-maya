#!/bin/sh
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Removes the MAYA_MODULE_PATH export that installers up to 0.15.15 wrote to the
# user's shell startup files on Linux and macOS.
#
# Those installers registered the plug-in by appending a line of the form
#
#     export MAYA_MODULE_PATH="<value at install time>:<install dir>/"
#
# The value is a snapshot taken when the installer ran, so it masks every later
# change the user or studio makes to MAYA_MODULE_PATH, and it outlives an
# uninstall. Newer installers register the plug-in with a .mod file instead.
#
# Usage: remove_legacy_maya_module_path.sh <install dir> [home dir]
#
# Only lines that are exactly `export MAYA_MODULE_PATH="..."` and whose last
# entry is the given install dir (with or without a trailing slash) are removed.
# The install dir is compared as a literal string. A changed file is first
# copied to <file>.deadline-cloud-for-maya.bak (or .bak.1 to .bak.9 if earlier
# backups exist), then rewritten in place so that symlinks, ownership and
# permissions are kept. For a system-scope install the installer runs as root,
# so these are the dotfiles of the home directory the installer reports.
#
# This script always exits 0: failing to clean up must never fail an install
# or uninstall.

log() {
    printf '%s\n' "remove_legacy_maya_module_path: $*"
}

install_dir=$1
home_dir=${2:-$HOME}

# Strip trailing slashes, but keep "/" itself so that it is rejected below.
while [ "${#install_dir}" -gt 1 ] && [ "${install_dir%/}" != "$install_dir" ]; do
    install_dir=${install_dir%/}
done

case "$install_dir" in
    /) log "refusing to use '/' as the install directory"; exit 0 ;;
    /*) ;;
    "") log "no install directory given, nothing to do"; exit 0 ;;
    *) log "install directory '$install_dir' is not absolute, nothing to do"; exit 0 ;;
esac

if [ -z "$home_dir" ] || [ ! -d "$home_dir" ]; then
    log "home directory '$home_dir' not found, nothing to do"
    exit 0
fi

tmp_file=$(mktemp "${TMPDIR:-/tmp}/deadline-cloud-for-maya.XXXXXX") || {
    log "could not create a temporary file, nothing done"
    exit 0
}
trap 'rm -f "$tmp_file"' EXIT

for name in .bashrc .bash_profile .bash_login .profile .zshrc .zprofile; do
    file=$home_dir/$name
    [ -f "$file" ] || continue

    # Values are passed through the environment, not `awk -v`, because -v
    # processes backslash escapes. Matching uses index/substr only, so regex
    # metacharacters in the install dir are never interpreted.
    # Kept lines go to $DCM_OUT; removed lines go to stdout.
    removed=$(
        DCM_DIR=$install_dir DCM_OUT=$tmp_file awk '
            BEGIN {
                dir = ENVIRON["DCM_DIR"]
                out = ENVIRON["DCM_OUT"]
                prefix = "export MAYA_MODULE_PATH=\""
                printf "" > out
            }
            function is_legacy(line,    value, n, d) {
                if (substr(line, 1, length(prefix)) != prefix) return 0
                if (substr(line, length(line), 1) != "\"") return 0
                value = substr(line, length(prefix) + 1, length(line) - length(prefix) - 1)
                if (index(value, "\"") != 0) return 0
                if (substr(value, length(value), 1) == "/") value = substr(value, 1, length(value) - 1)
                n = length(value)
                d = length(dir)
                if (n < d || substr(value, n - d + 1) != dir) return 0
                # The install dir must be a whole entry: the whole value, or preceded by ":".
                return n == d || substr(value, n - d, 1) == ":"
            }
            {
                if (is_legacy($0)) print $0
                else print $0 > out
            }
        ' "$file"
    ) || {
        log "could not read $file, skipped"
        continue
    }

    [ -n "$removed" ] || continue

    if [ ! -w "$file" ]; then
        log "$file contains a legacy MAYA_MODULE_PATH line but is not writable, skipped"
        continue
    fi

    # Check that every line was either kept or removed before overwriting anything.
    original_count=$(awk 'END { print NR }' "$file")
    kept_count=$(awk 'END { print NR }' "$tmp_file")
    removed_count=$(printf '%s\n' "$removed" | awk 'END { print NR }')
    if [ "$original_count" != "$((kept_count + removed_count))" ]; then
        log "unexpected result while processing $file, skipped"
        continue
    fi

    # Never overwrite an earlier backup, and never write through a symlink planted at the
    # backup path: use the first of .bak, .bak.1, ... .bak.9 that does not exist.
    backup=
    for suffix in "" .1 .2 .3 .4 .5 .6 .7 .8 .9; do
        candidate=$file.deadline-cloud-for-maya.bak$suffix
        if [ ! -e "$candidate" ] && [ ! -L "$candidate" ]; then
            backup=$candidate
            break
        fi
    done
    if [ -z "$backup" ]; then
        log "too many existing backups of $file, skipped"
        continue
    fi
    if ! cp -p "$file" "$backup"; then
        log "could not back up $file to $backup, skipped"
        continue
    fi

    # Write through the existing file (and any symlink) to keep its inode and mode.
    if ! cat "$tmp_file" > "$file"; then
        log "could not rewrite $file, restoring it from $backup"
        cat "$backup" > "$file" 2>/dev/null
        continue
    fi

    printf '%s\n' "$removed" | while IFS= read -r line; do
        log "removed from $file: $line"
    done
    log "backed up the original $file to $backup"
done

exit 0
