#!/bin/bash
# kicad-cli with a hard timeout: it hangs rather than failing on some malformed inputs.
T=${KCLI_TIMEOUT:-120}
CLI=${KICAD_CLI:-}
if [ -z "$CLI" ]; then CLI=$(command -v kicad-cli || true); fi
if [ -z "$CLI" ]; then CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli; fi
if [ ! -x "$CLI" ]; then
  printf 'Set KICAD_CLI to the KiCad 10 command-line executable.\n' >&2
  exit 127
fi
perl -e 'alarm shift; exec @ARGV' "$T" "$CLI" "$@" 2> >(grep -v Fontconfig >&2)
