# -*- coding: utf-8 -*-

from imio.pm.wsclient.browser import vocabularies
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase

from mock import patch


class testVocabularies(WS4PMCLIENTTestCase):
    """
    Test the vocabularies.
    """

    @patch('imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getConfigInfos')
    def test_pm_meeting_config_id_vocabulary(self, _rest_getConfigInfos):
        """ """
        _rest_getConfigInfos.return_value = type(
            'ConfigInfos', (object,), {
                'configInfo': [
                    {'id': u'plonegov-assembly', 'title': u'PloneGov Assembly'},
                    {'id': u'plonemeeting-assembly', 'title': u'PloneMeeting Assembly'},
                 ]
             }
        )()
        raw_voc = vocabularies.pm_meeting_config_id_vocabularyFactory()
        self.assertEqual(len(raw_voc), 2)
        voc = [v for v in raw_voc]
        self.assertEqual(voc[0].value, 'plonegov-assembly')
        self.assertEqual(voc[1].value, 'plonemeeting-assembly')
