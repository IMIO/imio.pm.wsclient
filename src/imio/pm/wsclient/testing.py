# -*- coding: utf-8 -*-
"""Test layers and a fake PloneMeeting.

PloneMeeting is not available in the tests: FakeSession replaces requests.Session
(used by browser/settings.py) and FAKE_PM answers the plonemeeting.restapi
endpoints the client calls, with data reset before each test.
"""
from imio.pm.wsclient.browser.settings import IWS4PMClientSettings
from imio.pm.wsclient.interfaces import IWS4PMClientLayer
from json import dumps
from json import loads
from plone import api
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import login
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry
from plone.testing import Layer
from plone.testing.zope import WSGI_SERVER_FIXTURE
from Products.statusmessages.interfaces import IStatusMessage
from unidecode import unidecode
from urllib.parse import parse_qs
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.ramcache.interfaces.ram import IRAMCache

import base64
import imio.pm.wsclient
import itertools
import mimetypes
import re
import requests
import transaction
import unittest


PM_URL = u"http://pm.example.org/plone"
PM_USERNAME = u"pmManager"
PM_PASSWORD = u"Meeting_12"
USER_PASSWORD = "Password_12"
SEND_TO_PM_VIEW_NAME = "@@send_to_plonemeeting_form"
STATE_TITLES = {
    "itemcreated": u"Created",
    "accepted": u"Accepted",
    "delayed": u"Delayed",
}


class FakeResponse(object):
    """What browser/settings.py reads of a requests.Response."""

    def __init__(self, status_code, data=None, content=None):
        self.status_code = status_code
        if content is None:
            content = b"" if data is None else dumps(data).encode("utf-8")
        self.content = content

    def json(self):
        return loads(self.content)


class FakeSession(object):
    """requests.Session sending its requests to FAKE_PM."""

    def __init__(self):
        self.auth = None
        self.headers = {}

    def get(self, url, **kwargs):
        return FAKE_PM.answer("get", url, self.auth)

    def post(self, url, json=None, **kwargs):
        # sent as JSON, like requests does
        return FAKE_PM.answer("post", url, self.auth, loads(dumps(json)))


def normalize(text):
    return re.sub(r"[^a-z0-9.]+", "-", unidecode(text).lower()).strip("-")


