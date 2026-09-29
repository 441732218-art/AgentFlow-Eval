#!/bin/sh
# (c) 2026 AgentFlow-Eval
# Write /runtime-config.json and the nginx DEFAULT_API_KEY placeholder.
#
# By default no key is published: runtime-config.json carries an empty apiKey and nginx
# forwards only the X-API-Key sent by the browser (users sign in through the API key gate).
# Single-user private stacks may opt in with PRIVATE_STACK_AUTO_API_KEY=true, which publishes
# the first API_KEYS secret to anyone who can reach this container. Never enable it on a
# network-reachable deployment.
set -eu

HTML_ROOT="${HTML_ROOT:-/usr/share/nginx/html}"
CONFIG_PATH="${HTML_ROOT}/runtime-config.json"
NGINX_CONF="${NGINX_CONF:-/etc/nginx/conf.d/default.conf}"

extract_first_secret() {
  raw="${API_KEYS:-}"
  if [ -z "$raw" ]; then
    printf ''
    return
  fi
  first=$(printf '%s' "$raw" | cut -d',' -f1)
  secret=$(printf '%s' "$first" | cut -d':' -f1)
  printf '%s' "$secret" | tr -d ' \t\r\n'
}

SECRET=""
if [ "${PRIVATE_STACK_AUTO_API_KEY:-false}" = "true" ]; then
  SECRET=$(extract_first_secret)
fi

if [ -n "$SECRET" ]; then
  # Minimal JSON escape for " and \
  escaped=$(printf '%s' "$SECRET" | awk 'BEGIN{ORS=""} {gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); print}')
  printf '{"apiKey":"%s","authHint":"private-docker"}\n' "$escaped" > "$CONFIG_PATH"
  echo "[agentflow-frontend] PRIVATE_STACK_AUTO_API_KEY=true: API key published via runtime-config.json and nginx"
else
  printf '{"apiKey":"","authHint":"sign-in"}\n' > "$CONFIG_PATH"
  echo "[agentflow-frontend] runtime-config.json has no API key (sign in through the API key gate)"
fi

# Replace @@DEFAULT_API_KEY@@ in nginx conf (awk avoids sed delimiter issues).
# An empty value makes nginx drop the X-API-Key header instead of injecting a key.
if [ -f "$NGINX_CONF" ]; then
  TMP="${NGINX_CONF}.tmp.$$"
  DEFAULT_API_KEY="$SECRET" awk '
    {
      key = ENVIRON["DEFAULT_API_KEY"]
      while (match($0, /@@DEFAULT_API_KEY@@/)) {
        $0 = substr($0, 1, RSTART-1) key substr($0, RSTART+RLENGTH)
      }
      print
    }
  ' "$NGINX_CONF" > "$TMP"
  mv "$TMP" "$NGINX_CONF"
fi

# Validate nginx config before taking over PID 1
nginx -t
exec nginx -g "daemon off;"
