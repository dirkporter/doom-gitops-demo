#!/usr/bin/env bash
# Proves the API -> PostgreSQL path end to end WITHOUT needing the real DOOM
# image. Run against a cluster where the doom-demo app is synced and healthy.
set -euo pipefail

NS=doom-demo

echo "== Port-forwarding the API service to localhost:8080 =="
oc -n "$NS" port-forward svc/doom-api-service 8080:80 >/tmp/pf.log 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT
sleep 3

echo "== Health check =="
curl -sf http://localhost:8080/healthz && echo

echo "== Posting a sample level completion =="
curl -sf -X POST http://localhost:8080/level-complete \
  -H 'Content-Type: application/json' \
  -d '{"player_id":"doomguy","level":"E1M1","time_seconds":42}' && echo

echo "== Reading it back from the DB via the API =="
curl -sf http://localhost:8080/scores && echo

echo
echo "If you saw the row above, the Deployment -> Service -> VM(Postgres) path works."
echo "To inspect Postgres directly on the VM:"
echo "  virtctl -n $NS console doom-db-vm     # login admin / Password123"
echo "  sudo -u postgres psql -d doom_stats -c 'SELECT * FROM level_times;'"
