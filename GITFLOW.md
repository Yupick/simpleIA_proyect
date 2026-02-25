# Gitflow - Guía rápida

Este repositorio usa el modelo Gitflow para organizar el desarrollo.

Principios básicos
- `main` (o `master`): rama de producción. Código estable listo para release.
- `develop`: rama de integración diaria. Todas las features se integran aquí.
- `feature/*`: ramas de trabajo para nuevas funcionalidades, creadas desde `develop`.
- `release/*`: ramas para preparar releases, creadas desde `develop`.
- `hotfix/*`: correcciones urgentes sobre `main`, creadas desde `main`.

Convenciones de nombres
- Features: `feature/nombre-descriptivo`
- Releases: `release/x.y.z`
- Hotfixes: `hotfix/desc-corta`

Flujo de trabajo (comandos comunes)

1) Crear feature desde `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/mi-feature
```

2) Finalizar feature y merge a `develop` (usando PR):

```bash
git push -u origin feature/mi-feature
# Abrir pull request a develop, revisión y merge
```

3) Preparar release:

```bash
git checkout develop
git pull origin develop
git checkout -b release/1.2.0
# Ajustes menores, actualizar versión y changelog
git push -u origin release/1.2.0
# Abrir PR desde release/1.2.0 a main y develop (si procede)
```

4) Hotfix (corrección urgente en producción):

```bash
git checkout main
git pull origin main
git checkout -b hotfix/urgente-fix
# Aplicar fix
git push -u origin hotfix/urgente-fix
# Abrir PR a main y luego merge también a develop
```

Recomendaciones
- Protege ramas `main` y `develop` en el repositorio remoto (requiere PRs y revisiones).
- Usa CI que ejecute tests y linters en PRs hacia `develop` y `main`.
- No hagas force-push a `develop` o `main`.
- Añade plantillas de PR que pidan: descripción, testing realizado, cambios migración/DB.

Automatización
- Si quieres usar la extensión `git-flow` (que facilita comandos), instala `git-flow` o `git-flow-avh`.
- En este repo hay un script `scripts/gitflow-init.sh` para crear las ramas básicas si no existen.

Soporte
Si quieres que yo configure hooks, protección de ramas (a través de GitHub API) o plantillas de PR, dime y lo implemento.
