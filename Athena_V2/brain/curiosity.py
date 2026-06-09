def generate_question(concepts):

    if not concepts:

        return (
            "Pode me ensinar "
            "algo novo hoje?"
        )

    return (
        f"Você mencionou "
        f"'{concepts[0]}'. "
        f"O que isso significa?"
    )