How this is supposed to work
============================

This script should download message labels from gmail and apply them on
local copy of that messages (made with
[getmail](http://pyropus.ca/software/getmail/) or other software) as header
in messages.

Idea is really simple:

1. prepare index "Message-ID header" => "message file"
2. save index in $MAILDIR/gmail-sync-labels.index
3. Download (message-id, labels) pairs from gmail
4. Apply labels on message with message-id

How to use this
=============

before: make backup of your Maildir.  It works for me, but it may destroy
mails for you.  It was tested with python 3.3, it may or may not work with
older releases.  Feel free to post patches / pull requests / issues about
older versions.

    cp config.py.template config_named.py
    edit config_named.py
    python3 gmail-sync-labels.py config_named

How to use the label restorer
=============================

The restorer currently works by copying from one gmail account to another,
keying by message ID.  Note that this tool is not well tested.

    cp config.py.template config_old.py
    cp config.py.template config_new.py
    edit config_old.py config_new.py
    python3 gmail-restore-labels.py config_old config_new

Similar Projects
================

1. [gmail-notmuch](http://git.zx2c4.com/gmail-notmuch/)
   <br/>This project used to have NotMuch support, but it was removed for lack of maintenance.

See Also
=============
* https://github.com/hiciu/gmail-sync-labels
* https://github.com/fastcat/gmail-sync-labels
