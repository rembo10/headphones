import os
import re
from urlparse import urlparse

from lib.rtorrent import RTorrent

import headphones
from headphones import logger, helpers


class rtorrentclient(object):
    def __init__(self):
        self.conn = None

        host = headphones.CONFIG.RTORRENT_HOST
        if not host.startswith('http'):
            host = 'http://' + host

        if host.endswith('/'):
            host = host[:-1]

        self.username = headphones.CONFIG.RTORRENT_USERNAME
        self.password = headphones.CONFIG.RTORRENT_PASSWORD
        self.auth = headphones.CONFIG.RTORRENT_AUTHENTICATION
        self.verify = headphones.CONFIG.RTORRENT_VERIFY
        self.ssl = headphones.CONFIG.RTORRENT_SSL
        self.rpcurl = headphones.CONFIG.RTORRENT_RPC_URL

        ca_bundle = None
        if headphones.CONFIG.RTORRENT_CA_BUNDLE is not None:
            ca_bundle = headphones.CONFIG.RTORRENT_CA_BUNDLE

        logger.debug('calling connect(%s,%s,%s,%s,%s,%s,%s,%s)',
                host, self.username, "PASSWORD", self.auth, self.verify,
                self.ssl, self.rpcurl, ca_bundle)
        self.conn = self.connect(host, self.username, self.password,
                self.auth, self.verify, self.ssl, self.rpcurl, ca_bundle)

        if self.conn is None:
            logger.warn('Could not establish connection to %s' % host)
            return 'Error establishing connection to Rtorrent'

    def getVerifySsl(self, verify, ca_bundle):
        # Ensure verification has been enabled
        if not verify:
            return False

        # Use ca bundle if defined
        if ca_bundle is not None and os.path.exists(ca_bundle):
            return ca_bundle

        # Use default ssl verification
        return True

    def connect(self, host, username, password, auth, verify, ssl, rpc_url, ca_bundle):
        if self.conn is not None:
            return self.conn

        if not host:
            return False

        url = helpers.cleanHost(host, protocol=True, ssl=ssl)

        # Automatically add '+https' to 'httprpc' protocol if SSL is enabled
        if ssl is True and url.startswith('httprpc://'):
            url = url.replace('httprpc://', 'httprpc+https://')

        parsed = urlparse(url)

        # rpc_url is only used on http/https scgi pass-through
        if parsed.scheme in ['http', 'https']:
            url += rpc_url

        logger.debug(url)

        if username and password:
            try:
                self.conn = RTorrent(
                    url, (auth, username, password),
                    verify_server=True,
                    verify_ssl=self.getVerifySsl(verify, ca_bundle)
                )
            except Exception as err:
                logger.error('Failed to connect to rTorrent: %s', err)
                return False
        else:
            logger.debug('NO username %s / NO password %s' % (username, password))
            try:
                self.conn = RTorrent(
                    url, (auth, username, password),
                    verify_server=True,
                    verify_ssl=self.getVerifySsl(verify, ca_bundle)
                )
            except Exception as err:
                logger.error('Failed to connect to rTorrent: %s', err)
                return False

        return self.conn

    def find_torrent(self, hash):
        return self.conn.find_torrent(hash)

    def get_torrent(self, torrent):
        torrent_files = []
        torrent_directory = os.path.normpath(torrent.directory)
        try:
            for f in torrent.get_files():
                if not os.path.normpath(f.path).startswith(torrent_directory):
                    file_path = os.path.join(torrent_directory, f.path.lstrip('/'))
                else:
                    file_path = f.path

                torrent_files.append(file_path)

            torrent_info = {
                'hash': torrent.info_hash,
                'name': torrent.name,
                'label': torrent.get_custom1() if torrent.get_custom1() else '',
                'folder': torrent_directory,
                'completed': torrent.complete,
                'files': torrent_files,
                'upload_total': torrent.get_up_total(),
                'download_total': torrent.get_down_total(),
                'ratio': torrent.get_ratio(),
                'total_filesize': torrent.get_size_bytes(),
                'time_started': torrent.get_time_started()
                }

        except Exception:
            raise

        return torrent_info if torrent_info else False

    def load_torrent(self, filepath):
        start = bool(headphones.CONFIG.RTORRENT_STARTONLOAD)

        if filepath.startswith('magnet'):
            logger.debug('torrent magnet link set to : ' + filepath)
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', filepath)[0].upper()
            # Send request to rTorrent
            try:
                # cannot verify_load magnet as it might take a very very long time for it to retrieve metadata
                torrent = self.conn.load_magnet(filepath, torrent_hash, verify_load=True)
                if not torrent:
                    logger.error('Unable to find the torrent, did it fail to load?')
                    return False
            except Exception as err:
                logger.error('Failed to send magnet to rTorrent: %s', err)
                return False
            else:
                logger.info('Torrent successfully loaded into rtorrent using magnet link as source.')
        else:
            logger.debug('filepath to torrent file set to : ' + filepath)
            try:
                torrent = self.conn.load_torrent(filepath, verify_load=True)
                if not torrent:
                    logger.error('Unable to find the torrent, did it fail to load?')
                    return False
            except Exception as err:
                logger.error('Failed to send torrent to rTorrent: %s', err)
                return False

        # we can cherrypick the torrents here if required and if it's a pack (0day instance)
        # torrent.get_files() will return list of files in torrent
        # f.set_priority(0,1,2)
        # for f in torrent.get_files():
        #     logger.info('torrent_get_files: %s' % f)
        #     f.set_priority(0)  #set them to not download just to see if this works...
        # torrent.updated_priorities()

        if headphones.CONFIG.RTORRENT_LABEL is not None:
            torrent.set_custom(1, headphones.CONFIG.RTORRENT_LABEL)
            logger.debug('Setting label for torrent to : ' + headphones.CONFIG.RTORRENT_LABEL)

        if headphones.CONFIG.RTORRENT_DIRECTORY is not None:
            torrent.set_directory(headphones.CONFIG.RTORRENT_DIRECTORY)
            logger.debug('Setting directory for torrent to : ' + headphones.CONFIG.RTORRENT_DIRECTORY)

        logger.info('Successfully loaded torrent.')

        # note that if set_directory is enabled, the torrent has to be started AFTER it's loaded or else it will give chunk errors and not seed
        if start:
            logger.info('[' + str(start) + '] Now starting torrent.')
            torrent.start()
        else:
            logger.info('[' + str(start) + '] Not starting torrent due to configuration setting.')
        return True

    def start_torrent(self, torrent):
        return torrent.start()

    def stop_torrent(self, torrent):
        return torrent.stop()

    def delete_torrent(self, torrent):
        deleted = []
        try:
            for file_item in torrent.get_files():
                file_path = os.path.join(torrent.directory, file_item.path)
                os.unlink(file_path)
                deleted.append(file_item.path)

            if torrent.is_multi_file() and torrent.directory.endswith(torrent.name):
                try:
                    for path, _, _ in os.walk(torrent.directory, topdown=False):
                        os.rmdir(path)
                        deleted.append(path)
                except:
                    pass
        except Exception:
            raise

        torrent.erase()

        return deleted


def addTorrent(link):
    rtorrentClient = rtorrentclient()
    return rtorrentClient.load_torrent(link)
    return True
