#!/bin/sh
# (c) 2026 AgentFlow-Eval
# Write /runtime-config.json from API_KEYS so the SPA can bootstrap auth.
# Also rewrite nginx DEFAULT_API_KEY placeholder for proxy-side injection.
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

SECRET=$(extract_first_secret)

if [ -n "$SECRET" ]; then
  # Minimal JSON escape for " and \
  escaped=$(printf '%s' "$SECRET" | awk 'BEGIN{ORS=""} {gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); print}')
  printf '{"apiKey":"%s","authHint":"private-docker"}\n' "$escaped" > "$CONFIG_PATH"
  echo "[agentflow-frontend] runtime-config.json written (apiKey length=${#SECRET})"
else
  printf '{"apiKey":"","authHint":"no-api-keys-env"}\n' > "$CONFIG_PATH"
  echo "[agentflow-frontend] runtime-config.json empty (set API_KEYS to auto-bootstrap)"
fi

# Replace @@DEFAULT_API_KEY@@ in nginx conf (awk avoids sed delimiter issues)
if [ -f "$NGINX_CONF" ]; then
  TMP="${NGINX_CONF}.tmp.$$"
  # Use a rare RS so we can still process line-by-line; inject key via ENV
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
  echo "[agentflow-frontend] nginx DEFAULT_API_KEY substituted (len=${#SECRET})"
fi

# Validate nginx config before taking over PID 1
nginx -t
exec nginx -g "daemon off;"
