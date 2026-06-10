def main():
    try:
        from gui.main_window import AthenaDesktopApp
    except ImportError as error:
        print("Não consegui iniciar a interface desktop da Athena.")
        print("Dependência provável ausente: customtkinter.")
        print("Instale com: pip install customtkinter")
        print(f"Detalhe técnico: {error}")
        return

    try:
        app = AthenaDesktopApp()
        app.mainloop()
    except Exception as error:
        print("A interface desktop não pôde ser aberta neste ambiente.")
        print("O núcleo da Athena continua disponível com: python main.py")
        print("Se a dependência estiver ausente, instale com: pip install customtkinter")
        print(f"Detalhe técnico: {error}")


if __name__ == "__main__":
    main()
