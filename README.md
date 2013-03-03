How this is supposed to work
============================

This script should download message labels from gmail and apply them on local copy of that messages (made with [getmail](http://pyropus.ca/software/getmail/) or other software) either as tags in notmuch database ([notmuch, the mail indexer](http://notmuchmail.org/), something like offline gmail in shell) or as header in messages.

Idea is really simple:

1. if not using notmuch: 
    1. prepare index "Message-ID header" => "message file"
    2. save index in $MAILDIR/gmail-sync-labels.index
2. Download (message-id, labels) pairs from gmail
3. Apply labels on message with message-id

How to use this
=============

before: make backup of your Maildir. It works for me, but it may destroy mails for you.

    cp config.py.template config.py
    edit config.py
    python3 gmail-sync-labels.py
