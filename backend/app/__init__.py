"""Aura backend.

Używamy SYSTEMOWEGO magazynu certów (truststore) zamiast wbudowanego certifi —
dzięki temu klienci HTTP (httpx, urllib) respektują CA skonfigurowane w systemie
(korporacyjne proxy / antywirus w dev, poprawne CA w produkcji). Bez tego
przechwytywanie TLS wywala żądania, a robots.txt cicho przechodzi w allow-all.
"""

import truststore

truststore.inject_into_ssl()
