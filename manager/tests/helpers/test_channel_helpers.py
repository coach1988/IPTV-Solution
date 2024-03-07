from unittest import TestCase

from manager.helpers.channel_helper import ChannelHelper, GroupCategoryFinder, GroupCategory


class ChannelTest(TestCase):

    def example_1(self):
        return {
            'name': 'Yes Movies Drama HD',
            'logo': 'https://images/8dd.png',
            'url': 'http://video.m3u8',
            'category': 'Israel',
            'tvg': {'id': 'yes-movies-drama-il-hd', 'name': 'tvg_name', 'url': None, 'chno': None},
            'country': {'code': None, 'name': None},
            'language': {'code': None, 'name': None},
            'status': 'GOOD',
            'live': True,
        }

    def test_from_m3u_entry_all_populated(self):
        actual = ChannelHelper.from_m3u_entry(self.example_1())
        expected = ChannelHelper(
            name='Yes Movies Drama HD',
            logo='https://images/8dd.png',
            url='http://video.m3u8',
            tvg_id='yes-movies-drama-il-hd',
            tvg_name='tvg_name',
            original_group='Israel',
            group='Israel',
        )
        self.assertEqual(actual, expected)


class ChannelFactoryTest(TestCase):
    factory = GroupCategoryFinder.default()

    @staticmethod
    def channel():
        return ChannelHelper(
                name='Yes Movies Drama HD',
                logo='https://images/8dd.png',
                url='http://video.m3u8',
                tvg_id='yes-movies-drama-il-hd',
                tvg_name=None,
                original_group='Israel',
                group='Israel',
        )

    def test_category_assignment(self):
        category = self.factory.find(self.channel())
        self.assertEqual(category, GroupCategory.MOVIES)