class FakePloneMeeting(object):
    """PloneMeeting site at PM_URL, with the answers of plonemeeting.restapi 2.x.

    Any user authenticates with PM_PASSWORD; a "manager" sees every item and meeting,
    the others the items of their proposing groups. Tests change the data in place
    (users, orgs, configs, items, meetings, files) or with add_item/add_meeting.
    """

    url = PM_URL

    def reset(self):
        self._uids = itertools.count(1)
        self._created = itertools.count(1)
        self.users = {
            u"pmManager": {
                "fullname": u"M. PMManager",
                "manager": True,
                "groups": [u"developers_creators", u"developers_reviewers"],
            },
            u"pmCreator1": {
                "fullname": u"M. PMCreator One",
                "groups": [u"developers_creators"],
            },
            u"pmCreator2": {
                "fullname": u"M. PMCreator Two",
                "groups": [u"vendors_creators"],
            },
        }
        self.orgs = [
            {"id": u"developers", "UID": self._uid(), "title": u"Developers"},
            {"id": u"vendors", "UID": self._uid(), "title": u"Vendors"},
        ]
        self.configs = [
            {
                "id": u"plonemeeting-assembly",
                "title": u"PloneMeeting assembly",
                "categories": [],
                "item_type": u"MeetingItemPma",
                "meeting_type": u"MeetingPma",
                "usedItemAttributes": [
                    u"description",
                    u"motivation",
                    u"toDiscuss",
                    u"itemIsSigned",
                ],
            },
            {
                "id": u"plonegov-assembly",
                "title": u"PloneGov assembly",
                "categories": [
                    {"id": cat_id, "title": title, "enabled": True}
                    for cat_id, title in (
                        (u"deployment", u"Deployment topics"),
                        (u"maintenance", u"Maintenance topics"),
                        (u"development", u"Development topics"),
                        (u"events", u"Events"),
                        (u"research", u"Research topics"),
                        (u"projects", u"Projects"),
                    )
                ],
                "item_type": u"MeetingItemPga",
                "meeting_type": u"MeetingPga",
                "usedItemAttributes": [
                    u"description",
                    u"category",
                    u"copyGroups",
                    u"itemTags",
                ],
            },
        ]
        self.pod_templates = [
            {
                "id": u"itemTemplate",
                "UID": self._uid(),
                "title": u"Meeting item",
                "formats": [u"odt", u"pdf"],
            }
        ]
        self.items = []
        self.meetings = []
        self.files = {}

    def _uid(self):
        return u"%032x" % next(self._uids)

    def find(self, elements, value, keys=("id", "UID")):
        for element in elements:
            if value in [element.get(key) for key in keys]:
                return element

    def add_meeting(self, config_id, date, review_state=u"created"):
        cfg = self.find(self.configs, config_id)
        meeting = {
            "UID": self._uid(),
            "id": u"o%d" % (len(self.meetings) + 1),
            "config_id": cfg["id"],
            "date": date.strftime("%Y-%m-%dT%H:%M:%S"),
            "title": date.strftime("%d %B %Y"),
            "review_state": review_state,
            "@type": cfg["meeting_type"],
        }
        meeting["@id"] = u"{0}/Members/pmManager/mymeetings/{1}/{2}".format(
            self.url, cfg["id"], meeting["id"]
        )
        self.meetings.append(meeting)
        return meeting

    def add_item(
        self, config_id, proposing_group, creator, title=u"", annexes=(), **data
    ):
        """Item as created by the @item endpoint, annexes as sent in __children__."""
        cfg = self.find(self.configs, config_id)
        item = dict(
            data,
            title=title,
            config_id=cfg["id"],
            creator=creator,
            proposingGroup=self.find(self.orgs, proposing_group)["id"],
            UID=self._uid(),
            id=normalize(title),
            review_state=u"itemcreated",
            meeting=None,
            successors=[],
            annexes=[],
            created=u"2026-01-01T10:%02d:00+00:00" % next(self._created),
        )
        item["@type"] = cfg["item_type"]
        item["@id"] = u"{0}/Members/{1}/mymeetings/{2}/{3}".format(
            self.url, creator, cfg["id"], item["id"]
        )
        for annex in annexes:
            annex_id = normalize(annex["file"]["filename"])
            download = u"{0}/{1}/@@download/file".format(item["@id"], annex_id)
            content = base64.b64decode(annex["file"]["data"])
            self.files[download] = content
            item["annexes"].append(
                {
                    "@id": u"{0}/{1}".format(item["@id"], annex_id),
                    "@type": u"annex",
                    "UID": self._uid(),
                    "id": annex_id,
                    "title": annex["title"],
                    "file": {
                        "content-type": mimetypes.guess_type(annex_id)[0]
                        or "application/octet-stream",
                        "download": download,
                        "filename": annex["file"]["filename"],
                        "size": len(content),
                    },
                }
            )
        self.items.append(item)
        return item

    def answer(self, method, url, auth, data=None):
        if not url.startswith(self.url + u"/"):
            raise requests.exceptions.ConnectionError(
                u"Failed to establish a new connection to {0}".format(url)
            )
        if not auth or auth[0] not in self.users or auth[1] != PM_PASSWORD:
            return FakeResponse(
                401, {"type": "Unauthorized", "message": "Wrong login and/or password."}
            )
        if url in self.files:
            return FakeResponse(200, content=self.files[url])
        path, _, query = url[len(self.url) + 1 :].partition(u"?")
        query = parse_qs(query, keep_blank_values=True)
        if path.endswith(u"/document-generation"):
            template = self.find(self.pod_templates, query["template_uid"][0])
            return FakeResponse(
                200,
                content=u"{0} ({1})".format(
                    template["title"], query["output_format"][0]
                ).encode("utf-8"),
            )
        endpoint, _, rest = path.partition(u"/")
        user_id = (data or {}).get("in_name_of") or query.get("in_name_of", [auth[0]])[
            0
        ]
        if user_id not in self.users:
            return FakeResponse(
                400,
                {"type": "BadRequest", "message": "User %s does not exist!" % user_id},
            )
        handler = getattr(self, "_{0}_{1}".format(method, endpoint.lstrip(u"@")), None)
        if handler is None:
            return FakeResponse(
                404, {"type": "NotFound", "message": "Resource not found: %s" % url}
            )
        return handler(user_id, rest, query, data)

    def _get_infos(self, user_id, rest, query, data):
        return FakeResponse(
            200,
            {
                "connected_user": user_id,
                "packages": {
                    "Products.PloneMeeting": "4.2",
                    "plonemeeting.restapi": "2.14",
                    "imio.restapi": "1.0",
                },
            },
        )

    def _get_users(self, user_id, rest, query, data):
        if rest not in self.users:
            return FakeResponse(
                404, {"type": "NotFound", "message": "User %s does not exist!" % rest}
            )
        res = {"id": rest, "fullname": self.users[rest]["fullname"]}
        asked = query.get("extra_include", [])
        if "groups" in asked:
            suffixes = query.get("extra_include_groups_suffixes", [])
            groups = self.users[rest]["groups"]
            res["extra_include_groups"] = [
                {"id": org["id"], "UID": org["UID"], "title": org["title"]}
                for org in self.orgs
                if [
                    g
                    for g in groups
                    if g.startswith(org["id"] + u"_")
                    and (not suffixes or g[len(org["id"]) + 1 :] in suffixes)
                ]
            ]
            res["extra_include_groups_items_total"] = len(res["extra_include_groups"])
        if "configs" in asked:
            res["extra_include_configs"] = [
                {"id": cfg["id"], "title": cfg["title"]} for cfg in self.configs
            ]
            res["extra_include_configs_items_total"] = len(self.configs)
        if "categories" in asked:
            config_ids = query.get("extra_include_categories_configs", [])
            res["extra_include_categories"] = {
                cfg["id"]: cfg["categories"]
                for cfg in self.configs
                if not config_ids or cfg["id"] in config_ids
            }
        return FakeResponse(200, res)

    def _get_config(self, user_id, rest, query, data):
        cfg = self.find(self.configs, query["config_id"][0])
        return FakeResponse(
            200,
            {
                "id": cfg["id"],
                "title": cfg["title"],
                "usedItemAttributes": [
                    {"token": attr, "title": attr} for attr in cfg["usedItemAttributes"]
                ],
            },
        )

    def _can_see(self, user_id, item):
        user = self.users[user_id]
        return user.get("manager") or [
            g for g in user["groups"] if g.startswith(item["proposingGroup"] + u"_")
        ]

    def _serialize(self, user_id, item, query, full=False, prefix=u""):
        res = {
            key: item.get(key, u"")
            for key in ("@id", "@type", "UID", "id", "title", "description", "created")
        }
        res["review_state"] = item["review_state"]
        if full:
            category = self.find(
                self.find(self.configs, item["config_id"])["categories"],
                item.get("category"),
            )
            meeting = self.find(
                self.meetings, item.get("preferredMeeting"), keys=("UID",)
            )
            res.update(
                {
                    "review_state": {
                        "token": item["review_state"],
                        "title": STATE_TITLES[item["review_state"]],
                    },
                    "creators": [
                        {
                            "token": item["creator"],
                            "title": self.users[item["creator"]]["fullname"],
                        }
                    ],
                    "proposingGroup": {
                        "token": item["proposingGroup"],
                        "title": self.find(self.orgs, item["proposingGroup"])["title"],
                    },
                    "category": {
                        "token": category and category["id"],
                        "title": category and category["title"],
                    },
                    "preferredMeeting": {
                        "token": meeting and meeting["UID"] or u"whatever",
                        "title": meeting and meeting["title"],
                    },
                    "externalIdentifier": item.get("externalIdentifier", u""),
                }
            )
        asked = query.get(prefix + u"extra_include", [])
        if "meeting" in asked:
            meeting = self.find(self.meetings, item["meeting"], keys=("UID",))
            res["extra_include_meeting"] = meeting and self._meeting(meeting) or {}
        if "linked_items" in asked:
            linked = [
                self._serialize(
                    user_id,
                    linked_item,
                    query,
                    prefix=prefix + u"extra_include_linked_items_",
                )
                for linked_item in self._successors(item)
                if self._can_see(user_id, linked_item)
            ]
            res["extra_include_linked_items"] = linked
            res["extra_include_linked_items_items_total"] = len(linked)
        if "annexes" in asked:
            res["extra_include_annexes"] = item["annexes"]
        if "pod_templates" in asked:
            res["extra_include_pod_templates"] = [
                {
                    "id": template["id"],
                    "UID": template["UID"],
                    "title": template["title"],
                    "outputs": [
                        {
                            "format": output_format,
                            "url": u"{0}/document-generation?template_uid={1}"
                            u"&output_format={2}".format(
                                item["@id"], template["UID"], output_format
                            ),
                        }
                        for output_format in template["formats"]
                    ],
                }
                for template in self.pod_templates
            ]
        if "config" in asked:
            cfg = self.find(self.configs, item["config_id"])
            res["extra_include_config"] = {"id": cfg["id"], "title": cfg["title"]}
        return res

    def _successors(self, item):
        for uid in item["successors"]:
            successor = self.find(self.items, uid, keys=("UID",))
            yield successor
            for sub_successor in self._successors(successor):
                yield sub_successor

    def _meeting(self, meeting):
        res = {
            key: meeting[key]
            for key in ("@id", "@type", "UID", "id", "title", "date", "review_state")
        }
        res.update({"@extra_includes": [], "description": u"", "enabled": None})
        return res

    def _get_search(self, user_id, rest, query, data):
        if query.get("type") == ["meeting"]:
            states = ["created", "frozen"] + (
                ["published", "decided"] if self.users[user_id].get("manager") else []
            )
            res = [
                self._meeting(meeting)
                for meeting in self.meetings
                if meeting["config_id"] in query["config_id"]
                and meeting["review_state"] in states
            ]
        else:
            filters = {
                "externalIdentifier": query.get("externalIdentifier"),
                "title": query.get("Title"),
                "config_id": query.get("config_id"),
            }
            res = [
                self._serialize(user_id, item, query)
                for item in self.items
                if self._can_see(user_id, item)
                and not [
                    key
                    for key, values in filters.items()
                    if values and item.get(key) not in values
                ]
            ]
        return FakeResponse(200, {"items": res, "items_total": len(res)})

    def _get_get(self, user_id, rest, query, data):
        uid = query.get("uid", query.get("UID", [None]))[0]
        external_id = query.get("externalIdentifier", [None])[0]
        config_id = query.get("config_id", [None])[0]
        for item in self.items:
            if (uid and item["UID"] == uid) or (
                not uid
                and item.get("externalIdentifier") == external_id
                and config_id in (None, item["config_id"])
            ):
                if not self._can_see(user_id, item):
                    return FakeResponse(
                        403,
                        {
                            "error": {
                                "type": "Forbidden",
                                "message": "Can not access item",
                            }
                        },
                    )
                return FakeResponse(
                    200, self._serialize(user_id, item, query, full=True)
                )
        return FakeResponse(
            404, {"error": {"type": "NotFound", "message": "Item not found"}}
        )

    def _post_item(self, user_id, rest, query, json_data):
        data = dict(json_data)
        cfg = self.find(self.configs, data.pop("config_id"))
        org = self.find(self.orgs, data.pop("proposingGroup"))
        if not org or org["id"] + u"_creators" not in self.users[user_id]["groups"]:
            return FakeResponse(
                400,
                {
                    "type": "BadRequest",
                    "message": u"[{'field': 'proposingGroup', 'message': "
                    u"u'Proposing group is not available for user.', 'error': 'ValidationError'}]",
                },
            )
        ignored = data.pop("ignore_validation_for", [])
        warnings = []
        if cfg["categories"] and not self.find(cfg["categories"], data.get("category")):
            if "category" not in ignored:
                return FakeResponse(
                    400,
                    {
                        "type": "BadRequest",
                        "message": u"[{'field': 'category', 'message': "
                        u"u'Please select a category.', 'error': 'ValidationError'}]",
                    },
                )
            warnings.append(
                u"Validation was ignored for following fields: %s."
                % u", ".join(ignored)
            )
        data.pop("in_name_of", None)
        item = self.add_item(
            cfg["id"], org["id"], user_id, annexes=data.pop("__children__", ()), **data
        )
        res = self._serialize(user_id, item, {}, full=True)
        if warnings:
            res["@warnings"] = warnings
        return FakeResponse(201, res)


