import unittest
from nab.files import File

file_tests = [
    ('[gg]_C_The_Money_of_Soul_and_Possibility_Control_-_01_[7B880013].mkv',
     {'ext': 'mkv', 'group': 'gg', 'episode': 1,
      'title': 'c money of soul and possibility control'}),
    ('The Legend of Korra - The Complete Season 1 [720p-HDTV]',
     {'tags': ['720p', 'hdtv'], 'season': 1, 'title': 'legend of korra'}),
    ('[Furi] Avatar - The Last Airbender [720p] (Full 3 Seasons + Extras)',
     {'group': 'furi', 'tags': ['720p'], 'title': 'avatar last airbender'}),
    ('[UTW]_Angel_Beats!_-_04v2_[BD][h264-1080p_FLAC][0C19DD1C].mkv',
     {'ext': 'mkv', 'group': 'utw', 'episode': 4,
      'tags': ['bd', '1080p', 'flac'], 'title': 'angel beats'}),
    ('The.Legend.of.Korra.S02E14.Light.in.the.Dark.WEB-DL.x264.AAC.mp4',
     {'ext': 'mp4', 'episode': 14, 'season': 2, 'tags': ['x264', 'aac'],
      'title': 'legend of korra', 'eptitle': 'light in the dark'})
]


class TestFile(unittest.TestCase):

    def test_file(self):
        for filename, data in file_tests:
            f = File(filename)

            for name, value in data.iteritems():
                # if tags, make sure there are no MISSING tags
                # extra tags are acceptable and unavoidable
                if name == 'tags':
                    for tag in value:
                        self.assertIn(tag, f.__dict__[name])
                else:
                    self.assertEquals(f.__dict__[name], value)

if __name__ == '__main__':
    unittest.main()
