import unittest
from nab.files import File
from nab.show import Show

# fields: ext, group, tags
#         episode, season
#         title, eptitle

file_tests = [
    ('[gg]_C_The_Money_of_Soul_and_Possibility_Control_-_01_[7B880013].mkv',
     {'entry': ('C: The Money of Soul and Possibility Control', 1, 1),
      'ext': 'mkv', 'group': 'gg',
      'episode': 1, 'eprange': 1, 'season': None, 'serange': None,
      'title': 'c money of soul and possibility control', 'eptitle': None}),

    ('The Legend of Korra - The Complete Season 1 [720p-HDTV]',
     {'entry': ('The Legend of Korra', 1),
      'ext': None, 'group': None, 'tags': ['720p', 'hdtv'],
      'episode': None, 'eprange': None, 'season': 1, 'serange': 1,
      'title': 'legend of korra', 'eptitle': None}),

    ('[Furi] Avatar - The Last Airbender [720p] (Full 3 Seasons + Extras)',
     {'entry': ('Avatar the Last Airbender', ),
      'ext': None, 'group': 'furi', 'tags': ['720p'],
      'episode': None, 'eprange': None, 'season': None, 'serange': None,
      'title': 'avatar last airbender', 'eptitle': None}),

    ('[UTW]_Angel_Beats!_-_04v2_[BD][h264-1080p_FLAC][0C19DD1C].mkv',
     {'entry': ('Angel Beats', 1, 4),
      'ext': 'mkv', 'group': 'utw', 'tags': ['bd', '1080p', 'flac'],
      'episode': 4, 'eprange': 4, 'season': None, 'serange': None,
      'title': 'angel beats', 'eptitle': None}),

    ('The.Legend.of.Korra.S02E14.Light.in.the.Dark.WEB-DL.x264.AAC.mp4',
     {'entry': ('The Legend of Korra', 2, 14),
      'ext': 'mp4', 'group': None, 'tags': ['x264', 'aac'],
      'episode': 14, 'eprange': 14, 'season': 2, 'serange': 2,
      'title': 'legend of korra', 'eptitle': 'light in the dark'}),

    ('[uguu~] AIR 01-12 Complete Batch (BD-1080p)',
     {'entry': ('Air', ),
      'ext': None, 'group': 'uguu', 'tags': ['bd', '1080p'],
      'episode': None, 'eprange': None, 'season': None, 'serange': None,
      'title': 'air', 'eptitle': None}),

    ('[NoobSubs] Fate Zero S1 01-13 + SP01-03 (720p Blu-ray 8bit AAC MP4)',
     {'entry': ('Fate/Zero', 1),
      'ext': None, 'group': 'noobsubs',
      'tags': ['720p', '8bit', 'aac', 'mp4'],
      'episode': 1, 'eprange': 13, 'season': 1, 'serange': 1,
      'title': 'fate zero', 'eptitle': None}),

    ('[UTW] Fate Zero - 14-25 + Specials [BD][h264-1080p_FLAC]',
     {'entry': ('Fate/Zero', 2),
      'ext': None, 'group': 'utw', 'tags': ['bd', 'h264', '1080p', 'flac'],
      'episode': 14, 'eprange': 25, 'season': None, 'serange': None,
      'title': 'fate zero', 'eptitle': None}),

    ('Psycho-Pass',
     {'entry': ('Psycho-Pass', 1),
      'ext': None, 'group': None, 'tags': [],
      'episode': None, 'eprange': None, 'season': None, 'serange': None,
      'title': 'psycho-pass', 'eptitle': None}),

    ('Game of Thrones S04E06 720p HDTV x264-DIMENSION',
     {'entry': ('Game of Thrones', 4, 6),
      'ext': None, 'group': 'dimension', 'tags': ['720p', 'hdtv', 'x264'],
      'episode': 6, 'eprange': 6, 'season': 4, 'serange': 4,
      'title': 'game of thrones', 'eptitle': None}),

    ('[HorribleSubs] Monogatari Series Second Season - 04 [720p].mkv',
     {'entry': ('Bakemonogatari', 3, 4),
      'ext': 'mkv', 'group': 'horriblesubs', 'tags': ['720p'],
      'episode': 4, 'eprange': 4, 'season': None, 'serange': None,
      'title': 'monogatari series second season', 'eptitle': None}),

    ('Battlestar Galactica Complete Series '
     '2003-2009 720p XvidHD - RePack PsiClone',
     {'entry': ('Battlestar Galactica', ),
      'ext': None, 'tags': ['720p', 'xvidhd'],
      'episode': None, 'eprange': None, 'season': None, 'serange': None,
      'title': 'battlestar galactica', 'eptitle': None}),

    ('Blackadder Seasons 1-4 + Specials',
     {'entry': ('Blackadder', ),
      'ext': None,
      'episode': None, 'eprange': None, 'season': 1, 'serange': 4,
      'title': 'blackadder', 'eptitle': None}),

    ('Breaking Bad Season 5 Complete 720p.BRrip.Sujaidr',
     {'entry': ('Breaking Bad', 5),
      'ext': None, 'tags': ['720p', 'brrip'],
      'episode': None, 'eprange': None, 'season': 5, 'serange': 5,
      'title': 'breaking bad', 'eptitle': None}),

    ('[VIP]Black Lagoon - 1-24[BDrip,912x512,x264,AAC]',
     {'ext': None, 'group': 'vip', 'tags': ['bdrip', 'x264', 'aac'],
      'episode': 1, 'eprange': 24, 'season': None, 'serange': None,
      'title': 'black lagoon', 'eptitle': None}),

    ("JoJo's Bizarre Adventure (2012) - S01E02 - A Letter from the Past.mkv",
     {'entry': ("JoJo's Bizarre Adventure (2012)", 1, 2),
      'ext': 'mkv', 'group': None,
      'episode': 2, 'eprange': 2, 'season': 1, 'serange': 1,
      'title': "jojos bizarre adventure (2012)",
      'eptitle': 'a letter from past'}),

    ('JoJos Bizarre Adventure (2012)',
     {'entry': ("JoJo's Bizarre Adventure (2012)", ),
      'ext': None, 'group': None,
      'episode': None, 'eprange': None, 'season': None, 'serange': None,
      'title': 'jojos bizarre adventure (2012)', 'eptitle': None}),

    ('[PublicHD] Parks.and.Recreation.S06E21E22.720p.HDTV.X264-DIMENSION.mkv',
     {'entry': ('Parks and Recreation', 6, 21),
      'ext': 'mkv', 'group': 'dimension', 'tags': ['720p', 'hdtv', 'x264'],
      'episode': 21, 'eprange': 22, 'season': 6, 'serange': 6,
      'title': 'parks and recreation', 'eptitle': None})
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
                elif name == 'entry':
                    # lookup the details for this show
                    # and find out if it's a match
                    title = value[0]
                    show = Show(title)

                    entry = show
                    # iterate to individual seasons/episodes
                    for index in value[1:]:
                        entry = entry[index]

                    # test if this matches
                    print "Asserting matches %s" % entry
                    self.assertTrue(entry.match(f))

                else:
                    print "Asserting %s = %s" % (name, value)
                    self.assertEquals(f.__dict__[name], value)

if __name__ == '__main__':
    unittest.main()
