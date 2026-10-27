#!/usr/bin/env bash
set -euo pipefail

release_dir="${1:?usage: deploy.sh <release-directory>}"
project_name="${PROJECT_NAME:-triageiq}"
environment="${ENVIRONMENT:-prod}"
parameter_prefix="/${project_name}/${environment}"
runtime_env="/etc/triageiq/runtime.env"
artifacts_dir="/opt/triageiq/artifacts"

get_parameter() {
  aws ssm get-parameter --name "$1" --with-decryption --query 'Parameter.Value' --output text
}

test -f "${release_dir}/docker-compose.yml"
test -f "${release_dir}/artifacts/classifier.joblib"
test -f "${release_dir}/artifacts/metadata.json"

umask 077
{
  printf 'POSTGRES_PASSWORD=%s\n' "$(get_parameter "${parameter_prefix}/postgres-password")"
  printf 'GATEWAY_HTPASSWD=%s\n' "$(get_parameter "${parameter_prefix}/gateway-htpasswd")"
  printf 'SMOKE_PASSWORD=%s\n' "$(get_parameter "${parameter_prefix}/smoke-password")"
  printf '%s\n' 'SMOKE_USER=smoke'
  printf '%s\n' 'GATEWAY_BIND_ADDRESS=0.0.0.0'
  printf '%s\n' 'GATEWAY_PORT=80'
  printf 'ARTIFACTS_DIR=%s\n' "${artifacts_dir}"
} >"${runtime_env}"
chmod 600 "${runtime_env}"

cp -a "${release_dir}/artifacts/." "${artifacts_dir}/"
chown -R triageiq:triageiq "${artifacts_dir}"

cd "${release_dir}"
docker compose --env-file "${runtime_env}" -p "${project_name}" \
  up -d --build --remove-orphans gateway backend-api feedback-service model-service postgres

for _ in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1/healthz >/dev/null \
    && curl --fail --silent --show-error http://127.0.0.1:8002/health >/dev/null; then
    break
  fi
  sleep 5
done

curl --fail --silent --show-error http://127.0.0.1/healthz >/dev/null
curl --fail --silent --show-error http://127.0.0.1:8002/health >/dev/null
docker compose --env-file "${runtime_env}" -p "${project_name}" ps
