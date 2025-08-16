# Script para obtener la version actual
import subprocess

# Ejecuta los comandos en la terminal para determinar la version solo función en un entorno de git
def RunGit(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        return None

# Obtener información de Git
__branch__ = RunGit(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
__commit__ = RunGit(["git", "rev-parse", "HEAD"]) or "unknown"
__short_commit__ = RunGit(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
__tag__ = RunGit(["git", "describe", "--tags", "--abbrev=0"]) or "no-tag"

# Devuelve un diccionario con la información de version
def GetVersion():
    return {
        "branch": __branch__,
        "commit": __commit__,
        "short_commit": __short_commit__,
        "tag": __tag__
    }