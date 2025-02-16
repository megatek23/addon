# -*- coding: utf-8 -*-
# --------------------------------------------------------
# Conector pornhub By Alfa development Group
# --------------------------------------------------------

import re
from core import httptools
from core import scrapertools
from platformcode import logger

def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    response = httptools.downloadpage(page_url)
    data = response.data
    if not response.sucess or "Not Found" in data or "Video Disabled" in data or "<div class=\"removed\">" in data or "is unavailable" in data:
        return False, "[pornhub] El fichero no existe o ha sido borrado"
    return True, ""


def get_video_url(page_url, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []
    headers = {'Referer': "%s" % page_url}
    url= ""
    data = httptools.downloadpage(page_url, headers=headers).data
    data = scrapertools.find_single_match(data, '<div id="player"(.*?)</script>')
    data = data.replace('" + "', '' )
    videourl = scrapertools.find_multiple_matches(data, 'var media_\d+=([^;]+)')
    for elem in videourl:
        orden = scrapertools.find_multiple_matches(elem, '\*\/([A-z0-9]+)')
        url= ""
        for i in orden:
            url += scrapertools.find_single_match(data, '%s="([^"]+)"' %i)
    data = httptools.downloadpage(url, headers=headers).json
    for elem in data:
        url = elem['videoUrl']
        quality = elem['quality']
        if url:
            video_urls.append(["%s [pornhub]" % quality, url])
    video_urls.pop()
    video_urls.sort(key=lambda item: int( re.sub("\D", "", item[0])))
    return video_urls


