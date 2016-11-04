import unittest
import Models
import Managers
import tkinter


class TestTrackManager(unittest.TestCase):
    def setUp(self):
        self.track_manager = Managers.TrackManager(tkinter.Canvas(), "UnitTest.track")

    # def test_iter_from(self):
    #     # Reversing a reverse transversal is the same
    #     cache = list(self.track_manager.iter_from((0, 10)))
    #     self.assertSequenceEqual(cache,list(self.track_manager.iter_from(cache[-1].end, reverse=True))[::-1])
    #     self.assertNotEqual(cache,
    #                         list(self.track_manager.iter_from(cache[-1].end, reverse=True)))
    #     # Iterate from different points is not the same
    #     self.assertNotEqual(list(self.track_manager.iter_from((0, 10))), list(self.track_manager.iter_from((10, 30))))

    # def test__iter__(self):
    #     """Test all pieces are returned by __iter__"""
    #     cache = list(self.track_manager)
    #     for x, y in self.track_manager.track.values():
    #         if x is not None:
    #             self.assertIn(x, cache)
    #         if y is not None:
    #             self.assertIn(y, cache)

    def test_piece_coord(self):
        """Test all coordinates from pieces are in coordinate_dict"""
        for piece in self.track_manager:
            self.assertIn(piece.start, self.track_manager.coordinate_dict)
            self.assertIn(piece.end, self.track_manager.coordinate_dict)
            if isinstance(piece, Models.Point):
                self.assertIn(piece.alternate, self.track_manager.coordinate_dict)


if __name__ == "__main__":
    unittest.main()
