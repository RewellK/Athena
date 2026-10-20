import os
from pathlib import Path

def _main():
    try:
        from gui.main_window import AthenaDesktopApp
    except ImportError as error:
        print("Não consegui iniciar a interface desktop da Athena.")
        print("Dependência provável ausente: customtkinter.")
        print("Instale com: pip install customtkinter")
        print(f"Detalhe técnico: {error}")
        raise

    try:
        app = AthenaDesktopApp()
        Path("logs/gui.pid").write_text(str(os.getpid()))
        try:
            app.mainloop()
        finally:
            from runtime.process_lease import close_core
            if hasattr(app,'presence_panel'):app.presence_panel.stop_enrollment()
            if hasattr(app.chat_panel,'voice_input'):
                app.chat_panel.voice_input.cancel()
            app.athena.cancel_current_turn(reason='shutdown')
            app.task_runner.shutdown()
            close_core(app.athena)
            Path("logs/gui.pid").unlink(missing_ok=True)
    except Exception as error:
        print("A interface desktop não pôde ser aberta neste ambiente.")
        print("O núcleo da Athena continua disponível com: python main.py")
        print("Se a dependência estiver ausente, instale com: pip install customtkinter")
        print(f"Detalhe técnico: {error}")
        raise


def main():
    import os
    from pathlib import Path
    from runtime.process_lease import foreground_session
    from desktop.paths import prepare_home
    os.chdir(prepare_home())
    os.umask(0o077)
    with foreground_session():
        _main()


if __name__ == "__main__":
    main()
