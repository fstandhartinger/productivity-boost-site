FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html impressum.html datenschutz.html styles.css logo.svg favicon.svg robots.txt /usr/share/nginx/html/
COPY en /usr/share/nginx/html/en
EXPOSE 8080
HEALTHCHECK CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
