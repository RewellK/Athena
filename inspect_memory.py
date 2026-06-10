from memory.database import MemoryDB
from core.settings import Settings
from error_awareness.error_capture import ErrorCapture
from core.logger import AthenaLogger
from git_awareness.git_awareness_engine import GitAwarenessEngine
from self_code_awareness.self_code_awareness_engine import SelfCodeAwarenessEngine


def inspect():
    db = MemoryDB()

    print("\n=== DEFINIÇÕES ===\n")
    for concept, meaning in db.list_definitions():
        print(f"{concept} -> {meaning}")

    print("\n=== RELACIONAMENTOS ===\n")
    for source, relation, target, created_at in db.list_relationships():
        print(f"{source} -> {relation} -> {target} ({created_at})")

    print("\n=== OBJETIVOS ===\n")
    for owner, goal, status, priority, created_at in db.list_goals():
        print(f"{owner} -> {goal} | {status} | {priority} ({created_at})")

    print("\n=== EVENTOS ===\n")
    for event_id, name, event_date, description, created_at in db.list_events():
        print(f"{event_id} -> {name} | {event_date} | {description} ({created_at})")
        for person, role in db.list_event_participants(event_id):
            print(f"    - {person} ({role})")

    print("\n=== SHORT-TERM MEMORY ===\n")
    for row in db.list_short_term_memory(include_expired=True):
        memory_id, content, content_hash, created_at, expires_at, importance_score, processed = row
        print(f"{memory_id} | score={importance_score} | processed={processed}")
        print(f"    criado: {created_at} | expira: {expires_at}")
        print(f"    hash: {content_hash[:16]}...")
        print(f"    conteúdo: {content}")

    print("\n=== MID-TERM MEMORY ===\n")
    for row in db.list_mid_term_memory(include_expired=True):
        memory_id, summary, topics, source_count, created_at, expires_at, importance_score, promoted = row
        print(f"{memory_id} | fontes={source_count} | score={importance_score} | promoted={promoted}")
        print(f"    criado: {created_at} | expira: {expires_at}")
        print(f"    tópicos: {topics}")
        print(f"    resumo: {summary}")

    print("\n=== PROMOÇÕES DE MEMÓRIA ===\n")
    for source_layer, target_layer, content, reason, created_at in db.list_memory_promotions():
        print(f"{created_at} | {source_layer} -> {target_layer}")
        print(f"    conteúdo: {content}")
        print(f"    motivo: {reason}")

    print("\n=== DECISÕES DE APRENDIZADO ===\n")
    for input_text, action, category, score, reason, saved, created_at in db.list_learning_decisions():
        saved_text = "salvo" if saved else "não salvo"
        print(f"{created_at} | {action} | {category} | score={score} | {saved_text}")
        print(f"    entrada: {input_text}")
        print(f"    motivo: {reason}")

    print("\n=== LONG-TERM MEMORY REAL ===\n")
    for memory_id, content, source, importance_score, created_at in db.list_long_term_memory():
        print(f"{memory_id} | score={importance_score} | source={source} | {created_at}")
        print(f"    {content}")

    print("\n=== WORLD MODEL: ENTIDADES ===\n")
    for entity_id, name, entity_type, created_at in db.list_entities():
        print(f"{entity_id} | {name} | {entity_type} | {created_at}")

    print("\n=== WORLD MODEL: RELAÇÕES ===\n")
    for relation_id, source, relation, target, confidence, created_at in db.list_world_relationships():
        print(f"{relation_id} | {source} -> {relation} -> {target} | confiança={confidence} | {created_at}")

    print("\n=== WORLD MODEL: EVENTOS ===\n")
    for event_id, name, event_type, date, description, created_at in db.list_world_events():
        print(f"{event_id} | {name} | tipo={event_type} | data={date} | {created_at}")
        print(f"    descrição: {description}")
        for person, role in db.list_world_event_participants(event_id):
            print(f"    - {person} ({role})")

    print("\n=== WORLD MODEL: ESTADOS ATUAIS ===\n")
    for row in db.list_entity_states():
        state_id, entity_name, attribute, value, source_event, confidence, created_at, updated_at = row
        print(f"{state_id} | {entity_name}.{attribute} = {value} | fonte={source_event} | confiança={confidence}")
        print(f"    criado: {created_at} | atualizado: {updated_at}")

    print("\n=== WORLD MODEL: EXTRAÇÕES ===\n")
    for input_text, proposed_json, saved_json, created_at in db.list_world_extractions():
        print(f"{created_at} | entrada: {input_text}")
        print(f"    salvo: {saved_json}")

    print("\n=== KNOWLEDGE SOURCES V10 ===\n")
    for source_id, name, source_type, origin, confidence, rationale, metadata_json, created_at in db.list_knowledge_sources():
        print(f"{source_id} | {name} | tipo={source_type} | origem={origin} | confiança={confidence:.2f} | {created_at}")
        print(f"    motivo: {rationale}")
        print(f"    metadata: {metadata_json}")

    print("\n=== KNOWLEDGE INGESTIONS V10 ===\n")
    for ingestion_id, source_id, source_name, origin, source_confidence, summary, created_at in db.list_knowledge_ingestions():
        print(f"{ingestion_id} | fonte={source_name} ({source_id}) | origem={origin} | confiança fonte={source_confidence:.2f} | {created_at}")
        print(f"    resumo: {summary}")

    print("\n=== KNOWLEDGE SOURCE ITEMS V10 ===\n")
    for item_id, source_id, source_name, category, statement, confidence, origin, evidence_json, created_at in db.list_knowledge_source_items():
        print(f"{item_id} | [{category}] confiança={confidence:.2f} | fonte={source_name} ({source_id}) | origem={origin} | {created_at}")
        print(f"    {statement}")
        print(f"    evidências: {evidence_json}")

    print("\n=== AGENCY V11: INTENÇÕES ===\n")
    for intention_id, source_text, intention_json, confidence, status, created_at in db.list_intentions(limit=50):
        print(f"{intention_id} | status={status} | confiança={confidence:.2f} | {created_at}")
        print(f"    entrada: {source_text}")
        print(f"    intenção: {intention_json}")

    print("\n=== AGENCY V11: OBJETIVOS COGNITIVOS ===\n")
    for goal_id, intention_id, description, rationale, priority, confidence, status, created_at in db.list_agency_goals(limit=50):
        print(f"{goal_id} | intention={intention_id} | status={status} | prioridade={priority:.2f} | confiança={confidence:.2f} | {created_at}")
        print(f"    objetivo: {description}")
        print(f"    motivo: {rationale}")

    print("\n=== AGENCY V11: PLANOS ===\n")
    for plan_id, goal_id, plan_json, status, requires_approval, created_at in db.list_plans(limit=50):
        print(f"{plan_id} | goal={goal_id} | status={status} | aprovação={requires_approval} | {created_at}")
        print(f"    plano: {plan_json}")

    print("\n=== AGENCY V11: FERRAMENTAS ===\n")
    for row in db.list_tools():
        tool_id, capability, confidence, cost, latency, last_used, success_rate, enabled, created_at, updated_at = row
        print(f"{tool_id} | enabled={enabled} | confiança={confidence:.2f} | sucesso={success_rate:.2f} | custo={cost:.2f} | latência={latency:.2f}")
        print(f"    capacidade: {capability}")

    print("\n=== AGENCY V11: AÇÕES ===\n")
    for action_id, plan_id, tool_id, description, status, approval_required, result_summary, created_at, executed_at in db.list_actions(limit=50):
        print(f"{action_id} | plan={plan_id} | tool={tool_id} | status={status} | aprovação={approval_required} | criado={created_at} | executado={executed_at}")
        print(f"    ação: {description}")
        print(f"    resultado: {result_summary}")

    print("\n=== AGENCY V11: OUTCOMES ===\n")
    for outcome_id, action_id, status, summary, reflection, created_at in db.list_outcomes(limit=50):
        print(f"{outcome_id} | action={action_id} | status={status} | {created_at}")
        print(f"    resumo: {summary}")
        print(f"    reflexão: {reflection}")

    print("\n=== MEMÓRIAS LONGAS / CONVERSA LEGADA ===\n")
    for category, content, created_at in db.list_memories():
        print(f"{created_at} | {category} -> {content}")

    print("\n=== CONTADORES ===\n")
    print(f"Short-term ativas: {db.count_short_term_memory()}")
    print(f"Mid-term ativas: {db.count_mid_term_memory()}")
    print(f"Long-term real: {db.count_real_long_term_memory()}")
    print(f"Long-term estimadas: {db.count_long_term_memory()}")
    print(f"Entidades: {db.count_entities()}")
    print(f"Relações World Model: {db.count_world_relationships()}")
    print(f"Eventos World Model: {db.count_world_events()}")
    print(f"Estados atuais: {db.count_entity_states()}")
    print(f"Knowledge sources: {db.count_knowledge_sources()}")
    print(f"Knowledge source items: {db.count_knowledge_source_items()}")
    print(f"Intenções V11: {len(db.list_intentions(limit=100000))}")
    print(f"Objetivos de agência V11: {len(db.list_agency_goals(limit=100000))}")
    print(f"Planos V11: {len(db.list_plans(limit=100000))}")
    print(f"Ações V11: {len(db.list_actions(limit=100000))}")
    print(f"Outcomes V11: {len(db.list_outcomes(limit=100000))}")


    print("\n=== ERROR AWARENESS V12.1 ===\n")
    last_error = ErrorCapture(AthenaLogger()).last_error()
    if last_error:
        analysis = last_error.get("analysis", {})
        print(f"Último erro: {analysis.get('title', last_error.get('error_type'))}")
        print(f"Gravidade: {analysis.get('severity', 'médio')}")
        print(f"Módulo provável: {analysis.get('probable_module', 'não identificado')}")
        print(f"Explicação: {analysis.get('friendly_explanation', '')}")
    else:
        print("Nenhum erro registrado em logs/last_error.json.")

    print("\n=== SELF CODE AWARENESS V12 ===\n")
    settings = Settings()
    git_engine = GitAwarenessEngine(settings.get("projectRoot", "."), settings.get("officialRepositoryUrl"))
    self_code = SelfCodeAwarenessEngine(settings.get("projectRoot", "."), settings=settings, git_reader=git_engine.repository_reader)
    print(self_code.respond({"operation": "snapshot"}))

    print("\n=== GIT READ AWARENESS V12 ===\n")
    print(git_engine.respond({"operation": "summary"}))


if __name__ == "__main__":
    inspect()
