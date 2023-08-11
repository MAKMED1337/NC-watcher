class Kuhn:
    def __init__(self, verticies: int, left_part: int) -> None:
        self.n = verticies
        self.m = left_part
        self.G = [[] for i in range(self.n)]

    def add_edge(self, u: int, v: int) -> None:
        self.G[u].append(v)
        self.G[v].append(u)

    def try_kuhn(self, u: int, used: list[bool]) -> bool:
        if used[u]:
            return False
        used[u] = True

        for v in self.G[u]:
            if self.mt[v] == -1 or self.try_kuhn(self.mt[v], used):
                self.mt[v] = u
                return True
        return False

    def run(self) -> list[int]:
        self.mt = [-1] * self.n

        for u in range(self.m):
            self.try_kuhn(u, [False] * self.m)

        return self.mt
