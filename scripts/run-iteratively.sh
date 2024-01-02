#!/usr/bin/env bash
set -euo pipefail


export RPICAM_TG_CHAT_ID=
export RPICAM_TG_API_TOKEN=
export LD_LIBRARY_PATH='/system/lib64:/data/data/com.termux/files/usr/lib'
while true; do
    rpicam cam timelapse --spf 5 --duration 1 --post_to_tg --rotating --out ./rpicam_output/
    sleep 10
done
