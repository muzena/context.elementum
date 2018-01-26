# -*- coding: utf-8 -*-

"""
Misc functions for context handlers
"""

import sys
import xbmc
import xbmcaddon
import xbmcgui

try:
    import simplejson
except:
    import json as simplejson

import requests

from elementum.logger import log

ADDON = xbmcaddon.Addon()
api_key = ""


def doAssign():
    if not configureTMDB():
        return

    dbid = getDbId()
    imdbnumber = getIMDBNumber()
    mediatype = getMediaType()

    xbmcgui.Dialog().notification(ADDON.getLocalizedString(32011) if mediatype == 'season' else ADDON.getLocalizedString(32010), sys.listitem.getLabel(), xbmcgui.NOTIFICATION_INFO, 3000)

    log.debug("Assigning for: DBID=%s, IMDB=%s, MediaType=%s" % (dbid, imdbnumber, mediatype))

    # xbmc.executebuiltin("XBMC.RunPlugin(plugin://plugin.video.elementum/library/movie/play/%s)" % imdbnumber)


def doPlay():
    if not configureTMDB():
        return

    dbid = getDbId()
    imdbnumber = getIMDBNumber()
    mediatype = getMediaType()

    xbmcgui.Dialog().notification(ADDON.getLocalizedString(32009), sys.listitem.getLabel(), xbmcgui.NOTIFICATION_INFO, 3000)

    log.debug("Playing for: DBID=%s, IMDB=%s, MediaType=%s" % (dbid, imdbnumber, mediatype))

    if mediatype == 'movie':
        tmdb_id = getTMDBId('movie', imdbnumber)
        url = "plugin://plugin.video.elementum/library/movie/play/%s" % tmdb_id
    elif mediatype == 'episode':
        (show_id, season_number, episode_number) = getEpisodeDetails()
        tmdb_id = getTMDBId('show', show_id)
        url = "plugin://plugin.video.elementum/library/show/play/%s/%s/%s" % (tmdb_id, season_number, episode_number)

    log.debug("Fetched TMDB: %s" % tmdb_id)
    if tmdb_id is not None:
        log.debug("Starting Elementum with: %s" % url)
        xbmc.Player().play(url)


def getDbId():
    infolabel = xbmc.getInfoLabel('ListItem.Label')
    truelabel = sys.listitem.getLabel()
    if infolabel == truelabel:
        dbid = xbmc.getInfoLabel('ListItem.DBID')
    else:
        dbid = sys.listitem.getfilename().split('?')[0].rstrip('/').split('/')[-1]
    return dbid


def getIMDBNumber():
    return getVideoTag().getIMDBNumber()


def getMediaType():
    version = xbmcVersion()

    if xbmc.getInfoLabel('ListItem.DBTYPE'):
        # Seasons and calls from library will work
        return xbmc.getInfoLabel('ListItem.DBTYPE')
    elif version >= 18:
        # Will work on Kodi 17 and further
        return getVideoTag().getMediaType()
    else:
        # No other way, we query Kodi for information
        dbid = getDbId()

        response = getJSONResponse('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": { "movieid": %s }, "id": "0"}' % dbid)
        if 'error' not in response:
            return 'movie'

        response = getJSONResponse('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": { "episodeid": %s }, "id": "0"}' % dbid)
        if 'error' not in response:
            return 'episode'

        return None


def getEpisodeDetails():
    dbid = getDbId()
    response = getJSONResponse('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": { "episodeid": %s, "properties" : ["episode", "season","tvshowid"] }, "id": "0"}' % dbid)
    if 'result' in response:
        tvshowresponse = getJSONResponse('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": { "tvshowid": %s, "properties" : ["imdbnumber"] }, "id": "0"}' % response["result"]["episodedetails"]["tvshowid"])
        if 'result' in tvshowresponse:
            return (tvshowresponse["result"]["tvshowdetails"]["imdbnumber"], response["result"]["episodedetails"]["season"], response["result"]["episodedetails"]["episode"])


def getVideoTag():
    return sys.listitem.getVideoInfoTag()


def getTMDBId(mediatype, id):
    if isTMDBId(mediatype, id):
        return id
    else:
        if mediatype == 'movie':
            url = "https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=%s" % (id, api_key, 'imdb_id')
        elif mediatype == 'show':
            url = "https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=%s" % (id, api_key, 'tvdb_id')

        response = getJSON(url)

        if 'status_code' in response:
            xbmcgui.Dialog().notification(ADDON.getLocalizedString(32007), ADDON.getLocalizedString(32008), xbmcgui.NOTIFICATION_WARNING, 3000)
            return None

        if response['movie_results']:
            return response['movie_results'][0]['id']
        elif response['tv_results']:
            return response['tv_results'][0]['id']
        elif response['tv_episode_results']:
            return response['tv_episode_results'][0]['id']
        else:
            return None


def isTMDBId(mediatype, id):
    if mediatype == 'show':
        url = "https://api.themoviedb.org/3/tv/%s?api_key=%s&language=en-US" % (id, api_key)
    elif mediatype == 'movie':
        url = "https://api.themoviedb.org/3/movie/%s?api_key=%s&language=en-US" % (id, api_key)

    response = getJSON(url)

    if 'status_code' in response:
        return False
    else:
        return True


def xbmcVersion():
    build = xbmc.getInfoLabel('System.BuildVersion')

    methods = [
        lambda b: float(b.split()[0]),
        lambda b: float(b.split()[0].split('-')[1]),
        lambda b: float(b.split()[0].split('-')[0]),
        lambda b: 0.0
    ]

    for m in methods:
        try:
            version = m(build)
            break
        except ValueError:
            # parsing failed, try next method
            pass

    return version


def getJSONResponse(message):
    return simplejson.loads(xbmc.executeJSONRPC(message))


def configureTMDB():
    global api_key

    api_key = ADDON.getSetting('tmdb_api_key')
    if not api_key:
        # Temporarily use predefined key
        api_key = "29a551a65eef108dd01b46e27eb0554a"
        return True
        # xbmcgui.Dialog().notification(ADDON.getLocalizedString(32005),
        #    ADDON.getLocalizedString(32006), xbmcgui.NOTIFICATION_WARNING, 3000)
        # return False

    return True


def getJSON(url):
    page = requests.get(url).content
    try:
        return simplejson.loads(page)
    except:
        return simplejson.loads(page.decode('utf-8'))
