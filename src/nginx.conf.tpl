server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  charset utf-8;
  absolute_redirect off;
  port_in_redirect off;
  gzip on; gzip_comp_level 6; gzip_min_length 512;
  gzip_types text/css application/javascript application/json image/svg+xml text/plain;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
  add_header Cross-Origin-Opener-Policy same-origin always;
  add_header Content-Security-Policy "__CSP__" always;
  # preview host: keep it out of search engines until the real domain goes live
  set $robots "";
  if ($host ~* "mintapis\.com$") { set $robots "noindex, nofollow"; }
  add_header X-Robots-Tag $robots always;
  location = /robots.txt { default_type text/plain; if ($host ~* "mintapis\.com$") { return 200 "User-agent: *\nDisallow: /\n"; } try_files /robots.txt =404; }
  location ~ ^/en(?:/(.*))?$ { return 301 /$1; }
  location = /healthz { access_log off; default_type text/plain; return 200 "ok\n"; }
  location ~* \.(woff2|avif|webp|png|jpg|svg|mp4|webm|css|js)$ { add_header Cache-Control "public, max-age=31536000, immutable"; add_header X-Content-Type-Options nosniff always; add_header X-Robots-Tag $robots always; try_files $uri =404; }
  location ~* \.(json)$ { add_header Cache-Control "public, max-age=3600"; add_header X-Content-Type-Options nosniff always; add_header X-Robots-Tag $robots always; try_files $uri =404; }
  location / { add_header Cache-Control "public, max-age=300"; add_header X-Content-Type-Options nosniff always; add_header Referrer-Policy strict-origin-when-cross-origin always; add_header Content-Security-Policy "__CSP__" always; add_header X-Robots-Tag $robots always; try_files $uri $uri/ =404; }
  error_page 404 /404.html;
}
