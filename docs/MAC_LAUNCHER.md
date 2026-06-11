# Athena Mac Launcher

Este launcher permite iniciar a GUI da Athena pelo Finder no macOS.

## Como usar

1. Abra a pasta do projeto no Finder.
2. Dê duplo clique em `Athena.command`.
3. Se o macOS pedir permissão, autorize a execução do arquivo.

O launcher chama `scripts/start_gui.sh`, entra na raiz do projeto, ativa `venv`
quando ele existe e inicia `app.py`.

## Dependências

A GUI precisa de `customtkinter`. Se o launcher mostrar erro de dependência,
instale as dependências no ambiente virtual do projeto e tente novamente.

## Voz

Por padrão, a voz vem desligada em `config/settings.json` para manter a primeira
execução rápida e previsível. No macOS, o provider padrão é `macos_say`.
