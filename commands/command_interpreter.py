import unicodedata


class CommandInterpreter:
    def interpret(self, text):
        normalized = self._normalize(text)
        words = normalized.split()
        if not words:
            return {}
        word_set = set(words)
        if word_set & {"v12", "v13"} and word_set & {"pronta", "preparada", "ready"}:
            return {}

        approval = self._approval_command(normalized, words)
        if approval:
            return approval

        edit = self._edit_command(text, normalized, words)
        if edit:
            return edit

        if self._has(normalized, ["comando aprendizagem", "modo aprendizagem", "iniciar aprendizagem", "comecar a aprender", "começar a aprender", "athena aprender", "athena iniciar aprendizado", "entrar em modo de aprendizado"]):
            return {"command": "start_learning", "mode": "aprendizagem"}
        if self._has(normalized, ["parar de aprender", "encerrar aprendizado", "encerrar aprendizagem", "fechar modo aprendizagem", "parar aprendizagem", "finalizar aprendizagem"]):
            return {"command": "stop_learning", "mode": "aprendizagem"}
        if self._has(normalized, ["status aprendizagem", "status aprendizado"]):
            return {"command": "learning_status", "mode": "aprendizagem"}
        learned_topic = self._learned_topic(normalized)
        if learned_topic:
            return {"command": "learned_about_topic", "topic": learned_topic}
        if self._has(normalized, ["relatorio aprendizagem", "relatorio aprendizado", "revisar aprendizagem", "mostrar aprendizados", "o que voce aprendeu durante o aprender"]):
            return {"command": "learning_report", "mode": "aprendizagem"}

        if self._is_study_command(normalized):
            return {"command": "study_day", "mode": "estudo"}
        if self._is_study_report_command(normalized):
            return {"command": "study_report", "mode": "estudo"}

        if self._has(normalized, ["comando diagnostico", "diagnostico runtime", "diagnostico do runtime"]):
            return {"command": "diagnostic", "mode": "diagnostico"}
        if self._has(normalized, ["desligar runtime", "encerrar runtime", "parar runtime", "shutdown runtime"]):
            return {"command": "stop_runtime", "mode": "status"}
        if self._has(normalized, ["iniciar runtime", "ligar runtime", "start runtime"]):
            return {"command": "start_runtime", "mode": "status"}
        if self._has(normalized, ["comando silencio", "pausar processos internos", "modo silencio", "pausar runtime", "pause runtime"]):
            return {"command": "silence", "mode": "silencio"}
        if self._has(normalized, ["athena retomar", "retomar processos internos", "sair do silencio", "retomar runtime", "resume runtime"]):
            return {"command": "resume_runtime", "mode": "silencio"}
        if self._has(normalized, ["comando status", "athena status", "qual seu status", "voce esta acordada", "voce esta processando algo", "tem algo aguardando minha aprovacao", "voce esta em modo seguro", "como voce esta", "voce esta pronta", "o que voce esta fazendo", "voce tem pendencias"]):
            return {"command": "runtime_status", "mode": "status"}
        if self._has(normalized, ["listar comandos", "palheta de comandos", "quais comandos"]):
            return {"command": "list_commands", "mode": "status"}
        return {}

    def _learned_topic(self, normalized):
        prefix = "o que voce aprendeu sobre "
        if normalized.startswith(prefix):
            topic = normalized[len(prefix):].strip()
            return topic
        return ""

    def _is_study_command(self, normalized):
        exact = {
            "comando estudar",
            "athena comando estudar",
            "estudar o dia",
            "athena estudar o dia",
            "estudar nossa conversa",
            "athena estudar nossa conversa",
            "revisar o que falamos hoje",
            "athena revisar o que falamos hoje",
            "modo estudo",
            "athena modo estudo",
            "processar aprendizados de hoje",
            "athena processar aprendizados de hoje",
        }
        return normalized in exact

    def _is_study_report_command(self, normalized):
        exact = {
            "relatorio do estudo",
            "athena relatorio do estudo",
            "o que voce achou interessante",
            "athena o que voce achou interessante",
            "o que voce aprendeu hoje",
            "athena o que voce aprendeu hoje",
            "o que voce separou",
            "athena o que voce separou",
            "revisar estudo",
            "athena revisar estudo",
            "me mostra o que vale guardar",
            "athena me mostra o que vale guardar",
        }
        return normalized in exact

    def _approval_command(self, normalized, words):
        if not words:
            return {}
        if words[0] in {"aprovar", "aprove"} and ("aprendizado" in words or "aprendizados" in words or "candidato" in words or "candidatos" in words):
            return {"command": "approve_learning", "identifiers": self._numbers(words)}
        if words[0] in {"rejeitar", "rejeite"} and ("aprendizado" in words or "candidato" in words):
            return {"command": "reject_learning", "identifiers": self._numbers(words)}
        if "consolidar aprovados" in normalized or "consolidar aprendizados aprovados" in normalized:
            return {"command": "consolidate_approved"}
        if "descartar rejeitados" in normalized or "descartar aprendizados rejeitados" in normalized:
            return {"command": "discard_rejected"}
        if normalized in {"nao salve isso", "isso era so conversa descarta", "descarta isso"}:
            return {"command": "reject_learning", "identifiers": ["1"]}
        return {}

    def _edit_command(self, raw, normalized, words):
        if not words or words[0] not in {"editar", "edite"}:
            return {}
        identifiers = self._numbers(words)
        marker = ":"
        new_content = ""
        if marker in str(raw):
            new_content = str(raw).split(marker, 1)[1].strip()
        elif " para " in normalized:
            new_content = str(raw).split(" para ", 1)[1].strip()
        if identifiers and new_content:
            return {"command": "edit_learning", "identifiers": identifiers[:1], "content": new_content}
        return {}

    def _numbers(self, words):
        numbers = []
        for word in words:
            clean = "".join(char for char in word if char.isdigit())
            if clean:
                numbers.append(clean)
        return numbers

    def _has(self, normalized, phrases):
        return any(phrase in normalized for phrase in phrases)

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return " ".join("".join(chars).split())
