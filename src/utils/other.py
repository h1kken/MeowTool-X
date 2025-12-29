import os


def cls() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    
def chunks_generator(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
