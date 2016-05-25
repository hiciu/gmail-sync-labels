#!/usr/bin/python3

import config_oldbw
import config_newbw
import email.header
import imaplib
import os
import pprint
import re
import shelve
import ssl

class Gmail(imaplib.IMAP4_SSL):
    def __init__(self, cfg):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.set_default_verify_paths()
        # XXX: alternative, should work too:
        # ctx.load_verify_locations('/etc/ssl/certs/ca-certificates.crt')

        imaplib.IMAP4_SSL.__init__(self, 'imap.gmail.com', 993, ssl_context=ctx)

        # XXX: I have no idea how to check / if I need to check that thing. State from 2012-12-14.
        # MGL: set_default_verify_paths should do the work, as long as openssl is configured properly
        # assert self.sock.getpeercert() == {'subject': ((('countryName', 'US'),), (('stateOrProvinceName', 'California'),), (('localityName', 'Mountain View'),), (('organizationName', 'Google Inc'),), (('commonName', 'imap.gmail.com'),)), 'serialNumber': '3B73268B0000000068A5', 'subjectAltName': (('DNS', 'imap.gmail.com'),), 'version': 3, 'notBefore': 'Sep 12 11:55:49 2012 GMT', 'notAfter': 'Jun  7 19:43:27 2013 GMT', 'issuer': ((('countryName', 'US'),), (('organizationName', 'Google Inc'),), (('commonName', 'Google Internet Authority'),))}

        self.login(cfg.LOGIN, cfg.PASSWORD)

        assert 'X-GM-EXT-1' in self.capabilities

    def selectfolder(self, folder, readonly=True):
        resp = self.select(folder, readonly)
        assert resp[0] == 'OK'

        total = int(resp[1][0])
        assert total > 0

        return total

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
        imapid, gmailthreadid, gmailid, labels, payloadlen = regexp.match(odd_item[0].decode('utf-8')).groups()

        assert int(payloadlen) == len(odd_item[1])

        try:
            msgid = odd_item[1].decode('utf-8').split()[1]
        except IndexError:
            if config.DEBUG or config.MESSAGE_DETAILS:
                print('got message without Message-ID header: '
                      'gmail id %s, link: https://mail.google.com/mail/#all/%s'
                      % (gmailid, hex(int(gmailthreadid))[2:])
                )
            #continue
            # allow update by gmail id
            msgid = None

        yield msgid, gmailid, gmailthreadid, labels

def create_label_index(gmail, cfg):
    total = gmail.selectfolder(cfg.IMAP_FOLDER)
    index = dict()
    for msgid, gmailid, gmailthreadid, labels in download_labels(gmail, total):
        raise Exception('Not Implemented')

def apply_labels(gmail, cfg, index):
    raise Exception('Not Implemented')

def main():
    labelsfile = 'gmail-restore-labels.labels.pickle'
    index = None
    try:
        with open(labelsfile, 'rb') as f:
            index = pickle.load(f)
    except FileNotFoundError:
        print('No index file, will generate one')
        index = None
    if index is None:
        with oldgmail = Gmail(config_oldbw):
            index = create_label_index(oldgmail, cfg_oldbw)
        with open(labelsfile, 'rb') as f:
            pickle.dump(index, f)
    
    with newgmail = Gmail(config_newbw):
        apply_labels(newgmail, config_newbw, index)
    
    return

if __name__ == "__main__":
    main()
