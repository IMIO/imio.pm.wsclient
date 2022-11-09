files="imio.pm.wsclient PloneMeeting"
languages="en fr"

i18ndude rebuild-pot --pot imio.pm.wsclient.pot --create imio.pm.wsclient ../

for file in $files; do
    for language in $languages; do
        i18ndude sync --pot $file.pot $language/LC_MESSAGES/$file.po
        msgfmt -o $language/LC_MESSAGES/$file.mo $language/LC_MESSAGES/$file.po
    done
done
