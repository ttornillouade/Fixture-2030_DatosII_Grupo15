#!/bin/sh
# Corre DENTRO del contenedor (lo invoca scripts/cargar_clases.sh).
# Reemplaza la contraseña por defecto (SYS) de _SYSTEM, SuperUser y Admin por la de .env
# (variable IRIS_PASSWORD del compose) y evita el cambio forzado en el primer login.
# Es idempotente: se puede repetir.

iris session IRIS -U %SYS <<'EOF'
set clave = $SYSTEM.Util.GetEnviron("IRIS_PASSWORD")
if clave = "" { write "AVISO: IRIS_PASSWORD vacío, se mantiene la contraseña actual",! }
if clave '= "" { for usuario = "_SYSTEM", "SuperUser", "Admin" { kill p  set p("Password") = clave, p("ChangePassword") = 0, p("PasswordNeverExpires") = 1  set sc = ##class(Security.Users).Modify(usuario, .p)  write "Usuario ", usuario, ": ", $SELECT(sc: "contraseña local aplicada", 1: $SYSTEM.Status.GetErrorText(sc)), ! } }
halt
EOF
