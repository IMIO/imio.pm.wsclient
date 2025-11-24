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
        noform: 'redirect',
        redirect: $.plonepopups.redirectbasehref,
        closeselector: '[name="form.buttons.cancel"]'
    });}
});


function cleanURL(url) {
    return url.replace("javascript:", '').replace("window.location='", '').replace("window.open('", '').replace(", '_parent')", '').replace("'", "");
};

// while used with imio.actionspanel, we need to turn a <input> into a <a>
// to be able to use an overlay
jQuery('input.[class*=apButtonAction_plonemeeting_wsclient_action_]').each(function(){
    // send an item to PloneMeeting
    // apply if no proposingGroupId is passed in the request
    if ($(this).attr('onclick') && $(this).attr('onclick').indexOf('&proposingGroupId=') == -1) {
        // add a surrounding <a></a> tag as overlays are only working with links
        // extract window.location attribute from current input.onclick value
        url = $(this).attr('onclick');
        // clean URL as it could contain a javascript call like window.location, window.open, ...
        url = cleanURL(url)
        $(this).wrap("<a href='"+ url +"'></a>");
        // remove the onclick and use his value as href for added <a></a>
        $(this)[0].attributes['onclick'].value = '';
        // now work with the parent, actually the added <a>
        parent = $(this).parent();
        parent.prepOverlay({
            subtype: 'ajax',
            formselector: '#form',
            noform: 'redirect',
            redirect: $.plonepopups.redirectbasehref,
            closeselector: '[name="form.buttons.cancel"]'
        });
    } else {
        form = $(this).parent("form")
        if (form) {
            url = form.attr('action');
            // clean URL as it could contain a javascript call like window.location, window.open, ...
            url = cleanURL(url)
            $(this).wrap("<a href='"+ url +"'></a>");
            // remove the onclick and use his value as href for added <a></a>
            form.attr('action', '');
            // now work with the parent, actually the added <a>
            parent = $(this).parent();
            parent.prepOverlay({
                subtype: 'ajax',
                filter: "#content",
                formselector: '#form',
                noform: 'redirect',
                redirect: $.plonepopups.redirectbasehref,
                closeselector: '[name="form.buttons.cancel"]'
            });
        }
    }
});

};

jQuery(document).ready(initializeActionsOverlays);
