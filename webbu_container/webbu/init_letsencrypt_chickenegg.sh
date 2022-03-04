#!/bin/bash
# This script comes from https://medium.com/@pentacent/nginx-and-lets-encrypt-with-docker-in-less-than-5-minutes-b4b8a60d3a71
# and it solves the chicken and egg problem for nginx-certbot:
# We need nginx to perform the Let’s Encrypt validation But nginx won’t start if the certificates are missing.
# So what do we do? Create a dummy certificate, start nginx, delete the dummy and request the real certificates.
# IMPORTANT: not 100% sure but last time it worked after I commented out the port 443 (https) server in nginx.conf and removed the www. subdomain


if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

domains=(webbu.app)
rsa_key_size=4096
data_path="./data/certbot"  # must be same path as the one used in docker_compose file
email="fersarr@gmail.com" # Adding a valid address is strongly recommended
staging=0 # Set to 1 if you're testing your setup to avoid hitting request limits
docker_compose_cmd="docker-compose -f docker-compose.prod.yml"

if [ -d "$data_path" ]; then
  read -p "Existing data found for $domains at $data_path. Continue and replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi


if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "### Creating dummy certificate for $domains ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
$docker_compose_cmd run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo


if [ "$RUNNING_LOCALHOST" = "1" ]; then
  # we are running HTTPS on local host, so self-signed certificate is all we can get to get nginx up
  echo "exit: localhost only requires self-signed certificate"
  exit
fi

echo "### Starting nginx ..."
$docker_compose_cmd up --force-recreate -d nginx
echo

echo "### Deleting dummy certificate for $domains ..."
$docker_compose_cmd run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot
echo


echo "### Requesting Let's Encrypt certificate for $domains ..."
#Join $domains to -d args
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

# Enable staging mode if needed
if [ $staging != "0" ]; then staging_arg="--staging"; fi

$docker_compose_cmd run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot
echo

echo "### Reloading nginx ..."
$docker_compose_cmd exec nginx nginx -s reload