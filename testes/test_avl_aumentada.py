import unittest
from bisect import bisect_left
from random import Random

from codigo.avl_aumentada import (
    Node,
    balance_factor,
    delete,
    insert,
    range_agg,
    rank,
    rotate_left,
    rotate_right,
    search,
    select,
    update,
    validate_invariants,
)


class NodeMetadataTests(unittest.TestCase):
    def test_new_node_is_a_leaf(self) -> None:
        node = Node(40)

        self.assertEqual(node.height, 1)
        self.assertEqual(node.size, 1)
        self.assertEqual(node.subtree_sum, 40)

    def test_update_recalculates_metadata_from_children(self) -> None:
        root = Node(20)
        root.left = Node(10)
        root.right = Node(30)
        root.right.right = Node(40)

        update(root.right)
        update(root)

        self.assertEqual(root.right.height, 2)
        self.assertEqual(root.right.size, 2)
        self.assertEqual(root.right.subtree_sum, 70)
        self.assertEqual(root.height, 3)
        self.assertEqual(root.size, 4)
        self.assertEqual(root.subtree_sum, 100)


class RotationTests(unittest.TestCase):
    def test_right_rotation_balances_left_left_case(self) -> None:
        root = Node(30)
        root.left = Node(20)
        root.left.left = Node(10)
        update(root.left)
        update(root)

        self.assertEqual(balance_factor(root), 2)

        root = rotate_right(root)

        self.assertEqual(root.key, 20)
        self.assertEqual(root.left.key, 10)
        self.assertEqual(root.right.key, 30)
        self.assertEqual(balance_factor(root), 0)
        self.assertEqual(root.height, 2)
        self.assertEqual(root.size, 3)
        self.assertEqual(root.subtree_sum, 60)

    def test_right_rotation_preserves_middle_subtree(self) -> None:
        root = Node(30)
        root.left = Node(20)
        root.left.left = Node(10)
        root.left.right = Node(25)
        update(root.left)
        update(root)

        root = rotate_right(root)

        self.assertEqual(root.key, 20)
        self.assertEqual(root.right.key, 30)
        self.assertEqual(root.right.left.key, 25)
        self.assertEqual(root.right.size, 2)
        self.assertEqual(root.right.subtree_sum, 55)
        self.assertEqual(root.size, 4)
        self.assertEqual(root.subtree_sum, 85)

    def test_left_rotation_balances_right_right_case(self) -> None:
        root = Node(10)
        root.right = Node(20)
        root.right.right = Node(30)
        update(root.right)
        update(root)

        self.assertEqual(balance_factor(root), -2)

        root = rotate_left(root)

        self.assertEqual(root.key, 20)
        self.assertEqual(root.left.key, 10)
        self.assertEqual(root.right.key, 30)
        self.assertEqual(balance_factor(root), 0)
        self.assertEqual(root.height, 2)
        self.assertEqual(root.size, 3)
        self.assertEqual(root.subtree_sum, 60)


class InsertionTests(unittest.TestCase):
    def test_insert_handles_all_rotation_cases(self) -> None:
        cases = (
            ("left-left", (30, 20, 10)),
            ("right-right", (10, 20, 30)),
            ("left-right", (30, 10, 20)),
            ("right-left", (10, 30, 20)),
        )

        for case_name, keys in cases:
            with self.subTest(case=case_name):
                root = None
                for key in keys:
                    root = insert(root, key)

                self.assertEqual(root.key, 20)
                self.assertEqual(root.left.key, 10)
                self.assertEqual(root.right.key, 30)
                self.assertEqual(root.height, 2)
                self.assertEqual(root.size, 3)
                self.assertEqual(root.subtree_sum, 60)
                self.assertEqual(balance_factor(root), 0)

    def test_insert_updates_augmented_fields(self) -> None:
        root = None
        for key in (20, 10, 30, 40):
            root = insert(root, key)

        self.assertEqual(root.height, 3)
        self.assertEqual(root.size, 4)
        self.assertEqual(root.subtree_sum, 100)

    def test_insert_ignores_duplicate_key(self) -> None:
        root = insert(None, 20)
        root = insert(root, 20)

        self.assertEqual(root.size, 1)
        self.assertEqual(root.subtree_sum, 20)


class RequiredOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = None
        for key in (20, 10, 30, 40, 25, 5):
            self.root = insert(self.root, key)

    def test_search_finds_present_and_absent_keys(self) -> None:
        self.assertTrue(search(self.root, 25))
        self.assertFalse(search(self.root, 26))

    def test_rank_counts_strictly_smaller_keys(self) -> None:
        self.assertEqual(rank(self.root, 5), 0)
        self.assertEqual(rank(self.root, 20), 2)
        self.assertEqual(rank(self.root, 26), 4)
        self.assertEqual(rank(self.root, 100), 6)

    def test_select_uses_one_based_positions(self) -> None:
        self.assertEqual(select(self.root, 1), 5)
        self.assertEqual(select(self.root, 4), 25)
        self.assertEqual(select(self.root, 6), 40)

        with self.assertRaises(IndexError):
            select(self.root, 0)
        with self.assertRaises(IndexError):
            select(self.root, 7)

    def test_range_agg_sums_only_keys_inside_interval(self) -> None:
        self.assertEqual(range_agg(self.root, 10, 30), 85)
        self.assertEqual(range_agg(self.root, 11, 29), 45)
        self.assertEqual(range_agg(self.root, 31, 35), 0)
        self.assertEqual(range_agg(self.root, 35, 31), 0)


class DeletionTests(unittest.TestCase):
    def test_delete_handles_leaf_one_child_two_children_and_root(self) -> None:
        root = None
        expected = {20, 10, 30, 5, 15, 25, 40, 35}
        for key in expected:
            root = insert(root, key)

        for key in (5, 40, 30, 20):
            root = delete(root, key)
            expected.remove(key)
            validate_invariants(root)
            self.assertEqual(root.size, len(expected))
            self.assertEqual(root.subtree_sum, sum(expected))
            self.assertFalse(search(root, key))

    def test_delete_absent_key_does_not_change_tree(self) -> None:
        root = insert(None, 20)
        root = delete(root, 999)

        self.assertEqual(root.key, 20)
        self.assertEqual(root.size, 1)
        self.assertEqual(root.subtree_sum, 20)


class DifferentialTests(unittest.TestCase):
    def test_random_operations_match_python_reference(self) -> None:
        rng = Random(16)
        root = None
        reference: set[int] = set()

        for _ in range(1_000):
            key = rng.randrange(0, 250)
            if rng.random() < 0.55:
                root = insert(root, key)
                reference.add(key)
            else:
                root = delete(root, key)
                reference.discard(key)

            validate_invariants(root)
            ordered = sorted(reference)
            self.assertEqual(node_size_for_test(root), len(ordered))
            self.assertEqual(0 if root is None else root.subtree_sum, sum(ordered))

            probe = rng.randrange(0, 250)
            self.assertEqual(search(root, probe), probe in reference)
            self.assertEqual(rank(root, probe), bisect_left(ordered, probe))

            if ordered:
                position = rng.randrange(1, len(ordered) + 1)
                self.assertEqual(select(root, position), ordered[position - 1])

            start = rng.randrange(0, 250)
            end = rng.randrange(start, 250)
            expected_sum = sum(key for key in ordered if start <= key <= end)
            self.assertEqual(range_agg(root, start, end), expected_sum)


def node_size_for_test(root: Node | None) -> int:
    return 0 if root is None else root.size


if __name__ == "__main__":
    unittest.main()
