#!/bin/bash

PREVIEW_BROWSER=google-chrome-stable

if [ $# -eq 0 ]; then
  echo "Supply filename as argument"
  exit 1;
fi

print_usage() {
  printf "Usage: ..."
  printf "-f somefile.md"
}

while getopts 'f:' flag; do
  case "${flag}" in
    f) files="${OPTARG}" ;;
    *) print_usage
       exit 1 ;;
  esac
done

filepath=$(realpath "$files")
directory=$(dirname "$filepath")
filename=$(basename -- "$filepath")
extension="${filename##*.}"
filename="${filename%.*}"
first_run=true

#echo "(VP): $files"
cd "$directory"
echo "(VP) Rendering: $filepath"

if [ ! -f "$filepath" ]; then
  echo "(VP) Input file not found"
  exit 1;
fi

clean_up() {
  notify-send "VimPreview" "Stopped." --urgency=critical --expire-time=5000;
  kill -9 $(jobs -p %1) > /dev/null  2>&1;
  #pkill $PREVIEW_BROWSER;
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM 

TMP_DIR=$(mktemp -d -t ci-XXXXXXXXXX);
echo "(VP) Current directory: $(pwd)";
echo "(VP) Temp directory: $TMP_DIR";

if [ ! -d "./figures" ]; then
  mkdir ./figures;
fi

ln -s "$(realpath ./figures)" $TMP_DIR/figures

while true; do
  outfile="$TMP_DIR/$filename.html"
  just --justfile "$(dirname "$(realpath "$0")")/../justfile" compile-html "$filepath" "$outfile" '' \
    && echo "(VP) HTML converted at: $outfile";
  if [ "$first_run" = true ]; then
    echo "(VP) First run"
    $PREVIEW_BROWSER "$outfile" > /dev/null 2>&1 &
    disown;
    first_run="false";
  else
    echo "Reload browser."
    #$PREVIEW_BROWSER "$outfile" > /dev/null 2>&1 &
    #$PREVIEW_BROWSER ':reload';
  fi
  inotifywait -e CLOSE_WRITE -r "$directory" --exclude '.*\.pdf' -qq;
  echo "File change detected."
done
clean_up
