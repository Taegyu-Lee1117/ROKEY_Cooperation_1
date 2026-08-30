#!/usr/bin/env bash

set -eo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
DSR_WORKSPACE="${DSR_WORKSPACE:-$(dirname "$PROJECT_DIR")/ws_dsr}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export DATABASE_URL="${DATABASE_URL:-postgresql://icecream:icecream@127.0.0.1:5432/icecream_db}"

if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL이 실행 중이 아닙니다."
    echo "먼저 실행하세요: sudo systemctl start postgresql"
    exit 1
fi

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
    echo "FastAPI 가상환경이 없습니다: $BACKEND_DIR/.venv"
    echo "backend에서 python3 -m venv .venv 후 requirements.txt를 설치하세요."
    exit 1
fi

if [[ ! -f "$DSR_WORKSPACE/install/setup.bash" ]]; then
    echo "Doosan ROS 2 설치 파일이 없습니다: $DSR_WORKSPACE/install/setup.bash"
    echo "다른 위치라면 DSR_WORKSPACE 환경변수로 지정하세요."
    exit 1
fi

if [[ ! -f "$PROJECT_DIR/install/setup.bash" ]]; then
    echo "프로젝트가 빌드되지 않았습니다. 먼저 colcon build를 실행하세요."
    exit 1
fi

source /opt/ros/jazzy/setup.bash
source "$DSR_WORKSPACE/install/setup.bash"
source "$PROJECT_DIR/install/setup.bash"

cleanup() {
    if [[ -n "${FASTAPI_PID:-}" ]] && kill -0 "$FASTAPI_PID" 2>/dev/null; then
        kill "$FASTAPI_PID" 2>/dev/null || true
        wait "$FASTAPI_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

(
    cd "$BACKEND_DIR"
    exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
FASTAPI_PID=$!

echo "FastAPI PID: $FASTAPI_PID"
echo "키오스크: http://127.0.0.1:8000/kiosk"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

ros2 launch icecream_pj icecream_system.launch.py "$@"
