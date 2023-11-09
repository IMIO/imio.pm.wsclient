Changelog
=========

1.20 (unreleased)
-----------------

- Nothing changed yet.


1.19 (2023-11-09)
-----------------

- Fix encoding of values [URB-2785]
  [mpeeters]


1.18 (2023-08-14)
-----------------

- Fix an issue when there is a form instead of `onclick` attribute on input buttons
  [mpeeters]


1.17 (2022-06-29)
-----------------

- Cache the 'possible_meetingdates_vocabulary' vocabulary forever (until instance restarts).
  [sdelcourt]
  [mdhyne]
- By default make sure `inline_validation.js` is disabled to avoid too much calls to WS api.
  [gbastien]
- Added missing `docx.png`.
  [gbastien]
- Add a default inTheNameOf param for method _soap_getMeetingsAcceptingItems.
  [sdelcourt]

1.16 (2021-07-14)
-----------------

- Make sure to always find selected annexes to send with unrestricted catalog search.
  [sdelcourt]


1.15 (2021-03-29)
-----------------

- Use WSCLIENTLayer that inherits from PMLayer for WS4PMCLIENT
  so the amqp config is defined.
  [gbastien]
- Set correctly context in `renderTALExpression`
  [sgeulette]
- Do not rely on `unittest2` anymore.
  [gbastien]
- Fixed tests regarding `Meeting` moved from AT to DX.
  [gbastien]
- Set allowed_annexes_types default value to an empty list.
  [sdelcourt]

1.14 (2020-02-25)
-----------------

- Fixed tests as imio.pm.ws availableData to create an item now includes
  'associatedGroups', 'groupsInCharge', 'optionalAdvisers' and 'toDiscuss'.
  [gbastien]
- Replaced Plonemeeting by iA.delib in french translations.
  [sgeulette]

1.13 (2019-06-23)
-----------------

- Hide annexes field when there is no annex.
  [sgeulette]
- Can choose in settings to send multiple times an element
  [sgeulette]

1.12 (2018-12-04)
-----------------

- Fixed tests now that the create() testing helper method
  does not accept 'meetingConfig' paramter anymore.
  [gbastien]


1.11 (2017-10-13)
-----------------

- Display preferred meeting date in the item infos viewlet.
  [sdelcourt]


1.10 (2017-10-10)
-----------------

- Rename IPreferredMeetings interface.
  [sdelcourt]


1.9 (2017-10-10)
----------------

- Add preferred meeting selection in the send form.
  [sdelcourt]


1.8 (2017-08-22)
----------------

- Add translation for annex selection field.
  [sdelcourt]


1.7 (2017-08-18)
----------------

- Add annex selection in the send form.
  [sdelcourt]


1.6 (2017-05-24)
----------------

- Adapted regarding changes in imio.pm.ws for Products.PloneMeeting 4.0.
  [gbastien]


1.5 (2016-11-04)
----------------

- Try to make a correct release.
  [sdelcourt]


1.4 (2016-11-04)
----------------

- Add zope events WillbeSendToPMEvent and SentToPMEvent.
  [sdelcourt]


1.3 (2016-08-03)
----------------

- Display `extraAttrs` correctly in the preview form

1.2 (2016-05-13)
----------------
- Adapted code to work with Products.PloneMeeting 4.0

1.1 (2015-02-27)
----------------
- Adapted code to work with Products.PloneMeeting 3.3

1.0 (2015-02-27)
----------------
- Use with Products.PloneMeeting 3.2
- Initial release
