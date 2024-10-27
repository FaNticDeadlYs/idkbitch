import random

MOVES_3x3 = ["F", "F'", "F2", "B", "B'", "B2", 
             "R", "R'", "R2", "L", "L'", "L2",
             "U", "U'", "U2", "D", "D'", "D2"]

MOVES_2x2 = ["R", "R'", "R2", "U", "U'", "U2",
             "F", "F'", "F2"]

def generate_scramble(cube_type):
    moves = MOVES_2x2 if cube_type == "2x2" else MOVES_3x3
    length = 9 if cube_type == "2x2" else 20
    scramble = []
    last_face = None
    
    for _ in range(length):
        move = random.choice(moves)
        current_face = move[0]
        while current_face == last_face:
            move = random.choice(moves)
            current_face = move[0]
        scramble.append(move)
        last_face = current_face
    
    return " ".join(scramble)
