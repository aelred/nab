import unittest
from nab.files import File

# fields: ext, group, tags
#         episode, season
#         title, eptitle

file_tests = [
    ('[gg]_C_The_Money_of_Soul_and_Possibility_Control_-_01_[7B880013].mkv',
     {'ext': 'mkv', 'group': 'gg', 'episode': 1, 'eprange': 1, 'season': None,
      'title': 'c money of soul and possibility control', 'eptitle': None}),

    ('The Legend of Korra - The Complete Season 1 [720p-HDTV]',
     {'ext': None, 'group': None, 'tags': ['720p', 'hdtv'],
      'episode': None, 'eprange': None, 'season': 1,
      'title': 'legend of korra', 'eptitle': None}),

    ('[Furi] Avatar - The Last Airbender [720p] (Full 3 Seasons + Extras)',
     {'ext': None, 'group': 'furi', 'tags': ['720p'],
      'episode': None, 'eprange': None, 'season': None,
      'title': 'avatar last airbender', 'eptitle': None}),

    ('[UTW]_Angel_Beats!_-_04v2_[BD][h264-1080p_FLAC][0C19DD1C].mkv',
     {'ext': 'mkv', 'group': 'utw', 'tags': ['bd', '1080p', 'flac'],
      'episode': 4, 'eprange': 4, 'season': None,
      'title': 'angel beats', 'eptitle': None}),

    ('The.Legend.of.Korra.S02E14.Light.in.the.Dark.WEB-DL.x264.AAC.mp4',
     {'ext': 'mp4', 'group': None, 'tags': ['x264', 'aac'],
      'episode': 14, 'eprange': 14, 'season': 2,
      'title': 'legend of korra', 'eptitle': 'light in the dark'}),

    ('[uguu~] AIR 01-12 Complete Batch (BD-1080p)',
     {'ext': None, 'group': 'uguu', 'tags': ['bd', '1080p'],
      'episode': None, 'eprange': None, 'season': None,
      'title': 'air', 'eptitle': None}),

    ('[NoobSubs] Fate Zero S1 01-13 + SP01-03 (720p Blu-ray 8bit AAC MP4)',
     {'ext': None, 'group': 'noobsubs',
      'tags': ['720p', '8bit', 'aac', 'mp4'],
      'episode': 1, 'eprange': 13, 'season': 1,
      'title': 'fate zero', 'eptitle': None}),

    ('[UTW] Fate Zero - 14-25 + Specials [BD][h264-1080p_FLAC]',
     {'ext': None, 'group': 'utw', 'tags': ['bd', 'h264', '1080p', 'flac'],
      'episode': 14, 'eprange': 25, 'season': None,
      'title': 'fate zero', 'eptitle': None}),

    ('Psycho-Pass',
     {'ext': None, 'group': None, 'tags': [],
      'episode': None, 'eprange': None, 'season': None,
      'title': 'psycho-pass', 'eptitle': None}),

    ('Game of Thrones S04E06 720p HDTV x264-DIMENSION',
     {'ext': None, 'group': 'dimension', 'tags': ['720p', 'hdtv', 'x264'],
      'title': 'game of thrones', 'eptitle': None})
]


class TestFile(unittest.TestCase):

    def test_file(self):
        for filename, data in file_tests:
            f = File(filename)
            print filename
            print f.__dict__

            for name, value in data.iteritems():
                if name == 'tags':
                    # if tags, make sure there are no MISSING tags
                    # extra tags are acceptable and unavoidable
                    for tag in value:
                        print "Asserting %s in tags" % tag
                        self.assertIn(tag, f.__dict__[name])
                else:
                    print "Asserting %s = %s" % (name, value)
                    self.assertEquals(f.__dict__[name], value)

if __name__ == '__main__':
    unittest.main()
