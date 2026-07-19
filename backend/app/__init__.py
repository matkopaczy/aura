"""Aura backend.

Używamy SYSTEMOWEGO magazynu certów (truststore) zamiast wbudowanego certifi —
dzięki temu klienci HTTP (httpx, urllib) respektują CA skonfigurowane w systemie
(korporacyjne proxy / antywirus w dev, poprawne CA w produkcji). Bez tego
przechwytywanie TLS wywala żądania, a robots.txt cicho przechodzi w allow-all.
"""

import os

import truststore

# Antywirus (Avast/AVG) wstrzykuje procesom SSLKEYLOGFILE wskazujące na jego
# urządzenie proxy (\\.\aswMonFltProxy\<uchwyt>). Uchwyt jest per-proces i
# dezaktualizuje się, gdy antywirus zrestartuje sterownik — proces długożyjący
# (scheduler) dostaje wtedy PermissionError przy KAŻDEJ nowej sesji TLS
# (incydent 2026-07-19: 32/32 nocnych jobów padło). Keylog to funkcja czysto
# debugowa — usuwamy zmienną; weryfikacja certyfikatów (truststore) zostaje
# nietknięta.
os.environ.pop("SSLKEYLOGFILE", None)

truststore.inject_into_ssl()