FAKE_PM = FakePloneMeeting()


class FakePloneMeetingLayer(Layer):
    """FakeSession instead of requests.Session, FAKE_PM data reset before each test."""

    def setUp(self):
        self.session = requests.Session
        requests.Session = FakeSession
        FAKE_PM.reset()

    def tearDown(self):
        requests.Session = self.session

    def testSetUp(self):
        FAKE_PM.reset()
        # possible_meetingdates_vocabulary caches the PloneMeeting meetings
        getUtility(IRAMCache).invalidateAll()


FAKE_PM_FIXTURE = FakePloneMeetingLayer(name="FAKE_PM_FIXTURE")


class SendableAnnexes(object):
    """ISendableAnnexesToPM of the tests: the files of a folder (like the files
    attached to a mail in imio.dms.mail)."""

    def __init__(self, context):
        self.context = context

    def get(self):
        return [
            {"title": obj.Title(), "UID": obj.UID()}
            for obj in self.context.objectValues()
            if obj.portal_type == "File"
        ]


class WS4PMClientLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE, FAKE_PM_FIXTURE)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=imio.pm.wsclient, name="testing.zcml")

    def setUpPloneSite(self, portal):
        applyProfile(portal, "imio.pm.wsclient:testing")
        # no workflow, as Plone 4's PLONE_FIXTURE: content is visible to the members
        portal.portal_workflow.setDefaultChain("")
        for user_id in ("pmCreator1", "pmCreator2"):
            api.user.create(
                username=user_id,
                email="%s@example.org" % user_id,
                password=USER_PASSWORD,
            )
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        alsoProvides(portal.REQUEST, IWS4PMClientLayer)
        settings = getUtility(IRegistry).forInterface(IWS4PMClientSettings)
        settings.pm_url = PM_URL
        settings.pm_username = PM_USERNAME
        settings.pm_password = PM_PASSWORD
        settings.user_mappings = [
            {"local_userid": str(TEST_USER_ID), "pm_userid": u"pmCreator1"}
        ]
        settings.field_mappings = [
            {"field_name": u"title", "expression": u"object/Title"},
            {"field_name": u"description", "expression": u"object/Description"},
            {
                "field_name": u"decision",
                "expression": u"string:<p>${object/Description}</p>",
            },
            # plonegov-assembly uses categories: the item is always sent in "deployment"
            {
                "field_name": u"category",
                "expression": u'python: object.REQUEST.get("meetingConfigId") != "plonemeeting-assembly" and "deployment" or ""',
            },
            {"field_name": u"externalIdentifier", "expression": u"object/UID"},
        ]
        settings.generated_actions = [
            {
                "pm_meeting_config_id": u"plonemeeting-assembly",
                "condition": u"python:True",
                "permissions": u"View",
            },
            {
                "pm_meeting_config_id": u"plonegov-assembly",
                "condition": u"python:True",
                "permissions": u"Modify portal content",
            },
        ]
        transaction.commit()


