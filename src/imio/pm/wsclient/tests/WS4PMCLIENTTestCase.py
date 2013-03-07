# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

import transaction
from Acquisition import aq_base

from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from imio.pm.wsclient.testing import WS4PMCLIENT_PM_TEST_PROFILE_FUNCTIONAL


class WS4PMCLIENTTestCase(PloneMeetingTestCase):
    '''Base class for defining WS4PMCLIENT test cases.'''

    layer = WS4PMCLIENT_PM_TEST_PROFILE_FUNCTIONAL

    def setUp(self):
        """ """
        PloneMeetingTestCase.setUp(self)

    def _sendToPloneMeeting(self, obj):
        """
          Helper method for sending an element to PloneMeeting
        """
        # set correct config
        setCorrectSettingsConfig(self.portal)
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # use the 'send_to_plonemeeting' view
        self.request.set('URL', obj.absolute_url())
        self.request.set('ACTUAL_URL', obj.absolute_url() + '/@@send_to_plonemeeting')
        self.request.set('referer_query_string', 'meetingConfigId=plonemeeting-assembly&proposingGroupId=developers')
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        self.request.set('proposingGroupId', 'developers')
        self.request.form['form.submitted'] = True
        obj.restrictedTraverse('@@send_to_plonemeeting')()
        transaction.commit()
        return self.portal.portal_catalog(portal_type='MeetingItemPma', Title=obj.Title())[0].getObject()


def setCorrectSettingsConfig(portal, minimal=False, withValidation=True, **kwargs):
    """Set a workable set of settings for tests.
       If p_withValidation is False, remove validation because we want
       to force to set some values and relevant vocabularies for example do not contain that value.
       If p_minimal is True, only minimal settings are set to be able to connect."""
    if not withValidation:
        # disable validation when forcing some values to set
        from zope.schema._field import AbstractCollection
        old_validate = AbstractCollection._validate

        def _validate(self, value):
            return
        AbstractCollection._validate = _validate
    ws4pmSettings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
    settings = ws4pmSettings.settings()
    settings.pm_url = kwargs.get('pm_url', None) or u'%s/ws4pm.wsdl' % portal.absolute_url()
    settings.pm_username = kwargs.get('pm_username', None) or u'pmManager'
    settings.pm_password = kwargs.get('pm_password', None) or u'meeting'
    settings.user_mappings = kwargs.get('user_mappings', None) or \
                             u'localUserId|pmCreator1\r\nlocalUserId2|pmCreator2\r\nadmin|pmCreator1'
    settings.viewlet_display_condition = kwargs.get('viewlet_display_condition', None) or u''
    if not minimal:
        # these parameters are only available while correctly connected
        # to PloneMeeting webservices, either use withValidation=False
        # these fields mappings make it work if classic Document content_type
        settings.field_mappings = kwargs.get('field_mappings', None) or [
            {'field_name': u'title',
             'expression': u'object/Title'},
            {'field_name': u'description',
             'expression': u'object/Description'},
            # 'plonemeeting-assembly' does not use categories but 'plonegov-assembly' does
            {'field_name': u'category',
             'expression':
                u'python: object.REQUEST.get("meetingConfigId") != "plonemeeting-assembly" and "deployment" or ""'},
            {'field_name': u'decision',
             'expression': u'object/getText'},
            {'field_name': u'externalIdentifier',
             'expression': u'object/UID'}]
        settings.generated_actions = kwargs.get('generated_actions', None) or  [
            {'pm_proposing_group_id': u'developers',
             'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'developers',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:False',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'Manage portal'},
            ]
    if not withValidation:
        AbstractCollection._validate = old_validate


def createDocument(placeToCreate):
    """
      Helper method for creating a document object
    """
    data = {'title': 'Document title',
            'description': 'Document description',
            'text': '<p>Document rich text</p>'}
    documentId = placeToCreate.invokeFactory('Document', id='document', **data)
    document = getattr(placeToCreate, documentId)
    document.reindexObject()
    return document


def cleanMemoize(request, obj=None):
    """
      Remove every memoized informations : memoize on the REQUEST and on the object
    """
    annotations = IAnnotations(request)
    if 'plone.memoize' in annotations:
        annotations['plone.memoize'].clear()
    if obj and hasattr(aq_base(obj), '_memojito_'):
        delattr(obj, '_memojito_')
