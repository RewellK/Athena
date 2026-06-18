# BackgroundCognitionLoop

`BackgroundCognitionLoop` executa ciclos pequenos do runtime.

Na V13-pre ele fica desativado por padrao, para evitar processamento inesperado.

Ele pode:

- chamar `RuntimeSupervisor.run_once()`;
- respeitar pausa;
- respeitar safe mode;
- dormir entre ciclos;
- parar com segurança.

Ele nao deve chamar LLM pesada por padrao, usar fontes externas sem necessidade ou bloquear GUI/chat.
