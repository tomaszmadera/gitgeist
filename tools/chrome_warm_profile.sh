#!/bin/bash
# Wrapper for `tools/diversity_report.py run --chrome <this script>`.
#
# Why: on the Grok Bot box, headless Chrome hung on every brand-new --user-data-dir
# (no output until a 120 s timeout), while diversity_report.py gives each screenshot a
# new temporary profile. This wrapper replaces every --user-data-dir=<dir> argument
# with a private copy of an existing profile on which Chrome has already started once,
# deletes the copy afterwards, and passes every other argument through unchanged.
# It does not need to be used on a machine where plain headless Chrome works.
#
# Environment:
#   CHROME_WARM_PROFILE  (required) directory of the profile to copy for each call
#   CHROME_BIN           Chrome executable (default: google-chrome)
#   CHROME_EXTRA_FLAGS   extra flags, split on spaces (default: --no-sandbox, which a
#                        container running as root needs; set it to an empty string
#                        on a normal desktop)
#
# Example:
#   CHROME_WARM_PROFILE=$HOME/chrome-warm-profile tools/chrome_warm_profile.sh \
#       --headless=new --user-data-dir=/tmp/x --screenshot=out.png file:///page.html
#   python tools/diversity_report.py run --chrome tools/chrome_warm_profile.sh ...
#
# The script reads and writes nothing else; it holds no credentials. The profile copy
# can contain whatever the profile contains, so do not use a profile of a signed-in
# browser.

set -u

if [ -z "${CHROME_WARM_PROFILE:-}" ] || [ ! -d "$CHROME_WARM_PROFILE" ]; then
  echo "chrome_warm_profile.sh: set CHROME_WARM_PROFILE to an existing profile directory" >&2
  exit 2
fi

chrome="${CHROME_BIN:-google-chrome}"
extra="${CHROME_EXTRA_FLAGS---no-sandbox}"

args=()
tmp=""
for a in "$@"; do
  case "$a" in
    --user-data-dir=*)
      tmp=$(mktemp -d "${TMPDIR:-/tmp}/chrome-warm-XXXXXX")
      cp -r "$CHROME_WARM_PROFILE"/. "$tmp"/
      args+=("--user-data-dir=$tmp") ;;
    *) args+=("$a") ;;
  esac
done

# shellcheck disable=SC2086
"$chrome" $extra "${args[@]}"
rc=$?
[ -n "$tmp" ] && rm -rf "$tmp"
exit "$rc"
