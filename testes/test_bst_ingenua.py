import unittest

from codigo import bst_ingenua as bst


class NaiveBstTests(unittest.TestCase):
    def test_sorted_insertions_create_a_chain(self) -> None:
        root = None
        for key in (10, 20, 30, 40):
            root = bst.insert(root, key)

        self.assertEqual(bst.tree_size(root), 4)
        self.assertEqual(bst.tree_height(root), 4)
        self.assertTrue(bst.search(root, 40))

    def test_required_operations(self) -> None:
        root = None
        for key in (20, 10, 30, 40, 25, 5):
            root = bst.insert(root, key)

        self.assertEqual(bst.rank(root, 20), 2)
        self.assertEqual(bst.select(root, 4), 25)
        self.assertEqual(bst.range_agg(root, 10, 30), 85)

    def test_delete_handles_all_node_shapes(self) -> None:
        root = None
        for key in (20, 10, 30, 5, 15, 25, 40, 35):
            root = bst.insert(root, key)

        for key in (5, 40, 30, 20):
            root = bst.delete(root, key)
            self.assertFalse(bst.search(root, key))

        self.assertEqual(bst.tree_size(root), 4)


if __name__ == "__main__":
    unittest.main()
