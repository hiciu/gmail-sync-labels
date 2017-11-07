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

    cp config.py.template config.py
    edit config_named.py
    python3 gmail-sync-labels.py config_named
