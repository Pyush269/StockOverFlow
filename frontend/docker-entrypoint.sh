#!/bin/sh
set -eu
# Substitute only this setting; preserve Nginx variables such as $uri and $host.
case "${API_UPSTREAM:-}" in
  ''|*[!a-zA-Z0-9.:-]*) echo 'API_UPSTREAM must be a hostname:port' >&2; exit 1 ;;
esac
case "${NGINX_RESOLVER:-}" in
  ''|*[!a-zA-Z0-9.:-]*) echo 'NGINX_RESOLVER must be a DNS server address' >&2; exit 1 ;;
esac
envsubst '${API_UPSTREAM} ${NGINX_RESOLVER}' < /etc/nginx/templates/stockflow.conf.template > /tmp/stockflow.conf
exec "$@"
