/* The jQuery here above will load a jQuery popup */

// overlays for the action present in the object_actions dropdown list box 'Actions'
initializeActionsOverlays = function () {
jQuery('a.[id^=plone-contentmenu-actions-plonemeeting_wsclient_action_]').each(function(){
    // send an item to PloneMeeting
    // apply if no proposingGroupId is passed in the request
    if ($(this).attr('href').indexOf('&proposingGroupId=') == -1) {
    $(this).prepOverlay({
        subtype: 'ajax',
        formselector: '#form',
        closeselector: '[name="form.button.Cancel"]',
   });}
});
};

jQuery(document).ready(initializeActionsOverlays);
