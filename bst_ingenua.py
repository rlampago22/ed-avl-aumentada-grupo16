from __future__ import annotations


class Node:
    __slots__ = ("key", "left", "right")

    def __init__(self, key: int) -> None:
        self.key = key
        self.left: Node | None = None
        self.right: Node | None = None


def insert(root: Node | None, key: int) -> Node:
    if root is None:
        return Node(key)

    current = root
    while True:
        if key < current.key:
            if current.left is None:
                current.left = Node(key)
                return root
            current = current.left
        elif key > current.key:
            if current.right is None:
                current.right = Node(key)
                return root
            current = current.right
        else:
            return root


def search(root: Node | None, key: int) -> bool:
    current = root
    while current is not None:
        if key < current.key:
            current = current.left
        elif key > current.key:
            current = current.right
        else:
            return True
    return False


def delete(root: Node | None, key: int) -> Node | None:
    parent: Node | None = None
    current = root

    while current is not None and current.key != key:
        parent = current
        current = current.left if key < current.key else current.right

    if current is None:
        return root

    if current.left is not None and current.right is not None:
        successor_parent = current
        successor = current.right
        while successor.left is not None:
            successor_parent = successor
            successor = successor.left
        current.key = successor.key
        parent = successor_parent
        current = successor

    child = current.left if current.left is not None else current.right
    if parent is None:
        return child
    if parent.left is current:
        parent.left = child
    else:
        parent.right = child
    return root


def rank(root: Node | None, key: int) -> int:
    count = 0
    stack: list[Node] = []
    current = root
    while stack or current is not None:
        while current is not None:
            stack.append(current)
            current = current.left
        current = stack.pop()
        if current.key >= key:
            return count
        count += 1
        current = current.right
    return count


def select(root: Node | None, position: int) -> int:
    if position < 1:
        raise IndexError("posicao fora dos limites da arvore")

    count = 0
    stack: list[Node] = []
    current = root
    while stack or current is not None:
        while current is not None:
            stack.append(current)
            current = current.left
        current = stack.pop()
        count += 1
        if count == position:
            return current.key
        current = current.right
    raise IndexError("posicao fora dos limites da arvore")


def range_agg(root: Node | None, start: int, end: int) -> int:
    if start > end:
        return 0

    result = 0
    stack = [] if root is None else [root]
    while stack:
        current = stack.pop()
        if current.key < start:
            if current.right is not None:
                stack.append(current.right)
        elif current.key > end:
            if current.left is not None:
                stack.append(current.left)
        else:
            result += current.key
            if current.left is not None:
                stack.append(current.left)
            if current.right is not None:
                stack.append(current.right)
    return result


def tree_size(root: Node | None) -> int:
    if root is None:
        return 0
    count = 0
    stack = [root]
    while stack:
        current = stack.pop()
        count += 1
        if current.left is not None:
            stack.append(current.left)
        if current.right is not None:
            stack.append(current.right)
    return count


def tree_height(root: Node | None) -> int:
    if root is None:
        return 0
    maximum = 0
    stack = [(root, 1)]
    while stack:
        current, depth = stack.pop()
        maximum = max(maximum, depth)
        if current.left is not None:
            stack.append((current.left, depth + 1))
        if current.right is not None:
            stack.append((current.right, depth + 1))
    return maximum
