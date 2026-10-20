import hashlib
import json


class ASLInterpreter:
    """Validated operations over MemoryDB. Never eval, exec, shell or raw SQL."""
    FIELDS = {
        "definition.get": {"concept"},
        "definition.set": {"concept", "meaning"},
        "relation.find": {"source", "relation", "target"},
        "relation.add": {"source", "relation", "target"},
    }
    WRITES = {"definition.set", "relation.add"}

    def __init__(self, memory):
        self.memory = memory

    def validate(self, program):
        if not isinstance(program, dict) or set(program) != {"asl", "op", "args"} or program["asl"] != "1":
            raise ValueError("Esperado ASL 1 com asl, op, args")
        op, args = program["op"], program["args"]
        if not isinstance(op, str) or op not in self.FIELDS or not isinstance(args, dict):
            raise ValueError("Operação ASL inválida")
        expected = self.FIELDS[op]
        if not set(args) <= expected or (op != "relation.find" and set(args) != expected):
            raise ValueError("Argumentos ASL inválidos")
        if not args or any(not isinstance(v, str) or not v.strip() or len(v) > 4096 for v in args.values()):
            raise ValueError("Argumentos devem ser textos não vazios de até 4096 caracteres")
        canonical = json.dumps(program, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def execute(self, program, approval=None):
        digest = self.validate(program)
        op, args = program["op"], dict(program["args"])
        if op in self.WRITES and approval != digest:
            return {"status": "approval_required", "digest": digest, "program": program}
        if op == "definition.get":
            result = self.memory.get_definition(**args)
        elif op == "definition.set":
            # Existing definitions require a separate human decision; no overwrite.
            existing = self.memory.get_definition(args["concept"])
            if existing:
                return {"status": "exists", "result": existing}
            result = self.memory.save_definition(**args)
        elif op == "relation.find":
            result = self.memory.find_relationships(**args)
        else:
            existing = self.memory.find_relationships(**args)
            result = existing or self.memory.save_relationship(**args)
        return {"status": "completed", "result": result, "digest": digest}
