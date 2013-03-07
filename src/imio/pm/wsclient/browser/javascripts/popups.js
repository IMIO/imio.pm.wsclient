/* The jQuery here above will load a jQuery popup */

// overlays for the action present in the object_actions dropdown list box 'Actions'
initializeActionsOverlays = function () {
jQuery('a.[id^=plone-contentmenu-actions-plonemeeting_wsclient_action_]').each(function(){
    // send an item to PloneMeeting
    $(this).prepOverlay({
       subtype: 'ajax',
   });
});
};

jQuery(document).ready(initializeActionsOverlays);

