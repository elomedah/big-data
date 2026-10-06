#!/usr/bin/env bash
set -eu

destination=$1
shift

# A rerun may overlap a download that survived a disconnected controller.
exec 9>"${destination}.lock"
flock -w 14400 9
if [ -f "$destination" ] && tar -tzf "$destination" >/dev/null 2>&1; then
    exit 0
fi

previous_url=
for url in "$@"; do
    [ "$url" != "$previous_url" ] || continue
    previous_url=$url
    # Never combine partial downloads from different mirrors.
    key=$(printf '%s' "$url" | sha256sum | cut -d ' ' -f 1)
    partial="${destination}.${key}.part"
    for attempt in 1 2 3; do
        if curl --fail --location --show-error --silent \
            --connect-timeout 30 --max-time 1800 \
            --speed-limit 1024 --speed-time 120 \
            --continue-at - --output "$partial" "$url"; then
            if tar -tzf "$partial" >/dev/null 2>&1; then
                chmod 0644 "$partial"
                mv "$partial" "$destination"
                exit 0
            fi
            # A completed but invalid archive cannot be resumed.
            rm -f "$partial"
        fi
        echo "Download attempt $attempt failed for $url; retrying with resume." >&2
        sleep 5
    done
done
echo "Hive download failed. Partial files are retained beside $destination; rerun to resume." >&2
exit 1
