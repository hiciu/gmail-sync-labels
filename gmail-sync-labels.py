#!/usr/bin/python3.3

"""
Copyright (C) 2013 Krzysztof Warzecha <kwarzecha7@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import config

import imaplib
import os
import re
import shelve
import mailbox
import pprint
import ssl

if config.USE_NOTMUCH:
    import notmuch

class Gmail(imaplib.IMAP4_SSL):
    def __init__(self, login, password):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.set_default_verify_paths()
        # XXX: alternative, should work too:
        # ctx.load_verify_locations('/etc/ssl/certs/ca-certificates.crt')

        imaplib.IMAP4_SSL.__init__(self, 'imap.gmail.com', 993, ssl_context=ctx)

        # XXX: I have no idea how to check / if I need to check that thing. State from 2012-12-14.
        # MGL: set_default_verify_paths should do the work, as long as openssl is configured properly
        # assert self.sock.getpeercert() == {'subject': ((('countryName', 'US'),), (('stateOrProvinceName', 'California'),), (('localityName', 'Mountain View'),), (('organizationName', 'Google Inc'),), (('commonName', 'imap.gmail.com'),)), 'serialNumber': '3B73268B0000000068A5', 'subjectAltName': (('DNS', 'imap.gmail.com'),), 'version': 3, 'notBefore': 'Sep 12 11:55:49 2012 GMT', 'notAfter': 'Jun  7 19:43:27 2013 GMT', 'issuer': ((('countryName', 'US'),), (('organizationName', 'Google Inc'),), (('commonName', 'Google Internet Authority'),))}

        self.login(login, password)

        assert 'X-GM-EXT-1' in self.capabilities

        self.__message_from_imapid_re = re.compile('(\d+) \(X-GM-MSGID (\d+) X-GM-LABELS \((.*)\) RFC822 {(\d+)}')

    def selectfolder(self, folder, readonly=True):
        resp = self.select(folder, readonly)
        assert resp[0] == 'OK'

        total = int(resp[1][0])
        assert total > 0

        return total

    def listmessages(self, folder):
        print(' .. selecting mailbox')
        total = self.selectfolder(folder)

        print(' .. fetching remote index')
        resp = self.fetch('1:%d' % total, '(X-GM-MSGID)')

        assert resp[0] == 'OK'
        msglist = resp[1]

        headersexp = re.compile('(\d+) \(X-GM-MSGID (\d+)\)')

        print(' .. done')
        for msg in msglist:
            imapid, gmailid = headersexp.match(msg.decode('utf-8')).groups()

            yield int(imapid), int(gmailid)

    def message_from_imapid(self, imapid):
        resp = self.fetch('%d' % imapid, '(X-GM-MSGID X-GM-LABELS RFC822)')

        assert resp[0] == 'OK'
        assert resp[1][1] == b')'

        imapid, msgid, labels, msglen = self.__message_from_imapid_re.match(resp[1][0][0].decode('utf-8')).groups()

        assert int(msglen) == len(resp[1][0][1])

        mail = email.message_from_bytes(resp[1][0][1])
        mail.add_header('X-GM-MSGID', msgid)
        mail.add_header('X-GM-LABELS', labels)

        return mail

class MaildirDatabase(mailbox.Maildir):
    """ you should realy consider using some kind of database for this """
    def __init__(self, path):
        mailbox.Maildir.__init__(self, path)
        self.lock()

        self.__message_id_to_message_key = shelve.open(os.path.join(path, 'gmail-sync-labels.index'))
        self.__message_keys_without_message_id = shelve.open(os.path.join(path, 'gmail-sync-labels.missing'))

    def get_message_by_id(self, msgid):
        try:
            return self[self.__message_id_to_message_key[msgid]]
        except KeyError:
            return None

    def init(self):
        i = 0
        seen = 0
        skipped = 0
        known_message_keys = set(self.__message_id_to_message_key.values())
        known_bad_message_keys = set(self.__message_keys_without_message_id.keys())

        for key in sorted(self.iterkeys()):
            i += 1

            if i % 100 == 0:
                yield i
            
            if i % 1000 == 0:
                # print('snapshotting messages, seen %d of %d' % (seen, i))
                self.__message_id_to_message_key.sync()
                self.__message_keys_without_message_id.sync()

            if key in known_message_keys or key in known_bad_message_keys:
                seen += 1
                continue
            
            # TODO: handle duplicate message ids

            try:
                # print('processing key=%s' % key)
                message = self.get(key)
                self.__message_id_to_message_key[[v for k, v in message.items() if k.upper() == 'Message-ID'.upper()][0]] = key
            except IndexError:
                skipped += 1
                self.__message_keys_without_message_id[key] = None
                print('skipped message without Message-ID header: %s' % key)

        print('seen %d messages, skipped %d messages, processed %d messages' % (seen, skipped, i - seen - skipped))

    def close(self):
        self.__message_id_to_message_key.close()
        self.__message_keys_without_message_id.close()
        self.unlock()

    def apply_labels(self, msgid, labels):
        try:
            key = self.__message_id_to_message_key[msgid]
        except KeyError:
            print('no such message: %s' % msgid)
            return

        msg = self[key]
        if msg['X-GM-LABELS'] == labels:
            return

        del msg['X-GM-LABELS']
        msg['X-GM-LABELS'] = labels

        self[key] = msg

if config.USE_NOTMUCH:
    class NotmuchDatabase(notmuch.Database):
        def get_message_by_id(self, msgid):
            return self.find_message(msgid[1:-1])

        def init(self):
            yield len(self)

        def __len__(self):
            return self.create_query('').count_messages()

        def close(self):
            pass

        def apply_labels(self, msgid, labels):
            msg = self.find_message(msgid[1:-1])
            if not msg:
                print('no such message: %s' % msgid)
                return

            tags = list(filter(lambda x: len(x) != 0, map(str.strip, labels.split('"'))))

            if sorted(tags) == sorted(list(msg.get_tags())):
                return

            msg.freeze()
            msg.remove_all_tags(False)
            for tag in tags:
                msg.add_tag(tag, False)
            msg.thaw()
            msg.tags_to_maildir_flags()

def download_labels(gmail, total):
    resp = gmail.fetch('1:%d' % total, '(X-GM-THRID X-GM-MSGID X-GM-LABELS BODY[HEADER.FIELDS (MESSAGE-ID)])')

    assert resp[0] == 'OK'

    """
    response here is ugly:

    [(b'1 (X-GM-MSGID 1222139561679786370 X-GM-LABELS () BODY[HEADER.FIELDS (MESSAGE-ID)] {61}',
      b'Message-ID: <a38097d40612071225s1e399c3eu@mail.gmail.com>\r\n\r\n'),
     b')',
     (b'2 (X-GM-MSGID 1222140200241725271 X-GM-LABELS () BODY[HEADER.FIELDS (MESSAGE-ID)] {40}',
      b'Message-ID: <45787AFA.7020202@wp.pl>\r\n\r\n'),
     b')',
     ...
    ]
    """
    regexp = re.compile('(\d+) \(X-GM-THRID (\d+) X-GM-MSGID (\d+) X-GM-LABELS \((.*)\) BODY\[HEADER.FIELDS \(MESSAGE-ID\)\] {(\d+)}')

    # every even (2, 4, 6, 8, ...) item from response should be b')'
    for even_item in resp[1][1::2]:
        assert even_item == b')'

    # every odd (1, 3, 5, 7, ...) item should match regexp
    for odd_item in resp[1][::2]:
        imapid, gmailid, gmailthreadid, labels, payloadlen = regexp.match(odd_item[0].decode('utf-8')).groups()

        assert int(payloadlen) == len(odd_item[1])

        try:
            msgid = odd_item[1].decode('utf-8').split()[1]
        except IndexError:
            print('skipped message without Message-ID header: '
                  'gmail id %s, link: https://mail.google.com/mail/#all/%s'
                  % (gmailid, hex(int(gmailthreadid))[2:])
            )
            continue

        yield msgid, gmailid, labels

def main():
    print('opening maildir')
    if config.USE_NOTMUCH:
        db = NotmuchDatabase(mode=Database.MODE.READ_WRITE)
    else:
        db = MaildirDatabase(config.MAILDIR)

    total = len(db)

    try:
        print('searching for new messages')

        for progress in db.init():
            print('progress: %0.2f%%' % float(progress * 100 / total), end='\r')
        
        if config.INDEX_ONLY:
            print('indexing complete')
            return

        print('connecting to gmail')
        gmail = Gmail(config.LOGIN, config.PASSWORD)

        print('selecting mailbox')
        total = gmail.selectfolder(config.IMAP_FOLDER)
        i = 0

        print('downloading labels')
        for msgid, gmailid, labels in download_labels(gmail, total):
            i += 1
            if i % 10 == 0:
                print('progress: %0.2f%%' % float(i * 100 / total), end='\r')

            db.apply_labels(msgid, labels)

    finally:
        print('saving database')
        db.close()

if __name__ == "__main__":
    main()
