# Voice Configuration

## Estado padrao

A voz fica desligada por padrao:

```json
"voiceEnabled": false
```

Isso mantem a GUI rapida e evita falhas de TTS no primeiro uso.

## Providers

Providers suportados:

- `none`: nao fala.
- `macos_say`: usa o comando `say` do macOS.
- `piper`: usa Piper local quando `piperModelPath` esta configurado.
- `online_tts` / `openai_tts`: placeholders para futuro; nao exigem segredo no repo.

## Configuracoes principais

```json
"voiceProvider": "macos_say",
"fallbackVoiceProvider": "macos_say",
"voiceSpeakResponses": true,
"voiceSpeakStartupGreeting": false,
"voiceRate": 180,
"voiceVolume": 0.8,
"voiceName": null
```

## Garantia V12.6

A voz nao deve bloquear a resposta textual. `VoiceEngine` submete TTS em thread de fundo. Falhas de voz devem ser logadas e nao quebrar o chat.

## Como ativar

No `config/settings.json`:

```json
"voiceEnabled": true,
"voiceProvider": "macos_say"
```

Reinicie a GUI depois de alterar configuracoes manualmente.