FIXTURE = WS4PMClientLayer(name="FIXTURE")

INTEGRATION = IntegrationTesting(bases=(FIXTURE,), name="INTEGRATION")

FUNCTIONAL = FunctionalTesting(bases=(FIXTURE,), name="FUNCTIONAL")

ACCEPTANCE = FunctionalTesting(
    bases=(FIXTURE, REMOTE_LIBRARY_BUNDLE_FIXTURE, WSGI_SERVER_FIXTURE),
    name="ACCEPTANCE",
)


class WS4PMClientTestCase(unittest.TestCase):
    """Browser layer set; the test user is a Manager sending as pmCreator1 (user_mappings)."""

    layer = INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        alsoProvides(self.request, IWS4PMClientLayer)
        self.ws4pmSettings = getMultiAdapter(
            (self.portal, self.request), name="ws4pmclient-settings"
        )
        self.settings = self.ws4pmSettings.settings()

    def create_document(self, container=None, title=u"Document title"):
        return api.content.create(
            container=container or self.portal,
            type="Document",
            title=title,
            description=u"Document description",
        )

    def create_file(
        self,
        container,
        title=u"Annexe oubliée",
        data=b"hello\n",
        filename=u"annexe oubliée.txt",
    ):
        obj = api.content.create(container=container, type="File", title=title)
        obj.file = NamedBlobFile(data=data, filename=filename)
        return obj

    def send_form(self, obj, meeting_config_id="plonemeeting-assembly"):
        """The send form of obj, as opened by the generated action (request values are native strings)."""
        self.request.set("URL", obj.absolute_url())
        self.request.set(
            "ACTUAL_URL", "{0}/{1}".format(obj.absolute_url(), SEND_TO_PM_VIEW_NAME)
        )
        self.request.set("meetingConfigId", meeting_config_id)
        return obj.restrictedTraverse(SEND_TO_PM_VIEW_NAME).form_instance

    def send_to_pm(
        self,
        obj,
        meeting_config_id="plonemeeting-assembly",
        proposing_group=u"developers",
        **form
    ):
        """Submit the send form like a user; returns the created PloneMeeting item or None."""
        view = self.send_form(obj, meeting_config_id)
        self.request.form.update(
            {
                "form.widgets.meetingConfigId": str(meeting_config_id),
                "form.widgets.proposingGroup": [
                    FAKE_PM.find(FAKE_PM.orgs, proposing_group)["UID"]
                ],
                "form.buttons.send_to_plonemeeting": u"Send",
            }
        )
        self.request.form.update(form)
        view()
        self.clean_form()
        items = [
            item
            for item in FAKE_PM.items
            if item.get("externalIdentifier") == obj.UID()
        ]
        return items[-1] if items else None

    def clean_form(self):
        """Remove the submitted values, also cached in request.other by request.get."""
        for values in (self.request.form, self.request.other):
            for key in [key for key in values if key.startswith("form.")]:
                del values[key]

    def messages(self):
        """Status messages shown (not kept for the next page as after a redirect)."""
        self.request.response.setStatus(200)
        return [message.message for message in IStatusMessage(self.request).show()]

    def clean_memoize(self, obj=None):
        """Forget the PloneMeeting answers memoized on the request (and on obj)."""
        IAnnotations(self.request).get("plone.memoize", {}).clear()
        if obj is not None and "_memojito_" in obj.__dict__:
            del obj._memojito_
