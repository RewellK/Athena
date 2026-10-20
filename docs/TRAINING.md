# Preparação para treinar uma LLM da Athena

Usar e adaptar pesos abertos é compatível com a arquitetura: a LLM continua sendo
um componente substituível. Não foi treinada uma nova LLM nesta entrega.

O laboratório local registra exemplos a partir de solicitações e ferramentas que
realmente foram executadas. Uma ação tecnicamente bem sucedida não garante que o
modelo entendeu o pedido; por isso, execução sem revisão não vira automaticamente
exemplo positivo de treino. Os dados permanecem na pasta privada da Athena.

```bash
python scripts/learning_lab.py status
python scripts/learning_lab.py review --run-id ID --accept --note "Resultado conferido"
python scripts/learning_lab.py export
```

A exportação produz JSONL de mensagens e chamadas de ferramentas em
`.athena_workspace/training`, separado em treino/validação por grupo de pedido.
O export não publica dados, treina pesos ou substitui o modelo instalado.
Os arquivos podem conter informação pessoal: são locais e não entram no ZIP/Git.

## Condições para treino de pesos

1. Reunir exemplos corretos suficientes e um conjunto de avaliação independente.
2. Escolher modelo-base com licença adequada e backend de treino compatível.
3. Medir RAM/tempo antes de iniciar LoRA/SFT; manter orçamento de recursos explícito.
4. Avaliar intenção, ferramentas, memória, erros e latência contra o modelo atual.
5. Importar candidato no Ollama somente se houver melhora demonstrada e rollback.

O Mac validado é Intel com 16 GB e inferência em CPU. Ele não pode usar MLX, que
exige Apple Silicon; não foi instalado um treinador CUDA/GPU incompatível nem
iniciado um treino de vários bilhões de parâmetros. Esta entrega fornece dados e
critérios, não um treino supostamente concluído. Treinar do zero um modelo geral
comparável aos atuais não é uma alternativa prática nesse hardware.

Para o uso atual, o avanço medido veio do executor, das ferramentas e da escolha
de um modelo local mais adequado. O aprendizado de procedimentos já ocorre sem
atualizar os pesos da LLM.
