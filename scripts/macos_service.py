"""Optional per-user LaunchAgent. Nothing is installed until 'install' is invoked."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = "local.athena.resident"


def specification(python=None):
    return {"Label": LABEL, "ProgramArguments": [str(Path(python or sys.executable).absolute()),
            str(ROOT / "resident.py")], "WorkingDirectory": str(ROOT),
        "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 30,
        "ProcessType": "Background", "Umask": 0o077,
        "StandardOutPath": str(ROOT / "logs/resident.stdout.log"),
        "StandardErrorPath": str(ROOT / "logs/resident.stderr.log")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["print", "install", "uninstall", "status", "start", "stop"])
    args = parser.parse_args()
    if args.action == "print":
        print(plistlib.dumps(specification()).decode())
        return
    if sys.platform != "darwin":
        parser.error("launchd está disponível apenas no macOS")
    target = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
    domain = f"gui/{os.getuid()}"
    service = domain + "/" + LABEL
    if args.action == "install":
        (ROOT / "logs").mkdir(exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and plistlib.loads(target.read_bytes()).get("ProgramArguments") != specification()["ProgramArguments"]:
            parser.error("Outro diretório já usa este serviço. Desinstale o serviço anterior primeiro.")
        target.write_bytes(plistlib.dumps(specification()))
        target.chmod(0o600)
        if subprocess.run(["launchctl", "print", service], capture_output=True).returncode:
            subprocess.run(["launchctl", "bootstrap", domain, str(target)], check=True)
        print("Athena instalada para este usuário. Início automático ao entrar na sessão.")
    elif args.action == "uninstall":
        subprocess.run(["launchctl", "bootout", service], capture_output=True)
        target.unlink(missing_ok=True)
        print("Serviço removido. Memória preservada.")
    elif args.action == "status":
        subprocess.run(["launchctl", "print", service], check=True)
    elif args.action == "stop":
        subprocess.run(["launchctl", "bootout", service], check=True)
    elif args.action == "start":
        subprocess.run(["launchctl", "bootstrap", domain, str(target)], check=True)


if __name__ == "__main__":
    main()
