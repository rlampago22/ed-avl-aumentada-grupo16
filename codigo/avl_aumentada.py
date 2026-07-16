from __future__ import annotations


_rotation_counts = {"left": 0, "right": 0}


class Node:
    """Um no da AVL com os campos aumentados exigidos pelo projeto."""

    __slots__ = ("key", "left", "right", "height", "size", "subtree_sum")

    def __init__(self, key: int) -> None:
        self.key = key
        self.left: Node | None = None
        self.right: Node | None = None
        self.height = 1
        self.size = 1
        self.subtree_sum = key


def node_height(node: Node | None) -> int:
    return 0 if node is None else node.height


def node_size(node: Node | None) -> int:
    return 0 if node is None else node.size


def node_sum(node: Node | None) -> int:
    return 0 if node is None else node.subtree_sum


def update(node: Node) -> None:
    """Recalcula os campos do no a partir dos dois filhos."""

    node.height = 1 + max(node_height(node.left), node_height(node.right))
    node.size = 1 + node_size(node.left) + node_size(node.right)
    node.subtree_sum = node.key + node_sum(node.left) + node_sum(node.right)


def balance_factor(node: Node) -> int:
    return node_height(node.left) - node_height(node.right)


def rotate_right(root: Node) -> Node:
    """Corrige um desequilibrio reto para a esquerda."""

    _rotation_counts["right"] += 1
    new_root = root.left
    if new_root is None:
        raise ValueError("rotacao a direita exige um filho esquerdo")

    moved_subtree = new_root.right
    new_root.right = root
    root.left = moved_subtree

    update(root)
    update(new_root)
    return new_root


def rotate_left(root: Node) -> Node:
    """Corrige um desequilibrio reto para a direita."""

    _rotation_counts["left"] += 1
    new_root = root.right
    if new_root is None:
        raise ValueError("rotacao a esquerda exige um filho direito")

    moved_subtree = new_root.left
    new_root.left = root
    root.right = moved_subtree

    update(root)
    update(new_root)
    return new_root


def rebalance(node: Node) -> Node:
    """Atualiza o no e corrige um eventual desequilibrio AVL."""

    update(node)
    factor = balance_factor(node)

    if factor > 1:
        if node.left is None:
            raise RuntimeError("fator positivo sem filho esquerdo")
        if balance_factor(node.left) < 0:
            node.left = rotate_left(node.left)
        return rotate_right(node)

    if factor < -1:
        if node.right is None:
            raise RuntimeError("fator negativo sem filho direito")
        if balance_factor(node.right) > 0:
            node.right = rotate_right(node.right)
        return rotate_left(node)

    return node


def insert(root: Node | None, key: int) -> Node:
    """Insere uma chave e devolve a raiz atualizada da subarvore."""

    if root is None:
        return Node(key)

    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    else:
        return root

    return rebalance(root)


def search(root: Node | None, key: int) -> bool:
    """Informa se a chave esta presente na arvore."""

    current = root
    while current is not None:
        if key < current.key:
            current = current.left
        elif key > current.key:
            current = current.right
        else:
            return True
    return False


def _minimum(node: Node) -> Node:
    current = node
    while current.left is not None:
        current = current.left
    return current


def delete(root: Node | None, key: int) -> Node | None:
    """Remove uma chave e devolve a raiz atualizada da subarvore."""

    if root is None:
        return None

    if key < root.key:
        root.left = delete(root.left, key)
    elif key > root.key:
        root.right = delete(root.right, key)
    else:
        if root.left is None:
            return root.right
        if root.right is None:
            return root.left

        successor = _minimum(root.right)
        root.key = successor.key
        root.right = delete(root.right, successor.key)

    return rebalance(root)


def rank(root: Node | None, key: int) -> int:
    """Conta quantas chaves da arvore sao menores que key."""

    result = 0
    current = root
    while current is not None:
        if key <= current.key:
            current = current.left
        else:
            result += 1 + node_size(current.left)
            current = current.right
    return result


def select(root: Node | None, position: int) -> int:
    """Devolve a chave na posicao informada, contando a partir de 1."""

    if position < 1 or position > node_size(root):
        raise IndexError("posicao fora dos limites da arvore")

    current = root
    target = position
    while current is not None:
        current_position = node_size(current.left) + 1
        if target == current_position:
            return current.key
        if target < current_position:
            current = current.left
        else:
            target -= current_position
            current = current.right

    raise RuntimeError("metadado size inconsistente")


def prefix_sum(root: Node | None, key: int) -> int:
    """Soma as chaves menores ou iguais a key."""

    result = 0
    current = root
    while current is not None:
        if key < current.key:
            current = current.left
        else:
            result += node_sum(current.left) + current.key
            current = current.right
    return result


def range_agg(root: Node | None, start: int, end: int) -> int:
    """Soma as chaves presentes no intervalo inclusivo [start, end]."""

    if start > end:
        return 0
    return prefix_sum(root, end) - prefix_sum(root, start - 1)


def validate_invariants(root: Node | None) -> None:
    """Falha se ordenacao, balanceamento ou metadados estiverem incorretos."""

    def visit(
        node: Node | None,
        lower: int | None,
        upper: int | None,
    ) -> tuple[int, int, int]:
        if node is None:
            return 0, 0, 0

        if lower is not None and node.key <= lower:
            raise AssertionError("chave fora do limite inferior")
        if upper is not None and node.key >= upper:
            raise AssertionError("chave fora do limite superior")

        left_height, left_size, left_sum = visit(node.left, lower, node.key)
        right_height, right_size, right_sum = visit(node.right, node.key, upper)

        expected_height = 1 + max(left_height, right_height)
        expected_size = 1 + left_size + right_size
        expected_sum = node.key + left_sum + right_sum

        if abs(left_height - right_height) > 1:
            raise AssertionError("fator de balanceamento fora de [-1, 1]")
        if node.height != expected_height:
            raise AssertionError("altura armazenada incorreta")
        if node.size != expected_size:
            raise AssertionError("tamanho de subarvore incorreto")
        if node.subtree_sum != expected_sum:
            raise AssertionError("soma de subarvore incorreta")

        return expected_height, expected_size, expected_sum

    visit(root, None, None)


def reset_rotation_counts() -> None:
    _rotation_counts["left"] = 0
    _rotation_counts["right"] = 0


def rotation_counts() -> dict[str, int]:
    return _rotation_counts.copy()
