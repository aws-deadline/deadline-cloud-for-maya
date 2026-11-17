#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Forward the developer-license manager and vendor daemon, then run GUI tests.
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${LICENSE_ROLE_ARN:?Set LICENSE_ROLE_ARN}"
: "${BASTION_INSTANCE_TAG:?Set BASTION_INSTANCE_TAG}"
: "${RUNNER_TEMP:?Set RUNNER_TEMP}"
logs="$RUNNER_TEMP/integ_gui"
mkdir -p "$logs"

aws configure set profile.license.role_arn "$LICENSE_ROLE_ARN"
aws configure set profile.license.credential_source Environment
aws configure set profile.license.region "$AWS_REGION"
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$BASTION_INSTANCE_TAG" "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].InstanceId' \
    --profile license --region "$AWS_REGION" --output json > "$logs/bastions.json"
bastion=$(python3.11 - "$logs/bastions.json" <<'PY'
import json
import sys
from pathlib import Path

instances = json.loads(Path(sys.argv[1]).read_text())
if len(instances) != 1:
    raise SystemExit(f"Expected one licensing bastion, found {len(instances)}")
print(instances[0])
PY
)

pids=()
cleanup() {
    # Autodesk writes its diagnostics to files rather than service stdout.
    if [[ -d /var/opt/Autodesk/AdskLicensingService/Log ]]; then
        mkdir -p "$logs/licensing"
        for log in /var/opt/Autodesk/AdskLicensingService/Log/*.log; do
            [[ -f "$log" ]] || continue
            sed -E 's/ENCODED\{[^}]*\}/<encoded licensing message omitted>/g' "$log" \
                > "$logs/licensing/$(basename "$log")" || true
        done
    fi
    ps -eo pid,ppid,pgid,nlwp,args > "$logs/processes.txt" || true
    # Read every session log, including a session whose port never became ready.
    for log in "$logs"/ssm_*.log; do
        [[ -f "$log" ]] || continue
        while read -r session; do
            aws ssm terminate-session --session-id "$session" \
                --profile license --region "$AWS_REGION" || true
        done < <(sed -nE 's/.*SessionId: ([A-Za-z0-9._-]+).*/\1/p' "$log")
    done
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
for port in 27002 2702; do
    aws ssm start-session --target "$bastion" \
        --document-name DccInteg-PortForwardToLicenseServer \
        --parameters "{\"portNumber\":[\"$port\"],\"localPortNumber\":[\"$port\"]}" \
        --profile license --region "$AWS_REGION" > "$logs/ssm_$port.log" 2>&1 &
    pids+=("$!")
    if ! python3.11 - "$port" "${pids[-1]}" <<'PY'
import os
import socket
import sys
import time

port, pid = map(int, sys.argv[1:])
deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            print(f"License port {port} forwarded")
            break
    except ProcessLookupError:
        raise SystemExit(f"License tunnel for port {port} exited")
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"License port {port} not forwarded after 60s")
PY
    then
        cat "$logs/ssm_$port.log"
        exit 1
    fi
done

hatch run integ-gui:test-linux -- --basetemp "$logs/tests" -rA -x
